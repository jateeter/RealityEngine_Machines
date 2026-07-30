#!/usr/bin/env python3
"""Contract tests for the standard MCP/OpenAI/Ollama provider MVP fixture."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "provider-mvp"
COMPLETION_ENDPOINT = "/api/integrations/completions"
PROVIDERS = {"openai", "ollama", "mcp"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


class ProviderMvpFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mappings = load_json(FIXTURE_ROOT / "source-mappings.json")
        cls.observe = load_json(FIXTURE_ROOT / "provider_observe_probe.json")
        cls.writeback = load_json(FIXTURE_ROOT / "provider_completion_writeback_probe.json")

    def test_fixture_has_single_standard_completion_mapping(self) -> None:
        self.assertEqual(self.mappings["completionEndpoint"], COMPLETION_ENDPOINT)
        mappings = self.mappings["sourceMappings"]
        self.assertEqual(len(mappings), 1)

        mapping = mappings[0]
        self.assertEqual(mapping["id"], "mvp-provider-completion-risk")
        self.assertEqual(mapping["sensorIdTemplate"], "mvp.provider.{provider}.{agent}.completion")
        self.assertEqual(mapping["region"], {"offset": 4400, "length": 4})
        self.assertEqual(mapping["extract"]["type"], "json")
        self.assertEqual(mapping["extract"]["pointers"], [
            "/completed",
            "/failed",
            "/confidence",
            "/actionClass",
        ])
        self.assertEqual(mapping["normalize"], {"mode": "passthrough", "clamp": True})
        self.assertEqual(mapping["ttlMs"], 300000)

    def test_observe_probe_is_provider_neutral_and_read_only(self) -> None:
        binding = self.observe["machine"]["metadata"]["agentBinding"]

        self.assertEqual(set(binding["providers"]), PROVIDERS)
        self.assertEqual(binding["mode"], "observe")
        self.assertEqual(binding["writeBack"], {"type": "none"})

    def test_writeback_probe_routes_all_providers_through_pe_completion_ingest(self) -> None:
        binding = self.writeback["machine"]["metadata"]["agentBinding"]
        writeback = binding["writeBack"]
        mapping = self.mappings["sourceMappings"][0]

        self.assertEqual(set(binding["providers"]), PROVIDERS)
        self.assertEqual(binding["mode"], "advise")
        self.assertEqual(writeback["type"], "pe-sensor")
        self.assertEqual(writeback["sourceMappingId"], mapping["id"])
        self.assertEqual(writeback["sensorIdTemplate"], mapping["sensorIdTemplate"])
        self.assertEqual(writeback["region"], mapping["region"])
        self.assertEqual(writeback["ttlMs"], mapping["ttlMs"])
        self.assertEqual(writeback["expectedJsonPointers"], mapping["extract"]["pointers"])
        self.assertEqual(writeback["ingest"]["endpoint"], COMPLETION_ENDPOINT)
        self.assertEqual(writeback["ingest"]["method"], "POST")
        self.assertFalse(writeback["ingest"]["triggerPush"])
        self.assertTrue(writeback["ingest"]["compactPush"])

    def test_fixture_does_not_require_live_provider_services(self) -> None:
        for fixture in (self.observe, self.writeback):
            metadata = fixture["machine"]["metadata"]
            self.assertNotIn("apiKey", json.dumps(metadata).lower())
            self.assertNotIn("serverUrl", metadata.get("agentBinding", {}))
            self.assertNotIn("baseUrl", metadata.get("agentBinding", {}))


if __name__ == "__main__":
    unittest.main()
