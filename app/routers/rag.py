from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app import store
from app.dependencies import current_user
from app.rag import KnowledgeBaseUnavailableError, contextualize_question, generate_answer
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
    question = payload.question.strip()
    contextual_question = contextualize_question(question, messages)
    try:
        result = generate_answer(contextual_question)
        result["context_used"] = contextual_question != question
    except KnowledgeBaseUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Kho tri thức tạm thời không khả dụng. Vui lòng thử lại sau.",
        ) from exc
    try:
        result["session_id"] = store.save_chat_exchange(
            user["username"],
            payload.session_id,
            payload.question.strip(),
            result["answer"],
            result["sources"],
        )
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
    return session


@router.post("/feedback")
def provide_rag_feedback(request: Request, payload: RAGFeedback) -> dict[str, str]:
    user = current_user(request)
    if not store.set_chat_feedback(user["username"], payload.message_id, payload.feedback):
        raise HTTPException(status_code=404, detail="Không tìm thấy câu trả lời để đánh giá.")
    return {"message": "Đã ghi nhận phản hồi."}
