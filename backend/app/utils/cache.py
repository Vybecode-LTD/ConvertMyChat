"""Conversation cache using SQLAlchemy async (Railway Postgres)."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.schemas import ConversationData
from app.models.conversation_cache import ConversationCache

logger = logging.getLogger(__name__)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:32]


async def get_cached(db: AsyncSession, url: str) -> ConversationData | None:
    url_key = _url_hash(url)
    result = await db.execute(
        select(ConversationCache).where(ConversationCache.url_hash == url_key)
    )
    row = result.scalar_one_or_none()
    if not row:
        return None

    if datetime.now(timezone.utc) - row.cached_at.replace(tzinfo=timezone.utc) > timedelta(
        seconds=settings.cache_ttl_seconds
    ):
        return None

    return ConversationData.model_validate(row.conversation_data)


async def set_cached(db: AsyncSession, url: str, convo: ConversationData) -> None:
    url_key = _url_hash(url)
    result = await db.execute(
        select(ConversationCache).where(ConversationCache.url_hash == url_key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.conversation_data = convo.model_dump(mode="json")
        existing.message_count = convo.message_count
        existing.cached_at = datetime.now(timezone.utc)
    else:
        entry = ConversationCache(
            url_hash=url_key,
            share_url=url,
            conversation_data=convo.model_dump(mode="json"),
            message_count=convo.message_count,
        )
        db.add(entry)

    await db.commit()
