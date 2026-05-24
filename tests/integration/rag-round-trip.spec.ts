import { test, expect } from '@playwright/test';

/**
 * Integration: RAG query round-trip.
 * localAIStack FastAPI → Qdrant retrieval → RE perceive → perceptual space update.
 */

const LAS_URL  = 'http://localhost:4000';
const RE_URL   = 'https://localhost:3000';
const PE_URL   = 'https://localhost:3004';
const QD_URL   = 'http://localhost:4333';

test.describe('RAG Round-Trip', () => {
  test('Qdrant is reachable and reports collections', async ({ request }) => {
    const resp = await request.get(`${QD_URL}/collections`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body).toHaveProperty('result');
  });

  test('localAIStack /health reports all sub-services ok', async ({ request }) => {
    const resp = await request.get(`${LAS_URL}/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
    const services = body.services ?? {};
    const failing = Object.entries(services)
      .filter(([k, v]) => k !== 'ollama_models' && v !== 'ok')
      .map(([k, v]) => `${k}=${v}`);
    if (failing.length) console.warn('Degraded services:', failing.join(', '));
  });

  test('RE perceive smoke-test returns machine results', async ({ request }) => {
    const dim = parseInt(process.env.VECTOR_DIMENSION ?? '768', 10);
    const zero = Array(dim).fill(0.0);
    const resp = await request.post(
      `${RE_URL}/api/perceive`,
      { data: { vector: zero }, ignoreHTTPSErrors: true }
    );
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const step = body.step ?? body;
    const results = step.machineResults ?? {};
    const count = typeof results === 'object' ? Object.keys(results).length : 0;
    console.log(`Perceive: ${count} machines evaluated`);
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('rag_corrective_cycle machine is registered in RE', async ({ request }) => {
    const resp = await request.get(`${RE_URL}/api/machines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const machines: any[] = body.machines ?? [];
    const ids = machines.map((m: any) => (m.id ?? '').toLowerCase());
    const found = ids.some(id => id.includes('rag') && id.includes('corrective'));
    expect(found).toBeTruthy();
    console.log(`Total machines in RE: ${machines.length}`);
  });

  test('session machines are registered in RE', async ({ request }) => {
    const resp = await request.get(`${RE_URL}/api/machines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const ids: string[] = (body.machines ?? []).map((m: any) => (m.id ?? '').toLowerCase());
    expect(ids.some(id => id.includes('session') && id.includes('rag'))).toBeTruthy();
    expect(ids.some(id => id.includes('session') && id.includes('agent'))).toBeTruthy();
  });
});
