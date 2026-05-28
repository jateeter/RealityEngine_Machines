#!/usr/bin/env python3
"""Build a PE completion-ingest payload from a machine write-back contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_payload(path: Path, values: list[float] | None = None) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    machine = as_object(data.get("machine"))
    metadata = as_object(machine.get("metadata"))
    agent_binding = as_object(metadata.get("agentBinding"))
    write_back = as_object(agent_binding.get("writeBack"))
    if write_back.get("type") != "pe-sensor":
        raise SystemExit(f"{path}: agentBinding.writeBack.type is not pe-sensor")

    region = as_object(write_back.get("region"))
    length = int(region.get("length"))
    if values is None:
        values = [0.0 for _ in range(length)]
        if values:
            values[0] = 1.0
    if len(values) != length:
        raise SystemExit(f"{path}: values length {len(values)} does not match writeBack region length {length}")

    ingest = as_object(write_back.get("ingest"))
    return {
        "provider": write_back.get("provider", "localai"),
        "agent": agent_binding.get("agent"),
        "completionId": f"completion-{uuid4()}",
        "correlationId": str(uuid4()),
        "envelopeId": str(uuid4()),
        "sensorId": write_back.get("sensorId"),
        "name": write_back.get("name"),
        "region": region,
        "sourceMapping": write_back.get("sourceMapping"),
        "values": values,
        "ttlMs": write_back.get("ttlMs", 300000),
        "metadata": {
            "machineName": machine.get("name"),
            "machineClass": metadata.get("machineClass"),
            "semantics": as_list(write_back.get("semantics")),
            "normalization": write_back.get("normalization"),
            "writeBackType": write_back.get("type"),
        },
        "triggerPush": ingest.get("triggerPush", False),
        "compactPush": ingest.get("compactPush", True),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("machine_file")
    parser.add_argument("--values", help="Comma-separated numeric values. Defaults to a first-cell recommendation.")
    args = parser.parse_args()
    values = None
    if args.values:
        values = [float(part.strip()) for part in args.values.split(",") if part.strip()]
    print(json.dumps(build_payload(Path(args.machine_file), values), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
