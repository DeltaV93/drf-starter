/**
 * The organization the session is acting for.
 *
 * The server decides this -- it lives in the session, not in localStorage --
 * so the client only mirrors it. Switching is a request, not a state update:
 * every API call is scoped by what the server remembers, and a client-side
 * "active org" that disagreed with it would be a bug factory.
 */

import { useCallback, useEffect, useState } from 'react';

import { apiCall, apiData } from '../lib/api';
import { routes } from '../lib/routes';
import type { Organization, OrganizationList } from '../lib/types';

export const ORGANIZATIONS_ENABLED = import.meta.env.VITE_ORGANIZATIONS_ENABLED === 'true';

interface OrganizationState {
  organizations: Organization[];
  active: Organization | null;
  loading: boolean;
  error: string | null;
}

/** Also the resting state when the feature is switched off. */
const EMPTY: OrganizationState = {
  organizations: [],
  active: null,
  loading: ORGANIZATIONS_ENABLED,
  error: null,
};

async function fetchOrganizations(): Promise<OrganizationState> {
  const payload = await apiData<OrganizationList>({
    url: routes.api.organizations.list(),
    errorMessage: 'Could not load organizations.',
  });
  const organizations = payload?.organizations ?? [];
  return {
    organizations,
    // Fall back to the first one so a user with a single organization never
    // has to pick it; the server does the same when the session names none.
    active:
      organizations.find((o) => o.id === payload?.activeOrganizationId) ??
      organizations[0] ??
      null,
    loading: false,
    error: null,
  };
}

function toErrorState(error: unknown): OrganizationState {
  return {
    ...EMPTY,
    loading: false,
    error: error instanceof Error ? error.message : 'Could not load organizations.',
  };
}

export function useOrganizations() {
  const [state, setState] = useState<OrganizationState>(EMPTY);

  // The async work is inlined here rather than called out to a useCallback,
  // matching useAuthBootstrap: it keeps setState off the effect's synchronous
  // path, and the cancelled flag stops a slow response landing on a component
  // that has since unmounted.
  useEffect(() => {
    if (!ORGANIZATIONS_ENABLED) return;

    let cancelled = false;
    (async () => {
      try {
        const next = await fetchOrganizations();
        if (!cancelled) setState(next);
      } catch (error) {
        if (!cancelled) setState(toErrorState(error));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  /** Re-read after a mutation. Not called from an effect, so it may show the spinner. */
  const refresh = useCallback(async () => {
    if (!ORGANIZATIONS_ENABLED) return;
    setState((previous) => ({ ...previous, loading: true, error: null }));
    try {
      setState(await fetchOrganizations());
    } catch (error) {
      setState(toErrorState(error));
    }
  }, []);

  const switchTo = useCallback(
    async (slug: string) => {
      await apiCall({
        method: 'post',
        url: routes.api.organizations.switch(slug),
        errorMessage: 'Could not switch organization.',
      });
      // Re-read rather than patching locally: the server is the source of
      // truth for which organization the session is now acting for.
      await refresh();
    },
    [refresh],
  );

  return { ...state, refresh, switchTo };
}
