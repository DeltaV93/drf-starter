/**
 * Connecting the MCP servers this deployment offers.
 *
 * Only mounted when VITE_MCP_CLIENT_ENABLED matches the backend's
 * MCP_CLIENT_ENABLED -- see App.tsx.
 *
 * The list comes from the server and is not editable here. Which servers
 * exist, where they live and which of their tools are allowed all live in
 * modules in the backend repository, so this page can offer a choice between
 * them and nothing else. What it *can* do is hand over a token and turn a
 * connection on or off.
 */

import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { apiCall, apiData } from '../../lib/api';
import { routes } from '../../lib/routes';
import type { ConnectableServer } from '../../lib/types';
import { useToast } from '../../store/toast';

export default function ConnectionsPage() {
  const { t } = useTranslation();
  const toast = useToast();

  const [servers, setServers] = useState<ConnectableServer[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [connecting, setConnecting] = useState<ConnectableServer | null>(null);
  const [credential, setCredential] = useState('');
  const [busy, setBusy] = useState(false);

  const fetchServers = useCallback(
    () => apiData<ConnectableServer[]>({ url: routes.api.mcp.servers() }),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchServers();
        if (!cancelled) setServers(next ?? []);
      } catch (error) {
        if (!cancelled) toast.error(error instanceof Error ? error.message : t('genericError'));
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchServers, toast, t]);

  const refresh = async () => setServers((await fetchServers()) ?? []);

  const connect = async () => {
    if (!connecting) return;
    setBusy(true);
    try {
      await apiCall({
        method: 'put',
        url: routes.api.mcp.server(connecting.slug),
        data: { credential, enabled: true },
      });
      await refresh();
      toast.success(t('mcpConnected'));
      setConnecting(null);
      // Cleared here as well as on open: the token should not sit in memory
      // behind a closed dialog.
      setCredential('');
    } catch (error) {
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        (error instanceof Error ? error.message : t('genericError'));
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async (server: ConnectableServer) => {
    try {
      await apiCall({ method: 'delete', url: routes.api.mcp.server(server.slug) });
      await refresh();
      toast.success(t('mcpDisconnected'));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  const setEnabled = async (server: ConnectableServer, enabled: boolean) => {
    try {
      await apiCall({
        method: 'put',
        url: routes.api.mcp.server(server.slug),
        data: { enabled },
      });
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  if (!loaded) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Typography variant="h4" gutterBottom>
        {t('connections')}
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        {t('connectionsHelp')}
      </Typography>

      {servers.length === 0 ? (
        <Paper sx={{ p: 3 }}>
          <Typography color="text.secondary">{t('mcpNoServers')}</Typography>
        </Paper>
      ) : (
        <Stack spacing={2}>
          {servers.map((server) => (
            <Paper key={server.slug} sx={{ p: 3 }}>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={2}
                sx={{
                  justifyContent: 'space-between',
                  alignItems: { xs: 'flex-start', sm: 'center' },
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="h6">{server.label}</Typography>
                  {server.description && (
                    <Typography variant="body2" color="text.secondary">
                      {server.description}
                    </Typography>
                  )}

                  {/* What the model will be able to do, before anyone agrees
                      to it. A connection screen that does not say this is
                      asking for consent to something unnamed. */}
                  <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {server.allowed_tools === null ? (
                      <Chip size="small" color="warning" label={t('mcpAllTools')} />
                    ) : (
                      server.allowed_tools.map((tool) => (
                        <Chip key={tool} size="small" variant="outlined" label={tool} />
                      ))
                    )}
                  </Box>
                </Box>

                <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                  {server.connected && (
                    <Switch
                      checked={server.enabled}
                      onChange={(event) => void setEnabled(server, event.target.checked)}
                      slotProps={{ input: { 'aria-label': t('mcpEnabled') } }}
                    />
                  )}
                  {server.connected ? (
                    <Button color="error" onClick={() => void disconnect(server)}>
                      {t('mcpDisconnect')}
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      onClick={() => {
                        setCredential('');
                        setConnecting(server);
                      }}
                    >
                      {t('mcpConnect')}
                    </Button>
                  )}
                </Stack>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}

      <Dialog open={connecting !== null} onClose={() => setConnecting(null)} fullWidth>
        <DialogTitle>{t('mcpConnectTitle', { name: connecting?.label ?? '' })}</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            {connecting?.requires_user_credential
              ? t('mcpCredentialRequired')
              : t('mcpCredentialOptional')}
          </DialogContentText>
          <TextField
            autoFocus
            fullWidth
            type="password"
            label={t('mcpCredential')}
            value={credential}
            onChange={(event) => setCredential(event.target.value)}
            // Stored encrypted and never returned by the API, so this field
            // starts empty even for a server that is already connected.
            helperText={t('mcpCredentialHelp')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConnecting(null)}>{t('cancel')}</Button>
          <Button variant="contained" disabled={busy} onClick={() => void connect()}>
            {busy ? t('mcpConnecting') : t('mcpConnect')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
