/**
 * Your own profile: what the account is, and the three fields you may change.
 *
 * Only three, and that is the backend's decision rather than a simplification
 * for the small screen -- `UserUpdateSerializer` excludes role, account type
 * and verified status because those are privilege boundaries. A form here
 * offering them would fail silently on save.
 */

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { View } from 'react-native';
import { Button, Card, Divider, List, Text, useTheme } from 'react-native-paper';

import type { User } from '@app/shared/types';

import { FormField } from '../../components/FormField';
import { Screen, ScreenHeader } from '../../components/Screen';
import { ApiError, apiData } from '../../lib/api';
import { routes } from '../../lib/routes';
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
  const { user, isLoading, refresh } = useAuth();
  const toast = useToast();

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
        errorMessage: 'Could not save your profile.',
      });
      await refresh();
      toast.success('Profile updated.');
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors({
          first_name: error.fieldError('first_name'),
          last_name: error.fieldError('last_name'),
          phone_number: error.fieldError('phone_number'),
        });
        toast.error(error.message);
      } else {
        toast.error('Could not save your profile.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (isLoading || !user) {
    return <Screen loading />;
  }

  return (
    <Screen>
      <ScreenHeader title={user.display_name || user.username} subtitle={user.email} />

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
              Your email address is not confirmed yet. Check your inbox for the
              link — opening it on this device brings you straight back here.
            </Text>
          </Card.Content>
        </Card>
      ) : null}

      <FormField
        control={control}
        name="first_name"
        label="First name"
        serverError={fieldErrors.first_name}
        autoCapitalize="words"
      />
      <FormField
        control={control}
        name="last_name"
        label="Last name"
        serverError={fieldErrors.last_name}
        autoCapitalize="words"
      />
      <FormField
        control={control}
        name="phone_number"
        label="Phone number"
        serverError={fieldErrors.phone_number}
        keyboardType="number-pad"
      />

      <Button
        mode="contained"
        onPress={handleSubmit(onSubmit)}
        loading={submitting}
        disabled={submitting}
      >
        Save changes
      </Button>

      <View style={{ marginTop: theme.spacing(4) }}>
        <Text variant="titleMedium">Account</Text>
        <Divider style={{ marginVertical: theme.spacing(1) }} />
        <List.Item title="Username" description={user.username} />
        <List.Item title="Account type" description={user.account_type} />
        <List.Item
          title="Member since"
          description={new Date(user.date_joined).toLocaleDateString()}
        />
      </View>
    </Screen>
  );
}
