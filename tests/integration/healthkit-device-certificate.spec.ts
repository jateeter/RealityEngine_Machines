import { test, expect, request as playwrightRequest } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
import { laneOn } from '../support/lane-tls.js';

/**
 * Per-source client certificates on the PE's device routes (owner, 2026-11-12;
 * RealityEngine_CI docs/TRANSPORT_SECURITY.md, "Per source on the device routes").
 *
 * Every source reaches the device routes on https; whether it must also present
 * a lane certificate is the source's: HEALTHKIT_CLIENT_CERTIFICATE_REQUIRED names
 * the sources that must (every lane sets `pim`). For every PE the instance
 * registry lists, voters and followers alike:
 *   - a listed source without a certificate gets 403 {"error":"client certificate required"};
 *   - the same request with the harness certificate is served;
 *   - an unlisted source (a phone's bridge) is served without one.
 * A device request names its source in the `bridgeId` query parameter here
 * (GET …/healthkit/status), which every PE reads first.
 *
 * Lane only: over plaintext there are no certificates to ask for.
 */

const REGISTRY_URL = process.env.RE_REGISTRY_URL ?? '';
const LISTED = (process.env.HEALTHKIT_CLIENT_CERTIFICATE_REQUIRED ?? 'pim')
  .split(',').map((s) => s.trim()).filter(Boolean);
const STATUS = '/api/integrations/healthkit/status';

interface Instance { id: string; pe_url: string; status: string }

async function instances(request: APIRequestContext): Promise<Instance[]> {
  const resp = await request.get(REGISTRY_URL);
  expect(resp.ok(), `instance registry at ${REGISTRY_URL}`).toBe(true);
  const body = await resp.json() as { instances?: Instance[] };
  return (body.instances ?? []).filter((i) => i.status === 'running' && i.pe_url);
}

test.describe('PE device routes: per-source client certificates', () => {
  test.skip(!laneOn(), 'lane TLS is off: no certificates to ask for');
  test.skip(!REGISTRY_URL, 'no instance registry (RE_REGISTRY_URL)');
  test.skip(LISTED.length === 0, 'HEALTHKIT_CLIENT_CERTIFICATE_REQUIRED names no source');

  test('a listed source needs a certificate on every PE; an unlisted one does not', async ({ request }) => {
    const pes = await instances(request);
    expect(pes.length).toBeGreaterThan(0);
    // No client certificate: a context of its own (the default presents the harness's).
    // clientCertificates: [] explicitly: the suite's config would otherwise give
    // every context the harness certificate for the registry's origins.
    const bare = await playwrightRequest.newContext({ ignoreHTTPSErrors: false, clientCertificates: [] });
    try {
      for (const pe of pes) {
        const listed = `${pe.pe_url}${STATUS}?bridgeId=${encodeURIComponent(LISTED[0])}`;
        const refused = await bare.get(listed);
        expect(refused.status(), `${pe.id}: ${LISTED[0]} without a certificate`).toBe(403);
        expect(await refused.json(), pe.id).toEqual({ error: 'client certificate required' });
        expect((await request.get(listed)).status(), `${pe.id}: ${LISTED[0]} with the harness certificate`).toBe(200);
        const phone = await bare.get(`${pe.pe_url}${STATUS}?bridgeId=healthkit-ios-bridge-${pe.id}`);
        expect(phone.status(), `${pe.id}: an unlisted source without a certificate`).toBe(200);
      }
    } finally {
      await bare.dispose();
    }
  });
});
