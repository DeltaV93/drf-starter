/**
 * Members, roles and invitations for the active organization.
 *
 * Only rendered when VITE_ORGANIZATIONS_ENABLED matches the backend's
 * ORGANIZATIONS_ENABLED -- see App.tsx.
 */

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { apiCall, apiData } from '../../lib/api';
import { routes } from '../../lib/routes';
import type {
  OrganizationInvitation,
  OrganizationMember,
  OrganizationRole,
} from '../../lib/types';
import { useOrganizations } from '../../store/organization';
import { useToast } from '../../store/toast';

const ROLES: OrganizationRole[] = ['OWNER', 'ADMIN', 'MEMBER'];

export default function OrganizationPage() {
  const { t } = useTranslation();
  const { active, loading: orgLoading, refresh } = useOrganizations();
  const toast = useToast();

  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  // Derived, not stored: an effect that sets a loading flag synchronously
  // has nothing to await first, which is exactly the cascading render the
  // React Compiler rule is pointing at.
  const [loaded, setLoaded] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<OrganizationRole>('MEMBER');
  const [inviting, setInviting] = useState(false);

  const canManage = active?.role === 'OWNER' || active?.role === 'ADMIN';

  /**
   * Read members, and invitations when the caller may see them.
   *
   * Returns rather than setting state so the mount effect can inline its own
   * setState behind a cancellation guard -- see useAuthBootstrap for the same
   * shape. Calling a setState-ing callback straight from an effect is what the
   * React Compiler rule flags, and the guard is not decoration: without it a
   * slow response lands on an unmounted component.
   */
  const fetchAll = useCallback(async () => {
    const loadedMembers =
      (await apiData<OrganizationMember[]>({
        url: routes.api.organizations.members(),
      })) ?? [];

    const loadedInvitations = canManage
      ? ((await apiData<OrganizationInvitation[]>({
          url: routes.api.organizations.invitations(),
        })) ?? [])
      : [];

    return { members: loadedMembers, invitations: loadedInvitations };
  }, [canManage]);

  useEffect(() => {
    if (!active) return;

    let cancelled = false;
    (async () => {
      try {
        const next = await fetchAll();
        if (cancelled) return;
        setMembers(next.members);
        setInvitations(next.invitations);
      } catch (error) {
        if (cancelled) return;
        toast.error(error instanceof Error ? error.message : t('genericError'));
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [active, fetchAll, toast, t]);

  /** Re-read after a mutation. Not on an effect path, so it may set state freely. */
  const reload = useCallback(async () => {
    try {
      const next = await fetchAll();
      setMembers(next.members);
      setInvitations(next.invitations);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  }, [fetchAll, toast, t]);

  const invite = async (event: React.FormEvent) => {
    event.preventDefault();
    setInviting(true);
    try {
      await apiCall({
        method: 'post',
        url: routes.api.organizations.invitations(),
        data: { email: inviteEmail, role: inviteRole },
      });
      setInviteEmail('');
      toast.success(t('orgInvitationSent'));
      await reload();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    } finally {
      setInviting(false);
    }
  };

  const changeRole = async (member: OrganizationMember, role: OrganizationRole) => {
    try {
      await apiCall({
        method: 'patch',
        url: routes.api.organizations.member(member.id),
        data: { role },
      });
      await reload();
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  const removeMember = async (member: OrganizationMember) => {
    try {
      await apiCall({
        method: 'delete',
        url: routes.api.organizations.member(member.id),
      });
      await reload();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  const revoke = async (invitation: OrganizationInvitation) => {
    try {
      await apiCall({
        method: 'delete',
        url: routes.api.organizations.invitation(invitation.id),
      });
      await reload();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('genericError'));
    }
  };

  // Nothing to wait for once the organization list has settled on none.
  const loading = orgLoading || (active !== null && !loaded);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!active) {
    return (
      <Container maxWidth="md" sx={{ py: 6 }}>
        <Alert severity="info">{t('orgNone')}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Typography variant="h4" gutterBottom>
        {active.name}
      </Typography>

      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          {t('orgMembers')}
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('email')}</TableCell>
              <TableCell>{t('orgRole')}</TableCell>
              {canManage && <TableCell align="right" />}
            </TableRow>
          </TableHead>
          <TableBody>
            {members.map((member) => (
              <TableRow key={member.id}>
                <TableCell>{member.email}</TableCell>
                <TableCell>
                  {canManage && !member.is_last_owner ? (
                    <Select
                      size="small"
                      value={member.role}
                      onChange={(event) =>
                        void changeRole(member, event.target.value as OrganizationRole)
                      }
                    >
                      {ROLES.map((role) => (
                        <MenuItem key={role} value={role}>
                          {role}
                        </MenuItem>
                      ))}
                    </Select>
                  ) : (
                    <Chip
                      size="small"
                      label={member.role}
                      /* The last owner cannot be demoted or removed: an
                         ownerless organization cannot be administered. */
                      title={member.is_last_owner ? t('orgLastOwner') : undefined}
                    />
                  )}
                </TableCell>
                {canManage && (
                  <TableCell align="right">
                    <Button
                      size="small"
                      color="error"
                      disabled={member.is_last_owner}
                      onClick={() => void removeMember(member)}
                    >
                      {t('orgRemove')}
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      {canManage && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t('orgInvitations')}
          </Typography>

          <Box component="form" onSubmit={invite} sx={{ mb: 3 }}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                fullWidth
                size="small"
                type="email"
                required
                label={t('email')}
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
              />
              <Select
                size="small"
                value={inviteRole}
                onChange={(event) => setInviteRole(event.target.value as OrganizationRole)}
              >
                {ROLES.map((role) => (
                  <MenuItem key={role} value={role}>
                    {role}
                  </MenuItem>
                ))}
              </Select>
              <Button type="submit" variant="contained" disabled={inviting}>
                {t('orgInvite')}
              </Button>
            </Stack>
          </Box>

          {invitations.length === 0 ? (
            <Typography color="text.secondary">{t('orgNoInvitations')}</Typography>
          ) : (
            <Table size="small">
              <TableBody>
                {invitations.map((invitation) => (
                  <TableRow key={invitation.id}>
                    <TableCell>{invitation.email}</TableCell>
                    <TableCell>{invitation.role}</TableCell>
                    <TableCell>
                      {invitation.is_expired ? t('orgExpired') : ''}
                    </TableCell>
                    <TableCell align="right">
                      <Button size="small" color="error" onClick={() => void revoke(invitation)}>
                        {t('orgRevoke')}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      )}
    </Container>
  );
}
