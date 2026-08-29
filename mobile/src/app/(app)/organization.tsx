/**
 * The team: which organization you are acting for, who is in it, and who has
 * been invited.
 *
 * The switcher is the part that differs most from the website. There, the
 * server remembers the choice in the session; here the client remembers it
 * and names it on every request -- see `store/organization.ts`.
 */

import { useCallback, useState } from 'react';
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

import { EmptyState, Screen, ScreenHeader } from '../../components/Screen';
import { ApiError, apiData } from '../../lib/api';
import { flags } from '../../lib/config';
import { routes } from '../../lib/routes';
import { useResource } from '../../lib/useResource';
import { useOrganizations } from '../../store/organization';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

/** Roles that may invite or remove people. The backend enforces it too. */
const CAN_MANAGE = new Set(['OWNER', 'ADMIN']);

export default function OrganizationScreen() {
  const theme = useTheme<AppTheme>();
  const toast = useToast();
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
      apiData<OrganizationMember[]>({
        url: routes.api.organizations.members(),
        errorMessage: 'Could not load the members.',
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeSlug],
  );
  const fetchInvitations = useCallback(
    () =>
      apiData<OrganizationInvitation[]>({
        url: routes.api.organizations.invitations(),
        errorMessage: 'Could not load the invitations.',
      }),
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
        errorMessage: 'Could not send that invitation.',
      });
      setInviteEmail('');
      toast.success('Invitation sent.');
      invitationsResource.reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not send that invitation.');
    } finally {
      setInviting(false);
    }
  }

  async function revoke(id: number) {
    try {
      await apiData({ url: routes.api.organizations.invitation(id), method: 'DELETE' });
      toast.success('Invitation revoked.');
      invitationsResource.reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not revoke that invitation.');
    }
  }

  if (!flags.organizations) {
    return (
      <Screen>
        <ScreenHeader
          title="Teams are off"
          subtitle="Set EXPO_PUBLIC_ORGANIZATIONS_ENABLED, and ORGANIZATIONS_ENABLED on the backend."
        />
      </Screen>
    );
  }

  if (loading) return <Screen loading />;

  if (error) {
    return (
      <Screen>
        <ScreenHeader title="Team" subtitle={error} />
      </Screen>
    );
  }

  if (!active) {
    return (
      <Screen>
        <ScreenHeader
          title="No organization yet"
          subtitle="You are not a member of one. An invitation will bring you into a team."
        />
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader title={active.name} subtitle={active.role ?? undefined} />

      {organizations.length > 1 ? (
        <View style={{ marginBottom: theme.spacing(3) }}>
          <Text variant="titleMedium">Acting as</Text>
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

      <Text variant="titleMedium">Members</Text>
      <Divider style={{ marginVertical: theme.spacing(1) }} />
      {membersResource.loading ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : !members || members.length === 0 ? (
        <EmptyState message="No members." />
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
            Invitations
          </Text>
          <Divider style={{ marginVertical: theme.spacing(1) }} />

          <TextInput
            mode="outlined"
            label="Invite by email"
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
            Send invitation
          </Button>

          {invitations && invitations.length > 0
            ? invitations.map((invitation) => (
                <List.Item
                  key={invitation.id}
                  title={invitation.email}
                  description={
                    invitation.is_expired
                      ? 'Expired'
                      : `Expires ${new Date(invitation.expires_at).toLocaleDateString()}`
                  }
                  right={() => (
                    <Button onPress={() => revoke(invitation.id)} textColor={theme.colors.error}>
                      Revoke
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
