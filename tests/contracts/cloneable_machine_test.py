"""Cloneable machines: the tag rules and the clone space (localAssetStorageStack#8).

scripts/cloneable_machines.py decides which machines carry the `cloneable`
tag and checks domains/clone-space.json against its reserved range. These
tests pin each rule with fixtures and run the checker over the real corpus.
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

    def test_block_limits(self) -> None:
        self.assertEqual(assess(machine(lin=16, lout=16)), (True, "n = 3 folded + 4 bus = 7"))
        self.assertFalse(assess(machine(lin=17))[0])
        self.assertFalse(assess(machine(lout=17))[0])
        self.assertEqual(assess(machine(edges=[producer(12)])), (True, "n = 12 folded + 4 bus = 16"))
        self.assertEqual(assess(machine(edges=[producer(10), producer(3)])),
                         (False, "n = 13 folded + 4 bus = 17 exceeds 16"))


class TagWritingTests(unittest.TestCase):
    def test_tag_goes_into_canonical_list_and_mirrors(self) -> None:
        m = {"metadata": {"tags": ["a", "z"], "tagging": {"capabilityTags": [], "allTags": ["a", "z"]}}}
        cm.set_tag(m, "cloneable", True)
        self.assertEqual(m["metadata"]["tags"], ["a", "cloneable", "z"])
        self.assertEqual(m["metadata"]["tagging"]["capabilityTags"], ["cloneable"])
        self.assertEqual(m["metadata"]["tagging"]["allTags"], ["a", "cloneable", "z"])
        self.assertTrue(cm.is_tagged(m, "cloneable"))

    def test_unsorted_list_keeps_its_order(self) -> None:
        m = {"metadata": {"tags": ["z", "a"], "tagging": {}}}
        cm.set_tag(m, "cloneable", True)
        self.assertEqual(m["metadata"]["tags"], ["z", "a", "cloneable"])

    def test_missing_mirror_lists_are_not_invented(self) -> None:
        m: dict[str, Any] = {"metadata": {"tagging": {"family": "f"}}}
        cm.set_tag(m, "cloneable", True)
        self.assertEqual(m, {"metadata": {"tagging": {"family": "f", "capabilityTags": ["cloneable"]}}})

    def test_untag_restores_the_original(self) -> None:
        original: dict[str, Any] = {"metadata": {"tagging": {"family": "f"}}}
        m = copy.deepcopy(original)
        cm.set_tag(m, "cloneable", True)
        cm.set_tag(m, "cloneable", False)
        self.assertEqual(m, original)


class CloneSpaceTests(unittest.TestCase):
    def test_space_matches_its_reserved_range(self) -> None:
        self.assertEqual(cm.space_problems(SPACE), [])

    def test_block_is_32_cells_16_and_16(self) -> None:
        self.assertEqual((SPACE["block"]["cells"], SPACE["block"]["isreCells"], SPACE["block"]["osreCells"]), (32, 16, 16))
        self.assertEqual(SPACE["busCells"], 4)

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
    def test_every_tag_agrees_with_the_rules(self) -> None:
        docs = cm.load_machines()
        targets = cm.bus_targets({p: d["machine"] for p, (_, d) in docs.items()})
        wrong = []
        for path, (_, doc) in docs.items():
            ok, reason = cm.assess(path, doc["machine"], targets, SPACE)
            if cm.is_tagged(doc["machine"], SPACE["tag"]) != ok:
                wrong.append(f"{path.name}: {reason}")
        self.assertEqual(wrong, [], "run scripts/cloneable_machines.py --write:\n" + "\n".join(wrong[:10]))


if __name__ == "__main__":
    unittest.main()
