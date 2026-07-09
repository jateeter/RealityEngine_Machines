#!/usr/bin/env python3
"""Build (or verify) the generated corpus index at domains/corpus-index.json.

The index gives engines, Manager, and tooling an O(1) catalog of the corpus
without a recursive scan: one entry per machine file with its relFile (path
relative to machines/), name, domain, and perceptual regions. It lives under
domains/ — not machines/ — so machine loaders never mistake it for a machine.

Usage:
  python3 scripts/build-corpus-index.py --write   # regenerate
  python3 scripts/build-corpus-index.py --check   # fail if stale (CI/validate)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
INDEX = REPO_ROOT / "domains" / "corpus-index.json"


def resolved_domain(metadata: dict[str, Any]) -> str | None:
    tagging = metadata.get("tagging")
    primary = tagging.get("primaryDomain") if isinstance(tagging, dict) else None
    domain = primary or metadata.get("category") or metadata.get("domain")
    return str(domain) if domain else None


def build_index() -> dict[str, Any]:
    entries = []
    for path in sorted(MACHINES.rglob("*.json")):
        rel = path.relative_to(MACHINES).as_posix()
        try:
            root = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARN {rel}: unreadable machine JSON ({exc})", file=sys.stderr)
            continue
        machine = root.get("machine") if isinstance(root, dict) else None
        if not isinstance(machine, dict):
            print(f"WARN {rel}: no machine object", file=sys.stderr)
            continue
        raw_metadata = machine.get("metadata")
        metadata: dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
        raw_mapping = machine.get("perceptualMapping")
        mapping: dict[str, Any] = raw_mapping if isinstance(raw_mapping, dict) else {}
        entry: dict[str, Any] = {
            "relFile": rel,
            "name": machine.get("name", ""),
            "domain": resolved_domain(metadata),
        }
        for key in ("input", "output"):
            region = mapping.get(key)
            if isinstance(region, dict) and "offset" in region:
                entry[f"{key}Region"] = {"offset": region["offset"], "length": region.get("length", 0)}
        entries.append(entry)
    domains: dict[str, int] = {}
    for e in entries:
        domains[str(e["domain"])] = domains.get(str(e["domain"]), 0) + 1
    return {
        "schemaVersion": "1.0.0",
        "purpose": "Generated corpus catalog — regenerate with scripts/build-corpus-index.py --write; do not edit by hand.",
        "machineCount": len(entries),
        "domainCounts": dict(sorted(domains.items())),
        "machines": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate domains/corpus-index.json")
    mode.add_argument("--check", action="store_true", help="fail when the index is stale")
    args = parser.parse_args()

    index = build_index()
    rendered = json.dumps(index, indent=2) + "\n"

    if args.write:
        INDEX.write_text(rendered)
        print(f"corpus-index: wrote {index['machineCount']} machines across {len(index['domainCounts'])} domains")
        return 0

    if not INDEX.exists():
        print("corpus-index: MISSING — run scripts/build-corpus-index.py --write", file=sys.stderr)
        return 1
    if INDEX.read_text() != rendered:
        print("corpus-index: STALE — run scripts/build-corpus-index.py --write", file=sys.stderr)
        return 1
    print(f"corpus-index: OK ({index['machineCount']} machines, {len(index['domainCounts'])} domains)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
