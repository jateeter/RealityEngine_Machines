#!/usr/bin/env python3
"""Verify the threat-dynamics candidate machines and their simulated Sources, offline.

    python3 tools/verify_machines.py

Runs the repository's own gates against machines/ (not against the runtime
corpus, which these candidates are not part of):
  * schema    - schemas/machine.schema.json via Ajv (tools/validate_schema.mjs);
  * pattern   - scripts/check-one-ces-one-pattern.py;
  * clone     - scripts/cloneable_machines.py's rule: nothing here is cloneable
                (every machine is an observer fixture);
and adds the package's own:
  * shape     - one initial and one terminal event per CES, element count =
                input length, output vectors = output length;
  * observe   - no output named as a decision (TD-SD-02), no latch, no agent;
  * regions   - inside the band, no overlap between machines, clear of
                ai-governance-regime's band, reserved ranges and the corpus;
  * names     - filenames unique against the corpus and ai-governance-regime,
                THR prefix free;
  * build     - machines/ and threat-sources.json are the builder's output;
  * replay    - every fixture reproduces its expectedOutputsByStep;
  * sources   - every simulation declares exactly one simulated Source per
                input cell, with a SURFACE_SPEC create body and a deterministic
                pattern; the ISRE it composes replays to expectedOutputsByStep;
                the published lanes name the cells ai-governance-regime reads;
  * coverage  - NISTAML.061-.067 each have a detector with an adversarial and a
                near-miss simulation, and every CES that confirms a threat, or
                gates, is fired by at least one simulation.
The engines (3-of-3) remain the authority for every expected output.
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
GOV = PKG.parent / "ai-governance-regime"
GOV_BAND = (16960, 17430)
DECISIONS = {"HALT_PROMOTION", "REVOKE_EPOCH", "PERMIT_DEPLOY", "TRIGGER_INCIDENT", "LATCH"}
CLASSES = [f"NISTAML.06{i}" for i in range(1, 8)]
SURFACE_KEYS = {"type", "id", "name", "region", "pattern", "frequency", "amplitude", "dcOffset"}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    failures: list[str] = []
    bm = load("td_build", PKG / "tools" / "build_machines.py")
    band = (bm.BAND[0], bm.BAND[1] + 1)
    docs = {p: json.loads(p.read_text()) for p in sorted(MACHINES.glob("*.json"))}
    machines = {p: d["machine"] for p, d in docs.items()}

    # schema
    r = subprocess.run(["node", str(PKG / "tools" / "validate_schema.mjs"), str(REPO)], capture_output=True, text=True)
    for ln in r.stdout.strip().splitlines():
        if ln.startswith("schema:"):
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
    targets = cm.bus_targets(machines)
    n_clone = 0
    for p, m in machines.items():
        ok, reason = cm.assess(p, m, targets, space)
        if ok:
            failures.append(f"{p.name}: an observer is cloneable ({reason})")
        n_clone += ok
    print(f"clone: {n_clone} cloneable of {len(machines)} (scripts/cloneable_machines.py rule)")

    # shape + observe
    for p, m in machines.items():
        lin = m["perceptualMapping"]["input"]["length"]
        lout = m["perceptualMapping"]["output"]["length"]
        md = m["metadata"]
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
        outs = {s.split(": ", 1)[1] for s in md.get("outputSemantics", [])}
        if outs & DECISIONS:
            failures.append(f"{p.name}: outputs a decision {sorted(outs & DECISIONS)} (TD-SD-02: observe, never decide)")
        if md.get("agentBinding") or md.get("latchFeedback") or md.get("dispatchableAgent"):
            failures.append(f"{p.name}: carries an agent or a latch; threat-dynamics observes only")
        if not (md.get("threatSpec") or {}).get("observeOnly"):
            failures.append(f"{p.name}: threatSpec.observeOnly is not set")
    print("shape: checked; observe: no decision outputs, no agents, no latches")

    # regions
    spans = []
    for p, m in machines.items():
        for role in ("input", "output"):
            reg = m["perceptualMapping"][role]
            a, b = reg["offset"], reg["offset"] + reg["length"]
            if not (band[0] <= a and b <= band[1]):
                failures.append(f"{p.name}: {role} [{a}:{b - 1}] outside the band")
            spans.append((a, b, f"{p.name} {role}"))
    spans.sort()
    for (_a1, b1, n1), (a2, _b2, n2) in zip(spans, spans[1:]):
        if a2 < b1:
            failures.append(f"overlap: {n1} and {n2}")
    if band[0] < GOV_BAND[1] and GOV_BAND[0] < band[1]:
        failures.append("band overlaps ai-governance-regime's [16960:17429]")
    alloc = json.loads((REPO / "domains" / "region-allocation.json").read_text())
    for rb in alloc.get("reservedBands", []):
        a, b = rb["offset"], rb["offset"] + rb["length"]
        if a < band[1] and band[0] < b:
            failures.append(f"band overlaps reserved range {rb['id']}")
    corpus_max, names = 0, set()
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
    if corpus_max > band[0]:
        failures.append(f"the runtime corpus reaches cell {corpus_max}, inside the band")
    print(f"regions: band [{band[0]}:{band[1] - 1}], governance [16960:17429], corpus ends at {corpus_max}, clone space at 20480")

    # names
    names |= {p.name for p in (GOV / "machines").glob("*.json")}
    failures += [f"filename already used: {p.name}" for p in machines if p.name in names]
    prefixes = {pre for d in json.loads((REPO / "domains" / "domain-manifest.json").read_text())["domains"].values()
                for pre in d.get("codePrefixes", [])} | {"GOV"}
    if any("THR".startswith(x) or x.startswith("THR") for x in prefixes):
        failures.append("code prefix THR collides with an existing domain prefix")
    print(f"names: {len(machines)} unique; prefix THR free")

    # build
    b = subprocess.run([sys.executable, str(PKG / "tools" / "build_machines.py"), "--check"], capture_output=True, text=True)
    print(b.stdout.strip().splitlines()[-1] if b.stdout.strip() else b.stderr.strip())
    if b.returncode:
        failures.append("machines/ or threat-sources.json is not the builder's output")

    # replay
    replayed = 0
    for p, m in machines.items():
        lout = m["perceptualMapping"]["output"]["length"]
        for f in m.get("inputSequences", []):
            want = f["metadata"].get("expectedOutputsByStep") or [f["metadata"]["expectedOutputVector"]]
            got = [t or [0.0] * lout for t in bm.run(m["sequences"], f["events"])]
            if got != want:
                failures.append(f"{p.name}: fixture {f['name']} replays {got}, expects {want}")
            replayed += 1
    print(f"replay: {replayed} fixtures")

    # sources
    ts = json.loads((PKG / "threat-sources.json").read_text())
    by_id = {m["id"]: m for m in machines.values()}
    fired_by_machine: dict[str, set] = {}
    sims_by_machine: dict[str, set] = {}
    for sim in ts["simulations"]:
        m = by_id.get(sim["machine"])
        if m is None:
            failures.append(f"simulation {sim['name']}: no machine {sim['machine']}")
            continue
        inp = m["perceptualMapping"]["input"]
        cells = sorted(s["region"]["offset"] for s in sim["sources"])
        if cells != list(range(inp["offset"], inp["offset"] + inp["length"])):
            failures.append(f"simulation {sim['name']}: Sources cover {cells}, not one per input cell")
        for s in sim["sources"]:
            if s.get("type") != "simulated" or set(s) != SURFACE_KEYS or s["region"].get("length") != 1:
                failures.append(f"simulation {sim['name']}: {s.get('id')} is not a one-cell SURFACE_SPEC simulated create body")
            if s.get("pattern") not in ts["simulationRule"]["patterns"]:
                failures.append(f"simulation {sim['name']}: {s.get('id')} pattern {s.get('pattern')} is not deterministic")
        fired = set()
        trace = bm.run(m["sequences"], bm.compose(sim["sources"], inp, sim["steps"]), fired)
        lout = m["perceptualMapping"]["output"]["length"]
        if [t or [0.0] * lout for t in trace] != sim["expectedOutputsByStep"]:
            failures.append(f"simulation {sim['name']}: the composed ISRE does not replay expectedOutputsByStep")
        if sorted(fired) != sim["cesFired"]:
            failures.append(f"simulation {sim['name']}: fires {sorted(fired)}, records {sim['cesFired']}")
        fired_by_machine.setdefault(m["id"], set()).update(fired)
        sims_by_machine.setdefault(m["id"], set()).add(sim["class"])
    gov = {s["signal"]: s for s in json.loads((GOV / "governance-sources.json").read_text())["signals"]}
    for lane in ts["publishedLanes"]:
        g = gov.get(lane["signal"])
        if g is None or g.get("producerDomain") != "threat-dynamics":
            failures.append(f"lane {lane['signal']}: ai-governance-regime does not consume it from threat-dynamics")
        elif g["consumers"] != lane["governanceConsumers"]:
            failures.append(f"lane {lane['signal']}: governance consumers differ from governance-sources.json")
    moved = {n for n, s in gov.items() if s.get("producerDomain") == "threat-dynamics"}
    if moved != {lane["signal"] for lane in ts["publishedLanes"]}:
        failures.append(f"governance expects {sorted(moved)} from threat-dynamics; published {[l['signal'] for l in ts['publishedLanes']]}")
    print(f"sources: {len(ts['simulations'])} simulations replayed through composed ISREs; "
          f"{len(ts['publishedLanes'])} lanes match governance-sources.json")

    # coverage
    for cls in CLASSES:
        det = [m for m in machines.values() if (m["metadata"].get("threatSpec") or {}).get("attackClass") == cls]
        if len(det) != 1:
            failures.append(f"{cls}: {len(det)} detectors")
            continue
        have = sims_by_machine.get(det[0]["id"], set())
        for need in ("adversarial", "near-miss"):
            if need not in have:
                failures.append(f"{cls}: no {need} simulation")
    unfired = []
    for m in machines.values():
        if m["id"].startswith("THR00"):
            continue
        for s in m["sequences"]:
            obs = s["metadata"].get("observation", [])
            if ("THREAT_CONFIRMED" in obs or "GATE_PASS" in obs or "GATE_FAIL" in obs) and \
                    s["id"] not in fired_by_machine.get(m["id"], set()):
                unfired.append(s["id"])
    failures += [f"coverage: {sid} is never fired by a simulation" for sid in unfired]
    print(f"coverage: {len(CLASSES)} classes with adversarial and near-miss simulations; "
          f"every confirming and gate CES fired" if not unfired else f"coverage: {len(unfired)} unfired")

    for line in failures:
        print(f"FAIL: {line}")
    print("PASS" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
