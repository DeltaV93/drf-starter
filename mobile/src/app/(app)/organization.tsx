/**
 * The team: which organization you are acting for, who is in it, and who has
 * been invited.
 *
 * The switcher is the part that differs most from the website. There, the
 * server remembers the choice in the session; here the client remembers it
 * and names it on every request -- see `store/organization.ts`.
 */

import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import {
  ActivityIndicator,
  Button,
  Chip,
  Divider,
  List,
  Text,
  TextInput,
  useTheme,
} from 'react-native-paper';

import type { OrganizationInvitation, OrganizationMember } from '@app/shared/types';

import { ErrorState } from '../../components/ErrorState';
import { FeatureOff } from '../../components/FeatureOff';
import { EmptyState, Screen, ScreenHeader } from '../../components/Screen';
import { apiData } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useErrorMessage } from '../../lib/useErrorMessage';
import { useResource } from '../../lib/useResource';
import { useOrganizations } from '../../store/organization';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

/** Roles that may invite or remove people. The backend enforces it too. */
const CAN_MANAGE = new Set(['OWNER', 'ADMIN']);

export default function OrganizationScreen() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const toast = useToast();
  const describe = useErrorMessage();
  const { organizations, active, loading, error, switchTo } = useOrganizations();

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviting, setInviting] = useState(false);

  const manages = active?.role ? CAN_MANAGE.has(active.role) : false;

  // Both fetchers close over the active slug, so switching organization gives
  // them a new identity and `useResource` re-reads. The endpoints are scoped
  // by that same choice, so without it the previous team's rows would sit
  // there under the new organization's name.
  const activeSlug = active?.slug;

  const fetchMembers = useCallback(
    () =>
      apiData<OrganizationMember[]>({ url: routes.api.organizations.members() }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeSlug],
  );
  const fetchInvitations = useCallback(
    () =>
      apiData<OrganizationInvitation[]>({ url: routes.api.organizations.invitations() }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeSlug],
  );

  const membersResource = useResource(fetchMembers);
  // Only owners and admins may list invitations, so a refusal here is
  // ordinary for a member rather than a failure worth showing.
  const invitationsResource = useResource(fetchInvitations);
  const members = membersResource.data;
  const invitations = invitationsResource.data;

  async function invite() {
    setInviting(true);
    try {
      await apiData({
        url: routes.api.organizations.invitations(),
        method: 'POST',
        data: { email: inviteEmail, role: 'MEMBER' },
      });
      setInviteEmail('');
      toast.success(t('orgInvitationSent'));
      invitationsResource.reload();
    } catch (err) {
      toast.error(describe(err, 'couldNotSendInvitation'));
    } finally {
      setInviting(false);
    }
  }

  async function revoke(id: number) {
    try {
      await apiData({ url: routes.api.organizations.invitation(id), method: 'DELETE' });
      toast.success(t('invitationRevoked'));
      invitationsResource.reload();
    } catch (err) {
      toast.error(describe(err, 'couldNotRevokeInvitation'));
    }
  }

  if (!flags.organizations) {
    return (
      <FeatureOff
        feature={t('team')}
        clientFlag="EXPO_PUBLIC_ORGANIZATIONS_ENABLED"
        serverFlag="ORGANIZATIONS_ENABLED"
      />
    );
  }

  if (loading) return <Screen loading />;

  if (error) {
    return (
      <Screen>
        <ScreenHeader title={t('team')} />
        <ErrorState message={error} />
      </Screen>
    );
  }

  if (!active) {
    return (
      <Screen>
        <ScreenHeader title={t('noOrganizationYet')} subtitle={t('noOrganizationHelp')} />
      </Screen>
    );
  }

  return (
    <Screen
      // Both lists reload together: they are two halves of one screen, and a
      // gesture that refreshed only the members would be a lie about the
      // invitations underneath them.
      onRefresh={() => {
        membersResource.reload();
        invitationsResource.reload();
      }}
      refreshing={membersResource.refreshing || invitationsResource.refreshing}
    >
      <ScreenHeader title={active.name} subtitle={active.role ?? undefined} />

      {organizations.length > 1 ? (
        <View style={{ marginBottom: theme.spacing(3) }}>
          <Text variant="titleMedium">{t('actingAs')}</Text>
          <View
            style={{
              flexDirection: 'row',
              flexWrap: 'wrap',
              gap: theme.spacing(1),
              marginTop: theme.spacing(1),
            }}
          >
            {organizations.map((organization) => (
              <Chip
                key={organization.id}
                selected={organization.id === active.id}
                onPress={() => switchTo(organization)}
              >
                {organization.name}
              </Chip>
            ))}
          </View>
        </View>
      ) : null}

      <Text variant="titleMedium">{t('orgMembers')}</Text>
      <Divider style={{ marginVertical: theme.spacing(1) }} />
      {membersResource.loading ? (
        <ActivityIndicator accessibilityLabel={t('loading')} />
      ) : membersResource.error ? (
        <ErrorState
          message={describe(membersResource.error, 'couldNotLoadMembers')}
          onRetry={membersResource.reload}
        />
      ) : !members || members.length === 0 ? (
        <EmptyState message={t('noMembers')} />
      ) : (
        members.map((member) => (
          <List.Item
            key={member.id}
            title={`${member.first_name} ${member.last_name}`.trim() || member.email}
            description={`${member.email} · ${member.role}`}
          />
        ))
      )}

      {manages ? (
        <>
          <Text variant="titleMedium" style={{ marginTop: theme.spacing(3) }}>
            {t('orgInvitations')}
          </Text>
          <Divider style={{ marginVertical: theme.spacing(1) }} />

          <TextInput
            mode="outlined"
            label={t('inviteByEmail')}
        accessibilityLabel={t('inviteByEmail')}
            value={inviteEmail}
            onChangeText={setInviteEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            textContentType="emailAddress"
          />
          <Button
            mode="contained"
            onPress={invite}
            loading={inviting}
            disabled={inviting || !inviteEmail}
            style={{ marginTop: theme.spacing(1) }}
          >
            {t('orgInvite')}
          </Button>

          {invitations && invitations.length > 0
            ? invitations.map((invitation) => (
                <List.Item
                  key={invitation.id}
                  title={invitation.email}
                  description={
                    invitation.is_expired
                      ? t('orgExpired')
                      : t('expiresOn', {
                          date: new Date(invitation.expires_at).toLocaleDateString(),
                        })
                  }
                  right={() => (
                    <Button onPress={() => revoke(invitation.id)} textColor={theme.colors.error}>
                      {t('orgRevoke')}
                    </Button>
                  )}
                />
              ))
            : null}
        </>
      ) : null}
    </Screen>
  );
}
