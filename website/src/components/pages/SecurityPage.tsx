/**
 * Account security: two-factor, API keys, connected providers, data export.
 *
 * One page rather than four, because each section is small and they are all
 * things people look for in the same place. Every section renders only when
 * its backend flag is on -- with them out of step the calls 404.
 */

import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { apiCall, apiData } from '../../lib/api';
import { routes } from '../../lib/routes';
import type {
  ApiKey,
  AuditEventPage,
  CreatedApiKey,
  SocialConnections,
  TwoFactorStatus,
} from '@app/shared/types';
import { useToast } from '../../store/toast';

const TWO_FACTOR_ENABLED = import.meta.env.VITE_TWO_FACTOR_ENABLED === 'true';
const API_KEYS_ENABLED = import.meta.env.VITE_API_KEYS_ENABLED === 'true';
const SOCIAL_AUTH_ENABLED = import.meta.env.VITE_SOCIAL_AUTH_ENABLED === 'true';
const AUDIT_LOG_ENABLED = import.meta.env.VITE_AUDIT_LOG_ENABLED === 'true';

/** Shown once, and never retrievable afterwards. */
function ShownOnce({ title, values, onClose }: {
  title: string;
  values: string[];
  onClose: () => void;
}) {
  const { t } = useTranslation();

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>{t('shownOnceWarning')}</DialogContentText>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={0.5}>
            {values.map((value) => (
              <Typography key={value} sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                {value}
              </Typography>
            ))}
          </Stack>
        </Paper>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => void navigator.clipboard?.writeText(values.join('\n'))}>
          {t('copy')}
        </Button>
        <Button variant="contained" onClick={onClose}>
          {t('savedIt')}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function TwoFactorSection() {
  const { t } = useTranslation();
  const toast = useToast();

  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [provisioningUri, setProvisioningUri] = useState<string | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);

  const fetchStatus = useCallback(
    () => apiData<TwoFactorStatus>({ url: routes.api.auth.twoFactor.status() }),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchStatus();
        if (!cancelled) setStatus(next ?? null);
      } catch {
        // A visitor without the feature enabled is not an error worth shouting about.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchStatus]);

  const reload = async () => setStatus((await fetchStatus()) ?? null);

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    try {
      await work();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    } finally {
      setBusy(false);
    }
  };

  const beginEnrol = () =>
    run(async () => {
      const data = await apiData<{ provisioning_uri: string }>({
        method: 'post',
        url: routes.api.auth.twoFactor.enrol(),
        data: { password },
      });
      setProvisioningUri(data?.provisioning_uri ?? null);
      setPassword('');
    });

  const confirmEnrol = () =>
    run(async () => {
      const data = await apiData<{ recovery_codes: string[] }>({
        method: 'post',
        url: routes.api.auth.twoFactor.confirm(),
        data: { code },
      });
      setRecoveryCodes(data?.recovery_codes ?? []);
      setProvisioningUri(null);
      setCode('');
      await reload();
    });

  const disable = () =>
    run(async () => {
      await apiCall({
        method: 'post',
        url: routes.api.auth.twoFactor.disable(),
        data: { password },
      });
      setPassword('');
      toast.success(t('twoFactorDisabled'));
      await reload();
    });

  const regenerate = () =>
    run(async () => {
      const data = await apiData<{ recovery_codes: string[] }>({
        method: 'post',
        url: routes.api.auth.twoFactor.recoveryCodes(),
        data: { password },
      });
      setRecoveryCodes(data?.recovery_codes ?? []);
      setPassword('');
      await reload();
    });

  if (status === null) return null;

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        {t('twoFactorTitle')}
      </Typography>

      {recoveryCodes && (
        <ShownOnce
          title={t('recoveryCodes')}
          values={recoveryCodes}
          onClose={() => setRecoveryCodes(null)}
        />
      )}

      {status.enabled ? (
        <>
          <Alert severity="success" sx={{ mb: 2 }}>
            {t('twoFactorOn', { count: status.recovery_codes_remaining })}
          </Alert>
          {/* Re-authentication: a session left open on a shared machine must
              not be enough to remove the factor protecting the account. */}
          <TextField
            fullWidth
            size="small"
            type="password"
            label={t('confirmWithPassword')}
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            sx={{ mb: 2 }}
          />
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" disabled={busy || !password} onClick={() => void regenerate()}>
              {t('regenerateCodes')}
            </Button>
            <Button color="error" disabled={busy || !password} onClick={() => void disable()}>
              {t('twoFactorDisable')}
            </Button>
          </Stack>
        </>
      ) : provisioningUri ? (
        <>
          <Typography sx={{ mb: 1 }}>{t('twoFactorScan')}</Typography>
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography sx={{ fontFamily: 'monospace', wordBreak: 'break-all', fontSize: 13 }}>
              {provisioningUri}
            </Typography>
          </Paper>
          <TextField
            fullWidth
            size="small"
            label={t('twoFactorCode')}
            autoComplete="one-time-code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            sx={{ mb: 2 }}
          />
          <Button variant="contained" disabled={busy || !code} onClick={() => void confirmEnrol()}>
            {t('twoFactorConfirm')}
          </Button>
        </>
      ) : (
        <>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            {t('twoFactorOff')}
          </Typography>
          <TextField
            fullWidth
            size="small"
            type="password"
            label={t('confirmWithPassword')}
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            sx={{ mb: 2 }}
          />
          <Button variant="contained" disabled={busy || !password} onClick={() => void beginEnrol()}>
            {t('twoFactorEnable')}
          </Button>
        </>
      )}
    </Paper>
  );
}

function ApiKeysSection() {
  const { t } = useTranslation();
  const toast = useToast();

  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [created, setCreated] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [scope, setScope] = useState<'read' | 'write'>('read');

  const fetchKeys = useCallback(() => apiData<ApiKey[]>({ url: routes.api.apiKeys.list() }), []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchKeys();
        if (!cancelled) setKeys(next ?? []);
      } catch {
        // Feature off, or not permitted. Nothing to show.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchKeys]);

  const create = async () => {
    try {
      const data = await apiData<CreatedApiKey>({
        method: 'post',
        url: routes.api.apiKeys.list(),
        data: { name, scope },
      });
      // The only moment this value exists outside the server.
      setCreated(data?.key ?? null);
      setName('');
      setKeys((await fetchKeys()) ?? []);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  const revoke = async (key: ApiKey) => {
    try {
      await apiCall({ method: 'delete', url: routes.api.apiKeys.revoke(key.id) });
      setKeys((await fetchKeys()) ?? []);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        {t('apiKeys')}
      </Typography>

      {created && (
        <ShownOnce title={t('apiKeyCreated')} values={[created]} onClose={() => setCreated(null)} />
      )}

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
        <TextField
          fullWidth
          size="small"
          label={t('apiKeyName')}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Select
          size="small"
          value={scope}
          onChange={(event) => setScope(event.target.value as 'read' | 'write')}
        >
          <MenuItem value="read">{t('apiKeyRead')}</MenuItem>
          <MenuItem value="write">{t('apiKeyWrite')}</MenuItem>
        </Select>
        <Button variant="contained" disabled={!name} onClick={() => void create()}>
          {t('apiKeyCreate')}
        </Button>
      </Stack>

      {keys.length === 0 ? (
        <Typography color="text.secondary">{t('apiKeyNone')}</Typography>
      ) : (
        <List dense>
          {keys.map((key) => (
            <ListItem
              key={key.id}
              secondaryAction={
                key.is_revoked ? (
                  <Chip size="small" label={t('apiKeyRevoked')} />
                ) : (
                  <Button size="small" color="error" onClick={() => void revoke(key)}>
                    {t('apiKeyRevoke')}
                  </Button>
                )
              }
            >
              <ListItemText
                primary={`${key.name} (${key.prefix}…)`}
                secondary={`${key.scope}${key.last_used_at ? ` · ${t('apiKeyLastUsed')} ${new Date(key.last_used_at).toLocaleDateString()}` : ''}`}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
}

function ConnectionsSection() {
  const { t } = useTranslation();
  const toast = useToast();
  const [connections, setConnections] = useState<SocialConnections | null>(null);

  const fetchConnections = useCallback(
    () => apiData<SocialConnections>({ url: routes.api.social.connections() }),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchConnections();
        if (!cancelled) setConnections(next ?? null);
      } catch {
        // Feature off.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchConnections]);

  const disconnect = async (provider: string) => {
    try {
      await apiCall({ method: 'post', url: routes.api.social.disconnect(provider) });
      setConnections((await fetchConnections()) ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  if (connections === null) return null;

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        {t('connectedAccounts')}
      </Typography>

      {connections.providers.length === 0 ? (
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          {t('noConnections')}
        </Typography>
      ) : (
        <List dense>
          {connections.providers.map((connection) => (
            <ListItem
              key={connection.provider}
              secondaryAction={
                <Button
                  size="small"
                  color="error"
                  /* The backend refuses this when it would leave no way to
                     sign in; disabling it here just avoids the round trip. */
                  disabled={
                    connections.providers.length === 1 && !connections.has_usable_password
                  }
                  onClick={() => void disconnect(connection.provider)}
                >
                  {t('disconnect')}
                </Button>
              }
            >
              <ListItemText primary={connection.provider} />
            </ListItem>
          ))}
        </List>
      )}

      {connections.available.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          {connections.available
            .filter((provider) => !connections.providers.some((c) => c.provider === provider))
            .map((provider) => (
              <Button key={provider} variant="outlined" href={routes.api.social.begin(provider)}>
                {t('connect')} {provider}
              </Button>
            ))}
        </Stack>
      )}
    </Paper>
  );
}

function ActivitySection() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<AuditEventPage | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await apiData<AuditEventPage>({ url: routes.api.account.activity() });
        if (!cancelled) setEvents(next ?? null);
      } catch {
        // Feature off, or nothing recorded yet.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (events === null) return null;

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        {t('recentActivity')}
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        {t('recentActivityHelp')}
      </Typography>

      {events.results.length === 0 ? (
        <Typography color="text.secondary">{t('noActivity')}</Typography>
      ) : (
        <List dense>
          {events.results.map((event) => (
            <ListItem key={event.id} disableGutters>
              <ListItemText
                primary={event.action}
                secondary={`${new Date(event.created_at).toLocaleString()}${
                  event.ip_address ? ` \u00b7 ${event.ip_address}` : ''
                }${event.target ? ` \u00b7 ${event.target}` : ''}`}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
}

function DataExportSection() {
  const { t } = useTranslation();
  const toast = useToast();
  const [requested, setRequested] = useState(false);

  const request = async () => {
    try {
      await apiCall({ method: 'post', url: routes.api.account.requestExport() });
      setRequested(true);
      toast.success(t('exportRequested'));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        {t('dataExport')}
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        {/* The link goes to the account's own address, not back in this
            response -- holding a session is not the same as receiving it. */}
        {t('dataExportHelp')}
      </Typography>
      <Button variant="outlined" disabled={requested} onClick={() => void request()}>
        {requested ? t('exportRequested') : t('requestExport')}
      </Button>
    </Paper>
  );
}

export default function SecurityPage() {
  const { t } = useTranslation();

  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Typography variant="h4" gutterBottom>
        {t('security')}
      </Typography>
      <Divider sx={{ mb: 3 }} />

      {TWO_FACTOR_ENABLED && <TwoFactorSection />}
      {API_KEYS_ENABLED && <ApiKeysSection />}
      {SOCIAL_AUTH_ENABLED && <ConnectionsSection />}
      {AUDIT_LOG_ENABLED && <ActivitySection />}
      <DataExportSection />

      <Box sx={{ height: 24 }} />
    </Container>
  );
}
