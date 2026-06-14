# ConvertMyChat — Complete Session Artifacts Index
## Domain: convertmy.chat

## Project Scaffold (final)
**`convertmychat-full-scaffold.zip`** — 67 files, ready for Claude Code.

Stack: FastAPI + SQLAlchemy async + asyncpg + Alembic + Playwright + Railway Postgres
Auth: Google OAuth + email/password + self-issued JWT (optional, three-tier)
Frontend: React 19 + Vite + TypeScript + Tailwind CSS

### Features
- Extract Gemini share links → export as PDF/DOCX/CSV/MD
- Embedded content detection: auto-extracts tables, JSON, and code blocks
- Bundle export: ZIP with main document + separated content files
- Optional user accounts with export history
- Admin panel (create/delete users, reset passwords, toggle admin/active)

### Branding Applied
- App name: ConvertMyChat
- Logo: "ConvertMy" + ".chat" in Ember accent
- Icon: "C" on Ember background
- localStorage key: cmc_token
- Database: convertmychat
- Package: convertmychat-frontend

## Skills (4)
| Skill | Format |
|-------|--------|
| `optional-auth-pattern` | .skill + .zip |
| `playwright-web-scraping` | .skill + .zip |
| `sqlalchemy-async-fastapi` | .skill + .zip |
| `structured-content-extractor` | .skill + .zip |

## Claude Code Session 1 Kickoff
> Read CLAUDE.md. Install deps, playwright install chromium.
> Set up .env, start FastAPI, verify tables auto-create, hit /api/health.
> Open a real Gemini share link, inspect the DOM, update parser.py selectors.
> Test e2e extraction + embedded content detection.
