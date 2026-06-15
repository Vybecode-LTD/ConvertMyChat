"""Public share pages — store a conversation and get a short URL for the pretty view."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation_share import ConversationShare, _make_slug
from app.models.schemas import ConversationData, ShareCreateRequest, ShareResponse

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_URL = "https://convertmy.chat"


@router.post("/share", response_model=ShareResponse)
async def create_share(body: ShareCreateRequest, db: AsyncSession = Depends(get_db)):
    """Store a conversation and return a short-link ID for the pretty view."""
    convo = body.conversation

    # Generate a unique slug
    slug = _make_slug()
    for _ in range(5):
        existing = await db.get(ConversationShare, slug)
        if not existing:
            break
        slug = _make_slug()

    share = ConversationShare(
        id=slug,
        share_url=convo.share_url,
        title=convo.title,
        message_count=convo.message_count,
        conversation_data=convo.model_dump(mode="json"),
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    view_url = f"{BASE_URL}/v/{share.id}"
    return ShareResponse(
        id=share.id,
        share_url=share.share_url,
        title=share.title,
        message_count=share.message_count,
        created_at=share.created_at,
        view_url=view_url,
    )


@router.get("/share/{share_id}")
async def get_share(share_id: str, db: AsyncSession = Depends(get_db)):
    """Return the stored conversation data for a share ID."""
    share = await db.get(ConversationShare, share_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or expired")
    return {
        "id": share.id,
        "title": share.title,
        "message_count": share.message_count,
        "created_at": share.created_at,
        "conversation": share.conversation_data,
    }
