#!/usr/bin/env python3
"""One provenance stamp for every generated asset.

Generated assets carried `schemaVersion` — the shape of the document — and
nothing about the corpus they were generated *from*. A `.json` or `.ttl` on disk
could not be attributed to a corpus state, so "is this current?" was not a
question the artifact could answer; it had to be re-derived and compared. That
is the gap `corpusFingerprint` closed for CES contract shards and `robot
annotate --version-iri` closed for the OWL, and this closes it for the rest.

**Content-derived, never time-derived.** A timestamp would change on every run
and break every `--check` drift gate in this repo — the gates compare generated
output against the committed file byte-for-byte. A git SHA is no better: it moves
on every commit, including commits that touch nothing this asset reads, so the
asset would read stale for reasons unrelated to it.

The digest is over the generator's declared *inputs*, using the definition in
`ces_corpus_fingerprint.py` rather than a second one. It changes when and only
when something the asset is derived from changes. Two people generating from the
same corpus get the same stamp; a drift gate stays meaningful.

Version strings read `1.0.0+corpus.79f4300a2a5b` — schema version, then the
first twelve hex of the input digest. The same scheme the cesgen registry uses,
so one convention covers every asset in the workspace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import ces_corpus_fingerprint as fp

REPO_ROOT = Path(__file__).resolve().parent.parent


def stamp(generator: str, inputs: Iterable[Path], schema_version: str = "1.0.0",
          root: Path | None = None) -> dict[str, Any]:
    """The provenance block to merge into a generated document.

    `inputs` is what the asset is derived from — the machine files, the ontology,
    whatever the generator actually reads. Naming them is the point: an asset
    whose stamp covers the wrong inputs reports current while its real sources
    have moved.
    """
    finger = fp.fingerprint_paths(list(inputs), root or (REPO_ROOT / "machines"))
    return {
        "schemaVersion": schema_version,
        "generator": generator,
        "assetVersion": f"{schema_version}+corpus.{finger['digest'][7:19]}",
        "inputs": {
            "algorithm": finger["algorithm"],
            "count": finger["machineCount"],
            "digest": finger["digest"],
        },
    }


def is_current(document: dict[str, Any], generator: str, inputs: Iterable[Path],
               schema_version: str = "1.0.0", root: Path | None = None) -> bool:
    """Whether a document's stamp matches the inputs as they stand now."""
    want = stamp(generator, inputs, schema_version, root)
    have = document.get("inputs") or {}
    return have.get("digest") == want["inputs"]["digest"]
