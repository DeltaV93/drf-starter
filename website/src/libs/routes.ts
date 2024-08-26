function apiJoin(...endpoints) {
    return endpoints.join('/');
}

export const routes = {
    api: {
         base_url: import.meta.env.VITE_APP_YOUR_API_ENDPOINT, // VITE_APP_YOUR_API_ENDPOINT should NOT include a slash ('/') at the end
        auth: {
             login: () => apiJoin(routes.api.base_url, 'login/'),
             createAccount: () => apiJoin(routes.api.base_url, 'register/'),
             passwordReset: () => apiJoin(routes.api.base_url, 'password-reset-confirm/'),
             passwordResetRequest: () => apiJoin(routes.api.base_url, 'password-reset-request/'),
             confirmPasswordToken: (id: string | undefined, token: string | undefined) => apiJoin(routes.api.base_url, `password-reset/${id}/${token}/`),
        },
        user: {
             profile: () => apiJoin(routes.api.base_url, 'profile/')
        },
        account: {
             subscriptions: (planId: string) => apiJoin(routes.api.base_url, `subscribe/${planId}/`)
        }

    }
}