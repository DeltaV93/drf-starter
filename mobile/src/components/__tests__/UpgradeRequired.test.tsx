import * as Linking from 'expo-linking';

import { renderWithProviders, userEvent } from '../../test/utils';
import { UpgradeRequired } from '../UpgradeRequired';

const base = {
  requirement: 'required' as const,
  minimum_version: '2.0.0',
  recommended_version: '',
  store_url: 'https://apps.apple.com/app/id1',
  message: '',
};

it('offers a way to the store', async () => {
  const openURL = jest.spyOn(Linking, 'openURL').mockResolvedValue(true);

  const user = userEvent.setup();
  const view = await renderWithProviders(<UpgradeRequired check={base} />);
  await user.press(view.getByText('Update'));

  expect(openURL).toHaveBeenCalledWith('https://apps.apple.com/app/id1');
});

it('says what to do when no store listing is configured', async () => {
  // A wall with a button that does nothing is worse than a wall that
  // explains itself.
  const view = await renderWithProviders(<UpgradeRequired check={{ ...base, store_url: '' }} />);

  expect(view.queryByText('Update')).toBeNull();
  expect(view.getByText(/App Store or Google Play/)).toBeTruthy();
});

it('prefers the message the admin wrote', async () => {
  // During an incident the specific sentence is worth more than the
  // translated generic one.
  const view = await renderWithProviders(
    <UpgradeRequired check={{ ...base, message: 'Version 1 could lose drafts.' }} />,
  );

  expect(view.getByText('Version 1 could lose drafts.')).toBeTruthy();
});

it('offers no way past it', async () => {
  /**
   * There is deliberately no dismiss, no "continue anyway", no back. If a
   * build is bad enough to refuse, the people most likely to take an escape
   * hatch are the ones the refusal was for.
   */
  const view = await renderWithProviders(<UpgradeRequired check={base} />);

  for (const escape of [/continue/i, /not now/i, /later/i, /dismiss/i, /skip/i]) {
    expect(view.queryByText(escape)).toBeNull();
  }
});
