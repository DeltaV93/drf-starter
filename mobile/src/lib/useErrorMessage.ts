/**
 * Turning anything thrown into something worth showing someone.
 *
 * Every screen was doing this by hand:
 *
 *     error instanceof ApiError ? error.message : 'Could not load this.'
 *
 * which is repetitive, untranslated, and -- the part that matters -- wrong
 * about the most common failure on a phone. A request that never reached the
 * server has no message from the server, so that branch fell through to a
 * generic "something went wrong" for what is actually "you are on a train".
 *
 * `ApiError.isNetworkError` has been there since the shared client was
 * written and nothing read it. This is what reads it.
 */

import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import { ApiError } from './api';

export type DescribeError = (error: unknown, fallbackKey?: string) => string;

export function useErrorMessage(): DescribeError {
  const { t } = useTranslation();

  return useCallback(
    (error: unknown, fallbackKey = 'genericError') => {
      if (error instanceof ApiError) {
        // No status means the request never got an answer: no signal, a
        // captive portal, the API host unreachable. The backend's own
        // wording cannot help here because the backend never saw it.
        if (error.isNetworkError) return t('offlineHelp');

        // Only the backend's own words are shown as-is. Anything else is a
        // fallback invented in English somewhere up the stack, and showing it
        // to a Spanish reader is worse than showing them the generic line.
        if (error.fromServer) return error.message;
      }
      return t(fallbackKey);
    },
    [t],
  );
}
