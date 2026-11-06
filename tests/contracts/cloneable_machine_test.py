"""Cloneable machines: the recognition rule and the clone space (localAssetStorageStack#8).

Engines recognise cloneable machines at load time; scripts/cloneable_machines.py
applies the same rule as a corpus author's report and checks
domains/clone-space.json against its reserved range. These tests pin each
rule with fixtures and run the report over the real corpus.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cloneable_machines", REPO_ROOT / "scripts" / "cloneable_machines.py")
assert spec and spec.loader
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

SPACE = cm.load_space()


def producer(cells: int, target: str = "Bus.json") -> dict[str, Any]:
    return {"type": "published-domain-bus-producer", "targetMachineFile": target, "targetInputElements": list(range(cells))}


def machine(lin: int = 4, lout: int = 4, edges: list[dict[str, Any]] | None = None, agent: bool = True,
            tags: list[str] | None = None, severity: str | None = None) -> dict[str, Any]:
    md: dict[str, Any] = {"interconnections": edges if edges is not None else [producer(3)]}
    if agent:
        md["agentBinding"] = {"agent": "x"}
    if tags is not None:
        md["tags"] = tags
    if severity:
        md["severity"] = severity
    return {"metadata": md, "perceptualMapping": {"input": {"offset": 0, "length": lin}, "output": {"offset": 4, "length": lout}}}


def assess(m: dict[str, Any], name: str = "T.json", targets: set[str] | None = None) -> tuple[bool, str]:
    return cm.assess(Path(name), m, targets or set(), SPACE)


class EligibilityTests(unittest.TestCase):
    def test_typical_bus_producer_qualifies_with_n_7(self) -> None:
        self.assertEqual(assess(machine()), (True, "n = 3 folded + 4 bus = 7"))

    def test_handoff_source_qualifies_and_folds_nothing(self) -> None:
        handoff = {"type": "document-workflow-handoff", "sourceMachine": "T", "targetMachine": "U"}
        self.assertEqual(assess(machine(lin=8, edges=[handoff], agent=False)), (True, "n = 0 folded + 4 bus = 4"))

    def test_a_handoff_into_the_machine_is_not_its_fanout(self) -> None:
        inbound = {"type": "document-workflow-handoff", "sourceMachine": "U", "targetMachine": "T"}
        self.assertEqual(assess(machine(edges=[inbound], agent=False)), (False, "dispatches no agentic action"))

    def test_no_agentic_action(self) -> None:
        self.assertEqual(assess(machine(agent=False)), (False, "dispatches no agentic action"))

    def test_no_fanout(self) -> None:
        self.assertEqual(assess(machine(edges=[])), (False, "has no fanout"))

    def test_bus_target_excluded(self) -> None:
        self.assertEqual(assess(machine(), "Bus.json", {"Bus.json"}), (False, "is a bus target"))

    def test_life_safety_and_fixture_excluded(self) -> None:
        self.assertEqual(assess(machine(severity="life-safety")), (False, "is life-safety"))
        self.assertEqual(assess(machine(tags=["arbitration-fixture"])), (False, "is a fixture"))

    def test_opt_out(self) -> None:
        m = machine()
        m["metadata"]["cloneable"] = False
        self.assertEqual(assess(m), (False, "opts out (metadata.cloneable: false)"))

    def test_block_limits(self) -> None:
        self.assertEqual(assess(machine(lin=16, lout=16)), (True, "n = 3 folded + 4 bus = 7"))
        self.assertFalse(assess(machine(lin=17))[0])
        self.assertFalse(assess(machine(lout=17))[0])
        # Nest layout: fanout has its own quarter, so 16 folded cells fit.
        self.assertEqual(assess(machine(edges=[producer(16)])), (True, "n = 16 folded + 4 bus = 20"))
        self.assertEqual(assess(machine(edges=[producer(10), producer(7)])),
                         (False, "fanout folds into 17 cells, more than the 16-cell fanout quarter"))


class CloneSpaceTests(unittest.TestCase):
    def test_space_matches_its_reserved_range(self) -> None:
        self.assertEqual(cm.space_problems(SPACE), [])

    def test_block_is_64_cells_in_four_uniform_quarters(self) -> None:
        self.assertEqual(SPACE["block"]["cells"], 64)
        self.assertEqual([(p["role"], p["offset"], p["length"]) for p in SPACE["block"]["layout"]],
                         [("input", 0, 16), ("output", 16, 16), ("fanout", 32, 16), ("bus", 48, 16)])
        self.assertEqual(SPACE["busCells"], 4)
        self.assertEqual(SPACE["band"]["length"] // 64, 1024)

    def test_layout_must_tile_uniformly(self) -> None:
        gap = copy.deepcopy(SPACE)
        gap["block"]["layout"][3]["offset"] = 50
        self.assertTrue(any("expected 48" in p for p in cm.space_problems(gap)))
        lopsided = copy.deepcopy(SPACE)
        lopsided["block"]["layout"][2]["length"] = 8
        lopsided["block"]["layout"][3]["offset"] = 40
        lopsided["block"]["layout"][3]["length"] = 24
        self.assertTrue(any("uniform" in p for p in cm.space_problems(lopsided)))
        missing = copy.deepcopy(SPACE)
        missing["block"]["layout"][3]["role"] = "fanout"
        self.assertTrue(any("exactly one" in p for p in cm.space_problems(missing)))

    def test_band_drift_is_reported(self) -> None:
        moved = copy.deepcopy(SPACE)
        moved["band"]["offset"] += 32
        self.assertTrue(any("!= reserved range" in p for p in cm.space_problems(moved)))
        ragged = copy.deepcopy(SPACE)
        ragged["band"]["length"] += 1
        self.assertTrue(any("whole number" in p for p in cm.space_problems(ragged)))

    def test_band_is_above_every_corpus_region(self) -> None:
        registry = json.loads((REPO_ROOT / "domains" / "region-allocation.json").read_text())
        self.assertGreaterEqual(SPACE["band"]["offset"], registry["vectorBudget"]["maxCellExclusive"])


class CorpusTests(unittest.TestCase):
    def test_corpus_outcome(self) -> None:
        """Pins today's outcome so a corpus change that moves it is noticed in review."""
        docs = cm.load_machines()
        machines = {p: d["machine"] for p, (_, d) in docs.items()}
        targets = cm.bus_targets(machines)
        cloneable = [p for p, m in machines.items() if cm.assess(p, m, targets, SPACE)[0]]
        self.assertGreater(len(cloneable), 0)
        self.assertTrue(all("fixture" not in str(as_tag) for p in cloneable
                            for as_tag in machines[p].get("metadata", {}).get("tags", [])))
        ifrs = [p for p in cloneable if p.parent.name == "ifrs-accounting"]
        self.assertEqual(len(ifrs), len(list((REPO_ROOT / "machines/domains/ifrs-accounting").glob("*.json"))),
                         "every IFRS machine is a handoff source and should qualify")


if __name__ == "__main__":
    unittest.main()
