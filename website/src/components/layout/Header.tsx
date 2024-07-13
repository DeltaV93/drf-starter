  import React from 'react';
  import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
  import {Link, useNavigate} from 'react-router-dom';
  import { useTranslation } from 'react-i18next';
  import { useAtom } from 'jotai';
  import { isAuthenticatedAtom, authActionsAtom } from '../../store/auth';

  const Header: React.FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [isAuthenticated] = useAtom(isAuthenticatedAtom);
    const [, dispatch] = useAtom(authActionsAtom);

    const handleLogout = () => {
      dispatch({ type: "LOGOUT" });
      navigate('/');
    };

    return (
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            <Link to="/">
              {t('appName')}
            </Link>
          </Typography>
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
        </Toolbar>
      </AppBar>
    );
  };

  export default Header;