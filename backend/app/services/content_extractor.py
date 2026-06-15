"""Detect and extract embedded structured content from conversation messages.

Extracts three types of embedded content:
1. Markdown tables → CSV or XLSX
2. JSON/YAML snippets → formatted .json files
3. Code blocks → individual source files with proper extensions

Each extracted piece gets a suggested filename and can be exported
as a standalone file alongside the main conversation document.
"""

import csv
import io
import json
import logging
import re
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    TABLE = "table"
    JSON = "json"
    CODE = "code"


class EmbeddedContent(BaseModel):
    """A single piece of extracted embedded content."""
    content_type: ContentType
    raw_text: str = Field(description="Original text as it appeared")
    parsed_data: dict | list | str = Field(description="Parsed/structured data")
    suggested_filename: str
    language: str | None = None  # For code blocks
    is_algorithm: bool = False  # True if the code block looks like a function/algorithm
    row_count: int | None = None  # For tables
    column_count: int | None = None  # For tables
    message_index: int = Field(description="Which message this came from")
    message_role: str = "model"


# === Language → Extension Map ===
LANG_EXTENSIONS = {
    "python": ".py", "py": ".py",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts",
    "jsx": ".jsx", "tsx": ".tsx",
    "html": ".html", "css": ".css",
    "sql": ".sql",
    "bash": ".sh", "shell": ".sh", "sh": ".sh",
    "json": ".json", "yaml": ".yaml", "yml": ".yaml",
    "ruby": ".rb", "go": ".go", "rust": ".rs",
    "java": ".java", "kotlin": ".kt",
    "csharp": ".cs", "c#": ".cs", "cs": ".cs",
    "cpp": ".cpp", "c++": ".cpp", "c": ".c",
    "php": ".php", "swift": ".swift",
    "r": ".r", "matlab": ".m",
    "markdown": ".md", "md": ".md",
    "xml": ".xml", "toml": ".toml",
    "dockerfile": ".dockerfile",
    "graphql": ".graphql", "gql": ".graphql",
    "text": ".txt", "": ".txt",
}


def _detect_tables(text: str, msg_index: int, msg_role: str, counter: list[int]) -> list[EmbeddedContent]:
    """Find Markdown-style pipe-delimited tables in text."""
    results = []

    # Match consecutive lines that start and end with |
    # A table needs at least a header row + separator row + one data row
    table_pattern = re.compile(
        r'((?:^\|.+\|$\n?){3,})',
        re.MULTILINE
    )

    for match in table_pattern.finditer(text):
        table_text = match.group(1).strip()
        lines = [l.strip() for l in table_text.split("\n") if l.strip()]

        if len(lines) < 3:
            continue

        # Parse the table
        rows = []
        for i, line in enumerate(lines):
            # Skip separator rows (|---|---|)
            if re.match(r'^\|[\s\-:|]+\|$', line):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]  # Remove empty first/last from split
            if cells:
                rows.append(cells)

        if len(rows) < 2:  # Need at least header + 1 data row
            continue

        counter[0] += 1
        results.append(EmbeddedContent(
            content_type=ContentType.TABLE,
            raw_text=table_text,
            parsed_data=rows,  # List of lists (first row = headers)
            suggested_filename=f"table_{counter[0]}.csv",
            row_count=len(rows) - 1,  # Exclude header
            column_count=len(rows[0]) if rows else 0,
            message_index=msg_index,
            message_role=msg_role,
        ))

    return results


def _detect_json(text: str, msg_index: int, msg_role: str, counter: list[int]) -> list[EmbeddedContent]:
    """Find JSON snippets — both fenced and standalone."""
    results = []

    # Strategy 1: fenced ```json blocks (already caught as code, but we parse the JSON)
    json_fence_pattern = re.compile(r'```(?:json)\s*\n(.*?)```', re.DOTALL)
    for match in json_fence_pattern.finditer(text):
        raw = match.group(1).strip()
        try:
            parsed = json.loads(raw)
            counter[0] += 1
            results.append(EmbeddedContent(
                content_type=ContentType.JSON,
                raw_text=raw,
                parsed_data=parsed,
                suggested_filename=f"data_{counter[0]}.json",
                language="json",
                message_index=msg_index,
                message_role=msg_role,
            ))
        except json.JSONDecodeError:
            continue

    # Strategy 2: standalone JSON objects/arrays not in fences
    # Look for { ... } or [ ... ] spanning multiple lines
    standalone_pattern = re.compile(r'(?:^|\n)(\{[\s\S]*?\}|\[[\s\S]*?\])(?:\n|$)')
    for match in standalone_pattern.finditer(text):
        raw = match.group(1).strip()
        # Skip if it's inside a code fence (already caught above)
        if f"```" in text[:match.start()].split("\n")[-1:][0] if text[:match.start()].split("\n") else "":
            continue
        if len(raw) < 10:  # Skip trivially small
            continue
        try:
            parsed = json.loads(raw)
            # Only include if it's meaningfully structured (not just {} or [])
            if isinstance(parsed, dict) and len(parsed) > 0:
                counter[0] += 1
                results.append(EmbeddedContent(
                    content_type=ContentType.JSON,
                    raw_text=raw,
                    parsed_data=parsed,
                    suggested_filename=f"data_{counter[0]}.json",
                    language="json",
                    message_index=msg_index,
                    message_role=msg_role,
                ))
            elif isinstance(parsed, list) and len(parsed) > 0:
                counter[0] += 1
                results.append(EmbeddedContent(
                    content_type=ContentType.JSON,
                    raw_text=raw,
                    parsed_data=parsed,
                    suggested_filename=f"data_{counter[0]}.json",
                    language="json",
                    message_index=msg_index,
                    message_role=msg_role,
                ))
        except (json.JSONDecodeError, ValueError):
            continue

    return results


_SCRIPT_LANGS = {"bash", "shell", "sh", "zsh", "cmd", "powershell", "ps1", "text", "txt", ""}
_ALGO_PATTERNS = re.compile(
    r'\b(def |function |func |class |public |private |protected |static |async def |'
    r'sub |procedure |algorithm |return |lambda |=>|->)\b',
    re.IGNORECASE,
)


def _is_algorithm(code: str, lang: str) -> bool:
    """Return True if this code block looks like a function, class, or algorithm."""
    if lang in _SCRIPT_LANGS:
        return False
    lines = [l for l in code.split("\n") if l.strip()]
    if len(lines) < 4:
        return False
    return bool(_ALGO_PATTERNS.search(code))


def _detect_code(text: str, msg_index: int, msg_role: str, counter: list[int]) -> list[EmbeddedContent]:
    """Find fenced code blocks (excluding JSON, which is handled separately)."""
    results = []

    code_pattern = re.compile(r'```(\w*)\s*\n(.*?)```', re.DOTALL)
    for match in code_pattern.finditer(text):
        lang = match.group(1).lower().strip()
        code = match.group(2).strip()

        if lang == "json":  # Handled by _detect_json
            continue
        if len(code) < 5:  # Skip trivially small
            continue

        counter[0] += 1
        ext = LANG_EXTENSIONS.get(lang, ".txt")
        if lang:
            filename = f"snippet_{counter[0]}{ext}"
        else:
            filename = f"snippet_{counter[0]}.txt"

        algo = _is_algorithm(code, lang)

        results.append(EmbeddedContent(
            content_type=ContentType.CODE,
            raw_text=code,
            parsed_data=code,
            suggested_filename=filename,
            language=lang or "text",
            is_algorithm=algo,
            message_index=msg_index,
            message_role=msg_role,
        ))

    return results


def extract_embedded_content(messages: list) -> list[EmbeddedContent]:
    """Extract all embedded content from a list of conversation messages.

    Args:
        messages: List of ConversationMessage objects

    Returns:
        List of EmbeddedContent objects with suggested filenames
    """
    all_content = []
    table_counter = [0]
    json_counter = [0]
    code_counter = [0]

    for msg in messages:
        text = msg.content
        idx = msg.index
        role = msg.role

        all_content.extend(_detect_tables(text, idx, role, table_counter))
        all_content.extend(_detect_json(text, idx, role, json_counter))
        all_content.extend(_detect_code(text, idx, role, code_counter))

    logger.info(
        f"Extracted {table_counter[0]} tables, {json_counter[0]} JSON blocks, "
        f"{code_counter[0]} code snippets"
    )
    return all_content


def table_to_csv_bytes(parsed_data: list[list]) -> bytes:
    """Convert parsed table data (list of lists) to CSV bytes."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    for row in parsed_data:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def json_to_bytes(parsed_data: dict | list) -> bytes:
    """Pretty-print JSON data to bytes."""
    return json.dumps(parsed_data, indent=2, ensure_ascii=False).encode("utf-8")


def code_to_bytes(code: str) -> bytes:
    """Encode code text to bytes."""
    return code.encode("utf-8")
