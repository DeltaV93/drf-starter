  import { atom } from 'jotai';
  import { atomWithStorage } from 'jotai/utils';

  interface User {
    id: string;
    email: string;
    name: string;
    // Add any other user properties you need
  }

  // Define the structure of the auth state
  interface AuthState {
    isAuthenticated: boolean;
    user: User | null;
    token: string | null;
  }

  const initialState: AuthState = {
    isAuthenticated: false,
    user: null,
    token: null,
  };

  // Create a persisted atom for the auth state
  const persistedAuthAtom = atomWithStorage<AuthState>('auth', initialState);

  // Create derived atoms for individual properties
  export const isAuthenticatedAtom = atom(
    (get) => get(persistedAuthAtom).isAuthenticated
  );

  export const userAtom = atom(
    (get) => get(persistedAuthAtom).user
  );

  export const tokenAtom = atom(
    (get) => get(persistedAuthAtom).token
  );

  // Create an atom for auth actions
  export const authActionsAtom = atom(
    null, // Read function returns null as we don't need to read from this atom
    (get, set, action: { type: string; payload?: any }) => {
      switch (action.type) {
        case 'LOGIN':
          set(persistedAuthAtom, {
            isAuthenticated: true,
            user: action.payload.user,
            token: action.payload.token,
          });
          break;
        case 'LOGOUT':
          set(persistedAuthAtom, initialState);
          break;
        case 'UPDATE_USER':
          set(persistedAuthAtom, (prev) => ({
            ...prev,
            user: { ...prev.user, ...action.payload },
          }));
          break;
        default:
          console.warn('Unknown action type:', action.type);
      }
    }
  );

  export function authAtom() {
    return {
      authState: persistedAuthAtom,
      isAuthenticated: isAuthenticatedAtom,
      user: userAtom,
      token: tokenAtom,
      authActions: authActionsAtom,
    };
  }