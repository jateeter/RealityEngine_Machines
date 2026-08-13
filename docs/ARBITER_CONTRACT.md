# Output Arbiter Contract v1.0

Status: **specification** — no runtime implements this yet.
Applies to: RealityEngine_CPP, RealityEngine_LSP, RealityEngine_Scala, RealityEngine_Manager (TypeScript PE).

This document is the single source of truth for how output Reality Events are
resolved into the next InputSpace Reality Event. All four runtimes build to it,
and byte equivalence across them is the acceptance test.

## 1. Why

At any instant a machine `M` has exactly one input Reality Event Vector, compared
against all active CES Reality Events. Its next value is produced by whatever
final Reality Events targeted its input positions. When more than one such event
targets the same position, something must decide the resolved value.

Today nothing does:

| level | current behaviour | defect |
|---|---|---|
| machine (`OutputArbiter`) | `AND`/`OR`/`PASSTHROUGH` decide *whether* to emit; `combineOutputs` takes **the first** output as the value | selects, does not resolve |
| universal (merge) | `perceptualArray[offset+i] = value` per machine in list order | **last writer wins** |

All 1323 machines declare `PASSTHROUGH`, so the machine gate is always open. The
merge order is a `ListBuffer` in machine-iteration order — stable, therefore a
wrong resolution reproduces perfectly and reads as correct. There is also an
internal contradiction: one machine with N asserted outputs enqueues N writes to
the same region, so the merge applies *last* while its own arbiter declared
*first* representative.

## 1.1 Contributors are not only machines

A position is a bus member because *some output event targets it and some machine
reads it*. Nothing in that definition says the writer must be a machine. An
external provider emitting through a PE source is structurally identical to a
machine emitting a final Reality Event: both are contributions to a position.
ACP, MCP, MQTT, Ollama, HealthKit and sensors differ only in transport and in the
validate/transform step that precedes the contribution — downstream of that they
are indistinguishable, and they arbitrate together.

This is not hypothetical. Of 4,003 cells targeted by `openClawProjection`
write-backs across 1,184 machines, **2,794 are already bus members** — a machine
output writes them too. **898 of 1,184 machines** have an agent write-back landing
on a position a machine output also writes.

Measured contention in the corpus (1323 machines):

| | positions |
|---|--:|
| domain bus (DB) total | 2,802 |
| single-writer among machines | 2,534 |
| contended, **machines only** | 268 |
| contended, **including external providers** | **2,833** |
| — of which machine *and* agent write the same cell | 2,794 |

Counting machines alone understates contention by **10.6×**. The 268 are
structured — repeated blocks of four writers (`signal-monitor`,
`capacity-balancer`, `agent-dispatcher`, `outcome-stabilizer`) converging on three
readers (`resource-router`, `referral-optimizer`, `governance-escalator`) — but
they are the minority case. The dominant case is a deterministic machine output
and an advisory agent assessment landing on one position in one instant with no
rule to resolve them.

By contrast the ACP completion band `[17000:22311]` contains **0** bus cells and
is read by **0** machines, so completions currently contribute to nothing and
arbitrate over nothing. See jateeter/localOpenClawStack#18.

## 2. Position

The arbiter is one stage with three phases, placed between the final Reality
Events of instant `k` and the InputSpace Reality Event of instant `k+1`:

```
IS(k) ──▶ snapshot ──▶ every machine compares its input EV to active CES events
                            │
                            ▼
                     final Reality Events emitted
                            │
              L1 ── machine arbiter ── N CES outputs → 1 machine vector
                            │
                     GATHER  (cell → [contribution])      ← nothing written yet
                            │
              L2 ── universal arbiter ── contributions → 1 value per cell
                            │
                     COMMIT  (exactly one write per cell)
                            ▼
                          IS(k+1)
```

This position is forced. It is the only point where every final Reality Event of
the instant is known *and* the next InputSpace Reality Event has not yet been
formed. Resolving earlier cannot see all contributors; resolving later mutates a
committed event.

**No runtime may write into the perceptual array during phase 2.** Gather
produces contributions; only commit writes.

## 3. Contribution

A contribution is provider-tagged. Machine outputs and PE sources use the same
shape; only `provider` and the origin fields differ.

```
Provider   := "machine" | "acp" | "mcp" | "mqtt" | "localai" | "sensor"
Determinism := "deterministic" | "measured" | "generated"

Contribution := {
  cell            : uint32       // absolute InputSpace position
  value           : float64      // clamped [0,1]
  provider        : Provider
  determinism     : Determinism
  originId        : string       // machineId, or the PE sourceId for non-machine providers
  cesId           : string?      // machine providers only
  outputVectorId  : string?      // machine providers only
  ragStatusCode   : string?      // "GREEN"|"AMBER"|"RED", when the provider supplies one
}
```

`determinism` is the load-bearing classification; `provider` is transport.

| class | meaning | default providers |
|---|---|---|
| `deterministic` | reproducible from the corpus and `IS(k)` alone | `machine` |
| `measured` | exogenous but not generated — a reading, reproducible under replay | `sensor`, `mqtt` |
| `generated` | produced by a non-deterministic process; not reproducible | `acp`, `mcp`, `localai` |

A provider's default class may be overridden per source, but a `generated`
contribution may never be reclassified upward.

Non-machine contributions enter only after the PE source has validated syntax and
semantics and transformed the response. A contribution that fails validation is
never created — it is not a contribution with a null value, and it must not reach
the arbiter.

## 4. Rules

### 4.1 The binding invariant

Every admissible rule MUST be a **commutative monoid**: commutative, associative,
and with an identity. This is not stylistic — it is what permits parallel
reduction in any order, and what makes four independent implementations agree.

*First* and *last*, the two rules in use today, satisfy none of it.

### 4.2 Rule set

Values are float64 clamped to `[0,1]` (`dense-float64-clamped-0-1`).

| rule | definition | identity | exact in IEEE-754 |
|---|---|---|---|
| `OR` | `max(a,b)` | `0.0` | yes |
| `AND` | `min(a,b)` | `1.0` | yes |
| `MAX` | `max(a,b)` | `0.0` | yes |
| `MIN` | `min(a,b)` | `1.0` | yes |
| `SEVERITY` | see 4.3 | lowest severity, `0.0` | yes |
| `PRECEDENCE` | see 4.3a | lowest rank, `0.0` | yes |
| `MEAN` | see 4.4 | — | **no** — restricted |

`OR` and `MAX` are the same operation on `[0,1]`; both names are kept because
they express different intent (asserted-ness vs magnitude). Implementations MUST
treat them identically.

### 4.3 `SEVERITY`

Contributions carry the `ragStatusCode` of the determination that produced them.
Order `GREEN(0) < AMBER(1) < RED(2)`. Resolve to the maximum severity present;
among contributions at that severity, resolve the value by `MAX`. Both steps are
commutative monoids, so the composite is one.

A contribution from a sequence typed `re:LifeSafetySequence` is promoted to
severity `3` and dominates unconditionally.

### 4.3a `PRECEDENCE` — determinism ranking

The dominant contention case is a deterministic machine output and a generated
agent assessment on one position. `OR`/`MAX` would let the generated value
override the determination whenever it happened to be larger — a non-deterministic
process silently overwriting a deterministic one, decided by magnitude.

`PRECEDENCE` resolves by **determinism class** first, then by `MAX` on value
among contributions at the winning class:

```
deterministic (3)  >  measured (2)  >  generated (1)
```

Resolution is the lexicographic maximum of `(class, value)`. Lexicographic max
over a totally-ordered pair is commutative, associative and idempotent, so §4.1
holds and parallel reduction remains safe.

**The ordering is not a status hierarchy and not a preference.** It follows from
reproducibility. A deterministic contribution is derivable from the corpus and
`IS(k)` alone; a generated one is not derivable from anything and cannot be
reproduced by re-running the instant. Letting the irreproducible term win would
make `IS(k+1)` irreproducible, and with it every downstream determination — the
corpus would lose the property that makes it provable at all.

A domain may raise a specific cell's ranking in the registry, but doing so
deliberately imports irreproducibility into that lane and must carry a rationale
saying so.

### 4.3b Guardrails on generated contributions

Precisely because a `generated` value cannot be reproduced, it may not be trusted
on arrival. A `generated` contribution MUST pass both gates in the PE source
before it exists as a contribution:

**Syntactic.** Arity matches the target region length exactly; every value is a
number in `[0,1]` after declared normalization; required response fields are
present; no extra positions. A response of the wrong shape is rejected, never
truncated or padded.

**Semantic.** Each position carries the meaning the region's declared axis says
it carries — the response mapping resolves to the declared semantics, the value
lies within any declared band for that axis, and the emission answers the trigger
that was dispatched. A well-formed response asserting the wrong quantity is
rejected.

A contribution failing either gate **is never created.** It is not a contribution
with a null or zeroed value, and it must not reach the arbiter — a rejected
generated response leaves the cell to its deterministic contributors, which is
the correct outcome, not a degraded one.

Every rejection MUST emit an observability record (§6) carrying the gate that
failed and the offending response. Silent rejection is as damaging as silent
acceptance: it presents as an agent that never answers.

The 9 machines where `openClawProjection.semantics` and the derived agent
write-back semantics genuinely disagree (jateeter/localOpenClawStack#17) are
exactly the population the semantic gate exists to catch.

### 4.4 `MEAN` — restricted

Floating-point addition is **not associative**, so a parallel reduction of
`MEAN` is not order-independent and will break byte equivalence.

`MEAN` is therefore permitted only under a mandated canonical order:
contributions MUST be sorted ascending by `(machineId, cesId, outputVectorId)`
and summed in that order, then divided by the count. The sum is serial *within* a
cell; cells remain independent, so parallelism across cells is unaffected.

Runtimes that cannot guarantee this ordering MUST reject `MEAN` at load time
rather than approximate it.

### 4.5 Uncontended cells

A cell with exactly one contributing machine resolves to that contribution
regardless of declared rule. Implementations SHOULD short-circuit; the result
MUST be identical either way.

## 5. Declaration

Contention is a property of the corpus, not of a machine, so it is declared
centrally in `domains/arbitration-registry.json` (schema:
`schemas/arbitration-registry.schema.json`), generated and drift-checked like
`region-allocation.json`.

```json
{
  "schemaVersion": "1.0.0",
  "entries": [
    { "cell": 1735, "rule": "SEVERITY",
      "writers": [
        { "provider": "machine", "originId": "HSPH001_...json" },
        { "provider": "machine", "originId": "HSPH004_...json" }
      ],
      "readers": ["HSPH002_...json"],
      "rationale": "four-way convergence; suppressed contributors must stay attributable" },

    { "cell": 928, "rule": "PRECEDENCE",
      "providerRanks": { "machine": 3, "acp": 1 },
      "writers": [
        { "provider": "machine", "originId": "DocumentSigningWorkflowMonitor.json" },
        { "provider": "acp", "originId": "acp.openclaw.documentsigningworkflowmonitor.input-analyst.assessment" }
      ],
      "readers": ["DocumentSigningWorkflowMonitor.json"],
      "rationale": "agent assessment is advisory; the machine determination wins" }
  ]
}
```

**Validation: any cell with more than one writer — counting machine outputs and
PE sources alike — MUST have an entry.** An undeclared contended cell is a corpus
error, not a runtime default.

Registry generation must enumerate PE source write-back regions
(`openClawProjection.writeBackRegion`, MQTT mappings, sensor and localAI source
regions) alongside machine output regions. Deriving from machine outputs alone
misses **2,794** of **2,833** contended cells.

## 6. Observability

The domain bus exists to observe and manage dynamic operation, so resolution
must not be invisible. For every contended cell, every instant, the arbiter emits:

```
ArbitrationRecord := {
  instant, cell, rule, resolved : float64,
  contributors : [ {provider, originId, cesId?, outputVectorId?, value} ],
  suppressed   : [ {provider, originId, cesId?, outputVectorId?, value} ]
}
```

`provider` is mandatory on every entry. A suppressed agent assessment must remain
attributable — "the agent's answer was discarded" is exactly the operational fact
the domain bus exists to surface.

`suppressed` is what the resolution discarded. Emitting records for uncontended
cells is OPTIONAL and SHOULD be off by default.

## 7. Parallelism directives

The stage is structurally parallel: gather is a map, resolve is a per-cell
reduction over an independent contributor set, commit is a scatter over disjoint
cells. **Cells never interact.** Partition by cell range and the work is
embarrassingly parallel; the commutative-monoid requirement in 4.1 is what makes
any partitioning safe.

Each runtime SHOULD use its idiomatic concurrency rather than a ported design:

- **RealityEngine_CPP** — `std::future` / `std::async` over disjoint cell
  partitions, or a thread pool with per-thread gather buffers merged at the
  barrier. No shared mutable state during resolve; commit writes disjoint cells
  so it needs no locking.

- **RealityEngine_LSP** — actor-theory decomposition: an actor per contended cell
  (or per cell shard) receiving contribution messages and resolving at the
  instant barrier. Mailbox accumulation is naturally commutative, which matches
  4.1 exactly; prefer message passing over shared structure.

- **RealityEngine_Scala** — the runtime is already Akka-based with per-machine
  actors. Shard L2 across typed actors by cell range and join with
  `Future.traverse` / `Future.sequence`; parallel collections are acceptable for
  the pure reduce. *(Proposed — confirm against the existing actor supervision
  before building.)*

- **RealityEngine_Manager (TypeScript PE)** — `Promise.all` over cell shards;
  `worker_threads` for the resolve when the contended set is large, since the
  Node event loop will not otherwise overlap CPU-bound reduction.

Parallelism MUST NOT change results. Byte equivalence is the gate, and any
implementation whose output depends on partitioning has violated 4.1.

## 8. Acceptance

0. **Byte equivalence is only defined over reproducible contributions.** A
   `generated` contribution is not reproducible by construction, so §8.1 is
   tested either with generated sources disabled, or by **replaying a recorded
   contribution set** so every runtime sees identical inputs. Comparing two live
   agent runs and expecting identical vectors is not a test — it is a
   misunderstanding of what `generated` means.
1. Given one corpus, one `IS(k)`, and one replayed contribution set, all four
   runtimes produce a byte-identical `IS(k+1)`.
2. Shuffling machine load order does not change `IS(k+1)` in any runtime.
3. Varying the parallel partitioning does not change `IS(k+1)`.
4. **Varying the arrival order of PE source contributions does not change
   `IS(k+1)`.** Non-machine contributions arrive asynchronously, so this is the
   externally-visible form of §4.1 and the one most likely to be violated.
5. A cell written by both a machine output and a PE source resolves per its
   declared rule, in all four runtimes.
5a. A `generated` contribution never overrides a `deterministic` one under
   `PRECEDENCE`, at any value.
5b. A response failing the syntactic gate produces **no contribution** and one
   rejection record; the cell resolves from its remaining contributors.
5c. A well-formed response asserting the wrong quantity fails the semantic gate
   and produces no contribution.
6. An undeclared contended cell fails corpus validation, counting machine and
   non-machine writers alike.
7. `MEAN` without canonical ordering is rejected at load.
8. Every contended cell emits an `ArbitrationRecord` whose `contributors ∪
   suppressed` equals the full contribution set for that cell and instant, with
   `provider` populated on every entry.
9. Both minimal fixtures (§9) resolve per their declared rules in all four
   runtimes.

## 9. Minimal fixtures

The RS ring latch (`RSRingLatchStageA/B`) proves propagation but has no
contention — every DB position it uses has one writer. Two fixtures are needed,
and they are not interchangeable:

**9a — machine/machine contention.** Two machines writing one cell, read by a
third, with a declared rule. The least structure that distinguishes resolution
from overwrite.

**9b — machine/provider contention.** One machine and one PE source writing one
cell, read by that machine, with `PRECEDENCE` declared. This is the dominant real
case (2,794 cells) and 9a cannot exercise it: only 9b can prove that an advisory
contribution does not override a determination, and that an asynchronous arrival
order does not change the result.

Both belong beside the ring in the regression corpus.

## 10. Open

- `SEVERITY` needs `ragStatusCode` on the contribution. Confirm all four runtimes
  carry determination metadata that far into the merge; if not, that plumbing is
  in scope.
- Whether L1 should become element-wise (`OR`/`MAX`) or keep gate semantics with
  a separate value rule. This document assumes element-wise; the current
  "first representative" behaviour is replaced either way.
- **The PE guardrail implementation is unverified.** §4.3b requires that a
  generated contribution failing the syntactic or semantic gate is never created.
  No runtime's implementation of that step has been read, so whether either gate
  is actually enforced before contribution is unknown. Given #17 found 1,127
  semantic disagreements between the corpus and the derived agent write-back
  semantics — 9 of them substantive — the semantic gate is the one most likely to
  be absent or nominal.
- **Whether MQTT, MCP and Ollama truly share the ACP source path** is asserted
  architecturally and unconfirmed in code. If any of them bypasses the PE source
  path, it bypasses this arbiter too.
