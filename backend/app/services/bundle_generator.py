"""Generate a ZIP bundle containing the main export + extracted content files.

Structure inside the zip:
  conversation_export/
  ├── conversation_20260614.pdf    (main doc)
  ├── tables/
  │   ├── table_1.csv
  │   └── table_2.csv
  ├── json/
  │   ├── data_1.json
  │   └── data_2.json
  └── code/
      ├── snippet_1.py
      └── snippet_2.sql
"""

import io
import zipfile
import asyncio
from datetime import datetime

from app.models.schemas import ConversationData, ExportFormat
from app.services.content_extractor import (
    EmbeddedContent, ContentType,
    table_to_csv_bytes, json_to_bytes, code_to_bytes,
)
from app.services.doc_generator import generate_docx
from app.services.pdf_generator import generate_pdf
from app.services.csv_generator import generate_csv_bytes
from app.services.md_generator import generate_markdown_bytes
from app.services.html_generator import generate_html_bytes


GENERATORS = {
    ExportFormat.DOCX: generate_docx,
    ExportFormat.PDF: generate_pdf,
    ExportFormat.CSV: generate_csv_bytes,
    ExportFormat.MARKDOWN: generate_markdown_bytes,
    ExportFormat.HTML: generate_html_bytes,
}

EXTENSIONS = {
    ExportFormat.PDF: "pdf",
    ExportFormat.DOCX: "docx",
    ExportFormat.CSV: "csv",
    ExportFormat.MARKDOWN: "md",
    ExportFormat.HTML: "html",
}

SUBFOLDERS = {
    ContentType.TABLE: "tables",
    ContentType.JSON: "json",
    ContentType.CODE: "code",
}


def _safe_title(title: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
    return safe.strip().replace(" ", "_")[:40] or "gemini_conversation"


def _algorithm_md(item: EmbeddedContent) -> bytes:
    """Wrap an algorithm code block as a Markdown file with a fenced block."""
    lang = item.language or ""
    header = f"## {item.suggested_filename.replace('.', '_')}\n\n"
    body = f"```{lang}\n{item.raw_text}\n```\n"
    return (header + body).encode("utf-8")


async def generate_bundle(
    conversation: ConversationData,
    main_format: ExportFormat,
    embedded_content: list[EmbeddedContent],
    include_tables: bool = True,
    include_json: bool = True,
    include_code: bool = True,
) -> bytes:
    """Generate a ZIP file containing the main export + selected embedded content.

    Args:
        conversation: The full conversation data
        main_format: Format for the main document (pdf/docx/csv/md)
        embedded_content: List of extracted embedded content
        include_tables: Whether to include table CSV files
        include_json: Whether to include JSON files
        include_code: Whether to include code snippet files

    Returns:
        ZIP file as bytes
    """
    # Generate main document (CPU-bound)
    generator = GENERATORS[main_format]
    main_bytes = await asyncio.to_thread(generator, conversation)

    # Build the zip
    zip_buffer = io.BytesIO()
    title = _safe_title(conversation.title)
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    folder_name = f"{title}_{timestamp}"

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Main document
        main_ext = EXTENSIONS[main_format]
        main_filename = f"{folder_name}/{title}.{main_ext}"
        zf.writestr(main_filename, main_bytes)

        # Embedded content files
        algo_items = []
        for item in embedded_content:
            # Check if this type is included
            if item.content_type == ContentType.TABLE and not include_tables:
                continue
            if item.content_type == ContentType.JSON and not include_json:
                continue
            if item.content_type == ContentType.CODE and not include_code:
                continue

            if item.content_type == ContentType.CODE and item.is_algorithm:
                # Algorithm blocks go to functions/ as .md files
                algo_items.append(item)
                md_name = item.suggested_filename.rsplit(".", 1)[0] + ".md"
                filepath = f"{folder_name}/functions/{md_name}"
                zf.writestr(filepath, _algorithm_md(item))
                continue

            subfolder = SUBFOLDERS[item.content_type]
            filepath = f"{folder_name}/{subfolder}/{item.suggested_filename}"

            if item.content_type == ContentType.TABLE:
                file_bytes = table_to_csv_bytes(item.parsed_data)
            elif item.content_type == ContentType.JSON:
                file_bytes = json_to_bytes(item.parsed_data)
            elif item.content_type == ContentType.CODE:
                file_bytes = code_to_bytes(item.parsed_data)
            else:
                continue

            zf.writestr(filepath, file_bytes)

        # Add a manifest file listing what's in the bundle
        manifest_lines = [
            f"# {conversation.title}",
            f"Source: {conversation.share_url}",
            f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"Messages: {conversation.message_count}",
            f"Main document: {title}.{main_ext}",
            "",
        ]

        tables = [i for i in embedded_content if i.content_type == ContentType.TABLE and include_tables]
        jsons = [i for i in embedded_content if i.content_type == ContentType.JSON and include_json]
        codes = [i for i in embedded_content if i.content_type == ContentType.CODE and include_code and not i.is_algorithm]
        algos = [i for i in embedded_content if i.content_type == ContentType.CODE and include_code and i.is_algorithm]

        if tables:
            manifest_lines.append(f"Tables ({len(tables)}):")
            for t in tables:
                manifest_lines.append(f"  - tables/{t.suggested_filename} ({t.row_count} rows x {t.column_count} cols)")

        if jsons:
            manifest_lines.append(f"JSON blocks ({len(jsons)}):")
            for j in jsons:
                manifest_lines.append(f"  - json/{j.suggested_filename}")

        if codes:
            manifest_lines.append(f"Code snippets ({len(codes)}):")
            for c in codes:
                manifest_lines.append(f"  - code/{c.suggested_filename} ({c.language})")

        if algos:
            manifest_lines.append(f"Functions/algorithms ({len(algos)}):")
            for a in algos:
                md_name = a.suggested_filename.rsplit(".", 1)[0] + ".md"
                manifest_lines.append(f"  - functions/{md_name} ({a.language})")

        zf.writestr(f"{folder_name}/MANIFEST.md", "\n".join(manifest_lines))

    zip_buffer.seek(0)
    return zip_buffer.read()
