/**
 * Toast notifications.
 *
 * Toasts are transient UI, so they live in a plain atom -- persisting them to
 * storage (as the previous version did) meant stale messages reappeared on
 * every reload.
 */

import { atom, useAtomValue, useSetAtom } from 'jotai';
import { useCallback, useMemo } from 'react';

export type ToastSeverity = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  id: string;
  severity: ToastSeverity;
  message: string;
  duration: number;
}

export const toastsAtom = atom<ToastMessage[]>([]);

let nextId = 0;

export function useToast() {
  const setToasts = useSetAtom(toastsAtom);

  const dismiss = useCallback(
    (id: string) => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    },
    [setToasts],
  );

  const show = useCallback(
    (severity: ToastSeverity, message: string, duration = 5000) => {
      // Date.now() alone collides when two toasts fire in the same tick.
      const id = `${Date.now()}-${nextId++}`;
      setToasts((current) => [...current, { id, severity, message, duration }]);
      return id;
    },
    [setToasts],
  );

  const success = useCallback(
    (message: string, duration?: number) => show('success', message, duration),
    [show],
  );
  const error = useCallback(
    (message: string, duration?: number) => show('error', message, duration),
    [show],
  );
  const info = useCallback(
    (message: string, duration?: number) => show('info', message, duration),
    [show],
  );
  const warning = useCallback(
    (message: string, duration?: number) => show('warning', message, duration),
    [show],
  );

  // Memoised as a whole, and that matters more than it looks.
  //
  // Every member was already stable, but the object around them was rebuilt
  // on each render -- so `toast` in an effect's dependency array changed every
  // time. Pages fetch in an effect that lists `toast` (it reports failures),
  // set state with the result, re-render, get a new `toast`, and fetch again:
  // a page that loads a list once was loading it continuously.
  //
  // Nothing looked wrong. The list was correct, the page rendered, and the
  // requests were invisible without opening the network tab.
  return useMemo(
    () => ({ show, dismiss, success, error, info, warning }),
    [show, dismiss, success, error, info, warning],
  );
}

export function useToasts() {
  return useAtomValue(toastsAtom);
}
