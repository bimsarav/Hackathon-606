import { expect, test } from '@playwright/test';
import { signIn, teamIdsOf, USERS } from './helpers';

test('employee raises an incident, agent assigns it, technician resolves it, employee sees it resolved', async ({ page, request }) => {
  const title = `E2E printer jam ${Date.now()}`;
  const techTeams = await teamIdsOf(request, USERS.technician);
  expect(techTeams.length).toBeGreaterThan(0);

  // Employee raises the incident
  await signIn(page, USERS.employee);
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Incidents', exact: true }).click();
  await page.getByRole('link', { name: 'New incident' }).click();
  await page.getByLabel('Title').fill(title);
  await page.getByLabel('Description').fill('The third floor printer keeps jamming on every job.');
  await page.getByRole('button', { name: 'Submit incident' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText(title);
  await expect(page.getByTestId('incident-status')).toContainText(/new/i);
  const incidentUrl = page.url();
  expect(incidentUrl).toMatch(/\/incidents\/\d+$/);

  // Service desk agent assigns it to the technician's team and the technician
  await signIn(page, USERS.agent);
  await page.goto(incidentUrl);
  await expect(page.getByRole('heading', { level: 1 })).toContainText(title);
  await page.getByLabel('Team', { exact: true }).selectOption(String(techTeams[0]));
  await expect(page.getByLabel('Member').locator('option', { hasText: 'Maya' })).toHaveCount(1);
  await page.getByLabel('Member').selectOption({ label: await page.getByLabel('Member').locator('option', { hasText: 'Maya' }).innerText() });
  await page.getByRole('button', { name: 'Assign', exact: true }).click();
  await expect(page.getByTestId('incident-status')).toContainText(/assigned/i);

  // Technician starts and resolves it
  await signIn(page, USERS.technician);
  await page.goto(incidentUrl);
  await page.getByLabel('New status').selectOption('IN_PROGRESS');
  await page.getByRole('button', { name: 'Update status' }).click();
  await expect(page.getByTestId('incident-status')).toContainText(/in progress/i);
  await page.getByLabel('New status').selectOption('RESOLVED');
  await page.getByLabel('Resolution code').selectOption('SOLVED');
  await page.getByLabel('Resolution notes').fill('Cleared the paper path and replaced the roller.');
  await page.getByRole('button', { name: 'Update status' }).click();
  await expect(page.getByTestId('incident-status')).toContainText(/resolved/i);

  // Employee sees it resolved
  await signIn(page, USERS.employee);
  await page.goto(incidentUrl);
  await expect(page.getByTestId('incident-status')).toContainText(/resolved/i);
  await expect(page.getByText('Cleared the paper path and replaced the roller.')).toBeVisible();
});
