/**
 * A failed load, with a way out of it.
 *
 * The way out is the point. Every list on a phone can fail for a reason that
 * has nothing to do with the app -- a tunnel, a lift, a hotel wifi splash
 * page -- and the previous version of these screens showed the message and
 * stopped, leaving no way to try again except backing out of the screen and
 * returning to it.
 *
 * Announced as an alert so a screen reader says what happened rather than
 * leaving someone on a silent screen wondering whether it is still loading.
 */

import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { Button, Text, useTheme } from 'react-native-paper';

import type { AppTheme } from '../theme/paper';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();

  return (
    <View
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
      style={{ alignItems: 'center', padding: theme.spacing(3), gap: theme.spacing(2) }}
    >
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
        {message}
      </Text>
      {onRetry ? (
        <Button mode="outlined" onPress={onRetry} icon="refresh">
          {t('retry')}
        </Button>
      ) : null}
    </View>
  );
}
