# RealityEngine_Machines Semantics Guidance

This directory holds the OWL semantic representation of machine behavior used
by verification and auditing in the RE and PE components. See
`docs/SEMANTIC_OWL_ROADMAP.md` for the rollout plan.

- `ontology/re-core.ttl`: core TBox — classes, properties, canonical action
  individuals (`re:actionCode`), RAG statuses, and audit axioms. This file is
  the single source of truth for the action vocabulary; add new action codes
  here (with the correct consequence class: Logging / Notification /
  Escalation) before generating ABoxes that use them.
- `abox/<domain>/<MachineFile>.ttl`: generated per-machine ABox files.
  **Never edit by hand** — regenerate with
  `python3 scripts/generate-owl.py --machine <json> --write`. Machine JSON
  stays the source of truth for behavior; drift is caught by
  `generate-owl.py --check` and `tests/contracts/owl_semantics_test.py`.
- Generated output must stay byte-deterministic; treat any nondeterminism in
  `scripts/generate-owl.py` as a bug.
- IRIs follow `https://realityengine.example.org/machines/<domain>/<stem>#`;
  file renames therefore change semantic identity and must be treated as
  contract changes.
