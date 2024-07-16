import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { TextField, Button, Typography, Box, List, ListItem } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { apiCall } from '../../utils/api';
import { usePasswordValidation } from '../../hooks/usePasswordValidation';
import { getToast } from '../../store/toast';
import {routes} from "../../libs/routes.ts";

interface ConfirmPasswordForm {
  password: string;
  confirmPassword: string;
}

const ConfirmNewPasswordPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { userId, token } = useParams<{ userId: string; token: string }>();
  const [isValidToken, setIsValidToken] = useState(false);
  const { control, handleSubmit, watch } = useForm<ConfirmPasswordForm>();
  const password = watch('password', '');
  const confirmPassword = watch('confirmPassword', '');
  const { isValid, errors } = usePasswordValidation(password, confirmPassword);
  const toast = getToast();

  useEffect(() => {
    const verifyToken = async () => {
      try {
        const response = await apiCall({
          method: 'GET',
          url: routes.api.auth.confirmPasswordToken(userId, token),
        });
        if(response.data.status == "success"){
          setIsValidToken(response.data.data.is_valid);
        }
      } catch (error) {
        console.error('Token verification error:', error);
        toast.error(t('invalidResetLink'));
      }
    };

    verifyToken();
  }, [userId, token, navigate, t, toast]);

  const onSubmit = async (data: ConfirmPasswordForm) => {
    if (data.password !== data.confirmPassword) {
      toast.error(t('passwordsDontMatch'));
      return;
    }

    if (!isValid) {
      toast.error(t('passwordRequirements'));
      return;
    }

    try {
      await apiCall({
        method: 'POST',
        url: routes.api.auth.passwordReset(),
        data: { userId, token, newPassword: data.password },
      });
      toast.success(t('passwordResetSuccess'));
      navigate('/login');
    } catch (error) {
      console.error('Password reset error:', error);
      toast.error(t('passwordResetError'));
    }
  };

  return (
    <Box sx={{ maxWidth: 400, margin: 'auto', mt: 4 }}>

            {isValidToken ? (
              <>
              <Typography variant="h4" component="h1" gutterBottom>
                {t('resetPassword')}
              </Typography>
              <form onSubmit={handleSubmit(onSubmit)}>
                <Controller
                  name="password"
                  control={control}
                  defaultValue=""
                  rules={{ required: t('passwordRequired') }}
                  render={({ field, fieldState: { error } }) => (
                    <TextField
                      {...field}
                      type="password"
                      label={t('newPassword')}
                      fullWidth
                      margin="normal"
                      error={!!error}
                      helperText={error?.message}
                    />
                  )}
                />
                <Controller
                  name="confirmPassword"
                  control={control}
                  defaultValue=""
                  rules={{ required: t('confirmPasswordRequired') }}
                  render={({ field, fieldState: { error } }) => (
                    <TextField
                      {...field}
                      type="password"
                      label={t('confirmPassword')}
                      fullWidth
                      margin="normal"
                      error={!!error}
                      helperText={error?.message}
                    />
                  )}
                />
                {errors.length > 0 && (
                  <List>
                    {errors.map((error, index) => (
                      <ListItem key={index}>
                        <Typography color="error">{error}</Typography>
                      </ListItem>
                    ))}
                  </List>
                )}
                <Button type="submit" disabled={!isValid} fullWidth variant="contained" color="primary" sx={{ mt: 3 }}>
                  {t('resetPassword')}
                </Button>
              </form>
              </>
            ) : (
              <>
                <Typography>{t('verifyingToken')}</Typography>
              </>
            )}

    </Box>
  );
};

export default ConfirmNewPasswordPage;