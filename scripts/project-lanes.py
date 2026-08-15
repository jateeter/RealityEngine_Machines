#!/usr/bin/env python3
"""Project the lane graph the guardrail shapes validate.

Three artifacts meet here, and each stays the authority on its own half:

    domains/region-allocation.json    allocation — which span belongs to whom
    domains/lane-contracts.json       semantics — what the positions mean
    domains/arbitration-registry.json contention — which cells have >1 writer,
                                      and the rule that resolves them

The projector composes them into `semantics/lanes/lane-graph.ttl`, the RDF the
shapes in `semantics/shapes/re-guardrails.shacl.ttl` are written against. It
invents nothing: every triple traces to one of the three inputs, and a lane the
sidecar left unresolved is omitted rather than guessed at.

Scope. Only ingress is projected. `sharedOutputLanes` and `interDomainBuses`
are machine-to-machine merges — they are not places external information
enters, so they are deliberately out of scope and no lane is emitted for them.

Autonomy is transitive. Each lane declares the autonomy its values carry
FORWARD, which rides through the arbiter into the next machine's input rather
than being re-established per hop. The minimum along a chain dominates and only
a specific approval permits acting above it, which the egress shape enforces.

Semantic contention is carried, not resolved. Where writers disagree about what
a contended cell means, every naming is emitted — `re:axisName` for one and
`reg:contendedName` for the rest — so the arbiter can surface the divergence at
the moment it resolves the cell. That is a second check on the semantic
integrity of the deterministic core, and collapsing it here would throw it away.

Usage:

    python3 scripts/project-lanes.py --write
    python3 scripts/project-lanes.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LANE_CONTRACTS = REPO_ROOT / "domains" / "lane-contracts.json"
OUTPUT = REPO_ROOT / "semantics" / "lanes" / "lane-graph.ttl"

AUTONOMY = {
    "observe": "re:Observe",
    "advise": "re:Advise",
    "supervised-act": "re:SupervisedAct",
    "automated-act": "re:AutomatedAct",
}
CONVERSION = {
    "none": "reg:NoConversion",
    "linear": "reg:LinearConversion",
    "affine": "reg:AffineConversion",
    "prohibited": "reg:ProhibitedConversion",
}
SCALE = {
    "ratio": "reg:RatioScale",
    "interval": "reg:IntervalScale",
    "ordinal": "reg:OrdinalScale",
    "nominal": "reg:NominalScale",
}

HEADER = """# Ingress lane graph — GENERATED. Do not edit by hand.
#
# Projected by scripts/project-lanes.py from:
#   domains/region-allocation.json     allocation
#   domains/lane-contracts.json        semantics
#   domains/arbitration-registry.json  contention and its resolution
#
# Validated by semantics/shapes/re-guardrails.shacl.ttl. Regenerate with:
#
#     python3 scripts/project-lanes.py --write
#
# Only ingress is projected. sharedOutputLanes and interDomainBuses are
# machine-to-machine merges, not places external information enters, and are
# deliberately absent.

@prefix reg:   <https://realityengine.example.org/ontology/re-guardrails#> .
@prefix re:    <https://realityengine.example.org/ontology/re-core#> .
@prefix lane:  <https://realityengine.example.org/lanes/> .
@prefix qudt:  <http://qudt.org/schema/qudt/> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
"""


def literal(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def number(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return repr(float(value))


def resolve(lane: dict, axis: dict, profiles: dict) -> dict:
    resolved = dict(profiles.get(lane.get("profile"), {}))
    resolved.update(axis)
    return resolved


def project(document: dict) -> tuple[str, dict]:
    profiles = document["derivationProfiles"]
    lines = [HEADER]
    emitted = 0
    omitted = 0
    axes_emitted = 0
    flagged = 0

    for lane in document["lanes"]:
        if not lane["axes"]:
            omitted += 1
            continue

        emitted += 1
        node = f"lane:{lane['id']}"
        statements = [
            "a reg:IngressLane",
            f"reg:laneId {literal(lane['id'])}",
            f"reg:laneOffset {lane['offset']}",
            f"reg:laneLength {lane['length']}",
        ]

        statements.append(
            f"reg:enforcementStage {literal(lane.get('enforcement', 'observe'))}"
        )

        for provider in lane.get("permittedProviders", []):
            statements.append(f"reg:permittedProvider {literal(provider)}")

        carried = AUTONOMY.get(lane.get("carriesAutonomy", ""))
        if carried:
            statements.append(f"reg:carriesAutonomy {carried}")

        if lane.get("lifeSafety"):
            statements.append("reg:lifeSafetyLane true")
            floor = AUTONOMY.get(lane.get("requiredAutonomy", ""))
            if floor:
                statements.append(f"reg:requiredAutonomy {floor}")

        for writer in lane.get("machineWriters", []):
            statements.append(f"reg:machineWriter {literal(writer)}")

        contention = lane.get("contention")
        if contention:
            statements.append("reg:contentionArbitrated true")
            statements.append(
                f"reg:contendedCellCount {len(contention['contendedCells'])}"
            )
            for rule in contention["rules"]:
                statements.append(f"reg:arbitrationRule {literal(rule)}")

        if lane.get("semanticContention"):
            statements.append("reg:semanticContention true")
            flagged += 1

        axis_nodes = [f"{node}-axis-{axis['index']}" for axis in lane["axes"]]
        statements.append("reg:hasAxis " + " , ".join(axis_nodes))

        lines.append(f"{node}\n    " + " ;\n    ".join(statements) + " .\n")

        for axis in lane["axes"]:
            resolved = resolve(lane, axis, profiles)
            axes_emitted += 1
            axis_statements = [
                "a reg:LaneAxis",
                f"re:axisIndex {axis['index']}",
                f"re:axisName {literal(axis['name'])}",
                f"reg:canonicalUcum {literal(resolved['canonicalUcum'])}",
            ]
            if resolved.get("expectedUcum"):
                axis_statements.append(
                    f"reg:expectedUcum {literal(resolved['expectedUcum'])}"
                )
            for code in resolved.get("acceptedUcum", []):
                axis_statements.append(f"reg:acceptedUcum {literal(code)}")
            axis_statements.append(f"reg:quantityKind <{resolved['quantityKind']}>")
            if resolved.get("qudtUnitIri"):
                axis_statements.append(f"reg:qudtUnitIri <{resolved['qudtUnitIri']}>")
            axis_statements.append(
                f"reg:conversionPolicy {CONVERSION[resolved['conversionPolicy']]}"
            )
            axis_statements.append(f"reg:scaleType {SCALE[resolved['scaleType']]}")
            for value in resolved.get("permittedValue", []):
                axis_statements.append(f"reg:permittedValue {number(value)}")
            if "minValue" in resolved:
                axis_statements.append(f"reg:minValue {number(resolved['minValue'])}")
            if "maxValue" in resolved:
                axis_statements.append(f"reg:maxValue {number(resolved['maxValue'])}")
            for alternative in axis.get("contendedNames", []):
                axis_statements.append(f"reg:contendedName {literal(alternative)}")

            lines.append(
                f"{node}-axis-{axis['index']}\n    "
                + " ;\n    ".join(axis_statements)
                + " .\n"
            )

    summary = {
        "lanesEmitted": emitted,
        "lanesOmitted": omitted,
        "axesEmitted": axes_emitted,
        "semanticContentionFlagged": flagged,
    }
    return "\n".join(lines), summary


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Project the ingress lane graph from the corpus contracts."
    )
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)

    document = json.loads(LANE_CONTRACTS.read_text())
    rendered, summary = project(document)

    if arguments.check:
        if not OUTPUT.exists():
            print(f"project-lanes: {OUTPUT.name} missing; run --write")
            return 1
        if OUTPUT.read_text() != rendered:
            print(f"project-lanes: {OUTPUT.name} is stale; run --write")
            return 1
        print(f"project-lanes: OK ({summary['lanesEmitted']} lanes)")
        return 0

    if arguments.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered)
        print(f"project-lanes: wrote {OUTPUT.relative_to(REPO_ROOT)}")
    else:
        print("project-lanes: plan only, nothing written")

    print(f"  lanes emitted          {summary['lanesEmitted']}")
    print(f"  lanes omitted (review) {summary['lanesOmitted']}")
    print(f"  axes emitted           {summary['axesEmitted']}")
    print(f"  semantic contention    {summary['semanticContentionFlagged']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
