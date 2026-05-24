import { test, expect } from '@playwright/test';

/**
 * Smoke tests — lightweight HTTP-only checks, no browser.
 * Runs first in CI to fast-fail before heavier suites.
 *
 * In multi-engine mode (RE_REGISTRY_URL set), each registered instance is
 * verified independently.  Falls back to single-instance env vars when not set.
 */

const RE_URL  = process.env.RE_BASE_URL   ?? 'https://localhost:3000';
const VIZ_URL = process.env.VIZ_BASE_URL  ?? 'https://localhost:3001';
const PE_URL  = process.env.PE_BASE_URL   ?? 'https://localhost:3004';
const LAS_URL = process.env.LAS_BASE_URL  ?? 'http://localhost:4000';
const QD_URL  = process.env.QD_BASE_URL   ?? 'http://localhost:4333';
const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';

interface EngineInstance { id: string; re_url: string; pe_url: string; }

async function getInstances(request: Parameters<Parameters<typeof test>[1]>[0]['request']): Promise<EngineInstance[]> {
  if (!REGISTRY_URL) return [];
  try {
    const resp = await request.get(REGISTRY_URL);
    if (!resp.ok()) return [];
    const body = await resp.json() as { instances?: EngineInstance[] };
    return body.instances ?? [];
  } catch { return []; }
}

test.describe('Service Smoke Tests', () => {
  test('Visualizer Backend /health', async ({ request }) => {
    const resp = await request.get(`${VIZ_URL}/health`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
  });

  test('localAIStack API /health', async ({ request }) => {
    const resp = await request.get(`${LAS_URL}/health`);
    expect(resp.ok()).toBeTruthy();
  });

  test('Qdrant /collections', async ({ request }) => {
    const resp = await request.get(`${QD_URL}/collections`);
    expect(resp.ok()).toBeTruthy();
  });

  test('RE instances — all /api/health pass', async ({ request }) => {
    const instances = await getInstances(request);
    if (instances.length > 0) {
      for (const inst of instances) {
        const resp = await request.get(`${inst.re_url}/api/health`);
        expect(resp.ok(), `RE instance '${inst.id}' health check failed`).toBeTruthy();
      }
    } else {
      // Single-instance fallback
      const resp = await request.get(`${RE_URL}/api/health`, { ignoreHTTPSErrors: true });
      expect(resp.ok()).toBeTruthy();
    }
  });

  test('PE instances — all /api/health pass', async ({ request }) => {
    const instances = await getInstances(request);
    if (instances.length > 0) {
      for (const inst of instances) {
        if (!inst.pe_url) continue;
        const resp = await request.get(`${inst.pe_url}/api/health`);
        expect(resp.ok(), `PE instance '${inst.id}' health check failed`).toBeTruthy();
      }
    } else {
      const resp = await request.get(`${PE_URL}/api/health`, { ignoreHTTPSErrors: true });
      expect(resp.ok()).toBeTruthy();
    }
  });

  test('RE /api/machines returns array', async ({ request }) => {
    const instances = await getInstances(request);
    const checkUrl = instances.length > 0 ? instances[0].re_url : RE_URL;
    const resp = await request.get(`${checkUrl}/api/machines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(Array.isArray(body.machines ?? body)).toBeTruthy();
  });

  test('PE /api/sources returns array', async ({ request }) => {
    const instances = await getInstances(request);
    const checkUrl = instances.length > 0 ? (instances[0].pe_url || PE_URL) : PE_URL;
    const resp = await request.get(`${checkUrl}/api/sources`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(Array.isArray(body.sources ?? body)).toBeTruthy();
  });
});
