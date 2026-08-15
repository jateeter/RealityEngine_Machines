#!/usr/bin/env python3
"""Derive ingress lane contracts from the corpus.

Lane contracts are the *semantics* of a span of the universal vector: what each
position means, in what unit, over what value domain, convertible how. They are
kept separate from `domains/region-allocation.json`, which stays the authority
on *allocation* — which span belongs to whom. This script writes the semantics
sidecar, `domains/lane-contracts.json`; nothing here edits the allocation.

A lane is a distinct region, not a machine. 1,185 machines carry an
`openClawProjection`, but they land on 983 distinct write-back regions: several
machines legitimately read one externally-written lane. Modelling per machine
would invent lanes that overlap by construction.

Derivation
----------

Nothing is assumed from the `normalization` label alone — it disagrees with the
data often enough to be untrustworthy on its own. The evidence used is the
label, `perceptualMapping.bitsPerElement`, and the values the machine's own
sequence vectors actually contain:

    label                     bits  values        -> scale     policy       domain
    machine-native-binary     1     {0,1}            nominal    prohibited   [0,1]
    machine-native-ordinal    4     {0..3}           ordinal    prohibited   [0..3]
    machine-native-scalar     8     0..1 continuous  ratio      none         0..1

All three are dimensionless (UCUM `1`, qkind:Dimensionless, unit:UNITLESS): a
machine-native ordinal or normalized index is not a physical quantity, and
rescaling one is a category error rather than an arithmetic one, which is why
the categorical cases prohibit conversion outright.

Anything the evidence does not settle goes to `review` rather than being
guessed. Guessing here would put a fabricated unit behind a guardrail that is
supposed to be the thing you trust.

Usage:

    python3 scripts/backfill-lane-contracts.py            # plan, writes nothing
    python3 scripts/backfill-lane-contracts.py --write
    python3 scripts/backfill-lane-contracts.py --check    # fail when stale
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ucum import UcumError, canonical  # noqa: E402

MACHINES = REPO_ROOT / "machines"
REGION_ALLOCATION = REPO_ROOT / "domains" / "region-allocation.json"
ARBITRATION_REGISTRY = REPO_ROOT / "domains" / "arbitration-registry.json"
OUTPUT = REPO_ROOT / "domains" / "lane-contracts.json"

SCHEMA_VERSION = "1.0.0"

DIMENSIONLESS = {
    "canonicalUcum": "1",
    "expectedUcum": "1",
    "acceptedUcum": ["1"],
    "quantityKind": "http://qudt.org/vocab/quantitykind/Dimensionless",
    "qudtUnitIri": "http://qudt.org/vocab/unit/UNITLESS",
}

# (normalization, bitsPerElement) -> the settled reading of the positions.
PROFILES = {
    ("machine-native-binary", 1): {
        "scaleType": "nominal",
        "conversionPolicy": "prohibited",
        "permittedValue": [0, 1],
    },
    ("machine-native-ordinal", 4): {
        "scaleType": "ordinal",
        "conversionPolicy": "prohibited",
        "permittedValue": [0, 1, 2, 3],
    },
    ("machine-native-scalar", 8): {
        "scaleType": "ratio",
        "conversionPolicy": "none",
        "minValue": 0,
        "maxValue": 1,
    },
}

def profile_name(key: tuple) -> str:
    label, bits = key
    return f"{label}/{bits}"


REVIEW_REASONS = {
    "profile-unrecognised": (
        "The normalization label and bitsPerElement do not form a settled "
        "profile; the label is contradicted by the element width."
    ),
    "axis-name-disagreement": (
        "Machines sharing this region disagree on what its positions mean. "
        "re:axisName is functional, so this is an inconsistency to adjudicate, "
        "not a spelling variant."
    ),
    "contention-undeclared": (
        "This region shares cells with another externally-writable region and "
        "at least one shared cell has no entry in domains/arbitration-registry.json. "
        "Overlap itself is normal — a machine output feeding another machine's "
        "input is the interconnect mechanism, and 669 output regions equal an "
        "input region exactly. What is a corpus error, per ARBITER_CONTRACT.md, "
        "is a contended cell with no declared resolution."
    ),
    "physical-units-need-owner": (
        "A service lane carrying real physical quantities. Units, value domain "
        "and conversion policy need a domain owner, not a derivation."
    ),
}


def load_machines() -> list[dict]:
    records = []
    for path in sorted(MACHINES.rglob("*.json")):
        try:
            document = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        machine = document.get("machine") or document
        if not isinstance(machine, dict):
            continue
        metadata = machine.get("metadata") or {}
        projection = metadata.get("openClawProjection")
        if not isinstance(projection, dict):
            continue
        region = projection.get("writeBackRegion") or {}
        offset, length = region.get("offset"), region.get("length")
        if not isinstance(offset, int) or not isinstance(length, int):
            continue
        mapping = machine.get("perceptualMapping") or {}
        records.append(
            {
                "file": path.relative_to(REPO_ROOT).as_posix(),
                "stem": path.stem,
                "offset": offset,
                "length": length,
                "semantics": list(projection.get("semantics") or []),
                "normalization": projection.get("normalization"),
                "bits": mapping.get("bitsPerElement"),
                "severity": metadata.get("severity"),
            }
        )
    return records


def contention_index() -> dict[int, dict]:
    """Per-cell contention, read from the arbitration registry.

    A cell ci of a Reality Event E = {c1..cn} is *contended* when more than one
    writer competes for ci's next value — M1(j) and M2(l) both targeting ci.
    That is a property of a cell and its writers, not of how two regions happen
    to overlap; an earlier version of this script computed region-against-region
    overlap and called those cells shared, which is a different and smaller set.

    domains/arbitration-registry.json is the authority: it already carries the
    writers and the resolving rule per cell. This reads it rather than deriving
    a second opinion. tests/contracts/lane_contracts_test.py checks that the
    registry still agrees with writer multiplicity computed from the corpus, so
    a stale registry is caught rather than trusted.
    """
    registry = json.loads(ARBITRATION_REGISTRY.read_text())
    index: dict[int, dict] = {}
    for entry in registry.get("entries", []):
        cell = entry.get("cell")
        if isinstance(cell, int):
            index[cell] = entry
    return index


def machine_writers_of(entry: dict) -> list[str]:
    """Machines whose output competes for this cell's next value."""
    names = set()
    for writer in entry.get("writers", []):
        if writer.get("provider") == "machine" and writer.get("originId"):
            names.add(Path(writer["originId"]).stem)
    return sorted(names)


def build_axes(names: list[str]) -> list[dict]:
    """Axes carry only what varies: position and meaning. The unit contract
    comes from the lane's profile, so a profile change is one edit rather than
    3,617, and a reader sees the rule instead of thousands of copies of it."""
    return [{"index": index, "name": name} for index, name in enumerate(names)]


def resolve_axis(axis: dict, profile: dict) -> dict:
    """The projector's view: profile defaults with per-axis overrides on top."""
    resolved = dict(DIMENSIONLESS)
    resolved.update(profile)
    resolved.update(axis)
    return resolved


def build() -> dict:
    machines = load_machines()
    by_region: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for record in machines:
        by_region[(record["offset"], record["length"])].append(record)

    contention = contention_index()

    lanes: list[dict] = []
    review: list[dict] = []

    for (offset, length), records in sorted(by_region.items()):
        lane_id = f"mi-{offset}-{length}"
        readers = sorted(record["stem"] for record in records)
        lane = {
            "id": lane_id,
            "source": "machine-input",
            "offset": offset,
            "length": length,
            "readers": readers,
        }

        reasons: list[str] = []

        distinct_names = {tuple(record["semantics"]) for record in records}
        if len(distinct_names) > 1:
            reasons.append("axis-name-disagreement")

        profiles = {(record["normalization"], record["bits"]) for record in records}
        profile = None
        if len(profiles) == 1:
            key = next(iter(profiles))
            profile = PROFILES.get(key)
            if profile is None:
                reasons.append("profile-unrecognised")
        else:
            reasons.append("profile-unrecognised")

        # Contended cells of this lane, per the arbitration registry. A cell is
        # contended when more than one writer competes for its next value; the
        # registry names those writers and the rule that resolves them.
        cells = sorted(range(offset, offset + length))
        contended = [cell for cell in cells if cell in contention]

        if contended:
            entries = [contention[cell] for cell in contended]
            machine_writers = sorted(
                {name for entry in entries for name in machine_writers_of(entry)}
            )
            lane["machineWriters"] = machine_writers
            lane["contention"] = {
                "contendedCells": contended,
                "arbitrated": True,
                "rules": sorted({e["rule"] for e in entries if e.get("rule")}),
            }

        names = sorted(distinct_names)[0] if distinct_names else ()
        if profile and len(names) == length and not reasons:
            lane["profile"] = profile_name(next(iter(profiles)))
            lane["axes"] = build_axes(list(names))
        else:
            lane["axes"] = []
            if profile and len(names) != length:
                reasons.append("profile-unrecognised")
            for reason in sorted(set(reasons)) or ["profile-unrecognised"]:
                item = {
                    "laneId": lane_id,
                    "reason": reason,
                    "readers": readers,
                    "detail": REVIEW_REASONS[reason],
                }
                if reason == "contention-undeclared":
                    item["undeclaredCells"] = lane["contention"]["undeclaredCells"]
                review.append(item)

        lanes.append(lane)

    # Service lanes: allocation is authoritative, semantics are not derivable.
    allocation = json.loads(REGION_ALLOCATION.read_text())
    for entry in allocation.get("serviceLanes", []):
        lane_id = entry["id"]
        lanes.append(
            {
                "id": lane_id,
                "source": "service-lane",
                "offset": entry["offset"],
                "length": entry["length"],
                "provider": entry.get("provider"),
                "readers": sorted(
                    Path(name).stem for name in entry.get("corpusReaders", [])
                ),
                "axes": [],
            }
        )
        review.append(
            {
                "laneId": lane_id,
                "reason": "physical-units-need-owner",
                "provider": entry.get("provider"),
                "detail": REVIEW_REASONS["physical-units-need-owner"],
            }
        )

    lanes.sort(key=lambda lane: (lane["offset"], lane["length"], lane["id"]))
    review.sort(key=lambda item: (item["reason"], item["laneId"]))

    annotated = [lane for lane in lanes if lane["axes"]]
    positions = sum(len(lane["axes"]) for lane in annotated)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "$comment": (
            "GENERATED by scripts/backfill-lane-contracts.py. Semantics of "
            "externally-writable regions; domains/region-allocation.json "
            "remains the authority on allocation. Do not edit by hand."
        ),
        "generator": "scripts/backfill-lane-contracts.py",
        "derivationProfiles": {
            profile_name(key): {**DIMENSIONLESS, **profile}
            for key, profile in sorted(PROFILES.items(), key=lambda item: str(item[0]))
        },
        "summary": {
            "lanes": len(lanes),
            "lanesAnnotated": len(annotated),
            "lanesNeedingReview": len(lanes) - len(annotated),
            "positionsAnnotated": positions,
            "machinesCovered": len(machines),
            "reviewByReason": {
                reason: sum(1 for item in review if item["reason"] == reason)
                for reason in sorted({item["reason"] for item in review})
            },
        },
        "lanes": lanes,
        "review": review,
    }


def verify_units(document: dict) -> list[str]:
    problems = []
    profiles = document["derivationProfiles"]
    for lane in document["lanes"]:
        profile = profiles.get(lane.get("profile"), {})
        for raw in lane["axes"]:
            axis = {**profile, **raw}
            codes = [axis.get("canonicalUcum"), axis.get("expectedUcum")]
            codes += list(axis.get("acceptedUcum") or [])
            for code in [value for value in codes if value]:
                try:
                    if canonical(code) != code:
                        problems.append(
                            f"{lane['id']} axis {axis['index']}: {code!r} is not canonical"
                        )
                except UcumError as error:
                    problems.append(f"{lane['id']} axis {axis['index']}: {error}")
    return problems


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=False) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Derive ingress lane contracts from the corpus."
    )
    parser.add_argument("--write", action="store_true", help="write the sidecar")
    parser.add_argument("--check", action="store_true", help="fail when stale")
    arguments = parser.parse_args(argv)

    document = build()

    problems = verify_units(document)
    if problems:
        print("backfill-lane-contracts: emitted non-canonical UCUM:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    summary = document["summary"]
    rendered = render(document)

    if arguments.check:
        if not OUTPUT.exists():
            print(f"backfill-lane-contracts: {OUTPUT.name} missing; run --write")
            return 1
        if OUTPUT.read_text() != rendered:
            print(f"backfill-lane-contracts: {OUTPUT.name} is stale; run --write")
            return 1
        print(
            f"backfill-lane-contracts: OK "
            f"({summary['lanesAnnotated']}/{summary['lanes']} lanes annotated)"
        )
        return 0

    if arguments.write:
        OUTPUT.write_text(rendered)
        print(f"backfill-lane-contracts: wrote {OUTPUT.relative_to(REPO_ROOT)}")
    else:
        print("backfill-lane-contracts: plan only, nothing written")

    print(f"  lanes                {summary['lanes']}")
    print(f"  annotated            {summary['lanesAnnotated']}")
    print(f"  positions annotated  {summary['positionsAnnotated']}")
    print(f"  needing review       {summary['lanesNeedingReview']}")
    for reason, count in summary["reviewByReason"].items():
        print(f"    {reason:28} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
