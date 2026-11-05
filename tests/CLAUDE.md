# RealityEngine_Machines Tests Guidance

This directory contains corpus contract, smoke, integration, and e2e tests.

- Prefer `RE_REGISTRY_URL` for multi-engine live tests.
- Use `RE_BASE_URL` and `PE_BASE_URL` for single-engine fallback.
- Keep stale fixture expectations separate from live endpoint evidence.
- When failures differ by engine, report corpus count, source count, identity-key parity, and byte equality separately.

## Standing rules

The standing rules are in
`../../RealityEngine_CI/docs/ENGINEERING_CONTRACT.md`, which is
authoritative. They are not listed or summarised here, so this file never
falls behind the contract. Read it before changing anything here.
