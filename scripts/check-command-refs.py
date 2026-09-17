#!/usr/bin/env python3
"""check-command-refs — every command this repo tells you to run must exist.

WHY THIS EXISTS
---------------
`scripts/remap-cross-domain-output-lanes.py` ended its regeneration recipe with
two commands that had ceased to exist:

    node scripts/cesgen-oracles.mjs     lives in RealityEngine_CI, not here
    node scripts/cesgen-contracts.mjs   retired with the artifact it wrote

The second wrote `contracts.json`, a cross-runtime parity recording that went
nine weeks stale and was replayed all that time against a corpus it no longer
described (RealityEngine_CI#327, RealityEngine_Machines#115). When the artifact
and its generator were retired, the instruction to regenerate them stayed.

That residue is worse than a dead link. A recipe is followed by someone making
exactly the kind of change that invalidates derived artifacts, and `node: cannot
find module` at the end of a five-command `&&` chain reads as a tooling hiccup,
not as "this artifact is no longer maintained here and something else now owns
it". The reader has already run the first three commands and will reasonably
conclude the job is done.

`check-generators.py` guards the same class one door over — a generator that
exists but is reachable from nothing. This guards its mirror image: a call that
is reachable but points at nothing. Absence is invisible in both directions, and
neither is caught by any gate that reads the corpus.

It is also why the blind spot survived. `remap-cross-domain-output-lanes.py` is
in check-generators' EXCLUDED set, correctly — it is a one-shot migration with
no artifact to keep current. Excluding a script from the inventory gate says
nothing about whether the instructions inside it still resolve.

WHAT IT ASSERTS
---------------
For every tracked text file, each of these that names a target in THIS repo:

    npm run <script>            -> declared in package.json "scripts"
    node scripts/<file>.mjs|js  -> the file exists
    python3 scripts/<file>.py   -> the file exists
    bash scripts/<file>.sh      -> the file exists

A reference introduced by another workspace repository -- `cd ../RealityEngine_CI
&& node scripts/x.mjs` -- resolves against that repo's tree, not this one, and is
skipped. The test is proximity, not the whole line: a sibling repo named 200
characters away in a prose paragraph says nothing about which tree the command
runs in, and treating it as cross-repo would silently drop this repo's own
references from the checked set. Skipped references are listed under --summary so
the unchecked set stays visible rather than silently absent -- which is the
failure mode this file exists to stop, and not one to reproduce inside it.

Usage:
    scripts/check-command-refs.py --check     # exit 1 on any dangling reference
    scripts/check-command-refs.py --summary   # every reference found, resolved or not
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKAGE_JSON = REPO / "package.json"

# How far back from a match to look for a sibling repo name before calling the
# reference cross-repo. Wide enough for `cd ../RealityEngine_CI && npm run x`,
# narrow enough that a repo named elsewhere in a prose paragraph does not
# suppress a reference that really does resolve here.
CROSS_REPO_WINDOW = 60

# Sibling repositories in the workspace. A reference introduced by one of these
# resolves against that repo's tree, which this gate cannot read.
SIBLING_REPOS = (
    "RealityEngine_CI",
    "RealityEngine_CPP",
    "RealityEngine_LSP",
    "RealityEngine_Scala",
    "RealityEngine_Manager",
    "RealityEngine_AI",
    "localAIStack",
    "localOpenClawStack",
    "localHealthkitBridge",
)

SCANNED_SUFFIXES = {".md", ".py", ".mjs", ".js", ".sh", ".json", ".yml", ".yaml"}

PATTERNS = (
    ("npm", re.compile(r"npm run ([A-Za-z0-9:_.-]+)")),
    ("node", re.compile(r"node\s+(scripts/[\w./-]+\.(?:mjs|js))")),
    ("python", re.compile(r"python3?\s+(scripts/[\w./-]+\.py)")),
    ("bash", re.compile(r"bash\s+(scripts/[\w./-]+\.sh)")),
)


def npm_scripts() -> set[str]:
    return set(json.loads(PACKAGE_JSON.read_text()).get("scripts", {}))


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return out.stdout.split()


def scan() -> tuple[list[tuple], list[tuple]]:
    """Return (dangling, cross_repo) reference lists."""
    declared = npm_scripts()
    dangling: list[tuple] = []
    cross_repo: list[tuple] = []

    for rel in tracked_files():
        path = REPO / rel
        if path.suffix not in SCANNED_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for kind, rx in PATTERNS:
            for match in rx.finditer(text):
                target = match.group(1)
                lineno = text[: match.start()].count("\n") + 1

                # Look back only within the current line, so a repo named on the
                # previous line cannot suppress this one.
                line_start = text.rfind("\n", 0, match.start()) + 1
                window = text[max(line_start, match.start() - CROSS_REPO_WINDOW) : match.start()]
                if any(repo in window for repo in SIBLING_REPOS):
                    cross_repo.append((rel, lineno, kind, target))
                    continue

                resolved = target in declared if kind == "npm" else (REPO / target).exists()
                if not resolved:
                    dangling.append((rel, lineno, kind, target))

    return sorted(dangling), sorted(cross_repo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 on any dangling reference")
    parser.add_argument("--summary", action="store_true", help="print every reference found")
    args = parser.parse_args()

    if not (args.check or args.summary):
        parser.print_help()
        return 2

    dangling, cross_repo = scan()

    if args.summary:
        print(f"check-command-refs: {len(cross_repo)} cross-repo reference(s), not checked here")
        for rel, lineno, kind, target in cross_repo:
            print(f"  {rel}:{lineno}  [{kind}]  {target}")
        print()

    if dangling:
        print(f"check-command-refs: {len(dangling)} dangling command reference(s)")
        for rel, lineno, kind, target in dangling:
            what = "npm script" if kind == "npm" else "file"
            print(f"  {rel}:{lineno}  [{kind}]  {target}  -- no such {what}")
        print()
        print("  A command this repo tells someone to run does not exist. Either the")
        print("  target was retired -- say so at the call site and name what replaced")
        print("  it -- or the reference is a typo. Do not delete the line silently: a")
        print("  recipe that loses a step is how a derived artifact goes stale unseen.")
        return 1

    print("[ok]   every command reference in this repo resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
