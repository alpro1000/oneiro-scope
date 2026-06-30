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
    // Reuse a server already listening on the URL. The test-ui workflow starts
    // a dev server for its lunar-API smoke step whose next-server child can
    // outlive the step; without reuse, Playwright aborts with "port already in
    // use" in CI. Reusing is safe — e2e specs mock their own network calls.
    reuseExistingServer: true
  }
});
