/**
 * Run the version check once per launch, and hold the answer.
 *
 * Written to the same rule as `useResource`: the request lives inside the
 * effect and every state write happens after an await or in a callback,
 * because React's compiler rules reject a state-setting call in an effect's
 * synchronous body -- and on a phone that costs a visible stutter before the
 * first paint.
 *
 * The deadline is the part worth explaining. Holding the splash screen until
 * the backend answers would be simplest, and it is wrong: a blocked build is
 * rare and a slow connection is not, so every launch on a bad network would
 * pay a spinner for a wall almost nobody sees. Instead the splash waits only
 * briefly. The check keeps running, and if it comes back `required` after the
 * app is already on screen, the wall drops then -- a moment of the app being
 * visible is a far better trade than seconds of splash for everyone.
 */

import { useEffect, useState } from 'react';

import type { UpgradeCheck } from '@app/shared/types';

import { checkForUpgrade } from './upgrade';

/**
 * How long the splash screen will wait for the answer.
 *
 * Long enough to cover a healthy round trip, so the ordinary case never shows
 * the app and then replaces it. Short enough that a dead network is not
 * something the user sits through.
 */
const SPLASH_DEADLINE_MS = 1500;

export interface UpgradeGate {
  /** True while the caller should keep the splash screen up. */
  pending: boolean;
  /** The answer, or null until it arrives. It fails open, so never a throw. */
  check: UpgradeCheck | null;
}

export function useUpgradeGate(): UpgradeGate {
  const [check, setCheck] = useState<UpgradeCheck | null>(null);
  const [deadlinePassed, setDeadlinePassed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const timer = setTimeout(() => {
      if (!cancelled) setDeadlinePassed(true);
    }, SPLASH_DEADLINE_MS);

    (async () => {
      // Cannot reject: `checkForUpgrade` turns every failure into "carry on".
      const result = await checkForUpgrade();
      if (!cancelled) setCheck(result);
    })();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return { pending: check === null && !deadlinePassed, check };
}
