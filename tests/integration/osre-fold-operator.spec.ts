import { test, expect, type APIRequestContext } from '@playwright/test';
import { deployed, requireEngine, type Instance } from '../support/deployed-endpoints.js';

/**
 * Integration: a source on an OSRE cell is folded with the OSRE value by the
 * writing machine's declared operator over [0..1], on every deployed PE
 * (RealityEngine_CI docs/ARBITER_CONTRACT.md §4.4b; owner decision 2026-10-02).
 *
 * Stimulus: the OpenClaw dispatch seed [0,1,0,1] on [4210:4214] fires
 * `OpenClaw Completion E2E` (declared `or`), whose output [1,0,0,0] lands on
 * [4214:4218]. A second source writes [0,0.4,0,0] on that output lane. After the
 * push, the next assembled vector must be the fold, `max`:
 *
 *   4214: max(source 0,   OSRE 1) = 1   — the source alone would have read 0
 *   4215: max(source 0.4, OSRE 0) = 0.4
 *
 * Both lanes are quiesced for the push, so only these two sources write them.
 */
const SEED = { offset: 4210, length: 4 };
const OUT = { offset: 4214, length: 4 };
const opts = { ignoreHTTPSErrors: true } as const;

interface SourceLite { id?: string; active?: boolean; region?: { offset?: number; length?: number } }

async function engines(request: APIRequestContext): Promise<{ id: string; re: string; pe: string }[]> {
  const ep = await deployed(request);
  const running = ep.instances.filter((i: Instance) => (i.status ?? 'running') === 'running');
  if (running.length > 0) return running.map((i) => ({ id: i.id, re: i.re_url, pe: i.pe_url }));
  return [{ id: 'single', re: requireEngine(ep.re, 'RE'), pe: requireEngine(ep.pe, 'PE') }];
}

/** Deactivate every active source overlapping [lo, hi); returns their ids to restore. */
async function quiesce(request: APIRequestContext, pe: string, lo: number, hi: number): Promise<string[]> {
  const body = await (await request.get(`${pe}/api/sources`, opts)).json() as { sources?: SourceLite[] } | SourceLite[];
  const sources = Array.isArray(body) ? body : body.sources ?? [];
  const ids: string[] = [];
  for (const s of sources) {
    const o = s.region?.offset ?? -1, l = s.region?.length ?? 0;
    if (!s.id || s.active !== true || o >= hi || o + l <= lo) continue;
    const r = await request.patch(`${pe}/api/sources/${encodeURIComponent(s.id)}`, { ...opts, data: { active: false } });
    expect(r.ok(), `${pe}: quiescing ${s.id}`).toBe(true);
    ids.push(s.id);
  }
  return ids;
}

test.describe('OSRE fold operator', () => {
  test('a source on a machine output lane folds with the OSRE value (or = max) on every PE', async ({ request }) => {
    const results: string[] = [];
    for (const engine of await engines(request)) {
      // Layer-local reset: both halves, so the machine starts from its initial state.
      expect((await request.post(`${engine.re}/api/engine/reset`, { ...opts, data: {} })).ok(), `${engine.id}: RE reset`).toBe(true);
      expect((await request.post(`${engine.pe}/api/reset`, { ...opts, data: {} })).ok(), `${engine.id}: PE reset`).toBe(true);
      const restored = await quiesce(request, engine.pe, SEED.offset, OUT.offset + OUT.length);
      const stamp = Date.now();
      const seedId = `osre-fold-seed-${engine.id}-${stamp}`;
      const laneId = `osre-fold-lane-${engine.id}-${stamp}`;
      try {
        for (const [id, region, inputs] of [
          [seedId, SEED, [[0, 1, 0, 1]]],
          [laneId, OUT, [[0, 0.4, 0, 0]]],
        ] as const) {
          const r = await request.post(`${engine.pe}/api/sources`, {
            ...opts,
            data: { id, type: 'test', name: id, active: true, region, inputs, loop: true },
          });
          expect(r.ok(), `${engine.id}: registering ${id}`).toBe(true);
        }
        expect((await request.post(`${engine.pe}/api/push`, { ...opts, data: { compact: true } })).ok()).toBe(true);
        const state = await (await request.get(`${engine.pe}/api/state`, opts)).json() as { assembledVector?: number[] };
        const v = state.assembledVector ?? [];
        const got = [v[OUT.offset], v[OUT.offset + 1]];
        results.push(`${engine.id}: [${got.join(', ')}]`);
        expect(got[0], `${engine.id}: 4214 = max(source 0, OSRE 1)`).toBe(1);
        expect(got[1], `${engine.id}: 4215 = max(source 0.4, OSRE 0)`).toBeCloseTo(0.4, 12);
      } finally {
        await request.delete(`${engine.pe}/api/sources/${encodeURIComponent(seedId)}`, opts);
        await request.delete(`${engine.pe}/api/sources/${encodeURIComponent(laneId)}`, opts);
        for (const id of restored) {
          await request.patch(`${engine.pe}/api/sources/${encodeURIComponent(id)}`, { ...opts, data: { active: true } });
        }
      }
    }
    console.log(`  OSRE fold on the output lane: ${results.join('; ')}`);
  });
});
