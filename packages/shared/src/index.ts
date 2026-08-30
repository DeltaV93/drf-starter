/**
 * Everything the website and the mobile app share.
 *
 * Subpath imports (`@app/shared/brand`, `@app/shared/types`) are the ones to
 * reach for at a call site -- they keep the import list honest about what a
 * module actually depends on. This barrel exists for the few places that want
 * the lot, and for tooling that resolves the package root.
 */

export * from './api';
export * from './brand';
export * from './passwordValidation';
export * from './routes';
export * from './types';
