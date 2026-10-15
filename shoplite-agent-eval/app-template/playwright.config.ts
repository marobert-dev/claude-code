import { defineConfig, devices } from '@playwright/test';

const apiPort = Number(process.env.SHOPLITE_API_PORT ?? 5080);
const webPort = Number(process.env.SHOPLITE_WEB_PORT ?? 5173);
const apiUrl = `http://localhost:${apiPort}`;
const webUrl = `http://localhost:${webPort}`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 30_000,
  reporter: [['list'], ['json', { outputFile: 'test-results/e2e-results.json' }]],
  use: {
    baseURL: webUrl,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `dotnet run --project backend/src/ShopLite.Api --no-launch-profile --urls ${apiUrl}`,
      url: `${apiUrl}/api/products/categories`,
      env: { ASPNETCORE_ENVIRONMENT: 'Development' },
      timeout: 180_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm --prefix frontend run dev',
      url: webUrl,
      env: { SHOPLITE_API_URL: apiUrl, SHOPLITE_WEB_PORT: String(webPort) },
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
});
