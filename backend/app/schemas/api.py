from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if any(ord(character) < 32 for character in cleaned):
            raise ValueError("Display name contains invalid control characters")
        return cleaned

    @field_validator("password")
    @classmethod
    def reject_common_passwords(cls, value: str) -> str:
        common = {"password123", "1234567890", "qwerty12345", "letmein1234"}
        if value.lower() in common:
            raise ValueError("Choose a less common password")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserView(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: datetime


class TokenView(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView


class DocumentView(BaseModel):
    id: str
    filename: str
    size_bytes: int
    page_count: int | None
    status: str
    error_message: str | None
    progress: int = 0
    created_at: datetime


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[str] = Field(default_factory=list, max_length=50)


class FeedbackRequest(BaseModel):
    answer_id: str
    helpful: bool
    comment: str | None = Field(default=None, max_length=500)

