#!/usr/bin/env python3
"""Check the corpus's cloneable machines and their ISRE/OSRE slot pools.

A cloneable machine is a template an engine clones, one clone per agentic
action, recycling the clone when the action completes
(localAssetStorageStack#8; the clone and recycle routes are specified in
RealityEngine_CI SURFACE_SPEC.md). Its `machine.cloneable` block reserves
two pools, so that each clone has cells of its own (the contended-cell rule):

- inputPool: maxClones input slots, each the length of the machine's own
  perceptualMapping.input region;
- outputPool: maxClones output slots, each the length of its
  perceptualMapping.output region.

Clone k reads input slot k and writes output slot k.

Checks:
1. Each pool's length is maxClones x the machine's own region length.
2. Nothing else occupies a pool: no machine's input or output region (the
   template's own included), no PE service lane, no provider-reserved band,
   and no other pool (the same machine's other pool included).
3. No corpus machine and no service lane writes the template's own input
   region, so the template itself never fires; only its clones run.

Usage:
  python3 scripts/cloneable_machines.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
REGISTRY = REPO_ROOT / "domains" / "region-allocation.json"

Region = tuple[int, int]


def region(r: Any) -> Region | None:
    if isinstance(r, dict) and isinstance(r.get("offset"), int) and isinstance(r.get("length"), int):
        return (int(r["offset"]), int(r["length"]))
    return None


def overlaps(a: Region, b: Region) -> bool:
    return a[0] < b[0] + b[1] and b[0] < a[0] + a[1]


def fmt(r: Region) -> str:
    return f"[{r[0]}:{r[0] + r[1]}]"


def cloneable_entry(name: str, domain: str | None, machine: dict[str, Any]) -> dict[str, Any] | None:
    """The pool record for one machine, or None when it is not cloneable.

    A malformed block is returned with `error` set rather than dropped, so a
    typo cannot quietly make a machine non-cloneable.
    """
    block = machine.get("cloneable")
    if block is None:
        return None
    raw_mapping = machine.get("perceptualMapping")
    mapping: dict[str, Any] = raw_mapping if isinstance(raw_mapping, dict) else {}
    entry: dict[str, Any] = {
        "machine": name,
        "domain": domain or "",
        "input": region(mapping.get("input")),
        "output": region(mapping.get("output")),
    }
    if not isinstance(block, dict):
        entry["error"] = "cloneable must be an object"
        return entry
    n = block.get("maxClones")
    pools = (region(block.get("inputPool")), region(block.get("outputPool")))
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        entry["error"] = f"maxClones must be an integer >= 1, got {n!r}"
    elif None in pools or entry["input"] is None or entry["output"] is None:
        entry["error"] = "cloneable needs inputPool and outputPool {offset, length} and the machine needs its own input and output regions"
    else:
        entry.update(maxClones=n, inputPool=pools[0], outputPool=pools[1])
    return entry


def pool_problems(
    corpus: list[dict[str, Any]],
    service_lanes: list[dict[str, Any]],
    reserved_bands: list[dict[str, Any]],
) -> list[str]:
    """Every violation of the cloneable contract in `corpus`.

    corpus entries: {"name", "domain", "input", "output", "cloneable"}, where
    `cloneable` is the result of cloneable_entry() or None.
    """
    problems: list[str] = []
    pools: list[tuple[str, str, Region]] = []  # (machine, "inputPool"/"outputPool", region)

    for m in corpus:
        c = m.get("cloneable")
        if not c:
            continue
        if "error" in c:
            problems.append(f"{m['name']}: {c['error']}")
            continue
        n = c["maxClones"]
        for pool_key, own_key in (("inputPool", "input"), ("outputPool", "output")):
            pool, own = c[pool_key], c[own_key]
            if pool[1] != n * own[1]:
                problems.append(
                    f"{m['name']}: {pool_key} length {pool[1]} != maxClones {n} x {own_key} length {own[1]} = {n * own[1]}"
                )
            pools.append((m["name"], pool_key, pool))

    # 2. nothing else occupies a pool
    for i, (owner, key, pool) in enumerate(pools):
        for m in corpus:
            for lane in ("input", "output"):
                r = m.get(lane)
                if r and overlaps(r, pool):
                    problems.append(f"{m['name']} {lane} {fmt(r)} lies inside {owner} {key} {fmt(pool)}")
        for lane in service_lanes:
            r = (int(lane["offset"]), int(lane["length"]))
            if overlaps(r, pool):
                problems.append(f"service lane {lane['id']} {fmt(r)} lies inside {owner} {key} {fmt(pool)}")
        for band in reserved_bands:
            r = (int(band["offset"]), int(band["length"]))
            if overlaps(r, pool):
                problems.append(f"reserved band {band['id']} {fmt(r)} overlaps {owner} {key} {fmt(pool)}")
        for other_owner, other_key, other in pools[i + 1:]:
            if overlaps(other, pool):
                problems.append(f"{owner} {key} {fmt(pool)} overlaps {other_owner} {other_key} {fmt(other)}")

    # 3. the template's own input has no writer
    for m in corpus:
        c = m.get("cloneable")
        if not c or "error" in c:
            continue
        own_input = c["input"]
        for w in corpus:
            r = w.get("output")
            if r and overlaps(r, own_input):
                problems.append(
                    f"{w['name']} output {fmt(r)} writes template {m['name']}'s own input {fmt(own_input)}; the template must never fire"
                )
        for lane in service_lanes:
            r = (int(lane["offset"]), int(lane["length"]))
            if overlaps(r, own_input):
                problems.append(f"service lane {lane['id']} {fmt(r)} writes template {m['name']}'s own input {fmt(own_input)}")

    return problems


def resolved_domain(metadata: dict[str, Any]) -> str | None:
    tagging = metadata.get("tagging")
    primary = tagging.get("primaryDomain") if isinstance(tagging, dict) else None
    domain = primary or metadata.get("category") or metadata.get("domain")
    return str(domain) if domain else None


def load_corpus(machines_root: Path = MACHINES) -> list[dict[str, Any]]:
    out = []
    for path in sorted(machines_root.rglob("*.json")):
        try:
            machine = json.loads(path.read_text()).get("machine")
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        if not isinstance(machine, dict):
            continue
        raw_metadata = machine.get("metadata")
        metadata: dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
        raw_mapping = machine.get("perceptualMapping")
        mapping: dict[str, Any] = raw_mapping if isinstance(raw_mapping, dict) else {}
        domain = resolved_domain(metadata)
        out.append({
            "name": path.name,
            "domain": domain,
            "input": region(mapping.get("input")),
            "output": region(mapping.get("output")),
            "cloneable": cloneable_entry(path.name, domain, machine),
        })
    return out


def registry_pools(corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The clonePools section of the region allocation registry."""
    pools = []
    for m in corpus:
        c = m.get("cloneable")
        if not c or "error" in c:
            continue
        pools.append({
            "machine": m["name"],
            "domain": c["domain"],
            "maxClones": c["maxClones"],
            "slotInputLength": c["input"][1],
            "slotOutputLength": c["output"][1],
            "inputPool": {"offset": c["inputPool"][0], "length": c["inputPool"][1]},
            "outputPool": {"offset": c["outputPool"][0], "length": c["outputPool"][1]},
        })
    return sorted(pools, key=lambda p: p["inputPool"]["offset"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    registry = json.loads(REGISTRY.read_text())
    corpus = load_corpus()
    problems = pool_problems(corpus, registry.get("serviceLanes", []), registry.get("reservedBands", []))
    templates = sum(1 for m in corpus if m["cloneable"])
    if problems:
        print(f"cloneable-machines: {len(problems)} problem(s) across {templates} cloneable machine(s)", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"cloneable-machines: OK — {templates} cloneable machine(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
