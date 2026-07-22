import { expect, test } from "@playwright/test";


test("operator creates, evaluates, and reviews a real persisted demo ticket", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Support readiness workbench" })).toBeVisible();
  await expect(page.getByLabel("System boundary")).toContainText("No automatic send");

  await page.getByRole("button", { name: "Create synthetic ticket" }).click();
  const newestTicket = page.getByRole("listitem").first();
  await expect(newestTicket).toContainText("Where is my fictional order?");

  await newestTicket.getByRole("button", { name: /Evaluate T-DEMO-/ }).click();
  await expect(page.getByRole("heading", { name: "Review-only draft" })).toBeVisible();
  await expect(page.getByText("0 — unavailable by design")).toBeVisible();
  await expect(page.getByRole("button", { name: /send/i })).toHaveCount(0);

  await page.getByRole("button", { name: "Record approval" }).click();
  await expect(page.getByText("approved", { exact: true })).toBeVisible();
  await expect(page.getByText("ready_for_authorized_human_send")).toBeVisible();
});


test("mobile workbench has no page-level horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
});
