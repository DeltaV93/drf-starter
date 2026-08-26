import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { http } from '../../lib/api';
import { renderWithProviders, screen, waitFor, within } from '../../test/utils';
import ConnectionsPage from './ConnectionsPage';

function server(overrides = {}) {
  return {
    slug: 'example',
    label: 'Example MCP server',
    description: 'A placeholder connection.',
    transport: 'connector',
    requires_user_credential: false,
    allowed_tools: ['search', 'fetch'],
    connected: false,
    enabled: false,
    last_used_at: null,
    ...overrides,
  };
}

function mockList(...servers: ReturnType<typeof server>[]) {
  return vi
    .spyOn(http, 'request')
    .mockResolvedValue({ data: { status: 'success', data: servers } });
}

describe('ConnectionsPage', () => {
  beforeEach(() => {
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { status: 'success', data: { csrfToken: 'test-token' } },
    });
  });

  it('lists what a connection would be able to do, before anyone agrees to it', async () => {
    // A connection screen that does not name the tools is asking for consent
    // to something unnamed.
    mockList(server());
    renderWithProviders(<ConnectionsPage />);

    expect(await screen.findByText('Example MCP server')).toBeInTheDocument();
    expect(screen.getByText('search')).toBeInTheDocument();
    expect(screen.getByText('fetch')).toBeInTheDocument();
  });

  it('warns when a server is not restricted to a tool list', async () => {
    // `allowed_tools: null` means the server can add a tool at any time and
    // it arrives unreviewed. That is worth saying out loud.
    mockList(server({ allowed_tools: null }));
    renderWithProviders(<ConnectionsPage />);

    expect(await screen.findByText(/every tool this server offers/i)).toBeInTheDocument();
  });

  it('sends the token to the connect endpoint', async () => {
    const request = mockList(server());
    renderWithProviders(<ConnectionsPage />);

    await userEvent.click(await screen.findByRole('button', { name: /^connect$/i }));
    await userEvent.type(screen.getByLabelText(/token/i), 'sk-secret');

    // Scoped to the dialog: the card behind it still has a Connect button,
    // and picking by document order would silently reopen the dialog instead.
    const dialog = within(screen.getByRole('dialog'));
    await userEvent.click(dialog.getByRole('button', { name: /^connect$/i }));

    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'put',
          url: '/api/v1/mcp/servers/example/',
          data: { credential: 'sk-secret', enabled: true },
        }),
      ),
    );
  });

  it('offers disconnect rather than connect once connected', async () => {
    mockList(server({ connected: true, enabled: true }));
    renderWithProviders(<ConnectionsPage />);

    expect(await screen.findByRole('button', { name: /disconnect/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^connect$/i })).not.toBeInTheDocument();
  });

  it('says nothing is on offer rather than rendering an empty page', async () => {
    mockList();
    renderWithProviders(<ConnectionsPage />);

    expect(await screen.findByText(/offers no connections/i)).toBeInTheDocument();
  });

  it('loads the list once rather than in a loop', async () => {
    // `useToast()` used to return a fresh object every render. Pages list
    // `toast` in the effect's dependencies (it reports failures), so the
    // effect re-ran after every state update: fetch, set state, re-render,
    // fetch again. The list was correct and the page rendered, so nothing
    // looked wrong without the network tab open -- this page made 16 requests
    // to load one list before the hook was memoised.
    const request = mockList(server());
    renderWithProviders(<ConnectionsPage />);

    await screen.findByText('Example MCP server');
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(request).toHaveBeenCalledTimes(1);
  });

  it('starts the token field empty even for a connected server', async () => {
    // The API never returns a stored credential, so there is nothing to
    // prefill -- and a masked placeholder would imply otherwise.
    mockList(server({ connected: true, enabled: true }));
    renderWithProviders(<ConnectionsPage />);

    await screen.findByRole('button', { name: /disconnect/i });
    expect(screen.queryByLabelText(/token/i)).not.toBeInTheDocument();
  });
});
