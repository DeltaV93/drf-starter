/**
 * What a failure says to the person holding the phone.
 *
 * Three cases the previous version collapsed into one generic sentence:
 * being offline, being throttled, and the server actually refusing. Only the
 * third has anything useful in its message.
 */

import { ApiError } from '../api';
// Through the test helper, which initialises the real i18next instance --
// without it every `t()` returns the key rather than the sentence.
import { renderHook } from '../../test/utils';
import { useErrorMessage } from '../useErrorMessage';

async function describe_(error: unknown, fallback?: string) {
  const view = await renderHook(() => useErrorMessage());
  return view.result.current(error, fallback);
}

it('says you are offline when the request never reached the server', async () => {
  // No status: no signal, a captive portal, the host unreachable. The
  // backend's wording cannot help because the backend never saw it.
  const error = new ApiError('Request failed');

  expect(await describe_(error)).toMatch(/offline/i);
});

it('shows the backend its own words when it refused', async () => {
  const error = new ApiError('That email is already registered.', 400, {}, true);

  expect(await describe_(error)).toBe('That email is already registered.');
});

it('does not show a message the backend never sent', async () => {
  // `fromServer` false means the text was invented up the stack, in whatever
  // language that code was written in.
  const error = new ApiError('Request failed with status code 500', 500, {}, false);

  expect(await describe_(error, 'couldNotLoadFiles')).toBe('Could not load your files.');
});

describe('when throttled', () => {
  it('says how long to wait, in seconds', async () => {
    const error = new ApiError('Too many requests', 429, {}, true, 45);

    expect(await describe_(error)).toBe('Too many attempts. Try again in 45 seconds.');
  });

  it('rounds up to whole minutes', async () => {
    // Telling someone to wait 59 seconds when the answer is a minute invites
    // them to try at 58 and fail again.
    const error = new ApiError('Too many requests', 429, {}, true, 61);

    expect(await describe_(error)).toBe('Too many attempts. Try again in 2 minutes.');
  });

  it('never says to wait zero seconds', async () => {
    const error = new ApiError('Too many requests', 429, {}, true, 0);

    expect(await describe_(error)).toBe('Too many attempts. Try again in 1 second.');
  });

  it('falls back when the header is missing', async () => {
    const error = new ApiError('Too many requests', 429, {}, true);

    expect(await describe_(error)).toBe('Too many attempts. Try again in a moment.');
  });
});
