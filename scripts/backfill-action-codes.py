#!/usr/bin/env python3
"""Normalize free-text output `action` strings to controlled action codes.

Reads curated mapping files from semantics/action-mapping/<domain>.json
(exact original string -> controlled code). For every matching output vector,
the original prose is preserved in `actionNarrative` and `action` becomes the
controlled code declared in semantics/ontology/re-core.ttl.

Default mode is a dry-run plan; pass --write to rewrite machine JSON in place
(json.dumps indent=2, matching the other backfill scripts). Actions that are
already valid controlled codes are left untouched. Actions with no mapping are
reported (and fail the run with --strict).

Usage:
  python3 scripts/backfill-action-codes.py --domain health-personal
  python3 scripts/backfill-action-codes.py --domain health-personal --write
  python3 scripts/backfill-action-codes.py --all --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MACHINES_ROOT = REPO_ROOT / "machines"
MAPPING_ROOT = REPO_ROOT / "semantics" / "action-mapping"
ONTOLOGY_PATH = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"

ACTION_CODE_PATTERN = re.compile(r're:actionCode "([^"]+)"')


def known_codes() -> set[str]:
    return set(ACTION_CODE_PATTERN.findall(ONTOLOGY_PATH.read_text()))


def domain_for(path: Path) -> str:
    rel = path.resolve().relative_to(MACHINES_ROOT.resolve())
    if len(rel.parts) >= 3 and rel.parts[0] == "domains":
        return rel.parts[1]
    return "core"


def load_mapping(domain: str) -> dict[str, str]:
    mapping_path = MAPPING_ROOT / f"{domain}.json"
    if not mapping_path.exists():
        return {}
    with mapping_path.open() as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", help="one domain under machines/domains/")
    parser.add_argument("--all", action="store_true", help="whole corpus")
    parser.add_argument("--write", action="store_true", help="rewrite machine JSON")
    parser.add_argument("--strict", action="store_true",
                        help="fail if any action string has no code or mapping")
    args = parser.parse_args()
    if not (args.domain or args.all):
        parser.error("choose --domain or --all")

    codes = known_codes()
    if args.domain:
        paths = sorted((MACHINES_ROOT / "domains" / args.domain).rglob("*.json"))
    else:
        paths = sorted(MACHINES_ROOT.rglob("*.json"))

    mappings: dict[str, dict[str, str]] = {}
    changed_files = 0
    changed_actions = 0
    unmapped: dict[str, int] = {}
    for path in paths:
        with path.open() as handle:
            doc = json.load(handle)
        machine = doc.get("machine")
        if not machine:
            continue
        domain = domain_for(path)
        if domain not in mappings:
            mappings[domain] = load_mapping(domain)
        mapping = mappings[domain]
        dirty = False
        for sequence in machine.get("sequences", []):
            for vector in (sequence.get("events") or []):
                for output in (vector.get("outputEvents") or []):
                    metadata = output.get("metadata")
                    if not metadata or "action" not in metadata:
                        continue
                    action = metadata["action"]
                    if action in codes:
                        continue
                    code = mapping.get(action)
                    if code is None:
                        unmapped[action] = unmapped.get(action, 0) + 1
                        continue
                    metadata["actionNarrative"] = action
                    metadata["action"] = code
                    dirty = True
                    changed_actions += 1
        if dirty:
            changed_files += 1
            rel = path.relative_to(REPO_ROOT)
            if args.write:
                path.write_text(json.dumps(doc, indent=2) + "\n")
                print(f"rewrote {rel}")
            else:
                print(f"would rewrite {rel}")

    print(f"backfill-action-codes: {changed_actions} action(s) in {changed_files} "
          f"file(s){'' if args.write else ' (dry run)'}; "
          f"{len(unmapped)} distinct unmapped string(s)")
    if unmapped:
        for action, count in sorted(unmapped.items(), key=lambda kv: -kv[1])[:20]:
            print(f"UNMAPPED x{count}: {action[:120]}", file=sys.stderr)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
