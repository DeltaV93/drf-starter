/**
 * Transient messages.
 *
 * The same shape as the website's store, deliberately, so a screen ported
 * between the two does not have to relearn it. The one difference is that
 * only one is shown at a time -- a phone has no room for a stack, and Paper's
 * Snackbar occupies the bottom of the screen where the tab bar already is.
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

  // Memoised as a whole, for the reason the website's version records: every
  // member was already stable, but a fresh object each render makes `toast`
  // in an effect's dependency array change every time -- and a screen that
  // fetches in that effect fetches forever, invisibly.
  return useMemo(
    () => ({ show, dismiss, success, error, info, warning }),
    [show, dismiss, success, error, info, warning],
  );
}

export function useToasts() {
  return useAtomValue(toastsAtom);
}
