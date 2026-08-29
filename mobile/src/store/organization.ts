/**
 * The organization the app is acting for.
 *
 * Unlike the website, the client has to remember this. The server keeps the
 * browser's choice in its session; a bearer-token client has no session, so
 * it stores the slug and sends it as `X-Organization` on every request. See
 * `apps/organizations/context.py` for why a header is safe there -- the value
 * is resolved against the caller's own memberships, so it is a preference,
 * not an authorization.
 *
 * The choice is persisted: reopening the app in whichever organization you
 * were last in is the whole point of switching.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { atom, useAtom, useAtomValue, useSetAtom } from 'jotai';
import { useCallback, useEffect, useState } from 'react';

import { ORGANIZATION_HEADER } from '@app/shared/routes';
import type { Organization, OrganizationList } from '@app/shared/types';

import { apiData, http } from '../lib/api';
import { flags } from '../lib/config';
import { routes } from '../lib/routes';

const STORAGE_KEY = 'org.activeSlug';

const activeSlugAtom = atom<string | null>(null);

// Mirrored outside jotai because the interceptor below is not a component and
// cannot read an atom. The atom is what re-renders; this is what travels.
let activeSlug: string | null = null;

/**
 * Send the stored slug on every request.
 *
 * An interceptor rather than a per-call argument: the alternative is every
 * screen in the app remembering to pass it, and the one that forgets shows
 * another organization's data with nothing to explain it.
 */
http.interceptors.request.use((config) => {
  if (flags.organizations && activeSlug) {
    config.headers.set(ORGANIZATION_HEADER, activeSlug);
  }
  return config;
});

export function useOrganizationBootstrap(): void {
  const setSlug = useSetAtom(activeSlugAtom);

  useEffect(() => {
    if (!flags.organizations) return;
    let cancelled = false;

    AsyncStorage.getItem(STORAGE_KEY)
      .then((stored) => {
        if (cancelled || !stored) return;
        activeSlug = stored;
        setSlug(stored);
      })
      .catch(() => {
        // No stored choice is a perfectly good state: the backend falls back
        // to the caller's earliest organization.
      });

    return () => {
      cancelled = true;
    };
  }, [setSlug]);
}

export function useActiveOrganizationSlug(): string | null {
  return useAtomValue(activeSlugAtom);
}

interface OrganizationState {
  organizations: Organization[];
  active: Organization | null;
  loading: boolean;
  error: string | null;
}

const EMPTY: OrganizationState = {
  organizations: [],
  active: null,
  loading: flags.organizations,
  error: null,
};

export function useOrganizations() {
  const [state, setState] = useState<OrganizationState>(EMPTY);
  const [slug, setSlug] = useAtom(activeSlugAtom);
  const [attempt, setAttempt] = useState(0);

  // The fetch is inlined in the effect and every write happens after the
  // await, rather than calling a `load` callback from the effect body. React's
  // compiler rules reject the latter, and rightly: a synchronous setState
  // there renders twice before the first paint. `useResource` records the
  // same reasoning at greater length.
  useEffect(() => {
    if (!flags.organizations) return;
    let cancelled = false;

    (async () => {
      try {
        const payload = await apiData<OrganizationList>({
          url: routes.api.organizations.list(),
          errorMessage: 'Could not load organizations.',
        });
        if (cancelled) return;

        const organizations = payload?.organizations ?? [];
        setState({
          organizations,
          // Prefer the one this device chose. The server's own answer is the
          // fallback, and the first organization the fallback's fallback --
          // the same order `active_membership()` resolves in.
          active:
            organizations.find((o) => o.slug === activeSlug) ??
            organizations.find((o) => o.id === payload?.activeOrganizationId) ??
            organizations[0] ??
            null,
          loading: false,
          error: null,
        });
      } catch (error) {
        if (cancelled) return;
        setState({
          ...EMPTY,
          loading: false,
          error: error instanceof Error ? error.message : 'Could not load organizations.',
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  const switchTo = useCallback(
    async (organization: Organization) => {
      // Told to the server as well as stored here. The server call is what
      // updates a session, if this client ever has one, and it is also the
      // check that the caller really is a member -- it 404s if not.
      await apiData({
        url: routes.api.organizations.switch(organization.slug),
        method: 'POST',
        errorMessage: 'Could not switch organization.',
      });

      activeSlug = organization.slug;
      setSlug(organization.slug);
      setState((current) => ({ ...current, active: organization }));
      await AsyncStorage.setItem(STORAGE_KEY, organization.slug).catch(() => {
        // The switch holds for this launch either way.
      });
    },
    [setSlug],
  );

  const forget = useCallback(async () => {
    activeSlug = null;
    setSlug(null);
    await AsyncStorage.removeItem(STORAGE_KEY).catch(() => {});
  }, [setSlug]);

  return { ...state, slug, reload, switchTo, forget };
}
