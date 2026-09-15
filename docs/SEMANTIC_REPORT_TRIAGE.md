# ROBOT report triage — the record of the 151 INFO violations

Last reviewed: 2026-09-15
Status: **resolved.** The gate reports 0 INFO / 0 WARN corpus-wide.

`scripts/reason-owl.sh` runs `robot report` against
`semantics/robot-report-profile.txt`. For most of this ontology's life it was
clean at ERROR and WARN and carried **151 INFO**, stamped onto every released
artifact as `reportInfoPendingTriage`.

This file is the record of what that number was and how it reached zero. It is
kept rather than deleted because the count is the kind of thing that comes back,
and the next person to see it rise should be able to find out what it meant last
time and what was decided.

## What the 151 were

| Rule | Count | Where |
| --- | --- | --- |
| `missing_definition` | 134 | `semantics/ontology/re-core.ttl` |
| `missing_superclass` | 17 | `semantics/ontology/re-core.ttl` |
| **Total** | **151** | |

**Every one was in the hand-authored TBox. None came from the 1,328 generated
ABoxes.** That was the most useful fact in the whole investigation and the bare
count actively obscured it: 151 sounds like a corpus problem and was in fact a
review of one file. It also meant the generators were not emitting
under-specified individuals, which nobody could have concluded from the number
alone.

Measured against `re-core.ttl` merged with `qudt-subset.ttl` the report gave
153, not 151: the extra two were a `missing_definition` and a `missing_label` on
the **qudt-subset ontology header**, a vendored extract the corpus-wide merge
does not include. The discrepancy is recorded because it is the sort of thing
that looks like a miscount later.

## How they were resolved

### `missing_definition` — 134

`obo:IAO_0000115` was added to every class, property and individual.

**89 were authored.** They were written from each term's domain, range and role
rather than paraphrased from its label, because a definition that restates the
label teaches nobody anything and a wrong definition is worse than none — it
will be believed. Where a term carries a meaning a reader could plausibly get
wrong, the definition says so explicitly:

- `re:inputOffset` records that `{offset, length}` is a **half-open** span while
  prose renders the range **closed** — the distinction that produced 5,094
  incorrect lane references across the corpus.
- `re:targetMachineName` records *why* it exists: machine ids are minted per
  runtime, so only the corpus name is stable across engines.
- `re:hasRagStatus` records why it is functional: without it an individual
  holding both GREEN and RED is no contradiction under open-world semantics, and
  the escalation audit axiom could never fail.

**30 were adopted from an existing `rdfs:comment`.** Those comments were already
definitional; only the predicate was wrong. A definition filed under
`rdfs:comment` is invisible to every consumer that expects the standard
annotation, which is exactly what the rule was reporting. `rdfs:comment` is kept
throughout for commentary that is not definition.

**Adopting comments introduced two new violations, which were fixed properly.**
`lowercase_definition` fired on `re:idempotent` and `re:outputAlphabetTop`,
whose comments open with `f(x,x,..,x)` and `k`. Both were rewritten as
definitions rather than downgrading the rule; the algebraic detail stays in
`rdfs:comment`, which is where it belongs.

### `missing_superclass` — 17

The top-level classes were placed under **PROV**, not under a root invented for
the purpose.

This followed a pattern already in the file: `re:PerceptionEvent` and
`re:SequenceObservation` were already `prov:Activity`, and `re:DispatchRecord`
already `prov:Entity`. An invented `re:Entity` would have satisfied the check
while asserting nothing.

`re:Agent` is placed under `prov:Agent` specifically, and the rest under
`prov:Entity`. That distinction is deliberate: an agent is an actor that bears
responsibility for what it does, which is what `prov:Agent` denotes, and not
merely a thing that exists.

## What was deliberately not done

**The count was not cleared by editing the profile.** Downgrading these rules to
ignore would have reached zero while changing nothing about the ontology, and
`reportInfoPendingTriage` would then have asserted a cleanliness achieved by not
looking.

`semantics/robot-report-profile.txt` is untouched. Both rules still fail if a
future term arrives undefined or unplaced — which is the point of resolving the
count this way rather than the other.

## What the gate guarantees now

```
robot report (re-core)         0 violations, all levels
reason-owl.sh --all            0 INFO / 0 WARN, consistent under ELK
reason-owl.sh health-personal  consistent under ELK and HermiT
generate-owl --all --check     exit 0   (generated ABoxes unaffected)
generate-owl --manifest-check  exit 0   (manifest unchanged)
validate-corpus.sh             exit 0
```

A new term added without a definition, or a new top-level class added without a
superclass, now moves the count off zero. Before this work it moved it from 151
to 152 and nobody would have noticed.

## Reproducing

```bash
scripts/reason-owl.sh --all              # corpus-wide; prints the INFO count
robot report --input <merged.owl> \
     --profile semantics/robot-report-profile.txt \
     --fail-on none --output report.tsv
awk -F'\t' 'NR>1 {c[$1" "$2]++} END{for (r in c) print c[r], r}' report.tsv
```

## History

- Raised while closing the semantic OWL roadmap (M0–M5 complete and measured);
  disclosed debt behind a passing gate, not a regression.
- Filed as #141 with this document as the analysis.
- Resolved in the same sitting rather than incrementally as first recommended.
