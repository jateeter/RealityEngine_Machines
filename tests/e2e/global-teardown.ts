import { FullConfig } from '@playwright/test';

async function globalTeardown(_config: FullConfig) {
  console.log('Running global E2E test teardown...');

  if (process.env.REUSE_SERVICES === 'true') {
    console.log('Services managed externally (REUSE_SERVICES=true), skipping shutdown');
  } else if (process.env.CI) {
    console.log('Stopping universe (CI mode)...');
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);
    try {
      await execAsync('cd ../RealityEngine_CI && ./stopUniverse.sh');
      console.log('Universe stopped');
    } catch (error) {
      console.error('Failed to stop universe:', error);
    }
  } else {
    console.log('Leaving services running for local development');
  }

  console.log('Teardown complete');
}

export default globalTeardown;
