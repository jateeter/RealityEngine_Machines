#!/usr/bin/env python3
"""Contract checks for the personal-health patient safety transport bus."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

# Corpus reads go through the shared accessors so both schema spellings
# resolve while RealityEngine_CI#220 layer 1 is in flight.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from event_keys import sequence_events  # noqa: E402
MACHINES = REPO_ROOT / "machines"
FIXTURE = next(MACHINES.rglob("PatientSafetyTransportInterconnect.json"))
BUS_TAG = "published-bus-health-personal-patient-safety-transport"


def load_machine(name: str) -> dict:
    with next(MACHINES.rglob(name)).open() as handle:
        return json.load(handle)["machine"]


class PatientSafetyTransportBusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with FIXTURE.open() as handle:
            cls.machine = json.load(handle)["machine"]

    def test_published_bus_mapping_is_stable(self) -> None:
        self.assertEqual(self.machine["metadata"]["domainLevelTag"], BUS_TAG)
        self.assertIn(BUS_TAG, self.machine["metadata"]["tags"])
        self.assertEqual(self.machine["perceptualMapping"]["input"], {"offset": 4310, "length": 10})
        self.assertEqual(self.machine["perceptualMapping"]["output"], {"offset": 7378, "length": 4})
        self.assertEqual(self.machine["metadata"]["machineClass"], "bridge")

    def test_bus_input_composes_existing_machine_mappings(self) -> None:
        bus = self.machine["metadata"]["publishedDomainBus"]
        composition = {entry["role"]: entry for entry in bus["inputComposition"]}

        self.assertEqual(composition["fall_outcome"]["machineInputRegion"], {"offset": 3813, "length": 2})
        self.assertEqual(composition["fall_outcome"]["machineOutputRegion"], {"offset": 1941, "length": 2})
        self.assertEqual(composition["transport_access"]["machineInputRegion"], {"offset": 1983, "length": 4})
        self.assertEqual(composition["transport_access"]["machineOutputRegion"], {"offset": 2015, "length": 4})
        self.assertEqual(composition["social_context"]["machineInputRegion"], {"offset": 2011, "length": 8})
        self.assertEqual(composition["social_context"]["machineOutputRegion"], {"offset": 2035, "length": 4})

    def test_existing_producers_declare_interconnection_without_tag_changes(self) -> None:
        expected = {
            "FallDetection.json": "health-personal.patient-safety-transport.fall-outcome",
            "HomeTransportationBarrierMonitor.json": "health-personal.patient-safety-transport.transport-access",
            "HomeSocialIsolationMonitor.json": "health-personal.patient-safety-transport.social-context",
        }
        for file_name, interconnection_id in expected.items():
            with self.subTest(machine=file_name):
                machine = load_machine(file_name)
                interconnections = machine["metadata"].get("interconnections", [])
                ids = {item.get("id") for item in interconnections}
                self.assertIn(interconnection_id, ids)
                match = next(item for item in interconnections if item.get("id") == interconnection_id)
                self.assertEqual(match["busTag"], BUS_TAG)
                self.assertEqual(match["targetMachine"], "Patient Safety Transport Interconnect")
                self.assertEqual(match["publishedOutputRegion"], {"offset": 7378, "length": 4})

    def test_authored_sequence_activates_urgent_fanout(self) -> None:
        authored = {item["name"]: item for item in self.machine["inputSequences"]}
        sequence = authored["Confirmed fall with transportation failure fan-out"]
        self.assertEqual(sequence_events(sequence), [[1, 0, 1, 1, 0, 0, 0, 0, 0, 1]])
        self.assertEqual(sequence["metadata"]["expectedOutputVector"], [1, 0, 0, 0])
        self.assertEqual(sequence["metadata"]["sourceRegionInputs"]["FallDetection[1941:1943]"], [4, 3])
        self.assertIn(
            "HSPH132_care-coordination-resource-router",
            sequence["metadata"]["expectedDownstreamConsumers"],
        )


if __name__ == "__main__":
    unittest.main()
