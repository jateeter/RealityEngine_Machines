import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';

/**
 * Integration: GET /api/perceptual-simulation/state agrees 3-of-3 —
 * RealityEngine_CI SURFACE_SPEC.md "Perceptual simulation state"
 * (RealityEngine_CI#453), held to docs/QUORUM_CONTRACT.md.
 *
 * The payload is nested under `state` with exactly perceptualSpace,
 * currentStep, isRunning and machines. LSP returned it flat until
 * RealityEngine_LSP#140, and every consumer reading state.perceptualSpace saw
 * nothing from it. Scala's extra top-level `success: true` is permitted and
 * nothing else is.
 *
 * Read-only: no step, start or reset is issued, so the comparison is of the
 * engines' current state, not of a stimulus.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const NATIVES = ['cpp', 'lsp', 'scala'] as const;
const STATE_KEYS = ['currentStep', 'isRunning', 'machines', 'perceptualSpace'];
const TOP_LEVEL_ALLOWED = ['state', 'success'];

interface Instance { id: string; runtime: string; re_url: string; status: string }
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

function expectUnanimous(label: string, signatures: Map<Runtime, string>) {
  const distinct = new Set(signatures.values());
  const report = [...signatures].map(([rt, sig]) => `  ${rt.padEnd(5)} ${sig}`).join('\n');
  expect(distinct.size, `${label}: disagreement (3-of-3, no reference member)\n${report}`).toBe(1);
}

test.describe('perceptual simulation state quorum', () => {
  let engines: Map<Runtime, Instance>;
  const bodies = new Map<Runtime, Record<string, unknown>>();

  test.beforeEach(async ({ request }) => {
    engines = await natives(request);
    test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
    const missing = NATIVES.filter(rt => !engines.has(rt));
    expect(missing, `3-of-3 needs all three native runtimes running; missing: ${missing.join(', ')}`).toEqual([]);
    for (const rt of NATIVES) {
      const r = await request.get(`${engines.get(rt)!.re_url}/api/perceptual-simulation/state`, { timeout: 60_000 });
      expect(r.ok(), `${rt} GET /api/perceptual-simulation/state`).toBe(true);
      bodies.set(rt, await r.json() as Record<string, unknown>);
    }
  });

  test('payload is nested under "state" with the agreed keys', async () => {
    const keys = new Map<Runtime, string>();
    for (const rt of NATIVES) {
      const body = bodies.get(rt)!;
      const extra = Object.keys(body).filter(k => !TOP_LEVEL_ALLOWED.includes(k));
      expect(extra, `${rt} top-level keys outside {state, success}: flat payload?`).toEqual([]);
      if ('success' in body) expect(body.success, `${rt} success`).toBe(true);
      const state = body.state as Record<string, unknown> | undefined;
      expect(state && typeof state === 'object', `${rt} has no "state" object`).toBe(true);
      keys.set(rt, JSON.stringify(Object.keys(state!).sort()));
    }
    expectUnanimous('state key set', keys);
    expect(JSON.parse([...keys.values()][0]!)).toEqual(STATE_KEYS);
  });

  test('field types agree and the vector and machine list match', async () => {
    const types = new Map<Runtime, string>();
    const lengths = new Map<Runtime, string>();
    const names = new Map<Runtime, string>();
    for (const rt of NATIVES) {
      const s = bodies.get(rt)!.state as Record<string, unknown> | undefined;
      expect(s && typeof s === 'object', `${rt} has no "state" object`).toBe(true);
      if (!s) continue;
      types.set(rt, JSON.stringify([
        Number.isInteger(s.currentStep), typeof s.isRunning,
        Array.isArray(s.machines), Array.isArray(s.perceptualSpace),
        (s.perceptualSpace as unknown[]).every(v => typeof v === 'number'),
      ]));
      lengths.set(rt, String((s.perceptualSpace as unknown[]).length));
      names.set(rt, JSON.stringify((s.machines as Array<{ name?: string }>).map(m => m.name)));
    }
    expectUnanimous('field types [int step, isRunning type, machines[], perceptualSpace[], numeric]', types);
    expect(JSON.parse([...types.values()][0]!)).toEqual([true, 'boolean', true, true, true]);
    expectUnanimous('perceptualSpace length', lengths);
    expectUnanimous('machines (names, canonical order)', names);
  });
});
