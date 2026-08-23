import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

  return {
    // The app styles through MUI's `sx` prop rather than emotion's `css`
    // prop, so no emotion babel plugin is needed (and plugin-react v6 runs
    // oxc, not babel, so it could not be configured here anyway).
    plugins: [react()],
    server: {
      port: 3000,
      // Proxy /api to Django in development so the browser sees one origin.
      // Same-origin means session and CSRF cookies just work, with no
      // SameSite=None or CORS preflight involved.
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
      },
    },
    preview: {
      port: 3000,
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
      },
    },
    build: {
      sourcemap: mode !== 'production',
      rollupOptions: {
        output: {
          // Split the two big vendor groups out of the app bundle so a code
          // change does not invalidate the cached framework chunks.
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return undefined;
            if (/[\\/]node_modules[\\/](@mui|@emotion)[\\/]/.test(id)) return 'mui';
            if (/[\\/]node_modules[\\/](react|react-dom|react-router)/.test(id)) return 'vendor';
            return undefined;
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      css: false,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov'],
        include: ['src/**/*.{ts,tsx}'],
        exclude: ['src/test/**', 'src/**/*.d.ts', 'src/main.tsx'],
      },
    },
  };
});
