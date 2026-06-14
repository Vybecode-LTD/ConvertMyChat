"""Conversation cache — avoids re-scraping the same share link."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConversationCache(Base):
    __tablename__ = "conversation_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url_hash: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    share_url: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
