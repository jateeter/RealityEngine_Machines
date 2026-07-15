import { test, expect } from '@playwright/test';

/**
 * Integration: HealthKit ingest contract parity.
 *
 * Every registered PE must expose the canonical HealthKit bridge surface:
 *   GET  /api/integrations/healthkit/status
 *   POST /api/integrations/healthkit/ingest
 *
 * The ingest contract (see localHealthkitBridge/docs/INGEST_CONTRACT.md):
 *   - batch body: { bridgeId, bridgeToken?, samples: [{ type, sourceName?,
 *     unit?, values[] | value, metadata? }] }
 *   - auth when HEALTHKIT_BRIDGE_TOKEN is configured: body bridgeToken/token
 *     OR an equivalent "Authorization: Bearer <token>" header
 *   - response: { success, bridgeId, resolved[], unmapped[] } with HTTP
 *     200 (all resolved) / 207 (partial) / 400 (all unmapped)
 *
 * Resolution depends on the engine's configured source mappings, so this
 * suite asserts cross-engine parity of status codes and resolution counts
 * rather than absolute resolution success.
 *
 * Auth cases run only when HEALTHKIT_BRIDGE_TOKEN is exported to the test
 * process AND the engines were started with the same value.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const PE_URL = process.env.PE_BASE_URL ?? '';
const BRIDGE_TOKEN = process.env.HEALTHKIT_BRIDGE_TOKEN ?? '';

const INGEST_PATH = '/api/integrations/healthkit/ingest';
const STATUS_PATH = '/api/integrations/healthkit/status';

interface EngineInstance {
  id: string;
  runtime: string;
  pe_url: string;
  status: string;
}

async function fetchEngines(request: Parameters<Parameters<typeof test>[1]>[0]['request']): Promise<EngineInstance[]> {
  if (REGISTRY_URL) {
    try {
      const resp = await request.get(REGISTRY_URL);
      if (resp.ok()) {
        const body = await resp.json() as { instances?: EngineInstance[] };
        const running = (body.instances ?? []).filter(i => i.status === 'running' && i.pe_url);
        if (running.length > 0) return running;
      }
    } catch { /* fall through to PE_BASE_URL */ }
  }
  if (PE_URL) return [{ id: 'single', runtime: 'unknown', pe_url: PE_URL, status: 'running' }];
  return [];
}

function canonicalSamples() {
  return [
    {
      type: 'HKCorrelationTypeIdentifierBloodPressure',
      unit: 'mm[Hg]',
      values: [0.72, 0.48, 0.24, 0.99],
      metadata: { standard: 'SpeziHealthKit', fhirCode: '85354-9' },
    },
    {
      type: 'HKWorkoutTypeIdentifierWorkout',
      unit: 'normalized',
      values: [0.65, 0.58, 0.42, 0.97],
      metadata: { standard: 'SpeziHealthKit', fhirCode: '55411-3' },
    },
    {
      type: 'HKCategoryTypeIdentifierSleepAnalysis',
      unit: 'normalized',
      values: [0.82, 0.12, 0.18, 0.96],
      metadata: { standard: 'SpeziHealthKit', fhirCode: '93832-4' },
    },
  ];
}

function batchBody(extra: Record<string, unknown> = {}) {
  return { bridgeId: 'healthkit-contract-test', samples: canonicalSamples(), ...extra };
}

test.describe('HealthKit Ingest Contract Parity', () => {
  test.skip(() => !REGISTRY_URL && !PE_URL, 'Neither RE_REGISTRY_URL nor PE_BASE_URL set — skipping live contract tests');

  test('every PE advertises the canonical status + ingest endpoints', async ({ request }) => {
    const engines = await fetchEngines(request);
    expect(engines.length, 'no running PE instances found').toBeGreaterThan(0);

    for (const engine of engines) {
      const resp = await request.get(`${engine.pe_url}${STATUS_PATH}`);
      expect(resp.status(), `${engine.id} ${STATUS_PATH}`).toBe(200);
      const body = await resp.json();
      expect(body.ingestEndpoint, `${engine.id} ingestEndpoint`).toBe(INGEST_PATH);
      expect(body.statusEndpoint, `${engine.id} statusEndpoint`).toBe(STATUS_PATH);
      expect(body, `${engine.id} tokenConfigured`).toHaveProperty('tokenConfigured');
      // When a token is configured the engine must advertise both auth paths.
      if (body.tokenConfigured === true && body.contract?.auth) {
        expect(body.contract.auth, `${engine.id} contract.auth`).toBe('bridgeToken|bearer');
      }
    }
  });

  test('batch ingest returns the same status and resolution counts on every engine', async ({ request }) => {
    const engines = await fetchEngines(request);
    expect(engines.length, 'no running PE instances found').toBeGreaterThan(0);

    const results: Array<{ id: string; status: number; resolved: number; unmapped: number; success: boolean }> = [];
    for (const engine of engines) {
      const payload = BRIDGE_TOKEN ? batchBody({ bridgeToken: BRIDGE_TOKEN }) : batchBody();
      const resp = await request.post(`${engine.pe_url}${INGEST_PATH}`, { data: payload });
      expect([200, 207, 400], `${engine.id} ingest status ${resp.status()}`).toContain(resp.status());
      const body = await resp.json();
      expect(Array.isArray(body.resolved), `${engine.id} resolved[]`).toBe(true);
      expect(Array.isArray(body.unmapped), `${engine.id} unmapped[]`).toBe(true);
      expect(typeof body.success, `${engine.id} success`).toBe('boolean');
      results.push({
        id: engine.id,
        status: resp.status(),
        resolved: body.resolved.length,
        unmapped: body.unmapped.length,
        success: body.success,
      });
    }

    const [first, ...rest] = results;
    for (const r of rest) {
      expect(r.status, `${r.id} status vs ${first.id}`).toBe(first.status);
      expect(r.resolved, `${r.id} resolved count vs ${first.id}`).toBe(first.resolved);
      expect(r.unmapped, `${r.id} unmapped count vs ${first.id}`).toBe(first.unmapped);
      expect(r.success, `${r.id} success vs ${first.id}`).toBe(first.success);
    }
  });

  test.describe('token auth (requires HEALTHKIT_BRIDGE_TOKEN)', () => {
    test.skip(() => !BRIDGE_TOKEN, 'HEALTHKIT_BRIDGE_TOKEN not set — skipping auth parity tests');

    test('wrong body token is rejected with 401 on every engine', async ({ request }) => {
      const engines = await fetchEngines(request);
      for (const engine of engines) {
        const resp = await request.post(`${engine.pe_url}${INGEST_PATH}`, {
          data: batchBody({ bridgeToken: 'definitely-wrong-token' }),
        });
        expect(resp.status(), `${engine.id} wrong token`).toBe(401);
      }
    });

    test('body bridgeToken is accepted on every engine', async ({ request }) => {
      const engines = await fetchEngines(request);
      for (const engine of engines) {
        const resp = await request.post(`${engine.pe_url}${INGEST_PATH}`, {
          data: batchBody({ bridgeToken: BRIDGE_TOKEN }),
        });
        expect(resp.status(), `${engine.id} body token`).not.toBe(401);
      }
    });

    test('Authorization: Bearer is accepted as an alternative on every engine', async ({ request }) => {
      const engines = await fetchEngines(request);
      for (const engine of engines) {
        const resp = await request.post(`${engine.pe_url}${INGEST_PATH}`, {
          data: batchBody(),
          headers: { Authorization: `Bearer ${BRIDGE_TOKEN}` },
        });
        expect(resp.status(), `${engine.id} bearer token`).not.toBe(401);
      }
    });

    test('wrong Bearer token does not bypass a missing body token', async ({ request }) => {
      const engines = await fetchEngines(request);
      for (const engine of engines) {
        const resp = await request.post(`${engine.pe_url}${INGEST_PATH}`, {
          data: batchBody(),
          headers: { Authorization: 'Bearer definitely-wrong-token' },
        });
        expect(resp.status(), `${engine.id} wrong bearer`).toBe(401);
      }
    });
  });
});
