# RealityEngine_Machines Corpus Guidance

This directory contains the canonical machine definitions consumed by every engine.

- Keep IDs, schema fields, triggers, and domain placement stable unless the change is intentional.
- Validate with `npm run validate` or stricter contract tests after corpus changes.
- Remember that C++, LSP, Scala, Manager, and localAIStack workflows may all consume this data.
- Use JSON schema support when editing machine files.

## Standing rules

The standing rules are in
`../../RealityEngine_CI/docs/ENGINEERING_CONTRACT.md`, which is
authoritative. They are not listed or summarised here, so this file never
falls behind the contract. Read it before changing anything here.
