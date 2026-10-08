import fs from 'node:fs';
import path from 'node:path';

/**
 * Where is the instance registry? The same order as RealityEngine_CI's
 * scripts/lib/registry-url.sh (and scripts/registry_url.py here):
 *
 *   1. RE_REGISTRY_URL, when set.
 *   2. RealityEngine_CI/.universe-registry-url — startUniverse.sh writes the
 *      address the running universe serves there; stopUniverse.sh removes it.
 *      The CI checkout is REALITY_ENGINE_CI_DIR, else the sibling directory
 *      (Playwright runs from this repo's root, as playwright.config.ts assumes).
 *   3. http://127.0.0.1:${RE_REGISTRY_PORT:-5999}/re-registry.json.
 *
 * 5999 is the shim's port only with fixed ports; under --free-ports it is
 * OS-assigned, and a literal :5999 fallback looked where nothing listened.
 */
export function registryUrl(): string {
  const env = process.env.RE_REGISTRY_URL?.trim();
  if (env) return env;
  const ciDir = process.env.REALITY_ENGINE_CI_DIR
    ?? path.resolve(process.cwd(), '..', 'RealityEngine_CI');
  try {
    const recorded = fs.readFileSync(path.join(ciDir, '.universe-registry-url'), 'utf8')
      .split('\n')[0].trim();
    if (recorded) return recorded;
  } catch {
    // No universe has recorded an address: fall through to the default.
  }
  return `http://127.0.0.1:${process.env.RE_REGISTRY_PORT ?? '5999'}/re-registry.json`;
}
