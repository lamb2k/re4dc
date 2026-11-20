#!/usr/bin/env python3
"""svc_cost.py: operations and memory touched per actor per tick, the original units against the native services
(lane eng-svc; docs/engine/SERVICES.md "Cost indicator"). PC counts, no timing.

    svc_cost.py <reference census dir> <native census dir> [--md out.md] [--json out.json]

Both directories are census runs with RE4_SVC_TRACE=1 over the same fixture and tick window (census.py's
census.json in each). For every actor and service (skeleton: the skeleton entry points, IK and the palette;
collision: the collision entry points), per traced tick:
  calls       boundary calls into the service (from behaviour, host and the other services)
  helpers     math helper calls made inside it, by kind: matrix x matrix (PSMTXConcat, and the native chain kernel's
              apply), matrix x vector, inverse, quaternion, trigonometry (sinf / cosf / acosf), key segments (hermite)
  accesses    loads and stores to guest and service memory made inside it (every one, traced)
  lines       distinct 32-byte lines those touch per tick (the SH-4 operand cache line), by region: parts records,
              character / object records, archives (keys, collision files), the native tables
"""
import collections
import json
import sys

HELPER_KIND = {
    "PSMTXConcat": "mtx x mtx", "skel_xm_apply_3x4": "mtx x mtx", "skel_xm_apply_scale": "mtx col scale",
    "PSMTXMultVec": "mtx x vec", "PSMTXMultVecSR": "mtx x vec", "skel_xm_point3": "mtx x vec",
    "PSMTXInverse": "inverse", "C_QUATMtx": "quaternion", "C_QUATSlerp": "quaternion", "PSMTXQuat": "quaternion",
    "sinf": "trig", "cosf": "trig", "acosf": "trig", "hermite": "key segment", "skel_xm_load_3x4": "xmtrx load",
    "PSMTXCopy": "mtx copy", "memcpy": "mem copy", "memset": "mem clear", "memclr_asm": "mem clear",
}
SERVICE_OF_UNIT = {"skeleton": "skeleton", "collision": "collision", "cloth": "cloth"}


def svc_of(entry_unit_kind):
    return SERVICE_OF_UNIT.get(entry_unit_kind)


def load(d):
    j = json.load(open(d + "/census.json"))
    traced = None
    for line in open(d + "/mem.tsv"):
        if line.startswith("# ticks"):
            traced = int(line.split("\t")[1])
            break
    return j, traced


def table(j, traced):
    ticks = j["ticks"]
    out = collections.defaultdict(lambda: collections.Counter())
    for r in j["boundary"]:
        s = r["service"]
        if s in ("skeleton", "collision"):
            out[(r["actor"], s)]["calls"] += r["calls"] / ticks
    # helpers: the outermost service entry (ctx) gives the service; the census names helpers demangled
    unit_kind = {}
    for r in j["boundary"] + j["nested"]:
        unit_kind[r["entry"]] = r["service"]
    for r in j["mem"]:
        unit_kind.setdefault(r["ctx"], r["ctx_kind"])
    for r in j["helpers"]:
        s = unit_kind.get(r["ctx"])
        if s not in ("skeleton", "collision"):
            continue
        name = r["helper"].split("(")[0]
        k = HELPER_KIND.get(name)
        if k:
            out[(r["actor"], s)]["h:" + k] += r["calls"] / ticks
    for r in j["mem"]:
        s = r["ctx_kind"]
        if s not in ("skeleton", "collision"):
            continue
        out[(r["actor"], s)]["accesses"] += r["acc_per_tick"]
        out[(r["actor"], s)]["lines"] += r["lines_per_tick"]
        out[(r["actor"], s)]["lines:" + r["region"]] += r["lines_per_tick"]
    return out


def main():
    a, b = sys.argv[1], sys.argv[2]
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    js = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    ja, ta = load(a)
    jb, tb = load(b)
    A, Bn = table(ja, ta), table(jb, tb)
    keys = sorted(set(A) | set(Bn), key=lambda k: (k[1], k[0]))
    cols = ["calls", "accesses", "lines", "lines:parts", "lines:em", "lines:obj", "lines:chr", "lines:room", "lines:svc",
            "lines:heap", "h:mtx x mtx", "h:mtx col scale", "h:mtx x vec", "h:inverse", "h:quaternion", "h:trig",
            "h:key segment", "h:xmtrx load", "h:mtx copy", "h:mem copy", "h:mem clear"]
    rows = []
    for k in keys:
        ra, rb = A.get(k, {}), Bn.get(k, {})
        rows.append({"actor": k[0], "service": k[1], "ref": {c: ra.get(c, 0.0) for c in cols}, "native": {c: rb.get(c, 0.0) for c in cols}})
    if js:
        json.dump({"ref": a, "native": b, "ticks_ref": ja["ticks"], "traced_ref": ta, "ticks_native": jb["ticks"],
                   "traced_native": tb, "rows": rows}, open(js, "w"), indent=1)
    lines = ["Per actor per tick (traced ticks: reference %s, native %s); reference / native" % (ta, tb), "",
             "| Actor | Service | Calls | Accesses | Lines (32 B) | of which records (parts + model) | archives | native tables | mtx x mtx | mtx x vec | inverse | quaternion | trig | key segments |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        x, y = r["ref"], r["native"]
        def p(c, f="%.0f"):
            return (f % x[c]) + " / " + (f % y[c])
        rec = lambda d: d["lines:parts"] + d["lines:em"] + d["lines:obj"]
        arc = lambda d: d["lines:chr"] + d["lines:room"]
        lines.append("| %s | %s | %s | %s | %s | %.0f / %.0f | %.0f / %.0f | %.0f / %.0f | %s | %s | %s | %s | %s | %s |" % (
            r["actor"], r["service"], p("calls", "%.1f"), p("accesses"), p("lines"), rec(x), rec(y), arc(x), arc(y),
            x["lines:svc"], y["lines:svc"], p("h:mtx x mtx", "%.1f"), p("h:mtx x vec", "%.1f"), p("h:inverse", "%.1f"),
            p("h:quaternion", "%.1f"), p("h:trig", "%.1f"), p("h:key segment", "%.1f")))
    text = "\n".join(lines) + "\n"
    if md:
        open(md, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
