from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app import store
from app.assistant_policy import diagnose, fold, snapshot
from app.dependencies import current_user
from app.rag import KnowledgeBaseUnavailableError, generate_answer, OUT_OF_SCOPE_PATTERNS
from app.schemas import RAGFeedback, RAGQuestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask")
def ask_rag(request: Request, payload: RAGQuestion) -> dict:
    # FastAPI runs sync endpoints in its worker pool, including DB and LLM waits.
    user = current_user(request)
    history = []
    if payload.session_id:
        session = store.get_chat_session(user["username"], payload.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.")
        history = session["messages"]
    context = store.get_incident_context(user["username"], payload.session_id) if payload.session_id else None
    if context is None and history:
        first_question = next((m["content"] for m in history if m["role"] == "user"), "")
        seed = diagnose(first_question)
        context = seed["context"] if seed else None
    if payload.action or payload.fact_answers or payload.step_results:
        if context is None or payload.expected_revision != context.get("revision", 0):
            raise HTTPException(status_code=409, detail="Sự cố đã thay đổi. Tải lại lượt hiện tại trước khi xác nhận.")
    expected_revision = context.get("revision", 0) if context else None
    try:
        policy = diagnose(payload.question.strip(), context, action=payload.action,
                          answers=payload.fact_answers, step_results=payload.step_results, role=user["role"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if policy is None and (payload.action or payload.fact_answers or payload.step_results):
        raise HTTPException(status_code=422, detail="Không có sự cố đang hoạt động cho thao tác này.")
    try:
        if policy and not any(pattern in fold(payload.question) for pattern in OUT_OF_SCOPE_PATTERNS):
            result = {"answer": "", "sources": [], "triage": {"category": {"printer": "hardware", "network": "network"}.get(policy["incident_topic"], "general"), "priority": "medium", "priority_reason": "Mức tạm thời; cần xác nhận tác động và độ khẩn cấp."}}
        else:
            result = generate_answer(payload.question.strip())
    except KnowledgeBaseUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Kho tri thức tạm thời không khả dụng. Vui lòng thử lại sau.",
        ) from exc
    # Retrieval is not approval: a paraphrase missed by topic detection must
    # never expose legacy procedural text outside the reviewed catalogue.
    if policy is None and result.get("matches") and not result.get("out_of_scope"):
        policy = diagnose(payload.question.strip(), {
            "topic": "other_it", "initial_question": payload.question.strip(),
            "facts": {}, "state": "CLARIFY", "steps": [], "sources": [],
        })
    if result.get("out_of_scope"):
        result["triage"]["resolution_scope"] = "OUT_OF_SCOPE"
    if policy and not result.get("out_of_scope"):
        result.update({k: v for k, v in policy.items() if k != "context"})
        context = policy["context"]
        context["revision"] = (expected_revision or 0) + 1
        result["revision"] = context["revision"]
        result["handoff_question"] = policy["handoff"]["description"]
        result.update(sources=[], matches=[], grounded=False, llm_generated=False)
        result["triage"]["resolution_scope"] = "ESCALATE_IT" if policy["state"] in ("HANDOFF_PREVIEW", "IN_SCOPE_NO_SOURCE") else policy["state"]
    try:
        result["session_id"] = store.save_chat_exchange(
            user["username"],
            payload.session_id,
            payload.question.strip(),
            result["answer"],
            result["sources"],
            incident_context=context,
            expected_revision=expected_revision,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Sự cố đã được cập nhật bởi yêu cầu khác.") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.") from exc
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
