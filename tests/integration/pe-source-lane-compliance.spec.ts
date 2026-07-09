import { test, expect } from '@playwright/test';
import { readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

/**
 * Integration: external data-stream PE source lane compliance.
 *
 * Every region-bearing PE source mapping in the CI integrations config
 * (acp-<machine>-input-assessment entries generated for OpenClaw input
 * analysts, plus the fixed cross-service lanes) must write a lane the corpus
 * actually declares: either a machine's own input region or a lane recorded
 * in domains/region-allocation.json serviceLanes.
 *
 * Reads INTEGRATIONS_CONFIG when set, else the sibling
 * RealityEngine_CI/config/integrations.json; skips when neither exists.
 */

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..');
const MACHINES_ROOT = join(REPO_ROOT, 'machines');
const ALLOCATION = join(REPO_ROOT, 'domains', 'region-allocation.json');
const CONFIG_PATH =
  process.env.INTEGRATIONS_CONFIG && existsSync(process.env.INTEGRATIONS_CONFIG)
    ? process.env.INTEGRATIONS_CONFIG
    : join(REPO_ROOT, '..', 'RealityEngine_CI', 'config', 'integrations.json');

interface Region { offset: number; length: number }

async function collectMachineInputLanes(dir: string): Promise<Map<string, string[]>> {
  const lanes = new Map<string, string[]>();
  const entries = await readdir(dir, { withFileTypes: true }).catch(() => []);
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      for (const [k, v] of await collectMachineInputLanes(full)) {
        lanes.set(k, [...(lanes.get(k) ?? []), ...v]);
      }
    } else if (entry.name.endsWith('.json')) {
      try {
        const machine = JSON.parse(await readFile(full, 'utf8')).machine;
        const r: Region | undefined = machine?.perceptualMapping?.input;
        if (r && Number.isInteger(r.offset) && Number.isInteger(r.length)) {
          const key = `${r.offset}:${r.length}`;
          lanes.set(key, [...(lanes.get(key) ?? []), entry.name]);
        }
      } catch { /* non-machine JSON */ }
    }
  }
  return lanes;
}

test.describe('PE Source Lane Compliance', () => {
  test.skip(() => !existsSync(CONFIG_PATH), `integrations config not found at ${CONFIG_PATH}`);

  test('every region-bearing source mapping targets a declared lane', async () => {
    const config = JSON.parse(await readFile(CONFIG_PATH, 'utf8'));
    const mappings: any[] = Array.isArray(config.sourceMappings) ? config.sourceMappings : [];
    const regionMappings = mappings.filter(m => m?.region && Number.isInteger(m.region.offset));
    expect(regionMappings.length, 'config must carry region-bearing source mappings').toBeGreaterThan(0);

    const inputLanes = await collectMachineInputLanes(MACHINES_ROOT);
    const allocation = JSON.parse(await readFile(ALLOCATION, 'utf8'));
    const serviceLanes = new Set(
      (allocation.serviceLanes ?? []).map((l: any) => `${l.offset}:${l.length}`),
    );
    const reservedBands: Array<{ offset: number; length: number }> = allocation.reservedBands ?? [];
    const inReservedBand = (r: Region) =>
      reservedBands.some(b => r.offset >= b.offset && r.offset + r.length <= b.offset + b.length);

    const unmatched: string[] = [];
    for (const m of regionMappings) {
      const key = `${m.region.offset}:${m.region.length}`;
      if (!inputLanes.has(key) && !serviceLanes.has(key) && !inReservedBand(m.region)) {
        unmatched.push(`${m.id ?? '(no id)'} -> ${key}`);
      }
    }
    if (unmatched.length > 0) {
      console.error(`unmatched source-mapping lanes: ${unmatched.slice(0, 10).join(', ')}`);
    }
    expect(unmatched, `${unmatched.length} source mappings write undeclared lanes`).toHaveLength(0);
  });

  test('input-assessment mappings match their machine input lane exactly', async () => {
    const config = JSON.parse(await readFile(CONFIG_PATH, 'utf8'));
    const mappings: any[] = Array.isArray(config.sourceMappings) ? config.sourceMappings : [];
    const canon = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '');

    const byCanon = new Map<string, Region>();
    async function walk(dir: string): Promise<void> {
      for (const entry of await readdir(dir, { withFileTypes: true }).catch(() => [])) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) await walk(full);
        else if (entry.name.endsWith('.json')) {
          try {
            const machine = JSON.parse(await readFile(full, 'utf8')).machine;
            const r: Region | undefined = machine?.perceptualMapping?.input;
            if (r) byCanon.set(canon(entry.name.replace(/\.json$/, '')), r);
          } catch { /* ignore */ }
        }
      }
    }
    await walk(MACHINES_ROOT);

    const mismatched: string[] = [];
    let checked = 0;
    for (const m of mappings) {
      const match = /^acp-(.+)-input-assessment$/.exec(String(m?.id ?? ''));
      if (!match || !m.region) continue;
      const lane = byCanon.get(canon(match[1]));
      if (!lane) continue; // shortened ids are covered by the declared-lane test
      checked++;
      if (lane.offset !== m.region.offset || lane.length !== m.region.length) {
        mismatched.push(`${m.id}: mapping ${m.region.offset}:${m.region.length} != machine input ${lane.offset}:${lane.length}`);
      }
    }
    expect(checked, 'must resolve a meaningful number of input-assessment mappings').toBeGreaterThan(100);
    expect(mismatched, mismatched.slice(0, 5).join('; ')).toHaveLength(0);
  });
});
