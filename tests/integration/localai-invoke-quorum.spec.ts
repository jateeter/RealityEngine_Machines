import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';

/**
 * Integration: the localAI invoke surface agrees 3-of-3 — RealityEngine_CI
 * SURFACE_SPEC.md "localAI invoke contract" (INTEGRATION_ROADMAP.md §6 Q7/Q1,
 * RealityEngine_CI#445), held to docs/QUORUM_CONTRACT.md.
 *
 * Before it, each runtime kept its own allow-list: C++ nine operations exact,
 * LSP eight by prefix with "/" allowed, Scala an OpenAI-shaped list localAIStack
 * does not serve. The same request body reached different endpoints — or none —
 * depending on the runtime. No runtime is the reference: every case below must
 * produce the same answer on all three, or it is a disagreement.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const NATIVES = ['cpp', 'lsp', 'scala'] as const;
type Runtime = typeof NATIVES[number];
interface Instance { id: string; runtime: string; pe_url: string; status: string }

async function natives(request: APIRequestContext): Promise<Map<Runtime, Instance>> {
  const out = new Map<Runtime, Instance>();
  if (!REGISTRY_URL) return out;
  const resp = await request.get(REGISTRY_URL);
  if (!resp.ok()) return out;
  for (const i of ((await resp.json()) as { instances?: Instance[] }).instances ?? []) {
    if (i.status === 'running' && (NATIVES as readonly string[]).includes(i.runtime) && !out.has(i.runtime as Runtime)) {
      out.set(i.runtime as Runtime, i);
    }
  }
  return out;
}

function expectUnanimous(label: string, signatures: Map<Runtime, string>) {
  const report = [...signatures].map(([rt, sig]) => `  ${rt.padEnd(5)} ${sig}`).join('\n');
  expect(new Set(signatures.values()).size, `${label}: disagreement (3-of-3, no reference member)\n${report}`).toBe(1);
}

// Each case: a request body, and what is compared. Ids and the provider's own
// response body legitimately differ run to run, so they are reduced to presence.
const CASES: Array<[string, Record<string, unknown>]> = [
  ['allowed POST with payload', { endpoint: '/graphql', payload: { query: '{ __typename }' } }],
  ['method defaults from the allow-list', { path: '/graph/schema' }],
  ['query string ignored for matching', { endpoint: 'health?probe=1' }],
  ['unserved, unlisted path', { path: '/v1/models' }],
  ['"/" is not a wildcard', { endpoint: '/' }],
  ['method is part of the match', { endpoint: '/graphql', method: 'GET' }],
  ['no target', {}],
];

test.describe('localAI invoke quorum', () => {
  let engines: Map<Runtime, Instance>;

  test.beforeEach(async ({ request }) => {
    test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
    engines = await natives(request);
    const missing = NATIVES.filter(rt => !engines.has(rt));
    expect(missing, `3-of-3 needs all three native runtimes running; missing: ${missing.join(', ')}`).toEqual([]);
  });

  test('catalog: same key set and the same allow-list', async ({ request }) => {
    const sigs = new Map<Runtime, string>();
    for (const rt of NATIVES) {
      const r = await request.get(`${engines.get(rt)!.pe_url}/api/integrations/localai/catalog`);
      expect(r.ok(), `${rt} GET /api/integrations/localai/catalog`).toBe(true);
      const d = await r.json() as Record<string, unknown>;
      sigs.set(rt, JSON.stringify({ keys: Object.keys(d).sort(), allowedEndpoints: d.allowedEndpoints }));
    }
    expectUnanimous('localai catalog', sigs);
    const allowed = JSON.parse([...sigs.values()][0]!).allowedEndpoints as unknown[];
    expect(allowed.length, 'no allow-list configured: every runtime would refuse everything').toBeGreaterThan(0);
  });

  for (const [label, body] of CASES) {
    test(`invoke: ${label}`, async ({ request }) => {
      const sigs = new Map<Runtime, string>();
      for (const rt of NATIVES) {
        const r = await request.post(`${engines.get(rt)!.pe_url}/api/integrations/localai/invoke`, { data: body });
        const d = await r.json() as Record<string, unknown>;
        const reduced = Object.fromEntries(Object.entries(d).map(([k, v]) =>
          ['correlationId', 'invocationId', 'response'].includes(k) ? [k, '<present>'] : [k, v]));
        const sorted = Object.fromEntries(Object.keys(reduced).sort().map(k => [k, reduced[k]]));
        sigs.set(rt, JSON.stringify({ status: r.status(), body: sorted }));
      }
      expectUnanimous(`invoke ${label}`, sigs);
    });
  }
});
