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

Measured contention in the corpus (1323 machines):

| | positions |
|---|--:|
| domain bus (DB) total | 2,802 |
| single-writer | 2,534 |
| **contended (>1 writing machine)** | **268** |

The 268 are structured, not incidental: repeated blocks of four writers
(`signal-monitor`, `capacity-balancer`, `agent-dispatcher`, `outcome-stabilizer`)
converging on three readers (`resource-router`, `referral-optimizer`,
`governance-escalator`).

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

```
Contribution := {
  cell            : uint32       // absolute InputSpace position
  value           : float64      // clamped [0,1]
  machineId       : string
  cesId           : string
  outputVectorId  : string
}
```

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
      "writers": ["HSPH001_...json", "HSPH004_...json"],
      "readers": ["HSPH002_...json"],
      "rationale": "four-way convergence; suppressed contributors must stay attributable" }
  ]
}
```

**Validation: any cell with more than one writing machine MUST have an entry.**
An undeclared contended cell is a corpus error, not a runtime default. The 2,534
single-writer positions need no entry.

## 6. Observability

The domain bus exists to observe and manage dynamic operation, so resolution
must not be invisible. For every contended cell, every instant, the arbiter emits:

```
ArbitrationRecord := {
  instant, cell, rule, resolved : float64,
  contributors : [ {machineId, cesId, outputVectorId, value} ],
  suppressed   : [ {machineId, cesId, outputVectorId, value} ]
}
```

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

1. Given one corpus and one `IS(k)`, all four runtimes produce a byte-identical
   `IS(k+1)`.
2. Shuffling machine load order does not change `IS(k+1)` in any runtime.
3. Varying the parallel partitioning does not change `IS(k+1)`.
4. An undeclared contended cell fails corpus validation.
5. `MEAN` without canonical ordering is rejected at load.
6. Every contended cell emits an `ArbitrationRecord` whose `contributors ∪
   suppressed` equals the full contribution set for that cell and instant.
7. The minimal contention fixture (§9) resolves per its declared rule in all four
   runtimes.

## 9. Minimal contention fixture

The RS ring latch (`RSRingLatchStageA/B`) proves propagation but has no
contention — every DB position it uses has one writer. The arbiter needs its own
smallest fixture: **two machines writing one cell, read by a third, with a
declared rule.** That is the least structure that can distinguish resolution from
overwrite, and it belongs beside the ring in the regression corpus.

## 10. Open

- `SEVERITY` needs `ragStatusCode` on the contribution. Confirm all four runtimes
  carry determination metadata that far into the merge; if not, that plumbing is
  in scope.
- Whether L1 should become element-wise (`OR`/`MAX`) or keep gate semantics with
  a separate value rule. This document assumes element-wise; the current
  "first representative" behaviour is replaced either way.
