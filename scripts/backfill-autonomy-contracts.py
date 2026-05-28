#!/usr/bin/env python3
"""Backfill four-mode agent autonomy policy contracts.

Dry-run by default. Pass --write to modify machine JSON files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PROTECTED_DOMAINS = {
    "health-services",
    "health-personal",
    "life-balance",
    "community-services",
    "legal-services",
}
AUTOMATED_DOMAINS = {"agriculture", "built-space", "transportation", "data-center", "energy"}
AUTOMATED_KEYWORDS = {
    "balancer",
    "controller",
    "dispatch-controller",
    "optimizer",
    "optimization",
    "planner",
    "scheduler",
    "scheduling",
}
AUTOMATED_BLOCKERS = {
    "alert",
    "biohazard",
    "compliance",
    "crisis",
    "danger",
    "evidence",
    "fraud",
    "governance",
    "guardian",
    "hazard",
    "incident",
    "risk",
    "safety",
    "security",
}
OBSERVE_KEYWORDS = {
    "archive",
    "availability",
    "evidence",
    "monitor",
    "readiness",
    "record",
    "report",
    "reporting",
    "tracker",
    "watch",
}
ADVISE_KEYWORDS = {
    "forecast",
    "forecaster",
    "prediction",
    "predictor",
    "triage",
    "warning",
}
POLICY = {
    "observe": {
        "mode": "observe",
        "stage": 0,
        "writeBackType": "none",
        "canWriteBack": False,
        "canStageActions": False,
        "canExecuteActions": False,
        "requiresHumanApproval": False,
        "requiresRunbook": False,
        "blockedWhenRag": [],
    },
    "advise": {
        "mode": "advise",
        "stage": 1,
        "writeBackType": "pe-sensor",
        "canWriteBack": True,
        "canStageActions": False,
        "canExecuteActions": False,
        "requiresHumanApproval": False,
        "requiresRunbook": False,
        "blockedWhenRag": [],
    },
    "supervised-act": {
        "mode": "supervised-act",
        "stage": 2,
        "writeBackType": "pe-sensor",
        "canWriteBack": True,
        "canStageActions": True,
        "canExecuteActions": False,
        "requiresHumanApproval": True,
        "requiresRunbook": True,
        "blockedWhenRag": ["RED"],
    },
    "automated-act": {
        "mode": "automated-act",
        "stage": 3,
        "writeBackType": "pe-sensor",
        "canWriteBack": True,
        "canStageActions": True,
        "canExecuteActions": True,
        "requiresHumanApproval": False,
        "requiresRunbook": True,
        "blockedWhenRag": ["AMBER", "RED"],
        "rollbackRequired": True,
    },
}
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


def primary_domain(metadata: dict[str, Any]) -> str:
    tagging = as_object(metadata.get("tagging"))
    return str(tagging.get("primaryDomain") or metadata.get("category") or metadata.get("domain") or "missing")


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


def infer_mode(path: Path, machine: dict[str, Any], metadata: dict[str, Any]) -> str:
    domain = primary_domain(metadata)
    if domain in PROTECTED_DOMAINS:
        return "supervised-act"

    title_text = " ".join(
        [
            path.stem,
            str(machine.get("name", "")),
            str(metadata.get("operationalFocus", "")),
        ]
    ).lower()
    context_text = " ".join(
        [
            title_text,
            str(machine.get("description", "")),
            " ".join(str(x) for x in as_list(metadata.get("tags"))),
        ]
    ).lower()
    title_words = set(re.split(r"[^a-z0-9]+", title_text))
    context_words = set(re.split(r"[^a-z0-9]+", context_text))
    title_hyphen_text = title_text.replace("_", "-")
    context_hyphen_text = context_text.replace("_", "-")

    if domain in AUTOMATED_DOMAINS:
        automated = any(keyword in title_words or keyword in title_hyphen_text for keyword in AUTOMATED_KEYWORDS)
        blocked = any(keyword in title_words or keyword in title_hyphen_text for keyword in AUTOMATED_BLOCKERS)
        if automated and not blocked:
            return "automated-act"

    if any(keyword in context_words or keyword in context_hyphen_text for keyword in ADVISE_KEYWORDS):
        return "advise"
    if any(keyword in title_words or keyword in title_hyphen_text for keyword in OBSERVE_KEYWORDS):
        return "observe"
    return "advise"


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
        "sourceMapping": {
            "id": f"localai-{code}-completion",
            "sensorId": sensor_id,
            "name": name,
            "region": region,
            "ttlMs": TTL_MS,
        },
    }


def apply_policy(path: Path, machine: dict[str, Any], metadata: dict[str, Any], agent_binding: dict[str, Any]) -> list[str]:
    mode = infer_mode(path, machine, metadata)
    policy = dict(POLICY[mode])
    risk_controls = {
        "requiresHumanApproval": policy["requiresHumanApproval"],
        "requiresRunbook": policy["requiresRunbook"],
        "maxAutonomy": mode,
        "blockedWhenRag": list(policy["blockedWhenRag"]),
    }

    updates: list[str] = []
    if agent_binding.get("mode") != mode:
        agent_binding["mode"] = mode
        updates.append("mode")
    if agent_binding.get("autonomyPolicy") != policy:
        agent_binding["autonomyPolicy"] = policy
        updates.append("autonomyPolicy")
    if agent_binding.get("riskControls") != risk_controls:
        agent_binding["riskControls"] = risk_controls
        updates.append("riskControls")

    desired_writeback = {"type": "none"} if mode == "observe" else writeback_for(path, machine, metadata, agent_binding)
    if agent_binding.get("writeBack") != desired_writeback:
        agent_binding["writeBack"] = desired_writeback
        updates.append("writeBack")
    return updates


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
        updates = apply_policy(path, machine, metadata, agent_binding)
        if updates:
            changed += 1
            print(f"{path.relative_to(repo_root)}: {', '.join(updates)}")
            if args.write:
                path.write_text(json.dumps(data, indent=2) + "\n")

    mode = "updated" if args.write else "would update"
    print(f"{mode} {changed} machine files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
