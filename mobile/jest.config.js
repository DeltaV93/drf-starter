// jest-expo is what makes the Expo module mocks and the React Native
// transform available; without it every `import * as SecureStore` blows up on
// a native module that does not exist in Node.
module.exports = {
  preset: 'jest-expo',
  setupFiles: ['<rootDir>/src/test/setup.ts'],
  // The default pattern ignores everything under node_modules, but React
  // Native and every Expo package ship untranspiled ESM -- and so does
  // `@app/shared`, which is TypeScript source symlinked in from the
  // workspace. Each has to be transformed rather than skipped.
  transformIgnorePatterns: [
    'node_modules/(?!(?:.pnpm/)?((jest-)?react-native|@react-native(-community)?|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|react-native-paper|react-native-vector-icons|@app/shared))',
  ],
  collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/test/**'],
};
