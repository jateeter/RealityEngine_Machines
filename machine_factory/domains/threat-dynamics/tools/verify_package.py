#!/usr/bin/env python3
"""Integrity check for the threat-dynamics factory package.

Checks, offline and read-only:
  * every received file in admission-source-manifest.json exists with its sha256
    (none today: both sources are recorded by sha256 only);
  * no package file is unaccounted for;
  * every JSON file parses;
  * scope decisions and amendments have unique ids, and every amendment a CES
    cites exists;
  * the sources recorded by hash only are not committed.
"""
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
AUTHORED = {
    "README.md", "SPECIFICATION.md", "PACKAGE_STATUS.md", "REVIEW_QUEUE.md", "scope-decisions.json",
    "semantic-amendments.json", "admission-source-manifest.json", "threat-sources.json",
    "tools/build_machines.py", "tools/verify_machines.py", "tools/verify_package.py", "tools/validate_schema.mjs",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    errors = []
    manifest = json.loads((PKG / "admission-source-manifest.json").read_text())
    listed = {e["path"] for e in manifest["files"]}
    for entry in manifest["files"]:
        p = PKG / entry["path"]
        if not p.is_file():
            errors.append(f"missing: {entry['path']}")
        elif sha256(p) != entry["sha256"]:
            errors.append(f"changed: {entry['path']}")
    hashed_only = {manifest[k]["sha256"] for k in ("specification", "designIntent")}
    files = [p for p in sorted(PKG.rglob("*")) if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts]
    for p in files:
        rel = p.relative_to(PKG).as_posix()
        if rel not in listed and rel not in AUTHORED and not rel.startswith("machines/"):
            errors.append(f"unlisted: {rel}")
        if sha256(p) in hashed_only:
            errors.append(f"{rel}: a source recorded by sha256 only is committed")
        if rel.endswith(".json"):
            try:
                json.loads(p.read_text())
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON: {rel}: {exc}")
    sd = [d["id"] for d in json.loads((PKG / "scope-decisions.json").read_text())["decisions"]]
    sa = [a["id"] for a in json.loads((PKG / "semantic-amendments.json").read_text())["amendments"]]
    for name, ids in (("scope decision", sd), ("amendment", sa)):
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate {name} id")
    cited = {a for p in (PKG / "machines").glob("*.json")
             for s in json.loads(p.read_text())["machine"]["sequences"]
             for a in s["metadata"].get("semanticAmendments", [])}
    errors += [f"cited amendment {a} is not in semantic-amendments.json" for a in sorted(cited - set(sa))]
    print(f"files: {len(files)}; received: {len(listed)}; hashed only: {len(hashed_only)}; "
          f"decisions: {len(sd)}; amendments: {len(sa)} ({len(cited)} cited by CESs)")
    for e in errors:
        print(f"FAIL: {e}")
    print("PASS" if not errors else f"{len(errors)} failure(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
