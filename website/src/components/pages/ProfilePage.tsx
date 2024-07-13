import React, { useEffect, useState } from 'react';
import { Typography, Container, Box, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAtom } from 'jotai';
import { authAtom } from '../../store/auth';
import { apiCall } from '../../utils/api';
import {routes} from '../../lib/routes';

const ProfilePage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isAuthenticated] = useAtom(authAtom().isAuthenticated);
  const [user] = useAtom(authAtom().user);
  const [, dispatch] = useAtom(authAtom().authActions);
  const [profileData, setProfileData] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await apiCall(routes.api.user.profile(), 'GET');
        setProfileData(response);
      } catch (error) {
        console.error('Error fetching profile:', error);
        // Handle error (show toast, etc.)
      }
    };

    if (isAuthenticated) {
      fetchProfile();
    }
  }, [isAuthenticated]);

  const handleLogout = () => {
    dispatch({ type: 'LOGOUT' });
    navigate('/');
  };

  // if (!isAuthenticated) {
  //   navigate('/login');
  //   return null;
  // }

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('profile')}
        </Typography>
        {user && (
          <Box>
            <Typography variant="body1">{t('name')}: {user.name || 'user.name' }</Typography>
            <Typography variant="body1">{t('email')}: {user.email || 'user.email' }</Typography>
            {/* Add more profile information as needed */}
          </Box>
        )}
        {profileData && (
          <Box>
            {/* Add additional profile data here if needed */}
          </Box>
        )}
        <Button variant="contained" color="primary" onClick={handleLogout} sx={{ mt: 3 }}>
          {t('logout')}
        </Button>
      </Box>
    </Container>
  );
};

export default ProfilePage;