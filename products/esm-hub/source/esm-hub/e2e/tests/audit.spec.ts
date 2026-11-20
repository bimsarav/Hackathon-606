import { expect, test } from '@playwright/test';
import { signIn, USERS } from './helpers';

test('an auditor views the audit log', async ({ page }) => {
  await signIn(page, USERS.auditor);
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Audit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Audit log' })).toBeVisible();
  const table = page.getByRole('region', { name: 'Audit entries' });
  await expect(table).toBeVisible();
  await expect(table.locator('tbody tr').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Export CSV' })).toBeVisible();
  // Auditors are read-only: no admin navigation
  await expect(page.getByRole('link', { name: 'Admin' })).toHaveCount(0);
});
