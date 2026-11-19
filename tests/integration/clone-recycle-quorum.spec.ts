/**
 * Clone and recycle — 3-of-3 (RealityEngine_CI SURFACE_SPEC.md, "Cloneable
 * machines"; RealityEngine_CI#713; localAssetStorageStack ROADMAP phase 7).
 *
 * What regression compares, per the specification:
 * - GET /api/machines/cloneable, identical on the voting engines once each
 *   machine is named by its corpus name rather than its id. Ids are identity,
 *   which a comparison never compares (SURFACE_SPEC.md, "The OSRE value is the
 *   equality indicator across runtimes"): a machine loaded after boot gets an
 *   id minted per engine, and a universe that has run the regression holds 18
 *   of them, so a byte comparison failed on three agreeing engines
 *   (RealityEngine_CI deployment gate, 2026-11-18);
 * - each clone response, except `engineInstance` and the instance segment of
 *   `cloneId`;
 * - the steps of a clone, compared like any other machine's.
 *
 * One cloneable template, the same asset and envelope, on every voting engine:
 * clone, retry (idempotent), drive the clone through its template's sequences
 * on POST /api/machines/:cloneId/process, then a stale recycle, the recycle,
 * and a replay. Every engine is driven identically and the outcomes must agree:
 * the rule is compared, not any one engine's answer (no reference member).
 *
 * Regression runs identical corpora on the voting engines. In deployment the
 * corpora commonly differ and so may the cloneable sets; that is not a fault,
 * and this spec is a regression result only.
 */
import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const NATIVES = ['cpp', 'lsp', 'scala'] as const;
type Runtime = typeof NATIVES[number];
interface Instance { id: string; runtime: string; re_url: string; status: string }

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

/** Canonical JSON: sorted keys, so two engines' bodies compare by content. */
function canonical(v: unknown): string {
  if (Array.isArray(v)) return `[${v.map(canonical).join(',')}]`;
  if (v && typeof v === 'object') {
    return `{${Object.keys(v as object).sort().map(k => `${JSON.stringify(k)}:${canonical((v as Record<string, unknown>)[k])}`).join(',')}}`;
  }
  return JSON.stringify(v);
}

/** A clone response with the instance taken out, which is all that may differ. */
function withoutInstance(body: Record<string, unknown>, instance: string): string {
  const { engineInstance: _drop, ...rest } = body;
  return canonical(JSON.parse(JSON.stringify(rest).split(`.${instance}.`).join('.<instance>.')));
}

const RUN = Date.now().toString(36);
const ENVELOPE = `env-quorum-${RUN}`;
const ASSET = `asset-quorum-${RUN}`;

test.describe('Clone and recycle (3-of-3)', () => {
  test('the voting engines agree on what is cloneable, on a clone, its steps and its recycle', async ({ request }) => {
    test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
    test.setTimeout(180_000);
    const engines = await natives(request);
    const missing = NATIVES.filter(rt => !engines.has(rt));
    test.skip(missing.length > 0, `not applicable: 3-of-3 needs cpp, lsp and scala; this deployment lacks ${missing.join(', ')}`);

    // 1. The listing, each machine by its corpus name (its id is identity).
    const listings = new Map<Runtime, string>();
    const idOf = new Map<Runtime, Map<string, string>>(); // engine → name → its id
    for (const rt of NATIVES) {
      const re = engines.get(rt)!.re_url;
      const all = await request.get(`${re}/api/machines`, { timeout: 60_000 });
      expect(all.ok(), `${rt} GET /api/machines → ${all.status()}`).toBe(true);
      const names = new Map<string, string>();
      for (const m of (await all.json() as { machines: Array<{ id: string; name: string }> }).machines) names.set(m.id, m.name);
      idOf.set(rt, new Map([...names].map(([id, name]) => [name, id])));
      const r = await request.get(`${re}/api/machines/cloneable`, { timeout: 60_000 });
      expect(r.ok(), `${rt} GET /api/machines/cloneable → ${r.status()}`).toBe(true);
      const body = await r.json() as { machines: Array<Record<string, unknown> & { id: string }> };
      const byName = body.machines.map(({ id, ...rest }) => ({ ...rest, name: names.get(id) ?? `<unlisted ${id}>` }))
        .sort((a, b) => a.name.localeCompare(b.name));
      listings.set(rt, canonical({ ...body, machines: byName }));
    }
    const listingReport = [...listings].map(([rt, t]) => `  ${rt.padEnd(5)} ${t.length} bytes: ${t.slice(0, 80)}…`).join('\n');
    expect(new Set(listings.values()).size, `GET /api/machines/cloneable differs (compared by corpus name)\n${listingReport}`).toBe(1);

    const listed = (JSON.parse([...listings.values()][0]!) as { machines: Array<{ name: string; cloneable: boolean }> }).machines;
    const templateName = listed.find(m => m.cloneable)?.name;
    test.skip(!templateName, 'not applicable: the regression corpus holds no cloneable machine');
    // Each engine's own id for the template.
    const templateOn = (rt: Runtime) => idOf.get(rt)!.get(templateName!)!;

    // The template's sequences, as the inputs that drive its clone.
    const detail = await request.get(`${engines.get('cpp')!.re_url}/api/machines/${encodeURIComponent(templateOn('cpp'))}`);
    const sequences = ((await detail.json()).machine.sequences ?? []) as Array<{ events?: Array<{ elements?: Array<{ value: number }> }> }>;
    const inputs = sequences.flatMap(s => (s.events ?? []).map(e => (e.elements ?? []).map(el => el.value)));

    const outcomes = new Map<Runtime, string>();
    const live: Array<[string, string, number]> = [];
    try {
      for (const rt of NATIVES) {
        const inst = engines.get(rt)!;
        const re = inst.re_url;
        const cloneUrl = `${re}/api/engine/clone/machine/${encodeURIComponent(templateOn(rt))}?asset=${ASSET}&envelope=${ENVELOPE}`;

        // 2. Clone, then the same dispatch again.
        const first = await request.post(cloneUrl, { timeout: 60_000 });
        expect(first.status(), `${rt} clone`).toBe(201);
        const made = await first.json() as Record<string, unknown> & { cloneId: string; generation: number; engineInstance: string };
        live.push([re, made.cloneId, made.generation]);
        expect(made.engineInstance, `${rt} engineInstance is the registry id`).toBe(inst.id);
        const again = await request.post(cloneUrl, { timeout: 60_000 });

        // 3. The clone's steps: its template's events as inputs, in order.
        const steps: string[] = [];
        for (const input of inputs) {
          const r = await request.post(`${re}/api/machines/${encodeURIComponent(made.cloneId)}/process`, { data: { inputEvent: input }, timeout: 60_000 });
          const t = await r.json() as { machineOutput?: { vector?: number[] }; mergedOutput?: { vector?: number[] } };
          steps.push(canonical({ status: r.status(), output: t.machineOutput?.vector ?? null, merged: t.mergedOutput?.vector ?? null }));
        }
        const after = await request.get(`${re}/api/machines/${encodeURIComponent(made.cloneId)}`);
        const m = (await after.json()).machine as { cloneOf?: string; assetId?: string; envelopeId?: string; perceptualMapping?: unknown;
          sequences?: Array<{ id: string; events?: Array<{ id: string; isActive?: boolean }> }> };
        const active = (m.sequences ?? []).flatMap(s => (s.events ?? []).filter(e => e.isActive).map(e => `${s.id}/${e.id}`)).sort();

        // 4. A stale recycle, the recycle, a replay.
        const stale = await request.post(`${re}/api/engine/recycle/machine/${encodeURIComponent(made.cloneId)}?generation=${made.generation + 7}`);
        const recycled = await request.post(`${re}/api/engine/recycle/machine/${encodeURIComponent(made.cloneId)}?generation=${made.generation}`);
        if (recycled.ok()) live.pop();
        const replay = await request.post(`${re}/api/engine/recycle/machine/${encodeURIComponent(made.cloneId)}?generation=${made.generation}`);
        const gone = await request.get(`${re}/api/machines/${encodeURIComponent(made.cloneId)}`);

        outcomes.set(rt, canonical({
          clone: withoutInstance(made, inst.id),
          retry: { status: again.status(), same: again.ok() && withoutInstance(await again.json(), inst.id) === withoutInstance(made, inst.id) },
          // cloneOf by the template's name: its id is this engine's own.
          listedAs: { cloneOf: m.cloneOf === templateOn(rt) ? templateName : `<other ${m.cloneOf}>`, assetId: m.assetId, envelopeId: m.envelopeId, perceptualMapping: m.perceptualMapping },
          steps,
          active,
          stale: { status: stale.status(), generation: (await stale.json()).generation },
          recycle: { status: recycled.status(), body: withoutInstance(await recycled.json(), inst.id) },
          replay: replay.status(),
          afterRecycle: gone.status(),
        }));
      }
    } finally {
      for (const [re, id, generation] of live) {
        await request.post(`${re}/api/engine/recycle/machine/${encodeURIComponent(id)}?generation=${generation}`).catch(() => undefined);
      }
    }

    const report = [...outcomes].map(([rt, o]) => `  ${rt.padEnd(5)} ${o}`).join('\n');
    expect(new Set(outcomes.values()).size, `disagreement (3-of-3, no reference member)\n${report}`).toBe(1);
    // And what they agree on is the specified behaviour.
    const o = JSON.parse([...outcomes.values()][0]!);
    expect(o.retry, report).toEqual({ status: 200, same: true });
    expect(o.listedAs.cloneOf, report).toBe(templateName);
    expect(o.listedAs.assetId, report).toBe(ASSET);
    expect(o.stale.status, report).toBe(409);
    expect(o.recycle.status, report).toBe(200);
    expect(o.replay, report).toBe(404);
    expect(o.afterRecycle, report).toBe(404);
  });
});
