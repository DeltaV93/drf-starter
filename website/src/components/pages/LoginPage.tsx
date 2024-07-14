import React from 'react';
import {Controller, useForm} from 'react-hook-form';
import {Box, Button, Container, TextField, Typography} from '@mui/material';
import {useNavigate} from 'react-router-dom';
import {useTranslation} from 'react-i18next';
import {useAtom} from 'jotai';
import {authAtom} from '../../store/auth';
import {apiCall} from '../../utils/api';
import {routes} from '../../libs/routes.ts';

interface LoginForm {
    username: string;
    password: string;
}

const LoginPage: React.FC = () => {
    const {t} = useTranslation();
    const navigate = useNavigate();
    const [, dispatch] = useAtom(authAtom().authActions)
    const {control, handleSubmit} = useForm<LoginForm>();

    const onSubmit = async (data: LoginForm) => {
        try {
            const response = await apiCall({
                url: routes.api.auth.login(),
                method: 'POST',
                data: data
            });
            dispatch({
                type: 'LOGIN',
                payload: {user: response.user, token: response.token}
            });
            navigate('/profile');
        } catch (error) {
            console.error('Login error:', error);
            // Handle error (show toast, etc.)
        }
    };

    return (
        <Container maxWidth="xs">
            <Box sx={{mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
                <Typography variant="h4" component="h1" gutterBottom>
                    {t('login')}
                </Typography>
                <form onSubmit={handleSubmit(onSubmit)} style={{width: '100%'}}>

                    <Controller
                        name="username"
                        control={control}
                        defaultValue=""
                        rules={{required: t('usernameRequired')}}
                        render={({field, fieldState: {error}}) => (
                            <TextField
                                {...field}
                                label={'username'}
                                fullWidth
                                type="text"
                                margin="normal"
                                error={!!error}
                                helperText={error?.message}
                            />
                        )}
                    />
                    <Controller
                        name="password"
                        control={control}
                        defaultValue=""
                        rules={{required: t('passwordRequired')}}
                        render={({field, fieldState: {error}}) => (
                            <TextField
                                {...field}
                                type="password"
                                label={t('password')}
                                fullWidth
                                margin="normal"
                                error={!!error}
                                helperText={error?.message}
                            />
                        )}
                    />
                    <Button type="submit" fullWidth variant="contained" color="primary" sx={{mt: 3, mb: 2}}>
                        {t('login')}
                    </Button>
                </form>
                <Button color="primary" onClick={() => navigate('/reset-password')}>
                    {t('forgotPassword')}
                </Button>
            </Box>
        </Container>
    );
};

export default LoginPage;