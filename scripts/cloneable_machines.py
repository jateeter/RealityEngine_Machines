#!/usr/bin/env python3
"""Tag (or verify) the corpus machines suitable for cloning.

A cloneable machine is a template an engine clones: one clone per dispatch
envelope (one agentic action on one assetID), recycled when the action
completes (localAssetStorageStack#8; the clone and recycle routes are in
RealityEngine_CI SURFACE_SPEC.md). Instantiation uses the tag: an engine
clones only a machine carrying it.

The clone space is fixed by domains/clone-space.json: every clone gets one
block of 32 cells, 16 ISRE and 16 OSRE, in the engine clone band (a
reserved range in domains/domain-registry.json). So a machine qualifies when
all of these hold:

1. It dispatches an agentic action: it has an agentBinding, or it is the
   source of a document-workflow handoff (the handoff carries the assetID).
2. It has fanout: at least one published-domain-bus-producer edge or one
   outgoing document-workflow handoff.
3. It is not itself a bus target (an interconnect machine other machines
   publish into). A clone of a shared aggregator would split the bus.
4. It is not life-safety and not a fixture.
5. It fits the block: input length <= 16, output length <= 16, and n =
   (cells its fanout folds into, summed over its producer edges) + 4 bus
   cells <= 16. Handoffs carry the assetID and fold no cells.

The tag is written to metadata.tagging.capabilityTags (the canonical place),
and mirrored into metadata.tags and metadata.tagging.allTags where a machine
already carries those lists. --write applies it; --check fails on any
machine whose tag disagrees with these rules, and on a clone-space file that
disagrees with the reserved range.

Usage:
  python3 scripts/cloneable_machines.py --check
  python3 scripts/cloneable_machines.py --write
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

    block = space["block"]
    mapping = as_dict(machine.get("perceptualMapping"))
    lin = as_dict(mapping.get("input")).get("length")
    lout = as_dict(mapping.get("output")).get("length")
    folded = sum(len(as_list(e.get("targetInputElements"))) for e in producers)
    n = folded + space["busCells"]
    if not isinstance(lin, int) or lin > block["isreCells"]:
        return False, f"input length {lin} exceeds {block['isreCells']} ISRE cells"
    if not isinstance(lout, int) or lout > block["osreCells"]:
        return False, f"output length {lout} exceeds {block['osreCells']} OSRE cells"
    if n > block["isreCells"]:
        return False, f"n = {folded} folded + {space['busCells']} bus = {n} exceeds {block['isreCells']}"
    return True, f"n = {folded} folded + {space['busCells']} bus = {n}"


def is_tagged(machine: dict[str, Any], tag: str) -> bool:
    return tag in as_list(as_dict(as_dict(machine.get("metadata")).get("tagging")).get("capabilityTags"))


def set_tag(machine: dict[str, Any], tag: str, on: bool) -> None:
    md = machine.setdefault("metadata", {})
    tagging = md.setdefault("tagging", {})
    lists = [("capabilityTags", tagging, True), ("allTags", tagging, False), ("tags", md, False)]
    for key, holder, canonical in lists:
        if key not in holder and not canonical:
            continue  # mirror only into lists the machine already carries
        if key not in holder and not on:
            continue
        values = [v for v in as_list(holder.get(key)) if v != tag]
        if on:
            # Keep the list's own order: slot the tag into place only when the
            # list is already sorted, otherwise append it.
            if values == sorted(values, key=str):
                values = sorted(values + [tag], key=str)
            else:
                values.append(tag)
        holder[key] = values
    if not on and tagging.get("capabilityTags") == [] and "allTags" not in tagging:
        del tagging["capabilityTags"]  # a machine that never had the list stays without it


def space_problems(space: dict[str, Any], registry_path: Path = DOMAIN_REGISTRY) -> list[str]:
    problems = []
    block = space["block"]
    if block["cells"] != block["isreCells"] + block["osreCells"]:
        problems.append(f"clone-space block {block['cells']} != ISRE {block['isreCells']} + OSRE {block['osreCells']}")
    band = space["band"]
    if band["length"] % block["cells"]:
        problems.append(f"clone band length {band['length']} is not a whole number of {block['cells']}-cell blocks")
    ranges = as_list(as_dict(json.loads(registry_path.read_text()).get("rangePolicy")).get("reservedRanges"))
    match = [r for r in ranges if r.get("id") == band["reservedRangeId"]]
    if not match:
        problems.append(f"reserved range {band['reservedRangeId']} is missing from domains/domain-registry.json")
    elif (match[0].get("offset"), match[0].get("length")) != (band["offset"], band["length"]):
        problems.append(
            f"clone band [{band['offset']}:{band['offset'] + band['length']}] != reserved range "
            f"{band['reservedRangeId']} [{match[0].get('offset')}:{match[0].get('offset', 0) + match[0].get('length', 0)}]"
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


def render(doc: dict[str, Any], original: str) -> str:
    # Keep each file's own escaping: most are written with ensure_ascii off.
    for ensure_ascii in (False, True):
        if json.dumps(json.loads(original), indent=2, ensure_ascii=ensure_ascii) + "\n" == original:
            return json.dumps(doc, indent=2, ensure_ascii=ensure_ascii) + "\n"
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()

    space = load_space()
    tag = space["tag"]
    docs = load_machines()
    targets = bus_targets({p: d["machine"] for p, (_, d) in docs.items()})

    wrong, changed, tagged = [], 0, 0
    for path, (text, doc) in docs.items():
        ok, reason = assess(path, doc["machine"], targets, space)
        tagged += ok
        if is_tagged(doc["machine"], tag) == ok:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if args.check:
            wrong.append(f"{rel}: {'missing' if ok else 'must not carry'} the {tag} tag ({reason})")
            continue
        set_tag(doc["machine"], tag, ok)
        path.write_text(render(doc, text), encoding="utf-8")
        changed += 1

    problems = space_problems(space) + wrong
    if problems:
        print(f"cloneable-machines: {len(problems)} problem(s) — run scripts/cloneable_machines.py --write for tag drift", file=sys.stderr)
        for p in problems[:25]:
            print(f"  {p}", file=sys.stderr)
        return 1
    verb = f"wrote {changed} file(s)" if args.write else "OK"
    print(f"cloneable-machines: {verb} — {tagged} cloneable of {len(docs)} machines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
