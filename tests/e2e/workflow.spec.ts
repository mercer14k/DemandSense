import { test, expect } from "../../apps/web/node_modules/@playwright/test";
import { resolve } from "node:path";
const shots = resolve(process.cwd(), "../../docs/screenshots");
test("planner can inspect, explain, stress-test and export a real forecast", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Demand, with perspective." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Export forecast", exact: true }),
  ).toBeEnabled({ timeout: 30000 });
  await expect(page.getByText("1,500", { exact: true })).toBeVisible();
  await page.screenshot({
    path: resolve(shots, "workspace.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Explain from computed evidence" })
    .click();
  await expect(
    page.getByText(
      "Template explanation generated directly from computed evidence.",
      { exact: false },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "View backtests" }).click();
  await expect(
    page.getByRole("heading", { name: "Backtesting laboratory" }),
  ).toBeVisible();
  await page.screenshot({
    path: resolve(shots, "backtests.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page.getByLabel("Demand adjustment (%)").fill("25");
  await page
    .getByRole("button", { name: "Apply scenario", exact: true })
    .click();
  await expect(
    page.getByText("Saved scenario", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("Conditional scale transformation.", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: resolve(shots, "scenario.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Forecast workspace", exact: true })
    .click();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export forecast", exact: true })
    .click();
  expect((await download).suggestedFilename()).toMatch(/forecast-.*\.csv/);
  await page.getByLabel("Search SKU", { exact: true }).fill("SKU-0003");
  await page.getByRole("button", { name: /SKU-0003 CHI/ }).click();
  await expect(
    page.getByRole("heading", { name: "SKU-0003", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Data & provenance", exact: true })
    .click();
  await page.getByRole("button", { name: "Load validation reports" }).click();
  await expect(
    page.getByText("accepted", { exact: true }).first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("narrow viewport remains usable without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Export forecast", exact: true }),
  ).toBeEnabled({ timeout: 30000 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: resolve(shots, "mobile.png"), fullPage: true });
});
test("malformed CSV produces a visible atomic rejection", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Data & provenance", exact: true })
    .click();
  await page
    .getByLabel("Upload demand CSV")
    .setInputFiles({
      name: "bad.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(
        "record_id,dataset_id,sku,location,date,demand\nbad,invalid-demo,SKU-1,CHI,2025-01-01,-10\n",
      ),
    });
  await expect(
    page.getByText("rejected", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText(/greater than or equal to 0/)).toBeVisible();
});
