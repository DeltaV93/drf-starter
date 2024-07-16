import React from 'react';
import { Typography, Button, Container, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAtom } from 'jotai';
import {isAuthenticatedAtom} from '../../store/auth.tsx';

const HomePage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isAuthenticated] = useAtom(isAuthenticatedAtom);

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h2" component="h1" gutterBottom>
          {t('welcome')}
        </Typography>
        {isAuthenticated ? (
          <Button variant="contained" color="primary" onClick={() => navigate('/profile')}>
            {t('goToProfile')}
          </Button>
        ) : (
          <Box>
            <Button variant="contained" color="primary" onClick={() => navigate('/login')} sx={{ mr: 2 }}>
              {t('login')}
            </Button>
            <Button variant="outlined" color="primary" onClick={() => navigate('/signup')}>
              {t('signup')}
            </Button>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default HomePage;