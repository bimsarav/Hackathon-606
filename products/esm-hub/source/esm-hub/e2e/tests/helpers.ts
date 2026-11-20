import { expect, type APIRequestContext, type Page } from '@playwright/test';

export const PASSWORD = 'Demo-Passw0rd1';

/** nginx refills one login token every 12 s; wait a little longer, at most 8 times. */
const LOGIN_RETRY_WAIT_MS = 13_000;
const MAX_LOGIN_RETRIES = 8;

export const USERS = {
  agent: 'omar.ahmed2@example.test',
  technician: 'maya.clark3@example.test',
  teamLead: 'daniel.jones4@example.test',
  serviceManager: 'sara.khan5@example.test',
  changeManager: 'liam.brown6@example.test',
  assetManager: 'noor.ahmed7@example.test',
  kbEditor: 'adam.clark8@example.test',
  admin: 'emily.jones9@example.test',
  auditor: 'zain.khan10@example.test',
  employee: 'priya.brown11@example.test',
  manager: 'aisha.brown1@example.test',
} as const;

/** Sign out (if signed in) and sign in as the given user through the login form. */
export async function signIn(page: Page, email: string): Promise<void> {
  await page.goto('/login');
  const signOut = page.getByRole('button', { name: 'Sign out' });
  if (await signOut.isVisible().catch(() => false)) {
    await signOut.click();
  } else {
    await page.evaluate(() => sessionStorage.clear());
    await page.goto('/login');
  }
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  const nav = page.getByRole('navigation', { name: 'Main' });
  const throttled = page.getByText('Too Many Requests').first();
  for (let attempt = 0; ; attempt++) {
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(nav.or(throttled)).toBeVisible();
    if (await nav.isVisible()) return;
    // The web tier rate-limits /auth/login (nginx: 5 r/min per IP). Respect it instead of weakening it.
    expect(attempt, 'login still throttled after retries').toBeLessThan(MAX_LOGIN_RETRIES);
    await page.waitForTimeout(LOGIN_RETRY_WAIT_MS);
  }
}

/** Log in over the API and return the user's team ids (to pick the right team in the assignment form). */
export async function teamIdsOf(request: APIRequestContext, email: string): Promise<number[]> {
  let login = await request.post('/api/v1/auth/login', { data: { email, password: PASSWORD } });
  for (let attempt = 0; login.status() === 429 && attempt < MAX_LOGIN_RETRIES; attempt++) {
    await new Promise((r) => setTimeout(r, LOGIN_RETRY_WAIT_MS));
    login = await request.post('/api/v1/auth/login', { data: { email, password: PASSWORD } });
  }
  expect(login.ok()).toBeTruthy();
  const { accessToken } = await login.json();
  const me = await request.get('/api/v1/auth/me', { headers: { Authorization: `Bearer ${accessToken}` } });
  expect(me.ok()).toBeTruthy();
  return (await me.json()).teamIds as number[];
}
