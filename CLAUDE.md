# CLAUDE.md — ConvertMyChat

## What This Is
Web app that extracts conversation data from Google Gemini shared chat links
and exports as PDF, DOCX, CSV, or Markdown. Optional user accounts save export
history. Admin panel for user management.

## Architecture
```
React (Vite/TS) → FastAPI → Playwright → Gemini share page
                         → SQLAlchemy async + asyncpg → Railway Postgres
                         → Doc generators (DOCX/PDF/CSV/MD)
                         → JWT auth (Google OAuth + email/password)
```

- **Frontend:** React 19 + Vite + TypeScript + Tailwind CSS
- **Backend:** FastAPI + Playwright + SQLAlchemy async + asyncpg
- **Database:** Railway Postgres (NOT Supabase)
- **Auth:** Google OAuth via authlib + self-issued JWT + passlib bcrypt
- **Migrations:** Alembic (async env.py)
- **Hosting:** Railway PRO

## Key Technical Facts
- Gemini share links are PUBLIC — no Google OAuth needed to VIEW them
- Google OAuth is for USER ACCOUNTS only (optional sign-in to save history)
- Share pages are client-side rendered Angular — Playwright required
- Auth is optional: extract/export works without login
- Admin routes require is_admin=True on user record
- DATABASE_URL comes from Railway Postgres plugin

## Standing Conventions (Vibrant Mindz)
- Dark background `#0a0a0a`, Ember accent `#e8440a`, JetBrains Mono
- `python -m pip` and `python -m uvicorn` always, never bare commands
- Pydantic Settings for all config, never hardcode secrets
- Async route handlers everywhere; CPU-bound work in `asyncio.to_thread()`
- CORS middleware configured for frontend origin
- Health endpoint at `GET /api/health`

## File Structure
```
convertmychat/
├── backend/
│   ├── app/
│   │   ├── core/           # config, database, security, exceptions
│   │   ├── models/         # SQLAlchemy models + Pydantic schemas
│   │   ├── routers/        # health, export, auth, history, admin
│   │   ├── services/       # scraper, parser, doc generators
│   │   ├── middleware/     # optional JWT auth middleware
│   │   └── utils/          # cache
│   ├── alembic/            # migrations (async env.py)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # LinkInput, FormatPicker, Preview, SignInButton,
│   │   │                   # HistoryView, AdminPanel
│   │   ├── contexts/       # AuthContext
│   │   ├── hooks/          # useExport, useAuth
│   │   ├── services/       # api.ts
│   │   └── types/
│   └── package.json
└── CLAUDE.md               # ← you are here
```

## Build Order
1. Backend core: config → database.py → security.py → SQLAlchemy models
2. Alembic: init + first migration
3. Services: scraper → parser → doc generators (unchanged from v1)
4. Routers: health → export → auth → history → admin
5. Frontend: types → api → auth context → components → App
6. Integration: wire frontend to backend, test e2e
7. Deploy: Dockerfile → railway.toml → env vars → Railway Postgres plugin

## Out of Scope
- Supabase (using Railway Postgres directly)
- Chrome extension (separate project)
- Batch export of multiple links (v2)
- Image extraction from conversations (v2)
- Email verification flow (v2 — for now, email/password just works)
- XLSX export for tables (v2 — currently CSV only)

## Named Failure Modes
- **GHOST_DOM:** Playwright loads page but content hasn't rendered. Fix: wait for selectors.
- **BOT_BLOCK:** Google detects headless browser. Fix: playwright-stealth + delays.
- **SELECTOR_DRIFT:** Google changes DOM. Fix: selectors isolated in parser.py.
- **DB_URL_SCHEME:** Railway gives postgresql://, asyncpg needs postgresql+asyncpg://. Fix: normalize in config.
- **ADMIN_ESCALATION:** Non-admin hits admin routes. Fix: is_admin check in middleware.

## Last Completed Task
Full scaffold v2 generated — Railway Postgres, SQLAlchemy async, Google OAuth,
admin panel, export history. Ready for Claude Code Session 1.
