# CLAUDE.md — ConvertMyChat Frontend

## Stack
React 19 + Vite + TypeScript + Tailwind CSS

## Commands
```bash
npm install
npm run dev
npm run build
```

## Design
Background #0a0a0a, Accent #e8440a (Ember), JetBrains Mono (mono), Inter (body)

## Views
- Home: extract + export flow (works without login)
- History: saved exports (requires login)
- Admin: user management (requires is_admin)

## Auth Flow
- JWT stored in localStorage as cmc_token
- AuthContext wraps app, checks token on mount
- Google OAuth: redirect → callback with ?code= → exchange for JWT
- All API calls include Authorization header if token present

## API: VITE_API_URL (default: proxied to localhost:8000)
