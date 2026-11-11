import { test, expect, type APIRequestContext } from '@playwright/test';
import { deployed, requireEngine, type Instance } from '../support/deployed-endpoints.js';

/**
 * Integration: the `POST /api/sources` create body, on every deployed PE
 * (RealityEngine_CI SURFACE_SPEC "POST /api/sources: the create body",
 * RealityEngine_CI#755).
 *
 * A create need not repeat the served shape. `kind` stands in for `type`;
 * `region` and a sensor's `sensorId` are required; the rest takes declared
 * defaults. Scala accepted only the full serialized shape, so a sparse sensor
 * body that C++ and LSP accepted answered 400 there.
 *
 * Each PE registers a sparse and a full sensor body, reads both back, and the
 * read-backs must match across PEs field for field (ids and offsets aside).
 */

const opts = { ignoreHTTPSErrors: true } as const;

interface Served {
  id: string; type: string; name: string; active: boolean; region: { offset: number; length: number };
  sensorId: string; lastValue: number[]; lastUpdated: number | null; ttlMs: number; origin?: string;
}

async function engines(request: APIRequestContext): Promise<{ id: string; pe: string }[]> {
  const ep = await deployed(request);
  const running = ep.instances.filter((i: Instance) => (i.status ?? 'running') === 'running');
  if (running.length > 0) return running.map((i) => ({ id: i.id, pe: i.pe_url }));
  return [{ id: 'single', pe: requireEngine(ep.pe, 'PE') }];
}

/** A cell no registered source writes, below the PE's dimension. */
async function freeCell(request: APIRequestContext, pe: string): Promise<number> {
  const state = await (await request.get(`${pe}/api/state`, opts)).json() as { perceptionDimension?: number };
  const body = await (await request.get(`${pe}/api/sources`, opts)).json() as { sources?: Served[] } | Served[];
  const sources = Array.isArray(body) ? body : body.sources ?? [];
  const used = new Set<number>();
  for (const s of sources) for (let c = s.region?.offset ?? -1; c < (s.region?.offset ?? -1) + (s.region?.length ?? 0); c++) used.add(c);
  const dim = state.perceptionDimension ?? 0;
  for (let c = dim - 3; c >= 0; c--) if (!used.has(c) && !used.has(c + 1)) return c;
  throw new Error(`${pe}: no free cell pair below dimension ${dim}`);
}

/** The fields the contract fixes, without the per-PE id, sensorId and offset. */
const comparable = (s: Served) => ({
  type: s.type, name: s.name, active: s.active, length: s.region.length,
  lastValue: s.lastValue, lastUpdated: s.lastUpdated, ttlMs: s.ttlMs, origin: s.origin ?? null,
});

test.describe('POST /api/sources: the create body', () => {
  test('a sparse and a full sensor body are accepted and read back alike on every PE', async ({ request }) => {
    const list = await engines(request);
    const seen: Record<string, unknown> = {};
    for (const engine of list) {
      const pe = engine.pe;
      const cell = await freeCell(request, pe);
      const stamp = Date.now();
      const sparseId = `create-sparse-${engine.id}-${stamp}`;
      const fullId = `create-full-${engine.id}-${stamp}`;
      const bodies = {
        // `kind`, not `type`; no lastValue, lastUpdated, nor (below) ttlMs.
        sparse: { id: sparseId, kind: 'sensor', name: 'create-body sparse', sensorId: sparseId,
                  region: { offset: cell, length: 1 }, origin: 'spec', active: false },
        full: { id: fullId, type: 'sensor', name: 'create-body full', sensorId: fullId,
                region: { offset: cell + 1, length: 1 }, active: false, lastValue: [], lastUpdated: null,
                ttlMs: 60000, origin: 'spec' },
      };
      try {
        const readBack: Record<string, unknown> = {};
        for (const [label, data] of Object.entries(bodies)) {
          const r = await request.post(`${pe}/api/sources`, { ...opts, data });
          expect(r.ok(), `${engine.id}: the ${label} body answered ${r.status()} ${await r.text()}`).toBe(true);
          const listing = await (await request.get(`${pe}/api/sources`, opts)).json() as { sources?: Served[] } | Served[];
          const sources = Array.isArray(listing) ? listing : listing.sources ?? [];
          const got = sources.find((s) => s.id === data.id);
          expect(got, `${engine.id}: ${data.id} is not listed after its create`).toBeDefined();
          expect((got as Served).sensorId, `${engine.id}: ${data.id} sensorId`).toBe(data.sensorId);
          readBack[label] = comparable(got as Served);
        }
        // The declared defaults, on the sparse body.
        expect(readBack.sparse, `${engine.id}: sparse defaults`).toMatchObject({
          type: 'sensor', active: false, lastValue: [], lastUpdated: null, ttlMs: 5000, origin: 'spec',
        });
        seen[engine.id] = readBack;
      } finally {
        for (const id of [sparseId, fullId]) await request.delete(`${pe}/api/sources/${id}`, opts);
      }
    }
    const [first, ...rest] = Object.keys(seen);
    for (const id of rest) expect(seen[id], `${id} reads the create bodies back unlike ${first}`).toEqual(seen[first]);
  });
});
