# RealityEngine_Machines Schema Guidance

This directory contains JSON schemas for machine and contract validation.

- Schema changes are cross-repo contract changes.
- Update tests, docs, and affected engine loaders together.
- Use JSON schema-aware editing.
- Verify with contract and validation commands before considering a schema change complete.
- The K-line records (RealityEngine_CI#603): `re-kline.schema.json` (RE half),
  `re-kline-event.schema.json` (`sustain-end`) and `re-isre-composition.schema.json`
  (PE half), sharing `kline-defs.schema.json`. `examples/klines/valid/` must pass
  and each file in `examples/klines/invalid/` (one defect each) must be refused;
  `scripts/validate-schemas.mjs` checks both. The bundle formats are not here yet.

## Standing rules

The standing rules are in
`../../RealityEngine_CI/docs/ENGINEERING_CONTRACT.md`, which is
authoritative. They are not listed or summarised here, so this file never
falls behind the contract. Read it before changing anything here.
