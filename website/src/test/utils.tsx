import { ThemeProvider } from '@mui/material/styles';
import { render, type RenderOptions } from '@testing-library/react';
import { Provider } from 'jotai';
import type { ReactElement, ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';

import i18n from '../i18n';
import type { User } from '@app/shared/types';
import theme from '../styles/theme';

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    username: 'ada',
    email: 'ada@example.com',
    first_name: 'Ada',
    last_name: 'Lovelace',
    display_name: 'Ada Lovelace',
    phone_number: '',
    account_type: 'FREE',
    role: 'USER',
    email_verified: true,
    date_joined: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

interface Options extends Omit<RenderOptions, 'wrapper'> {
  /** Initial history entries for the router. */
  routes?: string[];
}

/**
 * Render a component inside the same providers main.tsx sets up.
 *
 * A fresh jotai Provider per render keeps auth state from leaking between
 * tests.
 */
export function renderWithProviders(ui: ReactElement, { routes = ['/'], ...options }: Options = {}) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider>
        <MemoryRouter initialEntries={routes}>
          <ThemeProvider theme={theme}>
            <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
          </ThemeProvider>
        </MemoryRouter>
      </Provider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

export * from '@testing-library/react';
