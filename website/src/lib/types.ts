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
