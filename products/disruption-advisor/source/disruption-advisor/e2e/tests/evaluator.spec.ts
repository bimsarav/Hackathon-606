import { expect, type Page, test } from "@playwright/test";

const user = process.env.E2E_USER ?? "occ";
const password = process.env.E2E_PASSWORD ?? "";
const evalUser = process.env.E2E_EVAL_USER ?? "";
const evalPassword = process.env.E2E_EVAL_PASSWORD ?? "";

const FLIGHTS = `flight_number,date,origin,destination,std,sta,aircraft_registration,seat_capacity,booked_seats
G9981,2026-11-22,KHI,SHJ,05:00,07:30,A6-TS1,174,160
G9983,2026-11-22,SHJ,HBE,09:00,13:30,A6-TS2,174,174
`;
const PASSENGERS = `pnr,first_name,last_name,pax_type,flight_number,date,fare_family,fare_aed,loyalty_tier,travel_frequency,special_service
TS0001,Ahmed,Raza,AD,G9981,2026-11-22,Basic,,none,occasional,WCHR
TS0001,Ahmed,Raza,AD,G9983,2026-11-22,Basic,,none,occasional,WCHR
TS0002,Omar,Siddiqui,AD,G9981,2026-11-22,Ultimate,1450,Platinum,frequent,
TS0002,Omar,Siddiqui,AD,G9983,2026-11-22,Ultimate,1450,Platinum,frequent,
`;

async function signInAs(page: Page, name: string, secret: string) {
  await page.goto("/");
  await page.getByLabel("User name").fill(name);
  await page.getByLabel("Password").fill(secret);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("region", { name: "New scenario" })).toBeVisible();
}

test("the OCC role does not see the Model Card and Test data views, and the API refuses them", async ({ page, request }) => {
  await signInAs(page, user, password);
  const nav = page.getByRole("complementary", { name: "Navigation" });
  await expect(nav.getByRole("button", { name: "Delay Watchlist" })).toBeVisible();
  await expect(nav.getByRole("button", { name: "Model Card" })).toHaveCount(0);
  await expect(nav.getByRole("button", { name: "Test data" })).toHaveCount(0);
  const login = await request.post("/api/v1/auth/login", { data: { username: user, password } });
  const token = ((await login.json()) as { token: string }).token;
  const headers = { Authorization: `Bearer ${token}` };
  expect((await request.get("/api/v1/test-data", { headers })).status()).toBe(403);
  expect((await request.get("/api/v1/risk/model", { headers })).status()).toBe(403);
});

test("the evaluator reads the model evidence, uploads two flights, analyses one and removes them", async ({ page }) => {
  test.skip(!evalUser, "set E2E_EVAL_USER and E2E_EVAL_PASSWORD (an EVALUATOR account)");
  test.setTimeout(180_000);
  await signInAs(page, evalUser, evalPassword);
  const nav = page.getByRole("complementary", { name: "Navigation" });

  await nav.getByRole("button", { name: "Model Card" }).click();
  await expect(page.getByRole("heading", { name: "Model overview" })).toBeVisible();
  // One box per model or rule; each opens a detail page with charts and tables.
  await page.getByRole("button", { name: /Delay risk \(departure\): open details/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Delay risk (departure)" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Ranking quality (AUC) by delay threshold" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Calibration: delay of 60+ minutes" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Models compared on validation (Brier skill score)" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Performance by threshold" })).toBeVisible();
  await page.getByRole("button", { name: "← All models" }).click();
  await page.getByRole("button", { name: /Arrival delay & missed connections: open details/ }).click();
  await expect(page.getByRole("img", { name: /Missed connections: predicted vs what happened/ })).toBeVisible();
  await page.getByRole("button", { name: "← All models" }).click();
  await page.getByRole("button", { name: /Reward preference: open details/ }).click();
  await expect(page.getByText(/Trained on SIMULATED redemption history/)).toBeVisible();
  await expect(page.getByRole("img", { name: "Ranking quality (AUC) by reward type" })).toBeVisible();
  await page.getByRole("button", { name: "← All models" }).click();
  await page.getByRole("button", { name: /Cascade \(knock-on\) formula: open details/ }).click();
  await expect(page.getByRole("table", { name: "Cascade check summary" })).toBeVisible();
  await page.getByRole("button", { name: "← All models" }).click();

  await nav.getByRole("button", { name: "Test data" }).click();
  await expect(page.getByRole("heading", { name: "Test data" })).toBeVisible();
  try {
    await page.getByLabel("Upload flights sheet").setInputFiles({ name: "flights.csv", mimeType: "text/csv", buffer: Buffer.from(FLIGHTS) });
    await page.getByLabel("Upload passengers sheet").setInputFiles({ name: "passengers.csv", mimeType: "text/csv", buffer: Buffer.from(PASSENGERS) });
    await page.getByRole("button", { name: "Check files" }).click();
    await expect(page.getByText("Files are valid")).toBeVisible();
    await page.getByRole("button", { name: "Add to system" }).click();
    await expect(page.getByText("Test data loaded")).toBeVisible();
    await expect(page.getByText(/Delay risk scored with the saved model for 2 flights/)).toBeVisible();

    await nav.getByRole("button", { name: "Flight Delay", exact: true }).click();
    await page.locator("#ff-flight").fill("G9981");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await page.locator(".preset-list .preset").first().click();
    await expect(page.getByRole("heading", { name: "Recovery options", exact: true })).toBeVisible();
    await expect(page.locator("h1")).toContainText("G9981");
  } finally {
    // Always leave the system as found: wait for the page to say what is loaded, then remove it.
    await nav.getByRole("button", { name: "Test data" }).click();
    await expect(page.getByText(/Test data loaded|No test data is loaded/).first()).toBeVisible();
    const remove = page.getByRole("button", { name: "Remove test data" });
    if (await remove.count()) await remove.click();
    await expect(page.getByText(/No test data is loaded/)).toBeVisible();
  }
});

test("a bad flights sheet is rejected with the row and column, and nothing is added", async ({ page }) => {
  test.skip(!evalUser, "set E2E_EVAL_USER and E2E_EVAL_PASSWORD (an EVALUATOR account)");
  await signInAs(page, evalUser, evalPassword);
  await page.getByRole("complementary", { name: "Navigation" }).getByRole("button", { name: "Test data" }).click();
  const bad = FLIGHTS.replace("KHI,SHJ", "KHIX,SHJ");
  await page.getByLabel("Upload flights sheet").setInputFiles({ name: "flights.csv", mimeType: "text/csv", buffer: Buffer.from(bad) });
  await page.getByLabel("Upload passengers sheet").setInputFiles({ name: "passengers.csv", mimeType: "text/csv", buffer: Buffer.from(PASSENGERS) });
  await page.getByRole("button", { name: "Check files" }).click();
  const problems = page.getByRole("table", { name: "Problems found" });
  await expect(problems).toContainText("origin");
  await expect(problems).toContainText("not a 3-letter airport code");
  await expect(page.getByRole("button", { name: "Add to system" })).toBeDisabled();
});
