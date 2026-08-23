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
