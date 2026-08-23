import { Box, Button, Container, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { useAuth } from '../../store/auth';

export default function HomePage() {
  const { t } = useTranslation();
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h2" component="h1" gutterBottom align="center">
          {t('welcome')}
        </Typography>

        {!isLoading &&
          (isAuthenticated ? (
            <Button component={Link} to="/profile" variant="contained">
              {t('goToProfile')}
            </Button>
          ) : (
            <Box>
              <Button component={Link} to="/login" variant="contained" sx={{ mr: 2 }}>
                {t('login')}
              </Button>
              <Button component={Link} to="/signup" variant="outlined">
                {t('signup')}
              </Button>
            </Box>
          ))}
      </Box>
    </Container>
  );
}
