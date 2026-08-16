# RealityEngine_Machines Semantics Guidance

This directory holds the OWL semantic representation of machine behavior used
by verification and auditing in the RE and PE components. See
`docs/SEMANTIC_OWL_ROADMAP.md` for the rollout plan.

- `ontology/re-core.ttl`: core TBox — classes, properties, canonical action
  individuals (`re:actionCode`), RAG statuses, autonomy modes, the agent
  vocabulary, and audit axioms. This file is the single source of truth for the
  action vocabulary; add new action codes here (with the correct consequence
  class: Logging / Notification / Escalation) before generating ABoxes that use
  them.
- Agent vocabulary (`0.2.0`): `re:Agent`, `re:AgentFamily`, `re:AgentBinding`,
  `re:AutonomyMode`, `re:SemanticAxis`, `re:CompletionMapping`,
  `re:ResponseMapping`. It models both axes the corpus binds agents on — the
  per-machine assessment written into the machine's own input region, and the
  role-level completion written into the reserved band. `re:autonomyMode` values
  must stay in step with the enum in `schemas/agent-binding.schema.json`.
  `re:axisName` is functional on purpose: one region position carries one
  meaning, so two sources naming it differently is an inconsistency rather than
  a variant spelling. `generate-owl.py` does not emit these individuals yet;
  the vocabulary is declared ahead of the generator.
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

## The ROBOT report profile, and its two deliberate INFOs

`robot-report-profile.txt` lists all 32 rules ROBOT ships rather than expressing
a delta, so a rule cannot be disabled by omission (#46). Two of them report
against this ontology permanently, and that is a decision rather than a backlog:

- **`missing_definition` (120)** looks for a definition annotation property
  (`IAO:0000115` by convention). This ontology documents with `rdfs:comment`
  instead, and every class carries one — asserted by
  `owl_semantics_test.test_every_class_is_documented`. Properties are described
  by label, domain and range; requiring prose for each would add ~104
  restatements of the obvious.
- **`missing_superclass` (16)** wants every class under an upper ontology (BFO
  or similar). These 16 are the vocabulary's root concepts — `re:Machine`,
  `re:Determination`, `re:Action` and so on. Introducing a vacuous `re:Entity`
  to satisfy a linter would add a layer carrying no information.

Both are OBO Foundry publishing conventions, and this is not a published OBO
ontology. `ERROR` and `WARN` are both zero and should stay that way; a new
violation at either level is a real defect.

The escalation invariant — an emergency-path action may only be prescribed by a
`RED` determination — is the reason `reason-owl.sh` runs HermiT and not ELK
alone. ELK does not implement the constructs it relies on and passes a corpus
that violates it. Verified: asserting `re:UrgentIntervention` on a `GREEN`
determination makes HermiT reject the graph and ELK exit 0.
