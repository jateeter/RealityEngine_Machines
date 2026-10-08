/**
 * Endpoints of the universe that is actually deployed.
 *
 * Specs used to fall back to Docker-lane literals (https://localhost:5001,
 * :3004, http://localhost:4000, :4333). Against a native universe the engines
 * listen on their allocated bands (cpp 53xx, lsp 56xx, scala 51xx), so those
 * specs probed ports nothing was bound to and failed (RealityEngine_Machines#126).
 *
 * Resolution, in order — never a literal port:
 *   1. an explicit env override (RE_BASE_URL / PE_BASE_URL are the single-engine
 *      contract; LAS_BASE_URL, QD_BASE_URL, VIZ_BASE_URL for services);
 *   2. the instance registry (registry-url.ts: RE_REGISTRY_URL, else the
 *      universe's recorded address): the first instance for the
 *      engine pair, and its `services` block for everything else, which
 *      startUniverse.sh publishes from what it actually brought up.
 * A service with neither is reported as not deployed.
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import { registryUrl } from './registry-url.js';

export const REGISTRY_URL = registryUrl();

export interface Instance {
  id: string;
  runtime: string;
  re_url: string;
  pe_url: string;
  status?: string;
}

export interface Deployed {
  instances: Instance[];
  re?: string;
  pe?: string;
  localai?: string;
  qdrant?: string;
  managerBackend?: string;
  managerFrontend?: string;
  openclaw?: string;
}

let cached: Promise<Deployed> | undefined;

async function load(request: APIRequestContext): Promise<Deployed> {
  let registry: { instances?: Instance[]; services?: Record<string, { url?: string }> } = {};
  try {
    const resp = await request.get(REGISTRY_URL, { timeout: 5_000 });
    if (resp.ok()) registry = await resp.json();
  } catch {
    // No registry: only explicit env overrides can say where anything is.
  }
  const instances = registry.instances ?? [];
  const svc = (name: string) => registry.services?.[name]?.url;
  return {
    instances,
    re: process.env.RE_BASE_URL ?? instances[0]?.re_url,
    pe: process.env.PE_BASE_URL ?? instances[0]?.pe_url,
    localai: process.env.LAS_BASE_URL ?? svc('localai_api'),
    qdrant: process.env.QD_BASE_URL ?? svc('qdrant'),
    managerBackend: process.env.VIZ_BASE_URL ?? svc('manager_backend'),
    managerFrontend: process.env.VIZ_FRONTEND_URL ?? svc('manager_frontend'),
    openclaw: process.env.OPENCLAW_GATEWAY_URL ?? svc('openclaw_gateway'),
  };
}

export function deployed(request: APIRequestContext): Promise<Deployed> {
  cached ??= load(request);
  return cached;
}

/** An engine endpoint is required: a live spec with no engine is a failure. */
export function requireEngine(url: string | undefined, what: 'RE' | 'PE'): string {
  expect(url, `no deployed ${what}: set ${what}_BASE_URL or start a universe that publishes ${REGISTRY_URL}`)
    .toBeTruthy();
  return url!;
}

/** A support service may legitimately be absent from a deployment: skip, saying so. */
export function requireService(url: string | undefined, what: string): string {
  test.skip(!url, `${what} is not deployed (no instance-registry service entry and no env override)`);
  return url!;
}
