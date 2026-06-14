"""DOCX (Word) export generator."""

import io
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

from app.models.schemas import ConversationData


def generate_docx(conversation: ConversationData) -> bytes:
    doc = Document()

    # Title
    doc.add_heading(conversation.title, level=1)

    meta = doc.add_paragraph()
    r = meta.add_run(
        f"Source: {conversation.share_url}\n"
        f"Extracted: {conversation.extracted_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Messages: {conversation.message_count}"
    )
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    r.font.italic = True

    doc.add_paragraph("─" * 60)

    for msg in conversation.messages:
        label = "👤 User" if msg.role == "user" else "🤖 Gemini"
        doc.add_heading(label, level=3)
        doc.add_paragraph(msg.content)

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run("Exported by ConvertMyChat")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
