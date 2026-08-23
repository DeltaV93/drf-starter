import { CssBaseline } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import { Provider } from 'jotai';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { I18nextProvider } from 'react-i18next';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import i18n from './i18n';
import theme from './styles/theme';

const container = document.getElementById('root');
if (!container) throw new Error('No #root element found in index.html');

createRoot(container).render(
  <StrictMode>
    {/* Provider is at the root so every route shares one jotai store; it used
        to sit inside App, which reset auth state on each remount. */}
    <Provider>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <I18nextProvider i18n={i18n}>
            <App />
          </I18nextProvider>
        </ThemeProvider>
      </BrowserRouter>
    </Provider>
  </StrictMode>,
);
