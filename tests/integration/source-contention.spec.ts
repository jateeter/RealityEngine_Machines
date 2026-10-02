import { test, expect, type APIRequestContext } from '@playwright/test';
import { deployed, requireEngine, type Instance } from '../support/deployed-endpoints.js';

/**
 * Integration: two sources on one cell — the incumbent writer keeps it, on every
 * deployed PE (RealityEngine_CI docs/ARBITER_CONTRACT.md §4.4b, SURFACE_SPEC
 * "Sources & Sensors"; owner decision 2026-10-02).
 *
 * Two sources writing a cell in one transition violates the single transition
 * time constraint. Within a tier the source activated earliest keeps the cell,
 * so a newcomer loses however its name sorts — here it is named to sort FIRST,
 * which under the rule this replaced (the last name in (name, id) wins) would
 * have made the result look right by accident in only half the cases. The
 * contention is recorded, not absorbed: GET /api/sources/contention names the
 * cell, the winner and the suppressed source, and counts it.
 *
 * Every PE runs the same scenario, so the four runtimes are held to one
 * resolution: the same winner id on every engine.
 */

interface SourceRef { id: string; name: string; kind: string; activatedAt: number }
interface Contention {
  transition: number;
  cells: { cell: number; resolution: string; winner: SourceRef; suppressed: SourceRef[] }[];
  counters: { id: string; name: string; contended: number; suppressed: number }[];
}
interface SourceLite { id?: string; region?: { offset?: number; length?: number } }

const opts = { ignoreHTTPSErrors: true } as const;

async function engines(request: APIRequestContext): Promise<{ id: string; pe: string }[]> {
  const ep = await deployed(request);
  const running = ep.instances.filter((i: Instance) => (i.status ?? 'running') === 'running');
  if (running.length > 0) return running.map((i) => ({ id: i.id, pe: i.pe_url }));
  return [{ id: 'single', pe: requireEngine(ep.pe, 'PE') }];
}

/** Two adjacent cells no registered source writes, below the PE's dimension. */
async function freeLane(request: APIRequestContext, pe: string): Promise<number> {
  const state = await (await request.get(`${pe}/api/state`, opts)).json() as { perceptionDimension?: number };
  const body = await (await request.get(`${pe}/api/sources`, opts)).json() as { sources?: SourceLite[] } | SourceLite[];
  const sources = Array.isArray(body) ? body : body.sources ?? [];
  const used = new Set<number>();
  for (const s of sources) {
    const o = s.region?.offset ?? -1, l = s.region?.length ?? 0;
    for (let c = o; c < o + l; c++) used.add(c);
  }
  const dim = state.perceptionDimension ?? 0;
  for (let c = dim - 2; c >= 0; c--) if (!used.has(c) && !used.has(c + 1)) return c;
  throw new Error(`${pe}: no free two-cell lane below dimension ${dim}`);
}

test.describe('STT: the incumbent source keeps a contended cell', () => {
  test('a newcomer loses to the incumbent, and the contention is recorded on every PE', async ({ request }) => {
    const list = await engines(request);
    const winners: string[] = [];
    for (const engine of list) {
      const pe = engine.pe;
      const contention = await request.get(`${pe}/api/sources/contention`, opts);
      expect(contention.ok(), `${engine.id}: GET /api/sources/contention answered ${contention.status()}`).toBe(true);

      const lane = await freeLane(request, pe);
      const stamp = Date.now();
      const incumbentId = `stt-incumbent-${engine.id}-${stamp}`;
      const newcomerId = `stt-newcomer-${engine.id}-${stamp}`;
      const register = async (id: string, name: string, value: number) => {
        const r = await request.post(`${pe}/api/sources`, {
          ...opts,
          data: { id, type: 'test', name, active: true, region: { offset: lane, length: 2 },
                  inputs: [[value, value]], loop: true },
        });
        expect(r.ok(), `${engine.id}: registering ${id} answered ${r.status()}`).toBe(true);
      };
      try {
        await register(incumbentId, 'STT spec Zeta incumbent', 0.25);
        expect((await request.post(`${pe}/api/push`, { ...opts, data: { compact: true } })).ok()).toBe(true);
        // Named to sort first: the old rule's winner, the new rule's loser.
        await register(newcomerId, 'STT spec Alpha newcomer', 0.75);
        expect((await request.post(`${pe}/api/push`, { ...opts, data: { compact: true } })).ok()).toBe(true);

        const c = await (await request.get(`${pe}/api/sources/contention`, opts)).json() as Contention;
        const cell = c.cells.find((x) => x.cell === lane);
        expect(cell, `${engine.id}: cell ${lane} recorded as contended`).toBeTruthy();
        expect(cell!.resolution, `${engine.id}: resolution`).toBe('incumbent');
        expect(cell!.winner.id, `${engine.id}: the incumbent keeps the cell`).toBe(incumbentId);
        expect(cell!.suppressed.map((s) => s.id), `${engine.id}: the newcomer is suppressed`).toEqual([newcomerId]);
        expect(cell!.winner.activatedAt, `${engine.id}: the incumbent was activated first`)
          .toBeLessThan(cell!.suppressed[0]!.activatedAt);
        const counter = c.counters.find((x) => x.id === newcomerId);
        expect(counter?.suppressed ?? 0, `${engine.id}: the newcomer's loss is counted`).toBeGreaterThanOrEqual(1);

        const state = await (await request.get(`${pe}/api/state`, opts)).json() as { assembledVector?: number[] };
        expect(state.assembledVector?.[lane], `${engine.id}: the incumbent's value is assembled`).toBe(0.25);
        winners.push(cell!.winner.id.replace(`-${engine.id}-`, '-'));
      } finally {
        await request.delete(`${pe}/api/sources/${encodeURIComponent(newcomerId)}`, opts);
        await request.delete(`${pe}/api/sources/${encodeURIComponent(incumbentId)}`, opts);
      }
    }
    expect(new Set(winners).size, `every PE resolved the same way: ${winners.join(', ')}`).toBe(1);
  });
});
