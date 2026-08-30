/**
 * Two-step verification, API keys, activity, and your data.
 *
 * One screen rather than the website's several, because on a phone these are
 * things you visit once and leave. Each section is behind the flag its
 * backend is behind, and the whole screen still works with every one of them
 * off -- data export has no flag.
 */

import * as Clipboard from 'expo-clipboard';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Linking, View } from 'react-native';
import {
  ActivityIndicator,
  Button,
  Card,
  Dialog,
  Divider,
  List,
  Portal,
  Text,
  TextInput,
  useTheme,
} from 'react-native-paper';

import type { ApiKey, AuditEventPage, SocialConnections, TwoFactorStatus } from '@app/shared/types';

import { ErrorState } from '../../components/ErrorState';
import { EmptyState, Screen, ScreenHeader } from '../../components/Screen';
import { apiData } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useErrorMessage } from '../../lib/useErrorMessage';
import { useResource } from '../../lib/useResource';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

export default function SecurityScreen() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();

  return (
    <Screen>
      <ScreenHeader title={t('security')} />
      {flags.twoFactor ? <TwoFactorSection /> : null}
      {flags.apiKeys ? <ApiKeysSection /> : null}
      {flags.socialAuth ? <SocialSection /> : null}
      {flags.auditLog ? <ActivitySection /> : null}
      <DataExportSection />
      <View style={{ height: theme.spacing(4) }} />
    </Screen>
  );
}

function SectionHeading({ title }: { title: string }) {
  const theme = useTheme<AppTheme>();
  return (
    <View style={{ marginTop: theme.spacing(3) }}>
      <Text variant="titleMedium">{title}</Text>
      <Divider style={{ marginVertical: theme.spacing(1) }} />
    </View>
  );
}

// ---------------------------------------------------------------------------
// Two-step verification
// ---------------------------------------------------------------------------

function TwoFactorSection() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const toast = useToast();
  const describe = useErrorMessage();

  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [uri, setUri] = useState<string | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);

  const fetchStatus = useCallback(
    () =>
      apiData<TwoFactorStatus>({ url: routes.api.auth.twoFactor.status() }),
    [],
  );
  const { data: status, loading, reload } = useResource(fetchStatus);

  async function enrol() {
    setBusy(true);
    try {
      const payload = await apiData<{ provisioning_uri: string }>({
        url: routes.api.auth.twoFactor.enrol(),
        method: 'POST',
        data: { password },
      });
      setUri(payload?.provisioning_uri ?? null);
      setPassword('');
    } catch (error) {
      toast.error(describe(error, 'couldNotStartEnrolment'));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    try {
      const payload = await apiData<{ recovery_codes: string[] }>({
        url: routes.api.auth.twoFactor.confirm(),
        method: 'POST',
        data: { code },
      });
      setRecoveryCodes(payload?.recovery_codes ?? []);
      setUri(null);
      setCode('');
      reload();
    } catch (error) {
      toast.error(describe(error, 'codeNotAccepted'));
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    setBusy(true);
    try {
      await apiData({
        url: routes.api.auth.twoFactor.disable(),
        method: 'POST',
        data: { password },
      });
      setPassword('');
      toast.success(t('twoFactorDisabled'));
      reload();
    } catch (error) {
      toast.error(describe(error, 'couldNotTurnOff'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <SectionHeading title={t('twoStepTitle')} />

      {loading || !status ? (
        <ActivityIndicator accessibilityLabel={t('loading')} />
      ) : status.enabled ? (
        <>
          <Text style={{ marginBottom: theme.spacing(1) }}>
            {t('twoStepIsOn', { count: status.recovery_codes_remaining })}
          </Text>
          <TextInput
            mode="outlined"
            label={t('yourPassword')}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            textContentType="password"
          />
          <Button
            mode="outlined"
            onPress={disable}
            disabled={busy || !password}
            textColor={theme.colors.error}
            style={{ marginTop: theme.spacing(1) }}
          >
            {t('turnOff')}
          </Button>
        </>
      ) : uri ? (
        <>
          <Text style={{ marginBottom: theme.spacing(1) }}>{t('twoFactorScan')}</Text>
          {/* No QR code, and that is the right call on a phone: the
              authenticator is on this same device, so there is no second
              screen to point a camera at. Handing the URI to the OS opens
              the app with the secret already filled in. */}
          <Button mode="contained" onPress={() => Linking.openURL(uri)}>
            {t('openAuthenticator')}
          </Button>
          <Button
            mode="text"
            onPress={async () => {
              await Clipboard.setStringAsync(uri);
              toast.info(t('setupLinkCopied'));
            }}
          >
            {t('copySetupLink')}
          </Button>
          <TextInput
            mode="outlined"
            label={t('codeFromApp')}
            value={code}
            onChangeText={setCode}
            keyboardType="number-pad"
            textContentType="oneTimeCode"
          />
          <Button
            mode="contained"
            onPress={confirm}
            disabled={busy || !code}
            style={{ marginTop: theme.spacing(1) }}
          >
            {t('twoFactorConfirm')}
          </Button>
        </>
      ) : (
        <>
          <Text style={{ marginBottom: theme.spacing(1) }}>{t('twoStepIsOff')}</Text>
          <TextInput
            mode="outlined"
            label={t('yourPassword')}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            textContentType="password"
          />
          <Button
            mode="contained"
            onPress={enrol}
            disabled={busy || !password}
            style={{ marginTop: theme.spacing(1) }}
          >
            {t('turnOn')}
          </Button>
        </>
      )}

      {/* A dialog rather than a section, because these are shown exactly once
          and are useless to anyone who taps past them. */}
      <Portal>
        <Dialog visible={recoveryCodes !== null} onDismiss={() => setRecoveryCodes(null)}>
          <Dialog.Title>{t('saveRecoveryCodes')}</Dialog.Title>
          <Dialog.Content>
            <Text style={{ marginBottom: theme.spacing(1) }}>{t('recoveryCodesHelp')}</Text>
            {recoveryCodes?.map((recoveryCode) => (
              <Text key={recoveryCode} variant="titleMedium">
                {recoveryCode}
              </Text>
            ))}
          </Dialog.Content>
          <Dialog.Actions>
            <Button
              onPress={async () => {
                await Clipboard.setStringAsync((recoveryCodes ?? []).join('\n'));
                toast.info(t('recoveryCodesCopied'));
              }}
            >
              {t('copy')}
            </Button>
            <Button onPress={() => setRecoveryCodes(null)}>{t('done')}</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </>
  );
}

// ---------------------------------------------------------------------------
// API keys
// ---------------------------------------------------------------------------

function ApiKeysSection() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const toast = useToast();
  const describe = useErrorMessage();

  const fetchKeys = useCallback(
    () =>
      apiData<ApiKey[]>({ url: routes.api.apiKeys.list() }),
    [],
  );
  const { data: keys, loading, error, reload } = useResource(fetchKeys);

  async function revoke(id: number) {
    try {
      await apiData({ url: routes.api.apiKeys.revoke(id), method: 'DELETE' });
      toast.success(t('keyRevoked'));
      reload();
    } catch (error) {
      toast.error(describe(error, 'couldNotRevokeKey'));
    }
  }

  return (
    <>
      <SectionHeading title={t('apiKeys')} />
      {/* Listing and revoking only. Creating one shows a secret exactly once,
          which belongs somewhere it can be copied into a terminal -- so the
          app does not offer it. */}
      <Text style={{ marginBottom: theme.spacing(1), color: theme.colors.onSurfaceVariant }}>
        {t('apiKeysMobileHelp')}
      </Text>
      {loading ? (
        <ActivityIndicator accessibilityLabel={t('loading')} />
      ) : error ? (
        <ErrorState message={describe(error, 'couldNotLoadKeys')} onRetry={reload} />
      ) : !keys || keys.length === 0 ? (
        <EmptyState message={t('apiKeyNone')} />
      ) : (
        keys.map((key) => (
          <List.Item
            key={key.id}
            title={key.name}
            description={`${key.prefix}… · ${key.scope}${key.is_revoked ? ` · ${t('apiKeyRevoked')}` : ''}`}
            right={() =>
              key.is_revoked ? null : (
                <Button onPress={() => revoke(key.id)} textColor={theme.colors.error}>
                  {t('apiKeyRevoke')}
                </Button>
              )
            }
          />
        ))
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Linked sign-in providers
// ---------------------------------------------------------------------------

function SocialSection() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const toast = useToast();
  const describe = useErrorMessage();
  const fetchConnections = useCallback(
    () =>
      apiData<SocialConnections>({ url: routes.api.social.connections() }),
    [],
  );
  const { data: connections, loading, error, reload } = useResource(fetchConnections);

  async function disconnect(provider: string) {
    try {
      await apiData({ url: routes.api.social.disconnect(provider), method: 'POST' });
      toast.success(t('providerDisconnected', { provider }));
      reload();
    } catch (error) {
      toast.error(describe(error, 'couldNotDisconnect'));
    }
  }

  return (
    <>
      <SectionHeading title={t('connectedAccounts')} />
      {/* Disconnecting only. Connecting a provider needs the redirect flow,
          which on native means an authorization-code exchange the backend
          does not offer yet -- see docs/mobile.md. */}
      <Text style={{ marginBottom: theme.spacing(1), color: theme.colors.onSurfaceVariant }}>
        {t('linkedAccountsMobileHelp')}
      </Text>
      {loading ? (
        <ActivityIndicator accessibilityLabel={t('loading')} />
      ) : error || !connections ? (
        <ErrorState
          message={describe(error, 'couldNotLoadLinkedAccounts')}
          onRetry={reload}
        />
      ) : connections.providers.length === 0 ? (
        <EmptyState message={t('noConnections')} />
      ) : (
        connections.providers.map((connection) => (
          <List.Item
            key={connection.provider}
            title={connection.provider}
            description={new Date(connection.connected_at).toLocaleDateString()}
            right={() => (
              <Button
                onPress={() => disconnect(connection.provider)}
                // Unlinking the last provider when there is no usable password
                // would lock the account out entirely. The backend refuses it;
                // disabling the button says so before the tap.
                disabled={
                  !connections.has_usable_password && connections.providers.length === 1
                }
              >
                {t('unlink')}
              </Button>
            )}
          />
        ))
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Activity
// ---------------------------------------------------------------------------

function ActivitySection() {
  const { t } = useTranslation();
  const describe = useErrorMessage();
  const fetchActivity = useCallback(
    () =>
      apiData<AuditEventPage>({ url: routes.api.account.activity() }),
    [],
  );
  const { data: page, loading, error } = useResource(fetchActivity);

  return (
    <>
      <SectionHeading title={t('recentActivity')} />
      {loading ? (
        <ActivityIndicator accessibilityLabel={t('loading')} />
      ) : error || !page ? (
        <ErrorState message={describe(error, 'couldNotLoadActivity')} />
      ) : page.results.length === 0 ? (
        <EmptyState message={t('noActivity')} />
      ) : (
        page.results.map((event) => (
          <List.Item
            key={event.id}
            title={event.action}
            description={`${new Date(event.created_at).toLocaleString()}${
              event.ip_address ? ` · ${event.ip_address}` : ''
            }`}
          />
        ))
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Your data
// ---------------------------------------------------------------------------

function DataExportSection() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const toast = useToast();
  const describe = useErrorMessage();
  const [requesting, setRequesting] = useState(false);

  async function request() {
    setRequesting(true);
    try {
      await apiData({
        url: routes.api.account.requestExport(),
        method: 'POST',
      });
      toast.success(t('exportOnItsWay'));
    } catch (error) {
      toast.error(describe(error, 'couldNotRequestExport'));
    } finally {
      setRequesting(false);
    }
  }

  return (
    <>
      <SectionHeading title={t('dataExport')} />
      <Card mode="outlined">
        <Card.Content>
          <Text>{t('exportCardHelp')}</Text>
        </Card.Content>
        <Card.Actions>
          <Button onPress={request} loading={requesting} disabled={requesting}>
            {t('requestAnExport')}
          </Button>
        </Card.Actions>
      </Card>

      <Text
        variant="bodySmall"
        style={{ marginTop: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
      >
        {t('deleteAccountNote')}
      </Text>
    </>
  );
}
