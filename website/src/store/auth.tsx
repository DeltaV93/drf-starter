import {atom} from 'jotai';
import {atomWithStorage} from 'jotai/utils';
import {apiCall} from "../utils/api.tsx";

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


// Function to get CSRF token
export async function getCSRFToken(): Promise<string> {
    try {
        const response = await apiCall('/api/csrf/');
        return response.csrfToken;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        throw error;
    }
}

// const getCsrfToken = () => {
//   // const name = 'csrftoken';
//   const cookieValue = Cookies.get('csrftoken');
//   // if (document.cookie && document.cookie !== '') {
//   //   const cookies = document.cookie.split(';');
//   //   for (let i = 0; i < cookies.length; i++) {
//   //     const cookie = cookies[i].trim();
//   //     if (cookie.substring(0, name.length + 1) === (name + '=')) {
//   //       cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//   //       break;
//   //     }
//   //   }
//   // }
//   console.log(cookieValue, 'cookieValue', cookieValue)
//   return cookieValue;
// };

// Use this if you're not doing session based auth
// export const tokenAtom = atom(
//   (get) => get(persistedAuthAtom).token
// );

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
                    user: {...prev.user, ...action.payload},
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
        // token: tokenAtom, // Add this if you're using token based auth
        authActions: authActionsAtom,
        getCsrfToken, // Keep this if you're using session based auth
    };
}