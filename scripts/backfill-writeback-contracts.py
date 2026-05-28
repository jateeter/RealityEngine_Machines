#!/usr/bin/env python3
"""Backfill localAIStack -> PE write-back contracts.

Dry-run by default. Pass --write to modify machine JSON files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TTL_MS = 300000
INGEST = {
    "endpoint": "/api/integrations/completions",
    "method": "POST",
    "triggerPush": False,
    "compactPush": True,
}


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def slug(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", ".", text)
    return text.strip(".") or "unknown"


def machine_code(path: Path, metadata: dict[str, Any]) -> str:
    tagging = as_object(metadata.get("tagging"))
    code = tagging.get("machineCode")
    if isinstance(code, str) and code.strip():
        return slug(code)
    match = re.match(r"([A-Za-z]+[-_]?\d+)", path.stem)
    return slug(match.group(1)) if match else slug(path.stem)


def semantics_for_region(metadata: dict[str, Any], length: int) -> list[str]:
    semantics = [x for x in as_list(metadata.get("inputSemantics")) if isinstance(x, str) and x.strip()]
    if len(semantics) == length:
        return semantics
    return [f"localai_writeback_{idx}" for idx in range(length)]


def writeback_for(path: Path, machine: dict[str, Any], metadata: dict[str, Any], agent_binding: dict[str, Any]) -> dict[str, Any]:
    mapping = as_object(machine.get("perceptualMapping"))
    input_region = as_object(mapping.get("input"))
    offset = input_region.get("offset")
    length = input_region.get("length")
    if not isinstance(offset, int) or not isinstance(length, int) or length <= 0:
        raise ValueError(f"{path}: invalid perceptualMapping.input region")

    code = machine_code(path, metadata)
    agent = slug(agent_binding.get("agent"))
    sensor_id = f"localai.{code}.{agent}.completion"
    name = f"localAIStack {code} {agent} completion"
    region = {"offset": offset, "length": length}
    source_mapping = {
        "id": f"localai-{code}-completion",
        "sensorId": sensor_id,
        "name": name,
        "region": region,
        "ttlMs": TTL_MS,
    }
    return {
        "type": "pe-sensor",
        "provider": "localai",
        "sensorId": sensor_id,
        "name": name,
        "region": region,
        "semantics": semantics_for_region(metadata, length),
        "ttlMs": TTL_MS,
        "normalization": "already-normalized-0-1",
        "ingest": dict(INGEST),
        "sourceMapping": source_mapping,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machines-root", default="machines")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    machines_root = Path(args.machines_root)
    if not machines_root.is_absolute():
        machines_root = repo_root / machines_root

    changed = 0
    for path in sorted(machines_root.rglob("*.json")):
        with path.open() as handle:
            data = json.load(handle)
        machine = as_object(data.get("machine"))
        metadata = as_object(machine.get("metadata"))
        agent_binding = as_object(metadata.get("agentBinding"))
        if not agent_binding:
            continue
        if agent_binding.get("mode") == "observe":
            continue

        desired = writeback_for(path, machine, metadata, agent_binding)
        if agent_binding.get("writeBack") == desired:
            continue
        agent_binding["writeBack"] = desired
        changed += 1
        rel = path.relative_to(repo_root)
        print(f"{rel}: writeBack")
        if args.write:
            path.write_text(json.dumps(data, indent=2) + "\n")

    mode = "updated" if args.write else "would update"
    print(f"{mode} {changed} machine files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
