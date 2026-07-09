#!/usr/bin/env python3
"""Build (or verify) the universal-vector region allocation registry at
domains/region-allocation.json.

The registry is the allocation map of the universal input event vector:

- serviceLanes: cross-service lanes written by external PE sources
  (OpenClaw/ACP completion, agent completion risk, HealthKit, CareKit).
  These constants mirror Manager's OPENCLAW_PS_REGION and the CI/engine
  integrations source-mapping configs; corpus readers/writers of each lane
  are computed from the corpus so drift is visible in review.
- domains: per-domain machine counts and input/output offset spans.
- interDomainBuses: semantic published buses (from
  domains/semantic-bus-registry.json) with their vector lanes and a
  crossDomain flag when the bus consumes from more than its home domain.
- externalWritebackSummary: OpenClaw input-analyst write-back lanes — the
  contract is writeBackRegion == the machine's own input region, so only
  counts are recorded here.
- sharedOutputLanes: every cell range where more than one machine output
  overlaps, frozen as the reviewed baseline. New overlaps fail
  tests/contracts/region_allocation_test.py until they are either re-mapped
  or deliberately regenerated into this registry.

Usage:
  python3 scripts/build-region-allocation.py --write
  python3 scripts/build-region-allocation.py --check   # CI / validate hook
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
BUS_REGISTRY = REPO_ROOT / "domains" / "semantic-bus-registry.json"
DOMAIN_REGISTRY = REPO_ROOT / "domains" / "domain-registry.json"
REGISTRY = REPO_ROOT / "domains" / "region-allocation.json"

# Cross-service PE source lanes. Sources of truth:
#   - acp-openclaw-completion: RealityEngine_Manager machineDomains.ts
#     OPENCLAW_PS_REGION and CI ACP_COMPLETION_SOURCE_MAPPING_ID
#   - agent-completion-risk / healthkit-* / carekit-*: CI
#     config/integrations.json and RealityEngine_CPP config/integrations.*
SERVICE_LANES: list[dict[str, Any]] = [
    {"id": "agent-completion-risk", "offset": 4200, "length": 4, "provider": "localAIStack"},
    {"id": "acp-openclaw-completion", "offset": 4210, "length": 4, "provider": "OpenClaw ACP"},
    {"id": "healthkit-activity", "offset": 4300, "length": 4, "provider": "HealthKit"},
    {"id": "carekit-task", "offset": 4310, "length": 4, "provider": "CareKit"},
    {"id": "carekit-outcome", "offset": 4314, "length": 4, "provider": "CareKit"},
    {"id": "healthkit-heart-rate", "offset": 4320, "length": 4, "provider": "HealthKit (e2e)"},
    {"id": "healthkit-steps", "offset": 4330, "length": 4, "provider": "HealthKit (e2e)"},
    {"id": "healthkit-sleep", "offset": 4340, "length": 4, "provider": "HealthKit (e2e)"},
]


def region(r: Any) -> tuple[int, int] | None:
    if isinstance(r, dict) and isinstance(r.get("offset"), (int, float)) and isinstance(r.get("length"), (int, float)):
        return (int(r["offset"]), int(r["length"]))
    return None


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[0] + b[1] and b[0] < a[0] + a[1]


def resolved_domain(metadata: dict[str, Any]) -> str | None:
    tagging = metadata.get("tagging")
    primary = tagging.get("primaryDomain") if isinstance(tagging, dict) else None
    domain = primary or metadata.get("category") or metadata.get("domain")
    return str(domain) if domain else None


def load_corpus() -> list[dict[str, Any]]:
    out = []
    for path in sorted(MACHINES.rglob("*.json")):
        try:
            root = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        machine = root.get("machine")
        if not isinstance(machine, dict):
            continue
        raw_metadata = machine.get("metadata")
        metadata: dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
        raw_mapping = machine.get("perceptualMapping")
        mapping: dict[str, Any] = raw_mapping if isinstance(raw_mapping, dict) else {}
        raw_ocp = metadata.get("openClawProjection")
        ocp: dict[str, Any] = raw_ocp if isinstance(raw_ocp, dict) else {}
        out.append({
            "relFile": path.relative_to(MACHINES).as_posix(),
            "name": path.name,
            "domain": resolved_domain(metadata),
            "input": region(mapping.get("input")),
            "output": region(mapping.get("output")),
            "writeBack": region(ocp.get("writeBackRegion")),
        })
    return out


def build_registry() -> dict[str, Any]:
    corpus = load_corpus()

    max_cell = 0
    for m in corpus:
        for r in (m["input"], m["output"]):
            if r:
                max_cell = max(max_cell, r[0] + r[1])

    # per-domain spans
    domains: dict[str, dict[str, Any]] = {}
    for m in corpus:
        d = str(m["domain"])
        entry = domains.setdefault(d, {"machineCount": 0, "inputSpan": None, "outputSpan": None})
        entry["machineCount"] += 1
        for key, span_key in (("input", "inputSpan"), ("output", "outputSpan")):
            r = m[key]
            if not r:
                continue
            span = entry[span_key]
            lo, hi = r[0], r[0] + r[1]
            entry[span_key] = [lo, hi] if span is None else [min(span[0], lo), max(span[1], hi)]

    # service lanes with computed corpus readers/writers
    service_lanes = []
    for lane in SERVICE_LANES:
        lr = (lane["offset"], lane["length"])
        readers = sorted(m["name"] for m in corpus if m["input"] and overlaps(m["input"], lr))
        writers = sorted(m["name"] for m in corpus if m["output"] and overlaps(m["output"], lr))
        service_lanes.append({**lane, "corpusReaders": readers, "corpusWriters": writers})

    # inter-domain buses from the semantic bus registry
    inter_domain_buses = []
    bus_data = json.loads(BUS_REGISTRY.read_text()) if BUS_REGISTRY.exists() else {}
    for bus in bus_data.get("semanticBuses", []):
        src_domains = sorted({str(d) for d in bus.get("sourceDomains", []) if d})
        home = str(bus.get("domain"))
        inter_domain_buses.append({
            "id": bus.get("id"),
            "domain": home,
            "sourceDomains": src_domains,
            "crossDomain": bool([d for d in src_domains if d != home]),
            "inputRegion": bus.get("inputRegion"),
            "outputRegion": bus.get("outputRegion"),
            "consumerCount": len(bus.get("downstreamConsumers", [])),
        })
    inter_domain_buses.sort(key=lambda b: str(b["id"]))

    # write-back summary (the equality contract itself lives in the tests)
    wb = [m for m in corpus if m["writeBack"]]
    wb_by_domain: dict[str, int] = defaultdict(int)
    for m in wb:
        wb_by_domain[str(m["domain"])] += 1
    writeback_summary = {
        "count": len(wb),
        "allMatchMachineInput": all(m["writeBack"] == m["input"] for m in wb),
        "byDomain": dict(sorted(wb_by_domain.items())),
    }

    # shared output lanes — frozen baseline of output-output overlaps
    cell_owners: dict[int, list[str]] = defaultdict(list)
    by_name = {m["name"]: m for m in corpus}
    for m in corpus:
        if m["output"]:
            o, l = m["output"]
            for c in range(o, o + l):
                cell_owners[c].append(m["name"])
    groups: dict[tuple[str, ...], set[int]] = defaultdict(set)
    for c, names in cell_owners.items():
        if len(names) > 1:
            groups[tuple(sorted(names))].add(c)
    shared_output_lanes = []
    for names, cells in groups.items():
        lo, hi = min(cells), max(cells)
        doms = sorted({str(by_name[n]["domain"]) for n in names})
        shared_output_lanes.append({
            "cells": {"offset": lo, "length": hi - lo + 1},
            "owners": list(names),
            "domains": doms,
            "crossDomain": len(doms) > 1,
        })
    shared_output_lanes.sort(key=lambda g: (g["cells"]["offset"], g["owners"]))

    # provider-owned reserved bands mirrored from domain-registry rangePolicy
    reserved_bands = []
    registry_root = json.loads(DOMAIN_REGISTRY.read_text()) if DOMAIN_REGISTRY.exists() else {}
    raw_policy = registry_root.get("rangePolicy")
    range_policy: dict[str, Any] = raw_policy if isinstance(raw_policy, dict) else {}
    raw_ranges = range_policy.get("reservedRanges")
    for band in raw_ranges if isinstance(raw_ranges, list) else []:
        if not isinstance(band, dict):
            continue
        reserved_bands.append({
            "id": band.get("id"),
            "offset": band.get("offset"),
            "length": band.get("length"),
            "provider": band.get("provider"),
            "ownership": band.get("ownership"),
        })

    return {
        "schemaVersion": "1.0.0",
        "purpose": "Generated universal-vector region allocation registry — regenerate with scripts/build-region-allocation.py --write; do not edit by hand.",
        "vectorBudget": {
            "maxCellExclusive": max_cell,
            "note": "Engines grow the perceptual space on demand; this records the corpus footprint.",
        },
        "reservedBands": reserved_bands,
        "serviceLanes": service_lanes,
        "domains": dict(sorted(domains.items())),
        "interDomainBuses": inter_domain_buses,
        "externalWritebackSummary": writeback_summary,
        "sharedOutputLanes": shared_output_lanes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    registry = build_registry()
    rendered = json.dumps(registry, indent=2) + "\n"
    summary = (
        f"{len(registry['sharedOutputLanes'])} shared output lanes "
        f"({sum(1 for g in registry['sharedOutputLanes'] if g['crossDomain'])} cross-domain), "
        f"{len(registry['interDomainBuses'])} buses, "
        f"{registry['externalWritebackSummary']['count']} external write-backs"
    )

    if args.write:
        REGISTRY.write_text(rendered)
        print(f"region-allocation: wrote — {summary}")
        return 0

    if not REGISTRY.exists():
        print("region-allocation: MISSING — run scripts/build-region-allocation.py --write", file=sys.stderr)
        return 1
    if REGISTRY.read_text() != rendered:
        print("region-allocation: STALE — run scripts/build-region-allocation.py --write", file=sys.stderr)
        return 1
    print(f"region-allocation: OK — {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
