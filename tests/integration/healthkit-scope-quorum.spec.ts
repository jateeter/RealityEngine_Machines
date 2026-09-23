import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';

/**
 * Integration: HealthKit scope and resync agree 3-of-3 — localHealthkitBridge
 * docs/INGEST_CONTRACT.md "Scope and resync", held to RealityEngine_CI
 * docs/QUORUM_CONTRACT.md. No runtime is the reference.
 *
 * Safe against a live universe. Scope is per bridge and persists, so this uses
 * a bridgeId of its own (the real iOS bridge's scope is never touched) and a
 * HealthKit type no mapping resolves (no real sensor value is overwritten, and
 * the `remove` it sends has no sources to take out).
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const NATIVES = ['cpp', 'lsp', 'scala'] as const;
type Runtime = typeof NATIVES[number];
interface Instance { runtime: string; pe_url: string; status: string }

const TOKEN = process.env.HEALTHKIT_BRIDGE_TOKEN ?? '';
const PROBE = 'HKQuantityTypeIdentifierScopeQuorumProbe';
const OTHER = 'HKQuantityTypeIdentifierScopeQuorumOther';

async function natives(request: APIRequestContext): Promise<Map<Runtime, Instance>> {
  const out = new Map<Runtime, Instance>();
  if (!REGISTRY_URL) return out;
  const r = await request.get(REGISTRY_URL);
  if (!r.ok()) return out;
  for (const i of ((await r.json()) as { instances?: Instance[] }).instances ?? []) {
    if (i.status === 'running' && (NATIVES as readonly string[]).includes(i.runtime) && !out.has(i.runtime as Runtime)) {
      out.set(i.runtime as Runtime, i);
    }
  }
  return out;
}

test('HealthKit scope and resync: every step agrees 3-of-3', async ({ request }) => {
  test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
  const engines = await natives(request);
  const missing = NATIVES.filter(rt => !engines.has(rt));
  expect(missing, `3-of-3 needs all three native runtimes running; missing: ${missing.join(', ')}`).toEqual([]);

  const headers = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : undefined;
  const sigs = new Map<Runtime, string>();
  for (const rt of NATIVES) {
    const pe = engines.get(rt)!.pe_url;
    const bridgeId = `scope-quorum-${rt}-${Date.now()}`;
    const post = async (path: string, data: Record<string, unknown>) => {
      const r = await request.post(`${pe}${path}`, { data: { bridgeId, ...data }, headers });
      return { status: r.status(), body: await r.json() as Record<string, any> };
    };
    const ingest = (extra: Record<string, unknown> = {}) =>
      post('/api/integrations/healthkit/ingest', { samples: [{ type: PROBE, unit: '1', values: [0.5] }], ...extra });
    const scopeOf = async () => {
      const s = (await (await request.get(`${pe}/api/integrations/healthkit/status`)).json()) as Record<string, any>;
      return s.scope;
    };
    const steps: Record<string, unknown> = {};
    const openIngest = await ingest();
    steps.open = [openIngest.status, (openIngest.body.unmapped ?? []).map((u: any) => u.reason === 'not-in-scope' || u.reason === 'locked')];
    const add = await post('/api/integrations/healthkit/scope', { action: 'add', types: [PROBE], source: 'pim' });
    steps.add = [add.status, Object.keys(add.body).sort(), add.body.generation, add.body.applied];
    steps.refusedOther = (await post('/api/integrations/healthkit/ingest', { samples: [{ type: OTHER, unit: '1', values: [0.5] }] })).body.unmapped?.map((u: any) => u.reason);
    const resync = await post('/api/integrations/healthkit/resync', { requestedBy: 'localAIStack' });
    steps.resync = [resync.status, resync.body.success, resync.body.request?.types, resync.body.refused, Object.keys(resync.body.request ?? {}).sort()];
    const fulfil = await ingest({ resyncId: resync.body.request?.id });
    steps.fulfil = [fulfil.body.resyncId === resync.body.request?.id];
    const afterFulfil = await scopeOf();
    steps.fulfilState = (afterFulfil?.resyncRequests ?? []).map((r: any) => r.state);
    const lock = await post('/api/integrations/healthkit/scope', { action: 'lock', types: [PROBE] });
    steps.lock = [lock.status, lock.body.generation, lock.body.applied];
    steps.lockedIngest = (await ingest()).body.unmapped?.map((u: any) => u.reason);
    const lockedResync = await post('/api/integrations/healthkit/resync', { types: [PROBE], requestedBy: 'localAIStack' });
    steps.lockedResync = [lockedResync.status, lockedResync.body.success, lockedResync.body.refused];
    const remove = await post('/api/integrations/healthkit/scope', { action: 'remove', types: [PROBE] });
    steps.remove = [remove.status, remove.body.generation, remove.body.applied];
    const final = await scopeOf();
    steps.status = { keys: Object.keys(final ?? {}).sort(), declared: final?.declared, generation: final?.generation,
      types: Object.fromEntries(Object.entries(final?.types ?? {}).map(([k, v]: [string, any]) => [k, v.state])) };
    steps.badAction = (await post('/api/integrations/healthkit/scope', { action: 'resync', types: [PROBE] })).status;
    steps.noRequester = (await post('/api/integrations/healthkit/resync', {})).status;
    // Conformance before comparison: three runtimes that all lack the surface
    // would otherwise "agree" on three identical 404s.
    expect(add.status, `${rt}: POST /api/integrations/healthkit/scope`).toBe(200);
    expect(resync.status, `${rt}: POST /api/integrations/healthkit/resync`).toBe(202);
    expect(final, `${rt}: /status carries no scope`).toBeTruthy();
    sigs.set(rt, JSON.stringify(steps));
  }
  const report = [...sigs].map(([rt, s]) => `  ${rt.padEnd(5)} ${s}`).join('\n');
  expect(new Set(sigs.values()).size, `HealthKit scope: disagreement (3-of-3, no reference member)\n${report}`).toBe(1);
});
