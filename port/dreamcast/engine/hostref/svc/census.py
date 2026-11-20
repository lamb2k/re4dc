#!/usr/bin/env python3
"""census.py: read the service census tables of re4ref (svc_trace.cpp) and write the summaries SERVICES.md uses.

    census.py <census out dir> <re4ref census binary> [--md out.md] [--json out.json]

- Boundary calls: every call from code outside a service unit into a skeleton or collision entry point, per entry,
  per calling function, per actor; calls per tick (mean over the run).
- Helper calls inside each service entry (matrix, vector, trigonometry), per actor per tick.
- Memory per service entry and actor (RE4_SVC_TRACE=1 runs): accesses and distinct 32-byte lines per tick, by
  region (parts records, character records, archives, heap).
- Fields: every instruction outside the skeleton units that reads or writes a parts record (cParts, 0x1D8 B) or the
  skeleton's part of a model record (cModel 0x0C-0x2B4): field, who, how often, which bones.
"""
import bisect
import collections
import json
import re
import subprocess
import sys

UNIT_KIND = {}
for u in "model motion cMotBase ik shape".split():
    UNIT_KIND[u] = "skeleton"
UNIT_KIND["pl_cloth"] = "cloth"
for u in "atari at_mod at_sub at_sub2 atariInfo".split():
    UNIT_KIND[u] = "collision"
for u in "route_ck area".split():
    UNIT_KIND[u] = "routes"
for u in "math_sub sub2 pmtx".split():
    UNIT_KIND[u] = "math"

# cParts / cModel fields (include/model.h): (offset, size, name)
COORD = [(0x00, 4, "be_flag"), (0x04, 4, "pNext"), (0x08, 4, "vptr"), (0x0C, 48, "mat"), (0x3C, 48, "l_mat"),
         (0x6C, 4, "pParent"), (0x70, 12, "world"), (0x7C, 12, "world_old"), (0x88, 12, "world_old2"),
         (0x94, 12, "pos"), (0xA0, 12, "ang"), (0xAC, 12, "scale"), (0xB8, 12, "r_scale"), (0xC4, 48, "prevMat")]
PARTS = COORD + [(0xF4, 4, "pList"), (0xF8, 48, "lt_inv_mat|ik.bindMat"), (0x128, 12, "addRot|ik.len"),
                 (0x12C, 48, "ik.mat"), (0x15C, 12, "ik.axis"), (0x168, 12, "ik.dir"), (0x174, 12, "motParts.pos"),
                 (0x180, 12, "motParts.rot"), (0x18C, 12, "motParts.scale"), (0x198, 4, "motParts.ikAng"),
                 (0x19C, 36, "motParts.hist"), (0x1C0, 4, "motParts.flags"), (0x1C4, 20, "pad_1C4")]
MOTION = [(0x00, 4, "pMot"), (0x04, 4, "pHermite_data"), (0x08, 24, "Key_hist"), (0x20, 4, "Mot_frame_max"),
          (0x24, 4, "Mot_frame"), (0x28, 4, "Mot_frame_sav"), (0x2C, 4, "Mot_frame_old"), (0x30, 4, "Joint_num"),
          (0x34, 4, "pJoint_no"), (0x38, 4, "pJoint_kind"), (0x3C, 2, "Null_pos"), (0x3E, 2, "Null_rot"),
          (0x40, 2, "Mot_attr"), (0x42, 2, "Mot_state"), (0x44, 4, "Mot_flag"), (0x48, 12, "Pos"), (0x54, 12, "Pos_old"),
          (0x60, 12, "Pos_dist"), (0x6C, 12, "Pos_world"), (0x78, 12, "Pos_move_old"), (0x84, 12, "Ang"),
          (0x90, 12, "Ang_old"), (0x9C, 12, "Ang_dist"), (0xA8, 4, "pSeq_top"), (0xAC, 4, "Seq"), (0xB0, 4, "Seq_old"),
          (0xB4, 4, "Seq_old2"), (0xB8, 4, "Seq_frame"), (0xBC, 4, "Seq_frame_num"), (0xC0, 4, "Seq_speed"),
          (0xC4, 4, "Hokan_frame/cnt"), (0xC8, 4, "Brate"), (0xCC, 4, "pAttachCam"), (0xD0, 4, "blend"),
          (0xD4, 4, "flip"), (0xD8, 4, "blendTbl")]
MODEL = COORD + [(0xF4, 4, "pParts"), (0xF8, 4, "serial"), (0xFC, 4, "stat(r_no)"), (0x100, 4, "id/type/nParts/alpha"),
                 (0x104, 12, "speed"), (0x110, 12, "pos_old"), (0x11C, 12, "Wall_norm"), (0x128, 0x28, "model 128-14F"),
                 (0x150, 12, "invisible"), (0x15C, 4, "pModelInfo"), (0x160, 4, "pShadowModelInfo"),
                 (0x164, 0x74, "LightInfo")] + [(0x1D8 + o, s, "Motion." + n) for o, s, n in MOTION] + \
        [(0x2B4, 0x4C, "atari"), (0x300, 0x20, "model 300-31F")]


def field_name(table, off, beyond="beyond"):
    for o, s, n in table:
        if o <= off < o + s:
            return n
    return "%s+%03x" % (beyond, off)


class Syms:
    def __init__(self, binary):
        out = subprocess.run(["nm", "-n", "-C", binary], capture_output=True, text=True, check=True).stdout
        self.addr, self.name = [], []
        for line in out.splitlines():
            m = re.match(r"^([0-9a-f]{8}) ([TtWw]) (.*)$", line)
            if m:
                self.addr.append(int(m.group(1), 16))
                self.name.append(m.group(3))
        self.sec = []
        mp = open(binary + ".map").read()
        for m in re.finditer(r"^ (\.text\S*)\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+(\S+)$", mp, re.M):
            lo, sz, obj = int(m.group(2), 16), int(m.group(3), 16), m.group(4)
            if sz:
                self.sec.append((lo, lo + sz, obj))
        self.sec.sort()
        self.seclo = [s[0] for s in self.sec]

    def func(self, a):
        i = bisect.bisect_right(self.addr, a) - 1
        return self.name[i] if i >= 0 else "?"

    def unit(self, a):
        i = bisect.bisect_right(self.seclo, a) - 1
        if i >= 0 and self.sec[i][0] <= a < self.sec[i][1]:
            obj = self.sec[i][2]
            u = obj.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if "/sdk/" in obj or "/libm/" in obj:
                return "math:" + u
            if "/host/" in obj or "census" in obj:
                return "host:" + u
            return u
        return "?"


def kind_of(unit):
    if unit.startswith("math:"):
        return "math"
    if unit.startswith("host:"):
        return "host"
    return UNIT_KIND.get(unit, "behaviour")


def read_tsv(path):
    ticks, rows = 0, []
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("# ticks"):
            ticks = int(line.split("\t")[1])
        elif line and not line.startswith("#"):
            rows.append(line.split("\t"))
    return ticks, rows


def demangle(names):
    out = subprocess.run(["c++filt"], input="\n".join(names), capture_output=True, text=True, check=True).stdout
    return dict(zip(names, out.splitlines()))


def main():
    d, binary = sys.argv[1], sys.argv[2]
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    js = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    sy = Syms(binary)
    actors = {}
    for line in open(d + "/actors.tsv"):
        if line.startswith("#"):
            continue
        c, pool, slot, ident, typ, nparts, first = line.split()
        name = {"00": "Leon", "03": "Ashley", "15": "Ganado"}.get(ident, "id" + ident) if pool == "em" else "obj" + ident
        actors[int(c)] = "%s(%s%s,%s parts)" % (name, pool, slot, nparts)
    actors[128] = "-"
    ticks, calls = read_tsv(d + "/calls.tsv")
    names = demangle(sorted({r[1] for r in calls}))
    res = {"ticks": ticks, "boundary": [], "nested": [], "helpers": [], "mem": [], "fields": []}
    agg = collections.Counter()
    nest = collections.Counter()
    for idx, name, unit, kind, ret, depth0, actor, n in calls:
        ret = int(ret, 16)
        cu = sy.unit(ret)
        ck = kind_of(cu)
        entry = (UNIT_KIND.get(unit, "?"), unit, names[name])
        if depth0 == "1" and ck not in ("skeleton", "collision"):
            agg[(entry, ck, cu, sy.func(ret), actors.get(int(actor), actor))] += int(n)
        else:
            nest[(entry, cu, actors.get(int(actor), actor))] += int(n)
    for (entry, ck, cu, fn, act), n in sorted(agg.items(), key=lambda x: -x[1]):
        res["boundary"].append({"service": entry[0], "unit": entry[1], "entry": entry[2], "caller_kind": ck, "caller_unit": cu,
                                "caller": fn, "actor": act, "calls": n, "per_tick": n / max(ticks, 1)})
    for (entry, cu, act), n in sorted(nest.items(), key=lambda x: -x[1]):
        res["nested"].append({"service": entry[0], "unit": entry[1], "entry": entry[2], "caller_unit": cu, "actor": act,
                              "calls": n, "per_tick": n / max(ticks, 1)})
    _, mc = read_tsv(d + "/mcalls.tsv")
    mnames = demangle(sorted({r[1] for r in mc} | {r[4] for r in mc}))
    hel = collections.Counter()
    for idx, name, unit, ctx, ctxn, actor, n in mc:
        hel[(mnames.get(ctxn, ctxn), actors.get(int(actor), actor), mnames[name])] += int(n)
    for (ctx, act, h), n in sorted(hel.items(), key=lambda x: (x[0][0], x[0][1], -x[1])):
        res["helpers"].append({"ctx": ctx, "actor": act, "helper": h, "calls": n, "per_tick": n / max(ticks, 1)})
    try:
        _, mem = read_tsv(d + "/mem.tsv")
    except FileNotFoundError:
        mem = []
    if mem:
        mn = demangle(sorted({r[1] for r in mem}))
        for ctx, ctxn, cunit, actor, reg, acc, rd, wr, lines, lmax, seen in mem:
            res["mem"].append({"ctx": mn.get(ctxn, ctxn), "ctx_unit": cunit, "ctx_kind": UNIT_KIND.get(cunit, "none"),
                               "actor": actors.get(int(actor), actor), "region": reg, "acc_per_tick": int(acc) / ticks,
                               "reads": int(rd), "writes": int(wr), "lines_per_tick": int(lines) / ticks,
                               "lines_max": int(lmax), "ticks_seen": int(seen)})
        _, fl = read_tsv(d + "/fields.tsv")
        fn = demangle(sorted({r[2] for r in fl}))
        for eip, ctx, ctxn, reg, off, w, n, nt, bones in fl:
            a = int(eip, 16)
            u = sy.unit(a)
            k = kind_of(u)
            off = int(off)
            if reg == "parts":
                field = field_name(PARTS, off)
            else:
                if off >= 0x320:
                    continue   # cEm / cObj fields beyond the model record: behaviour's own state
                field = field_name(MODEL, off)
            res["fields"].append({"eip": eip, "func": sy.func(a), "unit": u, "kind": k, "ctx": fn.get(ctxn, ctxn),
                                  "ctx_unit_kind": "none" if ctx == "4096" else "service", "region": reg, "offset": off,
                                  "field": field, "write": w == "1", "count": int(n), "ticks": int(nt), "bones": bones})
    if js:
        json.dump(res, open(js, "w"), indent=1)
    lines = ["# census %s (%d ticks)" % (d, ticks), ""]
    lines.append("## Boundary calls (from behaviour, host and other units into skeleton and collision), per tick")
    lines.append("")
    lines.append("| Service | Entry | Caller | Caller unit | Actor | Calls a tick |")
    lines.append("|---|---|---|---|---|---:|")
    for r in res["boundary"]:
        lines.append("| %s | `%s` | `%s` | %s | %s | %.2f |" % (r["service"], r["entry"], r["caller"], r["caller_unit"], r["actor"], r["per_tick"]))
    if md:
        open(md, "w").write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
