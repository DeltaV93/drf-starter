/**
 * Translations, from the same files the website reads.
 *
 * The only difference is how the language is detected. The website uses
 * `i18next-browser-languagedetector`, which reads `navigator.language` and
 * the URL -- neither of which exists here. `expo-localization` asks the
 * operating system instead, which is both more accurate and the only source a
 * phone has.
 */

import * as Localization from 'expo-localization';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import enTranslations from '@app/shared/locales/en.json';
import esTranslations from '@app/shared/locales/es.json';

/**
 * The best supported match for the device's preferred languages.
 *
 * `getLocales()` returns them in the user's own order of preference, so the
 * first one we have translations for is the right answer -- taking only
 * `[0]` would fall back to English for someone whose phone lists English
 * first and Spanish second, which is not what they asked for either.
 */
function deviceLanguage(): string {
  const supported = new Set(['en', 'es']);
  for (const locale of Localization.getLocales()) {
    const code = locale.languageCode;
    if (code && supported.has(code)) return code;
  }
  return 'en';
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: enTranslations },
    es: { translation: esTranslations },
  },
  lng: deviceLanguage(),
  fallbackLng: 'en',
  interpolation: {
    // React Native escapes nothing into markup, so i18next's own escaping is
    // both unnecessary and visible -- it would render `&#39;` in a Text node.
    escapeValue: false,
  },
});

export default i18n;
