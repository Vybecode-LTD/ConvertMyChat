"""Export history for logged-in users."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ExtractionError
from app.models.user import User
from app.models.export_history import ExportHistory
from app.models.schemas import (
    HistoryItem, HistoryListResponse, ExportFormat,
    ConversationData,
)
from app.services.doc_generator import generate_docx
from app.services.pdf_generator import generate_pdf
from app.services.csv_generator import generate_csv_bytes
from app.services.md_generator import generate_markdown_bytes
from app.middleware.auth import get_current_user_required

router = APIRouter()


@router.get("/", response_model=HistoryListResponse)
async def list_history(
    skip: int = 0, limit: int = 20,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """List user's export history."""
    count_q = select(func.count()).select_from(ExportHistory).where(
        ExportHistory.user_id == user.id
    )
    total = (await db.execute(count_q)).scalar()

    q = (select(ExportHistory)
         .where(ExportHistory.user_id == user.id)
         .order_by(desc(ExportHistory.created_at))
         .offset(skip).limit(limit))
    rows = (await db.execute(q)).scalars().all()

    return HistoryListResponse(
        items=[HistoryItem.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/{item_id}/reexport")
async def reexport(
    item_id: UUID, format: ExportFormat,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """Re-export a saved conversation in a different format."""
    result = await db.execute(
        select(ExportHistory).where(
            ExportHistory.id == item_id, ExportHistory.user_id == user.id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise ExtractionError("History item not found")

    convo = ConversationData.model_validate(entry.conversation_data)

    generators = {
        ExportFormat.DOCX: generate_docx, ExportFormat.PDF: generate_pdf,
        ExportFormat.CSV: generate_csv_bytes, ExportFormat.MARKDOWN: generate_markdown_bytes,
    }
    file_bytes = await asyncio.to_thread(generators[format], convo)

    entry.last_export_format = format.value
    await db.commit()

    ct = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "csv": "text/csv", "markdown": "text/markdown"}
    ext = {"pdf": "pdf", "docx": "docx", "csv": "csv", "markdown": "md"}

    fn = f"{entry.title[:50].replace(' ', '_')}_{format.value}.{ext[format.value]}"
    return Response(content=file_bytes, media_type=ct[format.value],
                    headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@router.delete("/{item_id}")
async def delete_history_item(
    item_id: UUID,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """Delete a history item."""
    result = await db.execute(
        select(ExportHistory).where(
            ExportHistory.id == item_id, ExportHistory.user_id == user.id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise ExtractionError("History item not found")

    await db.delete(entry)
    await db.commit()
    return {"deleted": True}
