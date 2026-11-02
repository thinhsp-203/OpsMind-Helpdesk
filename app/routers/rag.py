from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app import store
from app.assistant_policy import diagnose, fold, incident_triage, snapshot
from app.dependencies import current_user
from app.rag import (
    KnowledgeBaseUnavailableError,
    contextualize_question,
    generate_answer,
    OUT_OF_SCOPE_PATTERNS,
)
from app.schemas import RAGFeedback, RAGQuestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask")
def ask_rag(request: Request, payload: RAGQuestion) -> dict:
    """Answer with published sources and optional bounded follow-up context.

    `has_sources` (legacy alias `grounded`) describes retrieval only.
    `answer_verification=not_verified` makes no semantic truth/faithfulness claim.
    `context_used` is true only when a recent user description was incorporated.
    """
    # FastAPI runs sync endpoints in its worker pool, including DB and LLM waits.
    user = current_user(request)
    messages = []
    if payload.session_id:
        session = store.get_chat_session(user["username"], payload.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.")
        messages = session["messages"]

    context = (
        store.get_incident_context(user["username"], payload.session_id)
        if payload.session_id
        else None
    )
    if context is None and messages:
        first_question = next((m["content"] for m in messages if m["role"] == "user"), "")
        seed = diagnose(first_question)
        context = seed["context"] if seed else None

    if payload.action or payload.fact_answers or payload.step_results:
        if context is None or payload.expected_revision != context.get("revision", 0):
            raise HTTPException(
                status_code=409,
                detail="Sự cố đã thay đổi. Tải lại lượt hiện tại trước khi xác nhận.",
            )

    expected_revision = context.get("revision", 0) if context else None
    question = payload.question.strip()

    try:
        policy = diagnose(
            question,
            context,
            action=payload.action,
            answers=payload.fact_answers,
            step_results=payload.step_results,
            role=user["role"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if policy is None and (payload.action or payload.fact_answers or payload.step_results):
        raise HTTPException(
            status_code=422,
            detail="Không có sự cố đang hoạt động cho thao tác này.",
        )

    contextual_question = contextualize_question(question, messages)
    is_explicit_oos = any(pattern in fold(question) for pattern in OUT_OF_SCOPE_PATTERNS)

    try:
        if policy and policy.get("incident_topic") != "other_it" and not is_explicit_oos:
            result = {
                "answer": "",
                "sources": [],
                "grounded": False,
                "has_sources": False,
                "answer_verification": "not_verified",
                "context_used": contextual_question != question,
                "triage": {
                    "category": {
                        "printer": "hardware",
                        "network": "network",
                    }.get(policy["incident_topic"], "general"),
                    "priority": "medium",
                    "priority_reason": "Mức tạm thời; cần xác nhận tác động và độ khẩn cấp.",
                },
            }
        else:
            result = generate_answer(contextual_question)
            result["context_used"] = contextual_question != question
    except KnowledgeBaseUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Kho tri thức tạm thời không khả dụng. Vui lòng thử lại sau.",
        ) from exc

    # Retrieval is not approval: a paraphrase missed by topic detection must
    # never expose legacy procedural text outside the reviewed catalogue.
    if policy is None and result.get("matches") and not is_explicit_oos:
        policy = diagnose(
            question,
            {
                "topic": "other_it",
                "initial_question": question,
                "facts": {},
                "state": "CLARIFY",
                "steps": [],
                "sources": [],
            },
        )

    if is_explicit_oos:
        result.setdefault("triage", {})["resolution_scope"] = "OUT_OF_SCOPE"
        result["out_of_scope"] = True
        policy = None
    elif policy is None and result.get("out_of_scope"):
        result.setdefault("triage", {})["resolution_scope"] = "OUT_OF_SCOPE"
        result["out_of_scope"] = True

    if policy:
        result.update({k: v for k, v in policy.items() if k != "context"})
        context = policy["context"]
        context["revision"] = (expected_revision or 0) + 1
        result["revision"] = context["revision"]
        result["handoff_question"] = policy["handoff"]["description"]
        result.update(
            sources=[],
            matches=[],
            grounded=False,
            has_sources=False,
            llm_generated=False,
            out_of_scope=False,
        )
        result["triage"] = incident_triage(context)

    try:
        result["session_id"] = store.save_chat_exchange(
            user["username"],
            payload.session_id,
            question,
            result["answer"],
            result.get("sources", []),
            incident_context=context,
            expected_revision=expected_revision,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail="Sự cố đã được cập nhật bởi yêu cầu khác.",
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phiên hội thoại.",
        ) from exc

    saved_session = store.get_chat_session(user["username"], result["session_id"])
    result["assistant_message_id"] = saved_session["messages"][-1]["id"]
    return result


@router.get("/sessions")
def get_rag_sessions(request: Request) -> list[dict]:
    user = current_user(request)
    return store.list_chat_sessions(user["username"])


@router.get("/sessions/{session_id}")
def get_rag_session(request: Request, session_id: str) -> dict:
    user = current_user(request)
    session = store.get_chat_session(user["username"], session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.")
    context = store.get_incident_context(user["username"], session_id)
    session["diagnostic"] = snapshot(context) if context else None
    return session


@router.post("/feedback")
def provide_rag_feedback(request: Request, payload: RAGFeedback) -> dict[str, str]:
    user = current_user(request)
    if not store.set_chat_feedback(user["username"], payload.message_id, payload.feedback):
        raise HTTPException(status_code=404, detail="Không tìm thấy câu trả lời để đánh giá.")
    return {"message": "Đã ghi nhận phản hồi."}
