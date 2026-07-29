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

### M4 — Engine surfacing (RE/PE APIs)

- Each engine (C++, LSP, Scala, TypeScript PE) serves the semantic identity of
  its loaded machines: `GET /api/machines/semantics/:name` returning the ABox
  (or its IRI + content hash), and machine list responses gain a
  `semanticsIri` + `semanticsHash` field.
- Parity tests compare `semanticsHash` across engines: semantic equivalence
  becomes a first-class verification class alongside byte equivalence.

### M5 — Semantic audit records (PE→RE→PE cycle) — future work

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
