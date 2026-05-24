import { FullConfig } from '@playwright/test';
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

async function waitForServices() {
  const services = [
    { name: 'Reality Engine',       url: 'https://localhost:3000/api/health' },
    { name: 'Visualizer Backend',   url: 'https://localhost:3001/health' },
    { name: 'Visualizer Frontend',  url: 'https://localhost:5173/' },
    { name: 'Perception Engine',    url: 'https://localhost:3004/api/health' },
    { name: 'localAIStack API',     url: 'http://localhost:4000/health' },
  ];

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
