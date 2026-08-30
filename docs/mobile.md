# The mobile app

An Expo app in `mobile/`, sharing the website's brand, route table and API
types through `packages/shared`. It talks to the same Django backend as the
website and signs in to the same accounts.

- [How it differs from the website](#how-it-differs-from-the-website)
- [Running it](#running-it)
- [Authentication](#authentication)
- [Deep links](#deep-links)
- [Push notifications](#push-notifications)
- [Feature flags](#feature-flags)
- [What the app deliberately does not do](#what-the-app-deliberately-does-not-do)
- [Building for the stores](#building-for-the-stores)

---

## How it differs from the website

Four things, and each one is a consequence of the client being native rather
than a browser on the same origin.

| | Website | Mobile |
|---|---|---|
| Credential | Session cookie + CSRF token | Bearer token pair, in the platform keystore |
| Active organization | Kept in the server session | Sent per request as `X-Organization` |
| UI library | MUI (Material Design 2) | React Native Paper (Material Design 3) |
| Emailed links | Open the SPA | Open the app, when it is installed |

Everything else is shared on purpose. `packages/shared` holds the brand
tokens, the backend route table, the API types, the response envelope and the
password rules; both apps import them, so a change lands in both.

---

## Running it

```bash
make fe-install          # one install at the workspace root
cp mobile/.env.example mobile/.env
make mobile-dev          # Expo dev server, then press i or a
```

The backend has to be reachable from the simulator, which is not the same as
being reachable from your machine:

| Where the app runs | `EXPO_PUBLIC_API_BASE_URL` |
|---|---|
| iOS simulator | `http://localhost:8000/api/v1` |
| Android emulator | `http://10.0.2.2:8000/api/v1` |
| A physical device | `http://<your LAN address>:8000/api/v1` |

A wrong value here looks exactly like the backend being down, so it is the
first thing to check.

`make test` and `make lint` cover the mobile app alongside everything else.

---

## Authentication

The backend gained bearer tokens for this app — added to the authentication
classes, never substituted for them, so the website's session auth is
untouched. See [Bearer tokens (mobile)](configuration.md#bearer-tokens-mobile)
for the settings.

```
POST /auth/token/                 credentials  → access + refresh (+ user)
POST /auth/token/2fa/verify/      challenge + code → access + refresh
POST /auth/token/refresh/         refresh → a new pair
POST /auth/token/revoke/          refresh → blacklisted; this is "sign out"
```

Three things about the client half are worth knowing before you change it.

**The pair lives in the keystore**, via `expo-secure-store` — the iOS keychain
and Keystore-backed storage on Android. Not AsyncStorage, which is a plaintext
file inside the app sandbox; a refresh token is a month-long credential.

**Refreshing is single-flight.** An access token expires while the app is
backgrounded, and the moment it comes forward every mounted screen fires at
once. Refreshing per 401 would spend the rotating refresh token several times
— the first spend invalidates it, so the rest fail and the user is thrown back
to the sign-in screen for no reason they can see. `src/lib/api.ts` starts one
refresh and makes everything else wait on it.

**Two-factor stops the token step.** With a second factor enrolled,
`/auth/token/` issues *no tokens*: it answers `two_factor_required` with a
short-lived signed challenge, which the verification screen exchanges for the
real pair. A client reading `access` unconditionally would store `undefined`
and believe itself signed in.

### Sharing the `Authorization` header

If `MCP_OAUTH_ENABLED` is on, two bearer schemes are live at once. They are
told apart by the `iss` claim: `MobileJWTAuthentication` runs first and
*declines* a token that is not ours, so `apps.mcp_oauth` still gets its turn.
Two authenticators that both raise cannot be chained in either order — see
`apps/authentication/authentication_token.py`.

---

## Deep links

The backend emails links into the web app — `/verify-email/<uid>/<token>`,
`/confirm-password/...`, `/invitations/<token>`. Configure the app's identity
and it publishes two association documents that make the operating system hand
those **same** URLs to the app when it is installed, and to the browser when it
is not. One email, both clients.

Set `MOBILE_IOS_APP_ID`, `MOBILE_ANDROID_PACKAGE` and
`MOBILE_ANDROID_SHA256_FINGERPRINTS` — see
[Mobile deep links](configuration.md#mobile-deep-links) — and confirm:

```bash
curl https://your-domain/.well-known/apple-app-site-association
curl https://your-domain/.well-known/assetlinks.json
```

Unset, each 404s. That is deliberate: an `applinks` document with no matching
detail tells iOS the association was checked and **refused**, and that answer
is cached.

Three things have to agree for a link to work, and none of them import each
other: the shared route table, `MOBILE_DEEP_LINK_PATHS` on the backend, and
the filenames under `mobile/src/app/`. `mobile/src/lib/__tests__/deepLinks.test.ts`
is what fails when they stop agreeing — nothing else would.

`webcredentials` is published alongside `applinks`, which is what lets iOS
offer a password saved for the website when signing in to the app. Android
gets the same through `delegate_permission/common.get_login_creds`.

---

## Push notifications

`PUSH_ENABLED` mounts `apps/push`, a registry of device tokens and nothing
more: it stores them and does not send anything, because which push service a
project uses is not a decision a template should make. Wire your sender to
`apps.push.models.Device`.

The app registers **after sign-in**, not at launch. The permission prompt is a
one-shot — someone who declines it on the first screen, before they know what
the app is, cannot be asked again from inside the app.

A token identifies an *installation*, not a person, so registering a token
that already exists moves it to whoever is registering. Without that, signing
in on a colleague's phone leaves it receiving your notifications.

### What the app does with one

`src/lib/push.ts` registers a foreground handler at module load — without one
the operating system shows nothing while the app is open, which reads as
"push is broken" rather than as a missing line. The banner shows; sound and
badge are off, because those are what people find intrusive from an app they
have just installed.

`usePushNavigation` opens the screen a notification names. The contract is one
key in `data`:

```json
{ "to": "ExponentPushToken[...]", "body": "Ada invited you", "data": { "path": "/organization" } }
```

It uses `useLastNotificationResponse` rather than a listener, and that is the
difference between working and half-working: the common case is a tap on an
app that was *not* running, where the response was delivered before any
listener could exist. The path goes through the same `safeRedirect` guard the
sign-in redirect uses — a payload is whatever reached the push service with
your credentials, not this app's code.

Rotation writes a blacklist row per refresh, swept nightly by
`CELERY_BEAT_SCHEDULE`. That needs a `celery -A template beat` process running
alongside the worker — see
[Bearer tokens (mobile)](configuration.md#bearer-tokens-mobile).

---

## Feature flags

Every `EXPO_PUBLIC_*_ENABLED` is the twin of a backend flag. Out of step, a
screen renders and then 404s against the API — the same failure the website
has, for the same reason. See [Mobile app](configuration.md#mobile-app) for
the full list.

Tabs and settings rows appear according to these flags. The routes still
exist when a flag is off (an emailed invitation has to keep working); the
screen explains which flag to set rather than showing a broken list.

---

## What the app deliberately does not do

Four things the website does that the app does not. Each is a decision, not an
oversight — if one is wrong for your product, change it knowingly.

**Buying a subscription.** Apple requires digital goods consumed in an app to
be sold through in-app purchase, and a Stripe checkout reached from the app is
grounds for rejection. The subscription screen is read-only and points at the
website. If you sell something the rules exempt — physical goods, or a B2B
service bought outside the app — a purchase flow is legitimate. If you sell
ordinary consumer software, adding IAP means an entitlement model the backend
does not have yet.

**Signing in with Google or LinkedIn.** The web flow is a browser redirect
that ends in a session cookie, which is no use to a token client. Doing it
natively needs `expo-auth-session` plus a backend endpoint that exchanges a
provider authorization code for a token pair. The app lists and unlinks
existing connections; linking a new one happens on the website.

**Creating an API key.** The secret is shown exactly once and belongs
somewhere it can be pasted into a terminal. Listing and revoking are here.

**Deleting your account.** Irreversible, and not a thing to put behind a
mis-tap on a phone.

---

## Building for the stores

Binaries are built with [EAS](https://docs.expo.dev/build/introduction/), not
in this repository's CI — a build needs signing material, which a pull request
has no business holding. CI bundles the app with Metro instead, which is what
catches an import that only resolves on someone's laptop.

`mobile/eas.json` has three profiles:

| Profile | What it is for |
|---|---|
| `development` | A development client for use with `make mobile-dev`. Points at `localhost` by default — override `EXPO_PUBLIC_API_BASE_URL` for a device on your LAN. |
| `preview` | An internal build, and an iOS simulator build, for sharing before release. |
| `production` | The store build. `autoIncrement` handles the build number. |

```bash
npx eas build --profile preview --platform ios
```

### Icon and splash

`npm run assets --workspace mobile` regenerates `mobile/assets/` from the
brand tokens, so a re-brand reaches the home screen too — the one place a
stale colour is impossible to miss and easiest to forget, because nothing in
the build reads an icon's contents.

The generator writes PNGs by hand rather than pulling in `sharp` or
ImageMagick: on a template, an image toolchain is the difference between "run
this" and "first, set up an image toolchain". The mark it draws is a
placeholder — a rounded square, not a logo. Overwrite the files, or edit
`mobile/scripts/generate-assets.mjs`, when you have real artwork.

### Crash reporting

`EXPO_PUBLIC_SENTRY_DSN` turns on Sentry, mirroring the backend's setup: off
unless configured, never during a test run, and personal information off by
default. See [Mobile app](configuration.md#mobile-app).

Before the first build, set the real identifiers in `mobile/app.config.ts`
(`ios.bundleIdentifier`, `android.package`) and keep them in step with the
backend:

```
MOBILE_IOS_APP_ID       = <appleTeamId>.<ios.bundleIdentifier>
MOBILE_ANDROID_PACKAGE  = <android.package>
MOBILE_APP_SCHEME       = <scheme>
```

`EXPO_PUBLIC_WEB_URL` decides the domain the app claims universal links on. It
has to be `https://` — a `http://localhost` value publishes no
`associatedDomains` at all, which is correct for development and would be a
silent failure in production.
