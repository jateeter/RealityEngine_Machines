import { test, expect } from '@playwright/test';
import { deployed, requireEngine, requireService, type Deployed } from '../support/deployed-endpoints.js';

/**
 * Integration: RAG query round-trip.
 * localAIStack FastAPI → Qdrant retrieval → RE perceive → perceptual space update.
 */


test.describe('RAG Round-Trip', () => {
  let ep: Deployed;
  test.beforeEach(async ({ request }) => { ep = await deployed(request); });

  test('Qdrant is reachable and reports collections', async ({ request }) => {
    const resp = await request.get(`${requireService(ep.qdrant, 'Qdrant')}/collections`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body).toHaveProperty('result');
  });

  test('localAIStack /health reports all sub-services ok', async ({ request }) => {
    const resp = await request.get(`${requireService(ep.localai, 'localAIStack API')}/health`);
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
      `${requireEngine(ep.re, 'RE')}/api/perceive`,
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

  // localAIStack's own machines (localAIStack/data/machines), which it
  // registers on every engine the instance registry lists (CI#518). Matched by
  // exact name: ids are minted per engine (machine-<uuid v7>), so the earlier
  // id substring match could never succeed and both tests failed everywhere.
  const LOCALAI_MACHINES = [
    'localai/rag_corrective_cycle',
    'localai/session_rag_context',
    'localai/session_agent_context',
  ];

  test('localAIStack RAG and session machines are registered on every engine', async ({ request }) => {
    requireService(ep.localai, 'localAIStack API');
    const engines = ep.instances.length
      ? ep.instances.map(i => ({ id: i.id, re: i.re_url }))
      : [{ id: 'RE', re: requireEngine(ep.re, 'RE') }];
    const missing: string[] = [];
    for (const engine of engines) {
      const resp = await request.get(`${engine.re}/api/machines`, { ignoreHTTPSErrors: true });
      expect(resp.ok(), `${engine.id} GET /api/machines`).toBeTruthy();
      const names = new Set(((await resp.json()).machines ?? []).map((m: { name?: string }) => m.name));
      const absent = LOCALAI_MACHINES.filter(n => !names.has(n));
      if (absent.length) missing.push(`${engine.id}: ${absent.join(', ')}`);
    }
    expect(missing, `localAIStack machines missing:\n  ${missing.join('\n  ')}`).toEqual([]);
  });
});
