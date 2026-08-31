/**
 * Your own profile: what the account is, and the three fields you may change.
 *
 * Only three, and that is the backend's decision rather than a simplification
 * for the small screen -- `UserUpdateSerializer` excludes role, account type
 * and verified status because those are privilege boundaries. A form here
 * offering them would fail silently on save.
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { View } from 'react-native';
import { Button, Card, Divider, List, Text, useTheme } from 'react-native-paper';

import type { User } from '@app/shared/types';

import { FormField } from '../../components/FormField';
import { Screen, ScreenHeader } from '../../components/Screen';
import { ApiError, apiData } from '../../lib/api';
import { routes } from '../../lib/routes';
import { useErrorMessage } from '../../lib/useErrorMessage';
import { useAuth } from '../../store/auth';
import { useToast } from '../../store/toast';
import type { AppTheme } from '../../theme/paper';

interface ProfileForm {
  first_name: string;
  last_name: string;
  phone_number: string;
}

export default function ProfileScreen() {
  const theme = useTheme<AppTheme>();
  const { t } = useTranslation();
  const { user, isLoading, refresh } = useAuth();
  const [refreshing, setRefreshing] = useState(false);
  const toast = useToast();
  const describe = useErrorMessage();

  const { control, handleSubmit, reset } = useForm<ProfileForm>({
    defaultValues: { first_name: '', last_name: '', phone_number: '' },
  });
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({});

  // Fill the form once the user arrives. `reset` rather than `defaultValues`
  // because the user is null on the first render -- the bootstrap is still
  // asking the server who this is.
  useEffect(() => {
    if (!user) return;
    reset({
      first_name: user.first_name ?? '',
      last_name: user.last_name ?? '',
      phone_number: user.phone_number ?? '',
    });
  }, [user, reset]);

  async function onSubmit(values: ProfileForm) {
    setSubmitting(true);
    setFieldErrors({});

    try {
      await apiData<User>({
        url: routes.api.users.me(),
        method: 'PATCH',
        data: values,
      });
      await refresh();
      toast.success(t('profileUpdated'));
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors({
          first_name: error.fieldError('first_name'),
          last_name: error.fieldError('last_name'),
          phone_number: error.fieldError('phone_number'),
        });
      }
      toast.error(describe(error, 'couldNotSaveProfile'));
    } finally {
      setSubmitting(false);
    }
  }

  if (isLoading || !user) {
    return <Screen loading />;
  }

  async function reload() {
    setRefreshing(true);
    try {
      await refresh();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    // Pulling here re-reads the profile, which is how someone who has just
    // confirmed their email in another app makes the banner go away.
    <Screen onRefresh={reload} refreshing={refreshing}>
      <ScreenHeader title={user.display_name || user.email} subtitle={user.email} />

      {!user.email_verified ? (
        <Card
          mode="contained"
          style={{
            marginBottom: theme.spacing(3),
            backgroundColor: theme.colors.tertiaryContainer,
          }}
        >
          <Card.Content>
            <Text style={{ color: theme.colors.onTertiaryContainer }}>
              {t('confirmEmailBanner')}
            </Text>
          </Card.Content>
        </Card>
      ) : null}

      <FormField
        control={control}
        name="first_name"
        label={t('firstName')}
        serverError={fieldErrors.first_name}
        autoCapitalize="words"
      />
      <FormField
        control={control}
        name="last_name"
        label={t('lastName')}
        serverError={fieldErrors.last_name}
        autoCapitalize="words"
      />
      <FormField
        control={control}
        name="phone_number"
        label={t('phoneNumber')}
        serverError={fieldErrors.phone_number}
        keyboardType="number-pad"
      />

      <Button
        mode="contained"
        onPress={handleSubmit(onSubmit)}
        loading={submitting}
        disabled={submitting}
      >
        {t('saveChanges')}
      </Button>

      <View style={{ marginTop: theme.spacing(4) }}>
        <Text variant="titleMedium">{t('account')}</Text>
        <Divider style={{ marginVertical: theme.spacing(1) }} />
        <List.Item title={t('username')} description={user.username ?? t('usernameNotSet')} />
        <List.Item title={t('accountType')} description={user.account_type} />
        <List.Item
          title={t('memberSince')}
          description={new Date(user.date_joined).toLocaleDateString()}
        />
      </View>
    </Screen>
  );
}
