import { AppBar, Box, Button, Toolbar, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../../store/auth';
import { useToast } from '../../store/toast';

export default function Header() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const { isAuthenticated, isLoading, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    toast.success(t('loggedOut'));
    navigate('/');
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          <Box
            component={Link}
            to="/"
            sx={{ color: 'inherit', textDecoration: 'none' }}
          >
            {t('appName')}
          </Box>
        </Typography>
        {/* Render nothing until the session is known, so the nav does not
            flicker from signed-out to signed-in on every page load. */}
        {!isLoading && (
          <Box>
            {isAuthenticated ? (
              <>
                <Button color="inherit" onClick={() => navigate('/profile')}>
                  {t('profile')}
                </Button>
                <Button color="inherit" onClick={handleLogout}>
                  {t('logout')}
                </Button>
              </>
            ) : (
              <>
                <Button color="inherit" onClick={() => navigate('/login')}>
                  {t('login')}
                </Button>
                <Button color="inherit" onClick={() => navigate('/signup')}>
                  {t('signup')}
                </Button>
              </>
            )}
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
}
