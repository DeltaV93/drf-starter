/**
 * Toast notifications.
 *
 * Toasts are transient UI, so they live in a plain atom -- persisting them to
 * storage (as the previous version did) meant stale messages reappeared on
 * every reload.
 */

import { atom, useAtomValue, useSetAtom } from 'jotai';
import { useCallback } from 'react';

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

  return {
    show,
    dismiss,
    success: useCallback(
      (message: string, duration?: number) => show('success', message, duration),
      [show],
    ),
    error: useCallback(
      (message: string, duration?: number) => show('error', message, duration),
      [show],
    ),
    info: useCallback(
      (message: string, duration?: number) => show('info', message, duration),
      [show],
    ),
    warning: useCallback(
      (message: string, duration?: number) => show('warning', message, duration),
      [show],
    ),
  };
}

export function useToasts() {
  return useAtomValue(toastsAtom);
}
