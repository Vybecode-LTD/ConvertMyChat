"""ConversationShare — stores conversations for public pretty-view pages."""

import random
import string
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _make_slug(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


class ConversationShare(Base):
    __tablename__ = "conversation_shares"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_make_slug)
    share_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="Conversation")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    conversation_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<ConversationShare {self.id}>"
