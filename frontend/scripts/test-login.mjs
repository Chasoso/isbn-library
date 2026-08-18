import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { chromium, expect } from "@playwright/test";

const baseUrl = "http://127.0.0.1:4173";
const serverEnv = {
  ...process.env,
  VITE_API_BASE_URL: "https://example.invalid/api",
  VITE_COGNITO_AUTHORITY: "https://example.invalid/authority",
  VITE_COGNITO_HOSTED_UI_DOMAIN: "https://example.invalid/hosted-ui",
  VITE_COGNITO_CLIENT_ID: "mock-client-id",
  VITE_COGNITO_REDIRECT_URI: "http://127.0.0.1:4173/auth/callback",
  VITE_COGNITO_LOGOUT_REDIRECT_URI: "http://127.0.0.1:4173",
  VITE_COGNITO_SCOPE: "openid email profile",
};

async function waitForServer(url, timeoutMs = 30_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {
      // keep polling
    }
    await delay(500);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

const server = spawn(
  process.execPath,
  ["scripts/dev.mjs", "--host", "127.0.0.1", "--port", "4173"],
  {
    cwd: process.cwd(),
    env: serverEnv,
    stdio: "ignore",
    windowsHide: true,
  },
);

let exitCode = 0;

try {
  await waitForServer(baseUrl);

  const browser = await chromium.launch({ headless: true });
  try {
    const viewports = [
      { name: "320x568", width: 320, height: 568 },
      { name: "375x667", width: 375, height: 667 },
      { name: "1440x900", width: 1440, height: 900 },
    ];

    for (const viewport of viewports) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        deviceScaleFactor: 1,
      });

      try {
        const page = await context.newPage();
        await page.goto(baseUrl, { waitUntil: "networkidle" });
        await expect(page.locator(".login-card")).toBeVisible();
        await expect(page.getByRole("heading", { name: "ログイン" })).toBeVisible();
        await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();
        await expect(page.locator(".login-error")).toHaveCount(0);

        const cardBox = await page.locator(".login-card").boundingBox();
        console.log(`${viewport.name}:`, cardBox);

        await page.screenshot({
          path: `local-screenshots/2026-08-16/login-${viewport.name}.png`,
          fullPage: false,
        });
      } finally {
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }
} catch (error) {
  exitCode = 1;
  console.error(error);
} finally {
  server.kill("SIGTERM");
  await delay(500);
}

process.exit(exitCode);
