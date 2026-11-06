#!/usr/bin/env python3
"""Report which corpus machines engines will recognise as cloneable, and
check the corpus's clone space.

Engines decide cloneability when they load the corpus, by the rule in
RealityEngine_CI SURFACE_SPEC.md (localAssetStorageStack#8); nothing is
written into machine files. This script applies the same rule so a corpus
author can see the outcome before a run. It is a report, not the authority:
the voting engines' 3-of-3 agreement in regression is.

The clone space is domains/clone-space.json: every clone gets one 64-cell
block in the engine clone band (a reserved range in
domains/domain-registry.json), laid out as four uniform 16-cell quarters
(the nest layout): input, output, fanout, bus. A machine is cloneable when
all hold:

1. It dispatches an agentic action: it has an agentBinding, or it is the
   source of a document-workflow handoff (the handoff carries the assetID).
2. It has fanout: at least one published-domain-bus-producer edge or one
   outgoing document-workflow handoff.
3. It is not itself a bus target (an interconnect machine other machines
   publish into).
4. It is not life-safety and not a fixture.
5. It does not opt out with metadata.cloneable: false.
6. It fits the block: input length <= 16, output length <= 16, and the
   cells its fanout folds into (over its producer edges) <= 16. Its 4 bus
   cells always fit the bus quarter; n = folded + 4 is reported. Handoffs
   carry the assetID and fold no cells.

Usage:
  python3 scripts/cloneable_machines.py --check    # clone space vs reserved range
  python3 scripts/cloneable_machines.py --report   # who qualifies, near-misses
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
CLONE_SPACE = REPO_ROOT / "domains" / "clone-space.json"
DOMAIN_REGISTRY = REPO_ROOT / "domains" / "domain-registry.json"


def load_space(path: Path = CLONE_SPACE) -> dict[str, Any]:
    return json.loads(path.read_text())


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def stem(path: Path) -> str:
    return path.name[:-5] if path.name.endswith(".json") else path.name


def bus_targets(machines: dict[Path, dict[str, Any]]) -> set[str]:
    """File names of every machine another machine publishes into."""
    out = set()
    for machine in machines.values():
        for edge in as_list(as_dict(machine.get("metadata")).get("interconnections")):
            target = as_dict(edge).get("targetMachineFile")
            if as_dict(edge).get("type") == "published-domain-bus-producer" and target:
                out.add(str(target))
    return out


def assess(path: Path, machine: dict[str, Any], targets: set[str], space: dict[str, Any]) -> tuple[bool, str]:
    """(qualifies, reason). The reason names the first rule that fails."""
    md = as_dict(machine.get("metadata"))
    edges = [as_dict(e) for e in as_list(md.get("interconnections"))]
    producers = [e for e in edges if e.get("type") == "published-domain-bus-producer"]
    handoffs = [e for e in edges if e.get("type") == "document-workflow-handoff" and e.get("sourceMachine") == stem(path)]

    if not (md.get("agentBinding") or handoffs):
        return False, "dispatches no agentic action"
    if not (producers or handoffs):
        return False, "has no fanout"
    if path.name in targets:
        return False, "is a bus target"
    if md.get("severity") == "life-safety":
        return False, "is life-safety"
    if any("fixture" in str(t) for t in as_list(md.get("tags"))):
        return False, "is a fixture"
    if md.get("cloneable") is False:
        return False, "opts out (metadata.cloneable: false)"

    block = space["block"]
    mapping = as_dict(machine.get("perceptualMapping"))
    lin = as_dict(mapping.get("input")).get("length")
    lout = as_dict(mapping.get("output")).get("length")
    folded = sum(len(as_list(e.get("targetInputElements"))) for e in producers)
    n = folded + space["busCells"]
    room = quarters(space)
    if not isinstance(lin, int) or lin > room["input"]:
        return False, f"input length {lin} exceeds the {room['input']}-cell input quarter"
    if not isinstance(lout, int) or lout > room["output"]:
        return False, f"output length {lout} exceeds the {room['output']}-cell output quarter"
    if folded > room["fanout"]:
        return False, f"fanout folds into {folded} cells, more than the {room['fanout']}-cell fanout quarter"
    return True, f"n = {folded} folded + {space['busCells']} bus = {n}"


def quarters(space: dict[str, Any]) -> dict[str, int]:
    """Role -> length of that part of the block (the nest layout)."""
    return {part["role"]: part["length"] for part in space["block"]["layout"]}


def space_problems(space: dict[str, Any], registry_path: Path = DOMAIN_REGISTRY) -> list[str]:
    problems = []
    block = space["block"]
    layout = sorted(block["layout"], key=lambda part: part["offset"])
    if sorted(part["role"] for part in layout) != ["bus", "fanout", "input", "output"]:
        problems.append("clone-space layout must have exactly one input, output, fanout and bus part")
    cursor = 0
    for part in layout:
        if part["offset"] != cursor:
            problems.append(f"clone-space layout: {part['role']} starts at {part['offset']}, expected {cursor} (parts must tile the block)")
        cursor = part["offset"] + part["length"]
    if cursor != block["cells"]:
        problems.append(f"clone-space layout covers {cursor} cells, block is {block['cells']}")
    if len({part["length"] for part in layout}) != 1:
        problems.append("clone-space layout must be uniform: every part the same length")
    if space["busCells"] > quarters(space).get("bus", 0):
        problems.append(f"busCells {space['busCells']} exceed the bus quarter")
    band = space["band"]
    if band["length"] % block["cells"]:
        problems.append(f"clone band length {band['length']} is not a whole number of {block['cells']}-cell blocks")
    ranges = as_list(as_dict(json.loads(registry_path.read_text()).get("rangePolicy")).get("reservedRanges"))
    match = [r for r in ranges if r.get("id") == band["reservedRangeId"]]
    if not match:
        problems.append(f"reserved range {band['reservedRangeId']} is missing from domains/domain-registry.json")
    elif (match[0].get("offset"), match[0].get("length")) != (band["offset"], band["length"]):
        problems.append(
            f"clone band [{band['offset']}:{band['offset'] + band['length'] - 1}] != reserved range "
            f"{band['reservedRangeId']} [{match[0].get('offset')}:{match[0].get('offset', 0) + match[0].get('length', 0) - 1}]"
        )
    return problems


def load_machines(root: Path = MACHINES) -> dict[Path, tuple[str, dict[str, Any]]]:
    out = {}
    for path in sorted(root.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict) and isinstance(doc.get("machine"), dict):
            out[path] = (text, doc)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args()

    space = load_space()
    if args.check:
        problems = space_problems(space)
        if problems:
            print(f"cloneable-machines: {len(problems)} clone-space problem(s)", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1
        band = space["band"]
        print(f"cloneable-machines: OK — clone band [{band['offset']}:{band['offset'] + band['length'] - 1}], "
              f"{band['length'] // space['block']['cells']} blocks of {space['block']['cells']}")
        return 0

    docs = load_machines()
    machines = {p: d["machine"] for p, (_, d) in docs.items()}
    targets = bus_targets(machines)
    reasons: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    near = []
    for path, machine in machines.items():
        ok, reason = assess(path, machine, targets, space)
        key = "cloneable" if ok else reason.split(" (")[0] if "exceeds" not in reason else "does not fit the block"
        reasons[key] = reasons.get(key, 0) + 1
        if ok:
            by_domain[path.parent.name] = by_domain.get(path.parent.name, 0) + 1
        elif "exceeds" in reason:
            near.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {reason}")
    print(f"cloneable-machines: {reasons.get('cloneable', 0)} of {len(machines)} machines are cloneable")
    for key, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {count:5}  {key}")
    print("  by domain: " + ", ".join(f"{d} {n}" for d, n in sorted(by_domain.items())))
    for line in near:
        print(f"  near-miss: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
