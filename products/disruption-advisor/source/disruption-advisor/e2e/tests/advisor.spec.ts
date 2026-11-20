import { expect, type Page, test } from "@playwright/test";

const user = process.env.E2E_USER ?? "occ";
const password = process.env.E2E_PASSWORD ?? "";

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("User name").fill(user);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Start with a disruption")).toBeVisible();
}

test("wrong password is rejected and the API needs a token", async ({ page, request }) => {
  await page.goto("/");
  await page.getByLabel("User name").fill(user);
  await page.getByLabel("Password").fill("definitely-wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toContainText("Wrong user name or password");
  expect((await request.get("/api/v1/meta")).status()).toBe(401);
});

test("scenario A: a delay is assessed, options compared, recommendation approved", async ({ page }) => {
  await signIn(page);
  await page.getByRole("tab", { name: "A · Delay" }).click();
  await page.locator(".preset-list .preset").first().click();
  await expect(page.getByRole("heading", { name: "Recovery options compared" })).toBeVisible();
  const recommended = page.locator("tr.recommended");
  await expect(recommended).toHaveCount(1);
  await expect(page.getByRole("heading", { name: /Why this recommendation/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Rotation impact/ })).toBeVisible();
  await page.getByRole("button", { name: "Approve recommended option" }).click();
  await expect(page.locator(".audit").first()).toContainText("APPROVE");
});

test("scenario B: a cancellation ranks passengers by tier and re-runs with new weights", async ({ page }) => {
  await signIn(page);
  await page.getByRole("tab", { name: "B · Cancellation" }).click();
  await page.locator(".preset-list .preset").first().click();
  await expect(page.getByRole("heading", { name: "Passengers in priority order" })).toBeVisible();
  const firstTier = page.locator("table.pax tbody tr").first().locator(".tier");
  await expect(firstTier).toHaveText("Care");
  await expect(page.locator("tr.unprotected").first()).toBeVisible(); // not enough seats for everyone

  await page.getByLabel(/Loyalty tier/).fill("50");
  await page.getByRole("button", { name: "Re-run with these weights" }).click();
  await expect(page.locator("table.pax tbody tr").first().locator(".tier")).toHaveText("Care");

  await page.getByRole("button", { name: "Why & message" }).first().click();
  await expect(page.locator("tr.detail")).toContainText("Tier 1");
  await expect(page.locator("tr.detail .message")).toContainText("Dear customer");
  await page.getByRole("button", { name: "Approve rebooking plan" }).click();
  await expect(page.locator(".audit").last()).toContainText("APPROVE");
});
