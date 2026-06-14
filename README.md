# ConvertMyChat

> Extract and export conversations from Google Gemini shared chat links.

Paste a `gemini.google.com/share/...` link → get a clean PDF, Word, CSV, or Markdown export.
Optional accounts save your export history. Admin panel for user management.

## Stack
- **Frontend:** React 19 + Vite + TypeScript + Tailwind CSS
- **Backend:** FastAPI + Playwright + SQLAlchemy async + asyncpg
- **Database:** Railway Postgres
- **Auth:** Google OAuth + email/password → self-issued JWT

## Quick Start

### Backend
```bash
cd backend
python -m pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # edit with your values
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/extract | Public | Extract conversation from share link |
| POST | /api/export | Public* | Generate file download (*saves to history if logged in) |
| POST | /api/auth/register | Public | Email/password signup |
| POST | /api/auth/login | Public | Email/password login |
| GET | /api/auth/google/login | Public | Get Google OAuth URL |
| POST | /api/auth/google/callback | Public | Exchange code for JWT |
| GET | /api/auth/me | User | Current user info |
| GET | /api/history/ | User | List export history |
| GET | /api/history/{id}/reexport | User | Re-export in new format |
| DELETE | /api/history/{id} | User | Delete history item |
| GET | /api/admin/users | Admin | List all users |
| POST | /api/admin/users | Admin | Create user |
| PATCH | /api/admin/users/{id} | Admin | Update user |
| POST | /api/admin/users/{id}/reset-password | Admin | Reset password |
| DELETE | /api/admin/users/{id} | Admin | Delete user |
| GET | /api/admin/stats | Admin | Dashboard stats |
