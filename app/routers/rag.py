from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app import store
from app.assistant_policy import diagnose, snapshot, incident_triage
from app.dependencies import current_user
from app.rag import KnowledgeBaseUnavailableError, contextualize_question, generate_answer
from app.schemas import RAGFeedback, RAGQuestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask")
def ask_rag(request: Request, payload: RAGQuestion) -> dict:
    user = current_user(request)
    messages = []
    existing_context = None

    # 1. Lấy lịch sử hội thoại và context sự cố hiện tại từ session
    if payload.session_id:
        session = store.get_chat_session(user["username"], payload.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.")
        messages = session["messages"]
        existing_context = store.get_incident_context(user["username"], payload.session_id)

    question = payload.question.strip()
    contextual_question = contextualize_question(question, messages)
    expected_revision = getattr(payload, "expected_revision", None)

    # 2. Thực thi chẩn đoán theo chính sách (truyền kèm existing_context và payload)
    policy = diagnose(
        question,
        context=existing_context,
        payload=payload,
    )

    try:
        result = generate_answer(contextual_question)
        result["context_used"] = contextual_question != question
    except KnowledgeBaseUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Kho tri thức tạm thời không khả dụng. Vui lòng thử lại sau.",
        ) from exc

    # 3. Phân nhánh xử lý giữa Policy sự cố và tra cứu RAG thông thường
    if policy and not result.get("out_of_scope"):
        result.update({k: v for k, v in policy.items() if k != "context"})
        context = policy.get("context", {})
        if "revision" in context:
            result["revision"] = context["revision"]
        if "handoff" in policy and isinstance(policy["handoff"], dict) and "description" in policy["handoff"]:
            result["handoff_question"] = policy["handoff"]["description"]
        
        # Chỉ xóa sources nếu chính sách yêu cầu ẩn RAG
        if policy.get("override_rag", True):
            result.update(sources=[], matches=[], grounded=False, llm_generated=False)
        result["triage"] = incident_triage(context)
    else:
        context = existing_context
        if result.get("out_of_scope"):
            result.setdefault("triage", {})["resolution_scope"] = "OUT_OF_SCOPE"

    # 4. Lưu dữ liệu hội thoại vào store
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
