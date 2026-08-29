/**
 * The mobile app's route table.
 *
 * The paths live in `@app/shared/routes` so this cannot drift from the
 * website. All that differs is where the base URL comes from -- see
 * `config.ts` for why it has to be spelled out rather than looked up.
 */

import { createRoutes } from '@app/shared/routes';

import { API_BASE_URL } from './config';

export const routes = createRoutes(API_BASE_URL);
