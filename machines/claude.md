# RealityEngine_Machines Corpus Guidance

This directory contains the canonical machine definitions consumed by every engine.

- Keep IDs, schema fields, triggers, and domain placement stable unless the change is intentional.
- Validate with `npm run validate` or stricter contract tests after corpus changes.
- Remember that C++, LSP, Scala, Manager, and localAIStack workflows may all consume this data.
- Use JSON schema support when editing machine files.

