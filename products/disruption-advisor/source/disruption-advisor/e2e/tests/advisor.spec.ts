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
  await expect(page.getByRole("heading", { name: /Flights affected/ })).toBeVisible();
  await page.getByRole("button", { name: "Approve recommended option" }).click();
  await expect(page.locator(".audit").first()).toContainText("APPROVE");

  // Choose another option: it becomes the selection, and approving it needs a reason (override).
  const other = page.locator("tr.option-row:not(.recommended)").first();
  if (await other.count()) {
    await other.click();
    await expect(page.locator("tr.option-row.selected")).not.toHaveClass(/recommended/);
    const approve = page.getByRole("button", { name: "Approve selected option (override)" });
    await expect(approve).toBeDisabled();
    await page.getByPlaceholder("Reason for choosing this option (required)").fill("Crew for the recommended aircraft not legal");
    await approve.click();
    await expect(page.getByText(/OVERRIDE: Crew for the recommended aircraft not legal/)).toBeVisible();
  }

  // The delay slider re-runs the scenario on screen.
  const slider = page.getByLabel(/Delay:/);
  await slider.focus();
  await slider.press("ArrowLeft");
  await expect(page.locator("h1")).toContainText("+2 h 15 min");
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

test("phase 2: delay watchlist ranks flights, shows reasons and opens a delay scenario", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: /Delay watchlist/ }).click();
  await expect(page.getByRole("heading", { name: /Delay watchlist/ })).toBeVisible();
  await page.getByLabel("Risk").selectOption("all");
  const table = page.getByRole("table", { name: "Watchlist flights" });
  await expect(table).toBeVisible();
  await table.locator("tbody tr.clickable").first().locator("button.link").click();
  await expect(page.getByRole("heading", { name: "Why this flight" })).toBeVisible();
  await page.getByRole("button", { name: /^Analyse a/ }).click();
  await expect(page.getByRole("heading", { name: "Recovery options compared" })).toBeVisible();
});

test("phase 3: strategies switch the recommendation", async ({ page }) => {
  await signIn(page);
  await page.getByRole("tab", { name: "A · Delay" }).click();
  await page.locator(".preset-list .preset").first().click();
  await expect(page.getByRole("heading", { name: "Strategies compared" })).toBeVisible();
  const switcher = page.getByRole("group", { name: "Strategy" });
  await expect(switcher.getByRole("button", { name: "Lowest cost" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".strategy-card.active")).toHaveAttribute("data-strategy", "lowest_cost");

  await switcher.getByRole("button", { name: "Protect passengers" }).click();
  await expect(switcher.getByRole("button", { name: "Protect passengers" })).toHaveAttribute("aria-pressed", "true");
  const active = page.locator(".strategy-card.active");
  await expect(active).toHaveAttribute("data-strategy", "protect_passengers");
  const pick = (await active.locator(".strategy-pick").innerText()).trim();
  await expect(page.locator("tr.recommended")).toHaveCount(1);
  await expect(page.locator("tr.recommended th")).toContainText(pick);
  await expect(page.locator("tr.option-row.selected")).toHaveClass(/recommended/);
});

test("phase 3: the agent investigates a flight and its recommendation opens for approval", async ({ page }) => {
  test.setTimeout(180_000);
  await signIn(page);
  await page.getByRole("tab", { name: "Ask the agent" }).click();
  await page.getByLabel("Strategy", { exact: true }).selectOption("protect_passengers");
  await page.locator(".preset-list .preset").first().click();
  // Works whether the AI or the rule-based planner answers.
  await expect(page.locator("[data-status]").first()).toHaveAttribute("data-status", "DONE", { timeout: 120_000 });
  expect(await page.locator("ol.agent-steps > li").count()).toBeGreaterThanOrEqual(3);
  await expect(page.getByRole("heading", { name: /^Recommendation/ })).toBeVisible();
  await expect(page.locator(".agent-panel .reasons li").first()).toBeVisible();
  await page.getByRole("button", { name: "Open scenario to review and approve" }).click();
  await expect(page.getByRole("heading", { name: "Recovery options compared" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Agent recommendation/ })).toBeVisible();
});
