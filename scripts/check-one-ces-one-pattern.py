#!/usr/bin/env python3
"""Each CES in a machine reflects exactly one regular expression, its own.

    scripts/check-one-ces-one-pattern.py --check     # gate (validate-corpus.sh)
    scripts/check-one-ces-one-pattern.py --report    # every violation found

Owner rule (2026-10-05, without exception): a CES is one regular expression over
Reality Events, and no two CESs of one machine may share one. Two CESs with the
same pattern are competing regular expressions: the machine declares two
outputs for what is one match, one of them is unreachable, and every engine
agrees on whichever wins, so the corpus defect reads as engine behaviour
(RealityEngine_Machines#165, which found seven). The fix is always to give the
competitor its own, distinct pattern. It is never a merge or an exception, and
there is no baseline.

Two checks, both failures:
  1. no two CESs of a machine share a pattern. A CES's pattern is its Reality
     Events in declared order: each event's element values and thresholds, its
     match algorithm, whether it is initial, and its transitions as positions,
     so that ids do not count;
  2. no two inputSequences of a machine present the same events while expecting
     different outputs (metadata.expectedOutputVector or expectedOutputRegion).
     This is the same defect seen from the input side, and the symptom that
     surfaced #165.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"


def ces_pattern(ces: dict) -> str:
    events = [e for e in ces.get("events") or [] if isinstance(e, dict)]
    position = {e.get("id"): i for i, e in enumerate(events)}
    return json.dumps([
        {"elements": [(x.get("value"), x.get("threshold")) for x in e.get("elements") or []],
         "matchAlgorithm": e.get("matchAlgorithm"),
         "isInitial": bool(e.get("isInitial")),
         "next": sorted(position.get(n, n) for n in e.get("nextEventIds") or [])}
        for e in events], sort_keys=True)


def expected(sequence: dict) -> dict | None:
    meta = sequence.get("metadata") or {}
    out = {k: meta[k] for k in ("expectedOutputVector", "expectedOutputRegion") if k in meta}
    return out or None


def violations(root: Path = MACHINES) -> list[str]:
    found: list[str] = []
    for path in sorted(root.rglob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # schema validation reports unreadable files
        machine = doc.get("machine", doc) if isinstance(doc, dict) else None
        if not isinstance(machine, dict):
            continue
        rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        name = machine.get("name", "?")

        by_pattern: dict[str, list[str]] = {}
        for ces in machine.get("sequences") or []:
            if isinstance(ces, dict):
                by_pattern.setdefault(ces_pattern(ces), []).append(str(ces.get("id", "?")))
        for ids in by_pattern.values():
            if len(ids) > 1:
                found.append(f"{name} ({rel}): CESs share one pattern: {', '.join(sorted(ids))}")

        by_input: dict[str, list[dict]] = {}
        for seq in machine.get("inputSequences") or []:
            if isinstance(seq, dict) and "events" in seq and expected(seq) is not None:
                by_input.setdefault(json.dumps(seq["events"], separators=(",", ":")), []).append(seq)
        for group in by_input.values():
            if len({json.dumps(expected(s), sort_keys=True) for s in group}) > 1:
                found.append(f"{name} ({rel}): inputSequences present the same events but expect "
                             f"different outputs: {', '.join(sorted(str(s.get('name', '?')) for s in group))}")
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = ap.parse_args()
    found = violations()
    for line in found:
        print(f"one-ces-one-pattern: {line}", file=sys.stderr if args.check else sys.stdout)
    if found:
        print(f"one-ces-one-pattern: {len(found)} violation(s)", file=sys.stderr if args.check else sys.stdout)
        return 1 if args.check else 0
    print("one-ces-one-pattern: OK (every CES holds its own pattern; no input expects two outputs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
