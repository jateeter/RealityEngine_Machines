/**
 * POST /api/machines keeps a declared id — 3-of-3 (SURFACE_SPEC, "POST
 * /api/machines keeps a declared id"; owner decision 2026-10-18).
 *
 * A machine loaded at runtime whose body declares an id must be ingested under
 * that id on every engine when no resident machine holds it, and must get a
 * minted id — never replacing the resident machine — when one does. Before
 * this, C++ and Scala minted for every POST and LSP reused a held id, so a
 * runtime-loaded machine had a different identity on each engine, and an LSP
 * re-post replaced the resident machine. The regression corpus never reaches
 * this (none of its machines declares an id); dynamic loading does.
 *
 * Every engine is posted the same body, and the outcomes must agree: the rule
 * is compared, not any one engine's answer (no reference member).
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

const RUN = Date.now().toString(36);
const DECLARED = `quorum-declared-id-${RUN}`;
const NAME = `Quorum Declared Id ${RUN}`;

function machineBody(): Record<string, unknown> {
  return {
    version: '1.0.0',
    machine: {
      id: DECLARED,
      name: NAME,
      arbiterRule: 'PASSTHROUGH',
      perceptualMapping: { input: { offset: 0, length: 4 }, output: { offset: 100, length: 2 } },
      sequences: [{
        id: `seq-${RUN}`, name: 'Declared Seq',
        events: [{ id: `v-${RUN}`, name: 'A', isInitial: true,
                   elements: [{ value: 1 }, { value: 0 }, { value: 0 }, { value: 0 }] }],
      }],
    },
  };
}

test.describe('POST /api/machines keeps a declared id (3-of-3)', () => {
  test('a free declared id is kept; a held one is minted and the resident machine untouched', async ({ request }) => {
    test.skip(!REGISTRY_URL, 'RE_REGISTRY_URL not set');
    const engines = await natives(request);
    const missing = NATIVES.filter(rt => !engines.has(rt));
    test.skip(missing.length > 0, `not applicable: 3-of-3 needs cpp, lsp and scala; this deployment lacks ${missing.join(', ')}`);

    const outcomes = new Map<Runtime, string>();
    const created: Array<[string, string]> = [];
    try {
      for (const rt of NATIVES) {
        const re = engines.get(rt)!.re_url;
        const first = await request.post(`${re}/api/machines`, { data: machineBody(), timeout: 60_000 });
        expect(first.ok(), `${rt} first POST`).toBe(true);
        const firstId = (await first.json()).machine.id as string;
        created.push([re, firstId]);

        const second = await request.post(`${re}/api/machines`, { data: machineBody(), timeout: 60_000 });
        expect(second.ok(), `${rt} second POST`).toBe(true);
        const s = (await second.json()).machine as { id: string; name: string };
        created.push([re, s.id]);

        const resident = await request.get(`${re}/api/machines/${encodeURIComponent(DECLARED)}`);
        const residentName = resident.ok()
          ? ((await resident.json()).machine ?? {}).name : `(GET ${resident.status()})`;

        outcomes.set(rt, JSON.stringify({
          firstKeptDeclared: firstId === DECLARED,
          secondMinted: s.id !== DECLARED && /^machine-/.test(s.id),
          secondVersioned: s.name === `${NAME} v2`,
          residentUntouched: residentName === NAME,
        }));
      }
    } finally {
      for (const [re, id] of created.reverse()) {
        await request.delete(`${re}/api/machines/${encodeURIComponent(id)}`).catch(() => undefined);
      }
    }

    const report = [...outcomes].map(([rt, o]) => `  ${rt.padEnd(5)} ${o}`).join('\n');
    expect(new Set(outcomes.values()).size, `disagreement (3-of-3, no reference member)\n${report}`).toBe(1);
    expect(JSON.parse([...outcomes.values()][0]!), `the rule\n${report}`).toEqual({
      firstKeptDeclared: true, secondMinted: true, secondVersioned: true, residentUntouched: true,
    });
  });
});
