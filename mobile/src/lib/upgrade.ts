/**
 * Asking the backend whether this build is still allowed to run.
 *
 * The one property that matters more than the feature working: **it fails
 * open**. Every path that is not an explicit `required` from the server ends
 * up as "carry on" -- offline, a 500, a timeout, a body in a shape this does
 * not recognise, a version string neither side can parse. A gate that fails
 * closed turns a backend wobble into every phone showing an upgrade wall that
 * no amount of tapping clears, and the fix has to go through App Review.
 *
 * The check runs unauthenticated, because the build being gated may be one
 * whose sign-in is exactly what broke.
 */

import axios from 'axios';
import * as Application from 'expo-application';
import { Platform } from 'react-native';

import type { UpgradeCheck, UpgradeRequirement } from '@app/shared/types';

import { routes } from './routes';

/**
 * A bare client, not the app's own.
 *
 * `lib/api.ts` attaches a bearer token and, on a 401, starts a refresh and
 * can end the session. None of that belongs on a public endpoint the app
 * calls at launch: a check that could sign someone out because a server
 * answered oddly would be worse than no check. This one carries no
 * credential and has no interceptors to trigger.
 *
 * The timeout matters as much as the rest. Without it a hung connection
 * leaves a socket open for as long as the OS allows, for an answer nobody is
 * waiting on any more -- `useUpgradeGate` stops holding the splash screen
 * long before this expires.
 */
const plain = axios.create({ timeout: 6000 });

/** Neither platform the gate knows about; nothing to ask. */
export function gatedPlatform(): 'ios' | 'android' | null {
  return Platform.OS === 'ios' || Platform.OS === 'android' ? Platform.OS : null;
}

/**
 * This build's own version, as the store shows it.
 *
 * `nativeApplicationVersion` rather than the value in app.config.ts: after an
 * over-the-air update the JavaScript can come from a different publish than
 * the binary it is running inside, and the gate is about the *binary* -- it
 * exists to say "this native build must be replaced", which no update can do.
 */
export function currentVersion(): string | null {
  return Application.nativeApplicationVersion;
}

const NOTHING: UpgradeCheck = {
  requirement: 'none',
  minimum_version: '',
  recommended_version: '',
  store_url: '',
  message: '',
};

function isRequirement(value: unknown): value is UpgradeRequirement {
  return value === 'none' || value === 'recommended' || value === 'required';
}

export async function checkForUpgrade(): Promise<UpgradeCheck> {
  const platform = gatedPlatform();
  const version = currentVersion();
  if (!platform || !version) return NOTHING;

  try {
    const response = await plain.get(routes.api.app.upgrade(platform, version));
    const data = response.data?.data;
    // Validated rather than trusted. A proxy that answers HTML, or an older
    // backend without this endpoint answering its own 404 page, must not be
    // able to produce a truthy `requirement` by accident.
    if (!data || !isRequirement(data.requirement)) return NOTHING;
    return {
      requirement: data.requirement,
      minimum_version: String(data.minimum_version ?? ''),
      recommended_version: String(data.recommended_version ?? ''),
      store_url: String(data.store_url ?? ''),
      message: String(data.message ?? ''),
    };
  } catch {
    return NOTHING;
  }
}
