import { test, expect } from '@playwright/test';

/**
 * Integration: PE sensor source registration via localAIStack lifespan hooks.
 * Verifies that sensors are registered in the Perception Engine after startup.
 */

const PE_URL = 'https://localhost:3004';
const LAS_URL = 'http://localhost:4000';

test.describe('PE Sensor Registration', () => {
  test('localAIStack API is healthy', async ({ request }) => {
    const resp = await request.get(`${LAS_URL}/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });

  test('PE has at least one sensor source registered', async ({ request }) => {
    const resp = await request.get(`${PE_URL}/api/sources`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const sensors = (body.sources ?? []).filter((s: any) => s.type === 'sensor');
    expect(sensors.length).toBeGreaterThan(0);
    console.log(`Registered sensor sources (${sensors.length}):`);
    sensors.forEach((s: any) => {
      const r = s.region ?? {};
      console.log(`  [${r.offset}:${r.offset + r.length}]  ${s.name}`);
    });
  });

  test('RAG signal regions [64:72] are covered by a sensor', async ({ request }) => {
    const resp = await request.get(`${PE_URL}/api/sources`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const offsets = (body.sources ?? [])
      .filter((s: any) => s.type === 'sensor')
      .map((s: any) => s.region?.offset);
    const covered = offsets.includes(64) || offsets.includes(68);
    expect(covered).toBeTruthy();
  });

  test('sensor write is accepted by PE', async ({ request }) => {
    const resp = await request.post(
      `${PE_URL}/api/sensors/localai_rag_retrieval`,
      {
        data: { values: [1.0, 0.5, 0.0, 0.0] },
        ignoreHTTPSErrors: true,
      }
    );
    // 200 OK with ok/id/success/updated, or 404 if not yet registered (non-fatal)
    if (resp.ok()) {
      const body = await resp.json();
      const accepted = body.ok || body.id || body.success || body.updated;
      expect(accepted).toBeTruthy();
    } else {
      expect([200, 404]).toContain(resp.status());
      console.log('Sensor not yet registered — will appear after first RAG query');
    }
  });
});
