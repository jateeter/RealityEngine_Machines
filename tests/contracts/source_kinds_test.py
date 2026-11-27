"""The source-kind taxonomy: schemas/source-kinds/re-source-kinds-<N>.json.

The PE half of a K-line records, per committed step, which source won each input
cell and of what kind (RealityEngine_CI SURFACE_SPEC.md, "The PE half: ISRE
composition"; owner, 2026-11-24). A PE refuses to boot when its taxonomy version
is not here, so the files are contract data, and these tests pin what the
specification says about them:

- versions are numbered from 1 with no gaps, each file names its own version,
  and every version after the first maps every (kind, provider) of the one
  before;
- version 1 is exactly the specification's vocabulary;
- classes are RealityEngine_CI docs/ARBITER_CONTRACT.md's determinism classes:
  a provider the contract calls generated is never classed above it, and an
  unknown provider is generated ("when in doubt it is generated").
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DIR = REPO_ROOT / "schemas" / "source-kinds"
NAME = re.compile(r"^re-source-kinds-(\d+)\.json$")

# ARBITER_CONTRACT.md §3, "default providers" per class. A generated provider
# may never be reclassified upward.
CONTRACT_GENERATED = {"acp", "mcp", "localai"}
CONTRACT_MEASURED = {"mqtt", "healthkit", "sensor", "stream", "ui", "synthetic"}


def load() -> dict[int, dict]:
    out = {}
    for path in sorted(DIR.glob("*.json")):
        m = NAME.match(path.name)
        if not m:
            raise AssertionError(f"{path.name}: not named re-source-kinds-<N>.json")
        out[int(m.group(1))] = json.loads(path.read_text())
    return out


def pairs(doc: dict) -> set[tuple[str, str | None]]:
    """Every (kind, provider) a version can record, the unknown provider included."""
    out: set[tuple[str, str | None]] = set()
    for k in doc["kinds"]:
        if "providers" in k:
            out |= {(k["kind"], p["provider"]) for p in k["providers"]}
            out.add((k["kind"], doc["unknownProvider"]["provider"]))
        else:
            out.add((k["kind"], None))
    return out


class SourceKindsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.versions = load()

    def test_versions_are_contiguous_and_self_named(self) -> None:
        self.assertTrue(self.versions, "no taxonomy version: a PE cannot boot")
        self.assertEqual(sorted(self.versions), list(range(1, max(self.versions) + 1)))
        for n, doc in self.versions.items():
            self.assertEqual(doc["format"], "re-source-kinds")
            self.assertEqual(doc["version"], n, f"re-source-kinds-{n}.json names version {doc['version']}")

    def test_each_later_version_maps_the_previous_one(self) -> None:
        self.assertIsNone(self.versions[1]["mappingFromPrevious"])
        for n in sorted(self.versions)[1:]:
            mapping = self.versions[n]["mappingFromPrevious"]
            self.assertTrue(mapping, f"version {n} has no mapping from {n - 1}")
            mapped = {(m["from"]["kind"], m["from"].get("provider")) for m in mapping}
            missing = pairs(self.versions[n - 1]) - mapped
            self.assertFalse(missing, f"version {n} does not map {sorted(missing, key=str)}")

    def test_version_1_is_the_specified_vocabulary(self) -> None:
        v1 = self.versions[1]
        kinds = {k["kind"]: k for k in v1["kinds"]}
        self.assertEqual(set(kinds), {"test", "sensor", "feedback", "none"})
        self.assertEqual({p["provider"] for p in kinds["sensor"]["providers"]},
                         {"mqtt", "healthkit", "carekit", "acp", "mcp", "localai", "signal"})
        self.assertEqual(v1["providerMapping"], {"openclaw": "acp", "ollama": "localai", "localaistack": "localai"})
        self.assertEqual(kinds["test"]["class"], "deterministic")
        self.assertEqual(kinds["feedback"]["class"], "deterministic")
        self.assertIsNone(kinds["none"]["class"])

    def test_version_2_adds_simulated_and_openai(self) -> None:
        # Owner, 2026-11-27: `simulated` (ARBITER_CONTRACT maps it to `synthetic`,
        # measured) and the `openai` provider (generated); v1 reads unchanged.
        v1, v2 = self.versions[1], self.versions[2]
        kinds = {k["kind"]: k for k in v2["kinds"]}
        self.assertEqual(set(kinds), {"test", "sensor", "simulated", "feedback", "none"})
        self.assertEqual(kinds["simulated"]["class"], "measured")
        self.assertIn({"provider": "openai", "class": "generated"}, kinds["sensor"]["providers"])
        self.assertTrue(all(m["from"] == m["to"] for m in v2["mappingFromPrevious"]), "v1 is renamed nowhere")
        self.assertEqual(v2["providerMapping"], v1["providerMapping"])

    def test_classes_follow_the_arbiter_contract(self) -> None:
        for n, doc in self.versions.items():
            self.assertEqual(doc["unknownProvider"]["class"], "generated", f"version {n}")
            for k in doc["kinds"]:
                providers = [p["provider"] for p in k.get("providers", [])]
                self.assertEqual(len(providers), len(set(providers)), f"version {n} {k['kind']}: a provider twice")
                for p in k.get("providers", []):
                    if p["provider"] in CONTRACT_GENERATED:
                        self.assertEqual(p["class"], "generated",
                                         f"version {n}: {p['provider']} is generated and may not be ranked above it")
                    if p["provider"] in CONTRACT_MEASURED:
                        self.assertEqual(p["class"], "measured", f"version {n}: {p['provider']}")
            names = [k["kind"] for k in doc["kinds"]]
            self.assertEqual(len(names), len(set(names)), f"version {n}: a kind twice")

    def test_mapped_providers_are_known(self) -> None:
        for n, doc in self.versions.items():
            providers = {p["provider"] for k in doc["kinds"] for p in k.get("providers", [])}
            unknown = set(doc["providerMapping"].values()) - providers
            self.assertFalse(unknown, f"version {n} maps origins to unlisted providers {sorted(unknown)}")


if __name__ == "__main__":
    unittest.main()
