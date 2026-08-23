/**
 * Every backend path in one place.
 *
 * VITE_API_BASE_URL must NOT end with a slash -- see .env.example.
 */

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

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

export const routes = {
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
    account: {
      requestExport: () => join(BASE_URL, 'account/export/'),
      activity: () => join(BASE_URL, 'account/activity/'),
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
      subscribe: (stripePriceId: string) => join(BASE_URL, `billing/subscribe/${stripePriceId}/`),
      addAddon: (addonId: number) => join(BASE_URL, `billing/add-addon/${addonId}/`),
      cancel: () => join(BASE_URL, 'billing/cancel/'),
    },
  },
  app: {
    home: '/',
    login: '/login',
    signup: '/signup',
    profile: '/profile',
    subscription: '/subscription',
    organization: '/organization',
    security: '/security',
    files: '/files',
    acceptInvitation: (token = ':token') => `/invitations/${token}`,
    passwordReset: '/reset-password',
    confirmPassword: (uid = ':uid', token = ':token') => `/confirm-password/${uid}/${token}`,
    verifyEmail: (uid = ':uid', token = ':token') => `/verify-email/${uid}/${token}`,
  },
} as const;
