#!/usr/bin/env python3
"""cloth_stats.py: the native cloth against the original with the wind on (lane eng-svc2; SERVICES.md section 12).

    cloth_stats.py <reference dir> <native dir> [--json out.json] [--radius 0.4] [--mean 2.0]

Random numbers are split (owner 2026-11-19): the cloth draws its wind phase from the engine's presentation generator
and the original from a stream of its own, so with the wind on the two chains swing in different phases and are
compared as statistics over the run, not tick by tick (with the wind off they compare bit for bit: svc_compare.py).
Both directories hold pal.bin (svc_dump.cpp); the native one's svc.txt names every chain's link bones.

Each link's position relative to its model's bone 0, every tick. The wind pushes a link away from the root's
vertical axis, by an amount the random phase modulates around 1 (sin + 1) and the root's speed scales, so:
  radius  per chain, the mean over its links and the run of the horizontal distance from bone 0: native within
          --radius units of the original (default 0.4; the phase alone moves it at most 0.25 on the six fixtures, a
          wind twice as strong 0.55 on e1-route)
  mean    per link, its mean position within --mean units (default 2.0)
Reported, not checked: each link's sway (root mean square distance from its mean) and the largest single-tick
difference. Exit 0 when every chain passes.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svc_compare import read_pal  # noqa: E402


def chains(path):
    out = []
    for line in open(path):
        if line.startswith("chain "):
            w = line.split()
            out.append((int(w[3]), [int(b) for b in w[5:]]))
    return out


def offsets(pal, code, bones):
    ticks = sorted(t for t in pal if code in pal[t])
    a = np.stack([pal[t][code] for t in ticks]).astype(np.float64)   # ticks x bones x 27
    return a[:, bones, 12:15] - a[:, 0:1, 12:15]


def main():
    ra, rb = sys.argv[1], sys.argv[2]
    opt = {"--radius": 0.4, "--mean": 2.0}
    for k in opt:
        if k in sys.argv:
            opt[k] = float(sys.argv[sys.argv.index(k) + 1])
    js = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    pa, pb = read_pal(ra + "/pal.bin"), read_pal(rb + "/pal.bin")
    res = {"chains": 0, "links": 0, "fail": 0, "max_radius": 0.0, "max_mean": 0.0, "max_sway_diff": 0.0, "max_tick": 0.0,
           "first": None, "tolerances": opt, "per_chain": []}
    for code, bones in chains(rb + "/svc.txt"):
        x, y = offsets(pa, code, bones), offsets(pb, code, bones)
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        rx = np.sqrt(x[:, :, 0] ** 2 + x[:, :, 2] ** 2).mean()
        ry = np.sqrt(y[:, :, 0] ** 2 + y[:, :, 2] ** 2).mean()
        dr = float(ry - rx)
        mx, my = x.mean(axis=0), y.mean(axis=0)
        dm = float(np.linalg.norm(mx - my, axis=1).max())
        swx = np.sqrt(((x - mx) ** 2).sum(axis=2).mean(axis=0))
        swy = np.sqrt(((y - my) ** 2).sum(axis=2).mean(axis=0))
        res["chains"] += 1
        res["links"] += len(bones)
        res["max_radius"] = max(res["max_radius"], abs(dr))
        res["max_mean"] = max(res["max_mean"], dm)
        res["max_sway_diff"] = max(res["max_sway_diff"], float(np.abs(swy - swx).max()))
        res["max_tick"] = max(res["max_tick"], float(np.linalg.norm(x - y, axis=2).max()))
        ok = abs(dr) <= opt["--radius"] and dm <= opt["--mean"]
        res["per_chain"].append({"model": code, "links": len(bones), "radius_ref": float(rx), "radius_diff": dr, "mean_diff": dm, "ok": ok})
        if not ok:
            res["fail"] += 1
            if res["first"] is None:
                res["first"] = res["per_chain"][-1]
    res["verdict"] = "PASS" if res["fail"] == 0 and res["chains"] else "FAIL"
    if js:
        json.dump(res, open(js, "w"), indent=1)
    print("%s  cloth: %d chains, %d links; chain radius within %.3g u (tolerance %.3g), link mean position within %.3g u "
          "(tolerance %.3g); sway within %.3g u, largest single-tick difference %.3g u (reported); over %d%s" % (
              res["verdict"], res["chains"], res["links"], res["max_radius"], opt["--radius"], res["max_mean"], opt["--mean"],
              res["max_sway_diff"], res["max_tick"], res["fail"], ", first %s" % json.dumps(res["first"]) if res["first"] else ""))
    sys.exit(0 if res["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
