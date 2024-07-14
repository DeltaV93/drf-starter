function apiJoin(...endpoints) {
    return endpoints.join('/');
}

export const routes = {
    api: {
         base_url: import.meta.env.VITE_APP_YOUR_API_ENDPOINT, // VITE_APP_YOUR_API_ENDPOINT should NOT include a slash ('/') at the end
        auth: {
             login: () => apiJoin(routes.api.base_url, 'login/')
        },
        user: {
             profile: () => apiJoin(routes.api.base_url, 'profile/')
        }

    }
}