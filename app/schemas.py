from __future__ import annotations

import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Role = Literal["user", "agent", "admin"]


class UserDeletion(BaseModel):
    confirm_username: str = Field(min_length=1, max_length=120)

TicketStatus = Literal[
    "new", "in_progress", "pending_waiting_user", "resolved", "closed", "escalated"
]
Priority = Literal["low", "medium", "high", "urgent"]

# Bảng ánh xạ chuẩn hóa mức độ ưu tiên sự cố CNTT theo chuẩn SLA:
# - P1 · Khẩn cấp (urgent): Thời hạn phản hồi & xử lý tối đa 2 giờ
# - P2 · Cao (high): Thời hạn phản hồi & xử lý tối đa 8 giờ
# - P3 · Tiêu chuẩn/Trung bình (medium): Thời hạn phản hồi & xử lý tối đa 24 giờ
# - P4 · Thấp (low): Thời hạn phản hồi & xử lý tối đa 48 giờ
PRIORITY_SLA_MAPPING: dict[str, dict[str, Any]] = {
    "urgent": {"code": "P1", "label": "Khẩn cấp", "sla_hours": 2, "color": "red"},
    "high": {"code": "P2", "label": "Cao", "sla_hours": 8, "color": "orange"},
    "medium": {"code": "P3", "label": "Tiêu chuẩn", "sla_hours": 24, "color": "yellow"},
    "low": {"code": "P4", "label": "Thấp", "sla_hours": 48, "color": "green"},
}


def _validated_email(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    cleaned = value.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
        raise ValueError("Địa chỉ email không hợp lệ.")
    return cleaned


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(min_length=12, max_length=200)
    role: Role
    full_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    department: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=40)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validated_email(value) or ""


class UserUpdate(BaseModel):
    role: Role | None = None
    full_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    department: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validated_email(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "UserUpdate":
        if not any(
            getattr(self, field_name) is not None for field_name in type(self).model_fields
        ):
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    department: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    current_password: str | None = Field(default=None, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validated_email(value)

    @field_validator("full_name", "department", "phone", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_update_field(self) -> "ProfileUpdate":
        fields = [f for f in type(self).model_fields if f != "current_password"]
        if not any(getattr(self, field_name) is not None for field_name in fields):
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=200)
    force_change: bool = True


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)

    @field_validator("identifier", mode="before")
    @classmethod
    def trim_identifier(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=12, max_length=200)

    @field_validator("token", mode="before")
    @classmethod
    def trim_token(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TicketCreate(BaseModel):
    request_key: str | None = Field(default=None, min_length=16, max_length=64, pattern=r"^[a-zA-Z0-9-]+$")
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(default="general", min_length=2, max_length=50)
    priority: Priority = "medium"

    @field_validator("title", "description", "category", mode="before")
    @classmethod
    def trim_nonempty_fields(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Giá trị không được để trống.")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.lower()


class StatusUpdate(BaseModel):
    status: TicketStatus
    expected_status: TicketStatus | None = None


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    priority: Priority | None = None

    @field_validator("title", "description", "category", mode="before")
    @classmethod
    def trim_nonempty_fields(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Giá trị không được để trống.")
        return normalized

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return value.lower() if value else value

    @model_validator(mode="after")
    def require_update_field(self) -> "TicketUpdate":
        if not any(
            getattr(self, field_name) is not None for field_name in type(self).model_fields
        ):
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class AssignmentUpdate(BaseModel):
    assignee: str = Field(min_length=1, max_length=50)


class CommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=3000)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_comment(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RAGQuestion(BaseModel):
    step_results: dict[str, Literal["not_attempted", "attempted_success", "attempted_failure"]] = Field(default_factory=dict, max_length=3)
    expected_revision: int | None = Field(default=None, ge=0)
    action: Literal["confirm_resolved", "still_failing", "confirm_switch", "continue_incident"] | None = None
    fact_answers: dict[str, str] = Field(default_factory=dict, max_length=3)
    question: str = Field(min_length=3, max_length=2000)
    session_id: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TicketRating(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_optional_comment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class RAGFeedback(BaseModel):
    message_id: int = Field(gt=0)
    feedback: Literal["up", "down"]


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    category: Literal["network", "hardware", "software", "security", "general"]
    tags: str = Field(default="", max_length=200)
    content: str = Field(min_length=10)
    status: Literal["draft", "pending_review", "published"] = "draft"

    @field_validator("title", "content", "tags", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    category: Literal["network", "hardware", "software", "security", "general"] | None = None
    tags: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=10)
    status: Literal["draft", "pending_review", "published", "archived"] | None = None
    change_summary: str | None = Field(default="Cập nhật tài liệu", max_length=300)

    @field_validator("title", "content", "tags", "change_summary", mode="before")
    @classmethod
    def trim_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class KnowledgeReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    feedback: str | None = Field(default=None, max_length=1000)


class NotificationTestRequest(BaseModel):
    channel: Literal["telegram", "email"]
    target_email: str | None = Field(default=None, max_length=254)

class AccountDeleteRequest(BaseModel):
    confirmation: str | None = None
    password: str | None = None


class AccountDeleteResponse(BaseModel):
    message: str
    username: str

