from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app import store
from app.dependencies import current_user
from app.rag import generate_answer
from app.schemas import RAGFeedback, RAGQuestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask")
async def ask_rag(request: Request, payload: RAGQuestion) -> dict:
    user = await current_user(request)
    result = generate_answer(payload.question.strip())
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
async def get_rag_sessions(request: Request) -> list[dict]:
    user = await current_user(request)
    return store.list_chat_sessions(user["username"])


@router.get("/sessions/{session_id}")
async def get_rag_session(request: Request, session_id: str) -> dict:
    user = await current_user(request)
    session = store.get_chat_session(user["username"], session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.")
    return session


@router.post("/feedback")
async def provide_rag_feedback(request: Request, payload: RAGFeedback) -> dict[str, str]:
    user = await current_user(request)
    if not store.set_chat_feedback(user["username"], payload.message_id, payload.feedback):
        raise HTTPException(status_code=404, detail="Không tìm thấy câu trả lời để đánh giá.")
    return {"message": "Đã ghi nhận phản hồi."}
