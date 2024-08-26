import axios, {AxiosError, AxiosRequestConfig, AxiosResponse} from 'axios';
import {getToast} from '../store/toast';
import {authAtom} from "../store/auth.tsx";

const {getCsrfToken} = authAtom();

// Axios instances
const axiosInstance = axios.create({
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
});

// Function to set the CSRF token
const updateCsrfToken = () => {
    const token = getCsrfToken();
    if (token) {
        axiosInstance.defaults.headers['X-CSRFToken'] = token;
        console.log(token, 'token', axiosInstance.defaults.headers['X-CSRFToken'], 'axiosInstance.defaults.headers[\'X-CSRFToken\']')
    }
};


// Interceptor to conditionally set headers and withCredentials
axiosInstance.interceptors.request.use((config) => {
    // Check if the request needs CSRF token or credentials
    if (config.withCredentials) {
        updateCsrfToken();
    }
    return config;
});

// parameters for the function
interface ApiRequestOptions extends AxiosRequestConfig {
    successMessage?: string;
    errorMessage?: string;
    showSuccessToast?: boolean;
    showErrorToast?: boolean;
    useCsrfToken?: boolean;
    withCredentials?: boolean;
    credentials?: boolean,
}

export const apiCall = async <T = any>(
    options: ApiRequestOptions
): Promise<AxiosResponse<T>> => {
    const {
        successMessage = 'Operation successful',
        errorMessage = 'An error occurred',
        showSuccessToast = true,
        showErrorToast = true,
        useCsrfToken = true,
        withCredentials = true,
        ...axiosOptions
    } = options;

    const toast = getToast();

    // Conditionally apply settings to axiosInstance
    if (withCredentials) {
        axiosInstance.defaults.withCredentials = true;
    } else {
        delete axiosInstance.defaults.withCredentials; // Ensure it is not included
    }

    if (useCsrfToken) {
        const csrfToken = getCsrfToken();
        console.log(csrfToken, 'api')
        if (csrfToken) {
            axiosOptions.headers = {
                ...axiosOptions.headers,
                'X-CSRFToken': csrfToken
            };
        }
    }

    try {
        // Make the API call
        const response: AxiosResponse<T> = await axiosInstance(axiosOptions);

        // Show success toast if enabled
        if (showSuccessToast) {
            toast.success(successMessage);
        }

        return response;
    } catch (error) {
        // Handle errors
        if (axios.isAxiosError(error)) {
            const axiosError = error as AxiosError<any>;
            const errorMsg = axiosError.response?.data?.message || errorMessage;

            // Show error toast if enabled
            if (showErrorToast) {
                toast.error(errorMsg);
            }

            // You can handle specific error status codes here if needed
            switch (axiosError.response?.status) {
                case 401:
                    // Handle unauthorized error (e.g., redirect to login)
                    break;
                case 403:
                    // Handle forbidden error
                    break;
                // Add more cases as needed
            }
        } else {
            // Handle non-Axios errors
            console.error('Non-Axios error:', error);
            if (showErrorToast) {
                toast.error('An unexpected error occurred');
            }
        }

        throw error;
    }
};

// Use this helper function to set the authorization token
// export const setAuthToken = (token: string | null) => {
//     if (token) {
//         axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
//     } else {
//         delete axiosInstance.defaults.headers.common['Authorization'];
//     }
// };

export default axiosInstance;