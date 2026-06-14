"""CSV export generator."""

import csv
import io
from app.models.schemas import ConversationData


def generate_csv_bytes(conversation: ConversationData) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, quoting=csv.QUOTE_ALL)
    w.writerow(["index", "role", "content", "has_code", "source_url", "title"])
    for msg in conversation.messages:
        w.writerow([msg.index, msg.role, msg.content, msg.has_code_blocks,
                     conversation.share_url, conversation.title])
    return out.getvalue().encode("utf-8")
