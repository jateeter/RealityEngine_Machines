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

### M3 — Corpus-wide generation + validation gates (done; reasoned corpus-wide 2026-09-14)

Every reasoning result before this was single-domain, which is a weaker claim
than the milestone makes. `scripts/reason-owl.sh --all` now runs the whole
corpus:

```
reason-owl: ERROR 0  WARN 0  INFO 151
reason-owl: diff vs released — no axiom changes
reason-owl: OK (corpus (12 domains) merged, reported, and reasoned
            consistently under ELK)
```

**Released baselines are gzipped**, because otherwise this gate could not exist
at corpus scope. The merged corpus artifact is 96 MB raw — too large to commit,
and an uncommitted baseline makes `diff` report SKIPPED forever, which is an
unreachable verifier reporting healthy for the same reason a passing one does.
Compressed it is 4.4 MB, and `semantics/released/` as a whole went from ~100 MB
to 4.6 MB. Both scopes now report `no axiom changes` on a re-run, so the gate is
reachable *and* discriminating.

**HermiT now runs corpus-wide (#79, closed 2026-09-15).** ELK alone is a
well-formedness check rather than a completeness claim, because it does not
implement functional properties. The full corpus has now been reasoned under
both:

```
No violations found.
reason-owl: 0 INFO / 0 WARN pending triage
reason-owl: diff vs released — no axiom changes
reason-owl: OK (corpus (12 domains) merged, reported, and reasoned
            consistently under ELK HermiT)

real 20m51s
```

Run against the vocabulary as it stands after the definitions work, which
matters: that change added 17 `rdfs:subClassOf prov:Entity`/`prov:Agent` axioms,
and a full reasoner is exactly what can find a contradiction in those where ELK
cannot. It found none.

`--reasoner both` stays off by default corpus-wide — HermiT is 88x ELK there,
1,061s against 12s on the merged graph — and is scheduled rather than run per
change. What the merged graph tests that the shards cannot is cross-domain
contradiction, and today the machine IRI scheme means domains share no
individuals, so there is nothing for it to find. That is a property of the
corpus as it stands, not a permanent one; raise the frequency as cross-domain
interaction grows.

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

**The TypeScript PE conforms.** It is not an engine instance, so
`verify-semantic-parity.sh` gained `--extra-runtime id=url`; per the shaping on
`RealityEngine_CI#327` it conforms to the quorum rather than voting in it, so it
is compared against the settled result and cannot change it:

```
semantic-parity: conformer ts-1: conforms (fbd54a18…807e)
```

Same IRI and same hash as the three engines. M4's surface is therefore
implemented and agreeing across all four runtimes.

**The list surface is closed too (2026-09-15).** `semanticsIri`/`semanticsHash`
on machine list responses was M4's last open item. Measured on a full-corpus
three-engine universe:

| runtime | machine registry | `json/list` | `semanticsHash` | `semanticsIri` |
|---|---|---|---|---|
| cpp-1 | 1328 | 1328 | 1328 | 1328 |
| lsp-1 | 1328 | 1328 | 1328 | 1328 |
| scala-1 | 1328 | 1328 | 1328 | 1328 |

1328 common `relFile` keys, and the `semanticsHash` is identical across all
three on every one of them.

**It was not unimplemented — it was silently disabled on LSP by a path bug three
layers away** (RealityEngine_LSP#110). `machine-json-list-rows` relativized
against `(truename dir)` while the file walk used `uiop:directory-files`, which
does not resolve symlinks. On macOS /tmp is a symlink to /private/tmp and the
harness serves the corpus from /tmp, so the prefix test never matched and every
row fell back to a bare basename. `relFile` stopped being path-aware, and
`semantics-key-for-rel` then derived `core/<stem>` instead of `<domain>/<stem>`,
matched nothing in the manifest, and dropped both fields: 0 of 21 on LSP against
18 of 21 on cpp and scala.

A comment asserting the walk returned truenames is what made the code look
correct. Worth remembering as a shape: the surface reported a plausible value
rather than an error, so nothing failed — the milestone simply read as
unfinished.

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

**TypeScript PE emission — verified 2026-09-12.** Driven with
`POST /api/signals {region, values, triggerPush:true}`, it emits
`re:PerceptionEvent` with correct regions, and 32 of 50 records resolve a
`machineIri` (the remainder are localAI sources genuinely outside the corpus
manifest). Two conditions are required and neither is obvious:

- a source must be **active and carrying a value** — one registered through
  `POST /api/sources` with no value contributes nothing to `assembleVector`;
- `REALITY_ENGINE_URL` must reach a live RE, because emission happens *after*
  the push to the RE. With an unreachable target the push throws first and the
  buffer stays empty, which looks exactly like an unimplemented emitter.

**`re:DispatchRecord` — measured, and partially populated.** With
`TRIGGERS_ENABLED=true TRIGGER_DISPATCH_MODE=ledger`, every ledger entry carries
a `semantics` block and `machineIri` resolves:

```json
"semantics": {
  "machineIri": "…/health-personal/HomeTransportationBarrierMonitor#machine",
  "sequenceIri": null,
  "actionCode": null
}
```

`sequenceIri` was fixed on 2026-09-12 (`RealityEngine_Manager` `2b324a4`): the PE
read `op.sequenceId`, which the engines stopped emitting when the fold moved into
the machine's atomic step — they now emit `sequenceIds` and
`governance.sequenceId`. Reading only the singular field yielded `""` with no
error, so the join looked implemented and produced nothing. Measured after:

```
record.sequenceId  ''    ->  'transport-adequate'
sequenceIri        null  ->  …/HomeTransportationBarrierMonitor#seq-transport-adequate
```

**`actionCode` — implemented in all three engines and the PE, confirmed on two.**
`RealityEngine_CI#365`; C++ `bc40bc3`, Scala `8a55631`, LSP `e7edc69`, PE
`RealityEngine_Manager` `469c07d`.

```
cpp-1     9 entries, 5 with actionCode  ['continue-monitoring', 'log-activity', 'log-only']
scala-1   8 entries, 3 with actionCode  ['continue-monitoring', 'log-activity']
lsp-1     0 entries, 0 with actionCode  []   ← unmeasured, see below
```

and end to end on the dispatch ledger:

```
machineIri   …/HomeTransportationBarrierMonitor#machine
sequenceIri  …/HomeTransportationBarrierMonitor#seq-transport-adequate
actionCode   'continue-monitoring'
```

`lsp-1` emitted no merge entries at all — every source reports `"active": false`
and 0 of its 28 machines are active, so there was nothing to carry the field.
That is `RealityEngine_CI#358` (the 2-1 source-activity split) and predates this
work; LSP's implementation passes oracle parity 4966/4966. **Unmeasured, not
disagreeing** — a runtime that produced nothing has told us nothing.

Two notes for whoever finishes this. The PE's Dispatcher had been reading
`op.action`, a top-level field no engine has ever emitted, so that read was dead
from the day it was written and supplying the engine field alone changed nothing.
And the action cannot be recovered downstream of governance resolution, which
matches a rule by sequenceId and values and never sees the output event — so it
travels with the contributor and attaches to the decision that *wins* the
severity join, per the "decision travels whole" rule each engine already states.

Superseded note (the state before this work):
The corpus keeps `action` on the output event's metadata
(`fall-conf-out: action=emergency-dispatch`), but the RE does not propagate it
into the merge entry: `governance` carries `sequenceId`, `ragStatusCode` and
`processStatus`, and no `action` under any spelling. The consequence is larger
than one null field — `ESCALATION_ACTIONS` is keyed on `actionCode`, so the
escalation guardrail matches nothing and invariant 3 counts zero escalations
whatever was dispatched. It is not failing; it is unevaluable, which looks the
same from outside. **This was the open item in M5. Closed 2026-09-14.**

`actionCode` now travels with the contributor into the merge entry and attaches
to the decision that wins the severity join, so invariant 3 evaluates instead of
matching nothing. Measured on the live three-engine lane:

```
audit-chain: cpp-1:   14 observation(s); fall-conf-v1 -> ... -> fall-conf-v6
audit-chain: lsp-1:   14 observation(s); fall-conf-v1 -> ... -> fall-conf-v6
audit-chain: scala-1: 14 observation(s); fall-conf-v1 -> ... -> fall-conf-v6
audit-chain: OK (3 engine(s) produced a complete, corpus-joined evidence chain)
```

| runtime | audit records | carrying `actionCode` | escalation records | ragStatus |
|---|---|---|---|---|
| cpp-1 | 100 | 40 | 1 | RED: 1 |
| lsp-1 | 100 | 39 | 1 | RED: 1 |
| scala-1 | 100 | 39 | 1 | RED: 1 |

Two things this settles that a passing verifier alone does not. `actionCode`
propagates — `verify-audit-chain.sh:195` fails outright if the confirmed-fall
record does not carry `emergency-dispatch`, and it passed on all three. And
invariant 3 is **evaluable rather than vacuous**: one escalation record per
runtime, all `RED`, none unstated. It would now fail on a non-RED escalation,
which it previously could not, because a guardrail that matches nothing passes
for the same reason a satisfied one does.

The 40/39 split is the same one-observation delta recorded above; it falls in
the non-escalation set and does not reach the invariant.

Note the default: the ledger ships `enabled:false, mode:dry-run`, so a deployment
that has not turned it on emits no dispatch records at all and looks identical to
one where the feature is missing.

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
