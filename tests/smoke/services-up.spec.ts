import { test, expect } from '@playwright/test';
import { deployed, requireEngine, requireService, type Deployed } from '../support/deployed-endpoints.js';

/**
 * Smoke tests — lightweight HTTP-only checks, no browser.
 * Runs first in CI to fast-fail before heavier suites.
 *
 * Every endpoint is the deployed one (tests/support/deployed-endpoints.ts): each
 * engine instance the instance registry lists is checked, and the support
 * services come from its `services` block. RE_BASE_URL / PE_BASE_URL still
 * address a single engine directly. There is no literal-port fallback.
 */

test.describe('Service Smoke Tests', () => {
  let ep: Deployed;
  test.beforeEach(async ({ request }) => { ep = await deployed(request); });

  /** Every listed instance, or the single engine named by env. */
  const engines = () => ep.instances.length > 0
    ? ep.instances
    : [{ id: 'env', runtime: 'env', re_url: requireEngine(ep.re, 'RE'), pe_url: requireEngine(ep.pe, 'PE') }];

  test('Visualizer Backend /health', async ({ request }) => {
    const resp = await request.get(`${requireService(ep.managerBackend, 'Manager backend')}/health`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
  });

  test('localAIStack API /health', async ({ request }) => {
    const resp = await request.get(`${requireService(ep.localai, 'localAIStack API')}/health`);
    expect(resp.ok()).toBeTruthy();
  });

  test('Qdrant /collections', async ({ request }) => {
    const resp = await request.get(`${requireService(ep.qdrant, 'Qdrant')}/collections`);
    expect(resp.ok()).toBeTruthy();
  });

  test('RE instances — all /api/health pass', async ({ request }) => {
    for (const inst of engines()) {
      const resp = await request.get(`${inst.re_url}/api/health`, { ignoreHTTPSErrors: true });
      expect(resp.ok(), `RE instance '${inst.id}' health check failed`).toBeTruthy();
    }
  });

  test('PE instances — all /api/health pass', async ({ request }) => {
    for (const inst of engines()) {
      if (!inst.pe_url) continue;
      const resp = await request.get(`${inst.pe_url}/api/health`, { ignoreHTTPSErrors: true });
      expect(resp.ok(), `PE instance '${inst.id}' health check failed`).toBeTruthy();
    }
  });

  test('RE /api/machines returns array', async ({ request }) => {
    const resp = await request.get(`${engines()[0].re_url}/api/machines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(Array.isArray(body.machines ?? body)).toBeTruthy();
  });

  test('PE /api/sources returns array', async ({ request }) => {
    const resp = await request.get(`${requireEngine(engines()[0].pe_url, 'PE')}/api/sources`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(Array.isArray(body.sources ?? body)).toBeTruthy();
  });
});
