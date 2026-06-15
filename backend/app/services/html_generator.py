"""Generate a self-contained HTML export of a conversation with syntax highlighting."""

import html
import re
from datetime import datetime

from app.models.schemas import ConversationData

HIGHLIGHT_CDN = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0"


def _e(text: str) -> str:
    return html.escape(text)


def _inline_md(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code class="ic">\1</code>', text)
    return text


def _render_table_html(lines: list[str]) -> str:
    rows = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append(cells)
    if len(rows) < 2:
        return ""
    parts = ['<div class="tw"><table><thead><tr>']
    for cell in rows[0]:
        parts.append(f"<th>{_e(cell)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in rows[2:]:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{_e(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def _md_to_html(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    table_buf: list[str] = []

    for line in lines:
        # Code fence
        if line.startswith("```"):
            if in_code:
                code_content = "\n".join(code_buf)
                lang_class = f' class="language-{_e(code_lang)}"' if code_lang else ""
                out.append(f'<pre><code{lang_class}>{_e(code_content)}</code></pre>')
                in_code = False
                code_buf = []
                code_lang = ""
            else:
                if table_buf:
                    out.append(_render_table_html(table_buf))
                    table_buf = []
                in_code = True
                code_lang = line[3:].strip()
            continue

        if in_code:
            code_buf.append(line)
            continue

        # Table accumulation
        if line.startswith("|") and "|" in line[1:]:
            table_buf.append(line)
            continue
        else:
            if table_buf:
                out.append(_render_table_html(table_buf))
                table_buf = []

        stripped = line.strip()
        if stripped.startswith("### "):
            out.append(f"<h3>{_inline_md(_e(stripped[4:]))}</h3>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{_inline_md(_e(stripped[3:]))}</h2>")
        elif stripped.startswith("# "):
            out.append(f"<h1>{_inline_md(_e(stripped[2:]))}</h1>")
        elif re.match(r'^[-*] ', stripped):
            out.append(f"<li>{_inline_md(_e(stripped[2:]))}</li>")
        elif re.match(r'^\d+\. ', stripped):
            content = re.sub(r'^\d+\. ', '', stripped)
            out.append(f"<li>{_inline_md(_e(content))}</li>")
        elif stripped == "":
            out.append("<br>")
        else:
            out.append(f"<p>{_inline_md(_e(line))}</p>")

    if table_buf:
        out.append(_render_table_html(table_buf))

    return "\n".join(out)


def generate_html_bytes(conversation: ConversationData) -> bytes:
    platform = str((conversation.metadata or {}).get("platform", "gemini"))
    ai_label = {"chatgpt": "ChatGPT", "gemini": "Gemini"}.get(platform, "Gemini")
    summary = str((conversation.metadata or {}).get("summary", ""))
    title_esc = _e(conversation.title)
    exported_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    msgs_html = []
    for msg in conversation.messages:
        role_cls = "user" if msg.role == "user" else "asst"
        label = "You" if msg.role == "user" else ai_label
        msgs_html.append(
            f'<div class="msg {role_cls}">'
            f'<div class="lbl">{label}</div>'
            f'<div class="body">{_md_to_html(msg.content)}</div>'
            f'</div>'
        )

    summary_html = ""
    if summary:
        summary_html = (
            f'<div class="sum-box">'
            f'<div class="sum-lbl">AI Summary</div>'
            f'<div class="sum-body">{_e(summary)}</div>'
            f'</div>'
        )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_esc}</title>
<link rel="stylesheet" href="{HIGHLIGHT_CDN}/styles/github-dark.min.css">
<script src="{HIGHLIGHT_CDN}/highlight.min.js"></script>
<style>
:root{{--bg:#0a0a0a;--surf:#141414;--surf2:#1e1e1e;--bdr:#2a2a2a;--txt:#e8e8e8;--muted:#777;--ember:#e8440a}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:15px;line-height:1.7;padding:0 16px 80px}}
.wrap{{max-width:800px;margin:0 auto}}
header{{border-bottom:1px solid var(--bdr);padding:28px 0 20px;margin-bottom:32px}}
.title{{font-size:1.5rem;font-weight:700;margin-bottom:8px}}
.meta{{font-size:.8rem;color:var(--muted)}}
.meta a{{color:var(--ember);text-decoration:none}}
.sum-box{{background:var(--surf);border:1px solid var(--bdr);border-left:3px solid var(--ember);border-radius:8px;padding:16px 20px;margin-bottom:32px}}
.sum-lbl{{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--ember);font-weight:600;margin-bottom:8px}}
.sum-body{{font-size:.9rem;white-space:pre-wrap}}
.msg{{padding:20px 0;border-bottom:1px solid var(--bdr)}}
.msg:last-child{{border-bottom:none}}
.lbl{{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:10px}}
.user .lbl{{color:#60a5fa}}
.asst .lbl{{color:#4ade80}}
.body h1{{font-size:1.3rem;font-weight:600;margin:16px 0 8px}}
.body h2{{font-size:1.1rem;font-weight:600;margin:14px 0 6px}}
.body h3{{font-size:1rem;font-weight:600;margin:12px 0 5px}}
.body p{{margin:5px 0}}
.body li{{margin-left:20px;margin-bottom:3px}}
.body br{{display:block;content:"";margin:3px 0}}
pre{{background:#161616;border:1px solid var(--bdr);border-radius:8px;padding:16px;margin:12px 0;overflow-x:auto}}
pre code{{font-family:'JetBrains Mono','Fira Code',Consolas,monospace;font-size:13px;background:none;padding:0}}
code.ic{{background:#2a2a2a;padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono','Fira Code',Consolas,monospace;font-size:.85em;color:#f8b04a}}
.tw{{overflow-x:auto;margin:12px 0}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th{{background:var(--surf2);color:var(--txt);padding:8px 12px;text-align:left;font-weight:600;border:1px solid var(--bdr)}}
td{{padding:7px 12px;border:1px solid var(--bdr)}}
tr:nth-child(even) td{{background:var(--surf)}}
footer{{margin-top:40px;padding-top:20px;border-top:1px solid var(--bdr);font-size:.75rem;color:var(--muted);text-align:center}}
</style>
</head>
<body>
<div class="wrap">
<header>
<div class="title">{title_esc}</div>
<div class="meta">{conversation.message_count} messages &nbsp;·&nbsp; <a href="{_e(conversation.share_url)}" target="_blank" rel="noopener">Original link</a> &nbsp;·&nbsp; Exported {exported_at}</div>
</header>
{summary_html}
<div class="msgs">{"".join(msgs_html)}</div>
<footer>Exported by <a href="https://convertmy.chat" style="color:var(--ember);text-decoration:none">ConvertMyChat</a></footer>
</div>
<script>hljs.highlightAll();</script>
</body>
</html>"""

    return doc.encode("utf-8")
