import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

/**
 * Give the test environment a working `localStorage`.
 *
 * Node 26 defines its own `localStorage` on `globalThis`, and it is
 * `undefined` unless the process was started with `--localstorage-file`.
 * jsdom cannot help: under Vitest `window === globalThis`, so Node's getter
 * shadows the one jsdom would otherwise install, and every read is
 * `undefined` rather than a Storage.
 *
 * The failure is quiet and version-dependent -- the suite passes on Node 22
 * and dies on 26 with `Cannot read properties of undefined`, which reads like
 * a broken test rather than a missing global. The application itself is fine:
 * a browser always has storage, and MUI already copes when it does not.
 *
 * Installed only when there is nothing usable there, so a future Node that
 * provides a real one is left alone.
 */
function installLocalStorage() {
  if (typeof globalThis.localStorage?.getItem === 'function') return;

  class MemoryStorage implements Storage {
    #entries = new Map<string, string>();

    get length() {
      return this.#entries.size;
    }

    key(index: number) {
      return [...this.#entries.keys()][index] ?? null;
    }

    getItem(key: string) {
      return this.#entries.get(String(key)) ?? null;
    }

    setItem(key: string, value: string) {
      // Storage coerces both, and a test that sets a number should behave the
      // way the browser will.
      this.#entries.set(String(key), String(value));
    }

    removeItem(key: string) {
      this.#entries.delete(String(key));
    }

    clear() {
      this.#entries.clear();
    }
  }

  for (const name of ['localStorage', 'sessionStorage'] as const) {
    Object.defineProperty(globalThis, name, {
      value: new MemoryStorage(),
      configurable: true,
      writable: true,
    });
  }
}

installLocalStorage();

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeEach(() => {
  // Cookies persist across tests in jsdom; clear them so a CSRF cookie set
  // by one test cannot silently satisfy the next.
  for (const cookie of document.cookie.split(';')) {
    const name = cookie.split('=')[0]?.trim();
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }

  // Storage persists across tests the same way, and a remembered colour
  // scheme would make the next test's starting state depend on the last.
  globalThis.localStorage?.clear();
});
