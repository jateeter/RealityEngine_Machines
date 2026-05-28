#!/usr/bin/env python3
"""Backfill canonical RE -> localAIStack dispatch configuration.

Dry-run by default. Pass --write to modify machine JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CANONICAL_ENDPOINT = "http://localhost:4000/graphql"
CANONICAL_TEMPLATE = "triggers/graphql_trigger_template.py"
CANONICAL_DISPATCH = {
    "target": "localAIStack",
    "transport": "graphql",
    "mutation": "updateProcessState",
    "envelopeSchema": "schemas/ai-trigger-envelope.schema.json",
    "schemaRef": "localAIStack/services/api/routers/graphql_endpoint.py",
}


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
        trigger_config = as_object(metadata.get("triggerConfig"))
        if not metadata.get("agentBinding") or not trigger_config:
            continue

        updates = []
        if trigger_config.get("endpoint") != CANONICAL_ENDPOINT:
            trigger_config["endpoint"] = CANONICAL_ENDPOINT
            updates.append("endpoint")
        if trigger_config.get("template") != CANONICAL_TEMPLATE:
            trigger_config["template"] = CANONICAL_TEMPLATE
            updates.append("template")
        if trigger_config.get("dispatch") != CANONICAL_DISPATCH:
            trigger_config["dispatch"] = dict(CANONICAL_DISPATCH)
            updates.append("dispatch")

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
