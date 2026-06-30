// Setup polyfills BEFORE importing Playwright
import './setup';

import {test, expect} from '@playwright/test';

test.describe('LunarWidget', () => {
  test('toggles month table and highlights today', async ({page}) => {
    await page.route('**/api/lunar?**', async (route) => {
      const url = new URL(route.request().url());
      const date = url.searchParams.get('date') ?? '2024-05-14';
      await route.fulfill({
        status: 200,
        body: JSON.stringify({
          date,
          lunar_day: Number(date.split('-')[2]),
          phase: 'Waxing Crescent',
          description: `Dream focus for ${date}`,
          recommendation: `Notes for ${date}`,
          locale: url.searchParams.get('locale') ?? 'en',
          source: 'playwright-suite',
          timezone: url.searchParams.get('tz') ?? 'Europe/Moscow'
        }),
        headers: {'Content-Type': 'application/json'}
      });
    });

    await page.goto('/en/calendar');

    const toggle = page.getByRole('button', {name: '📅 Show month'});
    await expect(toggle).toBeVisible();
    await toggle.click();

    // The month table renders every day sorted ascending, so the *first* row
    // is the 1st of the month — only today's row carries aria-current="date".
    // Assert on that highlighted row directly rather than on .first().
    const todayRow = page.locator('[data-testid^="row-"][aria-current="date"]');
    await expect(todayRow).toHaveCount(1);
    await expect(todayRow).toBeVisible();
  });
});
