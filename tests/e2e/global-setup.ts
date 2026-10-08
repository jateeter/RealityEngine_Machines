import { FullConfig } from '@playwright/test';
import { registryUrl as resolveRegistryUrl } from '../support/registry-url.js';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function globalSetup(_config: FullConfig) {
  // Skip Docker service checks in multi-engine native mode or when explicitly
  // bypassed (e.g. in the multi-engine-tests CI job where Docker RE/PE are
  // not running and tests use RE_REGISTRY_URL instead).
  if (process.env.SKIP_GLOBAL_SETUP === 'true' || process.env.RE_REGISTRY_URL) {
    console.log('Global setup: skipping Docker service wait (SKIP_GLOBAL_SETUP or RE_REGISTRY_URL set)');
    return;
  }
  console.log('Starting global E2E test setup...');
  await waitForServices();
  console.log('All services are ready!');
}

// The deployed endpoints, never Docker-lane literals: the instance registry
// (both lanes publish one since RealityEngine_CI#363) or the env overrides. With
// neither there is nothing to wait for, and guessing ports would only make the
// wait fail later against addresses nothing is bound to (RealityEngine_Machines#126).
async function deployedServices(): Promise<Array<{ name: string; url: string }>> {
  const registryUrl = resolveRegistryUrl();
  let reg: any = {};
  try {
    const { stdout } = await execAsync(`curl -kfsS --max-time 5 "${registryUrl}"`);
    reg = JSON.parse(stdout);
  } catch { /* no registry: env overrides only */ }
  const inst = (reg.instances ?? [])[0] ?? {};
  const svc = (n: string) => reg.services?.[n]?.url;
  const candidates = [
    { name: 'Reality Engine',      base: process.env.RE_BASE_URL ?? inst.re_url,              path: '/api/health' },
    { name: 'Perception Engine',   base: process.env.PE_BASE_URL ?? inst.pe_url,              path: '/api/health' },
    { name: 'Visualizer Backend',  base: process.env.VIZ_BASE_URL ?? svc('manager_backend'),  path: '/health' },
    { name: 'Visualizer Frontend', base: process.env.VIZ_FRONTEND_URL ?? svc('manager_frontend'), path: '/' },
    { name: 'localAIStack API',    base: process.env.LAS_BASE_URL ?? svc('localai_api'),      path: '/health' },
  ];
  return candidates.filter(c => c.base).map(c => ({ name: c.name, url: `${c.base}${c.path}` }));
}

async function waitForServices() {
  const services = await deployedServices();
  if (services.length === 0) {
    console.log('Global setup: no deployment published (no instance registry, no *_BASE_URL); nothing to wait for');
    return;
  }

  const maxRetries = 60;
  const delayMs = 2000;

  for (const service of services) {
    let healthy = false;
    for (let retries = 0; retries < maxRetries; retries++) {
      try {
        await execAsync(`curl -kfsS "${service.url}" > /dev/null`);
        console.log(`  ${service.name} is healthy`);
        healthy = true;
        break;
      } catch {
        if (retries === 0 || (retries + 1) % 10 === 0) {
          console.log(`  Waiting for ${service.name} (${retries + 1}/${maxRetries})`);
        }
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
    if (!healthy) {
      throw new Error(`${service.name} failed to become healthy after ${maxRetries} retries`);
    }
  }
}

export default globalSetup;
