import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

export interface PasswordValidation {
  isValid: boolean;
  errors: string[];
}

/**
 * Client-side password checks.
 *
 * These mirror Django's default AUTH_PASSWORD_VALIDATORS: at least 8
 * characters and not entirely numeric. Deliberately no uppercase/symbol
 * rules -- the previous version required them, so it rejected passwords the
 * backend would happily accept, and the two never agreed.
 *
 * If you tighten AUTH_PASSWORD_VALIDATORS on the backend, tighten this to
 * match. The server remains the authority either way.
 */
export function usePasswordValidation(
  password: string,
  confirmPassword?: string,
): PasswordValidation {
  const { t } = useTranslation();

  return useMemo(() => {
    const errors: string[] = [];

    if (password.length < 8) {
      errors.push(t('passwordTooShort'));
    }
    if (password.length > 0 && /^\d+$/.test(password)) {
      errors.push(t('passwordAllNumeric'));
    }
    if (confirmPassword !== undefined && password !== confirmPassword) {
      errors.push(t('passwordsDontMatch'));
    }

    return { isValid: errors.length === 0, errors };
  }, [password, confirmPassword, t]);
}

export default usePasswordValidation;
