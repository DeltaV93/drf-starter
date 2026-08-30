/**
 * Load something from the API, once, and again on demand.
 *
 * Six screens wanted the same twelve lines, and the obvious shape for them --
 * a `load` callback the effect calls -- is the one React's compiler rules
 * reject, for a reason worth restating: calling a function that sets state
 * from an effect's *synchronous* body makes React render, discard, and render
 * again before the first paint. On a phone that is a visible stutter every
 * time a screen opens.
 *
 * So the fetch happens inside the effect and state is only ever set after the
 * await, which is the arrangement `useAuthBootstrap` uses too. Two smaller
 * consequences follow from the same rule:
 *
 * `loading` is derived rather than stored -- a `setLoading(true)` at the top
 * of the effect would be exactly the synchronous write being avoided. It also
 * means a reload keeps the previous data on screen instead of blanking it,
 * which is the better answer anyway.
 *
 * And reloading is a counter the effect depends on rather than a second code
 * path, so a manual refresh and the first load cannot drift apart.
 *
 * The cancelled flag stops a slow response landing on a screen the user has
 * already navigated away from.
 */

import { useCallback, useEffect, useState } from 'react';

export interface Resource<T> {
  data: T | null;
  loading: boolean;
  /**
   * Whatever was thrown, or null. Distinct from `data === null`.
   *
   * The raw error rather than a message, because only the component knows
   * how to say it: `useErrorMessage` translates, and distinguishes "you are
   * offline" from "the server refused". A hook cannot call `t` on the
   * caller's behalf without guessing which of the two it is.
   */
  error: unknown;
  reload: () => void;
}

export function useResource<T>(fetcher: () => Promise<T | undefined>): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const result = await fetcher();
        if (cancelled) return;
        setData(result ?? null);
        setError(null);
      } catch (thrown) {
        if (cancelled) return;
        setError(thrown);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [fetcher, attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  return { data, loading: data === null && error === null, error, reload };
}
