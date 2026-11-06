"""Cloneable machines: the ISRE/OSRE slot-pool contract (localAssetStorageStack#8).

A cloneable machine reserves maxClones input slots and maxClones output
slots, each the size of its own region; clone k uses slot k of each. These
tests pin the checker in scripts/cloneable_machines.py with fixtures and run
it over the real corpus and region allocation registry.
"""

from __future__ import annotations

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


def machine(name: str, inp: tuple[int, int], out: tuple[int, int], cloneable: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "perceptualMapping": {
            "input": {"offset": inp[0], "length": inp[1]},
            "output": {"offset": out[0], "length": out[1]},
            "bitsPerElement": 1,
        }
    }
    if cloneable is not None:
        body["cloneable"] = cloneable
    return {
        "name": name,
        "domain": "fixture",
        "input": inp,
        "output": out,
        "cloneable": cm.cloneable_entry(name, "fixture", body),
    }


def pools(n: int, inp: tuple[int, int], out: tuple[int, int]) -> dict[str, Any]:
    return {
        "maxClones": n,
        "inputPool": {"offset": inp[0], "length": inp[1]},
        "outputPool": {"offset": out[0], "length": out[1]},
    }


# A template with an 8-cell input and a 6-cell output, 4 clones:
# input pool 32 cells, output pool 24 cells.
TEMPLATE = ("Template.json", (30000, 8), (30008, 6))
GOOD = pools(4, (30100, 32), (30132, 24))


class CloneableFixtureTests(unittest.TestCase):
    def check(self, corpus: list[dict[str, Any]], lanes: list[dict[str, Any]] | None = None,
              bands: list[dict[str, Any]] | None = None) -> list[str]:
        return cm.pool_problems(corpus, lanes or [], bands or [])

    def test_well_formed_template_passes(self) -> None:
        self.assertEqual(self.check([machine(*TEMPLATE, GOOD)]), [])

    def test_non_cloneable_machine_has_no_pools(self) -> None:
        m = machine("Plain.json", (100, 2), (102, 2))
        self.assertIsNone(m["cloneable"])
        self.assertEqual(cm.registry_pools([m]), [])

    def test_pool_length_must_be_n_times_region(self) -> None:
        bad = pools(4, (30100, 31), (30132, 24))
        problems = self.check([machine(*TEMPLATE, bad)])
        self.assertEqual(len(problems), 1)
        self.assertIn("inputPool length 31 != maxClones 4 x input length 8 = 32", problems[0])

    def test_output_pool_length_checked_too(self) -> None:
        bad = pools(4, (30100, 32), (30132, 20))
        self.assertIn("outputPool length 20", self.check([machine(*TEMPLATE, bad)])[0])

    def test_malformed_block_is_reported_not_dropped(self) -> None:
        for block, needle in (
            ({"maxClones": 0, "inputPool": GOOD["inputPool"], "outputPool": GOOD["outputPool"]}, "maxClones"),
            ({"maxClones": True, "inputPool": GOOD["inputPool"], "outputPool": GOOD["outputPool"]}, "maxClones"),
            ({"maxClones": 4, "inputPool": GOOD["inputPool"]}, "outputPool"),
            ("yes", "object"),
        ):
            with self.subTest(block=block):
                problems = self.check([machine(*TEMPLATE, block)])
                self.assertEqual(len(problems), 1)
                self.assertIn(needle, problems[0])

    def test_template_own_region_must_sit_outside_its_pools(self) -> None:
        inside = ("Template.json", (30100, 8), (30008, 6))
        problems = self.check([machine(*inside, GOOD)])
        self.assertTrue(any("Template.json input [30100:30108] lies inside Template.json inputPool" in p for p in problems), problems)

    def test_other_machine_inside_a_pool_fails(self) -> None:
        intruder = machine("Intruder.json", (30140, 2), (500, 2))
        problems = self.check([machine(*TEMPLATE, GOOD), intruder])
        self.assertEqual(problems, ["Intruder.json input [30140:30142] lies inside Template.json outputPool [30132:30156]"])

    def test_service_lane_and_reserved_band_inside_a_pool_fail(self) -> None:
        lanes = [{"id": "lane-x", "offset": 30104, "length": 4}]
        bands = [{"id": "band-y", "offset": 30150, "length": 10}]
        problems = self.check([machine(*TEMPLATE, GOOD)], lanes, bands)
        self.assertEqual(len(problems), 2, problems)
        self.assertIn("service lane lane-x", problems[0])
        self.assertIn("reserved band band-y", problems[1])

    def test_pools_must_not_overlap_each_other(self) -> None:
        same_machine = pools(4, (30100, 32), (30120, 24))
        self.assertTrue(any("inputPool [30100:30132] overlaps Template.json outputPool" in p
                            for p in self.check([machine(*TEMPLATE, same_machine)])))
        other = machine("Other.json", (31000, 8), (31008, 6), pools(4, (30110, 32), (31100, 24)))
        self.assertTrue(any("overlaps Other.json inputPool" in p
                            for p in self.check([machine(*TEMPLATE, GOOD), other])))

    def test_template_never_fires(self) -> None:
        writer = machine("Writer.json", (700, 2), (30002, 2))
        problems = self.check([machine(*TEMPLATE, GOOD), writer])
        self.assertEqual(problems, ["Writer.json output [30002:30004] writes template Template.json's own input [30000:30008]; the template must never fire"])
        lanes = [{"id": "lane-z", "offset": 29998, "length": 4}]
        self.assertIn("service lane lane-z", self.check([machine(*TEMPLATE, GOOD)], lanes)[0])

    def test_registry_pool_record(self) -> None:
        self.assertEqual(cm.registry_pools([machine(*TEMPLATE, GOOD)]), [{
            "machine": "Template.json",
            "domain": "fixture",
            "maxClones": 4,
            "slotInputLength": 8,
            "slotOutputLength": 6,
            "inputPool": {"offset": 30100, "length": 32},
            "outputPool": {"offset": 30132, "length": 24},
        }])


class CloneableCorpusTests(unittest.TestCase):
    def test_corpus_honours_the_contract(self) -> None:
        registry = json.loads((REPO_ROOT / "domains" / "region-allocation.json").read_text())
        corpus = cm.load_corpus()
        problems = cm.pool_problems(corpus, registry["serviceLanes"], registry["reservedBands"])
        self.assertEqual(problems, [], "\n".join(problems[:10]))

    def test_registry_lists_every_pool(self) -> None:
        registry = json.loads((REPO_ROOT / "domains" / "region-allocation.json").read_text())
        self.assertEqual(registry["clonePools"], cm.registry_pools(cm.load_corpus()),
                         "clonePools drift: run scripts/build-region-allocation.py --write")


if __name__ == "__main__":
    unittest.main()
