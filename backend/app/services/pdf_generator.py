"""PDF export generator using fpdf2."""

import io
from fpdf import FPDF
from app.models.schemas import ConversationData


class ConvoPDF(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self._title = title

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, self._title, align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  ConvertMyChat", align="C")


def _sanitize(text: str) -> str:
    for old, new in {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                      "\u2013": "-", "\u2014": "--", "\u2026": "...", "\u00a0": " "}.items():
        text = text.replace(old, new)
    return "".join(ch for ch in text if ord(ch) < 0x10000)


def generate_pdf(conversation: ConversationData) -> bytes:
    pdf = ConvoPDF(conversation.title)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 15, _sanitize(conversation.title), ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"Source: {conversation.share_url}", ln=True)
    pdf.cell(0, 5, f"Extracted: {conversation.extracted_at.strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.cell(0, 5, f"Messages: {conversation.message_count}", ln=True)
    pdf.ln(8)

    for msg in conversation.messages:
        pdf.set_font("Helvetica", "B", 11)
        if msg.role == "user":
            pdf.set_text_color(30, 100, 180)
            pdf.cell(0, 8, "User", ln=True)
        else:
            pdf.set_text_color(180, 60, 30)
            pdf.cell(0, 8, "Gemini", ln=True)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5, _sanitize(msg.content))
        pdf.ln(6)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.read()
