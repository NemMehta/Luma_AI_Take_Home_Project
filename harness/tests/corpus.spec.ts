import { test, expect, type Page } from '@playwright/test';

// Phase 4a corpus: each category has a passing baseline and an injected failing
// run of the same search flow. The injection is the only difference, which is
// what makes each trace's true label unambiguous.

async function runHappyFlow(page: Page) {
  await page.goto('/');
  await expect(page.getByTestId('result-item')).toHaveCount(8);
  await page.getByTestId('search-input').fill('cher');
  await expect(page.getByTestId('result-item')).toHaveCount(1);
  await expect(page.getByTestId('result-item')).toHaveText(['Cherry']);
}

// --------------------------------------------------------------- stale_selector
test('stale_selector :: baseline', async ({ page }) => {
  await runHappyFlow(page);
});

test('stale_selector :: injected', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('result-item')).toHaveCount(8);
  // The search box id is #search now, not #search-box — locator never resolves.
  await page.locator('#search-box').fill('cher', { timeout: 4000 });
});

// -------------------------------------------------------------- network_failure
test('network_failure :: baseline', async ({ page }) => {
  await runHappyFlow(page);
});

test('network_failure :: injected', async ({ page }) => {
  await page.route('**/api/fruits.json', (route) =>
    route.fulfill({ status: 503, contentType: 'text/plain', body: 'Service Unavailable' }),
  );
  await page.goto('/');
  // The data the app depends on returns 503, so the list never populates.
  await expect(page.getByTestId('result-item')).toHaveCount(8, { timeout: 4000 });
});

// -------------------------------------------------------------------- real_bug
test('real_bug :: baseline', async ({ page }) => {
  await runHappyFlow(page);
});

test('real_bug :: injected', async ({ page }) => {
  await page.goto('/?inject=real_bug');
  await expect(page.getByTestId('result-item')).toHaveCount(8);
  await page.getByTestId('search-input').fill('cher');
  // Selectors work and the search runs, but the filter is inverted, so the
  // result is wrong (7 non-matching fruits instead of just "Cherry").
  await expect(page.getByTestId('result-item')).toHaveCount(1);
});

// ----------------------------------------------------------------- flaky_timing
test('flaky_timing :: baseline', async ({ page }) => {
  await runHappyFlow(page);
});

test('flaky_timing :: injected', async ({ page }) => {
  await page.goto('/?inject=flaky');
  await expect(page.getByTestId('result-item')).toHaveCount(8);
  await page.getByTestId('search-input').fill('cher');
  // The filtered result is painted ~3s late; we assert within 1.5s, before the
  // state is ready.
  await expect(page.getByTestId('result-item')).toHaveCount(1, { timeout: 1500 });
});
