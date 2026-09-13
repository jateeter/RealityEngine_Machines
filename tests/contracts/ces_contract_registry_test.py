#!/usr/bin/env python3
"""Contract checks for the CES contract registry.

`domains/ces-contract-registry.json` records which CES output-stream contract
shards exist, what corpus each was recorded against, and whether that corpus has
moved since. The registry earns its keep only if it cannot quietly fall behind
the corpus, and only if a shard cannot quietly stop describing the machines it
names — so both are gated here, in the repo where a corpus change is made and
where its author can act on the result.

The predecessor artifact is the reason these gates are shaped this way. It was
one recording for everything, made by replaying the corpus through a single
nominated engine, and it sat two months behind a corpus rewrite before anyone
noticed — the drift surfaced in a deployment gate as six mismatches that were
the corpus moving, not the engines being wrong. Three properties would have
caught it, and each is a test below: the artifact says which corpus it describes,
something compares that with the corpus as it stands, and the comparison runs
where the corpus changes.

Gates:

- the registry is not stale with respect to the corpus
- the registry validates against its schema
- every domain under machines/domains/ has a scope, and every scope resolves
- a recorded shard's fingerprint matches the corpus it claims, per machine
- no recorded shard has gone stale (`unrecorded` is a gap, `stale` is a lie)
- no shard claims a quorum its own verdicts show it did not hold
- a domain shard carries only its own domain's machines
- shard files exist exactly where the registry says, and parse
- a recorded shard's own machine list is the scope's machine list
- no shard records a contract from less than a formed 3-of-3 quorum
- versions are content-addressed, and agree with the fingerprints they encode
- corpus selections resolve completely, or name what they could not resolve
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ces_corpus_fingerprint as fp  # noqa: E402

# Whether the shards are reachable from this checkout, decided by the builder's
# own discovery rather than a second copy of it here. The shards live in
# RealityEngine_CI, and the two repos sit differently in different places:
# siblings locally, but in the e2e-tests workflow the RealityEngine_CI checkout
# is the workspace root with this repo inside it, and localAIStack is not present
# at all.
#
# Every shard-reading assertion below is SKIPPED, not passed, when they cannot be
# reached. Skipped says "not evaluated here" and shows up as such; passing would
# claim the shards were checked and found good, which is the conflation this
# whole artifact class exists to prevent. Asserting instead — which is what this
# suite did on its first CI run — reports 16 failures and 76 errors for a
# checkout that is simply missing a sibling repo.
_spec = importlib.util.spec_from_file_location(
    "ces_registry_builder", REPO_ROOT / "scripts" / "build-ces-contract-registry.py")
_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builder)
# Tested on the artifacts themselves, not on whether the repo was located.
# Finding RealityEngine_CI does not mean it carries the shards: the corpus-gate
# job checks it out at the PR ref, and a branch that has not recorded any shard
# has no config/ces-contracts at all. "Repo found" and "shards present" are
# different facts and the first was standing in for the second, which is why
# this gating did not work on its first attempt.
SHARDS_REACHABLE = _builder.SHARD_DIR.is_dir() or _builder.LEGACY_SHARD_PATHS[
    "corpus:regression"].is_file()


def _shard_readable(scope: str) -> bool:
    """Whether THIS scope's shard can actually be opened from here.

    The directory existing is not the same as a given shard resolving, and the
    difference is not hypothetical: in the corpus-gate job the RealityEngine_CI
    checkout is the workspace root, so `SHARD_DIR` resolves and exists while
    `REPO_ROOT / "../RealityEngine_CI/config/..."` -- the canonical spelling the
    registry records -- points at nothing. Reachability said yes, every shard
    read said no, and the suite reported 16 failures for a layout difference.
    """
    try:
        return _builder.shard_path(scope).is_file()
    except Exception:  # noqa: BLE001
        return False
UNREACHABLE_WHY = (f"no CES contract shards under {_builder.SHARD_DIR}; "
                   "shard-reading assertions cannot be evaluated in this checkout")

REGISTRY = REPO_ROOT / "domains" / "ces-contract-registry.json"
SCHEMA = REPO_ROOT / "schemas" / "ces-contract-registry.schema.json"
BUILDER = REPO_ROOT / "scripts" / "build-ces-contract-registry.py"
DOMAINS = REPO_ROOT / "machines" / "domains"

# The quorum rule, restated nowhere else. 3-of-3, never a majority: two runtimes
# agreeing is a contract with an unexamined third, and the largest cluster is
# not the answer (RealityEngine_CI/docs/QUORUM_CONTRACT.md §1).
QUORUM_RULE = "3-of-3"
NATIVE_RUNTIMES = {"cpp", "lsp", "scala"}


class CesContractRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not REGISTRY.exists():
            raise unittest.SkipTest(f"{REGISTRY.name} has not been built yet")
        cls.document = json.loads(REGISTRY.read_text())
        cls.scopes = cls.document["scopes"]

    # ── the registry itself ────────────────────────────────────────────────

    def test_registry_is_not_stale(self) -> None:
        """The generated file matches what the corpus and the shards produce now.

        This is the gate the predecessor did not have. Its `--check` mode existed
        and nothing invoked it, and a snapshot nobody re-takes silently becomes
        an assertion about the past.
        """
        result = subprocess.run([sys.executable, str(BUILDER), "--check"],
                                capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validates_against_schema(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads(SCHEMA.read_text())
        errors = sorted(Draft202012Validator(schema).iter_errors(self.document),
                        key=lambda e: list(e.path))
        self.assertEqual(
            [], [f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors])

    # ── coverage ───────────────────────────────────────────────────────────

    def test_every_domain_has_a_scope(self) -> None:
        """A domain the corpus holds but the registry does not name is a domain
        whose contract nobody is tracking — and it would be invisible, because
        the registry's own counts would look complete."""
        on_disk = {f"domain:{d.name}" for d in DOMAINS.iterdir() if d.is_dir()}
        self.assertEqual(set(), on_disk - set(self.scopes))

    def test_no_scope_is_empty(self) -> None:
        """A scope resolving to no machines is a name with nothing behind it,
        and it would record as a shard of zero contracts that reads as passing."""
        empty = [s for s, e in self.scopes.items() if e["machineCount"] == 0]
        self.assertEqual([], empty)

    def test_selections_resolve_completely(self) -> None:
        """A corpus list naming a file that resolves nowhere is a narrower scope
        wearing the name of a wider one. It may be a known state, but it must be
        enumerated in the registry rather than silently narrowing the shard."""
        for scope, entry in self.scopes.items():
            for missing in entry.get("unresolvedSelectionEntries", []):
                with self.subTest(scope=scope, missing=missing):
                    self.fail(f"{scope} names {missing}, which resolves to no file "
                              f"under any corpus root")

    # ── the shards ─────────────────────────────────────────────────────────

    def recorded_scopes(self) -> list[tuple[str, dict]]:
        return [(s, e) for s, e in self.scopes.items() if e["status"] == "recorded"]

    @unittest.skipUnless(SHARDS_REACHABLE, UNREACHABLE_WHY)
    def test_recorded_shards_exist_and_parse(self) -> None:
        for scope, entry in self.recorded_scopes():
            with self.subTest(scope=scope):
                path = _builder.shard_path(scope)
                self.assertTrue(path.exists(), f"{scope}: no shard at {entry['artifact']}")
                json.loads(path.read_text())

    @unittest.skipUnless(SHARDS_REACHABLE, UNREACHABLE_WHY)
    def test_recorded_fingerprint_matches_the_corpus_per_machine(self) -> None:
        """Recomputed here rather than trusted from the registry.

        The registry is generated by the same module it would be checked
        against, so comparing its two fields to each other proves only that the
        generator is self-consistent. Reading the shard and hashing the machine
        files independently is what makes this a check rather than a tautology.
        """
        for scope, entry in self.recorded_scopes():
            with self.subTest(scope=scope):
                shard = json.loads(_builder.shard_path(scope).read_text())
                recorded = shard.get("corpusFingerprint")
                self.assertIsNotNone(recorded, f"{scope}: shard carries no corpusFingerprint")
                drift = fp.compare(recorded, entry["corpus"])
                self.assertEqual(
                    {"added": [], "changed": [], "removed": []}, drift,
                    f"{scope} is registered as recorded but the corpus has moved")

    @unittest.skipUnless(SHARDS_REACHABLE, UNREACHABLE_WHY)
    def test_shard_covers_exactly_the_scope(self) -> None:
        """The shard's own machine list is the scope's machine list.

        A shard recorded with `--machine-names` narrowing it, or against a
        universe missing part of the scope, covers less than its name claims.
        Nothing in the shard's counts would show that: fewer machines simply
        means fewer contracts, which reads as a smaller domain.
        """
        for scope, entry in self.recorded_scopes():
            with self.subTest(scope=scope):
                shard = json.loads(_builder.shard_path(scope).read_text())
                self.assertEqual(
                    sorted(entry["corpus"]["members"]),
                    sorted((shard.get("corpusFingerprint") or {}).get("members", {})),
                    f"{scope}: the shard covers a different set of machines")

    @unittest.skipUnless(SHARDS_REACHABLE, UNREACHABLE_WHY)
    def test_domain_shards_contain_only_their_own_domain(self) -> None:
        """A domain shard describes that domain and nothing else.

        Shards are recorded against a live universe holding the whole resident
        corpus, and one push advances all of it — so the recorder sees every
        machine that fired, not only the one under test. Two mechanisms keep the
        shard domain-pure: chains are enumerated only from the domain's own
        files, and each step is filtered to entries carrying that machine's own
        sequence ids. Neither is visible in the artifact, so both are gated here.

        Without this, a shard could accumulate whatever else happened to be
        loaded, and the accumulation would be invisible: more contracts reads as
        better coverage, not as contamination. It would also make shards depend
        on load ORDER — a domain recorded early would describe less than the
        same domain recorded late, and neither would be reproducible.
        """
        for scope, entry in self.scopes.items():
            if entry["kind"] != "domain" or entry["status"] == "unrecorded":
                continue
            with self.subTest(scope=scope):
                own = {p.name for p in (DOMAINS / entry["name"]).rglob("*.json")}
                shard = json.loads(_builder.shard_path(scope).read_text())

                foreign = set()
                for key in ("contracts", "disagreements", "noRuntimeEmits",
                            "unmeasurable", "intermittent"):
                    for e in shard.get(key, []):
                        machine = e.get("machineFile") or e["chain"].split("::")[0]
                        if machine not in own:
                            foreign.add(machine)
                self.assertEqual(
                    set(), foreign,
                    f"{scope} carries machines from outside its domain: {sorted(foreign)}")

                members = {m.split("/")[-1]
                           for m in (shard.get("corpusFingerprint") or {}).get("members", {})}
                self.assertEqual(
                    own, members,
                    f"{scope}: the fingerprint does not cover exactly the domain directory")

    @unittest.skipUnless(SHARDS_REACHABLE, UNREACHABLE_WHY)
    def test_no_shard_records_below_quorum(self) -> None:
        """A recorded contract came from all three native runtimes.

        Silence from a runtime is a finding, never assent, so a shard written
        while one lane was down is not a weaker contract — it is not a contract.
        """
        for scope, entry in self.recorded_scopes():
            with self.subTest(scope=scope):
                shard = json.loads(_builder.shard_path(scope).read_text())
                quorum = shard.get("quorum") or {}
                self.assertEqual(QUORUM_RULE, quorum.get("rule"), f"{scope}: not {QUORUM_RULE}")
                self.assertTrue(quorum.get("formed"), f"{scope}: quorum not formed")
                self.assertEqual([], quorum.get("missing"), f"{scope}: a runtime was missing")
                self.assertTrue(
                    NATIVE_RUNTIMES.issubset(set(shard.get("runtimes") or [])),
                    f"{scope}: runtimes {shard.get('runtimes')} do not cover {sorted(NATIVE_RUNTIMES)}")
                for contract in shard.get("contracts", []):
                    self.assertEqual(QUORUM_RULE, contract.get("quorum"))
                    self.assertEqual(3, len(contract.get("agreedBy", [])),
                                     f"{scope}: {contract.get('chain')} agreed by fewer than three")

    @unittest.skipUnless(SHARDS_REACHABLE, UNREACHABLE_WHY)
    def test_no_shard_claims_a_quorum_it_did_not_hold(self) -> None:
        """A shard's quorum claim is checked against its own evidence.

        `quorum.formed` is recorded once, before anything is driven, so it says
        the quorum existed at the start — not that it survived. An `unmeasurable`
        verdict naming undriven runtimes is proof it did not: that runtime could
        not be reached, so every `agreed` entry claiming three-way agreement in
        the same artifact is asserting something the run was no longer able to
        observe.

        Measured: lsp and scala died partway through the energy domain. The
        artifact was written with `formed: true, missing: []`, 224 contracts
        agreed by three runtimes, and 139 chains that could not be driven. The
        quorum block and the verdict list contradicted each other, and only the
        block was being read.
        """
        for scope, entry in self.scopes.items():
            if entry["status"] == "unrecorded":
                continue
            with self.subTest(scope=scope):
                shard = json.loads(_builder.shard_path(scope).read_text())
                undriven = {r for u in shard.get("unmeasurable", [])
                            for r in u.get("undrivenRuntimes", [])}
                if not undriven:
                    continue
                self.fail(
                    f"{scope} claims {shard.get('quorum', {}).get('rule')} with "
                    f"missing={shard.get('quorum', {}).get('missing')}, but "
                    f"{len(shard['unmeasurable'])} chain(s) record "
                    f"{sorted(undriven)} as undriven — the quorum did not hold "
                    f"for the whole recording, so its agreed contracts are not "
                    f"three-way agreements. Re-record.")

    # ── versioning ─────────────────────────────────────────────────────────

    def test_versions_are_content_addressed(self) -> None:
        """A version encodes the corpus digest it was recorded against.

        Content-addressed rather than counted, so the registry stays a pure
        function of its inputs: two people building it from the same corpus and
        the same shards get the same file. A carried counter would have to be
        remembered, and a remembered number is one that can be wrong.
        """
        for scope, entry in self.scopes.items():
            with self.subTest(scope=scope):
                if entry["status"] == "unrecorded":
                    self.assertIsNone(entry["version"])
                    continue
                self.assertIsNotNone(entry["version"])
                if entry["status"] == "undatable":
                    self.assertTrue(entry["version"].endswith("+corpus.unknown"))
                    continue
                short = entry["corpus"]["digest"][7:19]
                self.assertEqual(f"{entry['recording']['contractVersion']}+corpus.{short}",
                                 entry["expectedVersion"])
                if entry["status"] == "recorded":
                    self.assertEqual(entry["version"], entry["expectedVersion"],
                                     f"{scope}: recorded but its version is not the expected one")
                else:
                    self.assertNotEqual(entry["version"], entry["expectedVersion"],
                                        f"{scope}: stale but its version did not move")

    def test_no_recorded_shard_has_gone_stale(self) -> None:
        """A shard that exists and no longer describes its machines fails here.

        This is the gate the whole design exists for, and it is deliberately
        harder than the others: satisfying it needs a live 3-of-3 universe,
        because re-recording is the only honest way to make a stale shard
        current again. Editing the registry would not do it, and neither would
        deleting the shard.

        `unrecorded` is not a failure and must never become one. A scope nobody
        has recorded yet is a named gap the registry is tracking — enumerated,
        visible, and true. A scope whose shard says one thing while the corpus
        says another is not a gap; it is a false statement that reads as a
        passing contract, and the two must not be scored the same way. That
        conflation is exactly how the predecessor artifact sat two months behind
        the corpus while looking fine.
        """
        stale = {s: e["drift"] for s, e in self.scopes.items() if e["status"] == "stale"}
        if not stale:
            return
        lines = []
        for scope, drift in sorted(stale.items()):
            moved = ", ".join(
                f"{len(drift[k])} {k}" for k in ("added", "changed", "removed") if drift[k])
            lines.append(f"  {scope}: {moved}")
            for kind in ("added", "changed", "removed"):
                lines += [f"      {kind[0].upper()} {m}" for m in drift[kind]]
        self.fail(
            "the corpus moved under these recorded shards:\n" + "\n".join(lines)
            + "\n  re-record against a live 3-of-3 universe:\n"
              "      RealityEngine_CI/scripts/record-ces-contract-shards.sh --only="
            + ",".join(sorted(stale)))

    def test_stale_scopes_name_what_moved(self) -> None:
        """Staleness without attribution sends the reader back to the corpus to
        re-derive what the gate already knew."""
        for scope, entry in self.scopes.items():
            if entry["status"] != "stale":
                continue
            with self.subTest(scope=scope):
                drift = entry.get("drift")
                self.assertIsNotNone(drift, f"{scope}: stale with no drift recorded")
                self.assertTrue(any(drift[k] for k in ("added", "changed", "removed")),
                                f"{scope}: stale but names no machine that moved")


if __name__ == "__main__":
    unittest.main()
