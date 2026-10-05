#!/usr/bin/env python3
"""A machine must not expect two different outputs from the same input.

    scripts/check-input-sequence-contradictions.py --check     # gate (validate-corpus.sh)
    scripts/check-input-sequence-contradictions.py --report    # every contradiction, known or new

Within one machine, two `inputSequences` whose `events` are identical are the
same input. If they declare different expected outputs
(`metadata.expectedOutputVector` or `metadata.expectedOutputRegion`), one
declaration is unsatisfiable by construction: no engine can present both for
one input. RealityEngine_Machines#165 found one, in
DigitalLogicDlx021030Interconnect, only after it had been investigated as a
three-engine disagreement. All three engines agreed; the corpus disagreed with
itself. Nothing checked for it, so there may be more.

Which way each one is resolved (give the families distinct input bits, or
declare that the machine cannot separate them) is the corpus-design question in
RealityEngine_Machines#164 and is decided per machine by the owner. Until then a
known contradiction is listed in the baseline beside this script, with the
issue that tracks it: visible in --report and named by --check, but not a
failure. A contradiction NOT in the baseline fails --check. A baseline entry
that no longer contradicts also fails, so the list cannot go stale.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
BASELINE = Path(__file__).resolve().with_name("input-sequence-contradictions.baseline.json")


def expected(sequence: dict) -> dict | None:
    meta = sequence.get("metadata") or {}
    out = {k: meta[k] for k in ("expectedOutputVector", "expectedOutputRegion") if k in meta}
    return out or None


def contradictions(root: Path = MACHINES) -> list[dict]:
    """Every group of same-input sequences that expect different outputs."""
    found: list[dict] = []
    for path in sorted(root.rglob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # schema validation reports unreadable files
        machine = doc.get("machine", doc) if isinstance(doc, dict) else None
        if not isinstance(machine, dict):
            continue
        by_input: dict[str, list[dict]] = {}
        for seq in machine.get("inputSequences") or []:
            if not isinstance(seq, dict) or "events" not in seq or expected(seq) is None:
                continue
            by_input.setdefault(json.dumps(seq["events"], separators=(",", ":")), []).append(seq)
        for group in by_input.values():
            outputs = {json.dumps(expected(s), sort_keys=True) for s in group}
            if len(outputs) > 1:
                found.append({
                    "machine": machine.get("name"),
                    "file": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
                    "sequences": sorted(s.get("name", "?") for s in group),
                    "expected": {s.get("name", "?"): expected(s) for s in group},
                })
    return found


def key(entry: dict) -> tuple:
    return (entry["machine"], tuple(entry["sequences"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = ap.parse_args()

    found = contradictions()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))["known"] if BASELINE.is_file() else []
    known = {key(e): e for e in baseline}
    current = {key(e): e for e in found}

    if args.report:
        for e in found:
            tag = f"known ({known[key(e)].get('issue', '?')})" if key(e) in known else "NEW"
            print(f"[{tag}] {e['machine']} ({e['file']})")
            for name, out in e["expected"].items():
                print(f"    {name}: {json.dumps(out, sort_keys=True)}")
        print(f"\n{len(found)} contradiction(s), {sum(1 for k in current if k not in known)} not in the baseline")
        return 0

    new = [current[k] for k in current if k not in known]
    resolved = [known[k] for k in known if k not in current]
    for e in found:
        if key(e) in known:
            print(f"input-sequence-contradictions: known, {known[key(e)].get('issue', '?')}: "
                  f"{e['machine']}: {', '.join(e['sequences'])}")
    for e in new:
        print(f"input-sequence-contradictions: NEW: {e['machine']} ({e['file']}): "
              f"same events, different expected output in {', '.join(e['sequences'])}", file=sys.stderr)
    for e in resolved:
        print(f"input-sequence-contradictions: baseline entry no longer contradicts, remove it: "
              f"{e['machine']}: {', '.join(e['sequences'])}", file=sys.stderr)
    if new or resolved:
        return 1
    print(f"input-sequence-contradictions: OK ({len(found)} known, 0 new)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
