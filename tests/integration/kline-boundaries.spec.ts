import { test, expect } from '@playwright/test';
import type { APIRequestContext, APIResponse } from '@playwright/test';
import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

/**
 * Integration: K-line boundaries, both halves, 3-of-3 (RealityEngine_CI#603,
 * SURFACE_SPEC.md "K-lines and runtime snapshots"; this repo's #222).
 *
 * The boundaries are set by the corpus, so every voter must open and close the
 * same K-lines for the same drive, and every PE must record the same ISRE
 * composition. From each voter's own reset (both halves), with `klineCapture`
 * (RE, /api/engine/config) and `isreCapture` (PE, /api/config) turned on for the
 * drive and restored after, PUSHES pushes through each PE, then on every voter:
 *   - `GET /api/klines` has the same K-lines by (focal, sequence, open.step,
 *     close.step, outcome, path); `id`, `instance`, `lamport` and `commit`
 *     are excluded and differ across engines;
 *   - every K-line validates against re-kline/1 and every composition record
 *     against re-isre-composition/1 (schemas/);
 *   - every composition record names the current taxonomy, re-source-kinds/2;
 *   - the composition records agree by re.step on sources (cells, kind,
 *     provider, class).
 *
 * The regression stage (RealityEngine_CI scripts/regression-kline-boundaries.py)
 * also checks reset and recovery closes, and each record against the corpus.
 *
 * It resets the voters and pushes: run it against a regression universe, not a
 * deployment. A conformance follower never votes and is not driven here.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const VOTERS = ['cpp', 'lsp', 'scala'] as const;
const PUSHES = Number(process.env.KLINE_PUSHES ?? 40);
const TAXONOMY = 're-source-kinds/2';
const REPO = join(dirname(fileURLToPath(import.meta.url)), '../..');

interface Instance { id: string; runtime: string; re_url?: string; pe_url?: string; status: string; role?: string }
interface Voter { id: string; runtime: string; re: string; pe: string }
type Rec = Record<string, any>;

async function voters(request: APIRequestContext): Promise<Voter[]> {
  if (!REGISTRY_URL) return [];
  const r = await request.get(REGISTRY_URL);
  if (!r.ok()) return [];
  const out: Voter[] = [];
  for (const i of ((await r.json()) as { instances?: Instance[] }).instances ?? []) {
    if (i.status !== 'running' || i.role === 'follower' || !i.re_url || !i.pe_url) continue;
    if (!(VOTERS as readonly string[]).includes(i.runtime) || out.some(v => v.runtime === i.runtime)) continue;
    out.push({ id: i.id, runtime: i.runtime, re: i.re_url.replace(/\/$/, ''), pe: i.pe_url.replace(/\/$/, '') });
  }
  return out;
}

function validators() {
  const require = createRequire(import.meta.url);
  const Ajv2020 = require('ajv/dist/2020.js').default ?? require('ajv/dist/2020.js');
  const ajv = new Ajv2020({ strict: false, allErrors: true });
  const dir = join(REPO, 'schemas');
  for (const f of readdirSync(dir).filter(n => n.endsWith('.schema.json'))) {
    ajv.addSchema(JSON.parse(readFileSync(join(dir, f), 'utf8')));
  }
  const base = 'https://realityengine.example.org/schemas/';
  return { kline: ajv.getSchema(`${base}re-kline.schema.json`), composition: ajv.getSchema(`${base}re-isre-composition.schema.json`) };
}

async function paged(request: APIRequestContext, url: string, list: string, cursor: string, from: number): Promise<Rec[]> {
  const out: Rec[] = [];
  let at: number | null = from;
  while (at !== null) {
    const r: APIResponse = await request.get(`${url}?${cursor}=${at}&limit=1000`);
    expect(r.status(), `GET ${url}`).toBe(200);
    const body: Rec = await r.json();
    out.push(...body[list]);
    at = body.next ?? null;
  }
  return out;
}

const key = (k: Rec) => JSON.stringify([k.focal.machine, k.focal.sequence, k.open.step, k.close.step, k.outcome,
  (k.path ?? []).map((p: Rec) => [p.event, p.step])]);
const composition = (r: Rec) => JSON.stringify([r.re.step, r.taxonomy,
  (r.sources ?? []).map((s: Rec) => [s.cells, s.kind, s.provider ?? null, s.class])]);

test.describe('K-line boundaries (#603)', () => {
  test.describe.configure({ mode: 'serial', timeout: 600_000 });
  let vs: Voter[];

  test.beforeAll(async ({ request }) => {
    vs = await voters(request);
  });

  test('both halves agree 3-of-3 and validate', async ({ request }) => {
    test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
    test.skip(vs.length < VOTERS.length, `3-of-3 needs cpp, lsp and scala; the registry lists ${vs.map(v => v.runtime).join(', ') || 'none'}`);
    const since: Record<string, number> = {};
    try {
      for (const v of vs) {
        expect((await request.put(`${v.re}/api/engine/config/klineCapture`, { data: { value: true } })).status(), `${v.id} klineCapture`).toBe(200);
        expect((await request.patch(`${v.pe}/api/config`, { data: { isreCapture: true } })).status(), `${v.id} isreCapture`).toBe(200);
        expect((await request.post(`${v.re}/api/engine/reset`, { data: {} })).ok(), `${v.id} RE reset`).toBe(true);
        expect((await request.post(`${v.pe}/api/reset`, { data: {} })).ok(), `${v.id} PE reset`).toBe(true);
        since[v.id] = (await (await request.get(`${v.re}/api/engine/clock`)).json()).commit + 1;
      }
      for (const v of vs) {
        for (let i = 0; i < PUSHES; i++) {
          expect((await request.post(`${v.pe}/api/push`, { data: { compact: true } })).status(), `${v.id} push ${i}`).toBe(200);
        }
      }
      const { kline, composition: comp } = validators();
      const keys: Record<string, string[]> = {};
      const comps: Record<string, string[]> = {};
      for (const v of vs) {
        const kl = await paged(request, `${v.re}/api/klines`, 'klines', 'since', since[v.id]);
        const cr = await paged(request, `${v.pe}/api/isre-composition`, 'records', 'from', since[v.id]);
        expect(kl.length, `${v.id}: the drive closed K-lines`).toBeGreaterThan(0);
        expect(cr.length, `${v.id}: one composition record per push`).toBe(PUSHES);
        const badK = kl.filter(k => !kline(k));
        expect(badK.length, `${v.id}: re-kline/1 ${JSON.stringify(kline.errors?.slice(0, 2))}`).toBe(0);
        const badC = cr.filter(r => !comp(r));
        expect(badC.length, `${v.id}: re-isre-composition/1 ${JSON.stringify(comp.errors?.slice(0, 2))}`).toBe(0);
        expect(cr.filter(r => r.taxonomy !== TAXONOMY).length, `${v.id}: every record names ${TAXONOMY}`).toBe(0);
        keys[v.runtime] = kl.map(key).sort();
        comps[v.runtime] = cr.sort((a, b) => a.re.step - b.re.step).map(composition);
      }
      for (const rt of VOTERS.slice(1)) {
        expect(keys[rt], `K-lines by parity key: cpp vs ${rt}`).toEqual(keys.cpp);
        expect(comps[rt], `ISRE composition by step: cpp vs ${rt}`).toEqual(comps.cpp);
      }
    } finally {
      for (const v of vs) {
        await request.delete(`${v.re}/api/engine/config/klineCapture`).catch(() => undefined);
        await request.patch(`${v.pe}/api/config`, { data: { isreCapture: false } }).catch(() => undefined);
      }
    }
  });
});
