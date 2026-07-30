// Setup polyfills BEFORE importing Playwright
import './setup';

import {test, expect} from '@playwright/test';

// Deterministic smoke test: the app boots and serves a page.
//
// It targets a STATIC legal page — outside [locale], no SSR fetch, no backend —
// because CI e2e runs no ephemeris service, so any page that SSR-loads a chart
// or lunar day is non-deterministic there (it renders the real screen when a
// backend happens to be reachable, and the honest error when not). The lunar
// calendar's own behaviour is covered by the jest unit test, which injects a
// payload without a live service; a backend-backed e2e for the calculation
// screens waits on CI running a real backend (tracked).
test.describe('App smoke', () => {
  test('boots and serves a static page', async ({page}) => {
    await page.goto('/legal/privacy');
    await expect(page.getByText(/Privacy Policy/i)).toBeVisible();
  });
});
