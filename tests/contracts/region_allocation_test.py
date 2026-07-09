#!/usr/bin/env python3
"""Contract checks for universal-vector region allocation.

Gates the interconnection/allocation invariants of the universal input
event vector:

- every OpenClaw input-analyst writeBackRegion equals its machine's own
  input region (external services write machine-native input lanes only)
- the semantic-bus registry's lane regions match the interconnect
  machine's perceptualMapping exactly (inter-domain bus compliance)
- no machine output claims a cross-service PE source lane unless it is
  recorded in the allocation registry's serviceLanes corpusWriters
- the set of output-lane overlaps matches the frozen baseline in
  domains/region-allocation.json — a new overlap means either re-map the
  machine or deliberately regenerate the registry
  (scripts/build-region-allocation.py --write) and review the diff
"""

from __future__ import annotations

import json
import unittest
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHINES = REPO_ROOT / "machines"
REGISTRY = REPO_ROOT / "domains" / "region-allocation.json"
BUS_REGISTRY = REPO_ROOT / "domains" / "semantic-bus-registry.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def region(r: Any) -> tuple[int, int] | None:
    if isinstance(r, dict) and isinstance(r.get("offset"), (int, float)) and isinstance(r.get("length"), (int, float)):
        return (int(r["offset"]), int(r["length"]))
    return None


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[0] + b[1] and b[0] < a[0] + a[1]


class RegionAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_json(REGISTRY)
        cls.corpus: list[dict[str, Any]] = []
        for path in sorted(MACHINES.rglob("*.json")):
            root = load_json(path)
            machine = root.get("machine")
            if not isinstance(machine, dict):
                continue
            raw_md = machine.get("metadata")
            metadata: dict[str, Any] = raw_md if isinstance(raw_md, dict) else {}
            raw_pm = machine.get("perceptualMapping")
            mapping: dict[str, Any] = raw_pm if isinstance(raw_pm, dict) else {}
            raw_ocp = metadata.get("openClawProjection")
            ocp: dict[str, Any] = raw_ocp if isinstance(raw_ocp, dict) else {}
            cls.corpus.append({
                "name": path.name,
                "input": region(mapping.get("input")),
                "output": region(mapping.get("output")),
                "writeBack": region(ocp.get("writeBackRegion")),
            })

    def test_external_writeback_targets_machine_input_lane(self) -> None:
        bad = [
            f"{m['name']}: writeBack {m['writeBack']} != input {m['input']}"
            for m in self.corpus
            if m["writeBack"] is not None and m["writeBack"] != m["input"]
        ]
        self.assertEqual(bad, [], "OpenClaw write-back lanes must equal the machine input lane:\n" + "\n".join(bad[:10]))

    def test_semantic_bus_lanes_match_interconnect_machines(self) -> None:
        by_name = {m["name"]: m for m in self.corpus}
        bad = []
        for bus in load_json(BUS_REGISTRY).get("semanticBuses", []):
            mf = str(bus.get("machineFile", "")).split("/")[-1]
            machine = by_name.get(mf)
            if machine is None:
                bad.append(f"{bus.get('id')}: interconnect machine {mf!r} not in corpus")
                continue
            if region(bus.get("inputRegion")) != machine["input"] or region(bus.get("outputRegion")) != machine["output"]:
                bad.append(f"{bus.get('id')}: bus lanes {bus.get('inputRegion')}/{bus.get('outputRegion')} != machine {machine['input']}/{machine['output']}")
        self.assertEqual(bad, [], "semantic-bus registry lane drift:\n" + "\n".join(bad[:10]))

    def test_service_lane_writers_are_registered(self) -> None:
        bad = []
        for lane in self.registry["serviceLanes"]:
            lane_region = (int(lane["offset"]), int(lane["length"]))
            allowed = set(lane["corpusWriters"])
            for m in self.corpus:
                if m["output"] and overlaps(m["output"], lane_region) and m["name"] not in allowed:
                    bad.append(f"{m['name']} output {m['output']} writes service lane {lane['id']} without registration")
        self.assertEqual(bad, [], "unregistered service-lane writers:\n" + "\n".join(bad[:10]))

    def test_output_overlap_baseline_is_frozen(self) -> None:
        cell_owners: dict[int, list[str]] = defaultdict(list)
        for m in self.corpus:
            if m["output"]:
                o, l = m["output"]
                for c in range(o, o + l):
                    cell_owners[c].append(m["name"])
        actual: set[tuple[str, ...]] = set()
        for names in cell_owners.values():
            if len(names) > 1:
                actual.add(tuple(sorted(names)))
        recorded = {tuple(sorted(g["owners"])) for g in self.registry["sharedOutputLanes"]}
        new = actual - recorded
        stale = recorded - actual
        msg = []
        if new:
            msg.append(f"NEW output-lane overlaps (re-map or regenerate the registry): {sorted(new)[:5]}")
        if stale:
            msg.append(f"stale registry entries (regenerate): {sorted(stale)[:5]}")
        self.assertEqual((len(new), len(stale)), (0, 0), "; ".join(msg))

    def test_no_machine_lane_inside_reserved_band(self) -> None:
        """domain-registry rangePolicy: reserved bands are owned by provider
        write-back sources — machine lanes must stay out of them."""
        bad = []
        for band in self.registry["reservedBands"]:
            band_region = (int(band["offset"]), int(band["length"]))
            for m in self.corpus:
                for key in ("input", "output"):
                    if m[key] and overlaps(m[key], band_region):
                        bad.append(f"{m['name']} {key} {m[key]} intersects reserved band {band['id']}")
        self.assertEqual(bad, [], "machine lanes inside provider-reserved bands:\n" + "\n".join(bad[:10]))

    def test_registry_totals_match_corpus(self) -> None:
        total = sum(d["machineCount"] for d in self.registry["domains"].values())
        self.assertEqual(total, len(self.corpus), "registry domain machineCount drift — regenerate")
        wb_count = sum(1 for m in self.corpus if m["writeBack"] is not None)
        self.assertEqual(self.registry["externalWritebackSummary"]["count"], wb_count)
        self.assertTrue(self.registry["externalWritebackSummary"]["allMatchMachineInput"])


if __name__ == "__main__":
    unittest.main()
