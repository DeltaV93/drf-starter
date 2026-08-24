import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';

import { renderWithProviders, screen } from '../../test/utils';
import ColorSchemeToggle from './ColorSchemeToggle';

describe('ColorSchemeToggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-mui-color-scheme');
  });

  it('offers light, dark and following the system', async () => {
    renderWithProviders(<ColorSchemeToggle />);

    await userEvent.click(screen.getByRole('button', { name: /appearance/i }));

    // Three options, not two: a light/dark switch has no way back to
    // "follow my system" once it has been touched.
    expect(screen.getByRole('menuitem', { name: 'Light' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Dark' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'System' })).toBeInTheDocument();
  });

  it('applies the choice to the document and remembers it', async () => {
    renderWithProviders(<ColorSchemeToggle />);

    await userEvent.click(screen.getByRole('button', { name: /appearance/i }));
    await userEvent.click(screen.getByRole('menuitem', { name: 'Dark' }));

    // The attribute is what the stylesheet keys off, and what the inline
    // script in index.html re-applies on the next visit.
    expect(document.documentElement.getAttribute('data-mui-color-scheme')).toBe('dark');
    expect(localStorage.getItem('mui-mode')).toBe('dark');
  });

  it('goes back to following the system', async () => {
    renderWithProviders(<ColorSchemeToggle />);

    await userEvent.click(screen.getByRole('button', { name: /appearance/i }));
    await userEvent.click(screen.getByRole('menuitem', { name: 'Dark' }));
    await userEvent.click(screen.getByRole('button', { name: /appearance/i }));
    await userEvent.click(screen.getByRole('menuitem', { name: 'System' }));

    expect(localStorage.getItem('mui-mode')).toBe('system');
  });
});
