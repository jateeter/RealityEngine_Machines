#!/usr/bin/env python3
"""Integrity check for the ai-governance-regime factory package (intake stage).

Checks, offline and read-only:
  * every file in admission-source-manifest.json exists at its package path with
    the recorded sha256 (the received files are kept byte-for-byte);
  * no package file is missing from the manifest;
  * every JSON file parses;
  * the intake corpora agree on what can be checked mechanically: unique ids,
    the stated summary counts, and corpus-315 holding every corpus-312 id.

It does not validate machines against the canonical machine schema (the
intake corpora are not in it yet; REVIEW_QUEUE.md GOV-R01), start engines or
judge governance semantics. `--write` re-records the manifest's hashes after a
deliberate change to a package file.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
MANIFEST = PKG / "admission-source-manifest.json"
# Files this package authors about itself; everything else is a received input.
AUTHORED = {
    "README.md", "PACKAGE_STATUS.md", "REVIEW_QUEUE.md", "scope-decisions.json",
    "machine-import-manifest.json", "admission-source-manifest.json",
    "tools/verify_package.py", "tools/build_machines.py", "tools/verify_machines.py",
    "tools/validate_schema.mjs", "tools/live_probe.py", "semantic-amendments.json", "CONNECTED_WORKFLOW.md",
    "governance-sources.json", "agentic-workflow-contract.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_files():
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts:
            yield p.relative_to(PKG).as_posix()


def check_corpora(errors):
    a = json.loads((PKG / "intake/corpus-312.json").read_text())
    b = json.loads((PKG / "intake/corpus-315.json").read_text())
    ids_a = [m["machineId"] for m in a["machines"]]
    ids_b = [m["machineId"] for m in b["machines"]]
    for name, ids in (("corpus-312", ids_a), ("corpus-315", ids_b)):
        if len(ids) != len(set(ids)):
            errors.append(f"{name}: duplicate machineId")
    if len(ids_a) != a["corpusMetadata"]["totalMachines"]:
        errors.append("corpus-312: machine count differs from corpusMetadata.totalMachines")
    if len(ids_b) != b["summaryCounts"]["totalMachines"]:
        errors.append("corpus-315: machine count differs from summaryCounts.totalMachines")
    missing = set(ids_a) - set(ids_b)
    if missing:
        errors.append(f"corpus-315 lacks {len(missing)} corpus-312 ids")
    return len(ids_a), len(ids_b), sorted(set(ids_b) - set(ids_a))


def main():
    ap = argparse.ArgumentParser(description="Integrity check for the ai-governance-regime factory package.")
    ap.add_argument("--write", action="store_true", help="re-record received-file hashes")
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    errors = []

    if args.write:
        for entry in manifest["files"]:
            entry["sha256"] = sha256(PKG / entry["path"])
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")

    listed = {e["path"] for e in manifest["files"]}
    for entry in manifest["files"]:
        p = PKG / entry["path"]
        if not p.is_file():
            errors.append(f"missing: {entry['path']}")
        elif sha256(p) != entry["sha256"]:
            errors.append(f"changed: {entry['path']} (received bytes must stay as received)")
    for rel in package_files():
        if rel not in listed and rel not in AUTHORED and not rel.startswith(("machines/", "agent-candidates/", "acceptance/")):
            errors.append(f"unlisted: {rel} (add it to admission-source-manifest.json)")
        if rel.endswith(".json"):
            try:
                json.loads((PKG / rel).read_text())
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON: {rel}: {exc}")

    n312, n315, added = check_corpora(errors)
    print(f"received files: {len(listed)}; corpus-312: {n312} machines; "
          f"corpus-315: {n315} machines (adds {', '.join(added)})")
    for e in errors:
        print(f"FAIL: {e}")
    print("PASS" if not errors else f"{len(errors)} failure(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
