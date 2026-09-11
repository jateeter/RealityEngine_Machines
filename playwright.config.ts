import { defineConfig, devices } from '@playwright/test';

const reuseServices = process.env.REUSE_SERVICES === 'true';
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: './tests',

  timeout: 60 * 1000,
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: 1,

  reporter: [
    ['html', { outputFolder: 'e2e-report' }],
    ['list'],
    ['json', { outputFile: 'e2e-results.json' }]
  ],

  use: {
    baseURL: 'https://localhost:5173',
    ignoreHTTPSErrors: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  // Pass multi-engine env vars through to tests
  // (Playwright does not forward all env vars automatically in some runners)
  env: {
    RE_REGISTRY_URL:    process.env.RE_REGISTRY_URL    ?? '',
    RE_BASE_URL:        process.env.RE_BASE_URL         ?? '',
    PE_BASE_URL:        process.env.PE_BASE_URL         ?? '',
    VIZ_BASE_URL:       process.env.VIZ_BASE_URL        ?? '',
    VIZ_FRONTEND_URL:   process.env.VIZ_FRONTEND_URL    ?? '',
    LAS_BASE_URL:       process.env.LAS_BASE_URL        ?? '',
    QD_BASE_URL:        process.env.QD_BASE_URL         ?? '',
    HEALTHKIT_BRIDGE_TOKEN: process.env.HEALTHKIT_BRIDGE_TOKEN ?? '',
    SKIP_GLOBAL_SETUP:  process.env.SKIP_GLOBAL_SETUP   ?? '',
  },

  // One project by default, in CI and locally alike.
  //
  // These are API and corpus integration tests — they drive the engines over
  // HTTP and assert on payloads. Almost nothing here is browser-dependent, so
  // running four engines multiplies the cost and the failure count without
  // multiplying the coverage: `pe-sensor-registration › RAG signal regions
  // [64:72]` is ONE finding that reported as FOUR, once per project, and read
  // as four failures on the deployment board.
  //
  // The split was `isCI ? [chromium] : [chromium, firefox, webkit, 'Mobile
  // Chrome']`, so the hosted lane had never run three of them and nobody kept
  // them green, while the local gate ran all four and counted the difference.
  // RealityEngine_CI#330 made exactly this change in the CI repo for exactly
  // this reason; this is the sibling copy it missed.
  //
  // Opt in when a cross-browser question is actually being asked:
  //
  //     PLAYWRIGHT_BROWSERS=all npx playwright test
  projects: process.env.PLAYWRIGHT_BROWSERS === 'all'
    ? [
        { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
        { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
        { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
        { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
      ]
    : [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

  // Services are managed externally by startUniverse.sh.
  // Set REUSE_SERVICES=true when they are already running.
  webServer: reuseServices
    ? undefined
    : {
        command: "bash -c 'cd ../RealityEngine_CI && ./startUniverse.sh --no-openclaw'",
        url: 'https://localhost:5173',
        ignoreHTTPSErrors: true,
        timeout: 300 * 1000,
        reuseExistingServer: !isCI,
      },

  globalSetup: './tests/e2e/global-setup.ts',
  globalTeardown: './tests/e2e/global-teardown.ts',
});
