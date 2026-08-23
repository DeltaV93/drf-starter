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
    },
    users: {
      me: () => join(BASE_URL, 'users/me/'),
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
    acceptInvitation: (token = ':token') => `/invitations/${token}`,
    passwordReset: '/reset-password',
    confirmPassword: (uid = ':uid', token = ':token') => `/confirm-password/${uid}/${token}`,
    verifyEmail: (uid = ':uid', token = ':token') => `/verify-email/${uid}/${token}`,
  },
} as const;
