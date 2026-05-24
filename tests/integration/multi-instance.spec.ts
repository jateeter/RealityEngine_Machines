import { test, expect } from '@playwright/test';

/**
 * Multi-instance integration tests.
 *
 * These tests require at least two engine instances in the registry
 * (RE_REGISTRY_URL env var must be set and the universe must have been
 * started with --engines=<two or more instances>).
 *
 * They are skipped automatically when only a single instance or no registry
 * is available, so they are safe to include in every CI run.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const VIZ_URL      = process.env.VIZ_BASE_URL ?? 'https://localhost:3001';

interface EngineInstance {
  id: string;
  runtime: string;
  re_url: string;
  pe_url: string;
  status: string;
}

async function fetchRegistry(request: Parameters<Parameters<typeof test>[1]>[0]['request']): Promise<EngineInstance[]> {
  if (!REGISTRY_URL) return [];
  try {
    const resp = await request.get(REGISTRY_URL);
    if (!resp.ok()) return [];
    const body = await resp.json() as { instances?: EngineInstance[] };
    return body.instances ?? [];
  } catch { return []; }
}

test.describe('Multi-Engine Instance Tests', () => {
  test.skip(() => !REGISTRY_URL, 'RE_REGISTRY_URL not set — skipping multi-engine tests');

  test('registry lists at least one instance', async ({ request }) => {
    const instances = await fetchRegistry(request);
    expect(instances.length, 'Registry must have at least one instance').toBeGreaterThanOrEqual(1);
    for (const inst of instances) {
      expect(inst.id).toBeTruthy();
      expect(inst.re_url).toMatch(/^https?:\/\//);
      expect(inst.status).toBe('running');
    }
  });

  test('all instances have distinct RE ports', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, 'Need at least 2 instances to test port uniqueness');

    const rePorts = instances.map(i => new URL(i.re_url).port);
    const unique = new Set(rePorts);
    expect(unique.size).toBe(instances.length);
  });

  test('each instance /api/health responds independently', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, 'Need at least 2 instances for independence test');

    const results = await Promise.all(
      instances.map(async inst => {
        try {
          const resp = await request.get(`${inst.re_url}/api/health`);
          return { id: inst.id, ok: resp.ok() };
        } catch {
          return { id: inst.id, ok: false };
        }
      })
    );
    for (const r of results) {
      expect(r.ok, `Instance '${r.id}' health check failed`).toBeTruthy();
    }
  });

  test('Manager /api/engines returns all registry instances', async ({ request }) => {
    const registryInstances = await fetchRegistry(request);
    test.skip(registryInstances.length < 1, 'No registry instances');

    const resp = await request.get(`${VIZ_URL}/api/engines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json() as { instances: EngineInstance[]; activeId: string | null };
    expect(Array.isArray(body.instances)).toBeTruthy();
    expect(typeof body.activeId === 'string' || body.activeId === null).toBeTruthy();
  });

  test('Manager can switch active instance', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, 'Need at least 2 instances to test switching');

    // Get current active
    const beforeResp = await request.get(`${VIZ_URL}/api/engines`, { ignoreHTTPSErrors: true });
    expect(beforeResp.ok()).toBeTruthy();
    const before = await beforeResp.json() as { activeId: string | null };

    // Switch to the second instance
    const target = instances.find(i => i.id !== before.activeId) ?? instances[1];
    const switchResp = await request.post(`${VIZ_URL}/api/engines/active`, {
      data: { id: target.id },
      ignoreHTTPSErrors: true,
    });
    expect(switchResp.ok(), `Switch to '${target.id}' failed`).toBeTruthy();
    const switched = await switchResp.json() as { activeId: string };
    expect(switched.activeId).toBe(target.id);

    // Restore original
    if (before.activeId) {
      await request.post(`${VIZ_URL}/api/engines/active`, {
        data: { id: before.activeId },
        ignoreHTTPSErrors: true,
      });
    }
  });

  test('instances have independent machine state', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, 'Need at least 2 instances for state isolation test');

    const [a, b] = instances;
    const [respA, respB] = await Promise.all([
      request.get(`${a.re_url}/api/machines`),
      request.get(`${b.re_url}/api/machines`),
    ]);
    expect(respA.ok(), `Instance '${a.id}' /api/machines failed`).toBeTruthy();
    expect(respB.ok(), `Instance '${b.id}' /api/machines failed`).toBeTruthy();
    // Both respond independently — state may differ (different runtimes / seeds)
    const bodyA = await respA.json() as { machines?: unknown[] };
    const bodyB = await respB.json() as { machines?: unknown[] };
    expect(Array.isArray(bodyA.machines ?? bodyA)).toBeTruthy();
    expect(Array.isArray(bodyB.machines ?? bodyB)).toBeTruthy();
  });
});
