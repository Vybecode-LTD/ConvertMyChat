"""PDF export generator using fpdf2 with Markdown structure support."""

import io
import re
from fpdf import FPDF

from app.models.schemas import ConversationData


class ConvoPDF(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self._title = title

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, self._title[:80], align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  ConvertMyChat", align="C")


def _sanitize(text: str) -> str:
    replacements = {
        "‘": "'", "’": "'",   # curly single quotes
        "“": '"', "”": '"',   # curly double quotes
        "–": "-", "—": "--",  # en/em dash
        "…": "...",                # ellipsis
        " ": " ",                  # non-breaking space
        "•": "*", "⁃": "*", "●": "*",  # bullet variants
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # fpdf2 built-in fonts are Latin-1 — drop anything outside that range
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _strip_inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def _render_table_pdf(pdf: FPDF, table_lines: list[str]):
    rows = []
    for line in table_lines:
        if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if cells:
            rows.append(cells)
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / ncols
    for r_idx, row in enumerate(rows):
        is_hdr = r_idx == 0
        if is_hdr:
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font("Helvetica", "B", 8)
        else:
            pdf.set_fill_color(255, 255, 255)
            pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(30, 30, 30)
        for c_idx in range(ncols):
            cell_txt = _sanitize(row[c_idx][:50]) if c_idx < len(row) else ""
            pdf.cell(col_w, 6, cell_txt, border=1, fill=is_hdr)
        pdf.ln()
    pdf.set_x(pdf.l_margin)
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)


def _reset_x(pdf: FPDF):
    pdf.set_x(pdf.l_margin)


def _render_markdown_pdf(pdf: FPDF, text: str):
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            pdf.set_font("Courier", "", 8)
            pdf.set_fill_color(245, 245, 245)
            pdf.set_text_color(50, 50, 50)
            for cl in code_lines:
                _reset_x(pdf)
                pdf.multi_cell(0, 4.5, _sanitize(cl), fill=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 40)
            i += 1
            continue

        # Markdown table
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            _render_table_pdf(pdf, table_lines)
            _reset_x(pdf)
            continue

        # ATX heading
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            sizes = {1: 16, 2: 14, 3: 12, 4: 11, 5: 10, 6: 10}
            pdf.set_font("Helvetica", "B", sizes.get(level, 11))
            pdf.set_text_color(30, 30, 30)
            _reset_x(pdf)
            pdf.multi_cell(0, 7, _sanitize(_strip_inline_md(m.group(2))))
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 40)
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}$", line.strip()):
            pdf.set_draw_color(200, 200, 200)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(4)
            i += 1
            continue

        # Bullet list
        m = re.match(r"^[-*+]\s+(.+)$", line)
        if m:
            pdf.set_font("Helvetica", "", 10)
            _reset_x(pdf)
            pdf.multi_cell(0, 5, _sanitize("  * " + _strip_inline_md(m.group(1))))
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            pdf.set_font("Helvetica", "", 10)
            _reset_x(pdf)
            pdf.multi_cell(0, 5, _sanitize(f"  {m.group(1)}. " + _strip_inline_md(m.group(2))))
            i += 1
            continue

        # Blank line
        if not line.strip():
            pdf.ln(3)
            i += 1
            continue

        # Regular paragraph
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        _reset_x(pdf)
        pdf.multi_cell(0, 5, _sanitize(_strip_inline_md(line)))
        i += 1


def generate_pdf(conversation: ConversationData) -> bytes:
    pdf = ConvoPDF(conversation.title[:80])
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 12, _sanitize(conversation.title))
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, _sanitize(f"Source: {conversation.share_url}"), ln=True)
    pdf.cell(
        0, 5,
        _sanitize(
            f"Extracted: {conversation.extracted_at.strftime('%Y-%m-%d %H:%M UTC')} - "
            f"{conversation.message_count} messages"
        ),
        ln=True,
    )
    pdf.ln(8)

    platform = str((conversation.metadata or {}).get("platform", "gemini"))
    ai = {"chatgpt": "ChatGPT", "gemini": "Gemini"}.get(platform, "Gemini")

    for msg in conversation.messages:
        if msg.role == "user":
            pdf.set_text_color(30, 100, 180)
        else:
            pdf.set_text_color(232, 68, 10)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "User" if msg.role == "user" else ai, ln=True)

        pdf.set_text_color(40, 40, 40)
        _render_markdown_pdf(pdf, msg.content)
        pdf.ln(4)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.read()
