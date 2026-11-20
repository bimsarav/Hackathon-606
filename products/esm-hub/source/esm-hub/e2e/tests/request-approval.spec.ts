import { expect, test } from '@playwright/test';
import { signIn, USERS } from './helpers';

test('a catalogue request is submitted and the manager approves it', async ({ page }) => {
  const title = `E2E VPN access ${Date.now()}`;

  await signIn(page, USERS.employee);
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Catalogue', exact: true }).click();
  await page.locator('article', { hasText: 'Request: VPN' }).getByRole('button', { name: 'Request this' }).click();
  await page.getByLabel('Request title').fill(title);
  await page.getByLabel('Details').fill('Need VPN for remote work next month.');
  await page.getByRole('button', { name: 'Submit request' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText(title);
  await expect(page.getByTestId('request-status')).toContainText(/pending approval|submitted/i);
  const requestUrl = page.url();

  await signIn(page, USERS.manager);
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Approvals', exact: true }).click();
  const row = page.getByTestId('approval-row').filter({ hasText: title });
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: /^Approve/ }).click();
  await expect(page.getByTestId('approval-row').filter({ hasText: title })).toHaveCount(0);

  await signIn(page, USERS.employee);
  await page.goto(requestUrl);
  await expect(page.getByTestId('request-status')).toContainText(/approved|in progress|fulfilled/i);
});
