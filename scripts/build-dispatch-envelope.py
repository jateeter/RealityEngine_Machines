#!/usr/bin/env python3
"""Build a canonical RE -> localAIStack dispatch envelope from a machine file."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def machine_code(path: Path) -> str:
    match = re.match(r"([A-Za-z]+[-_]?\d+)", path.stem)
    return match.group(1).replace("_", "-").upper() if match else path.stem


def status_from_rag(rag: str) -> str:
    return {"RED": "error", "AMBER": "warning", "GREEN": "info"}.get(rag, "info")


def governance_for_rule(metadata: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    governance = as_object(metadata.get("governance"))
    sla = as_object(governance.get("sla"))
    process_status = rule.get("processStatus") or status_from_rag(str(rule.get("ragStatusCode")))
    return {
        "ragStatusCode": rule.get("ragStatusCode"),
        "processStatus": process_status,
        "ownerTeam": governance.get("ownerTeam"),
        "slaSeconds": sla.get(process_status),
        "runbook": governance.get("runbook"),
        "escalationPolicy": governance.get("escalationPolicy"),
        "contact": governance.get("contact"),
        "description": rule.get("description"),
    }


def build_envelope(path: Path, sequence_id: str | None = None) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    machine = as_object(data.get("machine"))
    metadata = as_object(machine.get("metadata"))
    mapping = as_object(machine.get("perceptualMapping"))
    trigger_config = as_object(metadata.get("triggerConfig"))
    agent_binding = as_object(metadata.get("agentBinding"))
    rules = as_list(trigger_config.get("rules"))
    if not rules:
        raise SystemExit(f"{path}: metadata.triggerConfig.rules is empty")
    rule = next((r for r in rules if as_object(r).get("sequenceId") == sequence_id), rules[0])
    rule = as_object(rule)
    sequence = next(
        (as_object(s) for s in as_list(machine.get("sequences")) if as_object(s).get("id") == rule.get("sequenceId")),
        {},
    )
    values = as_list(rule.get("outputMatches"))
    active = [idx for idx, value in enumerate(values) if value]
    asserted_label = "+".join(f"cell-{idx}" for idx in active) if active else "none"
    actions = as_list(agent_binding.get("allowedActions"))
    action = str(actions[active[0]]) if active and active[0] < len(actions) else str(actions[0] if actions else rule.get("description"))

    return {
        "schemaVersion": "1.0.0",
        "envelopeType": "ces.terminal.event",
        "envelopeId": str(uuid4()),
        "correlationId": str(uuid4()),
        "emittedAt": datetime.now(UTC).isoformat(),
        "source": {
            "engine": "RE",
            "instance": "local",
            "endpoint": "http://localhost:3000",
        },
        "ces": {
            "machineId": str(machine.get("id") or path.stem),
            "machineName": str(machine.get("name")),
            "machineCode": machine_code(path),
            "sequenceId": str(rule.get("sequenceId")),
            "sequenceName": str(sequence.get("name") or rule.get("sequenceId")),
            "outputIndex": active[0] if active else 0,
            "stepNumber": 0,
            "perceptualMapping": {
                "input": as_object(mapping.get("input")),
                "output": as_object(mapping.get("output")),
            },
            "provenance": [str(sequence.get("id") or rule.get("sequenceId"))],
            "deprecation": None,
        },
        "outputVector": {
            "values": values,
            "encoding": "one-hot" if len(active) <= 1 else "multi-hot",
            "semantics": [{"index": idx, "label": f"cell-{idx}"} for idx in range(len(values))],
            "assertedLabel": asserted_label,
        },
        "projection": None,
        "governance": governance_for_rule(metadata, rule),
        "dispatch": {
            "processId": str(trigger_config.get("processId")),
            "processName": str(trigger_config.get("processName")),
            "agent": str(agent_binding.get("agent")),
            "action": action,
            "agentActionsCatalog": actions,
            "trigger": str(agent_binding.get("trigger")),
            "autonomyMode": str(agent_binding.get("mode")),
            "writeBack": agent_binding.get("writeBack"),
            "endpoint": {
                "kind": "graphql",
                "url": str(trigger_config.get("endpoint")),
                "mutation": as_object(trigger_config.get("dispatch")).get("mutation", "updateProcessState"),
                "schemaRef": as_object(trigger_config.get("dispatch")).get(
                    "schemaRef",
                    "localAIStack/services/api/routers/graphql_endpoint.py",
                ),
            },
        },
        "mqttContext": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("machine_file")
    parser.add_argument("--sequence-id")
    args = parser.parse_args()
    print(json.dumps(build_envelope(Path(args.machine_file), args.sequence_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
