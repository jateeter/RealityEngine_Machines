#!/usr/bin/env python3
"""Inventory and validate semantic published-domain buses.

Mechanical range/core buses are set aside. Semantic buses are checked into
`domains/semantic-bus-registry.json` so runtimes can expose bus semantics without
re-parsing the machine corpus.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RANGE_BUS_RE = re.compile(
    r"^[a-z][a-z0-9-]*\.(agx|bsx|csx|dcx|dlx|enx|hsph|lsx|tfx)-\d{3}-\d{3}$"
)
CORE_BUS_RE = re.compile(r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*-core$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def as_obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_region(value: Any, label: str, errors: list[str]) -> dict[str, int] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None
    offset = value.get("offset")
    length = value.get("length")
    if not isinstance(offset, int) or offset < 0:
        errors.append(f"{label}.offset must be a non-negative integer")
    if not isinstance(length, int) or length < 1:
        errors.append(f"{label}.length must be a positive integer")
    if errors and any(item.startswith(label) for item in errors):
        return None
    return {"offset": offset, "length": length}


def classify_bus(bus_id: str) -> str:
    if RANGE_BUS_RE.match(bus_id):
        return "mechanical-range"
    if CORE_BUS_RE.match(bus_id):
        return "mechanical-core"
    return "semantic"


def compact_region(region: Any) -> dict[str, int] | None:
    if not isinstance(region, dict):
        return None
    offset = region.get("offset")
    length = region.get("length")
    if isinstance(offset, int) and isinstance(length, int):
        return {"offset": offset, "length": length}
    return None


def collect_bus(path: Path, machines_root: Path) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    root = load_json(path)
    machine = as_obj(root.get("machine"))
    metadata = as_obj(machine.get("metadata"))
    bus = as_obj(metadata.get("publishedDomainBus"))
    if not bus:
        return None
    rel = path.relative_to(machines_root).as_posix()
    return rel, root, machine, metadata


def derive_output_semantics(machine: dict[str, Any]) -> list[dict[str, Any]]:
    semantics: list[dict[str, Any]] = []
    for seq in as_list(machine.get("sequences")):
        if not isinstance(seq, dict):
            continue
        item: dict[str, Any] = {
            "sequenceId": seq.get("id"),
            "name": seq.get("name"),
        }
        vectors = []
        for vector in as_list(seq.get("vectors")):
            if not isinstance(vector, dict):
                continue
            for out in as_list(vector.get("outputVectors")):
                if isinstance(out, dict):
                    vectors.append({
                        "id": out.get("id"),
                        "vector": out.get("vector"),
                    })
        if vectors:
            item["outputVectors"] = vectors
        semantics.append(item)
    return semantics


def semantic_entry(rel: str, machine: dict[str, Any], metadata: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    bus = as_obj(metadata.get("publishedDomainBus"))
    bus_id = bus.get("id")
    for field in ("id", "tag", "domain", "name", "description"):
        if not nonempty(bus.get(field)):
            errors.append(f"publishedDomainBus.{field} must be a non-empty string")
    input_region = validate_region(bus.get("inputRegion"), "publishedDomainBus.inputRegion", errors)
    output_region = validate_region(bus.get("outputRegion"), "publishedDomainBus.outputRegion", errors)
    composition = as_list(bus.get("inputComposition"))
    if not composition:
        errors.append("publishedDomainBus.inputComposition must be a non-empty array")

    roles: list[dict[str, Any]] = []
    source_domains: set[str] = set()
    source_machines: set[str] = set()
    used_elements: set[int] = set()
    for idx, item in enumerate(composition):
        if not isinstance(item, dict):
            errors.append(f"publishedDomainBus.inputComposition[{idx}] must be an object")
            continue
        role = item.get("role")
        source_machine = item.get("sourceMachine")
        if not nonempty(role):
            errors.append(f"publishedDomainBus.inputComposition[{idx}].role must be a non-empty string")
        if not nonempty(source_machine):
            errors.append(f"publishedDomainBus.inputComposition[{idx}].sourceMachine must be a non-empty string")
        source_domain = item.get("sourceDomain")
        if nonempty(source_domain):
            source_domains.add(source_domain)
        if nonempty(source_machine):
            source_machines.add(source_machine)
        machine_input = None
        if item.get("machineInputRegion") is not None:
            machine_input = validate_region(item.get("machineInputRegion"), f"publishedDomainBus.inputComposition[{idx}].machineInputRegion", errors)
        machine_output = validate_region(item.get("machineOutputRegion"), f"publishedDomainBus.inputComposition[{idx}].machineOutputRegion", errors)
        elements = item.get("composedInputElements")
        if not isinstance(elements, list) or not elements or not all(isinstance(v, int) and v >= 0 for v in elements):
            errors.append(f"publishedDomainBus.inputComposition[{idx}].composedInputElements must be a non-empty integer array")
            elements = []
        for element in elements:
            used_elements.add(element)
        roles.append({
            "role": role,
            "sourceDomain": source_domain,
            "sourceMachine": source_machine,
            "machineInputRegion": machine_input,
            "machineOutputRegion": machine_output,
            "composedInputElements": elements,
            "summary": item.get("summary"),
            "mapping": item.get("mapping") if isinstance(item.get("mapping"), dict) else {},
        })

    input_semantics = metadata.get("inputSemantics")
    if input_semantics is not None:
        if not isinstance(input_semantics, list) or not all(nonempty(v) for v in input_semantics):
            errors.append("metadata.inputSemantics must be a string array when present")
        elif input_region and len(input_semantics) != input_region["length"]:
            errors.append(
                "metadata.inputSemantics length must match publishedDomainBus.inputRegion.length "
                f"({len(input_semantics)} != {input_region['length']})"
            )
    elif input_region:
        errors.append("semantic published buses must declare metadata.inputSemantics")

    if input_region:
        out_of_range = sorted(v for v in used_elements if v >= input_region["length"])
        if out_of_range:
            errors.append(f"composedInputElements outside inputRegion length: {out_of_range}")

    downstream = []
    for consumer in as_list(bus.get("downstreamConsumers")):
        if isinstance(consumer, dict):
            downstream.append({
                "machine": consumer.get("machine"),
                "inputRegion": compact_region(consumer.get("inputRegion")),
                "role": consumer.get("role"),
            })

    if not downstream:
        errors.append("semantic published buses must declare publishedDomainBus.downstreamConsumers")

    return {
        "id": bus_id,
        "tag": bus.get("tag"),
        "domain": bus.get("domain"),
        "name": bus.get("name"),
        "description": bus.get("description"),
        "machineFile": rel,
        "machineName": machine.get("name"),
        "inputRegion": input_region,
        "outputRegion": output_region,
        "inputSemantics": input_semantics if isinstance(input_semantics, list) else [],
        "outputSpace": metadata.get("outputSpace"),
        "outputSemantics": derive_output_semantics(machine),
        "sourceDomains": sorted(source_domains),
        "sourceMachines": sorted(source_machines),
        "inputComposition": roles,
        "downstreamConsumers": downstream,
        "peContract": bus.get("peContract") if isinstance(bus.get("peContract"), dict) else {},
        "tags": metadata.get("tags") if isinstance(metadata.get("tags"), list) else [],
    }


def build_registry(repo_root: Path, machines_root: Path) -> tuple[dict[str, Any], list[str]]:
    semantic: list[dict[str, Any]] = []
    mechanical: list[dict[str, Any]] = []
    errors: list[str] = []
    counts: Counter[str] = Counter()

    for path in sorted(machines_root.rglob("*.json")):
        collected = collect_bus(path, machines_root)
        if collected is None:
            continue
        rel, _root, machine, metadata = collected
        bus = as_obj(metadata.get("publishedDomainBus"))
        bus_id = bus.get("id", "")
        classification = classify_bus(bus_id)
        counts[classification] += 1
        counts["published"] += 1
        if classification != "semantic":
            mechanical.append({
                "id": bus_id,
                "classification": classification,
                "domain": bus.get("domain"),
                "name": bus.get("name"),
                "machineFile": rel,
                "inputRegion": compact_region(bus.get("inputRegion")),
                "outputRegion": compact_region(bus.get("outputRegion")),
            })
            continue

        entry_errors: list[str] = []
        entry = semantic_entry(rel, machine, metadata, entry_errors)
        if entry_errors:
            for error in entry_errors:
                errors.append(f"{rel}: {error}")
        semantic.append(entry)

    seen: dict[str, str] = {}
    for entry in semantic:
        bus_id = entry.get("id")
        if bus_id in seen:
            errors.append(f"{entry.get('machineFile')}: duplicate semantic bus id {bus_id!r}; first seen in {seen[bus_id]}")
        elif isinstance(bus_id, str):
            seen[bus_id] = str(entry.get("machineFile"))

    semantic.sort(key=lambda item: item.get("id") or "")
    mechanical.sort(key=lambda item: item.get("id") or "")

    registry = {
        "schemaVersion": "1.0.0",
        "purpose": "Validated semantic published-domain bus registry. Mechanical range/core buses are inventoried but set aside from the semantic bus contract.",
        "generatedBy": "scripts/inventory-semantic-buses.py",
        "sourceRoot": str(machines_root.relative_to(repo_root)) if machines_root.is_relative_to(repo_root) else str(machines_root),
        "classificationPolicy": {
            "mechanicalRangePattern": RANGE_BUS_RE.pattern,
            "mechanicalCorePattern": CORE_BUS_RE.pattern,
            "semanticDefinition": "Any publishedDomainBus that is not a mechanical range bus or mechanical core aggregation bus.",
        },
        "counts": {
            "publishedBuses": counts["published"],
            "semanticBuses": len(semantic),
            "mechanicalRangeBuses": counts["mechanical-range"],
            "mechanicalCoreBuses": counts["mechanical-core"],
            "setAsideMechanicalBuses": len(mechanical),
        },
        "semanticBuses": semantic,
        "setAsideMechanicalBuses": mechanical,
    }
    return registry, errors


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machines-root", default="machines")
    parser.add_argument("--registry", default="domains/semantic-bus-registry.json")
    parser.add_argument("--write", action="store_true", help="write the generated registry")
    parser.add_argument("--check", action="store_true", help="fail if the checked-in registry is stale")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    machines_root = Path(args.machines_root)
    if not machines_root.is_absolute():
        machines_root = repo_root / machines_root
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = repo_root / registry_path

    registry, errors = build_registry(repo_root, machines_root)

    if args.write:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(stable_json(registry))

    stale = False
    if args.check:
        expected = stable_json(registry)
        if not registry_path.exists():
            errors.append(f"semantic bus registry missing: {registry_path.relative_to(repo_root)}")
        else:
            actual = registry_path.read_text()
            if actual != expected:
                stale = True
                errors.append(f"semantic bus registry stale: run scripts/inventory-semantic-buses.py --write")

    if not args.summary_only:
        for error in errors[:100]:
            print(f"ERROR {error}")
        if len(errors) > 100:
            print(f"ERROR ... {len(errors) - 100} more semantic bus validation errors")

    print("Semantic bus inventory summary")
    for key, value in registry["counts"].items():
        print(f"  {key}: {value}")
    if stale:
        print(f"  registry: stale ({registry_path})")
    elif registry_path.exists():
        print(f"  registry: {registry_path.relative_to(repo_root)}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
