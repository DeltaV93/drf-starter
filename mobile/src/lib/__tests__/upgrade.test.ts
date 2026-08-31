/**
 * The version gate, tested mostly for the ways it must *not* fire.
 *
 * Every false positive here is an upgrade wall on a working app, cleared only
 * by a store release. The failure worth guarding against is not a missed
 * block; it is a block that should never have happened.
 */

import axios from 'axios';

import { checkForUpgrade } from '../upgrade';

jest.mock('axios', () => {
  const get = jest.fn();
  return { __esModule: true, default: { create: () => ({ get }), __get: get } };
});

const mockGet = (axios as unknown as { __get: jest.Mock }).__get;

function answers(data: unknown) {
  mockGet.mockResolvedValue({ data: { data } });
}

beforeEach(() => jest.clearAllMocks());

it('reports a required upgrade', async () => {
  answers({
    requirement: 'required',
    minimum_version: '2.0.0',
    recommended_version: '',
    store_url: 'https://apps.apple.com/app/id1',
    message: '',
  });

  const check = await checkForUpgrade();

  expect(check.requirement).toBe('required');
  expect(check.store_url).toBe('https://apps.apple.com/app/id1');
});

it('sends the platform and the running version', async () => {
  answers({ requirement: 'none' });

  await checkForUpgrade();

  const url = mockGet.mock.calls[0][0] as string;
  expect(url).toContain('platform=ios');
  expect(url).toContain('version=1.0.0');
});

it('carries on when the backend cannot be reached', async () => {
  // The important one. Offline, DNS, a captive portal, a deploy in progress.
  mockGet.mockRejectedValue(new Error('Network Error'));

  await expect(checkForUpgrade()).resolves.toMatchObject({ requirement: 'none' });
});

it('carries on when the answer is not the shape it expects', async () => {
  // An older backend with no such endpoint answers its own 404 page; a proxy
  // answers HTML. Neither must be able to produce a block by accident.
  mockGet.mockResolvedValue({ data: '<!doctype html><title>Not found</title>' });

  await expect(checkForUpgrade()).resolves.toMatchObject({ requirement: 'none' });
});

it('carries on when the requirement is a value it does not know', async () => {
  // A future backend adding a fourth answer must degrade to "carry on"
  // rather than to whatever the client's default branch happens to be.
  answers({ requirement: 'sunsetting' });

  await expect(checkForUpgrade()).resolves.toMatchObject({ requirement: 'none' });
});

it('fills in the fields a sparse answer leaves out', async () => {
  answers({ requirement: 'recommended' });

  const check = await checkForUpgrade();

  expect(check).toEqual({
    requirement: 'recommended',
    minimum_version: '',
    recommended_version: '',
    store_url: '',
    message: '',
  });
});
