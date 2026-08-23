/// <reference types="vite/client" />

/** Typed access to the VITE_* variables this app reads. See .env.example. */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_PROXY_TARGET?: string;
  readonly VITE_STRIPE_ENABLED?: string;
  readonly VITE_ORGANIZATIONS_ENABLED?: string;
  readonly VITE_STRIPE_PUBLISHABLE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
