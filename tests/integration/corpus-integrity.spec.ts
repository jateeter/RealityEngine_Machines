import { test, expect } from '@playwright/test';
import { readdir, readFile } from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

/**
 * Integration: Machine corpus integrity.
 * Every machine JSON in machines/ must be present in RE after seeding.
 */

const RE_URL = 'https://localhost:3000';
const MACHINES_ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../..', 'machines');

async function collectMachineFiles(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true }).catch(() => []);
  const files: string[] = [];
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await collectMachineFiles(full));
    } else if (entry.name.endsWith('.json')) {
      files.push(full);
    }
  }
  return files;
}

test.describe('Machine Corpus Integrity', () => {
  let corpusIds: string[] = [];

  test.beforeAll(async () => {
    const files = await collectMachineFiles(MACHINES_ROOT);
    for (const file of files) {
      try {
        const raw = await readFile(file, 'utf8');
        const machine = JSON.parse(raw);
        if (machine.id) corpusIds.push(machine.id);
      } catch {
        console.warn(`Could not parse ${file}`);
      }
    }
    console.log(`Corpus contains ${corpusIds.length} machine definitions`);
  });

  test('machines/ directory is non-empty', async () => {
    const files = await collectMachineFiles(MACHINES_ROOT);
    expect(files.length).toBeGreaterThan(0);
    console.log(`Found ${files.length} machine JSON files`);
  });

  test('every corpus machine is present in RE after seeding', async ({ request }) => {
    if (corpusIds.length === 0) {
      test.skip(true, 'No machine definitions found in machines/ — add JSON files to run this test');
      return;
    }

    const resp = await request.get(`${RE_URL}/api/machines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const reIds = new Set((body.machines ?? []).map((m: any) => m.id));

    const missing: string[] = corpusIds.filter(id => !reIds.has(id));
    if (missing.length > 0) {
      console.error(`Missing from RE: ${missing.join(', ')}`);
    }
    expect(missing).toHaveLength(0);
  });

  test('RE has at least as many machines as the corpus', async ({ request }) => {
    const resp = await request.get(`${RE_URL}/api/machines`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const total = (body.machines ?? []).length;
    console.log(`RE total machines: ${total}  corpus size: ${corpusIds.length}`);
    expect(total).toBeGreaterThanOrEqual(corpusIds.length);
  });
});
