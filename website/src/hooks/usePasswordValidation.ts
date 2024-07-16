import { useState, useEffect } from 'react';

interface PasswordValidation {
  isValid: boolean;
  errors: string[];
}

export const usePasswordValidation = (password: string, confirmPassword: string): PasswordValidation => {
  const [isValid, setIsValid] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    const newErrors: string[] = [];

    if (password.length < 8) {
      newErrors.push('Password must be at least 8 characters long');
    }
    if (!/[A-Z]/.test(password)) {
      newErrors.push('Password must contain at least one uppercase letter');
    }
    if (!/[a-z]/.test(password)) {
      newErrors.push('Password must contain at least one lowercase letter');
    }
    if (!/[0-9]/.test(password)) {
      newErrors.push('Password must contain at least one number');
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      newErrors.push('Password must contain at least one special character');
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      newErrors.push('Password must contain at least one special character');
    }

    if (password !== confirmPassword) {
      newErrors.push('Passwords much match each other');
    }

    setErrors(newErrors);
    setIsValid(newErrors.length === 0);
  }, [password, confirmPassword]);

  return { isValid, errors };
};