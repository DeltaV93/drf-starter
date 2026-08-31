/**
 * The screen shown instead of the app when this build is too old to run.
 *
 * It replaces the whole tree rather than sitting over it as a dialog. A
 * dismissible block is not a block, and a modal above a live app is one
 * accidental tap away from the screens the gate exists to keep people out of.
 *
 * There is deliberately no "continue anyway". If a build is bad enough to
 * refuse, offering a way past it means the people most likely to take it are
 * the ones the refusal was for.
 */

import * as Linking from 'expo-linking';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { Button, Text, useTheme } from 'react-native-paper';

import type { UpgradeCheck } from '@app/shared/types';

import type { AppTheme } from '../theme/paper';

interface UpgradeRequiredProps {
  check: UpgradeCheck;
}

export function UpgradeRequired({ check }: UpgradeRequiredProps) {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();

  return (
    <View
      style={{
        flex: 1,
        justifyContent: 'center',
        padding: theme.spacing(3),
        backgroundColor: theme.colors.background,
      }}
    >
      <Text variant="headlineSmall" style={{ marginBottom: theme.spacing(1) }}>
        {t('upgradeRequiredTitle')}
      </Text>

      {/* Whatever the admin wrote wins: during an incident the specific
          sentence is worth more than the translated generic one. */}
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
        {check.message || t('upgradeRequiredBody')}
      </Text>

      {check.store_url ? (
        <Button
          mode="contained"
          onPress={() => {
            void Linking.openURL(check.store_url);
          }}
          style={{ marginTop: theme.spacing(3) }}
        >
          {t('upgradeAction')}
        </Button>
      ) : (
        // No listing configured. Saying so beats a button that does nothing,
        // and beats pretending there is nothing to do.
        <Text
          variant="bodySmall"
          style={{ marginTop: theme.spacing(3), color: theme.colors.onSurfaceVariant }}
        >
          {t('upgradeNoStoreLink')}
        </Text>
      )}
    </View>
  );
}
