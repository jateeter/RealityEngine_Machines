import { test, expect } from '@playwright/test';

/**
 * Integration: PE sensor source registration via localAIStack lifespan hooks.
 * Verifies that sensors are registered in the Perception Engine after startup.
 */

const PE_URL = process.env.PE_BASE_URL ?? 'https://localhost:3004';
const LAS_URL = 'http://localhost:4000';

test.describe('PE Sensor Registration', () => {
  test('localAIStack API is healthy', async ({ request }) => {
    const resp = await request.get(`${LAS_URL}/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });

  test('PE has at least one sensor source registered', async ({ request }) => {
    const resp = await request.get(`${PE_URL}/api/sources`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const sensors = (body.sources ?? []).filter((s: any) => s.type === 'sensor');
    expect(sensors.length).toBeGreaterThan(0);
    console.log(`Registered sensor sources (${sensors.length}):`);
    sensors.forEach((s: any) => {
      const r = s.region ?? {};
      console.log(`  [${r.offset}:${r.offset + r.length}]  ${s.name}`);
    });
  });

  test('the RAG signal lanes are covered by contiguous sensors', async ({ request }) => {
    // Was: `RAG signal regions [64:72] are covered by a sensor`, checking for a
    // sensor at offset 64 or 68.
    //
    // The lanes moved. localAIStack's canonical layout puts RAG topology nodes
    // at [7464:7472] — "4 nodes x 2 bytes" — and the live PE agrees:
    //
    //   localai/rag/retrieve          [7464:7466]
    //   localai/rag/grade_documents   [7466:7468]
    //   localai/rag/generate          [7468:7470]
    //   localai/rag/rewrite_query     [7470:7472]
    //
    // So the sensors were there the whole time and the assertion was pointing
    // 7,400 cells away. It failed for months without anyone learning that the
    // RAG lanes were fine (RealityEngine_Machines#124).
    //
    // Re-anchored on the thing the test is actually about: the RAG lanes are
    // covered, contiguously, by one sensor per node. Names are stable; the
    // offsets belong to the region allocation and have already moved once.
    // Hardcoding the new number would only schedule the same failure again.
    const resp = await request.get(`${PE_URL}/api/sources`, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();

    const ragSensors = (body.sources ?? [])
      .filter((s: any) => s.type === 'sensor' && String(s.name ?? '').startsWith('localai/rag/'))
      .map((s: any) => ({ name: s.name, offset: s.region?.offset, length: s.region?.length }))
      .sort((a: any, b: any) => a.offset - b.offset);

    expect(
      ragSensors.length,
      `no localai/rag/* sensors registered; sensors present: ` +
      `${(body.sources ?? []).filter((s: any) => s.type === 'sensor').map((s: any) => s.name).join(', ')}`,
    ).toBeGreaterThan(0);

    // Contiguous: each lane begins where the previous one ended. A gap means a
    // node writes into space no sensor is watching, which is the condition this
    // test exists to catch — and it is checkable without knowing the base.
    for (let i = 1; i < ragSensors.length; i++) {
      const prev = ragSensors[i - 1];
      const cur = ragSensors[i];
      expect(
        cur.offset,
        `RAG lanes are not contiguous: ${prev.name} ends at ${prev.offset + prev.length}, ` +
        `${cur.name} starts at ${cur.offset}`,
      ).toBe(prev.offset + prev.length);
    }
  });

  test('sensor write is accepted by PE', async ({ request }) => {
    const resp = await request.post(
      `${PE_URL}/api/sensors/localai_rag_retrieval`,
      {
        data: { values: [1.0, 0.5, 0.0, 0.0] },
        ignoreHTTPSErrors: true,
      }
    );
    // 200 OK with ok/id/success/updated, or 404 if not yet registered (non-fatal)
    if (resp.ok()) {
      const body = await resp.json();
      const accepted = body.ok || body.id || body.success || body.updated;
      expect(accepted).toBeTruthy();
    } else {
      expect([200, 404]).toContain(resp.status());
      console.log('Sensor not yet registered — will appear after first RAG query');
    }
  });
});
