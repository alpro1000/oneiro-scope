import {defineConfig, devices} from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {
    timeout: 5_000
  },
  fullyParallel: true,
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    locale: 'en-US'
  },
  projects: [
    {
      name: 'chromium',
      use: {...devices['Desktop Chrome']}
    },
    {
      name: 'mobile-chrome',
      use: {...devices['Pixel 5']}
    }
  ],
  webServer: {
    command: 'npm run dev -- --hostname 0.0.0.0 --port 3000',
    url: 'http://localhost:3000',
    timeout: 120_000,
    reuseExistingServer: !process.env.CI
  }
});
