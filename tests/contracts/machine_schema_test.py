#!/usr/bin/env python3
"""Contract checks for the canonical machine JSON schema."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHINES = REPO_ROOT / "machines"
SCHEMA = REPO_ROOT / "schemas" / "machine.schema.json"
MACHINE_CLASS_SCHEMA = REPO_ROOT / "schemas" / "machine-class.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


class MachineSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA)
        cls.machine_classes = set(load_json(MACHINE_CLASS_SCHEMA)["enum"])
        cls.machines = [
            (path, load_json(path))
            for path in sorted(MACHINES.rglob("*.json"))
        ]

    def test_schema_declares_core_cross_engine_contract(self) -> None:
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.schema["$id"], "https://realityengine.example.org/schemas/machine.schema.json")
        self.assertEqual(self.schema["required"], ["version", "machine"])

        machine_def = self.schema["$defs"]["machine"]
        self.assertEqual(
            machine_def["required"],
            ["name", "description", "metadata", "arbiterRule", "perceptualMapping", "sequences"],
        )
        self.assertEqual(machine_def["properties"]["arbiterRule"]["enum"], ["PASSTHROUGH"])
        self.assertEqual(machine_def["properties"]["matchAlgorithm"]["enum"], ["equals", "gte"])

    def test_schema_uses_standard_machine_class_catalog(self) -> None:
        machine_class_ref = self.schema["$defs"]["metadata"]["properties"]["machineClass"]["$ref"]
        self.assertEqual(machine_class_ref, "machine-class.schema.json")
        self.assertEqual(
            set(load_json(MACHINE_CLASS_SCHEMA)["enum"]),
            self.machine_classes,
        )

    def test_schema_ref_graph_is_filename_consistent_and_resolvable(self) -> None:
        """Every schema $id is filename-based and every external $ref resolves to a
        file that exists, so a standard $id/URI validator can load the whole graph
        (regression for the mixed $id/-1.0.0 ref convention)."""
        schema_dir = REPO_ROOT / "schemas"
        files = {p.name for p in schema_dir.glob("*.schema.json")}
        base = "https://realityengine.example.org/schemas/"

        def external_refs(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "$ref" and isinstance(v, str) and not v.startswith("#"):
                        yield v.split("#", 1)[0]
                    else:
                        yield from external_refs(v)
            elif isinstance(node, list):
                for item in node:
                    yield from external_refs(item)

        for name in files:
            doc = load_json(schema_dir / name)
            self.assertEqual(doc.get("$id"), base + name, f"{name}: $id must be filename-based")
            for ref in external_refs(doc):
                self.assertIn(ref, files, f"{name}: $ref '{ref}' does not resolve to a schema file")

    def test_required_contract_schemas_present(self) -> None:
        """Authoritative corpus artifacts each have a schema."""
        schema_dir = REPO_ROOT / "schemas"
        for required in (
            "machine.schema.json",
            "domain-manifest.schema.json",
            "domain-registry.schema.json",
            "semantic-bus-registry.schema.json",
            "ai-trigger-envelope.schema.json",
            "trigger-scenario.schema.json",
        ):
            self.assertTrue((schema_dir / required).exists(), f"missing schema: {required}")

    def test_schema_models_published_domain_bus_extension(self) -> None:
        metadata_properties = self.schema["$defs"]["metadata"]["properties"]
        self.assertIn("interconnections", metadata_properties)
        self.assertIn("publishedDomainBus", metadata_properties)
        self.assertIn("domainLevelTag", metadata_properties)

        bus_def = self.schema["$defs"]["publishedDomainBus"]
        self.assertEqual(
            bus_def["required"],
            ["id", "tag", "domain", "inputRegion", "outputRegion", "inputComposition"],
        )

    def test_current_corpus_satisfies_schema_required_contract_shape(self) -> None:
        failures: list[str] = []

        for path, root in self.machines:
            machine = root.get("machine")
            rel = path.relative_to(REPO_ROOT)

            if not isinstance(root.get("version"), str) or not root["version"]:
                failures.append(f"{rel}: version must be a non-empty string")
            if not isinstance(machine, dict):
                failures.append(f"{rel}: machine must be an object")
                continue

            for key in self.schema["$defs"]["machine"]["required"]:
                if key not in machine:
                    failures.append(f"{rel}: machine.{key} missing")

            metadata = machine.get("metadata", {})
            if not isinstance(metadata, dict):
                failures.append(f"{rel}: machine.metadata must be an object")
                continue

            machine_class = metadata.get("machineClass")
            if machine_class not in self.machine_classes:
                failures.append(f"{rel}: metadata.machineClass={machine_class!r} not in catalog")

            mapping = machine.get("perceptualMapping", {})
            for label in ("input", "output"):
                region = mapping.get(label)
                if not isinstance(region, dict):
                    failures.append(f"{rel}: perceptualMapping.{label} must be an object")
                    continue
                if not isinstance(region.get("offset"), int) or region["offset"] < 0:
                    failures.append(f"{rel}: perceptualMapping.{label}.offset must be non-negative integer")
                if not isinstance(region.get("length"), int) or region["length"] < 1:
                    failures.append(f"{rel}: perceptualMapping.{label}.length must be positive integer")

            if mapping.get("bitsPerElement") not in {1, 2, 4, 8}:
                failures.append(f"{rel}: perceptualMapping.bitsPerElement unsupported")

            sequences = machine.get("sequences")
            if not isinstance(sequences, list) or not sequences:
                failures.append(f"{rel}: machine.sequences must be a non-empty array")
                continue
            for idx, sequence in enumerate(sequences):
                if not isinstance(sequence, dict):
                    failures.append(f"{rel}: sequences[{idx}] must be an object")
                    continue
                if not isinstance(sequence.get("id"), str) or not sequence["id"]:
                    failures.append(f"{rel}: sequences[{idx}].id must be non-empty string")
                if not isinstance(sequence.get("vectors"), list) or not sequence["vectors"]:
                    failures.append(f"{rel}: sequences[{idx}].vectors must be non-empty array")

        self.assertFalse(failures, "\n".join(failures[:50]))


if __name__ == "__main__":
    unittest.main()
