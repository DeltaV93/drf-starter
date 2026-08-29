// Mirrors website/eslint.config.js, with two differences: the globals are
// React Native's rather than the browser's, and there is no react-refresh
// plugin -- Fast Refresh in Metro does not have the same export constraints.
//
// The react-hooks rules matter more here than anywhere: the compiler rules
// (`set-state-in-effect`, `incompatible-library`) catch the effect loops that
// on a phone show up as battery drain rather than as a slow page.

import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['node_modules', '.expo', 'dist', 'coverage', 'expo-env.d.ts'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.node, ...globals.browser },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    files: ['**/*.test.{ts,tsx}', 'src/test/**'],
    languageOptions: { globals: { ...globals.node, ...globals.jest } },
  },
  {
    // Metro and Jest both load their config with `require`, and this package
    // has no `"type": "module"` -- so these two are CommonJS, and only these
    // two. This file is `.mjs` for the same reason: it has to be ESM without
    // making the other two ESM as well.
    files: ['metro.config.js', 'jest.config.js'],
    languageOptions: { globals: globals.node, sourceType: 'commonjs' },
  },
);
