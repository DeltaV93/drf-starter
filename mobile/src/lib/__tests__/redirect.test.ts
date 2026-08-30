import { appRoutes } from '@app/shared/routes';

import { DEFAULT_DESTINATION, safeRedirect } from '../redirect';

describe('resuming a flow after sign-in', () => {
  it('keeps an in-app path', () => {
    expect(safeRedirect('/invitations/abc123')).toBe('/invitations/abc123');
  });

  it('falls back when nothing was asked for', () => {
    expect(safeRedirect(undefined)).toBe(DEFAULT_DESTINATION);
    expect(safeRedirect('')).toBe(DEFAULT_DESTINATION);
  });

  it('takes the first when the parameter repeats', () => {
    // expo-router hands back an array for a duplicated query parameter, and
    // `'/a,/b'` would be neither path.
    expect(safeRedirect(['/files', '/profile'])).toBe('/files');
  });
});

describe('refusing to leave the app', () => {
  // The value arrives from outside: anyone can send a
  // `drfstarter://login?redirect=...` link. Following one off-app is the
  // mobile shape of an open redirect, and it is most convincing precisely
  // because the person just signed in to the real app.
  it.each([
    ['https://evil.example.com', 'an absolute URL'],
    ['//evil.example.com', 'a protocol-relative URL'],
    ['/\\evil.example.com', 'a backslash some parsers read as a slash'],
    ['drfstarter://login', 'another scheme'],
    ['profile', 'a relative path with no leading slash'],
    ['/path?x=https://evil.example.com', 'a nested absolute URL'],
  ])('refuses %s (%s)', (value) => {
    expect(safeRedirect(value)).toBe(DEFAULT_DESTINATION);
  });

  it('falls back rather than throwing, so a stale link still signs you in', () => {
    expect(safeRedirect('nonsense')).toBe(DEFAULT_DESTINATION);
  });
});

describe('the default', () => {
  it('is the profile, taken from the shared route table', () => {
    expect(DEFAULT_DESTINATION).toBe(appRoutes.profile);
  });
});
