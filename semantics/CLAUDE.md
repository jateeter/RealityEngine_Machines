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
- Integration vocabulary (`0.4.0`): `re:MCPInvocation`, `re:MCPToolResult`,
  `re:ACPDispatch`, `re:OpenClawAgentBinding`, `re:SourceMappingWrite`,
  `re:SemanticGuardrailViolation`, plus `re:IntegrationProvider` and
  `re:EvidenceArtifact` to give provider and evidence a range. M2 of the
  roadmap. `re:OpenClawAgentBinding` declares **no properties of its own** on
  purpose — machine, agent id, input axes, autonomy mode and completion mapping
  are `re:AgentBinding`'s already, and a second name for one fact is a second
  thing to keep in step. Worked examples live in `integration/examples.ttl`,
  are hand-authored rather than generated, and are merged by `reason-owl.sh` in
  **every** scope so M2's "one MCP and one ACP workflow classify" is gated
  rather than asserted.
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

## Which corpus routine validation reasons over

**The full corpus is not loaded by routine validation.** The regression lanes
boot a minimal provable corpus, and full-corpus checks run manually or on a
cycle. The reasoner follows the same split:

| scope | command | cost | when |
|---|---|--:|---|
| minimal provable corpus | `npm run owl:reason:corpus` | ~5s | every PR |
| arbiter fixtures | `npm run owl:reason:arbiter` | ~4s | with the arbiter gate |
| one domain | `npm run owl:reason` | ~5-20s | while working in it |
| every domain | `npm run owl:reason:domains` | ~3min | cyclic |
| corpus-wide merge | `npm run owl:reason:all:complete` | ~18min | weekly |

This matters more as the corpus grows. Domains, machines and CES all expand at
MVP, and a gate whose cost scales with the corpus is a gate that eventually gets
switched off — which is worse than a smaller gate that keeps running. The
minimal corpus is chosen to be *provable*, not merely small: it carries the
machine classes, the bus and the fixtures the contracts are stated against.

## The ROBOT report profile, and why it is now at zero

`robot-report-profile.txt` lists all 32 rules ROBOT ships rather than expressing
a delta, so a rule cannot be disabled by omission (#46).

This section used to record two rules as permanently reporting — 120
`missing_definition` and 16 `missing_superclass` — and argued both were OBO
publishing conventions this ontology need not satisfy. **That is no longer the
state.** Both were closed rather than tolerated: every class carries an
`obo:IAO_0000115` definition, and the root classes sit under PROV, which says
something true about them instead of introducing a vacuous `re:Entity`.

`ERROR`, `WARN` and `INFO` are all zero. A violation at **any** of the three is
now a real signal, which it was not while 136 were expected — an argument for
tolerating a nonzero baseline is also an argument for never noticing the 137th.
A class added without a definition is caught by
`integration_vocabulary_test.test_every_new_class_carries_a_definition` before
it reaches the report.

## What OWL is not asked to check here

Two invariants are deliberately **not** ontology axioms, for one shared reason:
the open world concludes nothing from a *missing* assertion, so a class defined
over an absence is inert — and an inert defined class has an empty extension
that looks exactly like a clean result.

| Invariant | Checked in | Why not in OWL |
|---|---|---|
| An escalating determination states its RAG status | `tests/contracts/escalation_rag_test.py` | unstated is not a contradiction; the axiom evaluated 2 of 80 escalations |
| A source mapping write names a completion mapping | `tests/contracts/integration_vocabulary_test.py` | `owl:maxCardinality 0` is never entailed; HermiT classified the negative fixture as nothing |

Both keep a negative fixture, because a guard with no violating case to catch is
a guard nobody has seen work.

`scripts/prove-workflows.py` is where the rest of that closed-world work lives —
M3's six static workflow rules over a named corpus profile, emitting findings as
`re:SemanticGuardrailViolation` individuals:

| command | scope |
|---|---|
| `npm run prove:workflows` | the `standard-deployment` profile; must be clean |
| `npm run prove:workflows:fixtures` | the negative fixtures; each must fire |
| `--profile <manifest>` | any corpus manifest, including a full-corpus one |

Gated by `tests/contracts/static_provability_test.py` and
`tests/contracts/openclaw_profile_drift_test.py`, because a checker nobody
invokes is not a gate — `generate-regression-profile.py --check` had existed
since it was written and **nothing called it**.

`scripts/export-runtime-trace.py` is the M4 counterpart: it converts one
PE->RE->PE cycle into a graph in the same vocabulary, so a trace and the corpus
it came from merge into one thing a reasoner can ask questions across.

| command | scope |
|---|---|
| `npm run trace:export` | one cycle to Turtle + JSON-LD |
| `npm run trace:check` | joinability; non-zero if any event joins to nothing |

The join was already there and is the part worth knowing: the engines' own
`GET /api/audit/semantics` records carry `machineIri`, `sequenceIri`, `stepIri`
and `determinationIri` **byte-identical** to the ones `generate-owl.py` writes
into the ABox. The corpus join goes through `machineName`, never `machineId` —
ids are re-minted per runtime, so an id-keyed trace measures the runtime rather
than the corpus.

The exporter refuses to invent identifiers it is not given: a push id, a
correlation id on PE source writes and the output region on a sequence
observation have no runtime surface, and it reports them as gaps rather than
synthesising them. A generated push id would look exactly like a real one and
would join two events nothing actually connected.

`scripts/validate-runtime-trace.py` is M5: it merges ontology + profile ABoxes
+ trace, runs ROBOT report and HermiT, then the closed-world checks ROBOT cannot
make — exact region writes, cardinality, forbidden endpoint use. Every finding
becomes a named `re:SemanticGuardrailViolation` individual, because M5 asks for a
named record rather than an exit code.

| command | scope |
|---|---|
| `npm run trace:validate` | a live trace against the corpus it came from (~10s incl. HermiT) |
| `npm run trace:validate:check` | the six bad-trace fixtures; each must be rejected *and* emit a named record |

The allowed-endpoint catalogue M3's R2 reported as missing does exist — the PE
serves it at `GET /api/integrations/localai/catalog`, not in
`integrations.json`, which is why the static check could not see it. The
validator reads it for forbidden-endpoint use. **MCP invocations are not
recorded anywhere** (#152), so the invocation half of the MCP chain classifies
from the worked examples rather than from a live run.

Two things the prover reports rather than hides. It prints an `UNGATED` line for
any rule it cannot evaluate: R2's workflow-class half has no source of truth
(no `integrations.json` entry declares `allowedOperations`), and R6 cannot reach
the 625 machines that state RED only on a `re:TriggerRule`, because
`re:matchesOutputPosition` indexes the output *value vector* and not the
sequence's determination list, so no rule→determination join exists in the
ABox. Corpus-wide it finds 13 real violations, tracked in #149 — the limited
profile is the gate, per S7.

The escalation invariant — an emergency-path action may only be prescribed by a
`RED` determination — is the reason `reason-owl.sh` runs HermiT and not ELK
alone. ELK does not implement the constructs it relies on and passes a corpus
that violates it. Verified: asserting `re:UrgentIntervention` on a `GREEN`
determination makes HermiT reject the graph and ELK exit 0.

## Standing rules — authoritative in `../../RealityEngine_CI/docs/ENGINEERING_CONTRACT.md`

These apply here and are **not** restated in this file. They were previously
copied into eighteen `CLAUDE.md` files across six repositories, which is the
duplication problem the rules themselves warn about: copies drift, a rule added
to one applies only where someone looked, and with no authority a reader cannot
tell which copy is current.

| Rule | In short |
| --- | --- |
| Qualify every "registry" | Never the bare word — instance / machine / cesgen / arbitration / domain / semantic-bus / tag. |
| Verify a merge beyond the hosted checks | A green PR is not a verified PR; the hosted path cannot reach the integration points. Name what you could not exercise, and record what you noticed but did not chase. |
| Never commit to main | Branch from `origin/main`, PR, verify, squash-merge, clean up. |
| _CI is the authority | Peripheral repos keep minimal CI that forces local validation; RealityEngine_CI verifies fixes against a live universe. Check its `docs/` before adding CI anywhere else. |
| Use bash, not zsh | Shell work runs in `/opt/homebrew/bin/bash` (5.x), not zsh or macOS `/bin/bash` 3.2: any loop, unquoted variable, glob or `set --` goes through it with `set -euo pipefail`, and you check the command's exit status, not the pipeline tail. |

Read the contract for the full text, the qualifier table, and the cleanup steps.
