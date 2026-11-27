#!/usr/bin/env python3
"""Live run of the ai-governance-regime simulations on every engine (voters and followers).

For each engine pair: remove any resident GOV machine, register the 18 candidates
once (POST /api/machines, every declared region honoured), then for each simulation
in governance-sources.json:
  reset RE and PE, remove any source writing the governance band, create the
  simulation's simulated Sources, push `steps` times, and read the machine's output
  region from each step's perceptualSpace.

**The GOV-SA-06 feedback cell.** Its rule is a PE composition the engines do not
perform today: the PE writes the machine's previous LATCH output into the feedback
input element (GOV-R12). This probe stands in for that composition. It holds a
sensor Source on the feedback cell and, before each push, writes the LATCH value the
engine committed on the previous step (0 before the first). Results for those
simulations are labelled `feedback: harness-composed`.

Compares: voters 3-of-3, followers against the voters, and the voters against the
package's latched expectation.

Usage: python3 tools/live_probe.py --engine id=RE_URL,PE_URL[,role] ... --out DIR [--only a,b]
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import sys
import urllib.error
import urllib.request

PKG = pathlib.Path(__file__).resolve().parent.parent
PREFIX = "GOV"


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
    return {p.stem: json.loads(p.read_text())["machine"] for p in sorted((PKG / "machines").glob("*.json"))}


def band(ms):
    lo, hi = 10**9, 0
    for m in ms.values():
        for k in ("input", "output"):
            r = m["perceptualMapping"][k]
            lo, hi = min(lo, r["offset"]), max(hi, r["offset"] + r["length"])
    return lo, hi


def reg(d, k):
    return {x: (d.get(k) or d.get(k + "Region") or {}).get(x) for x in ("offset", "length")}


def resident(eng):
    _, body = call("GET", f"{eng['re']}/api/machines")
    lst = body if isinstance(body, list) else (body or {}).get("machines", [])
    return [(m.get("id"), m.get("name")) for m in lst if str(m.get("name", "")).startswith(PREFIX)]


def load_machines(eng, ms, log):
    gone = resident(eng)
    for mid, name in gone:
        st, _ = call("DELETE", f"{eng['re']}/api/machines/{mid}")
        if st >= 300:
            raise SystemExit(f"{eng['id']}: DELETE {name} -> {st}")
    if resident(eng):
        raise SystemExit(f"{eng['id']}: {PREFIX} machines still resident after delete")
    got = {}
    for stem, m in ms.items():
        st, body = call("POST", f"{eng['re']}/api/machines", m)
        if st >= 300:
            raise SystemExit(f"{eng['id']}: POST /api/machines {stem} -> {st} {str(body)[:300]}")
        rec = body.get("machine", body) if isinstance(body, dict) else {}
        pm = rec.get("perceptualMapping") or {}
        want = m["perceptualMapping"]
        ok = rec.get("name") == m["name"] and reg(pm, "input") == reg(want, "input") and reg(pm, "output") == reg(want, "output")
        got[stem] = {"name": rec.get("name"), "regionsHonoured": ok}
    log(f"{eng['id']}: removed {len(gone)}, registered {len(got)}, "
        f"regions honoured {sum(v['regionsHonoured'] for v in got.values())}")
    return got


def band_sources(eng, lo, hi):
    _, body = call("GET", f"{eng['pe']}/api/sources")
    srcs = body if isinstance(body, list) else (body or {}).get("sources", [])
    out = []
    for s in srcs:
        r = s.get("region") or {}
        o, n = r.get("offset", -1), r.get("length", 0)
        if o < hi and o + n > lo:
            out.append(s["id"])
    return out


def run_sim(eng, sim, m, lo, hi):
    for path, url in (("/api/engine/reset", eng["re"]), ("/api/reset", eng["pe"])):
        st, b = call("POST", url + path, {})
        if st >= 300:
            return {"error": f"reset {path} -> {st} {str(b)[:200]}"}
    for sid in band_sources(eng, lo, hi):
        call("DELETE", f"{eng['pe']}/api/sources/{sid}")
    created = []
    for s in sim["sources"]:
        st, b = call("POST", f"{eng['pe']}/api/sources", s)
        if st >= 300:
            return {"error": f"create source {s['id']} -> {st} {str(b)[:200]}"}
        created.append(s["id"])
    out = m["perceptualMapping"]["output"]
    o, n = out["offset"], out["length"]
    fb = m["metadata"].get("latchFeedback")
    sensor = None
    if sim.get("feedbackCell") is not None and fb:
        sensor = f"gov-probe-feedback-{sim['name']}"
        st, b = call("POST", f"{eng['pe']}/api/sources",
                     {"type": "sensor", "id": sensor, "name": f"feedback ({sim['name']})", "sensorId": sensor,
                      "region": {"offset": sim["feedbackCell"], "length": 1}})
        if st >= 300:
            return {"error": f"create feedback sensor -> {st} {str(b)[:200]}"}
        created.append(sensor)
    trace, prev_latch = [], 0.0
    for _ in range(sim["steps"]):
        if sensor:
            st, b = call("POST", f"{eng['pe']}/api/sensors/{sensor}", {"values": [prev_latch]})
            if st >= 300:
                return {"error": f"feedback write -> {st} {str(b)[:200]}", "trace": trace}
        st, b = call("POST", f"{eng['pe']}/api/push", {"includeMachineResults": False, "includeActiveRegions": False})
        if st >= 300:
            return {"error": f"push -> {st} {str(b)[:200]}", "trace": trace}
        step = b.get("step", b) if isinstance(b, dict) else {}
        space = step.get("perceptualSpace") or []
        if len(space) < o + n:
            return {"error": f"perceptualSpace has {len(space)} cells, output needs {o + n}", "trace": trace}
        row = [round(float(x), 4) for x in space[o:o + n]]
        trace.append(row)
        if fb:
            prev_latch = row[fb["fromOutputElement"]]
    for sid in created:
        call("DELETE", f"{eng['pe']}/api/sources/{sid}")
    return {"trace": trace, "feedback": "harness-composed" if sensor else None}


def binar(rows):
    return [[1 if x >= 0.5 else 0 for x in r] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only")
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
    by_name = {m["name"]: m for m in ms.values()}
    lo, hi = band(ms)
    sims = json.loads((PKG / "governance-sources.json").read_text())["simulations"]
    if a.only:
        keep = set(a.only.split(","))
        sims = [s for s in sims if s["name"] in keep]

    with cf.ThreadPoolExecutor(len(engines)) as ex:
        loaded = dict(zip([e["id"] for e in engines], ex.map(lambda e: load_machines(e, ms, log), engines)))

    def per_engine(eng):
        res = {}
        for sim in sims:
            r = run_sim(eng, sim, by_name[sim["machine"]], lo, hi)
            res[sim["name"]] = r
            if "error" in r:
                log(f"{eng['id']}: {sim['name']}: ERROR {r['error']}")
        log(f"{eng['id']}: {len(sims)} simulations run")
        return res

    with cf.ThreadPoolExecutor(len(engines)) as ex:
        results = dict(zip([e["id"] for e in engines], ex.map(per_engine, engines)))

    voters = [e["id"] for e in engines if e["role"] == "voter"]
    followers = [e["id"] for e in engines if e["role"] != "voter"]
    rows = []
    for sim in sims:
        n = sim["name"]
        errs = {e: results[e][n]["error"] for e in results if "error" in results[e][n]}
        traces = {e: results[e][n].get("trace") for e in results}
        vt = {json.dumps(traces[v]) for v in voters if v not in errs}
        agree = not (set(errs) & set(voters)) and len(vt) == 1
        vtrace = traces[voters[0]] if agree else None
        exp = binar(sim["expectedOutputsByStep"])
        matches = vtrace is not None and binar(vtrace) == exp
        first = None
        if vtrace is not None and not matches:
            first = next(({"step": t, "engines": g, "expected": w} for t, (g, w) in enumerate(zip(binar(vtrace), exp))
                          if g != w), None)
        fol = {f: ("error" if f in errs else "not-compared" if vtrace is None
                   else "agrees" if traces[f] == vtrace else "differs") for f in followers}
        rows.append({"simulation": n, "machine": sim["machine"], "votersAgree": agree, "matchesExpected": matches,
                     "feedback": results[voters[0]][n].get("feedback"), "followers": fol, "errors": errs,
                     "firstDifferenceFromExpected": first})
    summary = {"simulations": len(rows), "votersAgree": sum(r["votersAgree"] for r in rows),
               "matchesExpected": sum(r["matchesExpected"] for r in rows),
               "feedbackHarnessComposed": sum(1 for r in rows if r["feedback"]),
               **{f"{f}.agrees": sum(r["followers"].get(f) == "agrees" for r in rows) for f in followers}}
    (out / "report.json").write_text(json.dumps({"engines": engines, "loaded": loaded, "simulations": rows,
                                                 "summary": summary}, indent=2))
    (out / "traces.json").write_text(json.dumps(results))
    log(json.dumps(summary))
    return 0 if summary["votersAgree"] == len(rows) == summary["matchesExpected"] else 1


if __name__ == "__main__":
    sys.exit(main())
