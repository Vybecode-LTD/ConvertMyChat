"""Extract and export Gemini conversations.

Works for anonymous AND logged-in users. If logged in, auto-saves to history.
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import InvalidShareLink, ExtractionError
from app.models.schemas import (
    ExtractRequest, ExtractResponse, ExportRequest, ExportFormat, ConversationData,
    ExtractResponseV2, EmbeddedContentItem, BundleExportRequest,
)
from app.models.user import User
from app.models.export_history import ExportHistory
from app.services.scraper import validate_share_url, scrape_share_page
from app.services.parser import parse_html_to_conversation
from app.services.doc_generator import generate_docx
from app.services.pdf_generator import generate_pdf
from app.services.csv_generator import generate_csv_bytes
from app.services.md_generator import generate_markdown_bytes
from app.services.content_extractor import extract_embedded_content, ContentType
from app.services.bundle_generator import generate_bundle
from app.utils.cache import get_cached, set_cached
from app.middleware.auth import get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter()

CONTENT_TYPES = {
    ExportFormat.PDF: "application/pdf",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ExportFormat.CSV: "text/csv",
    ExportFormat.MARKDOWN: "text/markdown",
}
EXTENSIONS = {ExportFormat.PDF: "pdf", ExportFormat.DOCX: "docx",
              ExportFormat.CSV: "csv", ExportFormat.MARKDOWN: "md"}


def _filename(title: str, fmt: ExportFormat) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip().replace(" ", "_")[:50]
    return f"{safe or 'gemini_conversation'}_{datetime.utcnow().strftime('%Y%m%d')}.{EXTENSIONS[fmt]}"


@router.post("/extract", response_model=ExtractResponse)
async def extract(body: ExtractRequest, db: AsyncSession = Depends(get_db)):
    url = body.url.strip()
    if not validate_share_url(url):
        raise InvalidShareLink()

    cached = await get_cached(db, url)
    if cached:
        return ExtractResponse(success=True, conversation=cached, cached=True)

    try:
        html, raw = await scrape_share_page(url)
    except Exception as e:
        raise ExtractionError(str(e))

    convo = parse_html_to_conversation(html, raw, url)
    if not convo.messages:
        raise ExtractionError("No messages found — link may be invalid or DOM changed.")

    await set_cached(db, url, convo)
    return ExtractResponse(success=True, conversation=convo, cached=False)


@router.post("/export")
async def export(
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    convo, fmt = body.conversation, body.format

    generators = {
        ExportFormat.DOCX: generate_docx,
        ExportFormat.PDF: generate_pdf,
        ExportFormat.CSV: generate_csv_bytes,
        ExportFormat.MARKDOWN: generate_markdown_bytes,
    }
    file_bytes = await asyncio.to_thread(generators[fmt], convo)

    # Auto-save to history if user is logged in
    if user:
        entry = ExportHistory(
            user_id=user.id,
            share_url=convo.share_url,
            title=convo.title,
            conversation_data=convo.model_dump(mode="json"),
            message_count=convo.message_count,
            last_export_format=fmt.value,
        )
        db.add(entry)
        await db.commit()

    filename = _filename(convo.title, fmt)
    return Response(
        content=file_bytes, media_type=CONTENT_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "X-Filename": filename},
    )


@router.post("/extract-v2", response_model=ExtractResponseV2)
async def extract_v2(body: ExtractRequest, db: AsyncSession = Depends(get_db)):
    """Extract conversation AND detect embedded content (tables, JSON, code).

    Returns the conversation data plus a summary of embedded content found,
    so the frontend can show toggle options before export.
    """
    url = body.url.strip()
    if not validate_share_url(url):
        raise InvalidShareLink()

    cached = await get_cached(db, url)
    if cached:
        convo = cached
        is_cached = True
    else:
        try:
            html, raw = await scrape_share_page(url)
        except Exception as e:
            raise ExtractionError(str(e))

        convo = parse_html_to_conversation(html, raw, url)
        if not convo.messages:
            raise ExtractionError("No messages found.")

        await set_cached(db, url, convo)
        is_cached = False

    # Detect embedded content
    embedded = extract_embedded_content(convo.messages)

    # Build response items (without full raw text — just metadata + preview)
    items = []
    for ec in embedded:
        preview = ec.raw_text[:200] if isinstance(ec.raw_text, str) else str(ec.parsed_data)[:200]
        items.append(EmbeddedContentItem(
            content_type=ec.content_type.value,
            suggested_filename=ec.suggested_filename,
            language=ec.language,
            row_count=ec.row_count,
            column_count=ec.column_count,
            message_index=ec.message_index,
            message_role=ec.message_role,
            preview=preview,
        ))

    summary = {
        "tables": sum(1 for e in embedded if e.content_type == ContentType.TABLE),
        "json": sum(1 for e in embedded if e.content_type == ContentType.JSON),
        "code": sum(1 for e in embedded if e.content_type == ContentType.CODE),
        "total": len(embedded),
    }

    return ExtractResponseV2(
        success=True,
        conversation=convo,
        embedded_content=items,
        content_summary=summary,
        cached=is_cached,
    )


@router.post("/export-bundle")
async def export_bundle(
    body: BundleExportRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """Export conversation as a ZIP bundle with main document + embedded content files.

    The bundle contains:
    - The main conversation document (PDF/DOCX/CSV/MD)
    - tables/ folder with CSVs (if include_tables=True)
    - json/ folder with formatted JSON files (if include_json=True)
    - code/ folder with source files (if include_code=True)
    - MANIFEST.md listing everything in the bundle
    """
    convo = body.conversation

    try:
        embedded = extract_embedded_content(convo.messages)
        bundle_bytes = await generate_bundle(
            conversation=convo,
            main_format=body.format,
            embedded_content=embedded,
            include_tables=body.include_tables,
            include_json=body.include_json,
            include_code=body.include_code,
        )
    except Exception as e:
        logger.exception("Bundle export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Bundle generation failed: {e}")

    # Auto-save to history if logged in
    if user:
        entry = ExportHistory(
            user_id=user.id,
            share_url=convo.share_url,
            title=convo.title,
            conversation_data=convo.model_dump(mode="json"),
            message_count=convo.message_count,
            last_export_format=f"bundle_{body.format.value}",
        )
        db.add(entry)
        await db.commit()

    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in convo.title).strip().replace(" ", "_")[:40]
    filename = f"{safe_title or 'gemini_export'}_bundle.zip"

    return Response(
        content=bundle_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "X-Filename": filename},
    )
