import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
  dir: './'
});

const config = createJestConfig({
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1'
  },
  transformIgnorePatterns: ['node_modules/(?!(framer-motion)/)'],
  testPathIgnorePatterns: ['/node_modules/', '/e2e/', '/.next/'],
  // Only run unit tests from __tests__ directory, exclude e2e tests
  testMatch: ['**/__tests__/**/*.test.{ts,tsx}']
});

export default config;
