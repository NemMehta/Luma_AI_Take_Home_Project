import { test, expect } from '@playwright/test';

// Both tests exercise the same flow: type a query into the search box and check
// the list filters down to the matching fruit. The second uses a stale selector
// so it fails for a real "locator not found" reason — that is the failing trace.

test('happy path: searching filters the list to the matching result', async ({ page }) => {
  await page.goto('/');

  // The demo seeds eight fruits on load.
  await expect(page.getByTestId('result-item')).toHaveCount(8);

  await page.getByTestId('search-input').fill('cher');

  await expect(page.getByTestId('result-item')).toHaveCount(1);
  await expect(page.getByTestId('result-item')).toHaveText(['Cherry']);
  await expect(page.getByTestId('empty-state')).toBeHidden();
});

test('stale selector: the old #search-box id no longer exists (intentional failure)', async ({ page }) => {
  await page.goto('/');

  // The search box id was renamed from #search-box to #search. This stale
  // selector resolves to nothing, so .fill() times out with a real
  // "locator not found" error — the failure trace this phase needs. The page
  // itself loads fine, so the selector is the only thing that's wrong.
  await page.locator('#search-box').fill('cher', { timeout: 4000 });

  // Never reached — kept so the intended flow mirrors the happy path.
  await expect(page.getByTestId('result-item')).toHaveCount(1);
});
