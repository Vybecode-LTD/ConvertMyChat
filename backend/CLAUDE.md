# CLAUDE.md — ConvertMyChat Backend

## Stack
FastAPI + SQLAlchemy async + asyncpg + Alembic + Playwright + authlib

## Commands
```bash
python -m pip install -r requirements.txt
playwright install chromium
python -m uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## API Routes
- `GET  /api/health` — healthcheck
- `POST /api/extract` — extract conversation (public)
- `POST /api/extract-v2` — extract + detect embedded content (tables/JSON/code)
- `POST /api/export` — generate single-file download (public, auto-saves if logged in)
- `POST /api/export-bundle` — generate ZIP with main doc + embedded content files
- `POST /api/auth/register` — email/password signup
- `POST /api/auth/login` — email/password login
- `GET  /api/auth/google/login` — get Google OAuth URL
- `POST /api/auth/google/callback` — exchange Google code for JWT
- `GET  /api/auth/me` — current user (requires JWT)
- `GET  /api/history/` — user's export history (requires JWT)
- `GET  /api/history/{id}/reexport` — re-export in new format
- `DELETE /api/history/{id}` — delete history item
- `GET  /api/admin/users` — list users (admin only)
- `POST /api/admin/users` — create user (admin only)
- `PATCH /api/admin/users/{id}` — update user (admin only)
- `POST /api/admin/users/{id}/reset-password` — reset password (admin only)
- `DELETE /api/admin/users/{id}` — delete user (admin only)
- `GET  /api/admin/users/{id}/history` — view user's history (admin only)
- `GET  /api/admin/stats` — dashboard stats (admin only)

## Database
Railway Postgres. DATABASE_URL auto-injected by Railway.
Normalize postgresql:// to postgresql+asyncpg:// in config.py.

## Auth Flow
1. Public routes (extract/export) need no auth
2. Optional auth: if JWT present on /export, auto-saves to history
3. Required auth: /history/* and /auth/me require valid JWT
4. Admin auth: /admin/* requires is_admin=True

## Env Vars
DATABASE_URL, JWT_SECRET, ADMIN_EMAIL, GOOGLE_CLIENT_ID,
GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, CORS_ORIGINS
