/** The envelope every backend endpoint answers with. See utils/api_utils.py. */
export interface ApiEnvelope<T = unknown> {
  status: 'success' | 'error';
  message?: string;
  data?: T;
  errors?: Record<string, string[] | string>;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  phone_number: string;
  account_type: string;
  role: string;
  email_verified: boolean;
  date_joined: string;
}

export interface AuthPayload {
  user: User;
  csrfToken: string;
}

export interface SubscriptionPlan {
  id: number;
  name: string;
  stripe_price_id: string;
  user_limit: number;
  price: string;
}

export interface Subscription {
  id: number;
  plan: SubscriptionPlan;
  status: string;
  current_period_end: string;
  is_current: boolean;
}

export type OrganizationRole = 'OWNER' | 'ADMIN' | 'MEMBER';

export interface Organization {
  id: number;
  name: string;
  slug: string;
  /** The requesting user's role. Null when the endpoint did not supply it. */
  role: OrganizationRole | null;
  member_count: number;
  created_at: string;
}

export interface OrganizationList {
  organizations: Organization[];
  activeOrganizationId: number | null;
}

export interface OrganizationMember {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: OrganizationRole;
  /** Removing or demoting this member would leave the organization ownerless. */
  is_last_owner: boolean;
  created_at: string;
}

export interface OrganizationInvitation {
  id: number;
  email: string;
  role: OrganizationRole;
  invited_by_email: string | null;
  expires_at: string;
  is_expired: boolean;
  created_at: string;
}

export interface TwoFactorStatus {
  enabled: boolean;
  /** Enrolment started but never confirmed with a code. */
  pending: boolean;
  recovery_codes_remaining: number;
}

export interface ApiKey {
  id: number;
  name: string;
  /** Not secret. Identifies the key in a listing or a log. */
  prefix: string;
  scope: 'read' | 'write';
  expires_at: string | null;
  revoked_at: string | null;
  last_used_at: string | null;
  created_at: string;
  is_expired: boolean;
  is_revoked: boolean;
}

/** Only ever present in the response that created the key. */
export interface CreatedApiKey extends ApiKey {
  key: string;
}

export interface Attachment {
  id: number;
  purpose: string;
  original_name: string;
  content_type: string;
  size_bytes: number;
  visibility: 'private' | 'public';
  download_url: string;
  created_at: string;
}

export interface SocialConnection {
  provider: string;
  uid: string;
  connected_at: string;
}

/** One row of the append-only audit log, scoped to the reader's own actions. */
export interface AuditEvent {
  id: number;
  action: string;
  actor_label: string;
  target: string;
  ip_address: string | null;
  /** Allow-listed per action -- never a request body. */
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditEventPage {
  results: AuditEvent[];
  count: number;
  next: string | null;
  previous: string | null;
}

export interface SocialConnections {
  providers: SocialConnection[];
  available: string[];
  /** False means the last provider cannot be unlinked -- nothing else to sign in with. */
  has_usable_password: boolean;
}

/**
 * One outbound MCP server this user could connect, with their own connection
 * state folded in.
 *
 * Everything except `connected`, `enabled` and `last_used_at` comes from a
 * module in the backend repository, not from a row -- so none of it can be
 * changed by a request, and the UI treats it as read-only.
 */
export interface ConnectableServer {
  slug: string;
  label: string;
  description: string;
  transport: string;
  /** True when the token has to be this user's own rather than the deployment's. */
  requires_user_credential: boolean;
  /** The curated surface, or null for "whatever the server offers". */
  allowed_tools: string[] | null;
  connected: boolean;
  enabled: boolean;
  last_used_at: string | null;
}

// ---------------------------------------------------------------------------
// Bearer-token authentication
//
// Used by clients with no cookie jar -- the mobile app. The website never
// sees these shapes: it authenticates with the session cookie and its login
// response carries `csrfToken` instead.
// ---------------------------------------------------------------------------

export interface TokenPair {
  access: string;
  refresh: string;
  /** Seconds until `access` expires, so a client can refresh ahead of a 401. */
  access_expires_in: number;
}

/** A completed token login. */
export interface TokenAuthPayload extends TokenPair {
  user: User;
}

/**
 * What `auth/token/` answers with.
 *
 * With two-factor enrolled the password step issues no tokens at all. It
 * answers `two_factor_required` plus a short-lived challenge the second step
 * exchanges for the real pair -- so a client that read `access` unconditionally
 * would store `undefined` and believe itself signed in.
 */
export interface TokenChallenge {
  two_factor_required: true;
  challenge: string;
}

export type TokenResponse = TokenAuthPayload | TokenChallenge;

export function isTokenChallenge(response: TokenResponse): response is TokenChallenge {
  return (response as TokenChallenge).two_factor_required === true;
}

/** A device registered to receive push notifications. */
export interface PushDevice {
  id: number;
  token: string;
  platform: 'ios' | 'android' | 'web';
  device_name: string;
  is_active: boolean;
  last_seen_at: string;
  created_at: string;
}
