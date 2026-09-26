# Corpus Exit Criteria v2.0

Status: **published**
Corpus ref: `corpus-exit-v2.0` (supersedes `corpus-exit-v1.0`)
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

- **§3 Settled** — pinned at `corpus-exit-v2.0`. Regenerate against it now. A
  change here is a new major version of this document and will be announced.
- **§4 Provisional** — known to be moving. Depend on it only if you must.
- **§5 Open** — not settled, and not this corpus's to settle. Named so you do
  not mistake silence for agreement.

## 2. The pinned ref

```
tag  corpus-exit-v2.0
```

Regenerate against the tag, not against `main`. Record the tag in whatever
artifact you generate, so a later mismatch is detectable rather than inferred.

The tag is the ref, deliberately, rather than a commit SHA written into this
file: the tag lands on the commit that merges this document, which cannot be
known while writing it. `git rev-parse corpus-exit-v2.0` resolves it. The SHA in
§6 is a different claim — the commit the figures were measured against, which is
the parent of the merge and is what makes those numbers auditable.

### Versions

| tag | measured at | what moved |
|---|---|---|
| `corpus-exit-v1.0` | `c1b7c29` (2026-08-15) | first publication |
| `corpus-exit-v2.0` | `0a07fb0c` (2026-09-26) | RS Flip Flop (deprecated demo) retired (#180): it wrote into the `agent-completion-risk` service lane. Machines 1,328 → 1,327, `openClawProjection` 1,185 → 1,184, agent specs 1,323 → 1,322, lanes 990 → 989. A §3 change, so a major version (§1). |

Every figure in §3 was re-measured at `0a07fb0c` with the same method that
reproduces all of v1.0's figures at `c1b7c29`; none is carried forward.

## 3. Settled

### 3.1 Corpus shape

| | |
|---|--:|
| machines | **1,327** |
| domains | **12** |
| schemas in `schemas/` | 16 |
| corpus artifacts schema-valid | 1,337 / 1,337 |
| contract tests | 190 passing, 12 skipped (they need a live universe) |

Domains: `agriculture`, `ai-services`, `built-space`, `community-services`,
`data-center`, `digital-logic`, `energy`, `health-personal`, `health-services`,
`legal-services`, `life-balance`, `transportation`.

### 3.2 Machine identity — and the join key

Three identifiers are corpus-unique across all 1,327 machines and may be relied
on: the **file stem**, `machine.name`, and the machine's IRI namespace. Name
uniqueness is scope-relative and enforced (#68,
`tests/contracts/name_uniqueness_test.py`): a CES name within its machine, a
machine within its domain, a domain within the universe.

**The canonical key for joining an external artifact to a corpus machine is
`machine.name`, normalised** — lowercased with all non-alphanumeric characters
removed.

This is measured, not asserted. Joining the 1,322 OpenClaw agent specs to the
corpus:

| agent-side key | target | joins |
|---|---|--:|
| **`machine.name`** | **corpus `machine.name`** | **1,322 / 1,322** |
| `machine.id` | corpus file stem | 1,320 / 1,322 |
| `machine.code` | corpus file stem | 1,315 / 1,322 |

`machine.code` is a short display code and **is not a join key**: it diverges from
corpus identity in seven cases (`DailyActivityMonitor` carries
`code: "activity-monitor"`, `MedicationAdherenceMonitor` carries
`code: "medication-adherence"`, and so on), and `tagging.machineCode` is absent
on 123 of 1,327 machines. Any resolver keying on `code` will silently miss those
machines.

### 3.3 Agent coverage — the counts that must reconcile

| | |
|---|--:|
| machines carrying `metadata.agentBinding` | 1,058 |
| machines carrying `metadata.openClawProjection` | 1,184 |
| carrying both | 1,058 |
| carrying neither | 143 |
| OpenClaw agent specs | 1,322 |
| machines joined to an agent spec | **1,322** |
| machines with no agent spec | **5** |

`agentBinding ⊂ openClawProjection` exactly: every machine with a curated binding
also has a projection, and 126 have a projection only.

The five uncovered machines are the arbitration conformance fixtures —
`ArbitrationProviderPeer`, `ArbitrationProviderTarget`, `ArbitrationReader`,
`ArbitrationWriterA`, `ArbitrationWriterB`, all in `digital-logic`. They are
**deliberately agent-free**: they exist to prove deterministic arbitration, and a
non-deterministic contributor is precisely what would invalidate them. A
regeneration that produces 1,327 agent specs is wrong.

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
| `domains/region-allocation.json` | 68 shared output lanes (0 cross-domain), 29 inter-domain buses, 1,184 external write-backs; one reserved band, `localaistack-integration` [7440:7952], exclusive |
| `domains/arbitration-registry.json` | 2,837 contended cells — `PRECEDENCE` 2,835, `SEVERITY` 2, `withinRank` on 268 |
| `domains/lane-contracts.json` | 989 lanes, **986 annotated** |
| `domains/corpus-index.json` | 1,327 machines, 12 domains |
| `domains/semantic-bus-registry.json` | current |
| `domains/ces-contract-registry.json` | 16 scopes: 15 recorded, 1 unrecorded (`corpus:regression`) |

All are generated and drift-checked. Regenerate them from the corpus rather than
hand-editing; `npm run validate` fails on drift.

Any cell with more than one writer — counting machine outputs and PE sources
alike — **must** have an arbitration-registry entry. An undeclared contended cell
is a corpus error, not a runtime default.

**No corpus machine may write a PE service lane** (new in v2.0). A service lane
belongs to the PE source that fills it; a corpus writer there overwrites the
source's values. `tests/contracts/region_allocation_test.py` fails on any such
writer outside a hand-kept list that only shrinks. Two remain on it (§5).

### 3.6 Schemas

The 16 schemas in `schemas/` are the validation contract.
`agent-binding.schema.json` is `$ref`'d directly by `localOpenClawStack`, so a
change there lands downstream immediately; it is **unchanged since v1.0**. Since
v1.0, `ces-contract-registry.schema.json` was added (#130), and
`machine.schema.json` and `ai-trigger-envelope.schema.json` changed (the envelope
is additive-only within 1.x, #168).

### 3.7 Verification a dependent must pass

A regeneration is correct when:

1. It resolves through §3.2's join key and reports **1,322 joined, 5 uncovered**,
   with the five being the arbitration fixtures by name.
2. Its counts reconcile against §3.3 and any difference is explained, not merely
   observed.
3. Artifacts it derives from corpus schemas validate against the schemas at this
   tag.
4. It records `corpus-exit-v2.0` in its output.

`RealityEngine_CI/scripts/check-corpus-exit-criteria.py` enforces 1, 2 and the
agent side of 4 across the repo boundary.

## 4. Provisional — will move

Depend on these only if you must.

| surface | why it moves |
|---|---|
| **every `sha256` in `semantics/abox-manifest.json`** | any change to a machine regenerates its ABox; this is what the RE/PE runtimes expose as `semanticsHash` |
| `re-core.ttl` version | currently `0.5.0` (was `0.3.0` at v1.0) |

`abox-manifest.json` is the corpus's semantic identity — name, IRI and `sha256`
per machine — and the four runtimes surface it as `semanticsIri` /
`semanticsHash`. **Do not pin these hashes at this tag.**

## 5. Open — not settled here

Named so their absence is not read as agreement:

- **Three service lanes carry real physical quantities with no unit owner.**
  `agent-completion-risk` (localAIStack), `healthkit-activity` and
  `healthkit-steps` (HealthKit) are the lanes `lane-contracts.json` holds for
  review (`physical-units-need-owner`). Units, value domain and conversion
  policy belong to their provider repos.
- **Two corpus machines still write a HealthKit service lane** —
  `DailyActivityWellnessInterconnect` (`healthkit-heart-rate`) and
  `HomeChronicPainMentalHealthAccessInterconnect` (`healthkit-steps`), #181.
  They are the whole of the §3.5 known-writer list.
- **The regression corpus has no recorded CES contract shard**
  (`corpus:regression`, unrecorded in the cesgen registry).
- **localAI's machines are corpus-managed but not corpus files.** Their
  ownership is decided (jateeter/localAIStack#38) and they sit in the reserved
  `localaistack-integration` band; the mechanism that declares their footprint in
  the corpus is the shadow-machine pattern (#93, design note). One output,
  `ai_load_bridge` → [272:280], lies outside the band.

### Resolved since v1.0

| v1.0 said | resolved by |
|---|---|
| 84,878 ABox individuals lacked `rdfs:label` (§4) | #80 via #85: 91,283 / 91,283 labelled |
| semantic axis names would be canonicalised (§4) | #81 via #86 and jateeter/localOpenClawStack#25: `snake_case`, taken verbatim |
| `re-core` TBox hygiene (§4) | #82 via #87: ERROR 0, WARN 0 |
| `AIHardwareResilience` GREEN/RED contradiction (§5) | #56 via #89 |
| name-uniqueness policy (§5) | #68 via #88: enforced at three scopes, 0 violations |
| what the corpus-wide OWL gate runs (§5) | #79 via #143: HermiT stays; the corpus-wide HermiT run is periodic |
| the 8 localAI machines unvalidated (§5) | jateeter/localAIStack#38: all validate (#47), a gate runs on change, ownership decided |
| HealthKit ingest contract was prose only (§5) | jateeter/localHealthkitBridge#9 |

## 6. Provenance

Every figure here was measured against `0a07fb0c`, not carried forward from an
earlier count. The corpus at this tag:

- the corpus-wide merge — all 12 domains, 1,327 ABoxes + TBox — is reported
  (ROBOT: no violations) and reasons consistently under **ELK and HermiT**;
  its version is `1.0.0+corpus.d550be8da2c3`
- `generate-owl.py --all --check` is byte-stable; `--manifest-check` is clean
  (1,327 machines), ROBOT v1.9.10
- `npm run validate`: 1,337 artifacts, 0 failed; `validate:strict` passes
- `npm run test:contracts`: 190 passing, 12 skipped
- every Machines generator `--check` passes (corpus-index, lane-contracts,
  region-allocation, ces-contracts, arbitration-registry)
- the measurement method reproduces every v1.0 figure at `c1b7c29`
