/**
 * The website's route table.
 *
 * The paths themselves live in `@app/shared/routes` so the mobile app cannot
 * drift from them. All that is web-specific is where the base URL comes from:
 * Vite substitutes `import.meta.env` at build time, and that syntax does not
 * survive React Native's bundler -- which is why the shared module takes the
 * base as an argument instead of reading it.
 *
 * VITE_API_BASE_URL must NOT end with a slash -- see .env.example.
 */

import { createRoutes, DEFAULT_API_BASE_URL } from '@app/shared/routes';

export const routes = createRoutes(import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL);
