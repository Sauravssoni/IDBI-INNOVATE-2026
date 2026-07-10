import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3005',
    trace: 'on-first-retry',
    screenshot: 'on',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000',
      env: {
        APP_ENV: 'development',
        DATABASE_URL: process.env.DATABASE_URL || 'postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test',
        JWT_SECRET: process.env.JWT_SECRET || 'test-secret',
        DEMO_USER_PASSWORD: process.env.DEMO_USER_PASSWORD || 'VyaparPulseDemo2026!',
        DEMO_ACCESS_ENABLED: 'true'
      },
      port: 8000,
      reuseExistingServer: false,
      stdout: 'pipe',
    },
    {
      command: 'npm run start -- -p 3005',
      env: {
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      },
      port: 3005,
      reuseExistingServer: false,
      stdout: 'pipe',
    },
  ],
});
