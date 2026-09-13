#!/usr/bin/env python3
"""What "the corpus changed" means, defined once.

A CES contract shard is a recording of what the three runtimes do with a set of
machines. It stays true only while that set is unchanged, so every shard has to
carry a description of the corpus it was recorded against, and something has to
compare that description with the corpus as it stands now.

Two places do the comparing — `RealityEngine_CI/scripts/regression-ces-contracts.py`
when it records, and `scripts/build-ces-contract-registry.py` when it reports
staleness — and if they computed the fingerprint even slightly differently
(sorted by a different key, hashing the parsed JSON rather than the bytes,
disagreeing about which files belong to a domain) the registry would report
drift that is not there, or miss drift that is. So the definition lives here,
in the repo that owns the corpus, and both sides import it.

**Per-file digests, not just a total.** A single digest answers "did the domain
change"; it cannot answer "which machine changed", and that is the question a
reader has when a shard goes stale. Incremental additions are the expected way
this corpus grows — a machine at a time, a domain at a time — so the registry
must be able to name the arrivals rather than only report that the count moved.

**Bytes, not parsed content.** A reformat that changes no semantics still
changes the file, and a recording made before it was made against a different
file. Claiming otherwise would require deciding which JSON differences are
semantically inert, which is a judgement this layer has no standing to make.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

ALGORITHM = "sha256/relfile-sorted-v1"


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(members: dict[str, str]) -> dict[str, Any]:
    """A corpus fingerprint over `relFile -> sha256` pairs.

    The rolled-up digest is taken over the sorted `relFile\\0sha256\\n` lines, so
    it depends on the names as well as the contents: a machine renamed but not
    otherwise touched is a different corpus, because the corpus addresses
    machines by globally-unique filename and something that resolved yesterday
    may not resolve today.
    """
    lines = "".join(f"{rel}\0{digest}\n" for rel, digest in sorted(members.items()))
    return {
        "algorithm": ALGORITHM,
        "machineCount": len(members),
        "digest": "sha256:" + hashlib.sha256(lines.encode("utf-8")).hexdigest(),
        "members": dict(sorted(members.items())),
    }


def fingerprint_paths(paths: Iterable[Path], root: Path) -> dict[str, Any]:
    """Fingerprint a set of machine files, keyed by their path relative to `root`.

    `root` is the corpus root (the directory holding `domains/`), so keys read
    as `domains/energy/EGX001_....json` — the same `relFile` spelling
    `domains/corpus-index.json` uses. A file outside `root` keys by basename;
    that is the localAIStack-owned trio, which the regression selection reaches
    across repos and which has no relFile in this corpus.
    """
    members: dict[str, str] = {}
    for path in paths:
        resolved = path.resolve()
        try:
            key = resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            key = resolved.name
        members[key] = file_digest(resolved)
    return fingerprint(members)


def compare(recorded: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """How a recorded fingerprint differs from the corpus as it stands.

    Returns the three lists a reader needs to act, never a boolean. "Stale" is
    the conclusion; which machines arrived, changed or left is the finding, and
    a gate that reports only the conclusion sends whoever reads it back to the
    corpus to re-derive what it already knew.
    """
    if not recorded:
        return {"added": sorted(current["members"]), "changed": [], "removed": []}
    old, new = recorded.get("members", {}), current["members"]
    return {
        "added": sorted(set(new) - set(old)),
        "removed": sorted(set(old) - set(new)),
        "changed": sorted(k for k in set(old) & set(new) if old[k] != new[k]),
    }


def is_current(recorded: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    return bool(recorded) and recorded.get("digest") == current["digest"]
