import { expect, type Page, test } from "@playwright/test";

const user = process.env.E2E_USER ?? "occ";
const password = process.env.E2E_PASSWORD ?? "";

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("User name").fill(user);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("region", { name: "New scenario" })).toBeVisible();
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
  await page.getByRole("button", { name: "Flight Delay", exact: true }).click();
  await page.locator(".preset-list .preset").first().click();
  await expect(page.getByRole("heading", { name: "Recovery options", exact: true })).toBeVisible();
  const recommended = page.locator("tr.recommended");
  await expect(recommended).toHaveCount(1);
  await expect(page.getByRole("heading", { name: "Why?", exact: true })).toBeVisible();
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
  await page.getByRole("button", { name: "Cancellation", exact: true }).click();
  await page.locator(".preset-list .preset").first().click();
  await page.getByRole("button", { name: "Show passenger detail" }).click();
  await expect(page.getByRole("heading", { name: "Passengers in priority order" })).toBeVisible();
  const firstTier = page.locator("table.pax tbody tr").first().locator(".tier");
  await expect(firstTier).toHaveText("Care");
  await expect(page.locator("tr.unprotected").first()).toBeVisible(); // not enough seats for everyone

  await page.getByLabel(/Loyalty tier/).fill("50");
  await page.getByRole("button", { name: "Re-run with these weights" }).click();
  await expect(page.locator("table.pax tbody tr").first().locator(".tier")).toHaveText("Care");

  await page.getByRole("button", { name: /Details/ }).first().click();
  await expect(page.locator("tr.detail")).toContainText("Priority score");
  await expect(page.locator("tr.detail .message")).toContainText("Dear customer");
  await page.getByRole("button", { name: "Approve rebooking plan" }).click();
  await expect(page.locator(".audit").last()).toContainText("APPROVE");
});

test("phase 2: delay watchlist ranks flights, shows reasons and opens a delay scenario", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: "Delay Watchlist", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Delay watchlist/ })).toBeVisible();
  await page.getByRole("combobox", { name: /^Risk/ }).selectOption("all");
  const table = page.getByRole("table", { name: "Watchlist flights" });
  await expect(table).toBeVisible();
  await table.locator("tbody tr.clickable").first().locator("button.link").click();
  await expect(page.getByRole("heading", { name: "Why this flight" })).toBeVisible();
  await page.getByRole("button", { name: /^Analyse a/ }).click();
  await expect(page.getByRole("heading", { name: "Recovery options", exact: true })).toBeVisible();
});

test("phase 3: strategies switch the recommendation", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: "Flight Delay", exact: true }).click();
  await page.locator(".preset-list .preset").first().click();
  await expect(page.getByRole("heading", { name: "Strategies compared" })).toBeVisible();
  await page.getByRole("button", { name: /Strategies compared/ }).click(); // sections fold until opened
  await expect(page.locator(".strategy-card.active")).toHaveAttribute("data-strategy", "lowest_cost");

  await page.locator('.strategy-card[data-strategy="protect_passengers"]').click();
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
  await page.getByRole("button", { name: "Predict the Flight Delay", exact: true }).click();
  await page.getByLabel("Strategy", { exact: true }).selectOption("protect_passengers");
  await page.locator(".preset-list .preset").first().click();
  // Works whether the AI or the rule-based planner answers.
  await expect(page.locator("[data-status]").first()).toHaveAttribute("data-status", "DONE", { timeout: 120_000 });
  expect(await page.locator("ol.agent-steps > li").count()).toBeGreaterThanOrEqual(3);
  await expect(page.getByRole("heading", { name: /^Recommendation/ })).toBeVisible();
  await expect(page.locator(".agent-panel .reasons li").first()).toBeVisible();
  await page.getByRole("button", { name: "Open scenario to review and approve" }).click();
  await expect(page.getByRole("heading", { name: "Recovery options", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Agent recommendation/ })).toBeVisible();
});

test("phase 2: the 7-day page shows last month's cascade check and no scenario launcher", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("region", { name: "New scenario" })).toBeVisible();
  await page.getByRole("button", { name: "Delay Watchlist", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Last month: cascade formula vs actual" })).toBeVisible();
  await expect(page.getByText("Within ±15 min").first()).toBeVisible();
  await page.getByRole("button", { name: "Expand the full view" }).click();
  await expect(page.getByRole("dialog", { name: "Cascade prediction vs actual" })).toBeVisible();
  await expect(page.getByRole("img", { name: /Scatter of/ })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByRole("region", { name: "New scenario" })).toBeHidden();
  await page.getByRole("button", { name: "Flight Delay", exact: true }).click();
  await expect(page.getByRole("region", { name: "New scenario" })).toBeVisible();
});

test("phase 5: a budget gives a reward plan from the preference model, and the plan can be approved", async ({ page }) => {
  await signIn(page);
  await page.getByRole("button", { name: "Flight Delay", exact: true }).click();
  await page.locator(".preset-list .preset").first().click();
  await page.getByRole("button", { name: "Show rewards & compensation" }).click();
  await expect(page.getByRole("heading", { name: "Passenger rewards (goodwill)" })).toBeVisible();
  await page.getByLabel("Budget (AED)").fill("4000");
  await page.getByRole("button", { name: "Recommend rewards" }).click();
  await expect(page.getByText(/trained on simulated redemption history/)).toBeVisible();
  await expect(page.getByText(/Planned spend/)).toBeVisible();
  await expect(page.getByRole("columnheader", { name: /Recommended reward/ })).toBeVisible();
  await page.getByRole("button", { name: /Approve reward plan/ }).click();
  await expect(page.locator("section.rewards .audit")).toContainText("APPROVE");
});
