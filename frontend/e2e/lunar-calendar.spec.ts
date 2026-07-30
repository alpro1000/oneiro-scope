// Setup polyfills BEFORE importing Playwright
import './setup';

import {test, expect} from '@playwright/test';

// The calendar SSR-loads today's lunar day from the backend. In CI no backend
// runs, so getLunarDay throws — and, per conventions.md §12, the page must show
// an honest error rather than a fabricated phase (the mock fallback that used
// to hide this was removed). That honest state is what this asserts end-to-end.
// The happy path (rendered day + month grid) is covered by the jest unit test,
// which can inject a payload without needing a live ephemeris service.
test.describe('Lunar calendar', () => {
  test('fails honestly when the backend is unreachable (no fabricated data)', async ({page}) => {
    await page.goto('/en/calendar');
    await expect(page.getByText(/Lunar data unavailable/i)).toBeVisible();
  });
});
