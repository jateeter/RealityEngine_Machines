#!/usr/bin/env python3
"""Backfill first-class agentBinding and machineClass metadata.

Dry-run by default.  Pass --write to modify machine JSON files.
The derivation is intentionally conservative and uses existing metadata:
dispatchableAgent, aiTrigger, agentActions, triggerConfig, and domain defaults.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def load_registry(repo_root: Path) -> dict[str, Any]:
    with (repo_root / "domains" / "domain-registry.json").open() as handle:
        return json.load(handle)["domains"]


def primary_domain(metadata: dict[str, Any]) -> str:
    tagging = as_object(metadata.get("tagging"))
    return str(
        tagging.get("primaryDomain")
        or metadata.get("category")
        or metadata.get("domain")
        or "missing"
    )


def infer_machine_class(filename: str, machine: dict[str, Any], metadata: dict[str, Any]) -> str:
    haystack = " ".join(
        [
            filename,
            str(machine.get("name", "")),
            str(machine.get("description", "")),
            " ".join(str(x) for x in as_list(metadata.get("tags"))),
        ]
    ).lower()
    rules = [
        ("sensor-preaggregator", ["preaggregator", "pre-aggregator", "sensor-normalizer"]),
        ("agent-dispatcher", ["agent-dispatcher", "dispatcher", "dispatch"]),
        ("risk-forecaster", ["forecast", "predictor", "risk", "readiness"]),
        ("governance-escalator", ["escalator", "governance", "guardrail"]),
        ("bridge", ["bridge", "overlay", "projection"]),
        ("safety-compliance-checker", ["safety", "compliance", "checker"]),
        ("evidence-archive", ["archive", "evidence", "record-retention"]),
        ("optimizer", ["optimizer", "optimization", "planner"]),
        ("outcome-stabilizer", ["stabilizer", "learning-loop", "recovery"]),
    ]
    for machine_class, needles in rules:
        if any(needle in haystack for needle in needles):
            return machine_class
    return "signal-monitor"


def build_agent_binding(metadata: dict[str, Any], domain_defaults: dict[str, Any]) -> dict[str, Any] | None:
    agent = metadata.get("dispatchableAgent")
    if not isinstance(agent, str) or not agent.strip():
        return None
    actions = [x for x in as_list(metadata.get("agentActions")) if isinstance(x, str) and x.strip()]
    rules = as_list(as_object(metadata.get("triggerConfig")).get("rules"))
    if not actions:
        actions = [
            str(rule.get("description") or rule.get("processName") or "Review CES output and recommend next action.")
            for rule in rules
            if isinstance(rule, dict)
        ]
    if not actions:
        actions = ["Review CES output and recommend next action."]
    trigger = metadata.get("aiTrigger")
    if not isinstance(trigger, str) or not trigger.strip():
        trigger = str(rules[0].get("processName", agent)) if rules and isinstance(rules[0], dict) else agent
    mode = domain_defaults.get("defaultAutonomy", "advise")
    return {
        "agent": agent,
        "mode": mode,
        "trigger": trigger,
        "allowedActions": actions,
        "writeBack": {"type": "none"},
        "riskControls": {
            "requiresHumanApproval": mode in {"supervised-act", "automated-act"},
            "requiresRunbook": mode in {"supervised-act", "automated-act"},
            "maxAutonomy": mode,
            "blockedWhenRag": ["RED"] if mode == "automated-act" else []
        }
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
    registry = load_registry(repo_root)

    changed = 0
    for path in sorted(machines_root.rglob("*.json")):
        with path.open() as handle:
            data = json.load(handle)
        machine = as_object(data.get("machine"))
        metadata = as_object(machine.get("metadata"))
        if not machine or not metadata:
            continue

        updates = []
        if "machineClass" not in metadata:
            metadata["machineClass"] = infer_machine_class(path.name, machine, metadata)
            updates.append("machineClass")

        domain_defaults = registry.get(primary_domain(metadata), {})
        if "agentBinding" not in metadata:
            binding = build_agent_binding(metadata, domain_defaults)
            if binding:
                metadata["agentBinding"] = binding
                updates.append("agentBinding")

        if updates:
            changed += 1
            rel = path.relative_to(repo_root)
            print(f"{rel}: {', '.join(updates)}")
            if args.write:
                path.write_text(json.dumps(data, indent=2) + "\n")

    mode = "updated" if args.write else "would update"
    print(f"{mode} {changed} machine files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
