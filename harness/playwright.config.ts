import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.PORT ?? 5173);
const BASE_URL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: './tests',
  outputDir: './test-results',
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: BASE_URL,
    // 'on' captures a trace for EVERY test, passing or failing — we need the
    // passing trace too. (Do NOT use 'on-first-retry': with retries: 0 a passing
    // test never retries, so no trace would be produced.)
    trace: 'on',
  },
  // Single browser → exactly one passing trace and one failing trace.
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'node server.mjs',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
