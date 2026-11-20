import { expect, test } from '@playwright/test';
import { signIn, USERS } from './helpers';

test('an employee cannot see the admin navigation', async ({ page }) => {
  await signIn(page, USERS.employee);
  const nav = page.getByRole('navigation', { name: 'Main' });
  await expect(nav.getByRole('link', { name: 'Incidents' })).toBeVisible();
  for (const name of ['Admin', 'Audit', 'Reports']) {
    await expect(nav.getByRole('link', { name })).toHaveCount(0);
  }
  // Deep links bounce back to the dashboard
  await page.goto('/admin/users');
  await expect(page).not.toHaveURL(/\/admin/);
  await page.goto('/audit');
  await expect(page).not.toHaveURL(/\/audit/);
});

test('an admin sees the admin navigation', async ({ page }) => {
  await signIn(page, USERS.admin);
  const nav = page.getByRole('navigation', { name: 'Main' });
  for (const name of ['Admin', 'Audit', 'Reports']) {
    await expect(nav.getByRole('link', { name })).toBeVisible();
  }
});
