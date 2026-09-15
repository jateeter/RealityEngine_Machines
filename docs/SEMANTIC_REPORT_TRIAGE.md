# ROBOT report triage — the 151 INFO violations

Last reviewed: 2026-09-15

`scripts/reason-owl.sh` runs `robot report` against
`semantics/robot-report-profile.txt` and gates on ERROR. The corpus-wide run is
clean at ERROR and WARN and carries **151 INFO** violations, stamped onto the
released artifact as `reportInfoPendingTriage` so the debt travels with the
thing it is debt about rather than living in a log.

This file is what that count means. It exists because a number with no
decomposition is not triageable: nobody can tell whether 151 is one systematic
omission or 151 separate judgements.

## The decomposition

| Rule | Count | Where |
| --- | --- | --- |
| `missing_definition` | 134 | `semantics/ontology/re-core.ttl` |
| `missing_superclass` | 17 | `semantics/ontology/re-core.ttl` |
| **Total** | **151** | |

**Every one is in the hand-authored TBox. None come from the 1,328 generated
ABoxes.** That is the single most useful fact here, and it bounds the work: this
is a review of one file, not a corpus sweep. It also means the generators are
not producing under-specified individuals — a conclusion the bare count of 151
actively obscured.

Measured separately, merging `re-core.ttl` with `qudt-subset.ttl` reports 153:
the extra two are a `missing_definition` and a `missing_label` on the
`qudt-subset` **ontology header** itself, which is a vendored extract rather
than authored vocabulary. The corpus-wide merge does not include it, which is
why the gate reports 151 and not 153.

## What each rule is asking for, and whether we should comply

### `missing_definition` — 134 entities

Every class and property in `re-core` lacks `IAO:0000115` (textual definition).
Affected entities are the whole authored vocabulary: `re:Action`, `re:Agent`,
`re:AgentBinding`, `re:AgentFamily`, `re:AutonomyMode`, `re:Determination`, and
so on.

This is an OBO **publishing** convention. It matters when an ontology is
consumed by people who did not write it — which is the direction this ontology
is heading as integration vocabulary grows (see the MCP/ACP work in
`RealityEngine_CPP/docs/SEMANTIC_OWL_ROADMAP.md`).

Recommended: **comply, incrementally.** A definition per entity is cheap
individually and expensive in one sitting, and a wrong definition is worse than
none because it will be believed. Take them as each area of the vocabulary is
next touched rather than as a bulk pass, and let the count fall.

### `missing_superclass` — 17 classes

Seventeen classes assert no `rdfs:subClassOf`. OBO convention places everything
beneath a root so a reasoner can classify the whole graph.

Recommended: **decide, then either comply or record the exemption.** Whether a
top-level `re:Entity` earns its keep is a modelling question, not a lint
question. Seventeen roots may be correct for a vocabulary that deliberately does
not commit to an upper ontology. What is not acceptable is leaving it undecided
and reading 17 as debt forever.

If the answer is "these are intentional roots", the profile should downgrade
`missing_superclass` for them explicitly, so the report stops reporting a
decision that has been made.

## Why this is INFO and not ERROR

`semantics/robot-report-profile.txt` maps OBO publishing conventions down from
ERROR deliberately. The gate's job is to catch statements that are *wrong* —
`illegal_use_of_built_in_vocabulary`, `duplicate_definition`,
`deprecated_class_reference` — not statements that are *absent*. Both of these
rules report absence.

Keeping them visible at INFO rather than removing them from the profile is the
point: an absent definition is real debt, and a profile that stops mentioning it
converts debt into a silence nobody revisits.

## What must not happen

**Do not clear the count by editing the profile.** Downgrading these rules to
ignore would take the number to zero while changing nothing about the ontology,
and the released artifact's `reportInfoPendingTriage` annotation would then
assert a cleanliness that was achieved by not looking.

The only two legitimate ways for the count to fall are: the definitions get
written, or a modelling decision is recorded and the profile is changed *to
match that decision*, in a PR that says so.

## Reproducing

```bash
scripts/reason-owl.sh --all              # corpus-wide, ELK; prints the INFO count
robot report --input <merged.owl> \
     --profile semantics/robot-report-profile.txt \
     --fail-on none --output report.tsv
awk -F'\t' 'NR>1 && $1=="INFO" {c[$2]++} END{for (r in c) print c[r], r}' report.tsv
```
