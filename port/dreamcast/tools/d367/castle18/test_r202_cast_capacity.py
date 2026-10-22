#!/usr/bin/env python3
"""Exercise the target loader on the retained r202 53+16 geometry cast and existing r200 control.
Private packages are explicit inputs; this test creates no meshes or runtime exceptions.
"""
from pathlib import Path
import argparse, hashlib, json, struct, subprocess, sys
HERE = Path(__file__).resolve().parent.parent
GAME = HERE.parents[1] / "game"
sys.path.insert(0, str(HERE))
from model_registry_pack_test import Pack


def main():
    a = argparse.ArgumentParser(description=__doc__)
    for n in ("primary", "partner", "control-primary", "control-partner", "out"):
        a.add_argument("--" + n, type=Path, required=True)
    args = a.parse_args()
    out = args.out.resolve()
    out.mkdir(exist_ok=False)
    primary, partner = args.primary.read_bytes(), args.partner.read_bytes()
    assert Pack(primary).sec("geom")["count"] == 53
    assert Pack(partner).sec("geom")["count"] == 16
    mat = (GAME / "coarse_actor_material.inc").read_text()
    reg = (GAME / "coarse_actor_owner_registry.inc").read_text()
    lo, hi = mat.index("struct Digest"), mat.index("struct SourceBlob")
    hi = mat.index("\n", hi) + 1
    rl, rh = reg.index("namespace nmr {"), reg.index('#else\n#include "native_model_registry.h"')
    types = "#pragma once\n#include <cstdint>\nnamespace re4dc_material {\n" + mat[lo:hi]
    types += '#include "actor_material_records.inc"\n}\n' + reg[rl:rh]
    lo = reg.index("nmr::Chunk registry_geom_view(")
    hi = reg.index("\n}", lo) + 2
    types += "\n" + reg[lo:hi] + "\n"
    (out / "pack_test_types.h").write_text(types)
    base = {"RE4DC_NMR_ASHLEY": 2, "RE4DC_NMR_PARTNER": 2, "RE4DC_NMR_SLOTS": 1,
            "RE4DC_NMR_MASK": 1, "RE4DC_NMR_DROP_BUMP": 1, "RE4DC_NMR_BONES": 96,
            "RE4DC_NMR_POOL": 1, "RE4DC_NMR_ROLES5": 1, "RE4DC_NMR_SHIFT": 1,
            "RE4DC_ACTOR_PL08": 1, "RE4DC_ROUTE_CH22": 1, "RE4DC_ROUTE_CH23": 1}
    exes = {}
    for mode in (0, 1):
        exe = out / ("loader-" + str(mode))
        defs = dict(base, RE4DC_NMR_R202_CAST_CAPACITY=mode)
        cmd = ["g++", "-std=c++17", "-O1", "-w", *[f"-D{k}={v}" for k, v in defs.items()],
               "-I", str(out), "-I", str(GAME), "-I", str(GAME / "platform/include"),
               str(HERE / "model_registry_pack_test.cpp"), "-o", str(exe)]
        subprocess.run(cmd, check=True, capture_output=True)
        exes[mode] = exe
    results = []
    def check(name, mode, room, paths, expected):
        output = subprocess.check_output([str(exes[mode]), room, *paths], text=True)
        actual = [line.rsplit(" ", 2)[-2] for line in output.splitlines()]
        assert actual == expected, (name, output, expected)
        results.append(dict(name=name, mode=mode, output=output))
    pair = [str(args.primary), "+" + str(args.partner)]
    check("existing64-limit-reproduced", 0, "202", pair, ["none", "table"])
    check("complete69-r202", 1, "202", pair, ["none", "none"])
    control = [str(args.control_primary), "+" + str(args.control_partner)]
    for mode in (0, 1):
        check("existing-r200-unchanged", mode, "200", control, ["none", "none"])
    def retarget(data, room, name):
        p = Pack(data); p.put(32, room); p.fix()
        dest = out / name; dest.write_bytes(p.b); return str(dest)
    elsewhere = [retarget(primary, 0x207, "primary207.re4nmr"),
                 "+" + retarget(partner, 0x207, "partner207.re4nmr")]
    check("other-room-still64", 1, "207", elsewhere, ["none", "table"])
    # Storage has72 slots; the audited room admission still stops at69.
    p = Pack(partner); sec = p.sec("geom"); p.put(sec["table"]+12, 17); p.put(sec["table"]+8, 17*64); p.fix()
    bad = out / "partner70.re4nmr"; bad.write_bytes(p.b)
    check("r202-rejects70", 1, "202", [str(args.primary), "+"+str(bad)], ["none", "table"])
    # A recomputed outer hash never bypasses an existing geometry proof.
    p = Pack(primary); at = p.rec("geom", 0, 64)+52; p.put(at, p.u32(at)^1); p.fix()
    bad = out / "geometry-corrupt.re4nmr"; bad.write_bytes(p.b)
    check("geometry-proof-preserved", 1, "202", [str(bad)], ["hash"])
    p = Pack(primary); p.put(44, p.u32(44)^1)
    bad = out / "header-corrupt.re4nmr"; bad.write_bytes(p.b)
    check("header-proof-preserved", 1, "202", [str(bad)], ["hash"])
    mk = (GAME / "native_model_registry.mk").read_text()
    fragment = mk[mk.index("# NMR_R202_CAST_CAPACITY=1"):mk.index("# NATIVE_MODEL_REGISTRY_ROLE_TEX23=1")]
    mf = out / "Makefile"
    mf.write_text(fragment + '\n.PHONY: show\nshow:\n\t@echo "$(GAME_CPPFLAGS)|$(PLATFORM_CPPFLAGS)"\n')
    for mode, pack, pool, roles, success in [(None,1,1,1,True),(0,1,1,1,True),(1,1,1,1,True),
                                           (2,1,1,1,False),(1,0,1,1,False),(1,1,0,1,False),(1,1,1,0,False)]:
        cmd = ["make", "--no-print-directory", "-f", str(mf), "show",
               f"NATIVE_MODEL_REGISTRY_PACK={pack}", f"NATIVE_MODEL_REGISTRY_POOL={pool}",
               f"NATIVE_MODEL_REGISTRY_ROLES5={roles}"]
        if mode is not None: cmd.append(f"NMR_R202_CAST_CAPACITY={mode}")
        cp = subprocess.run(cmd, text=True, capture_output=True)
        assert (cp.returncode == 0) == success, (cmd, cp.stdout, cp.stderr)
        if success: assert ("RE4DC_NMR_R202_CAST_CAPACITY=1" in cp.stdout) == (mode == 1)
        results.append(dict(name="make-prerequisites", mode=mode, pack=pack, pool=pool, roles=roles, success=success))
    report = {"cases":results,"inputs":{str(p):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (args.primary,args.partner,args.control_primary,args.control_partner)},
              "implementation":"actual target source, unchanged geometry/header/role/material/skeleton checks"}
    (out / "result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(f"PASS {len(results)} target-loader and make cases")


if __name__ == "__main__":
    main()
