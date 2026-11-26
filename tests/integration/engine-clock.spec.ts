import { randomUUID } from 'node:crypto';
import { test, expect } from '@playwright/test';
import type { APIRequestContext, APIResponse } from '@playwright/test';

/**
 * Integration: the full Lamport clock on every RE and PE (RealityEngine_CI#600,
 * SURFACE_SPEC.md "The instance clock"; this repo's #220).
 *
 * Every running instance the instance registry lists, voters and followers
 * alike, is two participants: its RE (`GET /api/engine/clock`) and its PE
 * (`GET /api/clock`). On each:
 *   - the clock is {instance, lamport, commit, step} (plus the inbound header
 *     counts), `lamport >= commit`, and both are monotonic across requests;
 *   - every response carries `RE-Clock: instance=<its instance>; lamport=<n>`;
 *   - a presented `RE-Clock` whose lamport is far ahead moves the participant's
 *     lamport past it (a receive is max(local, received) + 1);
 *   - a malformed header is refused with 400 and the spec's error body.
 *
 * The comparison (QUORUM_CONTRACT.md): `step` is compared 3-of-3 across the
 * voters' REs, while `instance`, `lamport` and `commit` are per participant and
 * excluded. Every participant's `instance` is asserted distinct.
 *
 * Safe against a live universe: it reads clocks and sends headers. The HealthKit
 * receive checks use a bridgeId of their own and a type no mapping resolves.
 *
 * The injected lamport stays far below 2^53 - 1: each injection is the
 * participant's lamport plus 10^6, and the participant persists its mark past
 * it, so a universe's clocks grow by about 10^6 per run of this spec.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const TOKEN = process.env.HEALTHKIT_BRIDGE_TOKEN ?? '';
const VOTERS = ['cpp', 'lsp', 'scala'] as const;
const JUMP = 1_000_000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const HEADER = /^instance=([0-9a-f-]{36}); lamport=(\d+)$/;

interface Instance { id: string; runtime: string; re_url?: string; pe_url?: string; status: string }
interface Participant { name: string; runtime: string; url: string; clockPath: string }
interface Clock { instance: string; lamport: number; commit: number; step: number; headers?: Record<string, number> }

async function participants(request: APIRequestContext): Promise<Participant[]> {
  if (!REGISTRY_URL) return [];
  const r = await request.get(REGISTRY_URL);
  if (!r.ok()) return [];
  const out: Participant[] = [];
  for (const i of ((await r.json()) as { instances?: Instance[] }).instances ?? []) {
    if (i.status !== 'running') continue;
    if (i.re_url) out.push({ name: `${i.id} RE`, runtime: i.runtime, url: i.re_url, clockPath: '/api/engine/clock' });
    if (i.pe_url) out.push({ name: `${i.id} PE`, runtime: i.runtime, url: i.pe_url, clockPath: '/api/clock' });
  }
  return out;
}

async function clockOf(request: APIRequestContext, p: Participant, headers?: Record<string, string>) {
  const r = await request.get(`${p.url}${p.clockPath}`, { headers });
  expect(r.status(), `${p.name} GET ${p.clockPath}`).toBe(200);
  return { response: r, clock: (await r.json()) as Clock };
}

/** The response's RE-Clock, parsed; asserted present and well formed. */
function stamped(p: Participant, r: APIResponse): { instance: string; lamport: number } {
  const value = r.headers()['re-clock'];
  expect(value, `${p.name}: the response carries RE-Clock`).toBeTruthy();
  const m = HEADER.exec(value!);
  expect(m, `${p.name}: RE-Clock "${value}" is "instance=<uuid>; lamport=<n>"`).not.toBeNull();
  return { instance: m![1], lamport: Number(m![2]) };
}

function presented(lamport: number): Record<string, string> {
  return { 'RE-Clock': `instance=${randomUUID()}; lamport=${lamport}` };
}

test.describe('engine clock (#600)', () => {
  let all: Participant[];

  test.beforeEach(async ({ request }) => {
    test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
    all = await participants(request);
    test.skip(all.length === 0, 'the instance registry lists no running instance');
  });

  test('the clock shape, lamport >= commit, and monotonic across requests', async ({ request }) => {
    for (const p of all) {
      const first = await clockOf(request, p);
      const c = first.clock;
      expect(Object.keys(c).filter(k => k !== 'headers').sort(), `${p.name}: clock keys`)
        .toEqual(['commit', 'instance', 'lamport', 'step']);
      expect(c.instance, `${p.name}: instance is a lower-case UUID`).toMatch(UUID);
      for (const k of ['lamport', 'commit', 'step'] as const) {
        expect(Number.isSafeInteger(c[k]) && c[k] >= 0, `${p.name}: ${k} = ${c[k]} is a non-negative integer`).toBe(true);
      }
      expect(c.lamport, `${p.name}: lamport >= commit`).toBeGreaterThanOrEqual(c.commit);
      expect(Object.keys(c.headers ?? {}).sort(), `${p.name}: header counts`).toEqual(['missing', 'received', 'rejected']);

      const header = stamped(p, first.response);
      expect(header.instance, `${p.name}: RE-Clock names the participant`).toBe(c.instance);
      // The response is a send after the body was read: its lamport is later.
      expect(header.lamport, `${p.name}: RE-Clock lamport >= the body's`).toBeGreaterThanOrEqual(c.lamport);

      const second = (await clockOf(request, p)).clock;
      expect(second.instance, `${p.name}: instance is stable`).toBe(c.instance);
      expect(second.lamport, `${p.name}: lamport increases across requests`).toBeGreaterThan(c.lamport);
      expect(second.commit, `${p.name}: commit never decreases`).toBeGreaterThanOrEqual(c.commit);
      expect(second.lamport, `${p.name}: lamport >= commit`).toBeGreaterThanOrEqual(second.commit);
    }
  });

  test('a presented RE-Clock far ahead moves lamport past it', async ({ request }) => {
    for (const p of all) {
      const before = (await clockOf(request, p)).clock;
      const injected = before.lamport + JUMP;
      const { clock: after, response } = await clockOf(request, p, presented(injected));
      expect(after.lamport, `${p.name}: lamport after receiving ${injected}`).toBeGreaterThan(injected);
      expect(after.headers?.received, `${p.name}: the header is counted as received`)
        .toBeGreaterThan(before.headers?.received ?? 0);
      expect(stamped(p, response).lamport, `${p.name}: the reply's RE-Clock is past the injection`).toBeGreaterThan(injected);
      // The jump is durable in this process: a later plain read stays past it.
      expect((await clockOf(request, p)).clock.lamport, `${p.name}: lamport stays past the injection`).toBeGreaterThan(injected);
    }
  });

  test('a malformed RE-Clock is refused with 400', async ({ request }) => {
    const malformed = [
      'instance=not-a-uuid; lamport=1',
      `instance=${randomUUID()}`,
      `instance=${randomUUID()}; lamport=-1`,
      `instance=${randomUUID().toUpperCase()}; lamport=1`,
    ];
    for (const p of all) {
      const before = (await clockOf(request, p)).clock;
      for (const value of malformed) {
        const r = await request.get(`${p.url}${p.clockPath}`, { headers: { 'RE-Clock': value } });
        expect(r.status(), `${p.name}: RE-Clock "${value}"`).toBe(400);
        expect(await r.json(), `${p.name}: the error body`).toEqual({ error: 'malformed RE-Clock header' });
      }
      const after = (await clockOf(request, p)).clock;
      expect((after.headers?.rejected ?? 0) - (before.headers?.rejected ?? 0), `${p.name}: rejected count`)
        .toBe(malformed.length);
      // A refused request still counts as a receive: lamport moved on.
      expect(after.lamport, `${p.name}: lamport after refusals`).toBeGreaterThan(before.lamport + malformed.length);
    }
  });

  test('comparison: step agrees 3-of-3 across the voters; instance is per participant', async ({ request }) => {
    const instances = new Map<string, string>();
    for (const p of all) {
      const c = (await clockOf(request, p)).clock;
      const holder = instances.get(c.instance);
      expect(holder, `${p.name} and ${holder} share instance ${c.instance}`).toBeUndefined();
      instances.set(c.instance, p.name);
    }

    const voterREs = new Map<string, Participant>();
    for (const p of all) {
      if ((VOTERS as readonly string[]).includes(p.runtime) && p.clockPath === '/api/engine/clock' && !voterREs.has(p.runtime)) {
        voterREs.set(p.runtime, p);
      }
    }
    const missing = VOTERS.filter(rt => !voterREs.has(rt));
    test.skip(missing.length > 0, `not applicable: 3-of-3 needs cpp, lsp and scala; this deployment lacks ${missing.join(', ')}`);
    const steps = new Map<string, number>();
    for (const [rt, p] of voterREs) steps.set(rt, (await clockOf(request, p)).clock.step);
    const report = [...steps].map(([rt, s]) => `  ${rt.padEnd(5)} step ${s}`).join('\n');
    expect(new Set(steps.values()).size, `step: disagreement (3-of-3, no reference member)\n${report}`).toBe(1);
  });

  test('HealthKit ingest, scope and resync apply the receive rule on every PE', async ({ request }) => {
    const auth: Record<string, string> = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};
    const probe = 'HKQuantityTypeIdentifierEngineClockProbe';
    const calls: Array<[string, (bridgeId: string) => Record<string, unknown>]> = [
      ['/api/integrations/healthkit/ingest', b => ({ bridgeId: b, samples: [{ type: probe, unit: '1', values: [0.5] }] })],
      ['/api/integrations/healthkit/scope', b => ({ bridgeId: b, action: 'resync', types: [probe] })],
      ['/api/integrations/healthkit/resync', b => ({ bridgeId: b, types: [probe], requestedBy: 'engine-clock-spec' })],
    ];
    for (const p of all.filter(q => q.clockPath === '/api/clock')) {
      const bridgeId = `engine-clock-${p.runtime}-${Date.now()}`;
      for (const [path, body] of calls) {
        const injected = (await clockOf(request, p)).clock.lamport + JUMP;
        const r = await request.post(`${p.url}${path}`, { data: body(bridgeId), headers: { ...auth, ...presented(injected) } });
        expect(r.status(), `${p.name} POST ${path}: answered, not refused for the header`).not.toBe(404);
        expect(stamped(p, r).lamport, `${p.name} POST ${path}: the reply is past the injection`).toBeGreaterThan(injected);
        expect((await clockOf(request, p)).clock.lamport, `${p.name} after POST ${path}`).toBeGreaterThan(injected);
      }
    }
  });
});
