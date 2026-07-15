# frontend/

Next.js application (Phase 3 — see docs/ROADMAP.md). Two surfaces in one app:

1. **Reader site** — Bangla + English news portal. SSG/ISR pages for speed (Lighthouse 95+ target), mobile-first, accessible.
2. **Admin dashboard** — review queue (`pending_approval` stories), article diff/edit view, approve/reject actions, agent-run inspector, analytics.

## Planned structure

```
frontend/
  src/app/(reader)/            # public site: home, category, article pages
  src/app/(admin)/admin/       # dashboard (Clerk-protected)
  src/components/
  src/lib/api.ts               # typed client for /api/v1
  src/i18n/                    # bn / en dictionaries
```

## Bootstrap (when starting Phase 3)

```
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir
npm i @clerk/nextjs
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` and consume the endpoints in docs/API_SPECIFICATION.md. Deploy target: Vercel.
