import { test, expect } from "@playwright/test";

test("dashboard shell renders accessible main landmark", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("main", { name: "Vue synthétique DEV_CORE" })).toBeVisible();
  await expect(page.getByText("DEV_CORE Platform")).toBeVisible();
});
