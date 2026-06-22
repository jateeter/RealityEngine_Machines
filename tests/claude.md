# RealityEngine_Machines Tests Guidance

This directory contains corpus contract, smoke, integration, and e2e tests.

- Prefer `RE_REGISTRY_URL` for multi-engine live tests.
- Use `RE_BASE_URL` and `PE_BASE_URL` for single-engine fallback.
- Keep stale fixture expectations separate from live endpoint evidence.
- When failures differ by engine, report corpus count, source count, identity-key parity, and byte equality separately.

