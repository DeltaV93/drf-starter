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
