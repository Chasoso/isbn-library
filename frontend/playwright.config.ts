import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173",
    port: 4173,
    reuseExistingServer: !process.env.CI,
    env: {
      VITE_E2E_DEMO_MODE: "true",
      VITE_API_BASE_URL: "http://127.0.0.1:4173/mock-api",
      VITE_COGNITO_AUTHORITY: "https://example.com/mock-authority",
      VITE_COGNITO_HOSTED_UI_DOMAIN: "https://example.com/mock-hosted-ui",
      VITE_COGNITO_CLIENT_ID: "mock-client-id",
      VITE_COGNITO_REDIRECT_URI: "http://127.0.0.1:4173/auth/callback",
      VITE_COGNITO_LOGOUT_REDIRECT_URI: "http://127.0.0.1:4173",
      VITE_COGNITO_SCOPE: "openid email profile",
    },
  },
  projects: [
    {
      name: "desktop-chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1600 },
      },
    },
  ],
});
