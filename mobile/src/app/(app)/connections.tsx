/**
 * Outbound MCP servers this account has connected.
 *
 * The mirror of the website's Connections page: a list of what the deployment
 * offers, with a switch per server.
 */

import { useCallback } from 'react';
import { ActivityIndicator, List, Switch, Text, useTheme } from 'react-native-paper';

import type { ConnectableServer } from '@app/shared/types';

import { EmptyState, Screen, ScreenHeader } from '../../components/Screen';
import { ApiError, apiData } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useResource } from '../../lib/useResource';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

export default function ConnectionsScreen() {
  const theme = useTheme<AppTheme>();
  const toast = useToast();
  const fetchServers = useCallback(
    () =>
      apiData<ConnectableServer[]>({
        url: routes.api.mcp.servers(),
        errorMessage: 'Could not load connections.',
      }),
    [],
  );
  const { data: servers, loading, error, reload } = useResource(fetchServers);

  async function toggle(server: ConnectableServer, enabled: boolean) {
    try {
      await apiData({
        url: routes.api.mcp.server(server.slug),
        method: 'PATCH',
        data: { enabled },
        errorMessage: 'Could not change that connection.',
      });
      reload();
    } catch (thrown) {
      toast.error(
        thrown instanceof ApiError ? thrown.message : 'Could not change that connection.',
      );
    }
  }

  if (!flags.mcpClient) {
    return (
      <Screen>
        <ScreenHeader
          title="Connections are off"
          subtitle="Set EXPO_PUBLIC_MCP_CLIENT_ENABLED, and MCP_CLIENT_ENABLED on the backend."
        />
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader
        title="Connections"
        subtitle="Servers this account can reach on your behalf."
      />

      {loading ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : error ? (
        <EmptyState message={error} />
      ) : !servers || servers.length === 0 ? (
        <EmptyState message="No servers are offered by this deployment." />
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
                accessibilityLabel={`${server.label} enabled`}
              />
            )}
          />
        ))
      )}

      <Text
        variant="bodySmall"
        style={{ marginTop: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
      >
        Connecting a server that needs your own credential happens on the
        website, where the provider’s sign-in page can complete.
      </Text>
    </Screen>
  );
}
