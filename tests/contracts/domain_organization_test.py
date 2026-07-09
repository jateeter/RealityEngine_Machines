#!/usr/bin/env python3
"""Contract checks for the domain-organized corpus layout.

The corpus lives entirely under machines/domains/<domain>/ (plus the optional
machines/core/ area for shared machines). Every machine's resolved domain —
metadata.tagging.primaryDomain, then metadata.category, then metadata.domain,
the same resolution scripts/audit-corpus.py uses — must match the domain
directory that contains it, and every domain directory must be registered in
domains/domain-manifest.json.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHINES = REPO_ROOT / "machines"
MANIFEST = REPO_ROOT / "domains" / "domain-manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def resolved_domain(root: dict[str, Any]) -> str | None:
    machine = root.get("machine")
    metadata = machine.get("metadata") if isinstance(machine, dict) else None
    if not isinstance(metadata, dict):
        return None
    tagging = metadata.get("tagging")
    primary = tagging.get("primaryDomain") if isinstance(tagging, dict) else None
    domain = primary or metadata.get("category") or metadata.get("domain")
    return str(domain) if domain else None


class DomainOrganizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest_domains = set(load_json(MANIFEST)["domains"])

    def test_no_machines_at_corpus_root(self) -> None:
        flat = sorted(p.name for p in MACHINES.glob("*.json"))
        self.assertEqual(
            flat, [],
            f"machine files must live under machines/domains/<domain>/ (or machines/core/), found at root: {flat[:5]}",
        )

    def test_every_domain_directory_is_manifested(self) -> None:
        domain_dirs = sorted(p.name for p in (MACHINES / "domains").iterdir() if p.is_dir())
        unmanifested = [d for d in domain_dirs if d not in self.manifest_domains]
        self.assertEqual(unmanifested, [], f"domain directories missing from domain-manifest.json: {unmanifested}")

    def test_machine_domain_matches_parent_directory(self) -> None:
        mismatches: list[str] = []
        for path in sorted((MACHINES / "domains").rglob("*.json")):
            domain_dir = path.relative_to(MACHINES / "domains").parts[0]
            domain = resolved_domain(load_json(path))
            if domain != domain_dir:
                mismatches.append(f"{path.relative_to(MACHINES)}: resolved domain {domain!r} != directory {domain_dir!r}")
        self.assertEqual(mismatches, [], "domain membership drift:\n" + "\n".join(mismatches[:10]))

    def test_manifest_counts_match_directory_counts(self) -> None:
        manifest = load_json(MANIFEST)["domains"]
        drift: list[str] = []
        for domain, entry in sorted(manifest.items()):
            expected = entry.get("currentMachineCount")
            actual = len(list((MACHINES / "domains" / domain).rglob("*.json")))
            if expected != actual:
                drift.append(f"{domain}: manifest currentMachineCount={expected} but directory has {actual}")
        self.assertEqual(drift, [], "manifest count drift:\n" + "\n".join(drift))


if __name__ == "__main__":
    unittest.main()
