/**
 * Light, dark, or whatever the phone is set to.
 *
 * Three states rather than two, and the third is the default. A boolean
 * "dark mode" toggle cannot express "follow the system", so an app built on
 * one stops tracking the phone's own schedule the first time anyone touches
 * it -- and there is no way back short of reinstalling.
 *
 * The preference is stored in AsyncStorage rather than SecureStore. It is not
 * a secret, and on iOS a keychain entry survives uninstalling the app: someone
 * who removed the app to reset it would find their old theme waiting.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { atom, useAtom, useAtomValue } from 'jotai';
import { useCallback, useEffect } from 'react';
import { useColorScheme as useSystemColorScheme } from 'react-native';

import { darkTheme, lightTheme, type AppTheme } from './paper';

export type ColorSchemePreference = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'ui.colorScheme';

const preferenceAtom = atom<ColorSchemePreference>('system');

/** Whether the stored preference has been read yet. */
const hydratedAtom = atom(false);

function isPreference(value: string | null): value is ColorSchemePreference {
  return value === 'system' || value === 'light' || value === 'dark';
}

/**
 * Read the stored preference once, at startup.
 *
 * Mount this exactly once, at the root. Until it resolves the app renders in
 * the system scheme, which is the right thing to show while we do not know:
 * it is what an app with no preference would show anyway, so a returning
 * visitor sees at most one frame of the wrong theme rather than a flash of
 * light on a dark phone.
 */
export function useColorSchemeBootstrap(): void {
  const [, setPreference] = useAtom(preferenceAtom);
  const [, setHydrated] = useAtom(hydratedAtom);

  useEffect(() => {
    let cancelled = false;

    AsyncStorage.getItem(STORAGE_KEY)
      .then((stored) => {
        if (cancelled) return;
        if (isPreference(stored)) setPreference(stored);
      })
      .catch(() => {
        // An unreadable preference is not an error worth surfacing; the
        // system scheme is a perfectly good answer.
      })
      .finally(() => {
        if (!cancelled) setHydrated(true);
      });

    return () => {
      cancelled = true;
    };
  }, [setPreference, setHydrated]);
}

export function useColorSchemePreference() {
  const [preference, setPreference] = useAtom(preferenceAtom);

  const choose = useCallback(
    (next: ColorSchemePreference) => {
      setPreference(next);
      AsyncStorage.setItem(STORAGE_KEY, next).catch(() => {
        // The choice still applies to this launch. Losing it on restart is a
        // better outcome than refusing to apply it.
      });
    },
    [setPreference],
  );

  return { preference, choose };
}

/** The scheme actually in force, resolving `system` against the OS. */
export function useResolvedColorScheme(): 'light' | 'dark' {
  const preference = useAtomValue(preferenceAtom);
  const system = useSystemColorScheme();

  if (preference === 'system') return system === 'dark' ? 'dark' : 'light';
  return preference;
}

export function useAppTheme(): AppTheme {
  return useResolvedColorScheme() === 'dark' ? darkTheme : lightTheme;
}

export function useColorSchemeHydrated(): boolean {
  return useAtomValue(hydratedAtom);
}
