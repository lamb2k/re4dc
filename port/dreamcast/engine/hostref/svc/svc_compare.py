#!/usr/bin/env python3
"""svc_compare.py: the original skeleton and collision units against the native services, tick by tick
(lane eng-svc; docs/engine/SERVICES.md "Equivalence").

    svc_compare.py <reference dir> <native dir> [--json out.json] [--pos 1.0] [--deg 0.1] [--col 0.01]

Both directories hold what svc_dump.cpp writes (pal.bin, col.txt). Checks:
  bones      every live model with parts, every tick, every bone: world position and world matrix translation
             (units), the world matrix's three axes (degrees), the palette's translation (units) and axes (degrees)
  collision  every boundary collision query in call order: the same kind, manager and actor; integer results
             (hit, attribute, flags, normal pointer) exact; points and normals within --col units
Exit status 0 when every value is within tolerance (PASS), 1 otherwise (FAIL). The first divergence is reported.
"""
import json
import math
import struct
import sys

import numpy as np


def read_pal(path):
    data = open(path, "rb").read()
    ticks = {}
    off = 0
    rec = 27 * 4
    while off < len(data):
        magic, t = struct.unpack_from("<II", data, off)
        off += 8
        if magic != 0x4B434954:
            raise ValueError("pal.bin: bad tick header at %d" % off)
        models = {}
        while True:
            code, n = struct.unpack_from("<II", data, off)
            off += 8
            if code == 0x444E4524:
                break
            arr = np.frombuffer(data, dtype="<f4", count=27 * n, offset=off).reshape(n, 27)
            off += rec * n
            models[code] = arr
        ticks[t] = models
    return ticks


def axes_deg(a, b):
    """largest angle between corresponding matrix axes (columns of the 3x3), degrees; rows of a/b: 12 floats"""
    A = a[:, :12].reshape(-1, 3, 4)[:, :, :3]
    B = b[:, :12].reshape(-1, 3, 4)[:, :, :3]
    na = np.linalg.norm(A, axis=1)
    nb = np.linalg.norm(B, axis=1)
    dot = np.einsum("nij,nij->nj", A, B) / np.maximum(na * nb, 1e-30)
    dot = np.clip(dot, -1.0, 1.0)
    return np.degrees(np.arccos(dot)).max(axis=1)


def compare_bones(ra, rb, tol_pos, tol_deg):
    res = {"ticks": 0, "bones": 0, "bit_identical_bones": 0, "equal_bones": 0, "max_pos": 0.0, "max_deg": 0.0, "max_pal_pos": 0.0,
           "max_pal_deg": 0.0, "first": None, "over": 0, "missing": 0}
    for t in sorted(set(ra) | set(rb)):
        if t not in ra or t not in rb:
            res["missing"] += 1
            if res["first"] is None:
                res["first"] = {"tick": t, "what": "tick missing in one run"}
            continue
        res["ticks"] += 1
        ma, mb = ra[t], rb[t]
        for code in sorted(set(ma) | set(mb)):
            if code not in ma or code not in mb or ma[code].shape != mb[code].shape:
                res["missing"] += 1
                if res["first"] is None:
                    res["first"] = {"tick": t, "actor": code, "what": "model missing or bone count differs"}
                continue
            a, b = ma[code].astype(np.float64), mb[code].astype(np.float64)
            res["bones"] += a.shape[0]
            res["bit_identical_bones"] += int(np.all(ma[code].view("<u4") == mb[code].view("<u4"), axis=1).sum())
            # equal as numbers (+0 and -0 equal: the C matrix library and XMTRX differ only in the sign of exact zeros)
            res["equal_bones"] += int(np.all((ma[code] == mb[code]) | (np.isnan(ma[code]) & np.isnan(mb[code])), axis=1).sum())
            # world translation (matrix column 3), world position, palette translation
            ta = a[:, [3, 7, 11]]; tb = b[:, [3, 7, 11]]
            wa = a[:, 12:15]; wb = b[:, 12:15]
            pa = a[:, [18, 22, 26]]; pb = b[:, [18, 22, 26]]
            with np.errstate(invalid="ignore"):
                dpos = np.nan_to_num(np.maximum(np.abs(ta - tb).max(axis=1), np.abs(wa - wb).max(axis=1)), nan=1e30)
                dpal = np.nan_to_num(np.abs(pa - pb).max(axis=1), nan=1e30)
                ddeg = np.nan_to_num(axes_deg(a, b), nan=180.0)
                dpdeg = np.nan_to_num(axes_deg(a[:, 15:], b[:, 15:]), nan=180.0)
            res["max_pos"] = max(res["max_pos"], float(dpos.max()))
            res["max_deg"] = max(res["max_deg"], float(ddeg.max()))
            res["max_pal_pos"] = max(res["max_pal_pos"], float(dpal.max()))
            res["max_pal_deg"] = max(res["max_pal_deg"], float(dpdeg.max()))
            bad = (dpos > tol_pos) | (dpal > tol_pos) | (ddeg > tol_deg) | (dpdeg > tol_deg)
            res["over"] += int(bad.sum())
            if bad.any() and res["first"] is None:
                k = int(np.argmax(bad))
                res["first"] = {"tick": t, "actor": code, "bone": k, "pos": float(dpos[k]), "deg": float(ddeg[k]),
                                "pal_pos": float(dpal[k]), "pal_deg": float(dpdeg[k])}
    return res


def f32(h):
    return struct.unpack("<f", struct.pack("<I", int(h, 16)))[0]


def compare_col(pa, pb, tol):
    la = open(pa).read().splitlines()
    lb = open(pb).read().splitlines()
    res = {"queries_ref": len(la), "queries_native": len(lb), "compared": 0, "identical": 0, "max_point": 0.0,
           "kinds": {}, "first": None, "over": 0}
    for i, (x, y) in enumerate(zip(la, lb)):
        res["compared"] += 1
        tx, ty = x.split(), y.split()
        kind = tx[1] if len(tx) > 1 else "?"
        res["kinds"][kind] = res["kinds"].get(kind, 0) + 1
        if x == y:
            res["identical"] += 1
            continue
        bad = None
        if len(tx) != len(ty) or tx[:2] != ty[:2]:
            bad = "query differs"
        else:
            for u, v in zip(tx, ty):
                if u == v:
                    continue
                if "," in u:   # a vector: three floats
                    for p, q in zip(u.split(","), v.split(",")):
                        d = abs(f32(p) - f32(q))
                        if math.isnan(d):
                            d = 1e30
                        res["max_point"] = max(res["max_point"], d)
                        if d > tol:
                            bad = "point %s vs %s" % (u, v)
                elif len(u) == 8 and len(v) == 8 and u.lower() == u:   # a float word or a pointer / attribute
                    fu, fv = f32(u), f32(v)
                    if kind[0] == "F" and u is tx[-2]:   # getFloor's height
                        d = abs(fu - fv)
                        res["max_point"] = max(res["max_point"], d)
                        if d > tol:
                            bad = "floor %g vs %g" % (fu, fv)
                    else:
                        bad = "word %s vs %s" % (u, v)
                else:
                    bad = "value %s vs %s" % (u, v)
        if bad:
            res["over"] += 1
            if res["first"] is None:
                res["first"] = {"line": i + 1, "tick": int(tx[0]), "kind": kind, "what": bad, "ref": x, "native": y}
    if len(la) != len(lb) and res["first"] is None:
        res["first"] = {"line": min(len(la), len(lb)) + 1, "what": "query count differs"}
        res["over"] += 1
    return res


def main():
    a, b = sys.argv[1], sys.argv[2]
    opt = {"--pos": 1.0, "--deg": 0.1, "--col": 0.01}
    for k in opt:
        if k in sys.argv:
            opt[k] = float(sys.argv[sys.argv.index(k) + 1])
    js = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    bones = compare_bones(read_pal(a + "/pal.bin"), read_pal(b + "/pal.bin"), opt["--pos"], opt["--deg"])
    col = compare_col(a + "/col.txt", b + "/col.txt", opt["--col"])
    ok = bones["over"] == 0 and bones["missing"] == 0 and col["over"] == 0
    out = {"verdict": "PASS" if ok else "FAIL", "tolerances": opt, "bones": bones, "collision": col}
    if js:
        json.dump(out, open(js, "w"), indent=1)
    print("%s  bones: %d ticks, %d bone-ticks, %d bit-identical, %d equal, max pos %.6g u, max axis %.6g deg, palette %.6g u / %.6g deg, over %d%s"
          % (out["verdict"], bones["ticks"], bones["bones"], bones["bit_identical_bones"], bones["equal_bones"], bones["max_pos"], bones["max_deg"],
             bones["max_pal_pos"], bones["max_pal_deg"], bones["over"],
             ", first %s" % json.dumps(bones["first"]) if bones["first"] else ""))
    print("      collision: %d/%d queries, %d identical, max point %.6g u, over %d, kinds %s%s"
          % (col["compared"], col["queries_ref"], col["identical"], col["max_point"], col["over"], json.dumps(col["kinds"]),
             ", first %s" % json.dumps(col["first"]) if col["first"] else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
