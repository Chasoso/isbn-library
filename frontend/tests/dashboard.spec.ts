import { expect, test } from "@playwright/test";

test.describe("frontend dashboard visuals", () => {
  test("home dashboard captures the updated bookshelf-focused layout", async ({ page }, testInfo) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "ホーム" })).toBeVisible();
    await expect(page.getByText("本棚の状態をひと目で把握")).toBeVisible();
    await expect(page.getByRole("button", { name: "検索" })).toBeVisible();
    await expect(page.getByRole("link", { name: /スキャンする/ })).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("home-dashboard.png"),
      fullPage: true,
    });
  });

  test("bookshelf page captures shelf layout and filters", async ({ page }, testInfo) => {
    await page.goto("/books");
    await expect(page.getByRole("heading", { name: "蔵書一覧" })).toBeVisible();
    await expect(page.getByText("本棚を眺めるように管理する")).toBeVisible();
    await expect(page.getByText("Books")).toBeVisible();
    await expect(page.locator(".library-toolbar").getByRole("link", { name: "カテゴリ管理" })).toBeVisible();

    await expect(page.locator(".coverflow-book.is-active").first()).toBeVisible();
    await expect(page.locator(".coverflow-selection")).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("bookshelf-view.png"),
      fullPage: true,
    });
  });

  test("book detail page captures desktop layout", async ({ page }, testInfo) => {
    await page.goto("/books/9784860648114");
    await expect(page.locator(".detail-grid")).toBeVisible();
    await expect(page.locator(".detail-status-panel")).toBeVisible();
    await expect(page.locator(".detail-actions")).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("book-detail-desktop.png"),
      fullPage: true,
    });
  });

  test("categories page captures management layout", async ({ page }, testInfo) => {
    await page.goto("/categories");
    await expect(page.getByRole("heading", { name: "カテゴリ管理" })).toBeVisible();
    await expect(page.getByPlaceholder("新しいカテゴリ名")).toBeVisible();
    await expect(page.locator(".category-card").first()).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("categories-view.png"),
      fullPage: true,
    });
  });
});
