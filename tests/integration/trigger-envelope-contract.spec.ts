import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

/**
 * Integration: every Perception Engine's trigger envelopes conform to
 * schemas/ai-trigger-envelope.schema.json — RealityEngine_CI
 * INTEGRATION_ROADMAP.md §6 Q3.
 *
 * Until this existed, the schema described a document no runtime produced:
 * every envelope C++ and LSP emitted failed it, and the only files that passed
 * were hand-written examples. Nothing ran a runtime's output through it, so the
 * two shapes drifted apart while both claimed schemaVersion 1.0.0.
 *
 * The stimulus is the OpenClaw dispatch seed used by
 * RealityEngine_CI/scripts/test-openclaw-integration.sh: a one-shot test source
 * over [4210:4214] carrying [0,1,0,1], pushed once. Against the regression
 * corpus it deterministically fires `OpenClaw Completion E2E` (and
 * `Home Transportation Barrier Monitor`) on every runtime that dispatches.
 * Only envelopes created by this push are checked.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const PE_URL = process.env.PE_BASE_URL ?? '';
const REPO = join(dirname(fileURLToPath(import.meta.url)), '../..');

// Runtimes known not to conform yet, each with the issue that tracks it. Marked
// as an expected failure rather than skipped, so a mark has to come out the
// moment its runtime starts passing. Empty: Scala's came out with #149.
const EXPECTED_FAILURE: Record<string, string> = {};

interface EngineInstance { id: string; runtime: string; pe_url: string; status: string }

async function fetchEngines(request: APIRequestContext): Promise<EngineInstance[]> {
  if (REGISTRY_URL) {
    try {
      const resp = await request.get(REGISTRY_URL);
      if (resp.ok()) {
        const body = await resp.json() as { instances?: EngineInstance[] };
        const running = (body.instances ?? []).filter(i => i.status === 'running');
        if (running.length > 0) return running;
      }
    } catch { /* fall through to PE_BASE_URL */ }
  }
  if (PE_URL) return [{ id: 'single', runtime: 'unknown', pe_url: PE_URL, status: 'running' }];
  return [];
}

function envelopeValidator() {
  const require = createRequire(import.meta.url);
  const Ajv2020 = require('ajv/dist/2020.js').default ?? require('ajv/dist/2020.js');
  const addFormats = require('ajv-formats').default ?? require('ajv-formats');
  const ajv = new Ajv2020({ strict: false, allErrors: true, allowUnionTypes: true });
  addFormats(ajv);
  const dir = join(REPO, 'schemas');
  for (const f of readdirSync(dir).filter(n => n.endsWith('.schema.json'))) {
    ajv.addSchema(JSON.parse(readFileSync(join(dir, f), 'utf8')));
  }
  return ajv.getSchema('https://realityengine.example.org/schemas/ai-trigger-envelope.schema.json');
}

interface LedgerRecord { id: string; envelope?: Record<string, unknown> }

async function ledgerRecords(request: APIRequestContext, peUrl: string): Promise<LedgerRecord[]> {
  const resp = await request.get(`${peUrl}/api/dispatch/ledger`);
  expect(resp.ok(), `GET ${peUrl}/api/dispatch/ledger`).toBe(true);
  const body = await resp.json() as { records?: LedgerRecord[] };
  return body.records ?? [];
}

const SEED_REGION = { offset: 4210, length: 4 };
const SEED_MACHINE = 'OpenClaw Completion E2E';

interface SourceRecord { id?: string; active?: boolean; region?: { offset?: number; length?: number } }

function sourceIdOf(body: unknown): string | undefined {
  const b = body as { id?: unknown; source?: { id?: unknown } } | null;
  const id = b?.source?.id ?? b?.id;
  return typeof id === 'string' && id !== '' ? id : undefined;
}

/** Deactivates every active source overlapping SEED_REGION; returns their ids to restore. */
async function quiesceLane(request: APIRequestContext, peUrl: string): Promise<string[]> {
  const resp = await request.get(`${peUrl}/api/sources`);
  expect(resp.ok(), `GET ${peUrl}/api/sources`).toBe(true);
  const body = await resp.json() as SourceRecord[] | { sources?: SourceRecord[] };
  const sources = Array.isArray(body) ? body : body.sources ?? [];
  const end = SEED_REGION.offset + SEED_REGION.length;
  const ids: string[] = [];
  for (const s of sources) {
    const o = s.region?.offset ?? -1, l = s.region?.length ?? 0;
    if (!s.id || s.active !== true || o >= end || o + l <= SEED_REGION.offset) continue;
    const off = await request.patch(`${peUrl}/api/sources/${encodeURIComponent(s.id)}`, { data: { active: false } });
    expect(off.ok(), `${peUrl}: deactivating ${s.id} on the seed lane answered ${off.status()}`).toBe(true);
    ids.push(s.id);
  }
  return ids;
}

test.describe('trigger envelope contract', () => {
  test('every runtime emits schema-conformant envelopes', async ({ request }) => {
    const engines = await fetchEngines(request);
    test.skip(engines.length === 0, 'no RE_REGISTRY_URL or PE_BASE_URL');
    const validate = envelopeValidator();
    expect(validate, 'envelope schema registered').toBeTruthy();

    const results: string[] = [];
    for (const engine of engines) {
      const before = new Set((await ledgerRecords(request, engine.pe_url)).map(r => r.id));
      // The seed must own its lane for the push. The corpus's own interned
      // `OpenClaw Completion E2E` source also writes [4210:4214], looping a
      // firing step and a non-firing one; both are seed-tier, so they compose
      // in name order and "Envelope contract seed" lost to it on every other
      // push. Whether this passed tracked the PE's push-count parity, and when
      // it did, the corpus source had fired the machine, not this seed
      // (RealityEngine_Machines#126).
      const quiesced = await quiesceLane(request, engine.pe_url);
      let seedId = `envelope-contract-${engine.id}-${Date.now()}`;
      try {
        const seeded = await request.post(`${engine.pe_url}/api/sources`, {
          data: { id: seedId, type: 'test', name: 'Envelope contract seed', active: true,
                  region: SEED_REGION, inputs: [[0, 1, 0, 1]], loop: false },
        });
        // A refused seed must fail here, not be masked by a corpus source that
        // happens to cover the same region (it did, on Scala, before #149).
        expect(seeded.ok(), `${engine.id}: seed source registration answered ${seeded.status()}`).toBe(true);
        // Delete by the id the PE assigned: a runtime that mints its own leaves
        // the requested one unknown, and every run leaked a seed.
        seedId = sourceIdOf(await seeded.json()) ?? seedId;
        try {
          await request.post(`${engine.pe_url}/api/push`, { data: { compact: true } });
        } finally {
          await request.delete(`${engine.pe_url}/api/sources/${encodeURIComponent(seedId)}`);
        }
      } finally {
        for (const id of quiesced) {
          await request.patch(`${engine.pe_url}/api/sources/${encodeURIComponent(id)}`, { data: { active: true } });
        }
      }
      const fresh = (await ledgerRecords(request, engine.pe_url)).filter(r => !before.has(r.id));

      const problems: string[] = [];
      if (fresh.length === 0) problems.push('the seed produced no envelopes');
      // Any fresh envelope used to count, so this passed on the TypeScript PE
      // while it could not dispatch the seed's own machine at all — a push
      // fires unrelated corpus machines too. Matched by name: some runtimes
      // mint machine ids (RealityEngine_Machines#126).
      else if (!fresh.some(r => (r.envelope?.ces as { machineName?: unknown } | undefined)?.machineName === SEED_MACHINE)) {
        problems.push(`the seed did not dispatch ${SEED_MACHINE}`);
      }
      for (const r of fresh) {
        if (!r.envelope) { problems.push(`${r.id}: record carries no envelope`); continue; }
        if (!validate!(r.envelope)) {
          const e = validate!.errors ?? [];
          problems.push(`${r.id}: ${e.slice(0, 3).map((x: { instancePath: string; message?: string }) =>
            `${x.instancePath || '(root)'} ${x.message}`).join('; ')}`);
        }
      }
      const expected = EXPECTED_FAILURE[engine.runtime];
      if (problems.length === 0 && expected) {
        problems.push(`passes now — remove the expected-failure mark (${expected})`);
      } else if (problems.length > 0 && expected) {
        results.push(`${engine.id}: expected failure (${expected})`);
        continue;
      }
      if (problems.length > 0) results.push(`${engine.id}: ${problems.join(' | ')}`);
    }
    const failures = results.filter(r => !r.includes('expected failure'));
    expect(failures, results.join('\n')).toEqual([]);
  });
});
