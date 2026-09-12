# OWL Semantic Representation Roadmap

Last reviewed: 2026-07-29

## Purpose

Give the machine corpus a formal, reasoner-checkable semantic representation
(OWL 2, Turtle serialization) of what each machine *does* — its critical event
sequences, the determinations those sequences emit, and the actions those
determinations prescribe — so that verification and auditing in both the
Perception Engine (PE) and Reality Engine (RE) can be performed against
semantics rather than against serialized JSON bytes.

The existing verification posture distinguishes service availability, registry
alignment, contract parity, byte equivalence, and integration success. OWL
semantics adds a sixth class: **semantic equivalence** — two engines (or two
corpus revisions) agree on the *meaning* of a machine's behavior even when
serialized payloads drift.

## Prototype (complete)

The Personal Health Fall Detection machine
(`machines/domains/health-personal/FallDetection.json`) is the first-pass
prototype:

- `semantics/ontology/re-core.ttl` — core TBox: `re:Machine`,
  `re:CriticalEventSequence` / `re:LifeSafetySequence`, `re:SequenceStep`,
  `re:ElementValue`, `re:Determination`, the `re:Action` hierarchy
  (`re:LoggingAction`, `re:NotificationAction`, `re:EscalationAction`),
  `re:TriggerRule`, `re:GovernancePolicy`, `re:Interconnection`,
  `re:PerceptualMapping`, and PROV-aligned audit classes
  (`re:PerceptionEvent`, `re:SequenceObservation`, `re:DispatchRecord`).
  Audit axioms are included, e.g. *a determination that prescribes an
  escalation action must carry RED* (`re:EscalationDetermination`), and
  *life-safety sequences are exactly those containing a life-safety step*.
- `scripts/generate-owl.py` — stdlib-only, byte-deterministic projector from
  machine JSON to per-machine ABox Turtle under `semantics/abox/<domain>/`.
  Action strings are resolved against the canonical action individuals
  declared in `re-core.ttl` (`re:actionCode`), so the ontology is the single
  source of truth for the action vocabulary.
- `semantics/abox/health-personal/FallDetection.ttl` — the checked-in
  prototype ABox (7 sequences, 88 individuals).
- `tests/contracts/owl_semantics_test.py` — parity gates: regeneration
  determinism, vocabulary closure (ABox uses only TBox-declared terms),
  sequence/trigger-rule parity with the JSON, life-safety typing, and the RED
  ⇒ escalation-action invariant.

Run:

```bash
python3 scripts/generate-owl.py --machine machines/domains/health-personal/FallDetection.json --check
npm run test:contracts
```

## Key corpus finding

A trial run of the generator over the full corpus (1,321 machine files, ~3 s)
succeeds structurally, but surfaces ~3,900 distinct free-text `action` strings
outside health-personal (full sentences such as "Route domain family review,
escalation, and resolver summary."). The health-personal domain already uses
controlled codes (`emergency-dispatch`, `caregiver-check-in`, `log-only`, …).
**Semantic auditability of actions requires a controlled action vocabulary
corpus-wide.** This is the largest single work item below (M2).

## Milestones

### M0 — Prototype (done)

Fall Detection TBox + ABox + generator + contract tests, as above.

### M1 — Domain rollout: health-personal (done — PR #37)

- Generate and check in ABoxes for every `machines/domains/health-personal/`
  machine (`generate-owl.py --domain health-personal --write`).
- Extend the ontology's canonical action individuals with the remaining
  health-personal action codes, each typed with the correct consequence class.
- Promote the generator `--check` into `scripts/validate-corpus.sh` for
  domains that have checked-in ABoxes (incremental gate, mirroring the
  STRICT_DOMAIN_CONTRACT pattern).

### M2 — Action vocabulary normalization (corpus-wide) (done — PR #38)

- Inventory all distinct `action` strings (`generate-owl.py --all` warning
  stream is the inventory tool).
- Define a controlled action-code vocabulary per domain family; map free-text
  actions to codes plus an `rdfs:comment` carrying the original prose.
- Backfill machine JSON via a `scripts/backfill-action-codes.py` (same
  plan/--write pattern as the other backfill scripts); keep the prose in a new
  `actionNarrative` metadata field so nothing is lost.
- Gate: `generate-owl.py --all --strict-actions` passes.

### M3 — Corpus-wide generation + validation gates (done)

Implementation note: instead of committing ~1,300 generated TTL files, the
corpus-wide gate is `semantics/abox-manifest.json` — per-machine name, IRI,
and sha256 of the generated ABox, checked by
`generate-owl.py --manifest-check` inside `npm run validate`. Exemplar ABoxes
stay checked in per rolled-out domain (health-personal). The manifest is also
the lookup engines use for `semanticsIri`/`semanticsHash` (M4).

Original plan:

- Check in ABoxes for all domains; add `owl:check` to `npm run validate`.
- Add external-toolchain validation in CI (optional, non-blocking at first):
  ROBOT `report`/`reason` (HermiT or ELK) over `re-core.ttl` + merged ABoxes
  to catch inconsistencies the structural validator cannot (e.g. an
  escalation action prescribed by a non-RED determination violates the
  `re:EscalationDetermination` axiom).
- Extend TBox coverage: openClawProjection, agentBinding/autonomy contracts,
  semantic-bus registry alignment (`semantic-bus-registry.schema.json` ↔
  `re:Interconnection`).
- Cross-machine reasoning: interconnection graphs (bus producers/consumers)
  become an RDF graph; validate region overlap and privacy-boundary
  annotations semantically.

### M4 — Engine surfacing (RE/PE APIs) — verified 3-of-3 (2026-09-12)

- Each engine (C++, LSP, Scala, TypeScript PE) serves the semantic identity of
  its loaded machines: `GET /api/machines/semantics/:name` returning the ABox
  (or its IRI + content hash), and machine list responses gain a
  `semanticsIri` + `semanticsHash` field.
- Parity tests compare `semanticsHash` across engines: semantic equivalence
  becomes a first-class verification class alongside byte equivalence.

**Measured on the three-engine lane** (`--engines=cpp:1,lsp:1,scala:1`,
regression corpus), `scripts/verify-semantic-parity.sh`:

```
semantic-parity: 'Fall Detection' — 3 engine(s) answered, 0 unmeasurable
  cpp-1:   fbd54a18bb8320faeb2dcf07f9c19eee5509e7eaae6aac037a6ccf20f6e8807e
  lsp-1:   fbd54a18bb8320faeb2dcf07f9c19eee5509e7eaae6aac037a6ccf20f6e8807e
  scala-1: fbd54a18bb8320faeb2dcf07f9c19eee5509e7eaae6aac037a6ccf20f6e8807e
semantic-parity: OK (engines agree with each other and the corpus manifest)
```

All three serve the surface and agree, and the agreed hash matches the corpus
manifest — so the comparison has an authority and is not three engines agreeing
with each other about something wrong.

**Why this read as unbuilt until now.** The surface answered `404` in the
single-engine Docker lane, which looks identical to an unimplemented endpoint.
It was not: the engine resolves semantic identity from
`semantics/abox-manifest.json`, and the container mounted only `machines/`, so
there was nothing to answer from. See M5 below — the same root cause, three
times.

Still open for M4: `semanticsIri`/`semanticsHash` on machine **list** responses
(the per-machine endpoint is what parity exercises today), and the TypeScript PE,
which is not in the instance registry and needs `--extra-runtime` to be compared.

### M5 — Semantic audit records (PE→RE→PE cycle) — invariants verified 3-of-3 (2026-09-12)

Record shapes and the shared `GET /api/audit/semantics` surface are
specified in `SEMANTIC_AUDIT_CONTRACT.md` (master in `RealityEngine_CI/docs/`);
per-runtime implementations are tracked in the engine repos' Phase 2 issues.

**Measured**, `scripts/verify-audit-chain.sh` on the three-engine lane:

```
cpp-1:   15 observation(s); confirmed-fall path fall-conf-v1 -> ... -> fall-conf-v6
lsp-1:   14 observation(s); confirmed-fall path fall-conf-v1 -> ... -> fall-conf-v6
scala-1: 14 observation(s); confirmed-fall path fall-conf-v1 -> ... -> fall-conf-v6
OK (3 engine(s) produced a complete, corpus-joined evidence chain)
```

All three audit invariants hold on every runtime: the confirmed-fall path
completes (1), every IRI shares the machine's manifest base (2), and no
escalation determination contradicts `re:EscalationDetermination` (3).
`re:PerceptionEvent` resolves on the PE side too — 378 of 400 records carry a
`machineIri`, the remaining 22 being localAI sources genuinely outside the
corpus manifest.

**The manifest must travel with the corpus.** Every engine resolves audit IRIs
by walking up from `MACHINES_DIR` for `semantics/abox-manifest.json`. That was
missing in three places, and each one silently produced records with
`machineIri`, `sequenceIri` and `stepIri` null — which the contract also permits
for a machine genuinely absent from the manifest, so *"the corpus was
relocated"* and *"this machine has no ABox"* were indistinguishable:

| where | fix |
|---|---|
| RE container mounted only `machines/` | `RealityEngine_CI` `fe14e39` |
| PE container mounted no corpus at all | `RealityEngine_CI` `cddbf52` |
| materialized corpus carried no `semantics/` | `RealityEngine_CI` `2e7a80d` |

The third meant **every** corpus-scoped lane — regression, standard-deployment,
arbiter-fixture — ran without the join M5 exists to provide.

`FallDetection.json` also had to join `config/regression-corpus.txt`: audit
invariant 1 names that machine, `verify-audit-chain.sh` drives it, and the
deployment gate runs on the regression corpus — where it was absent. All three
runtimes answered "0 records", which reads as an incomplete chain rather than as
a machine nobody loaded. An invariant whose subject is absent is not a passing
invariant.

Still open for M5: `re:DispatchRecord` (item 3 below) is unverified — the two
observation types are what the chain exercises today; and the TypeScript PE is
outside the registry-backed comparison.

Recognition of the semantic representations inside the live workflow:

1. **PE ingress (perceive)**: when PE writes a machine's input region, it
   emits a `re:PerceptionEvent` (machine IRI, tick, source id) into an audit
   graph (append-only Turtle/N-Quads ledger or the existing dispatch ledger
   extended with IRIs).
2. **RE recognition (process)**: when a CES advances or completes, RE emits a
   `re:SequenceObservation` referencing the step IRI (`m:step-…`) — not a
   string — so an auditor can join runtime behavior to corpus semantics with
   no name matching.
3. **PE egress (dispatch)**: trigger/bus/agent dispatches emit
   `re:DispatchRecord` entries linking the `re:Determination` IRI and the
   prescribed `re:Action` individual.
4. **Audit queries**: with PROV alignment, standard queries become possible:
   "show every EscalationAction dispatched in the last 24 h with the full
   step-by-step evidence chain that led to it", "find dispatches whose
   determination was not RED" (invariant violation), "find life-safety
   sequences that reached step N but never completed".
5. **Runtime recognition**: PE source activation can consult the ontology —
   e.g. refuse to bind a source that can write into the input region of a
   `re:LifeSafetySequence` machine unless the source mapping declares the
   required autonomy level.

Milestone M5 spans RealityEngine_CPP, RealityEngine_LSP, RealityEngine_Scala,
and RealityEngine_Manager (TypeScript PE), with e2e verification in
RealityEngine_CI.

## Validation strategy summary

| Layer | Tool | Gate |
|---|---|---|
| Determinism / drift | `generate-owl.py --check` | contract test + `npm run validate` |
| Vocabulary closure | `owl_semantics_test.py` | contract test |
| Safety invariants (structural) | `owl_semantics_test.py` | contract test |
| OWL consistency / reasoning | ROBOT + HermiT/ELK (CI container) | M3, non-blocking then blocking |
| Cross-engine semantic parity | `semanticsHash` comparison | M4, RealityEngine_CI e2e |
| Runtime audit-chain integrity | audit-graph queries | M5 |

## Risks and constraints

- **Action free-text debt (M2)** is the long pole; it touches ~thousands of
  machine files and needs domain-owner review, not mechanical rewrite alone.
- Keep the generator stdlib-only; reasoner-based validation belongs in CI
  containers, not developer laptops.
- Generated ABoxes are artifacts of the JSON: never hand-edit; JSON remains
  the single source of truth for behavior, the TTL for *vocabulary*.
- Corpus filenames are globally unique (enforced), so `<domain>/<stem>` IRIs
  are stable; renames are semantic identity changes and must be treated like
  contract changes.
