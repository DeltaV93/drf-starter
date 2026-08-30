/**
 * The app manifest, checked for the values that are easy to get wrong quietly.
 */

import config from '../../app.config';
import { version as packageVersion } from '../../package.json';

describe('app.config.ts', () => {
  it('takes its version from package.json rather than a literal of its own', () => {
    // Two copies drift the first time someone runs `npm version` and does not
    // think to edit the manifest. The store then shows one number and the
    // upgrade gate compares against the other.
    expect(config.version).toBe(packageVersion);
  });

  it('sets no build number, because EAS manages that remotely', () => {
    // eas.json declares appVersionSource: "remote". A buildNumber or
    // versionCode written here would be the value EAS initialises *from* and
    // then diverge from, which reads as builds silently reusing a number.
    expect(config.ios?.buildNumber).toBeUndefined();
    expect(config.android?.versionCode).toBeUndefined();
  });

  it('derives the runtime version from the native fingerprint', () => {
    // Not appVersion: that makes an update's compatibility depend on someone
    // remembering to bump a number when they add native code. The fingerprint
    // changes by itself when the runtime does, so an update cannot reach a
    // build it was not made for.
    expect(config.runtimeVersion).toEqual({ policy: 'fingerprint' });
  });
});
