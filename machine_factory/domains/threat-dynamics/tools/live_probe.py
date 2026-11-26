#!/usr/bin/env python3
"""Live run of the threat-dynamics simulations on every engine (voters and followers).

For each engine pair: register the 11 THR candidate machines on the RE (POST /api/machines,
declared regions honoured), then for each of the 45 simulations in threat-sources.json:
reset RE and PE, remove any source writing the THR band, create the simulation's simulated
Sources on the PE, push SIM_STEPS steps, and read the machine's output region from each
step's perceptualSpace. Compare voters 3-of-3, followers against the voters, and the voters
against the package's offline expectation.

Usage: python3 tools/live_probe.py --engine id=RE_URL,PE_URL[,role] ... --out DIR
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import sys
import urllib.error
import urllib.request

PKG = pathlib.Path(__file__).resolve().parent.parent
BAND = (17440, 17760)


def call(method, url, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")[:500]


def machines():
    out = {}
    for p in sorted((PKG / "machines").glob("*.json")):
        out[p.stem] = json.loads(p.read_text())["machine"]
    return out


def resident_thr(eng):
    st, body = call("GET", f"{eng['re']}/api/machines")
    lst = body if isinstance(body, list) else (body or {}).get("machines", [])
    return [(m.get("id"), m.get("name")) for m in lst if str(m.get("name", "")).startswith("THR")]


def load_machines(eng, ms, log):
    gone = resident_thr(eng)
    for mid, name in gone:
        st, _ = call("DELETE", f"{eng['re']}/api/machines/{mid}")
        if st >= 300:
            raise SystemExit(f"{eng['id']}: DELETE {name} -> {st}")
    left = resident_thr(eng)
    if left:
        raise SystemExit(f"{eng['id']}: THR machines still resident after delete: {left}")
    log(f"{eng['id']}: removed {len(gone)} resident THR machine(s)")
    got = {}
    for stem, m in ms.items():
        st, body = call("POST", f"{eng['re']}/api/machines", m)
        if st >= 300:
            raise SystemExit(f"{eng['id']}: POST /api/machines {stem} -> {st} {str(body)[:300]}")
        rec = body.get("machine", body) if isinstance(body, dict) else {}
        name = rec.get("name")
        pm = rec.get("perceptualMapping") or {}
        want = m["perceptualMapping"]
        def reg(d, k):
            return {x: (d.get(k) or d.get(k + "Region") or {}).get(x) for x in ("offset", "length")}
        ok = name == m["name"] and reg(pm, "input") == reg(want, "input") and reg(pm, "output") == reg(want, "output")
        got[stem] = {"name": name, "regionsHonoured": ok, "perceptualMapping": pm}
        log(f"{eng['id']}: loaded {stem} as {name!r} regions {'ok' if ok else 'MOVED ' + json.dumps(pm)}")
    return got


def band_sources(eng):
    st, body = call("GET", f"{eng['pe']}/api/sources")
    srcs = body if isinstance(body, list) else (body or {}).get("sources", [])
    hits = []
    for s in srcs:
        r = s.get("region") or {}
        o, n = r.get("offset", -1), r.get("length", 0)
        if o < BAND[1] and o + n > BAND[0]:
            hits.append(s["id"])
    return hits


def step_space(body):
    step = body.get("step", body) if isinstance(body, dict) else {}
    return step.get("perceptualSpace") or []


def run_sim(eng, sim, out_region):
    for path, url in (("/api/engine/reset", eng["re"]), ("/api/reset", eng["pe"])):
        st, b = call("POST", url + path, {})
        if st >= 300:
            return {"error": f"reset {path} -> {st} {str(b)[:200]}"}
    for sid in band_sources(eng):
        call("DELETE", f"{eng['pe']}/api/sources/{sid}")
    for s in sim["sources"]:
        st, b = call("POST", f"{eng['pe']}/api/sources", s)
        if st >= 300:
            return {"error": f"create source {s['id']} -> {st} {str(b)[:200]}"}
    o, n = out_region["offset"], out_region["length"]
    trace = []
    for _ in range(sim["steps"]):
        st, b = call("POST", f"{eng['pe']}/api/push", {"includeMachineResults": False, "includeActiveRegions": False})
        if st >= 300:
            return {"error": f"push -> {st} {str(b)[:200]}", "trace": trace}
        space = step_space(b)
        if len(space) < o + n:
            return {"error": f"perceptualSpace has {len(space)} cells, output region needs {o + n}", "trace": trace}
        trace.append([round(float(x), 4) for x in space[o:o + n]])
    for s in sim["sources"]:
        call("DELETE", f"{eng['pe']}/api/sources/{s['id']}")
    return {"trace": trace}


def persist(rows):
    """Carry the last written vector through steps where nothing asserted (an all-zero row)."""
    out, last = [], None
    for r in rows:
        if any(r):
            last = r
        out.append(last if last is not None else r)
    return out


def binar(trace):
    return [[1 if x >= 0.5 else 0 for x in row] for row in trace]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma-separated simulation names")
    a = ap.parse_args()
    engines = []
    for spec in a.engine:
        eid, rest = spec.split("=", 1)
        parts = rest.split(",")
        engines.append({"id": eid, "re": parts[0].rstrip("/"), "pe": parts[1].rstrip("/"),
                        "role": parts[2] if len(parts) > 2 else "voter"})
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    logf = open(out / "probe.log", "a")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")
        logf.flush()

    ms = machines()
    src = json.loads((PKG / "threat-sources.json").read_text())
    sims = src["simulations"]
    if a.only:
        keep = set(a.only.split(","))
        sims = [s for s in sims if s["name"] in keep]
    outs = {stem: m["perceptualMapping"]["output"] for stem, m in ms.items()}

    loaded = {}
    with cf.ThreadPoolExecutor(len(engines)) as ex:
        for eng, got in zip(engines, ex.map(lambda e: load_machines(e, ms, log), engines)):
            loaded[eng["id"]] = got
    for eng in engines:
        st, state = call("GET", f"{eng['pe']}/api/state")
        log(f"{eng['id']}: PE perceptionDimension {state.get('perceptionDimension') if isinstance(state, dict) else state}")

    def per_engine(eng):
        res = {}
        for sim in sims:
            res[sim["name"]] = run_sim(eng, sim, outs[sim["machine"]])
            r = res[sim["name"]]
            log(f"{eng['id']}: {sim['name']}: {'ERROR ' + r['error'] if 'error' in r else 'ok'}")
        return res

    results = {}
    with cf.ThreadPoolExecutor(len(engines)) as ex:
        for eng, r in zip(engines, ex.map(per_engine, engines)):
            results[eng["id"]] = r

    voters = [e["id"] for e in engines if e["role"] == "voter"]
    followers = [e["id"] for e in engines if e["role"] != "voter"]
    rows = []
    for sim in sims:
        n = sim["name"]
        exp = binar(sim["expectedOutputsByStep"])
        traces = {e: results[e][n].get("trace") for e in results}
        errs = {e: results[e][n]["error"] for e in results if "error" in results[e][n]}
        vt = [json.dumps(traces[v]) for v in voters if v not in errs]
        voters_agree = len(errs.keys() & set(voters)) == 0 and len(set(vt)) == 1
        vtrace = traces[voters[0]] if voters_agree else None
        matches_expected = vtrace is not None and binar(vtrace) == exp
        matches_persistent = vtrace is not None and binar(vtrace) == persist(exp)
        fol = {}
        for f in followers:
            if f in errs:
                fol[f] = "error"
            elif vtrace is None:
                fol[f] = "not-compared"
            else:
                fol[f] = "agrees" if traces[f] == vtrace else "differs"
        first_diff = None
        if vtrace is not None and not matches_expected:
            for t, (g, w) in enumerate(zip(binar(vtrace), exp)):
                if g != w:
                    first_diff = {"step": t, "engines": g, "expected": w}
                    break
        rows.append({"simulation": n, "class": sim["class"], "machine": sim["machine"],
                     "votersAgree": voters_agree, "matchesExpected": matches_expected,
                     "matchesExpectedPersistent": matches_persistent,
                     "followers": fol, "errors": errs, "firstDifferenceFromExpected": first_diff})
    report = {"engines": engines, "loaded": loaded, "simulations": rows,
              "summary": {"simulations": len(rows),
                          "votersAgree": sum(r["votersAgree"] for r in rows),
                          "matchesExpected": sum(r["matchesExpected"] for r in rows),
                          "matchesExpectedPersistent": sum(r["matchesExpectedPersistent"] for r in rows),
                          **{f"{f}.agrees": sum(r["followers"].get(f) == "agrees" for r in rows) for f in followers}}}
    (out / "report.json").write_text(json.dumps(report, indent=2))
    (out / "traces.json").write_text(json.dumps(results))
    log(json.dumps(report["summary"]))
    return 0 if report["summary"]["votersAgree"] == len(rows) == report["summary"]["matchesExpected"] else 1


if __name__ == "__main__":
    sys.exit(main())
