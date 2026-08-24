import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv, type Plugin } from 'vite';

import { darkPalette, identity, lightPalette } from './src/styles/brand.ts';

/**
 * Substitutes the brand tokens into index.html at build time.
 *
 * The tab title, the meta description and the two theme colours are brand
 * decisions, but index.html is static and cannot import a module. Without
 * this they would be a second copy to keep in step with brand.ts -- and the
 * one people forget, because a stale <title> looks like someone else's
 * problem until it ships.
 */
function brandHtml(): Plugin {
  return {
    name: 'brand-html',
    transformIndexHtml(html) {
      return html
        .replace(/%APP_NAME%/g, identity.name)
        .replace(/%APP_TAGLINE%/g, identity.tagline)
        .replace(/%THEME_COLOR_LIGHT%/g, lightPalette.background.default)
        .replace(/%THEME_COLOR_DARK%/g, darkPalette.background.default);
    },
  };
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

  return {
    // The app styles through MUI's `sx` prop rather than emotion's `css`
    // prop, so no emotion babel plugin is needed (and plugin-react v6 runs
    // oxc, not babel, so it could not be configured here anyway).
    plugins: [react(), brandHtml()],
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
