import axios, {AxiosRequestConfig, AxiosResponse, AxiosError} from 'axios';
import {getToast} from '../store/toast';

// Axios instances
const axiosInstance = axios.create({
    headers: {
        'Content-Type': 'application/json',
    },
});

// parameters for the function
interface ApiRequestOptions extends AxiosRequestConfig {
    successMessage?: string;
    errorMessage?: string;
    showSuccessToast?: boolean;
    showErrorToast?: boolean;
}

export const apiCall = async <T = any>(
    options: ApiRequestOptions
): Promise<AxiosResponse<T>> => {
    const {
        successMessage = 'Operation successful',
        errorMessage = 'An error occurred',
        showSuccessToast = true,
        showErrorToast = true,
        ...axiosOptions
    } = options;

    const toast = getToast();

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

// Helper function to set the authorization token
export const setAuthToken = (token: string | null) => {
    if (token) {
        axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
        delete axiosInstance.defaults.headers.common['Authorization'];
    }
};

export default axiosInstance;