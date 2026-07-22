import { defineConfig } from "@playwright/test";


export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:3000",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "cd ../.. && uv run --python 3.13 uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/readyz",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: {
        AUTO_CREATE_SCHEMA: "true",
        DATABASE_URL: "sqlite+aiosqlite:///./.state/e2e.sqlite3",
        WEB_ORIGIN: "http://127.0.0.1:3000",
      },
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: {
        NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000",
      },
    },
  ],
});
