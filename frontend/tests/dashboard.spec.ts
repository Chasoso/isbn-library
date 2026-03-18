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
    await expect(page.getByRole("button", { name: "絞り込む" })).toBeVisible();

    const firstSpine = page.locator(".bookshelf-spine").first();
    await firstSpine.click();
    await expect(page.locator(".bookshelf-book.is-selected").first()).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath("bookshelf-view.png"),
      fullPage: true,
    });
  });
});
