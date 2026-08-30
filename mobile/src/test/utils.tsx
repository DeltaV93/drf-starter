/**
 * Rendering a screen the way the app renders it.
 *
 * Two providers, and leaving either out fails in a way that looks like a bug
 * in the screen rather than in the test. Without the app's theme,
 * `theme.spacing(...)` is not a function -- Paper's default theme has no such
 * key. Without safe-area metrics, `useSafeAreaInsets` has no provider to read
 * and every `Screen` throws.
 *
 * The website has the same helper, for the same reason, in `src/test/utils.tsx`.
 */

import { render, type RenderOptions } from '@testing-library/react-native';
import type { ReactElement, ReactNode } from 'react';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider, type Metrics } from 'react-native-safe-area-context';

import { PaperIcon } from '../components/PaperIcon';
// Initialises the real i18next instance. Without it `useTranslation` warns
// and `t('username')` returns the key, so every query by visible text fails
// on a screen that is working perfectly.
import '../i18n';
import { lightTheme } from '../theme/paper';

/** A phone with a notch and a home indicator: the case with insets to get wrong. */
const METRICS: Metrics = {
  frame: { x: 0, y: 0, width: 390, height: 844 },
  insets: { top: 47, left: 0, right: 0, bottom: 34 },
};

function Providers({ children }: { children: ReactNode }) {
  return (
    <SafeAreaProvider initialMetrics={METRICS}>
      <PaperProvider theme={lightTheme} settings={{ icon: PaperIcon }}>
        {children}
      </PaperProvider>
    </SafeAreaProvider>
  );
}

/**
 * Render a screen with the providers the app gives it.
 *
 * Returns a promise, because `render` does: React Native Testing Library 14
 * renders concurrently, so the tree is not mounted when the call returns.
 * Forgetting the `await` leaves a Promise where the queries should be, and
 * the error names `getByLabelText` rather than the missing keyword.
 */
export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  return render(ui, { wrapper: Providers, ...options });
}

export * from '@testing-library/react-native';
