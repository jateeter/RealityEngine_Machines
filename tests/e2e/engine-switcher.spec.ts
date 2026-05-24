import { test, expect } from '@playwright/test';

/**
 * E2E test for the EngineSwitcher UI component.
 *
 * Requires the Visualizer to be running and at least two engine instances
 * registered.  Skipped when RE_REGISTRY_URL is not set or only one instance
 * is available.
 */

const VIZ_URL      = process.env.VIZ_FRONTEND_URL ?? 'https://localhost:5173';
const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';

interface EngineInstance { id: string; re_url: string; pe_url: string; }

test.describe('EngineSwitcher UI', () => {
  test.skip(() => !REGISTRY_URL, 'RE_REGISTRY_URL not set — skipping engine-switcher UI tests');

  test.beforeEach(async ({ page }) => {
    await page.goto(VIZ_URL, { waitUntil: 'networkidle' });
  });

  test('switcher button is visible when multiple instances exist', async ({ page, request }) => {
    // Check instance count first
    const resp = await request.get(REGISTRY_URL);
    const body = await resp.json() as { instances?: EngineInstance[] };
    const count = body.instances?.length ?? 0;
    test.skip(count < 2, `Only ${count} instance(s) — switcher requires 2+`);

    const switcher = page.locator('[title="Switch active engine instance"]');
    await expect(switcher).toBeVisible({ timeout: 10_000 });
  });

  test('dropdown opens and lists instances', async ({ page, request }) => {
    const resp = await request.get(REGISTRY_URL);
    const body = await resp.json() as { instances?: EngineInstance[] };
    const instances = body.instances ?? [];
    test.skip(instances.length < 2, `Only ${instances.length} instance(s)`);

    // Open the switcher
    const switcher = page.locator('[title="Switch active engine instance"]');
    await switcher.click();

    // All instances should appear in the dropdown
    for (const inst of instances) {
      await expect(page.getByText(inst.id)).toBeVisible({ timeout: 5_000 });
    }
  });

  test('selecting an instance switches active engine and updates machine list', async ({ page, request }) => {
    const resp = await request.get(REGISTRY_URL);
    const body = await resp.json() as { instances?: EngineInstance[] };
    const instances = body.instances ?? [];
    test.skip(instances.length < 2, `Only ${instances.length} instance(s)`);

    // Get initial machine list count from Manager
    const beforeEnginesResp = await request.get(`${VIZ_URL.replace('5173', '3001')}/api/engines`, { ignoreHTTPSErrors: true });
    const beforeEngines = await beforeEnginesResp.json() as { activeId: string | null };
    const firstActiveId = beforeEngines.activeId;

    // Pick a different instance
    const target = instances.find(i => i.id !== firstActiveId) ?? instances[1];

    // Open switcher and click target
    const switcher = page.locator('[title="Switch active engine instance"]');
    await switcher.click();
    await page.getByText(target.id, { exact: true }).first().click();

    // Wait for switcher to update (button label changes to target id)
    await expect(page.locator('[title="Switch active engine instance"]')).toContainText(target.id, { timeout: 8_000 });

    // Verify Manager reports the new active ID
    await page.waitForTimeout(500);
    const afterEnginesResp = await request.get(`${VIZ_URL.replace('5173', '3001')}/api/engines`, { ignoreHTTPSErrors: true });
    const afterEngines = await afterEnginesResp.json() as { activeId: string | null };
    expect(afterEngines.activeId).toBe(target.id);

    // Restore original active instance
    if (firstActiveId) {
      await request.post(`${VIZ_URL.replace('5173', '3001')}/api/engines/active`, {
        data: { id: firstActiveId },
        ignoreHTTPSErrors: true,
      });
    }
  });
});
