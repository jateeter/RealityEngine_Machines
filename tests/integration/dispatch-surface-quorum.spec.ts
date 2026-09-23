import { test, expect } from '@playwright/test';
import type { APIRequestContext, TestInfo } from '@playwright/test';

/**
 * Integration: the dispatch surface agrees 3-of-3 — RealityEngine_CI
 * SURFACE_SPEC.md "Dispatch surface shapes" (INTEGRATION_ROADMAP.md §6 Q5),
 * held to docs/QUORUM_CONTRACT.md.
 *
 * No runtime is the reference. Each signature is compared across C++, LSP and
 * Scala; any split is a disagreement, reported with what each runtime emitted.
 * A signature a runtime has declared it cannot take part in (participation
 * "unsupported") is reported as not evaluable, never as agreement.
 *
 * The record-level stimulus is the OpenClaw dispatch seed used by
 * RealityEngine_CI/scripts/test-openclaw-integration.sh: a one-shot test source
 * over [4210:4214] carrying [0,1,0,1], pushed once. Only records that push
 * created are compared.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const NATIVES = ['cpp', 'lsp', 'scala'] as const;
const PARTICIPATION = ['active', 'not-configured', 'not-active', 'unsupported', 'unavailable'];

const STATUS_KEYS = [
  'participation', 'enabled', 'mode', 'graphqlEndpoint', 'records', 'envelopesCreated',
  'droppedNoGovernance', 'droppedNoDispatch', 'droppedCatalogCold', 'replaysCreated', 'dispatchErrors',
  'machineCatalogCold', 'machineCatalogRefreshedAt', 'machineCatalogSize',
].sort();
const LEDGER_KEYS = ['enabled', 'mode', 'records'];
const RECORD_KEYS = [
  'id', 'envelopeId', 'correlationId', 'status', 'mode', 'target', 'machineId', 'sequenceIds',
  'ragStatusCode', 'processStatus', 'attempts', 'createdAt', 'updatedAt', 'providerReceipt',
  'envelope', 'error', 'semantics', 'replayOf',
].sort();

interface Instance { id: string; runtime: string; pe_url: string; status: string }
type Runtime = typeof NATIVES[number];

async function natives(request: APIRequestContext): Promise<Map<Runtime, Instance>> {
  const out = new Map<Runtime, Instance>();
  if (!REGISTRY_URL) return out;
  const resp = await request.get(REGISTRY_URL);
  if (!resp.ok()) return out;
  const body = await resp.json() as { instances?: Instance[] };
  for (const i of body.instances ?? []) {
    if (i.status === 'running' && (NATIVES as readonly string[]).includes(i.runtime) && !out.has(i.runtime as Runtime)) {
      out.set(i.runtime as Runtime, i);
    }
  }
  return out;
}

/** 3-of-3: every runtime's signature identical, or a disagreement naming each. */
function expectUnanimous(label: string, signatures: Map<Runtime, string>) {
  const distinct = new Set(signatures.values());
  const report = [...signatures].map(([rt, sig]) => `  ${rt.padEnd(5)} ${sig}`).join('\n');
  expect(distinct.size, `${label}: disagreement (3-of-3, no reference member)\n${report}`).toBe(1);
}

function notEvaluable(info: TestInfo, label: string, why: string) {
  info.annotations.push({ type: 'not evaluable', description: `${label}: ${why}` });
}

async function statusOf(request: APIRequestContext, i: Instance) {
  const r = await request.get(`${i.pe_url}/api/triggers/status`);
  expect(r.ok(), `${i.runtime} GET /api/triggers/status`).toBe(true);
  return await r.json() as Record<string, unknown>;
}

async function ledgerOf(request: APIRequestContext, i: Instance) {
  const r = await request.get(`${i.pe_url}/api/dispatch/ledger`);
  expect(r.ok(), `${i.runtime} GET /api/dispatch/ledger`).toBe(true);
  return await r.json() as { records?: Array<Record<string, unknown>> } & Record<string, unknown>;
}

test.describe('dispatch surface quorum', () => {
  let engines: Map<Runtime, Instance>;

  test.beforeEach(async ({ request }) => {
    engines = await natives(request);
    test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
    const missing = NATIVES.filter(rt => !engines.has(rt));
    expect(missing, `3-of-3 needs all three native runtimes running; missing: ${missing.join(', ')}`).toEqual([]);
  });

  test('/api/triggers/status carries the agreed keys and a declared participation', async ({ request }) => {
    const keys = new Map<Runtime, string>();
    for (const rt of NATIVES) {
      const s = await statusOf(request, engines.get(rt)!);
      keys.set(rt, JSON.stringify(Object.keys(s).sort()));
      expect(PARTICIPATION, `${rt} participation "${s.participation}" is outside the closed set`).toContain(s.participation);
      expect(s.participation, `${rt} declared unavailable: a finding`).not.toBe('unavailable');
    }
    expectUnanimous('triggers/status key set', keys);
    expect(JSON.parse([...keys.values()][0]!)).toEqual(STATUS_KEYS);
  });

  test('/api/dispatch/ledger wrapper agrees', async ({ request }) => {
    const keys = new Map<Runtime, string>();
    for (const rt of NATIVES) keys.set(rt, JSON.stringify(Object.keys(await ledgerOf(request, engines.get(rt)!)).sort()));
    expectUnanimous('dispatch/ledger key set', keys);
    expect(JSON.parse([...keys.values()][0]!)).toEqual(LEDGER_KEYS);
  });

  test('unknown record: GET and PATCH answer the same 404', async ({ request }) => {
    const sigs = new Map<Runtime, string>();
    for (const rt of NATIVES) {
      const pe = engines.get(rt)!.pe_url;
      const g = await request.get(`${pe}/api/dispatch/records/quorum-no-such-record`);
      const p = await request.patch(`${pe}/api/dispatch/records/quorum-no-such-record`, { data: { status: 'x' } });
      sigs.set(rt, JSON.stringify([g.status(), await g.json(), p.status(), await p.json()]));
    }
    expectUnanimous('unknown-record GET/PATCH', sigs);
  });

  test('seeded dispatch: record key set, semantics and PATCH agree', async ({ request }, info) => {
    const active: Runtime[] = [];
    const created = new Map<Runtime, Array<Record<string, unknown>>>();
    for (const rt of NATIVES) {
      const inst = engines.get(rt)!;
      const participation = (await statusOf(request, inst)).participation;
      // Only a declared state excuses a runtime. A missing or unknown one is
      // silence, and silence is a finding, not agreement (QUORUM_CONTRACT §2).
      expect(PARTICIPATION, `${rt} participation "${participation}" is not a declared state`).toContain(participation);
      if (participation !== 'active') {
        notEvaluable(info, 'record signatures', `${rt} declares participation "${participation}"${rt === 'scala' ? ' (RealityEngine_Scala#149)' : ''}`);
        continue;
      }
      active.push(rt);
      const before = new Set((await ledgerOf(request, inst)).records?.map(r => r.id) ?? []);
      const sourceId = `dispatch-quorum-${rt}-${Date.now()}`;
      const seeded = await request.post(`${inst.pe_url}/api/sources`, {
        data: { id: sourceId, type: 'test', name: 'Dispatch quorum seed', active: true,
                region: { offset: 4210, length: 4 }, inputs: [[0, 1, 0, 1]], loop: false },
      });
      expect(seeded.ok(), `${rt}: seed source registration answered ${seeded.status()}`).toBe(true);
      try {
        await request.post(`${inst.pe_url}/api/push`, { data: { compact: true } });
      } finally {
        await request.delete(`${inst.pe_url}/api/sources/${sourceId}`);
      }
      const fresh = ((await ledgerOf(request, inst)).records ?? []).filter(r => !before.has(r.id));
      expect(fresh.length, `${rt}: the seed produced no dispatch records`).toBeGreaterThan(0);
      created.set(rt, fresh);
    }

    // Conformance holds for every runtime that takes part, quorum or not.
    for (const rt of active) {
      for (const r of created.get(rt)!) {
        expect(Object.keys(r).sort(), `${rt} record ${r.id} key set`).toEqual(RECORD_KEYS);
      }
    }

    if (active.length < NATIVES.length) return; // not evaluable; annotated above

    // What each runtime derived for the same determination. Compared per
    // (machineId, sequenceIds) and only for pairs all three produced: which
    // sequences a push fires depends on each engine's history, and this test
    // does not equalise state first. Comparing whole record sets assumed it
    // had, and reported three histories as a disagreement (the defect class of
    // RealityEngine_CI#283/#304/#307).
    const byKey = new Map<Runtime, Map<string, string>>();
    for (const rt of NATIVES) {
      const m = new Map<string, string>();
      for (const r of created.get(rt)!) {
        const key = JSON.stringify([r.machineId, r.sequenceIds]);
        m.set(key, JSON.stringify({
          target: r.target, status: r.status, mode: r.mode, ragStatusCode: r.ragStatusCode,
          processStatus: r.processStatus, semantics: r.semantics, replayOf: r.replayOf,
          error: r.error, providerReceipt: r.providerReceipt,
        }));
      }
      byKey.set(rt, m);
    }
    const common = [...byKey.get('cpp')!.keys()].filter(k => NATIVES.every(rt => byKey.get(rt)!.has(k)));
    if (common.length === 0) {
      notEvaluable(info, 'seeded determinations', 'no (machineId, sequenceIds) was produced by all three runtimes on this push');
    }
    for (const key of common) {
      expectUnanimous(`seeded dispatch record ${key}`, new Map(NATIVES.map(rt => [rt, byKey.get(rt)!.get(key)!])));
    }

    // PATCH semantics: the same body produces the same delivery metadata.
    const patched = new Map<Runtime, string>();
    for (const rt of NATIVES) {
      const inst = engines.get(rt)!;
      const id = created.get(rt)![0]!.id as string;
      const resp = await request.patch(`${inst.pe_url}/api/dispatch/records/${id}`, {
        data: { status: 'delivered', provider: 'quorum', externalRunId: 'run-q', error: 'e',
                incrementAttempts: true, envelope: { forged: true } },
      });
      const body = await resp.json() as { success?: boolean; record?: Record<string, unknown> };
      const r = body.record ?? {};
      patched.set(rt, JSON.stringify({
        http: resp.status(), keys: Object.keys(body).sort(), success: body.success,
        status: r.status, error: r.error, attempts: r.attempts, providerReceipt: r.providerReceipt,
        envelopeUntouched: !(r.envelope as Record<string, unknown> | undefined)?.forged,
      }));
    }
    expectUnanimous('PATCH /api/dispatch/records/:id', patched);
  });

  test('replay: POST /api/dispatch/records/:id/replay agrees', async ({ request }, info) => {
    // SURFACE_SPEC.md "Dispatch replay" (INTEGRATION_ROADMAP §6 Q6). Compared as
    // relations to the replayed record -- same ids or re-minted, delivery state
    // reset, semantics carried -- so each runtime's own history does not matter.
    const sigs = new Map<Runtime, string>();
    for (const rt of NATIVES) {
      const inst = engines.get(rt)!;
      const records = (await ledgerOf(request, inst)).records ?? [];
      const original = records.find(r => r.mode !== 'replay');
      if (!original) {
        notEvaluable(info, 'replay', `${rt} holds no dispatch record to replay`);
        return;
      }
      const post = async (id: string, data: unknown) => {
        const r = await request.post(`${inst.pe_url}/api/dispatch/records/${encodeURIComponent(id)}/replay`, { data });
        return { status: r.status(), body: await r.json() as Record<string, any> };
      };
      const before = await statusOf(request, inst);
      const plain = await post(original.id as string, {});
      const fresh = await post(original.id as string, { freshIds: true });
      const unknown = await post('quorum-no-such-record', {});
      const after = await statusOf(request, inst);
      const a = plain.body.record ?? {}, b = fresh.body.record ?? {};
      sigs.set(rt, JSON.stringify({
        plain: {
          http: plain.status, keys: Object.keys(plain.body).sort(), recordKeys: Object.keys(a).sort(),
          mode: a.mode, status: a.status, attempts: a.attempts, providerReceipt: a.providerReceipt, error: a.error,
          replayOf: a.replayOf === original.id, newId: a.id !== original.id,
          keptIds: a.envelopeId === original.envelopeId && a.correlationId === original.correlationId,
          carried: ['target', 'machineId', 'sequenceIds', 'ragStatusCode', 'processStatus', 'semantics']
            .every(k => JSON.stringify(a[k]) === JSON.stringify((original as any)[k])),
          freshIds: plain.body.freshIds,
        },
        fresh: {
          http: fresh.status, freshIds: fresh.body.freshIds,
          reminted: b.envelopeId !== original.envelopeId && b.correlationId !== original.correlationId,
          envelopeCarriesNewIds: b.envelope?.envelopeId === b.envelopeId && b.envelope?.correlationId === b.correlationId,
        },
        unknown,
        counters: {
          envelopesCreated: Number(after.envelopesCreated) - Number(before.envelopesCreated),
          replaysCreated: Number(after.replaysCreated) - Number(before.replaysCreated),
        },
      }));
    }
    expectUnanimous('dispatch replay', sigs);
  });
});
