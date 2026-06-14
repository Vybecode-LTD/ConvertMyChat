"""Multi-platform conversation parser.

Detects the platform from the share URL and routes to the appropriate parser.
"""

import json
import logging
import re
from datetime import datetime

from app.models.schemas import ConversationData, ConversationMessage

logger = logging.getLogger(__name__)


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _html_to_markdown(el) -> str:
    try:
        from markdownify import markdownify
        inner = el.decode_contents()
        if not inner.strip():
            return el.get_text(separator="\n", strip=True)
        md = markdownify(inner, heading_style="ATX", bullets="-", strip=["img", "script", "style"])
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md.strip() or el.get_text(separator="\n", strip=True)
    except Exception:
        return el.get_text(separator="\n", strip=True)


def _extract_code_blocks(text: str) -> tuple[list[dict], bool]:
    matches = re.findall(r"```(\w*)\n(.*?)```", text, re.DOTALL)
    blocks = [{"language": lang or "text", "code": code.strip()} for lang, code in matches]
    return blocks, bool(blocks)


# ─── Gemini ──────────────────────────────────────────────────────────────────

_GEMINI_MSG_SELECTORS = [
    ".conversation-turn", "[data-message-id]",
    "message-content", ".query-content, .response-content",
]
_GEMINI_TITLE_SELECTORS = ["h1", ".conversation-title", "title"]


def _detect_gemini_role(text: str, prev_role: str | None) -> str:
    low = text.strip().lower()
    if any(low.startswith(p) for p in ["you said:", "user:", "prompt:"]):
        return "user"
    if any(low.startswith(p) for p in ["gemini:", "model:", "response:"]):
        return "model"
    return "model" if prev_role == "user" else "user"


def _parse_gemini(html: str, raw_text: str, share_url: str) -> ConversationData:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return _gemini_fallback(raw_text, share_url)

    title = "Gemini Conversation"
    for sel in _GEMINI_TITLE_SELECTORS:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True).lower() not in ["gemini", "google gemini", ""]:
            title = el.get_text(strip=True)
            break

    elems = []
    for sel in _GEMINI_MSG_SELECTORS:
        elems = soup.select(sel)
        if elems:
            break

    messages = []
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
                _detect_gemini_role(text, prev)
            )
            cbs, has = _extract_code_blocks(text)
            messages.append(ConversationMessage(
                role=role, content=text, index=idx, has_code_blocks=has, code_blocks=cbs,
            ))
            prev = role
    else:
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if len(p.strip()) > 20]
        prev = None
        for idx, para in enumerate(paragraphs):
            role = _detect_gemini_role(para, prev)
            cbs, has = _extract_code_blocks(para)
            messages.append(ConversationMessage(
                role=role, content=para, index=idx, has_code_blocks=has, code_blocks=cbs,
            ))
            prev = role

    if not messages:
        return _gemini_fallback(raw_text, share_url)

    return ConversationData(
        title=title, share_url=share_url,
        extracted_at=datetime.utcnow(),
        message_count=len(messages), messages=messages,
        metadata={"platform": "gemini"},
    )


def _gemini_fallback(raw_text: str, share_url: str) -> ConversationData:
    lines = [l.strip() for l in raw_text.split("\n")
             if len(l.strip()) > 5
             and not any(p in l.lower() for p in ["sign in", "google", "share", "copy", "menu"])]
    content = "\n".join(lines) or raw_text
    return ConversationData(
        title="Gemini Conversation", share_url=share_url,
        extracted_at=datetime.utcnow(), message_count=1,
        messages=[ConversationMessage(role="model", content=content, index=0,
                                      has_code_blocks=False, code_blocks=[])],
        metadata={"platform": "gemini", "parse_method": "raw_text_fallback"},
    )


# ─── ChatGPT ─────────────────────────────────────────────────────────────────

def _parse_chatgpt(html: str, raw_text: str, share_url: str) -> ConversationData:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script or not script.string:
        return _chatgpt_html_fallback(soup, share_url)

    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return _chatgpt_html_fallback(soup, share_url)

    page_props = data.get("props", {}).get("pageProps", {})
    server_resp = page_props.get("serverResponse", {})
    conv_data = (
        server_resp.get("data")
        or page_props.get("sharedConversation")
        or page_props.get("conversation")
        or {}
    )

    title = conv_data.get("title") or "ChatGPT Conversation"
    mapping = conv_data.get("mapping", {})

    if not mapping:
        return _chatgpt_html_fallback(soup, share_url)

    messages = _linearize_chatgpt_mapping(mapping)
    if not messages:
        return _chatgpt_html_fallback(soup, share_url)

    return ConversationData(
        title=title, share_url=share_url,
        extracted_at=datetime.utcnow(),
        message_count=len(messages), messages=messages,
        metadata={"platform": "chatgpt"},
    )


def _linearize_chatgpt_mapping(mapping: dict) -> list[ConversationMessage]:
    # Find the root node (parent is None or points outside the mapping)
    root_id = None
    for node_id, node in mapping.items():
        parent = node.get("parent")
        if parent is None or parent not in mapping:
            root_id = node_id
            break
    if not root_id:
        return []

    messages: list[ConversationMessage] = []
    visited: set[str] = set()

    def traverse(node_id: str) -> None:
        if node_id in visited or node_id not in mapping:
            return
        visited.add(node_id)

        node = mapping[node_id]
        msg = node.get("message")

        if msg:
            role = msg.get("author", {}).get("role", "")
            content_obj = msg.get("content", {})
            content_type = content_obj.get("content_type", "")

            if role in ("user", "assistant") and content_type == "text":
                parts = content_obj.get("parts", [])
                text = "\n".join(str(p) for p in parts if isinstance(p, str)).strip()
                if text:
                    cbs, has = _extract_code_blocks(text)
                    messages.append(ConversationMessage(
                        role="user" if role == "user" else "model",
                        content=text,
                        index=len(messages),
                        has_code_blocks=has,
                        code_blocks=cbs,
                    ))

        # Follow the last child — main branch in branched/regenerated conversations
        children = node.get("children", [])
        if children:
            traverse(children[-1])

    traverse(root_id)
    return messages


def _chatgpt_html_fallback(soup, share_url: str) -> ConversationData:
    """Fallback: parse visible HTML when __NEXT_DATA__ is unavailable."""
    articles = soup.find_all("article") or soup.find_all(attrs={"data-message-id": True})
    messages = []
    for idx, art in enumerate(articles):
        role_attr = art.get("data-message-author-role") or ("user" if idx % 2 == 0 else "assistant")
        text = _html_to_markdown(art)
        if text.strip():
            cbs, has = _extract_code_blocks(text)
            messages.append(ConversationMessage(
                role="user" if role_attr == "user" else "model",
                content=text, index=idx, has_code_blocks=has, code_blocks=cbs,
            ))
    if not messages:
        text = soup.get_text(separator="\n", strip=True)
        messages = [ConversationMessage(role="model", content=text, index=0,
                                        has_code_blocks=False, code_blocks=[])]
    return ConversationData(
        title="ChatGPT Conversation", share_url=share_url,
        extracted_at=datetime.utcnow(), message_count=len(messages),
        messages=messages,
        metadata={"platform": "chatgpt", "parse_method": "html_fallback"},
    )


# ─── Dispatcher ──────────────────────────────────────────────────────────────

def parse_html_to_conversation(html: str, raw_text: str, share_url: str) -> ConversationData:
    from app.services.scraper import detect_platform
    platform = detect_platform(share_url)
    if platform == "chatgpt":
        return _parse_chatgpt(html, raw_text, share_url)
    return _parse_gemini(html, raw_text, share_url)
