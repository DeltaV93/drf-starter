import React from 'react';
import {useForm, Controller} from 'react-hook-form';
import {TextField, Button, Container, Box, Typography} from '@mui/material';
import {useNavigate} from 'react-router-dom';
import {useTranslation} from 'react-i18next';
import {apiCall} from '../../utils/api';
import {routes} from '../../libs/routes';

interface PasswordResetForm {
    email: string;
}

const PasswordResetPage: React.FC = () => {
    const {t} = useTranslation();
    const navigate = useNavigate();
    const {control, handleSubmit} = useForm<PasswordResetForm>();

    const onSubmit = async (data: PasswordResetForm) => {
        try {
            await apiCall({
                "url": routes.api.auth.passwordReset(),
                "method":'POST',
                "data":data});
            // Show success message
            navigate('/login');
        } catch (error) {
            console.error('Password reset error:', error);
            // Handle error (show toast, etc.)
        }
    };

    return (
        <Container maxWidth="xs">
            <Box sx={{mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
                <Typography variant="h4" component="h1" gutterBottom>
                    {t('resetPassword')}
                </Typography>
                <form onSubmit={handleSubmit(onSubmit)} style={{width: '100%'}}>
                    <Controller
                        name="email"
                        control={control}
                        defaultValue=""
                        rules={{
                            required: t('emailRequired'),
                            pattern: {value: /^\S+@\S+$/i, message: t('invalidEmail')}
                        }}
                        render={({field, fieldState: {error}}) => (
                            <TextField
                                {...field}
                                label={t('email')}
                                fullWidth
                                margin="normal"
                                error={!!error}
                                helperText={error?.message}
                            />
                        )}
                    />
                    <Button type="submit" fullWidth variant="contained" color="primary" sx={{mt: 3, mb: 2}}>
                        {t('sendResetLink')}
                    </Button>
                </form>
            </Box>
        </Container>
    );
};

export default PasswordResetPage;