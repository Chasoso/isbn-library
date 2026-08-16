import { expect, test, type Page } from "@playwright/test";

async function assertNoHorizontalScroll(page: Page): Promise<void> {
  const viewportWidth = page.viewportSize()?.width ?? 0;
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(viewportWidth);
}

test.describe("frontend editorial bookshelf visuals", () => {
  test("home page keeps the editorial layout responsive", async ({ page }, testInfo) => {
    await page.goto("/");
    await expect(page.locator(".app-header")).toBeVisible();
    await expect(page.locator(".summary-grid")).toBeVisible();
    await expect(page.locator(".search-bar")).toBeVisible();
    await expect(page.locator(".recent-book-card").first()).toBeVisible();
    await assertNoHorizontalScroll(page);

    if (testInfo.project.name === "iphone-se-chromium") {
      await expect(page.locator(".bottom-nav")).toBeVisible();
      await expect(page.locator(".desktop-nav")).toBeHidden();
    } else {
      await expect(page.locator(".desktop-nav")).toBeVisible();
    }

    await page.screenshot({
      path: testInfo.outputPath("home-editorial.png"),
      fullPage: true,
    });
  });

  test("books page keeps search, filters, and shelf selection accessible", async ({ page }, testInfo) => {
    await page.goto("/books");
    await expect(page.locator(".bookshelf-shell")).toBeVisible();
    await assertNoHorizontalScroll(page);

    if (testInfo.project.name === "iphone-se-chromium") {
      await expect(page.locator(".mobile-tool-row")).toBeVisible();
      await page.locator(".filter-button").click();
      await expect(page.locator(".filter-sheet")).toBeVisible();
      await page.locator(".filter-sheet .sheet-heading button").click();
    } else {
      await expect(page.locator(".desktop-filters")).toBeVisible();
    }

    await expect(page.locator(".bookshelf-book").first()).toBeVisible();
    await expect(page.locator(".bookshelf-selection")).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("bookshelf-editorial.png"),
      fullPage: true,
    });
  });

  test("book detail page keeps the reading controls and metadata visible", async ({ page }, testInfo) => {
    await page.goto("/books/9784860648114");
    await expect(page.locator(".detail-grid")).toBeVisible();
    await expect(page.locator(".detail-status-panel")).toBeVisible();
    await expect(page.locator(".detail-actions")).toBeVisible();
    await assertNoHorizontalScroll(page);

    await page.screenshot({
      path: testInfo.outputPath("book-detail-editorial.png"),
      fullPage: true,
    });
  });

  test("categories page uses a compact table with modal editing", async ({ page }, testInfo) => {
    await page.goto("/categories");
    await expect(page.locator(".category-table")).toBeVisible();
    await expect(page.getByRole("button", { name: /Add category/i })).toBeVisible();
    await assertNoHorizontalScroll(page);

    await page.getByRole("button", { name: /Add category/i }).click();
    await expect(page.locator(".edit-sheet")).toBeVisible();
    await page.getByRole("button", { name: /Close editor/i }).click();

    await page.getByRole("button", { name: /Edit/i }).first().click();
    await expect(page.locator(".edit-sheet")).toBeVisible();
    await page.getByRole("button", { name: /Close editor/i }).click();

    await page.screenshot({
      path: testInfo.outputPath("categories-editorial.png"),
      fullPage: true,
    });
  });

  test("scan page keeps the camera-first layout", async ({ page }, testInfo) => {
    await page.goto("/scan");
    await expect(page.locator(".scan-panel")).toBeVisible();
    await expect(page.locator(".scanner-shell")).toBeVisible();
    await expect(page.locator(".scan-tips")).toBeVisible();
    await assertNoHorizontalScroll(page);

    await page.screenshot({
      path: testInfo.outputPath("scan-editorial.png"),
      fullPage: true,
    });
  });
});
