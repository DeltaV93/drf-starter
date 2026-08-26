import { AppBar, Box, Button, Toolbar, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';


import { useAuth } from '../../store/auth';
import { identity } from '../../styles/brand';
import { useToast } from '../../store/toast';
import ColorSchemeToggle from './ColorSchemeToggle';

// Keep in step with UPLOADS_ENABLED on the backend, or the link leads to
// a page whose calls 404.
const UPLOADS_ENABLED = import.meta.env.VITE_UPLOADS_ENABLED === 'true';
// Same contract for MCP_CLIENT_ENABLED.
const MCP_CLIENT_ENABLED = import.meta.env.VITE_MCP_CLIENT_ENABLED === 'true';

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
            {identity.name}
          </Box>
        </Typography>
        <ColorSchemeToggle />
        {/* Render nothing until the session is known, so the nav does not
            flicker from signed-out to signed-in on every page load. */}
        {!isLoading && (
          <Box>
            {isAuthenticated ? (
              <>
                <Button color="inherit" onClick={() => navigate('/profile')}>
                  {t('profile')}
                </Button>
                {UPLOADS_ENABLED && (
                  <Button color="inherit" onClick={() => navigate('/files')}>
                    {t('files')}
                  </Button>
                )}
                {MCP_CLIENT_ENABLED && (
                  <Button color="inherit" onClick={() => navigate('/connections')}>
                    {t('connections')}
                  </Button>
                )}
                <Button color="inherit" onClick={() => navigate('/security')}>
                  {t('security')}
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
