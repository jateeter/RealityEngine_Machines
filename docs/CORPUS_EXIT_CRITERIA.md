# Corpus Exit Criteria v1.0

Status: **published**
Corpus ref: `corpus-exit-v1.0`
Applies to: `RealityEngine_CI`, `localOpenClawStack`, `localAIStack`, `localHealthkitBridge`

This document is what the dependent repositories regenerate against. It exists
because four repos derive artifacts from this corpus and none of them regenerate
automatically, so without a pinned statement of the contract they each encode
whatever the corpus happened to look like on the day they ran.

That is not hypothetical. During the OWL rollout (#61) this corpus changed
`re-core` 0.2.0 → 0.3.0, deleted two properties, renamed every trigger-rule IRI,
split `m:agent-binding` into two individuals, renamed four sequence labels, and
took ABox coverage from 43 to 1,328 machines — which changed every `sha256` in
`abox-manifest.json`. A dependent that regenerated at the start of that day would
have been wrong by the end of it.

## 1. How to read this document

The contract is split by **stability**, because not all of it is equally settled:

- **§3 Settled** — pinned at `corpus-exit-v1.0`. Regenerate against it now. A
  change here is a new major version of this document and will be announced.
- **§4 Provisional** — known to be moving, with the issue that will move it.
  Depend on it only if you must, and expect to regenerate when that issue lands.
- **§5 Open** — not settled, and not this corpus's to settle. Named so you do
  not mistake silence for agreement.

Nothing in §3 is moved by any currently open issue. That is the point of the
split: the three dependent repos are blocked on §3, and §4 does not block them.

## 2. The pinned ref

```
tag     corpus-exit-v1.0
commit  c1b7c29
```

Regenerate against the tag, not against `main`. Record the tag in whatever
artifact you generate, so a later mismatch is detectable rather than inferred.

## 3. Settled

### 3.1 Corpus shape

| | |
|---|--:|
| machines | **1,328** |
| domains | **12** |
| schemas in `schemas/` | 15 |
| corpus artifacts schema-valid | 1,337 / 1,337 |
| contract tests | 112 passing |

Domains: `agriculture`, `ai-services`, `built-space`, `community-services`,
`data-center`, `digital-logic`, `energy`, `health-personal`, `health-services`,
`legal-services`, `life-balance`, `transportation`.

### 3.2 Machine identity — and the join key

Three identifiers are corpus-unique across all 1,328 machines and may be relied
on: the **file stem**, `machine.name`, and the machine's IRI namespace.

**The canonical key for joining an external artifact to a corpus machine is
`machine.name`, normalised** — lowercased with all non-alphanumeric characters
removed.

This is measured, not asserted. Joining the 1,323 OpenClaw agent specs to the
corpus:

| agent-side key | target | joins |
|---|---|--:|
| **`machine.name`** | **corpus `machine.name`** | **1,323 / 1,323** |
| `machine.id` | corpus file stem | 1,320 / 1,323 |
| `machine.code` | corpus file stem | 1,316 / 1,323 |

`machine.code` is a short display code and **is not a join key**: it diverges from
corpus identity in seven cases (`DailyActivityMonitor` carries
`code: "activity-monitor"`, `MedicationAdherenceMonitor` carries
`code: "medication-adherence"`, and so on), and `tagging.machineCode` is absent
on 123 of 1,328 machines and duplicated once (`rsflipflop`, shared by `RSFlipFlop`
and `RSFlipFlopDeprecatedDemo`). Any resolver keying on `code` will silently miss
those machines.

> Note for jateeter/localOpenClawStack#23: this supersedes that issue's
> "996 file-stem / 3 display-name / 211 ambiguous / 6 unresolvable" split, which
> describes *filenames*. Agent spec filenames are kebab-cased display names and
> carry no reliable relation to corpus identity — resolve through the `machine`
> object's `name` field instead.

### 3.3 Agent coverage — the counts that must reconcile

| | |
|---|--:|
| machines carrying `metadata.agentBinding` | 1,058 |
| machines carrying `metadata.openClawProjection` | 1,185 |
| carrying both | 1,058 |
| carrying neither | 143 |
| OpenClaw agent specs | 1,323 |
| machines joined to an agent spec | **1,323** |
| machines with no agent spec | **5** |

`agentBinding ⊂ openClawProjection` exactly: every machine with a curated binding
also has a projection, and 127 have a projection only.

The five uncovered machines are the arbitration conformance fixtures —
`ArbitrationProviderPeer`, `ArbitrationProviderTarget`, `ArbitrationReader`,
`ArbitrationWriterA`, `ArbitrationWriterB`, all in `digital-logic`. They are
**deliberately agent-free**: they exist to prove deterministic arbitration, and a
non-deterministic contributor is precisely what would invalidate them. A
regeneration that produces 1,328 agent specs is wrong.

### 3.4 Autonomy modes

`schemas/agent-binding.schema.json` requires `mode`, and every binding also
carries a `writeBack`. The mode grades what may return along the binding; it does
not describe whether the binding exists.

| mode | `canWriteBack` | `writeBackType` | stage | machines |
|---|---|---|--:|--:|
| `observe` | `false` | `none` | 0 | 109 |
| `advise` | `true` | `pe-sensor` | 1 | 358 |
| `supervised-act` | `true` | — | — | 491 |
| `automated-act` | `true` | — | — | 100 |

`observe` is egress-only and has **no** return leg. Consumers must not synthesise
a write-back region for an observe binding.

### 3.5 Region allocation and arbitration

| artifact | state |
|---|---|
| `domains/region-allocation.json` | 68 shared output lanes (0 cross-domain), 29 inter-domain buses, 1,185 external write-backs |
| `domains/arbitration-registry.json` | 2,837 contended cells — `PRECEDENCE` 2,835, `SEVERITY` 2, `withinRank` on 268 |
| `domains/lane-contracts.json` | 990 lanes, **987 annotated** |
| `domains/corpus-index.json` | 1,328 machines, 12 domains |
| `domains/semantic-bus-registry.json` | current |

All are generated and drift-checked. Regenerate them from the corpus rather than
hand-editing; `npm run validate` fails on drift.

Any cell with more than one writer — counting machine outputs and PE sources
alike — **must** have an arbitration-registry entry. An undeclared contended cell
is a corpus error, not a runtime default.

### 3.6 Schemas

The 15 schemas in `schemas/` are the validation contract. `agent-binding.schema.json`
is `$ref`'d directly by `localOpenClawStack`, so a change there lands downstream
immediately; it is unchanged at this tag.

### 3.7 Verification a dependent must pass

A regeneration is correct when:

1. It resolves through §3.2's join key and reports **1,323 joined, 5 uncovered**,
   with the five being the arbitration fixtures by name.
2. Its counts reconcile against §3.3 and any difference is explained, not merely
   observed.
3. Artifacts it derives from corpus schemas validate against the schemas at this
   tag.
4. It records `corpus-exit-v1.0` in its output.

## 4. Provisional — will move, with the issue that moves it

Depend on these only if you must.

| surface | moved by | what changes |
|---|---|---|
| `semantics/abox/**/*.ttl` content | #80 | adding `rdfs:label` to 84,878 individuals rewrites every ABox file |
| **every `sha256` in `semantics/abox-manifest.json`** | #80 | follows from the above — this is what the RE/PE runtimes expose as `semanticsHash` |
| semantic axis names | #81 | 947 machines differ only as `process stability` vs `process_stability`; canonicalisation will rewrite one side |
| `re-core.ttl` version | #80, #82 | currently `0.3.0` |

`abox-manifest.json` is the sharpest of these. It is the corpus's semantic
identity — name, IRI and `sha256` per machine — and the four runtimes surface it
as `semanticsIri` / `semanticsHash`. **Do not pin these hashes at this tag.**

## 5. Open — not settled here

Named so their absence is not read as agreement:

- **Three unresolved ingress lanes.** `agent-completion-risk` (localAIStack),
  `healthkit-activity` and `healthkit-steps` (HealthKit) have no axis annotations,
  so the lane projector omits rather than guesses them. They carry real physical
  quantities and belong to their provider repos —
  jateeter/localAIStack#38 and jateeter/localHealthkitBridge#9.
- **The 8 localAI machine definitions** have never been validated against
  `machine.schema.json`, and whether they are corpus machines or a separately
  contracted class is undecided — jateeter/localAIStack#38.
- **The HealthKit ingest contract** is prose plus one spec test, with no JSON
  schema — jateeter/localHealthkitBridge#9.
- **One trigger-rule contradiction**, `AIHardwareResilience` output position 5,
  both `GREEN "schedule maintenance"` and `RED "emergency replacement"` — #56.
  Allowlisted exactly in `tests/contracts/owl_semantics_test.py`.
- **Name-uniqueness policy** at the CES / machine / domain scopes — #68. Not a
  blocker: corpus-wide IRI collisions are structurally impossible, and
  corpus-wide `duplicate_label` is 0.
- **What the corpus-wide OWL gate runs** — #79.

## 6. Provenance

Every figure here was measured against `c1b7c29`, not carried forward from an
earlier count. The corpus at this tag:

- all 12 domains merge, report and reason clean under **ELK and HermiT**,
  0 report ERRORs, ROBOT v1.9.10
- the first corpus-wide merge — 1,328 ABoxes + TBox, 1,120,783 lines — is
  consistent under both reasoners with 0 ERRORs
- `generate-owl.py --all --check` is byte-stable; `--manifest-check` is clean
- `npm run validate`: 1,337 artifacts, 0 failed
- `npm run test:contracts`: 112 passing
