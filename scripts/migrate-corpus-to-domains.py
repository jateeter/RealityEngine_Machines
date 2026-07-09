#!/usr/bin/env python3
"""Migrate flat machine corpus files into machines/domains/<domain>/.

Each machine's domain is resolved the same way scripts/audit-corpus.py does:
metadata.tagging.primaryDomain, then metadata.category, then metadata.domain.
The resolved domain must exist in domains/domain-manifest.json — the script
fails loudly on any unmappable file and moves nothing.

Files are moved with `git mv` so history follows the file. Idempotent: files
already under machines/domains/ are left alone.

Usage:
  python3 scripts/migrate-corpus-to-domains.py --dry-run   # report the plan
  python3 scripts/migrate-corpus-to-domains.py             # perform the move
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
MANIFEST = REPO_ROOT / "domains" / "domain-manifest.json"


def resolve_domain(machine_file: Path) -> str | None:
    try:
        root = json.loads(machine_file.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    machine = root.get("machine") if isinstance(root, dict) else None
    metadata = machine.get("metadata") if isinstance(machine, dict) else None
    if not isinstance(metadata, dict):
        return None
    tagging = metadata.get("tagging")
    primary = tagging.get("primaryDomain") if isinstance(tagging, dict) else None
    domain = primary or metadata.get("category") or metadata.get("domain")
    return str(domain) if domain else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the plan without moving files")
    args = parser.parse_args()

    manifest_domains = set(json.loads(MANIFEST.read_text())["domains"])
    flat_files = sorted(p for p in MACHINES.glob("*.json") if p.is_file())
    if not flat_files:
        print("No flat machine files at machines/ root — nothing to migrate.")
        return 0

    plan: list[tuple[Path, Path]] = []
    errors: list[str] = []
    for path in flat_files:
        domain = resolve_domain(path)
        if domain is None or domain not in manifest_domains:
            errors.append(f"{path.name}: resolved domain {domain!r} is not in domain-manifest.json")
            continue
        target = MACHINES / "domains" / domain / path.name
        if target.exists():
            errors.append(f"{path.name}: target already exists at {target.relative_to(REPO_ROOT)}")
            continue
        plan.append((path, target))

    if errors:
        print(f"ABORT — {len(errors)} unmappable file(s); nothing moved:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    by_domain: dict[str, int] = {}
    for _, target in plan:
        by_domain[target.parent.name] = by_domain.get(target.parent.name, 0) + 1
    for domain in sorted(by_domain):
        print(f"  {by_domain[domain]:5d} -> machines/domains/{domain}/")
    print(f"{'Would move' if args.dry_run else 'Moving'} {len(plan)} files.")

    if args.dry_run:
        return 0

    for source, target in plan:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "mv", str(source.relative_to(REPO_ROOT)), str(target.relative_to(REPO_ROOT))],
            check=True,
            cwd=REPO_ROOT,
        )
    print(f"Moved {len(plan)} files. machines/ root is now domain-organized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
