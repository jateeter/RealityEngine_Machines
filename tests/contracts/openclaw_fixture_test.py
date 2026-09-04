#!/usr/bin/env python3
"""Contract checks for the deterministic OpenClaw completion machine."""

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
FIXTURE = next((REPO_ROOT / "machines").rglob("OpenClawCompletionE2E.json"))


class OpenClawFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with FIXTURE.open() as handle:
            cls.machine = json.load(handle)["machine"]

    def test_reserved_regions_match_pe_mapping_contract(self) -> None:
        mapping = self.machine["perceptualMapping"]
        self.assertEqual(mapping["input"], {"offset": 4210, "length": 4})
        self.assertEqual(mapping["output"], {"offset": 4214, "length": 4})

    def test_fixture_is_dispatchable_through_the_standard_agent_contract(self) -> None:
        metadata = self.machine["metadata"]
        self.assertEqual(metadata["machineClass"], "agent-dispatcher")
        self.assertEqual(metadata["agentBinding"]["agent"], "openclaw_e2e_agent")
        self.assertEqual(
            metadata["agentBinding"]["writeBack"]["sourceMapping"]["id"],
            "acp-openclaw-completion",
        )

    def test_dispatch_and_completion_sequences_are_stable(self) -> None:
        sequences = {item["id"]: item for item in self.machine["sequences"]}
        self.assertEqual(
            set(sequences),
            {"openclaw-e2e-dispatch-seed", "openclaw-e2e-completion-accepted"},
        )

        rules = {
            item["sequenceId"]: item["outputMatches"]
            for item in self.machine["metadata"]["triggerConfig"]["rules"]
        }
        self.assertEqual(rules["openclaw-e2e-dispatch-seed"], [1, 0, 0, 0])
        self.assertEqual(rules["openclaw-e2e-completion-accepted"], [0, 0, 0, 1])

    def test_authored_vectors_match_e2e_protocol(self) -> None:
        authored = {
            item["name"]: sequence_events(item)
            for item in self.machine["inputSequences"]
        }
        self.assertEqual(authored["Create ACP dispatch record"], [[0, 1, 0, 1]])
        self.assertEqual(authored["Accept OpenClaw completion"], [[1, 0, 0.95, 0]])


if __name__ == "__main__":
    unittest.main()
