/**
 * The one Snackbar the whole app shares.
 *
 * Only the oldest queued message is shown. A phone has no room for a stack,
 * and Paper's Snackbar sits exactly where the tab bar is -- two at once would
 * cover it entirely.
 */

import { useTranslation } from 'react-i18next';
import { Snackbar, useTheme } from 'react-native-paper';

import { useToast, useToasts, type ToastSeverity } from '../store/toast';
import type { AppTheme } from '../theme/paper';

export function Toast() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const toasts = useToasts();
  const { dismiss } = useToast();

  const current = toasts[0];

  // Colours by role rather than by literal, so a re-brand moves these too.
  const background: Record<ToastSeverity, string> = {
    success: theme.colors.primary,
    error: theme.colors.error,
    warning: theme.colors.tertiary,
    info: theme.colors.inverseSurface,
  };

  return (
    <Snackbar
      // Keyed by id so a second message replaces the first cleanly rather
      // than reusing the open Snackbar's dismissal timer.
      key={current?.id}
      visible={Boolean(current)}
      onDismiss={() => current && dismiss(current.id)}
      duration={current?.duration ?? 5000}
      style={current ? { backgroundColor: background[current.severity] } : undefined}
      action={{ label: t('cancel'), onPress: () => current && dismiss(current.id) }}
      // A failure announced only in colour is not announced at all. An
      // error interrupts whatever the screen reader is saying; everything
      // else waits for a pause, which is the right trade for a confirmation
      // nobody is waiting on.
      //
      // React Native has no `status` role, so the distinction is carried by
      // the live region alone for the non-error case.
      accessibilityRole={current?.severity === 'error' ? 'alert' : undefined}
      accessibilityLiveRegion={current?.severity === 'error' ? 'assertive' : 'polite'}
    >
      {current?.message ?? ''}
    </Snackbar>
  );
}
