#!/usr/bin/env python3
"""Verify the ai-governance-regime candidate machines, offline.

    python3 tools/verify_machines.py

Runs the repository's own gates against machines/ (not against the runtime
corpus, which these candidates are not part of):
  * schema   - schemas/machine.schema.json via Ajv (tools/validate_schema.mjs);
  * pattern  - scripts/check-one-ces-one-pattern.py: every CES its own regular
               expression, no input expecting two outputs;
  * clone    - scripts/cloneable_machines.py's recognition rule: every template
               cloneable, every fixture and the aggregator not;
and adds the package's own:
  * shape    - one initial event and one event without successors per CES (the
               corpus's measured shape), element count = input length, output
               vectors = output length;
  * regions  - inside the proposed band, no overlap between machines, nothing in
               a reserved range or under an existing corpus region;
  * names    - filenames unique against the runtime corpus, GOV prefix free;
  * build    - machines/ is byte-identical to tools/build_machines.py output;
  * replay   - every fixture reproduces its expectedOutputsByStep under the
               SURFACE_SPEC transition rule (authoring evaluator; the engines,
               3-of-3, remain the authority).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
REPO = PKG.parents[2]
MACHINES = PKG / "machines"
BAND = (16960, 17430)  # [16960:17429], scope-decisions.json GOV-SD-05


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    failures: list[str] = []
    docs = {p: json.loads(p.read_text()) for p in sorted(MACHINES.glob("*.json"))}

    # schema
    r = subprocess.run(["node", str(PKG / "tools" / "validate_schema.mjs"), str(REPO)],
                       capture_output=True, text=True)
    for ln in r.stdout.strip().splitlines():
        if ln.startswith(("schema:", "behaviors:")):
            print(ln)
    if not r.stdout.strip():
        print(r.stderr.strip())
    if r.returncode:
        failures += [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")] or ["schema validation failed"]

    # pattern
    one = load("one_ces", REPO / "scripts" / "check-one-ces-one-pattern.py")
    found = one.violations(MACHINES)
    print(f"pattern: {len(found)} violation(s) (scripts/check-one-ces-one-pattern.py)")
    failures += found

    # clone
    cm = load("cloneable_machines", REPO / "scripts" / "cloneable_machines.py")
    space = cm.load_space()
    machines = {p: d["machine"] for p, d in docs.items()}
    targets = cm.bus_targets(machines)
    n_clone = 0
    for p, m in machines.items():
        ok, reason = cm.assess(p, m, targets, space)
        kind = (m["metadata"].get("governanceSpec") or {}).get("kind", "aggregator")
        if kind == "template" and not ok:
            failures.append(f"{p.name}: template is not cloneable ({reason})")
        if kind != "template" and ok:
            failures.append(f"{p.name}: {kind} is cloneable ({reason})")
        n_clone += ok
    print(f"clone: {n_clone} cloneable of {len(machines)} (scripts/cloneable_machines.py rule)")

    # shape
    for p, m in machines.items():
        lin = m["perceptualMapping"]["input"]["length"]
        lout = m["perceptualMapping"]["output"]["length"]
        for s in m["sequences"]:
            evs = s["events"]
            if sum(1 for e in evs if e.get("isInitial")) != 1 or sum(1 for e in evs if not e.get("nextEventIds")) != 1:
                failures.append(f"{p.name}: {s['id']} is not one initial and one terminal event")
            for e in evs:
                if len(e["elements"]) != lin:
                    failures.append(f"{p.name}: {e['id']} has {len(e['elements'])} elements for input length {lin}")
                for o in e.get("outputEvents", []):
                    if len(o["vector"]) != lout:
                        failures.append(f"{p.name}: {o['id']} vector length {len(o['vector'])} != {lout}")
        for f in m.get("inputSequences", []):
            if any(len(ev) != lin for ev in f["events"]):
                failures.append(f"{p.name}: fixture {f['name']} has an event of the wrong length")
    print("shape: checked")

    # contracts: lanes, clone exit, agents
    lengths = {}
    behaviors = {p.name: json.loads(p.read_text())
                 for p in (PKG / "agent-candidates" / "ai-governance-regime").glob("*.agent.json")}
    for p, m in machines.items():
        md = m["metadata"]
        kind = (md.get("governanceSpec") or {}).get("kind", "aggregator")
        for s in m["sequences"]:
            lengths[len(s["events"])] = lengths.get(len(s["events"]), 0) + 1
        reserved = [i for i, s in enumerate(md.get("inputSemantics", [])) if s.lower().startswith("reserved")]
        if kind == "template" and reserved != [2, 3, 4, 5, 6, 7]:
            failures.append(f"{p.name}: template reserves {reserved}, not the lifecycle lanes 2-7")
        if kind != "template" and reserved:
            failures.append(f"{p.name}: {kind} reserves cells {reserved}")
        edges = md.get("interconnections", [])
        if kind == "template" and any(e["type"] == "published-domain-bus-producer" for e in edges):
            failures.append(f"{p.name}: a template publishes on a bus; a clone leaves only by continuation or termination")
        ab = md.get("agentBinding")
        if ab:
            ids = {s["id"] for s in m["sequences"]}
            if ab["trigger"] not in ids:
                failures.append(f"{p.name}: agent trigger {ab['trigger']} is not a CES")
            wr, ir = ab["writeBack"]["region"], m["perceptualMapping"]["input"]
            if not (ir["offset"] <= wr["offset"] and wr["offset"] + wr["length"] <= ir["offset"] + ir["length"]):
                failures.append(f"{p.name}: completion region is outside the input")
            beh = behaviors.get(f"{ab['agent']}.agent.json")
            if beh is None:
                failures.append(f"{p.name}: no agent behavior for {ab['agent']}")
            elif beh["agentBinding"] != ab:
                failures.append(f"{p.name}: agent behavior's binding differs from the machine's")
            elif not set(beh["dispatch"]["triggerSequenceIds"]) <= {s["id"] for s in m["sequences"]}:
                failures.append(f"{p.name}: behavior dispatch names a CES the machine lacks")
        elif kind != "aggregator" and p.name != "GOV08_latency-gate-sentinel.json":
            failures.append(f"{p.name}: no agentBinding")
    print("contracts: lanes 2-7 on templates, no template bus edges, agent triggers, completion lanes, behaviors")
    print("ces lengths: " + ", ".join(f"{k}: {v}" for k, v in sorted(lengths.items())))

    # regions
    spans = []
    for p, m in machines.items():
        for role in ("input", "output"):
            reg = m["perceptualMapping"][role]
            a, b = reg["offset"], reg["offset"] + reg["length"]
            if not (BAND[0] <= a and b <= BAND[1]):
                failures.append(f"{p.name}: {role} [{a}:{b - 1}] outside the band")
            spans.append((a, b, f"{p.name} {role}"))
    spans.sort()
    for (_a1, b1, n1), (a2, _b2, n2) in zip(spans, spans[1:]):
        if a2 < b1:
            failures.append(f"overlap: {n1} and {n2}")
    alloc = json.loads((REPO / "domains" / "region-allocation.json").read_text())
    for band in alloc.get("reservedBands", []):
        a, b = band["offset"], band["offset"] + band["length"]
        if a < BAND[1] and BAND[0] < b:
            failures.append(f"band overlaps reserved range {band['id']}")
    corpus_max = 0
    names = set()
    for cp in (REPO / "machines").rglob("*.json"):
        names.add(cp.name)
        try:
            pm = json.loads(cp.read_text())["machine"]["perceptualMapping"]
        except (KeyError, TypeError, ValueError):
            continue
        for role in ("input", "output"):
            reg = pm.get(role) or {}
            if "offset" in reg:
                corpus_max = max(corpus_max, reg["offset"] + reg.get("length", 0))
    if corpus_max > BAND[0]:
        failures.append(f"the runtime corpus reaches cell {corpus_max}, inside the band")
    print(f"regions: band [{BAND[0]}:{BAND[1] - 1}], corpus ends at {corpus_max}, clone space at 20480")

    # names
    clash = [p.name for p in machines if p.name in names]
    failures += [f"filename already in the corpus: {n}" for n in clash]
    prefixes = {pre for d in json.loads((REPO / "domains" / "domain-manifest.json").read_text())["domains"].values()
                for pre in d.get("codePrefixes", [])}
    if any("GOV".startswith(x) or x.startswith("GOV") for x in prefixes):
        failures.append("code prefix GOV collides with an existing domain prefix")
    print(f"names: {len(machines)} unique; prefix GOV free")

    # build
    b = subprocess.run([sys.executable, str(PKG / "tools" / "build_machines.py"), "--check"],
                       capture_output=True, text=True)
    print(b.stdout.strip().splitlines()[-1])
    if b.returncode:
        failures.append("machines/ is not the builder's output")

    # replay
    bm = load("build_machines", PKG / "tools" / "build_machines.py")
    replayed = 0
    for p, m in machines.items():
        fb = m["metadata"].get("latchFeedback")
        for f in m.get("inputSequences", []):
            want = f["metadata"].get("expectedOutputsByStep") or [f["metadata"]["expectedOutputVector"]]
            if fb:
                trace = bm.run(m["sequences"], f["events"], fb["inputElement"], fb["fromOutputElement"])
            else:
                trace = bm.run(m["sequences"], f["events"])
            lout = m["perceptualMapping"]["output"]["length"]
            got = [t or [0.0] * lout for t in trace]
            if got != want:
                failures.append(f"{p.name}: fixture {f['name']} replays {got}, expects {want}")
            for ev in f["events"]:
                if fb and ev[fb["inputElement"]] not in (0.0, 1.0):
                    failures.append(f"{p.name}: fixture {f['name']} latch feedback not binary")
            replayed += 1
    print(f"replay: {replayed} fixtures")

    for line in failures:
        print(f"FAIL: {line}")
    print("PASS" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
