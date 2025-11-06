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
  transformIgnorePatterns: ['node_modules/(?!(framer-motion)/)']
});

export default config;
