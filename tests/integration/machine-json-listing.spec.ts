import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
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

const REPO_MACHINES_ROOT = join(dirname(fileURLToPath(import.meta.url)), '../..', 'machines');

/**
 * The corpus the running universe actually booted.
 *
 * `startUniverse.sh --machine-corpus=standard-deployment` materializes a 12-file
 * subset into MACHINE_CORPUS_WORK_DIR and points every engine at it. Comparing
 * `json/list` against this repo's full tree would then report ~1,300 files as
 * missing — a failure that says nothing about path-aware addressing, which is
 * what this suite exists to guard.
 *
 * Set MACHINES_CORPUS_DIR to the active corpus root (the directory containing
 * `machines/`, stamped as MACHINE_CORPUS_ACTIVE_DIR in
 * RealityEngine_CI/.universe-engine-selection). Defaults to the repo corpus,
 * which is correct for a full-corpus universe.
 */
const MACHINES_ROOT = process.env.MACHINES_CORPUS_DIR
  ? join(process.env.MACHINES_CORPUS_DIR, 'machines')
  : REPO_MACHINES_ROOT;

interface EngineInstance {
  id: string;
  runtime: string;
  re_url: string;
  status: string;
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

  test('nested energy machine resolves to the same identity on every engine', async ({ request }) => {
    const engines = await fetchEngines(request);
    test.skip(engines.length < 2, 'Need at least 2 engines for cross-engine identity parity');

    const corpusRelFiles = await collectCorpusRelFiles(MACHINES_ROOT);
    const nested = corpusRelFiles.find(f => f.startsWith('domains/energy/'));
    test.skip(!nested, 'No energy domain corpus files present');

    const basename = nested!.split('/').pop()!.replace(/\.json$/, '');
    const identities: Array<{ engine: string; id: string; name: string }> = [];
    for (const engine of engines) {
      const resp = await request.get(`${engine.re_url}/api/machines/json/${basename}`, { ignoreHTTPSErrors: true });
      expect(resp.ok(), `${engine.id} (${engine.runtime}) must load ${basename}`).toBeTruthy();
      const body = await resp.json();
      identities.push({
        engine: `${engine.id}/${engine.runtime}`,
        id: String(body.machine?.id ?? ''),
        name: String(body.machine?.name ?? ''),
      });
    }
    const ids = new Set(identities.map(i => i.id));
    const names = new Set(identities.map(i => i.name));
    expect(ids.size, `machine id must be identical across engines: ${JSON.stringify(identities)}`).toBe(1);
    expect(names.size, `machine name must be identical across engines: ${JSON.stringify(identities)}`).toBe(1);
  });
});

// Offline contract — load-by-basename is only sound while corpus filenames
// stay globally unique, so this runs even without live engines.
//
// Uniqueness is a property of the whole repo corpus, not of whatever subset a
// given universe booted, so this deliberately uses REPO_MACHINES_ROOT: a
// collision must be caught even when the running universe loaded neither file.
test.describe('Corpus Filename Uniqueness', () => {
  test('corpus filenames are unique across all directories', async () => {
    const corpusRelFiles = await collectCorpusRelFiles(REPO_MACHINES_ROOT);
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
