// Setup polyfills BEFORE importing Playwright
import './setup';

import {test, expect} from '@playwright/test';

// The calendar SSR-loads today's lunar day from the ephemeris service. Whether
// that service is reachable in a given CI run is not guaranteed (the e2e
// workflows don't run a backend, and `reuseExistingServer` can hand us a dev
// server started with different env), so the page may render either the real
// instrument OR the honest "unavailable" error. BOTH are valid; what must never
// happen is a blank page or a fabricated phase (conventions.md §12). This
// asserts one of those two states renders. The happy path *with data* is
// covered precisely by the jest unit test, which injects a payload without a
// live service.
test.describe('Lunar calendar', () => {
  test('renders a valid state — real calendar or honest error, never fabricated', async ({page}) => {
    // If the calendar renders, keep its month fetches deterministic rather than
    // hammering an unreachable backend.
    await page.route('**/api/lunar?**', (route) =>
      route.fulfill({
        status: 200,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          date: '2024-05-14', lunar_day: 6, phase: 'Waxing Crescent',
          description: 'x', recommendation: 'y', locale: 'en',
          source: 'playwright', timezone: 'Europe/Moscow', illumination: 0.42
        })
      })
    );

    await page.goto('/en/calendar');

    // Calendar → the "· Swiss Ephemeris" eyebrow; error → "Lunar data unavailable".
    await expect(
      page.getByText(/Lunar data unavailable|Swiss Ephemeris/i).first()
    ).toBeVisible();
  });
});
