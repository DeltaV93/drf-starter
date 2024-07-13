function apiJoin(...endpoints) {
    return endpoints.join('/');
}

export const routes = {
    api: {
         base_url: import.meta.env.REACT_APP_YOUR_API_ENDPOINT, // REACT_APP_YOUR_API_ENDPOINT should include a slash ('/') at the end
        auth: {
             login: () => apiJoin(routes.api.base_url, 'login/')
        },
        user: {
             profile: () => apiJoin(routes.api.base_url, 'profile/')
        }

    }
}