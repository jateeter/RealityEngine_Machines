import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
import { deployed, requireService } from '../support/deployed-endpoints.js';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * Multi-instance integration tests.
 *
 * These tests require at least two engine instances in the registry
 * (RE_REGISTRY_URL env var must be set and the universe must have been
 * started with --engines=<two or more instances>).
 *
 * Universes are routinely started with one, two, three or more engines. With
 * fewer than two there is nothing to compare, so the multi-engine tests skip and
 * say why rather than failing (RealityEngine_Machines#126); a deployment gate
 * must not score a one-engine footprint as a defect. What holds for any number of
 * engines (every listed instance is well-formed) still runs.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';

interface EngineInstance {
  id: string;
  runtime: string;
  re_url: string;
  pe_url: string;
  status: string;
}

async function fetchRegistry(request: APIRequestContext): Promise<EngineInstance[]> {
  if (!REGISTRY_URL) return [];
  try {
    const resp = await request.get(REGISTRY_URL);
    if (!resp.ok()) return [];
    const body = await resp.json() as { instances?: EngineInstance[] };
    return body.instances ?? [];
  } catch { return []; }
}

test.describe('Multi-Engine Instance Tests', () => {
  test.skip(() => !REGISTRY_URL, 'RE_REGISTRY_URL not set — skipping multi-engine tests');

  test('every registry instance is well-formed', async ({ request }) => {
    const instances = await fetchRegistry(request);
    expect(instances.length, 'Registry must list at least one instance').toBeGreaterThanOrEqual(1);
    for (const inst of instances) {
      expect(inst.id).toBeTruthy();
      expect(inst.re_url).toMatch(/^https?:\/\//);
      expect(inst.status).toBe('running');
    }
  });

  test('registry lists at least two instances', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, `one-engine deployment (${instances.length} listed): multi-engine conformance is not applicable`);
    expect(instances.length).toBeGreaterThanOrEqual(2);
  });

  test('all instances have distinct RE ports', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, 'Need at least 2 instances to test port uniqueness');

    const rePorts = instances.map(i => new URL(i.re_url).port);
    const unique = new Set(rePorts);
    expect(unique.size).toBe(instances.length);
  });

  test('each instance /api/health responds independently', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, 'Need at least 2 instances for independence test');

    const results = await Promise.all(
      instances.map(async inst => {
        try {
          const resp = await request.get(`${inst.re_url}/api/health`);
          return { id: inst.id, ok: resp.ok() };
        } catch {
          return { id: inst.id, ok: false };
        }
      })
    );
    for (const r of results) {
      expect(r.ok, `Instance '${r.id}' health check failed`).toBeTruthy();
    }
  });

  test('Manager /api/engines returns all registry instances', async ({ request }) => {
    const registryInstances = await fetchRegistry(request);
    test.skip(registryInstances.length < 2, 'Need at least 2 instances for multi-engine manager conformance');

    const resp = await request.get(`${requireService((await deployed(request)).managerBackend, 'Manager backend')}/api/engines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json() as { instances: EngineInstance[]; activeId: string | null };
    expect(Array.isArray(body.instances)).toBeTruthy();
    expect(typeof body.activeId === 'string' || body.activeId === null).toBeTruthy();
  });

  test('Manager can switch active instance', async ({ request }) => {
    const instances = await fetchRegistry(request);
    test.skip(instances.length < 2, 'Need at least 2 instances to test switching');

    // Get current active
    const beforeResp = await request.get(`${requireService((await deployed(request)).managerBackend, 'Manager backend')}/api/engines`, { ignoreHTTPSErrors: true });
    expect(beforeResp.ok()).toBeTruthy();
    const before = await beforeResp.json() as { activeId: string | null };

    // Switch to the second instance
    const target = instances.find(i => i.id !== before.activeId) ?? instances[1];
    const switchResp = await request.post(`${requireService((await deployed(request)).managerBackend, 'Manager backend')}/api/engines/active`, {
      data: { id: target.id },
      ignoreHTTPSErrors: true,
    });
    expect(switchResp.ok(), `Switch to '${target.id}' failed`).toBeTruthy();
    const switched = await switchResp.json() as { activeId: string };
    expect(switched.activeId).toBe(target.id);

    // Restore original
    if (before.activeId) {
      await request.post(`${requireService((await deployed(request)).managerBackend, 'Manager backend')}/api/engines/active`, {
        data: { id: before.activeId },
        ignoreHTTPSErrors: true,
      });
    }
  });

  test('instances of one runtime have independent machine state', async ({ request }) => {
    // The pair is chosen by the registry's runtime field, never by position.
    // Registry order is --engines= order, so `const [a, b] = instances` compared
    // scala-1 with scala-2 under scala:2,lsp:1,cpp:1 and scala-1 with lsp-1
    // under scala:1,lsp:1,cpp:2, and passed either way (RealityEngine_CI#274).
    const running = (await fetchRegistry(request)).filter(i => i.status === 'running');
    const byRuntime = new Map<string, EngineInstance[]>();
    for (const inst of running) {
      byRuntime.set(inst.runtime, [...(byRuntime.get(inst.runtime) ?? []), inst]);
    }
    const groups = [...byRuntime].filter(([, list]) => list.length >= 2)
      .sort(([a], [b]) => a.localeCompare(b));
    const composition = [...byRuntime].map(([rt, list]) => `${rt}:${list.length}`).sort().join(', ');
    test.skip(groups.length === 0,
      `no runtime has two instances (${composition || 'none'}): same-runtime isolation is not applicable`);

    // A machine no deployment holds: a corpus machine renamed, with no
    // perceptualMapping and no inputSequences, so it occupies no region and
    // interns no PE test source (SURFACE_SPEC.md, "POST /api/machines always
    // ingests"). DELETE frees the name and leaves the instance as it was.
    const corpusFile = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'machines',
      'domains', 'agriculture', 'AGX001_aquaculture-water-quality-stability.json');
    const template = JSON.parse(readFileSync(corpusFile, 'utf8')) as { machine: Record<string, unknown> };

    // Membership is read by id, not from the GET /api/machines list: C++
    // lists from its running perceptual space, which a machine with no
    // perceptualMapping never enters, so the list omits it there while LSP and
    // Scala include it. GET /api/machines/:id answers for it on every runtime.
    const holds = async (inst: EngineInstance, id: string): Promise<boolean> => {
      const resp = await request.get(`${inst.re_url}/api/machines/${encodeURIComponent(id)}`);
      expect([200, 404], `${inst.id} GET /api/machines/${id} answered ${resp.status()}`)
        .toContain(resp.status());
      return resp.status() === 200;
    };

    for (const [runtime, [probe, ...others]] of groups) {
      test.info().annotations.push({ type: 'compared',
        description: `${runtime}: ${probe.id} vs ${others.map(o => o.id).join(', ')}` });
      const name = `zz-isolation-probe-${runtime}-${Date.now()}`;
      const { perceptualMapping: _pm, inputSequences: _is, ...machine } = template.machine;
      const created = await request.post(`${probe.re_url}/api/machines`,
        { data: { ...template, machine: { ...machine, name } } });
      expect(created.ok(), `${probe.id} POST /api/machines: ${created.status()} ${await created.text()}`).toBeTruthy();
      const id = ((await created.json()) as { machine?: { id?: string } }).machine?.id;
      expect(id, `${probe.id} POST /api/machines returned no machine id`).toBeTruthy();
      try {
        expect(await holds(probe, id!), `${probe.id} does not hold the machine it just ingested`).toBeTruthy();
        // Ids are minted per instance, so with separate state no other instance
        // can resolve this one; with shared state every one would.
        for (const other of others) {
          expect(await holds(other, id!),
            `${runtime}: machine ${id} ingested on ${probe.id} resolves on ${other.id}; instances of one runtime share machine state`)
            .toBeFalsy();
        }
      } finally {
        const removed = await request.delete(`${probe.re_url}/api/machines/${encodeURIComponent(id!)}`);
        expect(removed.ok(), `${probe.id} DELETE /api/machines/${id}`).toBeTruthy();
      }
      expect(await holds(probe, id!), `${probe.id} still holds the probe after DELETE`).toBeFalsy();
    }
  });
});
