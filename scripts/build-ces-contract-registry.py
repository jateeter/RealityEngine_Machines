#!/usr/bin/env python3
"""Build (or verify) the CES contract registry at domains/ces-contract-registry.json.

**What it registers.** One entry per *scope* — a set of machines a CES
output-stream contract can be recorded for. There are two kinds:

- `domain:<name>`, one per directory under `machines/domains/`, discovered
  rather than listed, so a domain becomes registrable the moment it exists.
- `corpus:<name>`, one per configured test-environment selection in
  `RealityEngine_CI/config/*-corpus.txt` — the same lists `startUniverse.sh`
  boots from. These are cross-domain by construction: `regression` reaches into
  five domains and into localAIStack.

**Why sharded at all.** The predecessor was one artifact for everything. A
machine added to one domain meant re-recording all of it, against a live
three-runtime quorum, and reviewing a diff nobody could read. Divergence is a
property of machine shape and the corpus grows a domain at a time, so the
shard boundary that matches how the corpus mutates is the domain.

**What "current" means.** A shard is a recording of what the cpp, LSP and Scala
runtimes did with a set of machines; it stays true only while that set is
unchanged. Each shard therefore carries the fingerprint of the corpus it was
recorded against (`corpusFingerprint`, written by the recorder), and this
builder compares it with the corpus as it stands. The comparison is per-machine,
so a stale shard names the machines that arrived, changed or left rather than
only reporting that it is stale — incremental addition is the expected way this
corpus grows, and "which ones" is the question a reader actually has.

**Versioning is content-addressed, not counted.** A shard's version is its
contract version and the first twelve hex of the corpus digest it was recorded
against (`2.0.0+corpus.79f4300a2a5b`). No counter is carried across builds, so
this stays a pure function of the corpus and the shards on disk: two people
building it from the same inputs get the same file, and a version that changed
says exactly which input moved. A monotonic revision would have to be
remembered, and a remembered number is one that can be wrong.

**Recording is not this script's job.** Shards are derived from a live 3-of-3
quorum by `RealityEngine_CI/scripts/regression-ces-contracts.py`, driven in bulk
by `RealityEngine_CI/scripts/record-ces-contract-shards.sh`. This repo owns the
corpus and therefore owns the question of whether a recording still describes
it; it does not own the runtimes and does not pretend to record anything. A
scope with no shard on disk is registered as `unrecorded` — a named gap, not an
absence.

Usage:
  python3 scripts/build-ces-contract-registry.py --write   # regenerate
  python3 scripts/build-ces-contract-registry.py --check   # fail if stale
  python3 scripts/build-ces-contract-registry.py --status  # human summary, no write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ces_corpus_fingerprint as fp  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
DOMAINS = MACHINES / "domains"
REGISTRY = REPO_ROOT / "domains" / "ces-contract-registry.json"

CI_ROOT = REPO_ROOT.parent / "RealityEngine_CI"
SHARD_DIR = CI_ROOT / "config" / "ces-contracts"
LOCAL_AI_MACHINES = REPO_ROOT.parent / "localAIStack" / "data" / "machines"

# The regression corpus predates the shard directory and is already the
# authoritative artifact the CI drift gate runs against, at its own path. It is
# registered where it lives rather than copied, because two files holding one
# contract is how the two come to disagree.
LEGACY_SHARD_PATHS = {"corpus:regression": CI_ROOT / "config" / "ces-contracts.json"}

MAX_CHAIN_DEPTH = 4  # the recorder's cap; mirrored so counts are comparable


# ── Scope discovery ─────────────────────────────────────────────────────────

def corpus_roots() -> list[Path]:
    """Where a selection's machines may live. More than one repo, deliberately.

    Three of the regression selection's entries are owned by localAIStack, and
    a scope that silently resolves 18 of 21 is a narrower scope wearing the name
    of a wider one.
    """
    return [MACHINES, LOCAL_AI_MACHINES]


def corpus_files() -> dict[str, Path]:
    """Basename → path across every root. Corpus filenames are globally unique."""
    out: dict[str, Path] = {}
    for root in corpus_roots():
        if root.is_dir():
            for f in sorted(root.rglob("*.json")):
                out.setdefault(f.name, f)
    return out


def domain_scopes() -> dict[str, list[Path]]:
    if not DOMAINS.is_dir():
        return {}
    return {f"domain:{d.name}": sorted(d.rglob("*.json"))
            for d in sorted(DOMAINS.iterdir()) if d.is_dir()}


def corpus_scopes(files: dict[str, Path]) -> tuple[dict[str, list[Path]], dict[str, list[str]]]:
    """The configured test-environment selections, and any entries that do not resolve.

    Unresolved entries are carried into the registry rather than dropped. A
    selection naming a machine that no longer exists is a finding about the
    selection; deleting it here would leave the registry describing a corpus
    nobody configured.
    """
    scopes: dict[str, list[Path]] = {}
    unresolved: dict[str, list[str]] = {}
    config = CI_ROOT / "config"
    if not config.is_dir():
        return scopes, unresolved
    for listing in sorted(config.glob("*-corpus.txt")):
        name = listing.stem[: -len("-corpus")]
        paths, missing = [], []
        for line in listing.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            base = line.split("/")[-1]
            (paths.append(files[base]) if base in files else missing.append(base))
        scopes[f"corpus:{name}"] = paths
        if missing:
            unresolved[f"corpus:{name}"] = sorted(missing)
    return scopes, unresolved


# ── Chain count (what a shard would have to cover) ──────────────────────────

def chain_count(path: Path) -> int:
    """Chains the recorder would enumerate from this machine.

    Registered so a scope states its size in the unit the recording actually
    costs. Machine count does not: a domain of 70 machines yields 104 chains and
    one of 71 yields 277, so planning a run from machine counts plans the wrong
    run.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    machine = raw.get("machine", raw) if isinstance(raw, dict) else {}
    mapping = machine.get("perceptualMapping") or {}
    if not mapping.get("input") or not mapping.get("output"):
        return 0
    total = 0
    for seq in machine.get("sequences") or []:
        events = seq.get("events") or []
        by_id = {e["id"]: e for e in events if "id" in e}

        def walk(trail: list[dict[str, Any]]) -> None:
            nonlocal total
            tail = trail[-1]
            if tail.get("outputEvents"):
                total += 1
            if len(trail) >= MAX_CHAIN_DEPTH:
                return
            seen = {e["id"] for e in trail}
            for nid in tail.get("nextEventIds") or []:
                nxt = by_id.get(nid)
                if nxt and nxt["id"] not in seen:
                    walk([*trail, nxt])

        for event in events:
            if event.get("isInitial"):
                walk([event])
    return total


# ── Shards ──────────────────────────────────────────────────────────────────

def shard_path(scope: str) -> Path:
    if scope in LEGACY_SHARD_PATHS:
        return LEGACY_SHARD_PATHS[scope]
    kind, _, name = scope.partition(":")
    return SHARD_DIR / f"{kind}-{name}.json"


def read_shard(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rel_to_repo(path: Path) -> str:
    """A path as written into the registry: repo-relative where possible.

    Shards live in the sibling CI repo, so most come out as `../RealityEngine_CI/...`.
    That the registry has to point outside this repo is the honest shape of the
    thing: the corpus is here, the runtimes that record against it are not.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        try:
            return "../" + path.resolve().relative_to(REPO_ROOT.resolve().parent).as_posix()
        except ValueError:
            return path.as_posix()


def scope_entry(scope: str, paths: list[Path], unresolved: list[str]) -> dict[str, Any]:
    current = fp.fingerprint_paths(paths, MACHINES)
    kind, _, name = scope.partition(":")
    path = shard_path(scope)
    shard = read_shard(path)

    entry: dict[str, Any] = {
        "kind": kind,
        "name": name,
        "artifact": rel_to_repo(path),
        "machineCount": len(paths),
        "chainCount": sum(chain_count(p) for p in paths),
        "corpus": current,
    }
    if unresolved:
        entry["unresolvedSelectionEntries"] = unresolved

    if shard is None:
        entry["status"] = "unrecorded"
        entry["version"] = None
        return entry

    recorded = shard.get("corpusFingerprint")
    contract_version = shard.get("version", "unknown")
    entry["recording"] = {
        "contractVersion": contract_version,
        "generatedBy": shard.get("generatedBy"),
        "quorum": (shard.get("quorum") or {}).get("rule") or shard.get("quorum"),
        "runtimes": shard.get("runtimes"),
        "machineCorpus": shard.get("machineCorpus"),
        "counts": shard.get("counts"),
        "recordedCorpusDigest": (recorded or {}).get("digest"),
    }

    if recorded is None:
        # A shard predating the fingerprint. It cannot be shown to describe the
        # current corpus, and cannot be shown not to — which is not the same as
        # being current, and is not recorded as though it were.
        entry["status"] = "undatable"
        entry["version"] = f"{contract_version}+corpus.unknown"
        entry["note"] = ("recorded before shards carried a corpus fingerprint; "
                         "re-record to make staleness decidable")
        return entry

    drift = fp.compare(recorded, current)
    if fp.is_current(recorded, current):
        entry["status"] = "recorded"
    else:
        entry["status"] = "stale"
        entry["drift"] = drift
    entry["version"] = f"{contract_version}+corpus.{recorded['digest'][7:19]}"
    entry["expectedVersion"] = f"{contract_version}+corpus.{current['digest'][7:19]}"
    return entry


# ── Document ────────────────────────────────────────────────────────────────

def build() -> dict[str, Any]:
    files = corpus_files()
    scopes: dict[str, list[Path]] = {}
    scopes.update(domain_scopes())
    corpus, unresolved = corpus_scopes(files)
    scopes.update(corpus)

    entries = {s: scope_entry(s, p, unresolved.get(s, [])) for s, p in sorted(scopes.items())}
    status_counts: dict[str, int] = {}
    for e in entries.values():
        status_counts[e["status"]] = status_counts.get(e["status"], 0) + 1

    return {
        "schemaVersion": "1.0.0",
        "purpose": ("Generated registry of CES output-stream contract shards — one per "
                    "corpus domain and per configured test-environment corpus. Regenerate "
                    "with scripts/build-ces-contract-registry.py --write; do not edit by hand."),
        "derivedFrom": "3-of-3 agreement across the cpp, lsp and scala runtimes",
        "contract": "../RealityEngine_CI/docs/QUORUM_CONTRACT.md",
        "recordedBy": "../RealityEngine_CI/scripts/regression-ces-contracts.py",
        "fingerprintAlgorithm": fp.ALGORITHM,
        "scopeCount": len(entries),
        "statusCounts": dict(sorted(status_counts.items())),
        # Summed across scopes, which overlap: every corpus selection's
        # machines also belong to a domain. Not a count of distinct chains, and
        # named so it cannot be read as one.
        "chainCountAcrossScopes": sum(e["chainCount"] for e in entries.values()),
        "scopes": entries,
    }


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def summarize(document: dict[str, Any]) -> None:
    order = {"stale": 0, "undatable": 1, "unrecorded": 2, "recorded": 3}
    rows = sorted(document["scopes"].items(),
                  key=lambda kv: (order.get(kv[1]["status"], 9), kv[0]))
    width = max(len(s) for s, _ in rows)
    for scope, e in rows:
        detail = ""
        if e["status"] == "stale":
            d = e["drift"]
            detail = (f"  +{len(d['added'])} added / ~{len(d['changed'])} changed"
                      f" / -{len(d['removed'])} removed")
        elif e["status"] == "recorded":
            c = e["recording"]["counts"] or {}
            detail = (f"  {c.get('agreed', '?')} agreed / {c.get('disagreement', '?')} disagreement"
                      f" / {c.get('noRuntimeEmits', '?')} silent / {c.get('unmeasurable', '?')} unmeasurable")
        print(f"{scope:<{width}}  {e['status']:<10} {e['machineCount']:>5} machines"
              f" {e['chainCount']:>6} chains{detail}")
    print()
    print(f"{document['scopeCount']} scopes, "
          f"{document['chainCountAcrossScopes']} chains across scopes (they overlap): "
          + ", ".join(f"{n} {s}" for s, n in document["statusCounts"].items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate the registry")
    mode.add_argument("--check", action="store_true", help="fail when the registry is stale")
    mode.add_argument("--status", action="store_true", help="print a summary; write nothing")
    parser.add_argument("--require-recorded", action="store_true",
                        help="with --check, also fail on any scope not currently recorded")
    args = parser.parse_args()

    document = build()
    serialized = render(document)

    if args.status:
        summarize(document)
        return 0

    if args.check:
        existing = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else None
        if existing != serialized:
            print(f"stale: {REGISTRY.relative_to(REPO_ROOT)} does not match the corpus",
                  file=sys.stderr)
            print("regenerate with: python3 scripts/build-ces-contract-registry.py --write",
                  file=sys.stderr)
            return 1
        if args.require_recorded:
            unmet = {s: e["status"] for s, e in document["scopes"].items()
                     if e["status"] != "recorded"}
            if unmet:
                for scope, status in sorted(unmet.items()):
                    print(f"{status}: {scope}", file=sys.stderr)
                print("re-record with: RealityEngine_CI/scripts/record-ces-contract-shards.sh",
                      file=sys.stderr)
                return 1
        print(f"ces-contract-registry: verified — {document['scopeCount']} scopes, "
              + ", ".join(f"{n} {s}" for s, n in document["statusCounts"].items()))
        return 0

    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(serialized, encoding="utf-8")
    print(f"wrote {REGISTRY.relative_to(REPO_ROOT)}")
    summarize(document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
