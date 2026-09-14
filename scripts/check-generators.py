#!/usr/bin/env python3
"""check-generators — the inventory gate for corpus generators and verifiers.

WHY THIS EXISTS
---------------
This repo carries ~20 scripts that either generate a corpus artifact or verify
one. Nothing enumerated them, so the only record of "which processes must run
before the corpus can be trusted" was the call list inside validate-corpus.sh —
a list that is correct only for as long as someone remembers to add to it.

That assumption has already failed twice in ways that cost real time:

  * `contracts.json` went 9 weeks stale because the generator that writes it was
    superseded and nothing asserted that the artifact still matched its corpus
    (RealityEngine_CI#327, RealityEngine_Machines#115).
  * `extract-qudt-subset.py --check` and `ucum.py` expose verification modes that
    no aggregator invokes, so they have never once run in a gate
    (RealityEngine_CI#352 found the same shape in four CI generators).

Both are the same defect: a process that exists but is reachable from nothing.
Absence is invisible — a generator nobody calls looks exactly like a generator
with nothing to report. This gate makes absence loud, which matters most as the
corpus grows: a new domain brings new artifacts, and the failure mode is not a
broken check but a check that was never wired up.

WHAT IT ASSERTS
---------------
  1. Every script on disk that exposes a --check or --write mode appears in
     generators.manifest.json. A new generator cannot be added silently.
  2. Every manifest entry names a script that exists. A deleted generator cannot
     linger as a phantom obligation.
  3. Every manifest entry declaring `invoked_by` is genuinely referenced by that
     file. A generator cannot claim coverage it does not have.
  4. Every entry declaring a --check mode is invoked by something. An unreachable
     verifier is reported rather than assumed healthy.
  5. Every entry declares its corpus scope, so "does this cover the full 1328
     machines or the 20-machine regression subset" is answerable without reading
     the script.

Usage:
    scripts/check-generators.py --check    # exit 1 on any drift (CI gate)
    scripts/check-generators.py --write    # reconcile the manifest from disk
    scripts/check-generators.py --summary  # human-readable inventory table
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
MANIFEST = REPO / "generators.manifest.json"

# A script earns a manifest entry when it can produce or verify an artifact.
# --check and --write are the repo's established verbs for exactly that; a script
# with neither is a one-shot tool (migrations, seeders) and is out of scope.
GENERATOR_MODES = ("--check", "--write")

# Migrations and one-shot conversions are deliberately excluded: they run once
# against a corpus state that no longer exists, so holding them to "is this
# artifact current" would assert something meaningless.
EXCLUDED = {
    "migrate-corpus-to-domains.py",
    "remap-cross-domain-output-lanes.py",
    "rename-corpus-event-keys.py",
    "check-generators.py",
    # Shared library, not a generator: it produces no artifact and has no CLI.
    # Detection is a text scan for mode strings, and its docstring explains why
    # the stamp must not be time-derived -- "would break every --check drift
    # gate" -- which the scan reads as offering --check. Excluded for what it is
    # rather than by loosening the scan, which would stop catching real cases.
    "asset_provenance.py",
    # Same shape: the fingerprint definition both repos import.
    "ces_corpus_fingerprint.py",
}


def discover() -> dict[str, list[str]]:
    """Scripts on disk that expose a generator mode, with the modes they accept."""
    found: dict[str, list[str]] = {}
    for path in sorted(SCRIPTS.iterdir()):
        if not path.is_file() or path.name in EXCLUDED:
            continue
        if path.suffix not in (".py", ".sh", ".mjs"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        modes = sorted({m for m in GENERATOR_MODES if m in text})
        if modes:
            found[path.name] = modes

    # npm aliases named *:check / *:write declare an intent to verify or
    # generate even when the script spells its flags differently. ucum.py is the
    # standing example: `ucum:check` verifies the corpus, but the script takes
    # --scan, so a flag-only scan would never see it.
    pkg = REPO / "package.json"
    if pkg.is_file():
        try:
            scripts_block = json.loads(pkg.read_text()).get("scripts", {})
        except (OSError, ValueError):
            scripts_block = {}
        for alias, cmd in scripts_block.items():
            if not alias.endswith((":check", ":write")):
                continue
            for candidate in SCRIPTS.iterdir():
                if candidate.name in EXCLUDED or not candidate.is_file():
                    continue
                if candidate.name in cmd:
                    found.setdefault(candidate.name, []).append(f"npm:{alias}")
                    found[candidate.name] = sorted(set(found[candidate.name]))
    return found


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {"version": 1, "generators": []}
    with MANIFEST.open() as fh:
        return json.load(fh)


# A gate RUNS a generator as part of a verification lane. package.json only
# DEFINES an npm alias — `npm run qudt:check` existing is not the same as anything
# calling it, and conflating the two is how extract-qudt-subset.py came to offer a
# --check mode that has never executed in any lane. The distinction is the whole
# point of this file, so it is structural rather than a comment.
GATE_FILES = ("validate-corpus.sh", "validate-guardrails.sh", "Makefile")


def invocation_sites(script_name: str) -> tuple[list[str], list[str]]:
    """(gated_by, defined_in) for this script.

    Verifies the manifest's `invoked_by` claim against reality rather than
    trusting it: a stale invoked_by is the same lie as a missing entry.
    """
    gated: list[str] = []
    defined: list[str] = []
    candidates = list(SCRIPTS.glob("*.sh")) + list(REPO.glob("Makefile")) + [REPO / "package.json"]
    for candidate in candidates:
        if not candidate.is_file() or candidate.name == script_name:
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if script_name not in text:
            continue
        rel = str(candidate.relative_to(REPO))
        (gated if candidate.name in GATE_FILES else defined).append(rel)
    return gated, defined


def check() -> int:
    manifest = load_manifest()
    entries = {g["script"]: g for g in manifest.get("generators", [])}
    on_disk = discover()
    failures: list[str] = []

    for name, modes in on_disk.items():
        if name not in entries:
            failures.append(
                f"{name} exposes {', '.join(modes)} but is absent from generators.manifest.json "
                f"— add it, or add it to EXCLUDED with a reason"
            )

    for name, entry in entries.items():
        if not (SCRIPTS / name).exists():
            failures.append(f"{name} is in the manifest but not on disk")
            continue
        if not entry.get("corpus"):
            failures.append(f"{name} declares no corpus scope (full | regression | none)")
        claimed = entry.get("invoked_by") or []
        gated, defined = invocation_sites(name)
        for site in claimed:
            if site not in gated + defined:
                failures.append(f"{name} claims invoked_by={site}, which does not reference it")
        # A gate root is the entry point; requiring it to be invoked by another
        # gate is circular. CI invokes these directly.
        is_gate_root = name in GATE_FILES
        if ("--check" in (entry.get("modes") or []) and not gated
                and not is_gate_root and not entry.get("ungated_reason")):
            where = f" (only defined in {', '.join(defined)})" if defined else ""
            failures.append(
                f"{name} offers --check but no gate invokes it{where} — an unreachable "
                f"verifier reports healthy for the same reason a passing one does. "
                f"Wire it into a gate, or set ungated_reason to record the decision"
            )

    if failures:
        print(f"check-generators: {len(failures)} finding(s)\n", file=sys.stderr)
        for f in failures:
            print(f"  FAIL  {f}", file=sys.stderr)
        return 1

    print(f"check-generators: {len(entries)} generator(s) inventoried, all reachable and scoped")
    return 0


def write() -> int:
    """Reconcile the manifest with disk, preserving human-authored fields."""
    manifest = load_manifest()
    entries = {g["script"]: g for g in manifest.get("generators", [])}
    on_disk = discover()

    for name, modes in on_disk.items():
        entry = entries.setdefault(name, {"script": name})
        entry["modes"] = modes
        entry.setdefault("artifact", None)
        entry.setdefault("corpus", None)
        entry.setdefault("cadence", "per-pr")
        gated, defined = invocation_sites(name)
        entry["invoked_by"] = gated + defined
        entry["gated_by"] = gated

    for name in list(entries):
        if name not in on_disk:
            del entries[name]

    manifest["version"] = manifest.get("version", 1)
    manifest["generators"] = [entries[k] for k in sorted(entries)]
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"check-generators: wrote {MANIFEST.relative_to(REPO)} ({len(entries)} generators)")
    return 0


def summary() -> int:
    manifest = load_manifest()
    rows = manifest.get("generators", [])
    print(f"{'script':<38} {'corpus':<11} {'cadence':<10} invoked_by")
    print("-" * 100)
    for g in rows:
        inv = ", ".join(g.get("invoked_by") or []) or "(nothing)"
        print(f"{g['script']:<38} {str(g.get('corpus')):<11} {str(g.get('cadence')):<10} {inv}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 on inventory drift")
    ap.add_argument("--write", action="store_true", help="reconcile manifest from disk")
    ap.add_argument("--summary", action="store_true", help="print the inventory")
    args = ap.parse_args()
    if args.write:
        return write()
    if args.summary:
        return summary()
    return check()


if __name__ == "__main__":
    sys.exit(main())
