"""Generate an AI summary of a conversation using Claude Haiku."""

import logging
from app.models.schemas import ConversationData

logger = logging.getLogger(__name__)

MAX_CHARS = 12000  # truncate long convos before sending to API


def _build_prompt(conversation: ConversationData) -> str:
    lines = [f"Conversation title: {conversation.title}", ""]
    char_count = 0
    for msg in conversation.messages:
        label = "User" if msg.role == "user" else "Assistant"
        snippet = msg.content[:500] if len(msg.content) > 500 else msg.content
        lines.append(f"{label}: {snippet}")
        char_count += len(snippet)
        if char_count > MAX_CHARS:
            lines.append("[...conversation truncated for summary...]")
            break
    return "\n".join(lines)


async def generate_summary(conversation: ConversationData, api_key: str) -> str:
    """Call Claude Haiku to summarise the conversation. Returns empty string on any failure."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("anthropic package not installed — skipping summary")
        return ""

    if not api_key:
        return ""

    client = AsyncAnthropic(api_key=api_key)
    prompt = _build_prompt(conversation)

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    "Summarise the following AI chat conversation in 2–4 sentences. "
                    "Be concise and factual — focus on what was discussed and any conclusions reached.\n\n"
                    + prompt
                ),
            }],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"AI summary generation failed: {e}")
        return ""
