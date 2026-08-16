import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "@playwright/test";

const baseUrl = process.env.BASE_URL ?? "http://127.0.0.1:4173";
const outputRoot = path.resolve("..", "artifacts", "screenshots", "2026-08-16-refine");

const viewports = [
  { name: "320x568", width: 320, height: 568, mobile: true },
  { name: "375x667", width: 375, height: 667, mobile: true },
  { name: "768x1024", width: 768, height: 1024, mobile: false },
  { name: "1440x900", width: 1440, height: 900, mobile: false },
];

const pages = [
  { name: "home", url: "/" },
  { name: "books", url: "/books" },
  { name: "book-detail", url: "/books/9784860648114" },
  { name: "categories", url: "/categories" },
  { name: "scan", url: "/scan" },
];

await mkdir(outputRoot, { recursive: true });

const browser = await chromium.launch({ headless: true });

try {
  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      isMobile: viewport.mobile,
      hasTouch: viewport.mobile,
      deviceScaleFactor: 1,
    });

    const page = await context.newPage();
    const viewportDir = path.join(outputRoot, viewport.name);
    await mkdir(viewportDir, { recursive: true });

    for (const target of pages) {
      await page.goto(`${baseUrl}${target.url}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(400);
      await page.screenshot({
        path: path.join(viewportDir, `${target.name}.png`),
        fullPage: false,
      });
    }

    await context.close();
  }
} finally {
  await browser.close();
}
