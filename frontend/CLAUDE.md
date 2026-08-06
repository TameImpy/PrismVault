@AGENTS.md

# Frontend-specific guidance

## Framework

Next.js 16.2.1 with Turbopack. Middleware uses `proxy.ts` (NOT `middleware.ts`). Never create a `middleware.ts` file — Next.js 16 does not allow both.

Read `node_modules/next/dist/docs/` before making framework-level changes. APIs and conventions may differ from earlier Next.js versions.

## Commands

```bash
npm run dev          # Dev server (memory-capped to 512MB)
npm run build        # Production build
npm test             # Run vitest
npm run test:watch   # Watch mode
```

## Key patterns

- **Auth**: All login/signup must use `useAuth()` from `contexts/AuthContext.tsx`, not raw fetch. This ensures AuthProvider state updates before navigation.
- **Auth navigation**: never `router.push` or `window.location.href` to or from a sign-in page — always `replace`, so the login form cannot sit one Back press behind the app (#161). Use `completeSignIn()` and `loginPath()` from `lib/authNavigation.ts`; a test reads these files and fails on a `push`. Reproduce anything in this area against `next build && next start`, never `next dev` — HMR blocks the back/forward cache and changes what Back does.
- **Route protection**: Dual approach — `proxy.ts` (server-side cookie check) + `useAuth()` guard in protected pages (client-side).
- **Analytics**: Use `useAnalytics()` from `components/AnalyticsProvider.tsx` for event tracking. Mixpanel is EU-hosted.
- **Design system**: Prism Deep Sea tokens in `app/globals.css` via Tailwind v4 `@theme`. See `PRISM DESIGN.MD` at project root.
- **API calls**: All fetch requests to the backend must use relative paths (`/api/...`) and include `credentials: "include"` for cookie auth. Next.js rewrites proxy these to the backend.

## Troubleshooting

- Delete `.next/` if stale build errors appear after file renames/deletions
- Dev server is memory-capped (`--max-old-space-size=512`) — if OOM, clear `.next/` cache
