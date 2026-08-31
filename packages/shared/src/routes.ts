/**
 * Every backend path in one place, for every client.
 *
 * This is a factory rather than a module-level constant because the two
 * clients discover their base URL by different mechanisms that cannot both
 * exist in one file. The website reads `import.meta.env.VITE_API_BASE_URL`,
 * which Vite substitutes at build time; React Native's Metro bundler does not
 * implement `import.meta` at all, so merely *mentioning* it here would break
 * the mobile bundle even on a line the website never reaches.
 *
 * So each app builds its own `routes` from `createRoutes(...)` and exports it
 * under the name its call sites already use. The paths themselves -- the part
 * that must never drift between the two -- live here once.
 */

/** The base every app falls back to: same-origin, behind a version prefix. */
export const DEFAULT_API_BASE_URL = '/api/v1';

/**
 * How a client with no session says which organization it is acting for.
 *
 * The browser never sends it -- its choice lives in the session cookie. The
 * mobile app has no session, so it names the organization on every request.
 * The backend resolves the value against the caller's own memberships, so it
 * is a preference rather than an authorization; `apps/organizations/context.py`
 * is the only place that reads it.
 */
export const ORGANIZATION_HEADER = 'X-Organization';

/**
 * Join URL segments with exactly one slash between them.
 *
 * Trailing slashes on the final segment are preserved on purpose: Django
 * routes end in a slash, and dropping it turns every POST into an
 * APPEND_SLASH redirect that loses the request body.
 */
function join(...segments: string[]): string {
  const [base, ...rest] = segments;
  return [base.replace(/\/+$/, ''), ...rest.map((s) => s.replace(/^\/+/, ''))]
    .filter(Boolean)
    .join('/');
}

/**
 * Client-side paths.
 *
 * Shared rather than web-only, and the reason is deep links. The backend
 * emails `${FRONTEND_URL}/verify-email/<uid>/<token>` and friends; when the
 * mobile app claims those URLs as universal links it has to recognise the
 * very same paths to route them to a screen. Two copies would mean an emailed
 * link that opens the app and then shows nothing.
 */
export const appRoutes = {
  home: '/',
  login: '/login',
  signup: '/signup',
  profile: '/profile',
  subscription: '/subscription',
  organization: '/organization',
  security: '/security',
  files: '/files',
  connections: '/connections',
  acceptInvitation: (token = ':token') => `/invitations/${token}`,
  passwordReset: '/reset-password',
  confirmPassword: (uid = ':uid', token = ':token') => `/confirm-password/${uid}/${token}`,
  verifyEmail: (uid = ':uid', token = ':token') => `/verify-email/${uid}/${token}`,
} as const;

/**
 * Build the route table against a base URL.
 *
 * `baseUrl` must NOT end with a slash -- see each app's `.env.example`.
 */
export function createRoutes(baseUrl: string = DEFAULT_API_BASE_URL) {
  const BASE_URL = baseUrl;

  return {
    api: {
      baseUrl: BASE_URL,
      health: () => join(BASE_URL, 'health/'),
      auth: {
        csrf: () => join(BASE_URL, 'auth/csrf/'),
        login: () => join(BASE_URL, 'auth/login/'),
        logout: () => join(BASE_URL, 'auth/logout/'),
        register: () => join(BASE_URL, 'auth/register/'),
        passwordReset: () => join(BASE_URL, 'auth/password-reset/'),
        passwordResetValidate: (uid: string, token: string) =>
          join(BASE_URL, `auth/password-reset/${uid}/${token}/`),
        passwordResetConfirm: () => join(BASE_URL, 'auth/password-reset/confirm/'),
        verifyEmail: () => join(BASE_URL, 'auth/verify-email/'),
        resendVerification: () => join(BASE_URL, 'auth/verify-email/resend/'),
        deleteAccount: () => join(BASE_URL, 'auth/delete-account/'),
        twoFactor: {
          status: () => join(BASE_URL, 'auth/2fa/'),
          enrol: () => join(BASE_URL, 'auth/2fa/enrol/'),
          confirm: () => join(BASE_URL, 'auth/2fa/confirm/'),
          disable: () => join(BASE_URL, 'auth/2fa/disable/'),
          recoveryCodes: () => join(BASE_URL, 'auth/2fa/recovery-codes/'),
          verify: () => join(BASE_URL, 'auth/2fa/verify/'),
        },
        // Bearer tokens, for clients that have no cookie jar. The website
        // never calls these -- it authenticates with the session cookie.
        token: {
          obtain: () => join(BASE_URL, 'auth/token/'),
          refresh: () => join(BASE_URL, 'auth/token/refresh/'),
          revoke: () => join(BASE_URL, 'auth/token/revoke/'),
          verifyTwoFactor: () => join(BASE_URL, 'auth/token/2fa/verify/'),
        },
      },
      social: {
        connections: () => join(BASE_URL, 'auth/social/connections/'),
        disconnect: (provider: string) =>
          join(BASE_URL, `auth/social/connections/${provider}/disconnect/`),
        // A full page navigation, not an XHR: the provider redirects the browser.
        begin: (provider: string) => join(BASE_URL, `auth/social/login/${provider}/`),
      },
      users: {
        me: () => join(BASE_URL, 'users/me/'),
      },
      mcp: {
        servers: () => join(BASE_URL, 'mcp/servers/'),
        server: (slug: string) => join(BASE_URL, `mcp/servers/${slug}/`),
      },
      account: {
        requestExport: () => join(BASE_URL, 'account/export/'),
        // Paginated with DRF's PageNumberPagination, so the page is a query
        // parameter rather than part of the path.
        activity: (page?: number) =>
          join(BASE_URL, `account/activity/${page && page > 1 ? `?page=${page}` : ''}`),
      },
      apiKeys: {
        list: () => join(BASE_URL, 'api-keys/'),
        revoke: (id: number) => join(BASE_URL, `api-keys/${id}/`),
      },
      files: {
        list: () => join(BASE_URL, 'files/'),
        detail: (id: number) => join(BASE_URL, `files/${id}/`),
        download: (id: number) => join(BASE_URL, `files/${id}/download/`),
      },
      // Asked before sign-in, and by a build that may be too old to sign in
      // at all -- so unlike everything else here it takes no credential.
      app: {
        upgrade: (platform: string, version: string) =>
          join(
            BASE_URL,
            `app/upgrade/?platform=${encodeURIComponent(platform)}` +
              `&version=${encodeURIComponent(version)}`,
          ),
      },
      // Push registration exists only for the mobile client, but it lives in
      // the same table so there is still one list of what the backend serves.
      push: {
        devices: () => join(BASE_URL, 'push/devices/'),
        device: (token: string) => join(BASE_URL, `push/devices/${encodeURIComponent(token)}/`),
      },
      organizations: {
        list: () => join(BASE_URL, 'organizations/'),
        active: () => join(BASE_URL, 'organizations/active/'),
        switch: (slug: string) => join(BASE_URL, `organizations/active/switch/${slug}/`),
        current: () => join(BASE_URL, 'organizations/current/'),
        members: () => join(BASE_URL, 'organizations/current/members/'),
        member: (id: number) => join(BASE_URL, `organizations/current/members/${id}/`),
        leave: () => join(BASE_URL, 'organizations/current/leave/'),
        invitations: () => join(BASE_URL, 'organizations/current/invitations/'),
        invitation: (id: number) => join(BASE_URL, `organizations/current/invitations/${id}/`),
        acceptInvitation: () => join(BASE_URL, 'organizations/invitations/accept/'),
      },
      billing: {
        plans: () => join(BASE_URL, 'billing/plans/'),
        subscription: () => join(BASE_URL, 'billing/subscription/'),
        subscribe: (stripePriceId: string) =>
          join(BASE_URL, `billing/subscribe/${stripePriceId}/`),
        addAddon: (addonId: number) => join(BASE_URL, `billing/add-addon/${addonId}/`),
        cancel: () => join(BASE_URL, 'billing/cancel/'),
      },
    },
    app: appRoutes,
  } as const;
}

export type Routes = ReturnType<typeof createRoutes>;
