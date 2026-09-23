#!/usr/bin/env python3
"""Build a canonical RE -> localAIStack dispatch envelope from a machine file."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
    # Same algorithm as the runtimes' asserted_label(): cell_<i>+cell_<j>.
    asserted_label = "+".join(f"cell_{idx}" for idx in active) if active else "none"
    actions = as_list(agent_binding.get("allowedActions"))
    action = str(actions[active[0]]) if active and active[0] < len(actions) else str(actions[0] if actions else rule.get("description"))
    output_region = as_object(mapping.get("output"))
    # The runtimes name a machine without an explicit id "machine-<file stem>".
    machine_id = str(machine.get("id") or f"machine-{path.stem.lower().replace('_', '-')}")
    # actionCode is the matching output event's metadata.action (RealityEngine_CI#365).
    action_code = next(
        (
            as_object(out.get("metadata")).get("action")
            for event in as_list(sequence.get("events"))
            for out in as_list(as_object(event).get("outputEvents"))
            if as_object(out).get("vector") == values
        ),
        None,
    )
    sequence_id = str(rule.get("sequenceId"))
    governance = governance_for_rule(metadata, rule)
    governance.update({
        "hasMachineGovernance": bool(as_object(metadata.get("governance"))),
        "machineId": machine_id,
        "machineName": str(machine.get("name")),
        "sequenceId": sequence_id,
        "actionCode": action_code,
        "source": "rule-only",
    })

    # The runtime shape: canonical 1.0.0 per schemas/ai-trigger-envelope.schema.json
    # (RealityEngine_CI INTEGRATION_ROADMAP.md \u00a76 Q3). Field for field what
    # the C++ PE emits for the same machine output, so an example built here is
    # interchangeable with one captured from a running engine.
    return {
        "schemaVersion": "1.0.0",
        "envelopeType": "ces.terminal.event",
        "envelopeId": f"trigger-envelope-{uuid4()}",
        "correlationId": f"trigger-correlation-{uuid4()}",
        "emittedAtMs": int(datetime.now(UTC).timestamp() * 1000),
        "source": {
            "engine": "PE",
            "observedEngine": "RE",
            "endpoint": "http://localhost:5301",
        },
        "ces": {
            "machineId": machine_id,
            "machineName": str(machine.get("name")),
            "machineCode": str(metadata.get("machineCode") or ""),
            "sequenceIds": [sequence_id],
            "stepNumber": 0,
            "perceptualMapping": {
                "output": output_region or None,
            },
            "provenance": [str(sequence.get("id") or sequence_id)],
            "deprecation": None,
        },
        "outputVector": {
            "values": values,
            "encoding": "vector",
            "semantics": [{"index": idx, "label": f"cell_{idx}"} for idx in range(len(values))],
            "assertedLabel": asserted_label,
        },
        "projection": None,
        "governance": governance,
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
