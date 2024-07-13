import { atom } from 'jotai';
import { atomWithStorage } from 'jotai/utils';

// Define the structure of a toast message
export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
}

// Create an atom to store the current toast messages
export const toastAtom = atomWithStorage<ToastMessage[]>('toastMessages', []);

// Utility function to add a new toast message
export const addToast = (toast: Omit<ToastMessage, 'id'>) => {
  const id = Date.now().toString();
  return (prevToasts: ToastMessage[]) => [
    ...prevToasts,
    { ...toast, id },
  ];
};

// Utility function to remove a toast message
export const removeToast = (id: string) => (prevToasts: ToastMessage[]) =>
  prevToasts.filter((toast) => toast.id !== id);

// Create an atom for the toast manager functions
export const toastManagerAtom = atom(
  (get) => get(toastAtom),
  (get, set, action: { type: 'add' | 'remove'; payload: any }) => {
    switch (action.type) {
      case 'add':
        set(toastAtom, addToast(action.payload));
        break;
      case 'remove':
        set(toastAtom, removeToast(action.payload));
        break;
    }
  }
);

// Utility function to show a toast
export const showToast = (
  type: ToastMessage['type'],
  message: string,
  duration: number = 5000
) => {
  return ({ set }: { set: (atom: typeof toastManagerAtom, value: any) => void }) => {
    const newToast = { type, message };
    set(toastManagerAtom, { type: 'add', payload: newToast });

    // Automatically remove the toast after the specified duration
    setTimeout(() => {
      set(toastManagerAtom, { type: 'remove', payload: newToast.id });
    }, duration);
  };
};

// Create a getter for easy access to toast functions
export const getToast = () => ({
  success: (message: string, duration?: number) => showToast('success', message, duration),
  error: (message: string, duration?: number) => showToast('error', message, duration),
  info: (message: string, duration?: number) => showToast('info', message, duration),
  warning: (message: string, duration?: number) => showToast('warning', message, duration),
});