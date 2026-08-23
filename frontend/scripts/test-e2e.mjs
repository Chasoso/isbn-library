import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { chromium, expect } from "@playwright/test";

const baseUrl = "http://127.0.0.1:4173";
const serverEnv = {
  ...process.env,
  VITE_E2E_DEMO_MODE: "true",
  VITE_API_BASE_URL: "http://127.0.0.1:4173/mock-api",
  VITE_COGNITO_AUTHORITY: "https://example.com/mock-authority",
  VITE_COGNITO_HOSTED_UI_DOMAIN: "https://example.com/mock-hosted-ui",
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

async function assertNoHorizontalScroll(page) {
  const viewportWidth = page.viewportSize()?.width ?? 0;
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(viewportWidth);
}

async function runDesktopChecks(page) {
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".app-header")).toBeVisible();
  await expect(page.locator(".shelf-summary")).toBeVisible();
  await expect(page.locator(".search-bar")).toBeVisible();
  await expect(page.locator(".recent-book-card").first()).toBeVisible();
  await assertNoHorizontalScroll(page);
  await expect(page.locator(".desktop-nav")).toBeVisible();

  await page.goto(`${baseUrl}/books`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".bookshelf-shell")).toBeVisible();
  await expect(page.locator(".desktop-filters")).toBeVisible();
  await expect(page.locator(".bookshelf-book").first()).toBeVisible();
  await assertNoHorizontalScroll(page);

  await page.goto(`${baseUrl}/books/9784860648114`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".detail-layout")).toBeVisible();
  await expect(page.locator(".detail-controls")).toBeVisible();
  await expect(page.locator(".detail-save-button")).toBeVisible();
  await expect(page.locator(".detail-danger-zone")).toBeVisible();
  await assertNoHorizontalScroll(page);

  await page.goto(`${baseUrl}/categories`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".category-table")).toBeVisible();
  await expect(page.getByRole("button", { name: "＋追加" })).toBeVisible();
  await page.getByRole("button", { name: "＋追加" }).click();
  await expect(page.locator(".edit-sheet")).toBeVisible();
  await page.getByRole("button", { name: "閉じる" }).click();
  await page.getByRole("button", { name: /を編集/ }).first().click();
  await expect(page.locator(".edit-sheet")).toBeVisible();
  await page.getByRole("button", { name: "閉じる" }).click();
  await assertNoHorizontalScroll(page);

  await page.goto(`${baseUrl}/scan`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".scan-panel")).toBeVisible();
  await expect(page.locator(".scan-message")).toBeVisible();
  await expect(page.locator(".scan-manual")).toBeVisible();
  if (await page.locator(".scanner-shell").count()) {
    await expect(page.locator(".scanner-shell")).toBeVisible();
  }
  await assertNoHorizontalScroll(page);
}

async function runMobileChecks(page) {
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".app-header")).toBeVisible();
  await expect(page.locator(".shelf-summary")).toBeVisible();
  await expect(page.locator(".search-bar")).toBeVisible();
  await expect(page.locator(".recent-book-card").first()).toBeVisible();
  await expect(page.locator(".bottom-nav")).toBeVisible();
  await expect(page.locator(".desktop-nav")).toBeHidden();
  await assertNoHorizontalScroll(page);

  await page.goto(`${baseUrl}/books`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".bookshelf-shell")).toBeVisible();
  await expect(page.locator(".mobile-tool-row")).toBeVisible();
  await page.locator(".filter-button").click();
  await expect(page.locator(".filter-sheet")).toBeVisible();
  await page.getByRole("button", { name: "閉じる" }).click();
  await expect(page.locator(".bookshelf-book").first()).toBeVisible();
  await assertNoHorizontalScroll(page);

  await page.goto(`${baseUrl}/books/9784860648114`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".detail-layout")).toBeVisible();
  await expect(page.locator(".detail-controls")).toBeVisible();
  await expect(page.locator(".detail-save-button")).toBeVisible();
  await expect(page.locator(".detail-danger-zone")).toBeVisible();
  await assertNoHorizontalScroll(page);

  await page.goto(`${baseUrl}/categories`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".category-table")).toBeVisible();
  await expect(page.getByRole("button", { name: "＋追加" })).toBeVisible();
  await assertNoHorizontalScroll(page);

  await page.goto(`${baseUrl}/scan`, { waitUntil: "domcontentloaded" });
  await expect(page.locator(".scan-panel")).toBeVisible();
  await expect(page.locator(".scan-message")).toBeVisible();
  await expect(page.locator(".scan-manual")).toBeVisible();
  await page.locator(".scan-manual input").fill("9780000000000");
  await page.locator(".scan-manual .primary-button").click();
  await expect(page.locator(".manual-registration-form")).toBeVisible();
  await expect(page.locator(".manual-registration-form input[name=title]")).toHaveValue("");
  await page.locator('[data-testid="manual-register-button"]').click();
  await expect(page.locator("#manual-title-error")).toBeVisible();
  await page.locator(".manual-registration-form input[name=title]").fill("Demo manual book");
  await page.locator(".manual-registration-form input[name=author]").fill("Demo author");
  await page.locator(".manual-registration-form input[name=publisher]").fill("Demo publisher");
  await page.locator('[data-testid="manual-register-button"]').click();
  await expect(page).toHaveURL(/\/books\/9780000000000$/);
  await expect(page.locator(".detail-layout")).toBeVisible();
  await assertNoHorizontalScroll(page);
}

const server = spawn(process.execPath, ["scripts/dev.mjs", "--host", "127.0.0.1", "--port", "4173"], {
  cwd: process.cwd(),
  env: serverEnv,
  stdio: "ignore",
  windowsHide: true,
});

let exitCode = 0;

try {
  await waitForServer(baseUrl);

  const browser = await chromium.launch({ headless: true });
  try {
    const desktopContext = await browser.newContext({
      viewport: { width: 1440, height: 1600 },
      deviceScaleFactor: 1,
    });
    const mobileContext = await browser.newContext({
      viewport: { width: 375, height: 667 },
      isMobile: true,
      hasTouch: true,
      deviceScaleFactor: 1,
    });

    try {
      await runDesktopChecks(await desktopContext.newPage());
      await runMobileChecks(await mobileContext.newPage());
    } finally {
      await desktopContext.close();
      await mobileContext.close();
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
