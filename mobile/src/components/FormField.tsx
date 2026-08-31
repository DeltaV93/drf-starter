/**
 * A text field wired to react-hook-form, with the backend's errors in it.
 *
 * The reason this is a component rather than a pattern each screen repeats:
 * a field has two independent sources of error -- what the client validated
 * and what the server said -- and showing only the first is the failure that
 * matters. "A user with that email already exists" cannot be known locally,
 * so a form that renders only client-side errors submits, fails, and shows
 * nothing.
 */

import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';
import { View } from 'react-native';
import { HelperText, TextInput, useTheme } from 'react-native-paper';

import type { AppTheme } from '../theme/paper';

interface FormFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  label: string;
  /** An error the server reported for this field, if any. */
  serverError?: string;
  /** Shown under the field while it has no error. */
  helperText?: string;
  secureTextEntry?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words';
  keyboardType?: 'default' | 'email-address' | 'number-pad';
  /**
   * What the OS password manager should offer here.
   *
   * Worth setting on every credential field. It is also the half of the
   * arrangement that `webcredentials` in the association document completes:
   * with both, iOS offers the password already saved for the website.
   */
  textContentType?: 'username' | 'password' | 'newPassword' | 'emailAddress' | 'oneTimeCode';
  autoComplete?: 'username' | 'email' | 'current-password' | 'new-password' | 'one-time-code';
  multiline?: boolean;
}

export function FormField<T extends FieldValues>({
  control,
  name,
  label,
  serverError,
  helperText,
  secureTextEntry,
  autoCapitalize = 'none',
  keyboardType = 'default',
  textContentType,
  autoComplete,
  multiline,
}: FormFieldProps<T>) {
  const theme = useTheme<AppTheme>();

  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { onChange, onBlur, value }, fieldState: { error } }) => {
        const message = error?.message ?? serverError;

        return (
          <View style={{ marginBottom: theme.spacing(1) }}>
            <TextInput
              mode="outlined"
              label={label}
              value={value ?? ''}
              onChangeText={onChange}
              onBlur={onBlur}
              error={Boolean(message)}
              secureTextEntry={secureTextEntry}
              autoCapitalize={autoCapitalize}
              keyboardType={keyboardType}
              textContentType={textContentType}
              autoComplete={autoComplete}
              multiline={multiline}
              // Announced by the screen reader instead of the placeholder,
              // which a floating label hides once there is a value.
              accessibilityLabel={label}
            />
            {/* `visible` rather than a conditional render: HelperText keeps
                its height reserved, so the form does not jump when an error
                appears under a field the user is still typing in. */}
            <HelperText type={message ? 'error' : 'info'} visible={Boolean(message || helperText)}>
              {message ?? helperText ?? ' '}
            </HelperText>
          </View>
        );
      }}
    />
  );
}
