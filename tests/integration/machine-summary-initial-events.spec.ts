import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';

/**
 * Integration: initialEventIds on the machine *summary* form.
 *
 * `GET /api/machines` returns the summary projection of every machine, and each
 * sequence in it must carry `initialEventIds` alongside `id` and `name`. The
 * Scala Perception Engine builds its machine corpus from this endpoint and reads
 * that key in MachineCorpus.scala `provenance()`, which ends
 * `.toOption.getOrElse(Vector.empty)` — so an engine that omits it hands the PE
 * an empty audit trail and raises nothing, in contradiction of that method's own
 * documented expectation that a fired sequence yields a non-empty one.
 *
 * Presence is asserted before agreement, and that order is the point. Three
 * engines that all omit the key agree perfectly, so an agreement-only check
 * passes on exactly the corpus-wide silence this suite exists to catch.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const RE_URL = process.env.RE_BASE_URL ?? '';

interface EngineInstance {
  id: string;
  runtime: string;
  re_url: string;
  status: string;
}

interface SummarySequence {
  id?: string;
  name?: string;
  initialEventIds?: string[];
}

interface SummaryMachine {
  id?: string;
  name?: string;
  sequences?: SummarySequence[];
}

async function fetchEngines(request: APIRequestContext): Promise<EngineInstance[]> {
  if (REGISTRY_URL) {
    try {
      const resp = await request.get(REGISTRY_URL);
      if (resp.ok()) {
        const body = await resp.json() as { instances?: EngineInstance[] };
        const running = (body.instances ?? []).filter(i => i.status === 'running');
        if (running.length > 0) return running;
      }
    } catch { /* fall through to RE_BASE_URL */ }
  }
  if (RE_URL) return [{ id: 'single', runtime: 'unknown', re_url: RE_URL, status: 'running' }];
  return [];
}

async function fetchSummaryMachines(request: APIRequestContext, engine: EngineInstance): Promise<SummaryMachine[]> {
  const resp = await request.get(`${engine.re_url}/api/machines`, { ignoreHTTPSErrors: true });
  expect(resp.ok(), `${engine.id} (${engine.runtime}) GET /api/machines must respond`).toBeTruthy();
  const body = await resp.json();
  return Array.isArray(body) ? body : (body.machines ?? body.data ?? []);
}

test.describe('Machine Summary Initial Events', () => {
  test.skip(() => !REGISTRY_URL && !RE_URL, 'Neither RE_REGISTRY_URL nor RE_BASE_URL set — skipping live summary tests');

  test('every engine emits initialEventIds on every summary sequence', async ({ request }) => {
    const engines = await fetchEngines(request);
    test.skip(engines.length === 0, 'No running engines available');

    for (const engine of engines) {
      const machines = await fetchSummaryMachines(request, engine);
      expect(machines.length, `${engine.id} (${engine.runtime}) must report a non-empty corpus`).toBeGreaterThan(0);

      const missing: string[] = [];
      let sequenceCount = 0;
      for (const machine of machines) {
        for (const seq of machine.sequences ?? []) {
          sequenceCount++;
          if (!Array.isArray(seq.initialEventIds)) {
            missing.push(`${machine.name ?? machine.id}/${seq.id ?? seq.name}`);
          }
        }
      }

      expect(sequenceCount, `${engine.id} (${engine.runtime}) corpus must contain sequences for this test to mean anything`).toBeGreaterThan(0);
      if (missing.length > 0) {
        console.error(`[${engine.id}/${engine.runtime}] summary sequences without initialEventIds: ${missing.slice(0, 5).join(', ')}${missing.length > 5 ? ` … +${missing.length - 5}` : ''}`);
      }
      expect(missing, `${engine.id} (${engine.runtime}) omits initialEventIds on ${missing.length}/${sequenceCount} summary sequences`).toHaveLength(0);
    }
  });

  test('summary initialEventIds agree across engines, in the same order', async ({ request }) => {
    const engines = await fetchEngines(request);
    test.skip(engines.length < 2, 'Need at least 2 engines for cross-engine parity');

    // Keyed by machine name + sequence id: ids are generated per runtime, so
    // they are not comparable across engines, but the corpus names are.
    const perEngine = new Map<string, Map<string, string[]>>();
    for (const engine of engines) {
      const machines = await fetchSummaryMachines(request, engine);
      const byKey = new Map<string, string[]>();
      for (const machine of machines) {
        for (const seq of machine.sequences ?? []) {
          byKey.set(`${machine.name ?? ''}::${seq.id ?? seq.name ?? ''}`, seq.initialEventIds ?? []);
        }
      }
      perEngine.set(`${engine.id}/${engine.runtime}`, byKey);
    }

    const allKeys = new Set<string>();
    for (const byKey of perEngine.values()) for (const k of byKey.keys()) allKeys.add(k);
    expect(allKeys.size, 'engines must report sequences to compare').toBeGreaterThan(0);

    // Order matters as much as membership: the engines sort initial event ids
    // so a majority comparison has something to agree on (RealityEngine_CI#197).
    const disagreements: string[] = [];
    for (const key of allKeys) {
      const rendered = [...perEngine.entries()].map(
        ([label, byKey]) => `${label}=${JSON.stringify(byKey.get(key) ?? null)}`,
      );
      const distinct = new Set(rendered.map(r => r.split('=').slice(1).join('=')));
      if (distinct.size > 1) disagreements.push(`${key}: ${rendered.join(' ')}`);
    }

    if (disagreements.length > 0) {
      console.error(`initialEventIds disagreements:\n  ${disagreements.slice(0, 5).join('\n  ')}`);
    }
    expect(disagreements, `${disagreements.length}/${allKeys.size} summary sequences disagree on initialEventIds`).toHaveLength(0);
  });
});
