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
    "PSMTXConcat": "concat", "skel_xm_apply_3x4": "xm apply", "skel_xm_apply_scale": "mtx col scale",
    "RotMatrix": "euler", "low_RotMatrix": "euler",
    "PSMTXMultVec": "mtx x vec", "PSMTXMultVecSR": "mtx x vec", "skel_xm_point3": "mtx x vec",
    "PSMTXInverse": "inverse", "C_QUATMtx": "quaternion", "C_QUATSlerp": "quaternion", "PSMTXQuat": "quaternion",
    "sinf": "trig", "cosf": "trig", "acosf": "trig", "hermite": "key segment", "skel_xm_load_3x4": "xmtrx load",
    "PSMTXCopy": "mtx copy", "memcpy": "mem copy", "memset": "mem clear", "memclr_asm": "mem clear",
    "PSVECNormalize": "vec normalize", "PSMTXRotAxisRad": "rot axis", "HermiteInterpolation": "key decode",
    "fRand0_1": "generator", "fRand1_1": "generator",
}
SERVICES = ("skeleton", "collision", "cloth")
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
        if s in SERVICES:
            out[(r["actor"], s)]["calls"] += r["calls"] / ticks
    # helpers: the outermost service entry (ctx) gives the service; the census names helpers demangled
    unit_kind = {}
    for r in j["boundary"] + j["nested"]:
        unit_kind[r["entry"]] = r["service"]
    for r in j["mem"]:
        unit_kind.setdefault(r["ctx"], r["ctx_kind"])
    for r in j["helpers"]:
        s = unit_kind.get(r["ctx"])
        if s not in SERVICES:
            continue
        name = r["helper"].split("(")[0].split(" ")[-1]
        k = HELPER_KIND.get(name)
        if k:
            out[(r["actor"], s)]["h:" + k] += r["calls"] / ticks
    for r in j["mem"]:
        s = r["ctx_kind"]
        if s not in SERVICES:
            continue
        out[(r["actor"], s)]["accesses"] += r["acc_per_tick"]
        out[(r["actor"], s)]["lines"] += r["lines_per_tick"]
        out[(r["actor"], s)]["lines:" + r["region"]] += r["lines_per_tick"]
    return out


def entries(j, service):
    """accesses and lines a tick per outermost entry point of a service (all actors)"""
    out = collections.Counter()
    lines = collections.Counter()
    for r in j["mem"]:
        if r["ctx_kind"] != service:
            continue
        name = r["ctx"].split("(")[0]
        out[name] += r["acc_per_tick"]
        lines[name] += r["lines_per_tick"]
    return out, lines


def kind_lines(d):
    """memk.tsv: distinct lines a tick per service kind and actor over every entry point, by region"""
    res = collections.defaultdict(collections.Counter)
    traced = 1
    for line in open(d + "/memk.tsv"):
        if line.startswith("# ticks"):
            traced = max(int(line.split("\t")[1]), 1)
            continue
        if line.startswith("#"):
            continue
        kind, actor, reg, acc, rd, wr, lsum, lmax, seen = line.rstrip("\n").split("\t")
        res[(kind, int(actor))][reg] += int(lsum) / traced
        res[(kind, int(actor))]["acc"] += int(acc) / traced
        res[(kind, int(actor))]["max"] = max(res[(kind, int(actor))]["max"], int(lmax))
    return res


def main():
    a, b = sys.argv[1], sys.argv[2]
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    js = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    ja, ta = load(a)
    jb, tb = load(b)
    A, Bn = table(ja, ta), table(jb, tb)
    keys = sorted(set(A) | set(Bn), key=lambda k: (k[1], k[0]))
    cols = ["calls", "accesses", "lines", "lines:parts", "lines:em", "lines:obj", "lines:chr", "lines:room", "lines:svc",
            "lines:heap", "h:concat", "h:xm apply", "h:euler", "h:mtx col scale", "h:mtx x vec", "h:inverse", "h:quaternion", "h:trig",
            "h:key segment", "h:xmtrx load", "h:mtx copy", "h:mem copy", "h:mem clear", "h:vec normalize", "h:rot axis",
            "h:key decode", "h:generator", "lines:mk"]
    rows = []
    for k in keys:
        ra, rb = A.get(k, {}), Bn.get(k, {})
        rows.append({"actor": k[0], "service": k[1], "ref": {c: ra.get(c, 0.0) for c in cols}, "native": {c: rb.get(c, 0.0) for c in cols}})
    if js:
        json.dump({"ref": a, "native": b, "ticks_ref": ja["ticks"], "traced_ref": ta, "ticks_native": jb["ticks"],
                   "traced_native": tb, "rows": rows}, open(js, "w"), indent=1)
    lines = ["Operations per actor per tick (all ticks of the run; reference / native)", "",
             "| Actor | Service | Boundary calls | Matrix x matrix: C library | XMTRX apply | XMTRX column scale | XMTRX load | Matrix x vector | Inverse | Quaternion | Trig (sin, cos, acos; 6 a rotation matrix) | Key decodes (HermiteInterpolation) | Key segments (hermite) | Normalize | Rotation about an axis | Generator |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        x, y = r["ref"], r["native"]
        if r["actor"] in ("-",) and x["calls"] == 0 and y["calls"] == 0:
            continue
        def p(c, f="%.1f"):
            return (f % x[c]) + " / " + (f % y[c])
        trig = lambda d: d["h:trig"] + 6 * d["h:euler"]
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %.1f / %.1f | %s | %s | %s | %s | %s |" % (
            r["actor"], r["service"], p("calls"), p("h:concat"), p("h:xm apply"), p("h:mtx col scale"), p("h:xmtrx load"),
            p("h:mtx x vec"), p("h:inverse"), p("h:quaternion"), trig(x), trig(y), p("h:key decode"), p("h:key segment"),
            p("h:vec normalize"), p("h:rot axis"), p("h:generator")))
    # distinct lines a tick per service kind and actor (every entry point together)
    ka, kb = kind_lines(a), kind_lines(b)
    names = {}
    for line in open(a + "/actors.tsv"):
        if not line.startswith("#"):
            c, pool, slot, ident, typ, nparts, first = line.split()
            names[int(c)] = "%s %s%s (%s bones)" % ({"00": "Leon", "03": "Ashley", "15": "Ganado", "16": "Ganado"}.get(ident, "id" + ident) if pool == "em" else {"03": "Ashley", "02": "handgun"}.get(ident, "obj" + ident), pool, slot, nparts)
    lines += ["", "Memory per actor per tick (traced ticks: reference %s, native %s; reference / native): loads and stores, and the distinct 32-byte lines they touch, every entry point of the service together" % (ta, tb), "",
              "| Actor | Service | Accesses | Lines | Records (parts + model) | Archives (keys, collision files) | Native tables | Baked motion keys | Most lines in one tick |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for key in sorted(set(ka) | set(kb), key=lambda k: (k[0], k[1])):
        if key[0] not in SERVICES:
            continue
        x, y = ka.get(key, collections.Counter()), kb.get(key, collections.Counter())
        tot = lambda d: sum(v for k, v in d.items() if k not in ("acc", "max"))
        rec = lambda d: d["parts"] + d["em"] + d["obj"]
        arc = lambda d: d["chr"] + d["room"] + d["core"]
        lines.append("| %s | %s | %.0f / %.0f | %.0f / %.0f | %.0f / %.0f | %.0f / %.0f | %.0f / %.0f | %.0f / %.0f | %d / %d |" % (
            names.get(key[1], "-" if key[1] == 250 else str(key[1])), key[0], x["acc"], y["acc"], tot(x), tot(y), rec(x), rec(y),
            arc(x), arc(y), x["svc"], y["svc"], x["mk"], y["mk"], x["max"], y["max"]))
    for svc in SERVICES:
        ea, la_ = entries(ja, svc)
        eb, lb_ = entries(jb, svc)
        lines += ["", "%s: accesses and lines a tick per outermost entry point (all actors; reference / native)" % svc, "",
                  "| Entry point | Accesses | Lines (per entry) |", "|---|---:|---:|"]
        for name in sorted(set(ea) | set(eb), key=lambda n: -(ea.get(n, 0) + eb.get(n, 0))):
            if ea.get(name, 0) + eb.get(name, 0) < 1:
                continue
            lines.append("| `%s` | %.0f / %.0f | %.0f / %.0f |" % (name, ea.get(name, 0), eb.get(name, 0), la_.get(name, 0), lb_.get(name, 0)))
    text = "\n".join(lines) + "\n"
    if md:
        open(md, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
