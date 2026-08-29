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

import { EmptyState, Screen, ScreenHeader } from '../../components/Screen';
import { ApiError, apiData } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useResource } from '../../lib/useResource';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

export default function SecurityScreen() {
  const theme = useTheme<AppTheme>();

  return (
    <Screen>
      <ScreenHeader title="Security" />
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
  const toast = useToast();

  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [uri, setUri] = useState<string | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);

  const fetchStatus = useCallback(
    () =>
      apiData<TwoFactorStatus>({
        url: routes.api.auth.twoFactor.status(),
        errorMessage: 'Could not read your two-step settings.',
      }),
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
        errorMessage: 'Could not start enrolment.',
      });
      setUri(payload?.provisioning_uri ?? null);
      setPassword('');
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not start enrolment.');
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
        errorMessage: 'That code was not accepted.',
      });
      setRecoveryCodes(payload?.recovery_codes ?? []);
      setUri(null);
      setCode('');
      reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'That code was not accepted.');
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
        errorMessage: 'Could not turn this off.',
      });
      setPassword('');
      toast.success('Two-step verification is off.');
      reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not turn this off.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <SectionHeading title="Two-step verification" />

      {loading || !status ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : status.enabled ? (
        <>
          <Text style={{ marginBottom: theme.spacing(1) }}>
            On. {status.recovery_codes_remaining} recovery codes left.
          </Text>
          <TextInput
            mode="outlined"
            label="Your password"
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
            Turn off
          </Button>
        </>
      ) : uri ? (
        <>
          <Text style={{ marginBottom: theme.spacing(1) }}>
            Add this to your authenticator app, then enter the code it shows.
          </Text>
          {/* No QR code, and that is the right call on a phone: the
              authenticator is on this same device, so there is no second
              screen to point a camera at. Handing the URI to the OS opens
              the app with the secret already filled in. */}
          <Button mode="contained" onPress={() => Linking.openURL(uri)}>
            Open my authenticator app
          </Button>
          <Button
            mode="text"
            onPress={async () => {
              await Clipboard.setStringAsync(uri);
              toast.info('Setup link copied.');
            }}
          >
            Copy the setup link instead
          </Button>
          <TextInput
            mode="outlined"
            label="Code from the app"
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
            Confirm
          </Button>
        </>
      ) : (
        <>
          <Text style={{ marginBottom: theme.spacing(1) }}>
            Off. Turning it on asks for a code from an authenticator app each
            time you sign in.
          </Text>
          <TextInput
            mode="outlined"
            label="Your password"
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
            Turn on
          </Button>
        </>
      )}

      {/* A dialog rather than a section, because these are shown exactly once
          and are useless to anyone who taps past them. */}
      <Portal>
        <Dialog visible={recoveryCodes !== null} onDismiss={() => setRecoveryCodes(null)}>
          <Dialog.Title>Save your recovery codes</Dialog.Title>
          <Dialog.Content>
            <Text style={{ marginBottom: theme.spacing(1) }}>
              These are shown once. Each one signs you in if you lose your
              authenticator.
            </Text>
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
                toast.info('Recovery codes copied.');
              }}
            >
              Copy
            </Button>
            <Button onPress={() => setRecoveryCodes(null)}>Done</Button>
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
  const toast = useToast();

  const fetchKeys = useCallback(
    () =>
      apiData<ApiKey[]>({
        url: routes.api.apiKeys.list(),
        errorMessage: 'Could not load your API keys.',
      }),
    [],
  );
  const { data: keys, loading, error, reload } = useResource(fetchKeys);

  async function revoke(id: number) {
    try {
      await apiData({ url: routes.api.apiKeys.revoke(id), method: 'DELETE' });
      toast.success('Key revoked.');
      reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not revoke that key.');
    }
  }

  return (
    <>
      <SectionHeading title="API keys" />
      {/* Listing and revoking only. Creating one shows a secret exactly once,
          which belongs somewhere it can be copied into a terminal -- so the
          app does not offer it. */}
      <Text style={{ marginBottom: theme.spacing(1), color: theme.colors.onSurfaceVariant }}>
        Create new keys on the website. Here you can see and revoke them.
      </Text>
      {loading ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : error ? (
        <EmptyState message={error} />
      ) : !keys || keys.length === 0 ? (
        <EmptyState message="No API keys." />
      ) : (
        keys.map((key) => (
          <List.Item
            key={key.id}
            title={key.name}
            description={`${key.prefix}… · ${key.scope}${key.is_revoked ? ' · revoked' : ''}`}
            right={() =>
              key.is_revoked ? null : (
                <Button onPress={() => revoke(key.id)} textColor={theme.colors.error}>
                  Revoke
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
  const toast = useToast();
  const fetchConnections = useCallback(
    () =>
      apiData<SocialConnections>({
        url: routes.api.social.connections(),
        errorMessage: 'Could not load your linked accounts.',
      }),
    [],
  );
  const { data: connections, loading, error, reload } = useResource(fetchConnections);

  async function disconnect(provider: string) {
    try {
      await apiData({ url: routes.api.social.disconnect(provider), method: 'POST' });
      toast.success(`${provider} disconnected.`);
      reload();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not disconnect.');
    }
  }

  return (
    <>
      <SectionHeading title="Linked accounts" />
      {/* Disconnecting only. Connecting a provider needs the redirect flow,
          which on native means an authorization-code exchange the backend
          does not offer yet -- see docs/mobile.md. */}
      <Text style={{ marginBottom: theme.spacing(1), color: theme.colors.onSurfaceVariant }}>
        Link a new provider on the website.
      </Text>
      {loading ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : error || !connections ? (
        <EmptyState message={error ?? 'No linked accounts.'} />
      ) : connections.providers.length === 0 ? (
        <EmptyState message="No linked accounts." />
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
                Unlink
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
  const fetchActivity = useCallback(
    () =>
      apiData<AuditEventPage>({
        url: routes.api.account.activity(),
        errorMessage: 'Could not load your activity.',
      }),
    [],
  );
  const { data: page, loading, error } = useResource(fetchActivity);

  return (
    <>
      <SectionHeading title="Recent activity" />
      {loading ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : error || !page ? (
        <EmptyState message={error ?? 'Nothing recorded yet.'} />
      ) : page.results.length === 0 ? (
        <EmptyState message="Nothing recorded yet." />
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
  const toast = useToast();
  const [requesting, setRequesting] = useState(false);

  async function request() {
    setRequesting(true);
    try {
      await apiData({
        url: routes.api.account.requestExport(),
        method: 'POST',
        errorMessage: 'Could not request your export.',
      });
      toast.success('We will email you a link when your export is ready.');
    } catch (error) {
      toast.error(
        error instanceof ApiError ? error.message : 'Could not request your export.',
      );
    } finally {
      setRequesting(false);
    }
  }

  return (
    <>
      <SectionHeading title="Your data" />
      <Card mode="outlined">
        <Card.Content>
          <Text>
            Request a copy of everything this account holds. It arrives as a
            link by email.
          </Text>
        </Card.Content>
        <Card.Actions>
          <Button onPress={request} loading={requesting} disabled={requesting}>
            Request an export
          </Button>
        </Card.Actions>
      </Card>

      <Text
        variant="bodySmall"
        style={{ marginTop: theme.spacing(2), color: theme.colors.onSurfaceVariant }}
      >
        Deleting your account is on the website. It is irreversible, and it is
        not a thing to offer behind a mis-tap on a phone.
      </Text>
    </>
  );
}
