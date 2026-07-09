import { test, expect } from '@playwright/test';
import { readdir } from 'fs/promises';
import { join, dirname, relative } from 'path';
import { fileURLToPath } from 'url';

/**
 * Integration: on-disk machine JSON listing parity.
 *
 * Every engine's GET /api/machines/json/list must enumerate the full corpus
 * recursively — including files in domain subdirectories
 * (machines/domains/<name>/) — and GET /api/machines/json/:name must load a
 * domain-nested file by basename. Guards the path-aware addressing contract
 * so a new domain directory cannot silently vanish from any engine surface.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const RE_URL = process.env.RE_BASE_URL ?? '';
const MACHINES_ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..', 'machines');

interface EngineInstance {
  id: string;
  runtime: string;
  re_url: string;
  status: string;
}

async function fetchEngines(request: Parameters<Parameters<typeof test>[1]>[0]['request']): Promise<EngineInstance[]> {
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

async function collectCorpusRelFiles(dir: string, root = dir): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true }).catch(() => []);
  const files: string[] = [];
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await collectCorpusRelFiles(full, root));
    } else if (entry.name.endsWith('.json')) {
      files.push(relative(root, full).split('\\').join('/'));
    }
  }
  return files;
}

test.describe('Machine JSON Listing Parity', () => {
  test.skip(() => !REGISTRY_URL && !RE_URL, 'Neither RE_REGISTRY_URL nor RE_BASE_URL set — skipping live listing tests');

  test('every engine json/list enumerates the corpus recursively with relFile', async ({ request }) => {
    const engines = await fetchEngines(request);
    test.skip(engines.length === 0, 'No running engines available');

    const corpusRelFiles = await collectCorpusRelFiles(MACHINES_ROOT);
    expect(corpusRelFiles.length).toBeGreaterThan(0);
    const nested = corpusRelFiles.filter(f => f.includes('/'));
    expect(nested.length, 'corpus must contain domain-nested files for this test to be meaningful').toBeGreaterThan(0);

    for (const engine of engines) {
      const resp = await request.get(`${engine.re_url}/api/machines/json/list`, { ignoreHTTPSErrors: true });
      expect(resp.ok(), `${engine.id} json/list must respond`).toBeTruthy();
      const body = await resp.json();
      const rows: any[] = body.machines ?? [];
      const relFiles = new Set(rows.map(r => String(r.relFile ?? r.filename)));

      const missing = corpusRelFiles.filter(f => !relFiles.has(f));
      if (missing.length > 0) {
        console.error(`[${engine.id}/${engine.runtime}] missing from json/list: ${missing.slice(0, 5).join(', ')}${missing.length > 5 ? ` … +${missing.length - 5}` : ''}`);
      }
      expect(missing, `${engine.id} (${engine.runtime}) json/list missing ${missing.length} corpus files`).toHaveLength(0);
    }
  });

  test('every engine loads a domain-nested machine file by basename', async ({ request }) => {
    const engines = await fetchEngines(request);
    test.skip(engines.length === 0, 'No running engines available');

    const corpusRelFiles = await collectCorpusRelFiles(MACHINES_ROOT);
    const nested = corpusRelFiles.find(f => f.includes('/'));
    test.skip(!nested, 'No domain-nested corpus files present');

    const basename = nested!.split('/').pop()!.replace(/\.json$/, '');
    for (const engine of engines) {
      const resp = await request.get(`${engine.re_url}/api/machines/json/${basename}`, { ignoreHTTPSErrors: true });
      expect(resp.ok(), `${engine.id} (${engine.runtime}) must load nested file ${basename} by basename`).toBeTruthy();
      const body = await resp.json();
      expect(body.success, `${engine.id} load response must report success`).toBeTruthy();
    }
  });
});

// Offline contract — load-by-basename is only sound while corpus filenames
// stay globally unique, so this runs even without live engines.
test.describe('Corpus Filename Uniqueness', () => {
  test('corpus filenames are unique across all directories', async () => {
    const corpusRelFiles = await collectCorpusRelFiles(MACHINES_ROOT);
    const seen = new Map<string, string>();
    const collisions: string[] = [];
    for (const rel of corpusRelFiles) {
      const base = rel.split('/').pop()!;
      const prev = seen.get(base);
      if (prev) collisions.push(`${base}: ${prev} vs ${rel}`);
      else seen.set(base, rel);
    }
    expect(collisions, `basename collisions break load-by-name: ${collisions.slice(0, 5).join('; ')}`).toHaveLength(0);
  });
});
