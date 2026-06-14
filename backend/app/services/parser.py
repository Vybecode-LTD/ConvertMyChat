"""Parse Gemini share page HTML into structured conversation data.

SELECTOR_DRIFT: all selectors are constants at the top — update only these.
Multi-strategy: known selectors → heuristic text → raw fallback.
"""

import logging
import re
from datetime import datetime

from app.models.schemas import ConversationData, ConversationMessage

logger = logging.getLogger(__name__)

# === SELECTORS — Update when Google changes the DOM ===
MESSAGE_BLOCK_SELECTORS = [
    ".conversation-turn", "[data-message-id]",
    "message-content", ".query-content, .response-content",
]
TITLE_SELECTORS = ["h1", ".conversation-title", "title"]


def _html_to_markdown(el) -> str:
    """Convert a BeautifulSoup element's inner HTML to clean Markdown."""
    try:
        from markdownify import markdownify
        inner = el.decode_contents()
        if not inner.strip():
            return el.get_text(separator="\n", strip=True)
        md_text = markdownify(inner, heading_style="ATX", bullets="-", strip=["img", "script", "style"])
        md_text = re.sub(r"\n{3,}", "\n\n", md_text)
        return md_text.strip() or el.get_text(separator="\n", strip=True)
    except Exception:
        return el.get_text(separator="\n", strip=True)


def _extract_code_blocks(text: str) -> tuple[list[dict], bool]:
    matches = re.findall(r"```(\w*)\n(.*?)```", text, re.DOTALL)
    blocks = [{"language": lang or "text", "code": code.strip()} for lang, code in matches]
    return blocks, len(blocks) > 0


def _detect_role(text: str, prev_role: str | None) -> str:
    low = text.strip().lower()
    if any(low.startswith(p) for p in ["you said:", "user:", "prompt:"]):
        return "user"
    if any(low.startswith(p) for p in ["gemini:", "model:", "response:"]):
        return "model"
    if prev_role == "user":
        return "model"
    if prev_role == "model":
        return "user"
    return "user"


def parse_html_to_conversation(html: str, raw_text: str, share_url: str) -> ConversationData:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return _text_fallback(raw_text, share_url)

    messages, title = [], "Gemini Conversation"

    for sel in TITLE_SELECTORS:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True).lower() not in ["gemini", "google gemini", ""]:
            title = el.get_text(strip=True)
            break

    # Strategy 1: known DOM selectors
    elems = []
    for sel in MESSAGE_BLOCK_SELECTORS:
        elems = soup.select(sel)
        if elems:
            break

    if elems:
        prev = None
        for idx, el in enumerate(elems):
            text = _html_to_markdown(el)
            if not text:
                continue
            classes = " ".join(el.get("class", []))
            role = el.get("data-role") or (
                "user" if any(k in classes for k in ["user", "query", "prompt"]) else
                "model" if any(k in classes for k in ["model", "response", "gemini"]) else
                _detect_role(text, prev)
            )
            cbs, has = _extract_code_blocks(text)
            messages.append(ConversationMessage(
                role=role, content=text, index=idx,
                has_code_blocks=has, code_blocks=cbs,
            ))
            prev = role
    else:
        # Strategy 2: heuristic paragraph splitting
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if len(p.strip()) > 20]
        prev = None
        for idx, para in enumerate(paragraphs):
            role = _detect_role(para, prev)
            cbs, has = _extract_code_blocks(para)
            messages.append(ConversationMessage(
                role=role, content=para, index=idx,
                has_code_blocks=has, code_blocks=cbs,
            ))
            prev = role

    if not messages:
        return _text_fallback(raw_text, share_url)

    return ConversationData(
        title=title, share_url=share_url,
        extracted_at=datetime.utcnow(),
        message_count=len(messages), messages=messages,
    )


def _text_fallback(raw_text: str, share_url: str) -> ConversationData:
    lines = [l.strip() for l in raw_text.split("\n")
             if len(l.strip()) > 5
             and not any(p in l.lower() for p in ["sign in", "google", "share", "copy", "menu"])]
    content = "\n".join(lines) or raw_text
    return ConversationData(
        title="Gemini Conversation", share_url=share_url,
        extracted_at=datetime.utcnow(), message_count=1,
        messages=[ConversationMessage(role="model", content=content, index=0,
                                      has_code_blocks=False, code_blocks=[])],
        metadata={"parse_method": "raw_text_fallback"},
    )
