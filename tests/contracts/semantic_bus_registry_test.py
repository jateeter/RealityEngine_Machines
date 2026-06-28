#!/usr/bin/env python3
"""Contract checks for the semantic published-domain bus registry."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "inventory-semantic-buses.py"
REGISTRY = REPO_ROOT / "domains" / "semantic-bus-registry.json"


def load_inventory_module():
    spec = importlib.util.spec_from_file_location("inventory_semantic_buses", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SemanticBusRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = load_inventory_module()
        cls.registry = json.loads(REGISTRY.read_text())

    def test_registry_matches_corpus_inventory(self) -> None:
        generated, errors = self.inventory.build_registry(REPO_ROOT, REPO_ROOT / "machines")
        self.assertEqual(errors, [])
        self.assertEqual(generated, self.registry)

    def test_registry_separates_semantic_from_mechanical_buses(self) -> None:
        counts = self.registry["counts"]
        self.assertEqual(counts["publishedBuses"], 135)
        self.assertEqual(counts["semanticBuses"], 29)
        self.assertEqual(counts["setAsideMechanicalBuses"], 106)
        self.assertEqual(
            counts["publishedBuses"],
            counts["semanticBuses"] + counts["setAsideMechanicalBuses"],
        )

    def test_semantic_buses_expose_machine_readable_semantics(self) -> None:
        buses = {bus["id"]: bus for bus in self.registry["semanticBuses"]}
        self.assertIn("health.infrastructure-support", buses)
        bus = buses["health.infrastructure-support"]
        self.assertEqual(bus["domain"], "health-personal")
        self.assertEqual(bus["inputRegion"], {"offset": 16900, "length": 16})
        self.assertEqual(bus["outputRegion"], {"offset": 16916, "length": 4})
        self.assertEqual(
            bus["sourceDomains"],
            ["built-space", "community-services", "transportation"],
        )
        self.assertGreaterEqual(len(bus["inputSemantics"]), 16)
        self.assertGreaterEqual(len(bus["outputSemantics"]), 4)


if __name__ == "__main__":
    unittest.main()
