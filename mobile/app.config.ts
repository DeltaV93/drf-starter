/**
 * The Expo app manifest, as code rather than JSON.
 *
 * It has to be code because two of the values are deployment-specific and
 * belong in the environment: the domain the app claims links on, and the
 * identifiers that domain's association documents have to name back. A static
 * app.json would mean editing a checked-in file per deployment, and the
 * failure mode of getting it wrong is silent -- links simply keep opening the
 * browser.
 *
 * Keep these in step with the backend:
 *
 *   MOBILE_IOS_APP_ID       = <ios.appleTeamId>.<ios.bundleIdentifier>
 *   MOBILE_ANDROID_PACKAGE  = <android.package>
 *   MOBILE_APP_SCHEME       = <scheme>
 *
 * `docs/mobile.md` has the checklist.
 */

import type { ExpoConfig } from 'expo/config';

import { darkPalette, identity, lightPalette } from '@app/shared/brand';

/** The host the app claims universal links on, derived from the web URL. */
function webHost(): string | null {
  const raw = process.env.EXPO_PUBLIC_WEB_URL;
  if (!raw) return null;
  try {
    const { hostname, protocol } = new URL(raw);
    // Universal links are HTTPS-only, and localhost can never be verified.
    // Returning null here is what keeps a development build from shipping an
    // associatedDomains entry that can only ever fail.
    if (protocol !== 'https:') return null;
    return hostname;
  } catch {
    return null;
  }
}

const host = webHost();

const config: ExpoConfig = {
  name: identity.name,
  slug: 'drf-starter',
  version: '0.1.0',
  orientation: 'portrait',
  // Answers `drfstarter://...`. Must match MOBILE_APP_SCHEME on the backend.
  // Development relies on this: there is no verified domain on a simulator.
  scheme: 'drfstarter',
  // Follow the system setting. The palette swap is in src/theme/.
  userInterfaceStyle: 'automatic',
  // Generated from the brand tokens by `npm run assets`. Placeholders on
  // purpose -- overwrite them when you have real artwork.
  icon: './assets/icon.png',
  ios: {
    bundleIdentifier: 'com.example.drfstarter',
    supportsTablet: true,
    // Every permission the app can ask for needs a sentence saying why, and
    // iOS treats a missing one as a hard error: App Review rejects the build,
    // and on a device the request does not prompt -- it crashes. Only the
    // permissions this app actually requests are listed; declaring one the
    // app never uses is its own review finding.
    infoPlist: {
      NSPhotoLibraryUsageDescription:
        'Lets you attach a photo from your library to your account.',
      // No NSCameraUsageDescription and no NSFaceIDUsageDescription: the
      // app opens the photo library but never a camera, and there is no
      // biometric unlock. Add them alongside the feature, not before it.
    },
    // `applinks` claims the emailed URLs; `webcredentials` is what lets iOS
    // offer a password saved for the website when signing in to the app.
    // Both need the matching half published at
    // https://<host>/.well-known/apple-app-site-association.
    associatedDomains: host
      ? [`applinks:${host}`, `webcredentials:${host}`]
      : undefined,
  },
  android: {
    package: 'com.example.drfstarter',
    // Named explicitly rather than left to autolinking, which adds the union
    // of what every installed library *might* use. An app asking for more
    // than it needs is a review finding on Play too, and an unexplained
    // permission in the store listing costs installs.
    permissions: [
      'android.permission.READ_MEDIA_IMAGES',
      'android.permission.POST_NOTIFICATIONS',
      'android.permission.INTERNET',
    ],
    blockedPermissions: [
      // Pulled in by expo-image-picker's manifest; the app never opens a
      // camera or records audio.
      'android.permission.CAMERA',
      'android.permission.RECORD_AUDIO',
    ],
    adaptiveIcon: {
      // Transparent foreground over a brand fill: Android crops this to
      // whatever shape the launcher uses, so anything at the edges is lost.
      foregroundImage: './assets/adaptive-icon.png',
      backgroundColor: lightPalette.primary.main,
    },
    intentFilters: host
      ? [
          {
            action: 'VIEW',
            // `autoVerify` is the difference between an App Link, which opens
            // the app directly, and a plain deep link, which shows a
            // disambiguation dialog. It requires assetlinks.json to verify.
            autoVerify: true,
            data: [{ scheme: 'https', host }],
            category: ['BROWSABLE', 'DEFAULT'],
          },
        ]
      : undefined,
  },
  web: {
    favicon: './assets/favicon.png',
  },
  plugins: [
    'expo-router',
    [
      'expo-splash-screen',
      {
        image: './assets/splash-icon.png',
        imageWidth: 160,
        backgroundColor: lightPalette.background.default,
        dark: { backgroundColor: darkPalette.background.default },
      },
    ],
    'expo-secure-store',
    'expo-localization',
    [
      'expo-notifications',
      {
        // The tint of the small status-bar icon on Android. Read from the
        // brand rather than repeated -- this file is outside `src/`, which is
        // exactly the kind of place a stray hex code survives a rebrand.
        color: lightPalette.primary.main,
      },
    ],
  ],
  experiments: {
    // Deliberately off. Typed routes generate `.expo/types` at dev-server
    // start, and `tsc --noEmit` in CI would then fail on a checkout where no
    // one has run `expo start` -- a typecheck that depends on having served
    // the app is not a typecheck.
    typedRoutes: false,
  },
};

export default config;
