#!/usr/bin/env python3
"""Rewrite the corpus schema keys for the Reality Event rename.

RealityEngine_CI#220 layer 1b. The theory has no vectors — only Reality Events —
and the corpus is the last place the old word survives as a contract:

    vectors        -> events
    outputVectors  -> outputEvents
    nextVectorIds  -> nextEventIds

## Why this is a script and not a sweep

Two reasons, and both are about what a text substitution would also hit.

`s/vectors/events/` matches prose. Corpus machines carry `description` fields
written in English, machine names, and sequence names, and a fair number of them
say "vectors" in a sentence. A regex has no way to tell a key from a paragraph,
and the damage would be silent — a corpus that reads slightly wrong for ever,
with every schema check still passing.

It also matches keys that are not ours. Nothing else in the corpus is spelled
this way today, but "today" is the whole problem: a sweep that is correct once
is not a tool, and this rewrite has to be reproducible if it is re-run against a
corpus that has moved.

So the rename is **path-aware**. Every occurrence in the corpus sits at exactly
one of four positions:

    /machine/inputSequences[]/events
    /machine/sequences[]/events
    /machine/sequences[]/events[]/outputEvents
    /machine/sequences[]/events[]/nextEventIds

Anything found outside those is a shape this script has not been told about, and
it **refuses the whole run** rather than guessing. That refusal is the point: it
is the check that the corpus has not grown a fifth position since the paths were
measured, and it fails before writing rather than after.

## Usage

    scripts/rename-corpus-event-keys.py --check     # report, write nothing
    scripts/rename-corpus-event-keys.py --write

Idempotent: a corpus already carrying the new spelling is reported as converted
and left alone, so a partial run can be finished by running it again.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

RENAME = {
    "vectors": "events",
    "outputVectors": "outputEvents",
    "nextVectorIds": "nextEventIds",
}

# The only positions these keys may occupy, in canonical spelling. A machine is
# a `{"machine": {...}}` wrapper, so paths begin below that.
ALLOWED_PATHS = {
    "/machine/inputSequences[]/events",
    "/machine/sequences[]/events",
    "/machine/sequences[]/events[]/outputEvents",
    "/machine/sequences[]/events[]/nextEventIds",
}


def canonical_path(path: str) -> str:
    """A path with both spellings collapsed, so pre- and post-run paths compare."""
    for legacy, canon in RENAME.items():
        path = path.replace(f"/{legacy}", f"/{canon}")
    return path


def find_occurrences(node: Any, path: str = "") -> list[tuple[str, str]]:
    """Every (path, key) where a renameable key appears, at any depth."""
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}/{key}"
            if key in RENAME or key in RENAME.values():
                found.append((canonical_path(here), key))
            found.extend(find_occurrences(value, here))
    elif isinstance(node, list):
        for item in node:
            found.extend(find_occurrences(item, f"{path}[]"))
    return found


def rewrite(node: Any) -> Any:
    """Rename in place, preserving key order — the diff should read as a rename."""
    if isinstance(node, dict):
        return {RENAME.get(k, k): rewrite(v) for k, v in node.items()}
    if isinstance(node, list):
        return [rewrite(v) for v in node]
    return node


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent / "machines")
    parser.add_argument("--write", action="store_true", help="write the rewrite; otherwise report only")
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"no corpus at {args.root}", file=sys.stderr)
        return 2

    files = sorted(args.root.rglob("*.json"))
    unexpected: list[str] = []
    legacy_total = 0
    per_path: dict[str, int] = {}
    to_write: list[tuple[Path, Any, bool]] = []
    unreadable: list[str] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
            doc = json.loads(text)
        except (OSError, ValueError) as exc:
            # Reported, never skipped silently: a file this cannot parse is a
            # file the rewrite would leave on the old spelling.
            unreadable.append(f"{path.relative_to(args.root)}: {exc}")
            continue

        occurrences = find_occurrences(doc)
        if not occurrences:
            continue

        for where, key in occurrences:
            if where not in ALLOWED_PATHS:
                unexpected.append(f"{path.relative_to(args.root)}  {where}  ({key})")
            else:
                per_path[where] = per_path.get(where, 0) + 1
                if key in RENAME:
                    legacy_total += 1

        if any(k in RENAME for _, k in occurrences):
            # A file holding a literal non-ASCII character was written with
            # `ensure_ascii=False`; one holding none was written with the
            # default. Round-trip it the way it came in.
            ascii_only = text.isascii()
            to_write.append((path, rewrite(doc), ascii_only))

    print(f"files scanned          {len(files)}")
    print(f"files needing rewrite  {len(to_write)}")
    print(f"legacy occurrences     {legacy_total}")
    for where in sorted(per_path):
        print(f"  {where:52} {per_path[where]:6}")

    if unreadable:
        print(f"\nUNREADABLE ({len(unreadable)}):", file=sys.stderr)
        for item in unreadable[:20]:
            print(f"  {item}", file=sys.stderr)
        return 1

    if unexpected:
        # Refuse the whole run. A key at an unknown position means the corpus
        # has a shape this script was not told about, and renaming the ones it
        # does recognise would leave the corpus half-converted with no record
        # of which half.
        print(f"\nREFUSING: {len(unexpected)} occurrence(s) outside the known paths.", file=sys.stderr)
        print("The corpus has a shape this script does not know about. Nothing was", file=sys.stderr)
        print("written. Add the path to ALLOWED_PATHS once you have decided it is", file=sys.stderr)
        print("correct, rather than widening the match.\n", file=sys.stderr)
        for item in unexpected[:20]:
            print(f"  {item}", file=sys.stderr)
        if len(unexpected) > 20:
            print(f"  ... and {len(unexpected) - 20} more", file=sys.stderr)
        return 1

    if not args.write:
        print("\n--check: nothing written. Re-run with --write to apply.")
        return 0

    for path, doc, ascii_only in to_write:
        # Preserve each file's own escaping. The corpus prose is full of em
        # dashes and arrows, and it is not written consistently: 27 files hold
        # them as literal UTF-8, 51 as \u escapes (none mixes the two), because
        # they came from generator scripts that disagreed about `ensure_ascii`.
        #
        # Picking either setting globally rewrites the other group's every
        # non-ASCII character. That is semantically identical JSON and a diff
        # touching nearly every line of 78 files — which defeats the point of
        # landing this as a mechanical commit a reviewer can check by eye.
        path.write_text(
            json.dumps(doc, indent=2, ensure_ascii=ascii_only) + "\n",
            encoding="utf-8",
        )
    print(f"\nrewrote {len(to_write)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
