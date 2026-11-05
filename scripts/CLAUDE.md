# RealityEngine_Machines Scripts Guidance

This directory contains corpus validation, backfill, and maintenance scripts.

- Keep scripts deterministic and explicit about input/output paths.
- Avoid rewriting large corpus areas without a clear user request.
- Prefer live checks that resolve engines from the instance registry (`RE_REGISTRY_URL`) when scripts validate runtime behavior.
- Use TypeScript or Bash language servers as appropriate.

## Standing rules

The standing rules are in
`../../RealityEngine_CI/docs/ENGINEERING_CONTRACT.md`, which is
authoritative. They are not listed or summarised here, so this file never
falls behind the contract. Read it before changing anything here.
