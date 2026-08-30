/**
 * Outbound MCP servers this account has connected.
 *
 * The mirror of the website's Connections page: a list of what the deployment
 * offers, with a switch per server.
 */

import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, List, Switch, Text, useTheme } from 'react-native-paper';

import type { ConnectableServer } from '@app/shared/types';

import { ErrorState } from '../../components/ErrorState';
import { FeatureOff } from '../../components/FeatureOff';
import { EmptyState, Screen, ScreenHeader } from '../../components/Screen';
import { apiData } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useErrorMessage } from '../../lib/useErrorMessage';
import { useResource } from '../../lib/useResource';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

export default function ConnectionsScreen() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const toast = useToast();
  const describe = useErrorMessage();
  const fetchServers = useCallback(
    () =>
      apiData<ConnectableServer[]>({ url: routes.api.mcp.servers() }),
    [],
  );
  const { data: servers, loading, error, reload } = useResource(fetchServers);

  async function toggle(server: ConnectableServer, enabled: boolean) {
    try {
      await apiData({
        url: routes.api.mcp.server(server.slug),
        method: 'PATCH',
        data: { enabled },
      });
      reload();
    } catch (thrown) {
      toast.error(describe(thrown, 'couldNotChangeConnection'));
    }
  }

  if (!flags.mcpClient) {
    return (
      <FeatureOff
        feature={t('connections')}
        clientFlag="EXPO_PUBLIC_MCP_CLIENT_ENABLED"
        serverFlag="MCP_CLIENT_ENABLED"
      />
    );
  }

  return (
    <Screen>
      <ScreenHeader title={t('connections')} subtitle={t('connectionsMobileHelp')} />

      {loading ? (
        <ActivityIndicator accessibilityLabel={t('loading')} />
      ) : error ? (
        <ErrorState message={describe(error, 'couldNotLoadConnections')} onRetry={reload} />
      ) : !servers || servers.length === 0 ? (
        <EmptyState message={t('mcpNoServers')} />
      ) : (
        servers.map((server) => (
          <List.Item
            key={server.slug}
            title={server.label}
            description={server.description}
            descriptionNumberOfLines={3}
            right={() => (
              <Switch
                value={server.enabled}
                onValueChange={(value) => toggle(server, value)}
                // Authorising a server that needs the user's own credential
                // is a redirect flow, which belongs where a browser can
                // complete it. Turning an authorised one off is safe here.
                disabled={server.requires_user_credential && !server.connected}
                accessibilityLabel={`${server.label}: ${t('mcpEnabled')}`}
              />
            )}
          />
        ))
      )}

      <Text
        variant="bodySmall"
        style={{ marginTop: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
      >
        {t('connectOnWebsite')}
      </Text>
    </Screen>
  );
}
