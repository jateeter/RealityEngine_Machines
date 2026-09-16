#!/usr/bin/env python3
"""The OpenClaw regression profile must agree with the corpus (M3 criterion 3).

M3's third acceptance criterion is that
`generate-regression-profile.py --check` is **required** before OpenClaw
validation. It was not. The script has carried `--check` since it was written,
and its own docstring says "Run it in CI and after any corpus change" — but a
search across every shell script, workflow and test in the workspace found
**nothing that calls it**. It was available, not required, which is a different
thing and the weaker one.

## Why the requirement belongs here

The profile is derived from `RealityEngine_CI/config/standard-deployment-corpus.txt`
plus this repository's machine corpus, so **this** repository is where it goes
stale. A corpus change lands here; the profile it invalidates lives two repos
away in `localOpenClawStack`; and nothing connected the two. Putting the check
in `localOpenClawStack`'s own CI would catch the drift only after someone
happened to run that repo's suite, which is not "before OpenClaw validation".

So the check runs in the contract suite, on every change to this repo — the
moment the profile can become wrong.

## What a stale profile actually costs

The profile names the machine-behavior agents bound to the machines the
Perception Engines load during a regression run. When it disagrees with the
corpus, OpenClaw validation dispatches to agents for machines that are not
loaded, or silently fails to dispatch for machines that are — and both look like
engine defects from outside. That is the shape this project keeps paying for:
`RealityEngine_CI#283`, `#304` and `#307` were all one measurement assuming
something it never asserted.

## Skipping, and why the skip is narrow

`localOpenClawStack` is an independent sibling repository and may not be checked
out. That is a legitimate absence and the test skips for it. It does **not** skip
for a missing profile, a missing agent index, or a `--check` that fails — those
are the conditions it exists to catch, and a test that skips on its own subject
matter is the inert guard this milestone was written to stop producing.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT.parent
OPENCLAW = WORKSPACE / "localOpenClawStack"
GENERATOR = OPENCLAW / "scripts" / "generate-regression-profile.py"
PROFILE = OPENCLAW / "machine-behaviors" / "agents" / "profiles" / "regression.txt"
AGENT_INDEX = OPENCLAW / "machine-behaviors" / "agents" / "INDEX.json"
MANIFEST = WORKSPACE / "RealityEngine_CI" / "config" / "standard-deployment-corpus.txt"


class OpenClawProfileDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not OPENCLAW.is_dir():
            raise unittest.SkipTest(
                "localOpenClawStack is not checked out; it is an independent "
                "sibling repository, not a dependency of this one")

    def test_the_drift_generator_is_present_and_offers_check(self) -> None:
        # Asserted rather than assumed: the criterion names this script by path
        # and by flag, so a rename or a removed flag must fail here loudly
        # instead of turning the requirement below into a silent no-op.
        self.assertTrue(GENERATOR.is_file(),
                        f"{GENERATOR} is missing — M3 criterion 3 names it directly")
        self.assertIn("--check", GENERATOR.read_text(),
                      "generate-regression-profile.py no longer offers --check")

    def test_the_committed_profile_exists(self) -> None:
        # Not a skip. start.sh consumes the committed profile, so its absence is
        # a broken deployment, not an absent optional input.
        self.assertTrue(PROFILE.is_file(),
                        f"{PROFILE} is missing — run generate-regression-profile.py")
        self.assertTrue(AGENT_INDEX.is_file(),
                        f"{AGENT_INDEX} is missing — the profile cannot be derived without it")

    def test_the_profile_agrees_with_the_corpus(self) -> None:
        """The requirement itself. A corpus change that invalidates the profile fails here.

        This is what makes `--check` *required*: it now runs on every change to
        the repository that owns the corpus the profile is derived from.
        """
        if not MANIFEST.is_file():
            self.skipTest(f"{MANIFEST} not present; RealityEngine_CI is a sibling repo")

        proc = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            cwd=OPENCLAW, capture_output=True, text=True, timeout=120)

        self.assertEqual(
            proc.returncode, 0,
            "the OpenClaw regression profile no longer matches the corpus.\n"
            "A machine added to, removed from or renamed in standard-deployment-corpus.txt\n"
            "changes which agents a regression run must dispatch to. Regenerate and commit:\n"
            "    cd ../localOpenClawStack && ./scripts/generate-regression-profile.py\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")

    def test_the_drift_check_actually_detects_drift(self) -> None:
        """The negative case, without mutating any repository.

        A test that only ever sees a clean tree cannot distinguish "the profile
        agrees with the corpus" from "--check cannot fail". That is exactly how
        M2 shipped an OWL axiom with an empty extension, so the guard is shown
        working here rather than assumed to.

        The generator accepts `--manifest`, so drift is simulated by handing it
        a manifest with one machine removed. Nothing on disk is changed.
        """
        if not MANIFEST.is_file():
            self.skipTest("RealityEngine_CI manifest not present")

        import tempfile

        lines = MANIFEST.read_text().splitlines(keepends=True)
        machines = [i for i, l in enumerate(lines)
                    if l.strip() and not l.startswith("#")]
        self.assertGreater(len(machines), 1, "manifest has too few machines to perturb")
        drifted = [l for i, l in enumerate(lines) if i != machines[0]]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "standard-deployment-corpus.txt"
            path.write_text("".join(drifted))
            proc = subprocess.run(
                [sys.executable, str(GENERATOR), "--check", "--manifest", str(path)],
                cwd=OPENCLAW, capture_output=True, text=True, timeout=120)

        self.assertNotEqual(
            proc.returncode, 0,
            "--check passed against a manifest with a machine removed, so it "
            "cannot detect drift and the requirement above is inert.\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")
        self.assertIn("stale", (proc.stdout + proc.stderr).lower(),
                      "--check failed, but not with a message that names drift")

    def test_every_profiled_agent_names_a_machine_in_the_manifest(self) -> None:
        """The join the generator makes, checked independently of the generator.

        `--check` compares the committed profile against what the generator
        would now produce. Both sides come from the same code, so a defect in
        the join logic agrees with itself. This reads the profile and the
        manifest directly and asks whether the agents named correspond to
        machines actually in the corpus.
        """
        if not MANIFEST.is_file():
            self.skipTest("RealityEngine_CI manifest not present")

        import json
        import re

        def norm(value: str) -> str:
            return re.sub(r"[^a-z0-9]", "", value.lower())

        manifest_stems = {
            norm(Path(line.strip()).stem)
            for line in MANIFEST.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        }
        # The manifest addresses machines by file; the agent index by display
        # name. Carry both keys so the join does not depend on which one a
        # machine's file happens to match.
        machine_names = set()
        for line in MANIFEST.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            path = REPO_ROOT / "machines" / line
            if path.is_file():
                with path.open() as fh:
                    machine_names.add(norm(json.load(fh)["machine"].get("name", "")))

        index = {norm(a.get("machineName", "")): a.get("agentId")
                 for a in json.loads(AGENT_INDEX.read_text()).get("agents", [])}
        by_agent = {v: k for k, v in index.items()}

        profiled = [l.split("#")[0].strip()
                    for l in PROFILE.read_text().splitlines()
                    if l.strip() and not l.startswith("#")]
        self.assertTrue(profiled, "the regression profile names no agents")

        orphans = []
        for agent_id in profiled:
            key = by_agent.get(agent_id)
            if key is None:
                orphans.append(f"{agent_id} (not in the agent index)")
            elif key not in machine_names and key not in manifest_stems:
                orphans.append(f"{agent_id} -> '{key}' (no such machine in the manifest)")

        self.assertEqual(orphans, [],
                         "profiled agents that name no machine in the regression corpus:\n  "
                         + "\n  ".join(orphans))


if __name__ == "__main__":
    unittest.main()
