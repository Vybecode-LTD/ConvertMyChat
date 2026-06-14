"""Markdown export generator."""

from app.models.schemas import ConversationData


def generate_markdown_bytes(conversation: ConversationData) -> bytes:
    lines = [
        f"# {conversation.title}", "",
        f"> **Source:** {conversation.share_url}",
        f"> **Extracted:** {conversation.extracted_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"> **Messages:** {conversation.message_count}", "", "---", "",
    ]
    for msg in conversation.messages:
        platform = str((conversation.metadata or {}).get("platform", "gemini"))
        ai = {"chatgpt": "ChatGPT", "gemini": "Gemini"}.get(platform, "Gemini")
        label = "👤 User" if msg.role == "user" else f"🤖 {ai}"
        lines.extend([f"## {label}", "", msg.content, ""])
    return "\n".join(lines).encode("utf-8")
