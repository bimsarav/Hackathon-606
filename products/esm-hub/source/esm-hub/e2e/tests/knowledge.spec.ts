import { expect, test } from '@playwright/test';
import { signIn, USERS } from './helpers';

test('KB search and read', async ({ page }) => {
  await signIn(page, USERS.employee);
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Knowledge', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Knowledge base' })).toBeVisible();

  // The list shows published articles; open the first one and read it.
  const first = page.locator('.articles h2 a').first();
  await expect(first).toBeVisible();
  const title = (await first.innerText()).trim();

  // Search by a word of that title and find the article again.
  const word = title.split(/\s+/).find((w) => w.length > 3) ?? title;
  await page.getByLabel('Search articles').fill(word);
  await page.getByRole('button', { name: 'Search' }).click();
  const hit = page.locator('.articles h2 a', { hasText: title });
  await expect(hit.first()).toBeVisible();

  await hit.first().click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title);
  await expect(page.locator('.article-body')).not.toBeEmpty();
  await expect(page.getByRole('heading', { name: 'Was this article helpful?' })).toBeVisible();
  await page.getByRole('button', { name: 'Helpful', exact: true }).click();
  await expect(page.getByText('your feedback was recorded')).toBeVisible();
});
