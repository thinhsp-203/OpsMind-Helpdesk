from __future__ import annotations

import csv
import io
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app import store
from app.dependencies import current_user, require_staff

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
async def analytics(request: Request) -> dict:
    user = await current_user(request)
    require_staff(user)
    return store.get_analytics()


@router.get("/agents/me")
async def agent_analytics(request: Request) -> dict:
    user = await current_user(request)
    require_staff(user)
    return store.get_agent_analytics(user["username"])


@router.get("/export")
async def export_analytics(request: Request) -> StreamingResponse:
    user = await current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới được xuất báo cáo.")
    tickets = store.list_tickets("", "admin")
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "ticket_id",
            "title",
            "requester",
            "assignee",
            "category",
            "priority",
            "status",
            "created_at",
            "sla_deadline",
            "rating",
        ]
    )

    def safe_csv_value(value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.lstrip().startswith(("=", "+", "-", "@")):
            return f"'{value}"
        return value

    for ticket in tickets:
        writer.writerow(
            [
                safe_csv_value(value)
                for value in [
                    ticket["id"],
                    ticket["title"],
                    ticket["requester"],
                    ticket["assignee"] or "",
                    ticket["category"],
                    ticket["priority"],
                    ticket["status"],
                    ticket["created_at"],
                    ticket["sla_deadline"],
                    ticket["rating"] or "",
                ]
            ]
        )
    content = "\ufeff" + stream.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="helpdesk-report.csv"'},
    )
