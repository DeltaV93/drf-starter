# Frontend

React + TypeScript + Vite SPA for the DRF Starter backend.

See the [root README](../README.md) for the full setup. Quick start:

```bash
cp .env.example .env
npm install
npm run dev            # http://localhost:3000
```

The dev server proxies `/api` to Django (`VITE_API_PROXY_TARGET`, default
`http://localhost:8000`) so the SPA and the API share an origin. That is what
makes session cookies work without `SameSite=None` or CORS preflights.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with HMR on port 3000 |
| `npm run build` | Typecheck, then production build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run typecheck` | `tsc` with no emit |
| `npm run lint` | ESLint, warnings treated as errors |
| `npm run test` | Vitest, single run |
| `npm run test:watch` | Vitest in watch mode |
| `npm run test:coverage` | Vitest with a v8 coverage report |

## Layout

```
src/
  lib/          api client, route table, shared types
  store/        jotai atoms and hooks (auth, toast)
  components/   common/ layout/ pages/
  hooks/        reusable hooks
  locales/      i18n resources (en, es)
  test/         vitest setup and render helpers
```

## Authentication

The server session is the source of truth. On boot `useAuthBootstrap` calls
`/users/me/` and the answer decides `authenticated` / `anonymous`; nothing is
trusted from `localStorage`. `ProtectedRoute` waits for that answer before
redirecting, so a hard refresh does not bounce a signed-in user to `/login`.

Unsafe requests need a CSRF token. `src/lib/api.ts` handles it: the request
interceptor reads the `csrftoken` cookie, fetching one from `/auth/csrf/`
first if it is missing, and sets `X-CSRFToken`. No call site has to think
about it.

## Billing

`VITE_STRIPE_ENABLED` gates the `/subscription` route and must agree with
`STRIPE_ENABLED` on the backend. Checkout is Stripe-hosted: the backend
creates a session and the app navigates to its URL, so card details never
reach this application. See the root README for how to remove billing
entirely.
