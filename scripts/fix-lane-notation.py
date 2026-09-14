#!/usr/bin/env python3
"""Rewrite lane prose from half-open values to inclusive, matching its brackets.

The corpus stores regions as unambiguous `{offset, length}`. Its prose writes
them as `[a:b]` where `b = offset + length` — half-open values inside closed
brackets. Read the way square brackets are normally read, every lane reference
names one cell more than it owns: `[16920:16922]` looks like three cells and is
two.

Nothing parses this text today; the risk is downstream. It lives in
`upstreamOutputRegion`, `downstreamPattern`, `downstreamMachine` and
`upstreamMachines` — the fields describing the connectivity network. Adjacent
lanes are the norm (the ring latch is 16920–16921 against 16922–16923), so
anything deriving edges by matching these strings would overrun into the
neighbouring lane and manufacture an edge between exactly the machines that must
not be connected.

**Only references corroborated by a declared region are rewritten.** For each
machine the script collects every `{offset, length}` it declares — perceptual
mapping, lanes, trigger rules, anything — and rewrites `[a:b]` only where some
declared region has `offset == a` and `offset + length == b`. A bracket pair
that is not a lane, or whose span disagrees with every declared region, is
reported and left alone: decrementing a number this script does not understand
would be a silent corpus defect, which is worse than the ambiguity being fixed.

Usage:
  scripts/fix-lane-notation.py            # dry run: per-file counts and skips
  scripts/fix-lane-notation.py --write
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
LANE = re.compile(r"\[(\d{2,5}):(\d{2,5})\]")


def declared_regions(node, out: set[tuple[int, int]]) -> None:
    """Every (offset, offset+length) pair the machine declares."""
    if isinstance(node, dict):
        o, l = node.get("offset"), node.get("length")
        if isinstance(o, int) and isinstance(l, int):
            out.add((o, o + l))
        for v in node.values():
            declared_regions(v, out)
    elif isinstance(node, list):
        for v in node:
            declared_regions(v, out)


def rewrite(text: str, spans: set[tuple[int, int]], stats: Counter,
            skipped: list[str], where: str) -> str:
    def sub(m: re.Match) -> str:
        a, b = int(m.group(1)), int(m.group(2))
        if (a, b) in spans:
            stats["rewritten"] += 1
            return f"[{a}:{b - 1}]"
        if b - a == 1:
            stats["already-inclusive"] += 1   # single cell, nothing to do
            return m.group(0)
        stats["skipped"] += 1
        skipped.append(f"{where}: [{a}:{b}] matches no declared region")
        return m.group(0)
    return LANE.sub(sub, text)


def walk(node, spans, stats, skipped, path=""):
    if isinstance(node, dict):
        return {k: walk(v, spans, stats, skipped, f"{path}.{k}") for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v, spans, stats, skipped, f"{path}[]") for v in node]
    if isinstance(node, str) and LANE.search(node):
        return rewrite(node, spans, stats, skipped, path)
    return node


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true")
    p.add_argument("--root", type=Path, default=REPO_ROOT / "machines")
    args = p.parse_args()

    # Corroborate against every region declared ANYWHERE in the corpus, not just
    # the machine holding the text. `upstreamMachines`, `downstreamPattern` and
    # `downstreamMachine` reference the *partner's* lanes by design -- that is
    # what makes them the connectivity network -- so same-machine corroboration
    # declined 125 of them, which are exactly the references most worth fixing.
    corpus_spans: set[tuple[int, int]] = set()
    docs: dict[Path, Any] = {}
    for f in sorted(args.root.rglob("*.json")):
        raw = f.read_text(encoding="utf-8")
        doc = json.loads(raw)
        docs[f] = (doc, LANE.search(raw) is not None)
        declared_regions(doc, corpus_spans)

    stats, skipped, touched = Counter(), [], 0
    for f, (doc, has_lane) in docs.items():
        if not has_lane:
            continue
        spans = corpus_spans
        before = json.dumps(doc, sort_keys=True)
        fixed = walk(doc, spans, stats, skipped, f.name)
        if json.dumps(fixed, sort_keys=True) != before:
            touched += 1
            if args.write:
                # Preserve the file's existing 2-space style.
                f.write_text(json.dumps(fixed, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")

    print(f"files touched      {touched}")
    print(f"refs rewritten     {stats['rewritten']}")
    print(f"single-cell (kept) {stats['already-inclusive']}")
    print(f"refs skipped       {stats['skipped']}")
    for s in skipped[:15]:
        print(f"   {s}")
    if len(skipped) > 15:
        print(f"   ... and {len(skipped) - 15} more")
    if not args.write:
        print("\n(dry run — re-run with --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
