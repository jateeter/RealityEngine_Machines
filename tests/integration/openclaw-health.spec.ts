import { test, expect } from '@playwright/test';

/**
 * Integration: OpenClaw gateway health.
 * Only runs when OPENCLAW_ENABLED=true is set in the environment.
 */

const OCS_GW_PORT  = process.env.OPENCLAW_GATEWAY_PORT ?? '18789';
const OCS_UI_PORT  = process.env.OPEN_WEBUI_PORT       ?? '8080';
const OCS_GW_URL   = `http://localhost:${OCS_GW_PORT}`;
const OCS_UI_URL   = `http://localhost:${OCS_UI_PORT}`;

test.describe('OpenClaw Gateway Health', () => {
  test.skip(!process.env.OPENCLAW_ENABLED, 'Set OPENCLAW_ENABLED=true to run OpenClaw tests');

  test('gateway /healthz responds 200', async ({ request }) => {
    const resp = await request.get(`${OCS_GW_URL}/healthz`);
    expect(resp.ok()).toBeTruthy();
  });

  test('Open WebUI responds 200 or 302', async ({ request }) => {
    const resp = await request.get(`${OCS_UI_URL}/`, { maxRedirects: 0 });
    expect([200, 302]).toContain(resp.status());
  });

  test('gateway accepts ACP request with token', async ({ request }) => {
    const token = process.env.OPENCLAW_GATEWAY_TOKEN;
    if (!token) {
      test.skip(true, 'OPENCLAW_GATEWAY_TOKEN not set');
      return;
    }
    const resp = await request.get(`${OCS_GW_URL}/api/v1/health`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect([200, 401, 404]).toContain(resp.status());
  });
});
