"""Pydantic models for API requests and responses."""

from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


# --- Export ---

class ExportFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"


class ConversationMessage(BaseModel):
    role: str = Field(description="'user' or 'model'")
    content: str
    index: int
    has_code_blocks: bool = False
    code_blocks: list[dict] = Field(default_factory=list)


class ConversationData(BaseModel):
    title: str = "Gemini Conversation"
    share_url: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    messages: list[ConversationMessage] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ExtractRequest(BaseModel):
    url: str


class ExtractResponse(BaseModel):
    success: bool
    conversation: ConversationData | None = None
    error: str | None = None
    cached: bool = False


class ExportRequest(BaseModel):
    conversation: ConversationData
    format: ExportFormat


# --- Auth ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# --- User ---

class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    avatar_url: str | None
    auth_provider: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None


# --- Admin ---

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None
    is_admin: bool = False


class AdminUserUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None


class AdminResetPassword(BaseModel):
    new_password: str = Field(min_length=8)


class AdminUserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


# --- History ---

# --- Embedded Content ---

class ContentTypeEnum(str, Enum):
    TABLE = "table"
    JSON = "json"
    CODE = "code"


class EmbeddedContentItem(BaseModel):
    content_type: ContentTypeEnum
    suggested_filename: str
    language: str | None = None
    row_count: int | None = None
    column_count: int | None = None
    message_index: int
    message_role: str = "model"
    preview: str = Field(default="", description="First 200 chars of content")


class ExtractResponseV2(BaseModel):
    success: bool
    conversation: ConversationData | None = None
    embedded_content: list[EmbeddedContentItem] = Field(default_factory=list)
    content_summary: dict = Field(default_factory=dict, description="Count by type: {tables: N, json: N, code: N}")
    error: str | None = None
    cached: bool = False


class BundleExportRequest(BaseModel):
    conversation: ConversationData
    format: ExportFormat
    include_tables: bool = True
    include_json: bool = True
    include_code: bool = True


# --- History ---

class HistoryItem(BaseModel):
    id: UUID
    share_url: str
    title: str
    message_count: int
    last_export_format: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int


# --- Share ---

class ShareCreateRequest(BaseModel):
    conversation: ConversationData


class ShareResponse(BaseModel):
    id: str
    share_url: str
    title: str
    message_count: int
    created_at: datetime
    view_url: str


# --- Health ---

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    playwright_ready: bool = False
