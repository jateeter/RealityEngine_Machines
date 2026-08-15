#!/usr/bin/env python3
"""Compile the guardrail into a flat decision table the runtimes load.

The architecture is: ontology and shapes at build time, a decision table at
runtime. A reasoner or a SHACL engine in a PE push cycle would be the wrong
shape entirely — but the shapes are also the only place the rules are written
down, so the runtimes need something derived from them rather than a second,
hand-maintained copy that drifts.

This emits that artifact. Every rule here is a lookup or a comparison: no
inference, no graph traversal, no joins beyond a region index. That is
possible because the shapes were written to be evaluable against asserted
triples only, so nothing they check requires deriving a fact first.

    CI            reasoner + SHACL over the lane graph  (correctness)
    engine load   this table                            (speed)
    push cycle    region lookup + bounds test            (hot path)

The table is keyed by "offset:length" — three regions in this corpus share an
offset with a different width, so offset alone does not identify a lane. A
runtime resolves (offset, length) -> lane, checks the writer against the lane's
provider list and the value against its axis contract, and consults
`enforcementStage` for what to do about a failure.

Egress rules that do not vary per lane — the autonomy ordering, the action
classes, the RAG statuses that permit escalation — travel in their own block so
a runtime does not have to carry re-core.ttl to evaluate a dispatch.

Usage:

    python3 scripts/compile-decision-table.py --write
    python3 scripts/compile-decision-table.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LANE_CONTRACTS = REPO_ROOT / "domains" / "lane-contracts.json"
CORE_ONTOLOGY = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
SHAPES = REPO_ROOT / "semantics" / "shapes" / "re-guardrails.shacl.ttl"
OUTPUT = REPO_ROOT / "semantics" / "lanes" / "decision-table.json"

SCHEMA_VERSION = "1.0.0"

AUTONOMY_RANK = {"observe": 0, "advise": 1, "supervised-act": 2, "automated-act": 3}

# Provenance classes whose values a model or procedure produced, and which must
# therefore inherit the envelope of the dispatch they answer.
INFERRED_CLASSES = ["inferred"]


def action_classes() -> dict[str, str]:
    """Canonical action code -> its consequence class, read from re-core.ttl.

    Only the canonical individuals carry re:actionCode, so this closes the
    dispatchable vocabulary without restating it.
    """
    text = CORE_ONTOLOGY.read_text()
    classes: dict[str, str] = {}
    pattern = re.compile(
        r"re:(\w+)\s+a\s+owl:NamedIndividual\s*,\s*re:(\w*Action)\s*;\s*"
        r're:actionCode\s+"([^"]+)"',
        re.S,
    )
    for _, consequence, code in pattern.findall(text):
        classes[code] = consequence
    return classes


def resolve(lane: dict, axis: dict, profiles: dict) -> dict:
    resolved = dict(profiles.get(lane.get("profile"), {}))
    resolved.update(axis)
    return resolved


def compile_table() -> dict:
    document = json.loads(LANE_CONTRACTS.read_text())
    profiles = document["derivationProfiles"]

    lanes: dict[str, dict] = {}
    for lane in document["lanes"]:
        if not lane["axes"]:
            continue
        entry = {
            "id": lane["id"],
            "length": lane["length"],
            "enforcement": lane.get("enforcement", "observe"),
            "permittedProviders": lane.get("permittedProviders", []),
            "carriesAutonomy": lane.get("carriesAutonomy"),
            "axes": [],
        }
        if lane.get("lifeSafety"):
            entry["lifeSafety"] = True
            entry["requiredAutonomy"] = lane.get("requiredAutonomy")
        if lane.get("machineWriters"):
            entry["machineWriters"] = lane["machineWriters"]
        contention = lane.get("contention")
        if contention:
            entry["contention"] = {
                "cells": contention["contendedCells"],
                "rules": contention["rules"],
            }
        if lane.get("semanticContention"):
            entry["semanticContention"] = True

        for axis in lane["axes"]:
            merged = resolve(lane, axis, profiles)
            compiled = {
                "index": axis["index"],
                "name": axis["name"],
                "canonicalUcum": merged["canonicalUcum"],
                "acceptedUcum": merged.get("acceptedUcum", []),
                "conversionPolicy": merged["conversionPolicy"],
                "scaleType": merged["scaleType"],
            }
            if "permittedValue" in merged:
                compiled["permittedValue"] = merged["permittedValue"]
            if "minValue" in merged:
                compiled["minValue"] = merged["minValue"]
            if "maxValue" in merged:
                compiled["maxValue"] = merged["maxValue"]
            if axis.get("contendedNames"):
                compiled["contendedNames"] = axis["contendedNames"]
            entry["axes"].append(compiled)

        # Keyed by offset AND length: three regions in the corpus share an
        # offset with a different width, so offset alone does not identify a
        # lane. A runtime resolves a write by (offset, length).
        key = f"{lane['offset']}:{lane['length']}"
        if key in lanes:
            raise SystemExit(f"compile-decision-table: duplicate lane key {key}")
        entry["offset"] = lane["offset"]
        lanes[key] = entry

    return {
        "schemaVersion": SCHEMA_VERSION,
        "$comment": (
            "GENERATED by scripts/compile-decision-table.py. The runtime form of "
            "semantics/shapes/re-guardrails.shacl.ttl: every rule reduced to a "
            "lookup or a comparison, keyed by lane offset. Correctness is "
            "established in CI against the shapes; this is what engines load."
        ),
        "generator": "scripts/compile-decision-table.py",
        "shapes": "semantics/shapes/re-guardrails.shacl.ttl",
        "ingress": {
            "lanesByRegion": lanes,
            "provenanceRequiringEnvelope": INFERRED_CLASSES,
            "ucumComparison": (
                "codes are compared as canonical strings; canonicalize with "
                "scripts/ucum.py before comparing"
            ),
        },
        "egress": {
            "autonomyRank": AUTONOMY_RANK,
            "actionClasses": action_classes(),
            "escalationRequiresRag": "RED",
            "observeMayNotDispatch": True,
            "autonomyIsTransitive": True,
        },
        "summary": {
            "lanes": len(lanes),
            "axes": sum(len(entry["axes"]) for entry in lanes.values()),
            "byEnforcement": {
                stage: sum(1 for e in lanes.values() if e["enforcement"] == stage)
                for stage in ("block", "warn", "observe")
            },
        },
    }


def render(table: dict) -> str:
    return json.dumps(table, indent=2) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Compile the guardrail decision table the runtimes load."
    )
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)

    table = compile_table()
    rendered = render(table)
    summary = table["summary"]

    if arguments.check:
        if not OUTPUT.exists():
            print(f"compile-decision-table: {OUTPUT.name} missing; run --write")
            return 1
        if OUTPUT.read_text() != rendered:
            print(f"compile-decision-table: {OUTPUT.name} is stale; run --write")
            return 1
        print(f"compile-decision-table: OK ({summary['lanes']} lanes)")
        return 0

    if arguments.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered)
        print(f"compile-decision-table: wrote {OUTPUT.relative_to(REPO_ROOT)}")
    else:
        print("compile-decision-table: plan only, nothing written")

    print(f"  lanes  {summary['lanes']}")
    print(f"  axes   {summary['axes']}")
    for stage, count in summary["byEnforcement"].items():
        print(f"    {stage:8} {count}")
    print(f"  action codes {len(table['egress']['actionClasses'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
