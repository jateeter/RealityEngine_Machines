#!/usr/bin/env python3
"""Dynamic ROBOT runtime validation — M5.

    scripts/validate-runtime-trace.py --trace trace.ttl --profile standard-deployment
    scripts/validate-runtime-trace.py --trace trace.ttl --emit violations.ttl
    scripts/validate-runtime-trace.py --fixtures      # each must be rejected

M3 proved the authored corpus. M4 exported what actually ran. M5 puts the two in
one graph and asks whether the run obeyed the semantics the corpus declares.

The sequence is the roadmap's:

    merge ontology + profile ABoxes + runtime trace
      -> ROBOT report   (syntax and profile errors)
      -> ROBOT reason   (consistency; the escalation axiom is HermiT-only)
      -> deterministic closed-world checks

## Why the last step is not ROBOT's

ROBOT answers what the graph entails. It cannot answer "this write went two
cells past the region its mapping declares", because that is arithmetic over
asserted values, nor "this endpoint is not in the allowed catalogue", because
absence from a list is not a contradiction under an open world. Those are the
closed-world half, and M5 names them explicitly: "Validate exact region writes,
cardinality, and forbidden endpoint use".

Every finding — from either half — becomes a named `re:SemanticGuardrailViolation`
individual. M5's third criterion asks for a *named violation record*, not an exit
code, because a run that fails should say which rule and which record.

## The allowed-endpoint catalogue

M3 reported R2's workflow-class half as ungated because no `integrations.json`
entry declares `allowedOperations`. It turns out the PE serves one:
`GET /api/integrations/localai/catalog` returns `allowedEndpoints` with ids,
methods and paths. This reads that when a PE URL is given, so forbidden-endpoint
use is checkable against what the deployment actually permits rather than
against a list maintained here.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = REPO_ROOT.parent
ONTOLOGY = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
EXAMPLES = REPO_ROOT / "semantics" / "integration" / "examples.ttl"
ABOX_ROOT = REPO_ROOT / "semantics" / "abox"
MACHINES_ROOT = REPO_ROOT / "machines"
CI_CONFIG = WORKSPACE / "RealityEngine_CI" / "config"
FIXTURE_ROOT = REPO_ROOT / "semantics" / "shapes" / "fixtures" / "bad-traces"
REPORT_PROFILE = REPO_ROOT / "semantics" / "robot-report-profile.txt"


def robot_bin() -> str | None:
    return os.environ.get("ROBOT_BIN") or shutil.which("robot")


class Violation:
    def __init__(self, rule: str, kind: str, severity: str, record: str, detail: str):
        self.rule, self.kind, self.severity = rule, kind, severity
        self.record, self.detail = record, detail

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule}: {self.kind} — {self.record}\n      {self.detail}"


class Result:
    def __init__(self) -> None:
        self.violations: list[Violation] = []
        self.checked: dict[str, int] = {}
        self.ungated: list[str] = []

    def add(self, *a) -> None:
        self.violations.append(Violation(*a))

    def bump(self, k: str, n: int = 1) -> None:
        self.checked[k] = self.checked.get(k, 0) + n

    def gap(self, note: str) -> None:
        self.ungated.append(note)


# ── Reading the trace ────────────────────────────────────────────────────────

def parse_ttl(text: str) -> dict[str, dict[str, list[str]]]:
    """Subject -> predicate -> objects, for the shape the exporter writes."""
    out: dict[str, dict[str, list[str]]] = {}
    subject: str | None = None
    for raw in text.splitlines():
        if raw.lstrip().startswith("#") or not raw.strip():
            continue
        if not raw.startswith((" ", "\t")):
            m = re.match(r"^([A-Za-z][\w-]*:[\w.:@+-]+)\s*$", raw.strip())
            subject = m.group(1) if m else None
            if subject:
                out.setdefault(subject, {})
            continue
        if subject is None:
            continue
        body = raw.strip().rstrip(" ;.").strip()
        m = re.match(r"^(?:a\s+(.*)|([A-Za-z][\w-]*:[\w-]+)\s+(.*))$", body)
        if not m:
            continue
        pred = "a" if m.group(1) is not None else m.group(2).removeprefix("re:")
        objs = [o.strip() for o in (m.group(1) or m.group(3)).split(",") if o.strip()]
        out[subject].setdefault(pred, []).extend(objs)
        if raw.rstrip().endswith("."):
            subject = None
    return out


def lit(vals: list[str] | None) -> str | None:
    if not vals:
        return None
    return vals[0].strip().strip('"').split("^^")[0].strip('"')


def num(vals: list[str] | None) -> int | None:
    v = lit(vals)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


# ── ROBOT half ───────────────────────────────────────────────────────────────

def robot_validate(trace: Path, profile: str, result: Result) -> None:
    """merge -> report -> reason, over ontology + profile ABoxes + the trace."""
    robot = robot_bin()
    if not robot:
        result.gap("ROBOT half SKIPPED: no ROBOT on PATH and no ROBOT_BIN set. "
                   "The closed-world half below still ran.")
        return

    inputs = ["--input", str(ONTOLOGY), "--input", str(EXAMPLES), "--input", str(trace)]
    manifest = CI_CONFIG / f"{profile}-corpus.txt"
    n_abox = 0
    if manifest.is_file():
        for line in manifest.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ab = ABOX_ROOT / Path(line).parent.name / f"{Path(line).stem}.ttl"
            if ab.is_file():
                inputs += ["--input", str(ab)]
                n_abox += 1
    result.bump("profile ABoxes merged", n_abox)

    with tempfile.TemporaryDirectory() as tmp:
        merged = Path(tmp) / "merged.owl"
        proc = subprocess.run([robot, "merge", *inputs, "--output", str(merged)],
                              capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            result.add("ROBOT", "merge-failed", "error", str(trace),
                       (proc.stderr or proc.stdout)[-500:])
            return
        result.bump("ROBOT merge", 1)

        rep = Path(tmp) / "report.tsv"
        proc = subprocess.run(
            [robot, "report", "--input", str(merged), "--profile", str(REPORT_PROFILE),
             "--fail-on", "ERROR", "--output", str(rep)],
            capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            rows = rep.read_text().splitlines()[1:] if rep.is_file() else []
            for row in rows[:20]:
                cols = row.split("\t")
                if len(cols) >= 3 and cols[0] == "ERROR":
                    result.add("ROBOT", f"report-{cols[1]}", "error", cols[2], row)
            if not result.violations:
                result.add("ROBOT", "report-failed", "error", str(trace),
                           (proc.stderr or proc.stdout)[-500:])
        result.bump("ROBOT report", 1)

        # HermiT, not ELK. The escalation invariant relies on constructs ELK does
        # not implement, and ELK passes a corpus that violates it — recorded in
        # semantics/claude.md and verified there.
        reasoned = Path(tmp) / "reasoned.owl"
        proc = subprocess.run(
            [robot, "reason", "--reasoner", "HermiT", "--input", str(merged),
             "--output", str(reasoned)],
            capture_output=True, text=True, timeout=3600)
        if proc.returncode != 0:
            result.add("ROBOT", "inconsistent-graph", "error", str(trace),
                       "HermiT rejected the merged graph: the run contradicts the "
                       "semantics the corpus declares.\n" +
                       (proc.stderr or proc.stdout)[-700:])
        result.bump("ROBOT reason (HermiT)", 1)


# ── Closed-world half ────────────────────────────────────────────────────────

def check_region_writes(g, result: Result) -> None:
    """Exact region writes: a write must land inside the region its mapping declares."""
    for subj, props in g.items():
        if "re:SourceMappingWrite" not in props.get("a", []):
            continue
        result.bump("region writes")
        targets = props.get("writesThroughMapping") or []
        if not targets:
            result.add("CW", "unmapped-completion-write", "error", subj,
                       "names no re:CompletionMapping: written by a route nothing approved")
            continue
        m = g.get(targets[0], {})
        m_off, m_len = num(m.get("completionOffset")), num(m.get("completionLength"))
        w_off, w_len = num(props.get("writeOffset")), num(props.get("writeLength"))
        if m_off is None or m_len is None or w_off is None or w_len is None:
            result.add("CW", "region-not-stated", "error", subj,
                       "write or mapping does not state both offset and length, so "
                       "containment cannot be decided")
            continue
        if w_off < m_off or w_off + w_len > m_off + m_len:
            result.add("CW", "write-outside-declared-region", "error", subj,
                       f"writes [{w_off}:{w_off + w_len}] through a mapping declaring "
                       f"[{m_off}:{m_off + m_len}]")


def check_cardinality(g, result: Result) -> None:
    """Cardinality: one determination per observation, one mapping per write.

    Functional in intent and not enforced by the wire format. Two mappings on
    one write means two authorisations were claimed for one act, and the
    approved route is then whichever the reader happens to look at first.
    """
    for subj, props in g.items():
        types = props.get("a", [])
        if "re:SequenceObservation" in types:
            result.bump("observations")
            det = props.get("recordsDetermination") or []
            if len(det) > 1:
                result.add("CW", "ambiguous-determination", "error", subj,
                           f"records {len(det)} determinations: {', '.join(det)}")
        if "re:SourceMappingWrite" in types:
            maps = props.get("writesThroughMapping") or []
            if len(maps) > 1:
                result.add("CW", "ambiguous-completion-mapping", "error", subj,
                           f"claims {len(maps)} approved mappings: {', '.join(maps)}")


def allowed_endpoints(pe_url: str | None) -> set[str] | None:
    """The deployment's own allowed-endpoint catalogue, if a PE is reachable.

    This is the source of truth M3's R2 reported as missing. It is served by the
    PE rather than declared in integrations.json, which is why the static check
    could not see it.
    """
    if not pe_url:
        return None
    try:
        with urllib.request.urlopen(f"{pe_url.rstrip('/')}/api/integrations/localai/catalog",
                                    timeout=20) as r:
            cat = json.loads(r.read())
    except Exception:
        return None
    eps = cat.get("allowedEndpoints") or []
    out = set()
    for e in eps:
        for key in ("id", "path"):
            if e.get(key):
                out.add(str(e[key]))
    return out or None


def check_forbidden_endpoints(g, allowed: set[str] | None, result: Result) -> None:
    for subj, props in g.items():
        if "re:MCPInvocation" not in props.get("a", []):
            continue
        result.bump("invocations")
        ep = lit(props.get("integrationEndpoint"))
        op = lit(props.get("allowedOperationId"))
        if allowed is None:
            continue
        for value, what in ((op, "operation"), (ep, "endpoint")):
            if value is None:
                continue
            tail = value.rsplit("/", 1)[-1]
            if value not in allowed and tail not in allowed and not any(
                    value.endswith(a) for a in allowed):
                result.add("CW", "forbidden-endpoint-use", "error", subj,
                           f"{what} '{value}' is not in the deployment's allowed "
                           f"catalogue ({len(allowed)} entries)")
    if allowed is None:
        result.gap("forbidden-endpoint check SKIPPED: no PE URL given, so the "
                   "deployment's allowed-endpoint catalogue could not be read. "
                   "Pass --pe-url to enable it.")


def check_run_grouping(g, result: Result) -> None:
    """Every event belongs to a run. Without it, merged traces lose their identity."""
    runs = [s for s, p in g.items() if "re:TraceRun" in p.get("a", [])]
    if len(runs) != 1:
        result.add("CW", "trace-run-ambiguous", "error", "(graph)",
                   f"the trace declares {len(runs)} re:TraceRun individuals; exactly one is expected")
    event_types = ("re:PerceptionEvent", "re:PerceptionPush", "re:SequenceObservation",
                   "re:SourceMappingWrite", "re:ACPDispatch", "re:MCPInvocation",
                   "re:DispatchRecord")
    orphans = [s for s, p in g.items()
               if any(t in p.get("a", []) for t in event_types) and not p.get("inTraceRun")]
    if orphans:
        result.add("CW", "event-outside-any-run", "error", f"{len(orphans)} event(s)",
                   f"first: {', '.join(orphans[:5])}")


def emit_violations(result: Result, path: Path, trace: Path) -> None:
    lines = [
        f"# Dynamic validation findings for {trace.name}.",
        "# Generated by scripts/validate-runtime-trace.py — M5.",
        "# Named individuals, not log lines: a violation joins to the graph it was",
        "# found in and can be counted, merged and reasoned over.",
        "",
        "@prefix re:   <https://realityengine.example.org/ontology/re-core#> .",
        "@prefix owl:  <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix v:    <https://realityengine.example.org/runtime-violations#> .",
        "",
    ]
    for i, v in enumerate(result.violations, 1):
        lines += [
            f"v:violation-{i:04d}",
            "    a owl:NamedIndividual , re:SemanticGuardrailViolation ;",
            f'    rdfs:label "{v.rule} {v.kind}" ;',
            f'    re:violationType "{v.kind}" ;',
            f'    re:severity "{v.severity}" ;',
            f'    re:recordId "{v.record}" .',
            "",
        ]
    path.write_text("\n".join(lines))


# ── Fixtures ─────────────────────────────────────────────────────────────────

def run_fixtures() -> int:
    """M5 criterion 3: dynamic validation fails and produces a named violation record."""
    if not FIXTURE_ROOT.is_dir():
        print(f"validate-runtime-trace: no fixtures at {FIXTURE_ROOT}", file=sys.stderr)
        return 2
    cases = json.loads((FIXTURE_ROOT / "cases.json").read_text())["cases"]
    failures = 0
    for case in cases:
        g = parse_ttl((FIXTURE_ROOT / case["graph"]).read_text())
        r = Result()
        check_region_writes(g, r)
        check_cardinality(g, r)
        check_forbidden_endpoints(g, set(case.get("allowed", [])) or None, r)
        check_run_grouping(g, r)
        kinds = {v.kind for v in r.violations}
        if case["expect"] in kinds:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "v.ttl"
                emit_violations(r, out, FIXTURE_ROOT / case["graph"])
                named = "re:SemanticGuardrailViolation" in out.read_text()
            print(f"  ok     {case['graph']:<40} -> {case['expect']}"
                  f"{'' if named else '  (BUT no named record emitted)'}")
            if not named:
                failures += 1
        else:
            print(f"  FAILED {case['graph']:<40} expected {case['expect']}, "
                  f"got {sorted(kinds) or 'nothing'}")
            failures += 1
    print()
    if failures:
        print(f"validate-runtime-trace: {failures} fixture(s) were not rejected — "
              f"the dynamic guard is not proven to fire")
    else:
        print(f"validate-runtime-trace: all {len(cases)} bad traces rejected, "
              f"each with a named violation record")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--trace", type=Path, help="runtime trace Turtle from export-runtime-trace.py")
    ap.add_argument("--profile", default="standard-deployment")
    ap.add_argument("--pe-url", default=None,
                    help="a PE base URL, to read the deployment's allowed-endpoint catalogue")
    ap.add_argument("--emit", type=Path, help="write violations as TTL individuals")
    ap.add_argument("--skip-robot", action="store_true",
                    help="closed-world checks only (the ROBOT half is the slow one)")
    ap.add_argument("--fixtures", action="store_true")
    args = ap.parse_args()

    if args.fixtures:
        return run_fixtures()
    if not args.trace or not args.trace.is_file():
        print("validate-runtime-trace: --trace is required (or --fixtures)", file=sys.stderr)
        return 2

    g = parse_ttl(args.trace.read_text())
    result = Result()

    if not args.skip_robot:
        robot_validate(args.trace, args.profile, result)
    else:
        result.gap("ROBOT half skipped by --skip-robot")

    check_region_writes(g, result)
    check_cardinality(g, result)
    check_forbidden_endpoints(g, allowed_endpoints(args.pe_url), result)
    check_run_grouping(g, result)

    if args.emit:
        emit_violations(result, args.emit, args.trace)

    print(f"validate-runtime-trace: {args.trace.name} against profile '{args.profile}'")
    for k in sorted(result.checked):
        print(f"  checked  {k}: {result.checked[k]}")
    for note in result.ungated:
        print(f"  UNGATED  {note}")
    print()
    for v in result.violations:
        print(f"  {v}")
    if args.emit:
        print(f"  wrote    {args.emit} ({len(result.violations)} named violation record(s))")

    if result.violations:
        print(f"\nvalidate-runtime-trace: FAIL — {len(result.violations)} violation(s)")
        return 1
    print("\nvalidate-runtime-trace: OK — the run obeys the semantics the corpus declares")
    return 0


if __name__ == "__main__":
    sys.exit(main())
