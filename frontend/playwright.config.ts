import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local.vercel' });

const useLocalServer = process.env.USE_LOCAL_SERVER !== 'false';
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3005';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  timeout: 60000,
  use: {
    baseURL,
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
  ...(useLocalServer ? {
    webServer: [
      {
        command: 'cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000',
        env: {
          APP_ENV: 'development',
          DATABASE_URL: process.env.DATABASE_URL || 'postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test',
          JWT_SECRET: process.env.JWT_SECRET || 'test-secret',
          DEMO_USER_PASSWORD: process.env.DEMO_USER_PASSWORD || 'VyaparPulseDemo2026!',
          DEMO_ACCESS_ENABLED: 'true',
          DEMO_RESET_ENABLED: 'true',
          DEMO_RESET_TOKEN: 'dummy',
          DEMO_DATABASE_FINGERPRINT: 'BYPASS'
        },
        port: 8000,
        reuseExistingServer: true,
        stdout: 'pipe',
      },
      {
        command: 'npm run start -- -p 3005',
        env: {
          NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? '',
          BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
        },
        port: 3005,
        reuseExistingServer: true,
        stdout: 'pipe',
      },
    ]
  } : {}),
});
