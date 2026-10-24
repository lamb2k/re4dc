#!/usr/bin/env python3
"""Foliage / branch coverage-preserving mip recovery (lane foliagemip22, 2026-10-22).

Start set: the cut-out foliage keys (include/foliage_keys.inc, scoped -> original via scoped_origins792.inc) of the
given rooms that the mipfix22 v2 gate held for coverage / coverage-tiny. Each is rebuilt with
alpha_mip.coverage_chain and requalified with the current gate (mip_quality.audit, every level to 1x1) plus a
silhouette floor (IoU >= --min-iou at every level of side >= 4). Accepted keys go into an add-on pack on top of the
input pack and the scoped descriptor rows are rebound. Any other key keeps its original bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
sys.path.insert(0, str(TOOLS / "d367" / "mipmap21"))
sys.path.insert(0, str(HERE))
import alpha_mip
import mip_quality as mq
import texpack
from vram.vq_pak import read_pak

PORT = TOOLS.parent


def sha(b):
    return hashlib.sha256(b).hexdigest()


def r32(n):
    return (n + 31) // 32 * 32


def start_set(quality_json, rooms, worlds=None):
    fol = {}
    for line in (PORT / "game/platform/include/foliage_keys.inc").read_text().splitlines():
        m = re.match(r"\{0x(\w{8})U,0x(\w{8})U,(\d)\}, // (r\w+)(.*)", line)
        if m:
            fol[(m[1] + "-" + m[2]).lower()] = (int(m[3]), m[4], m[5].strip())
    s2o = {}
    for line in (TOOLS / "d367/texture_rect21/scoped_origins792.inc").read_text().splitlines():
        m = re.findall(r"0x(\w{8})U", line)
        if len(m) == 4:
            s2o[f"{m[0]}-{m[1]}".lower()] = f"{m[2]}-{m[3]}".lower()
    out = []
    for r in json.loads(Path(quality_json).read_text())["rows"]:
        o = s2o.get(r["key"], r["key"])
        if o in fol and r["alpha"] and fol[o][1] in rooms and set(r["reasons"]) & {"coverage", "coverage-tiny"}:
            out.append(dict(key=r["key"], original=o, room=fol[o][1], foliage_class=fol[o][0], census=fol[o][2],
                            format=r["format"], pixel_format=r["pixel_format"], side=r["side"],
                            v2_reasons=r["reasons"], v2_levels=r["levels"]))
    if worlds:   # cut-outs outside the foliage table (bare-tree branches, fences) placed in these rooms' PS2 worlds
        have = {e["key"] for e in out}
        for room in sorted(rooms):
            p = Path(worlds) / room / "ps2-world.r4pw"
            if not p.exists():
                continue
            w = p.read_bytes()
            for r in json.loads(Path(quality_json).read_text())["rows"]:
                if r["key"] in have or not r["alpha"] or not set(r["reasons"]) & {"coverage", "coverage-tiny"}:
                    continue
                if struct.pack("<I", int(r["key"].split("-")[0], 16)) in w:
                    have.add(r["key"])
                    out.append(dict(key=r["key"], original=s2o.get(r["key"], r["key"]), room=room, foliage_class=None,
                                    census="world cut-out (not in foliage_keys.inc)", format=r["format"],
                                    pixel_format=r["pixel_format"], side=r["side"], v2_reasons=r["reasons"],
                                    v2_levels=r["levels"]))
    return sorted(out, key=lambda e: (e["room"], e["key"]))


def key_tuple(s):
    a, b = s.split("-")
    return int(a, 16), int(b, 16)


def work(job):
    e, blob, min_iou = job
    try:
        out, rep = alpha_mip.coverage_chain(blob, enabled=True)
    except ValueError as exc:
        e.update(decision="keep-original", why="generator: %s" % exc)
        return e, None
    e["levels"] = rep["levels"]
    e["base_coverage"] = rep["base_coverage"]
    for f in ("codebook_used", "spare_slots"):
        if f in rep:
            e[f] = rep[f]
    e["added_rounded_bytes"] = r32(rep["after_payload_bytes"]) - r32(rep["before_payload_bytes"])
    res = mq.audit((key_tuple(e["key"]), out))
    row = res[1]
    e["gate_verdict"], e["gate_reasons"] = row["verdict"], row["reasons"]
    bad_iou = [l["side"] for l in rep["levels"] if l["side"] >= 4 and l["iou"] < min_iou]
    good = [l["side"] for l in rep["levels"]
            if abs(l["coverage_err"]) <= mq.coverage_tol(rep["base_coverage"], l["side"]) and l["iou"] >= min_iou]
    floor = e["side"]
    for l in rep["levels"]:   # largest-first: smallest side such that every level above it is good
        if l["side"] in good:
            floor = l["side"]
        else:
            break
    e["good_floor_side"] = floor
    e["levels_good"] = sum(1 for l in rep["levels"] if l["side"] >= floor)
    if row["verdict"] == "pass" and not bad_iou:
        e["decision"] = "accept"
        e["output_sha256"] = sha(out)
        return e, out
    e["decision"] = "keep-original"
    e["why"] = ",".join(row["reasons"] + (["iou<%.2f@%s" % (min_iou, bad_iou)] if bad_iou else []))
    return e, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--quality-json", type=Path, required=True)
    ap.add_argument("--room-select", type=Path, required=True)
    ap.add_argument("--rooms", default="r100,r101,r103,r104")
    ap.add_argument("--worlds", help="dir with <room>/ps2-world.r4pw: add held cut-outs those worlds place")
    ap.add_argument("--min-iou", type=float, default=0.5)
    ap.add_argument("--scoped-inc", nargs=2, action="append", default=[], metavar=("IN", "OUT"))
    ap.add_argument("--out-pack", type=Path)
    ap.add_argument("--keys-out", type=Path, help="write accepted keys -> output package dir (for stills)")
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    pack = a.pack.read_bytes()
    texpack.verify(pack)
    members = read_pak(pack)
    holds = mq.read_hold(a.room_select)
    entries = start_set(a.quality_json, set(a.rooms.split(",")), a.worlds)
    jobs, ledger = [], []
    for e in entries:
        blob = members.get(key_tuple(e["key"]))
        if blob is None:
            e.update(decision="keep-original", why="not in pack")
            ledger.append(e)
        elif e["key"] in holds:
            e.update(decision="keep-original", why="room-select residency hold (lane mipmap22)")
            ledger.append(e)
        else:
            e["input_sha256"] = sha(blob)
            jobs.append((e, blob, a.min_iou))
    accepted = {}
    with multiprocessing.Pool(a.jobs) as pool:
        for e, out in pool.imap_unordered(work, jobs):
            ledger.append(e)
            if out is not None:
                accepted[key_tuple(e["key"])] = out
            print(e["room"], e["key"], e["format"], e["side"], e["decision"], e.get("why", ""),
                  e.get("added_rounded_bytes", ""), flush=True)
    ledger.sort(key=lambda e: (e["room"], e["key"]))
    summary = dict(input_pack_sha256=sha(pack), quality_json_sha256=sha(a.quality_json.read_bytes()),
                   room_select_sha256=sha(a.room_select.read_bytes()), rooms=a.rooms, min_iou=a.min_iou,
                   keys=len(entries), accepted=len(accepted),
                   added_rounded_bytes=sum(e.get("added_rounded_bytes", 0) for e in ledger if e["decision"] == "accept"))
    if a.out_pack:
        new = dict(members)
        new.update(accepted)
        out, n = texpack.build(new)
        texpack.verify(out)
        same, _ = texpack.build(dict(members))
        summary.update(off_identity=sha(same) == sha(pack), out_pack_sha256=sha(out), out_members=n,
                       changed_members=sum(members[x] != new[x] for x in members))
        a.out_pack.write_bytes(out)
    summary["scoped_rebound"] = {}
    for src, dst in a.scoped_inc:
        text, n = mq.rebind(Path(src).read_text(), accepted)
        Path(dst).write_text(text)
        summary["scoped_rebound"][dst] = dict(rows=n, sha256=sha(text.encode()))
    a.ledger.write_text(json.dumps(dict(summary=summary, keys=ledger), indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
