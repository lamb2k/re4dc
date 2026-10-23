#!/usr/bin/env python3
"""Count scenery proof/admission coverage without running or republishing assets.

Run the actual scenery producer in memory and the actual C++ cost predicate.
The receipt contains counts and source hashes only. It is not a camera hit
rate, numerical acceptance rate, emulator measurement, or frame-rate result.
"""
import argparse
import collections
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "scenery21"))
import scn21_build as producer


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_admission(nv, ni, ns):
    return nv >= 3 and ni >= 256 and ni//4 >= nv and ns >= 64


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True,
                        help="Native directory containing room subdirectories")
    parser.add_argument("--rooms", nargs="+", required=True)
    parser.add_argument("--groups", nargs="+", type=int, default=[1, 4], choices=(1, 2, 4, 8))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--source-label", default="user-supplied assets")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    probe = output / "cost_predicate.cpp"
    probe.write_text('#include "backface_certificate.hpp"\n#include <cstdio>\n'
                     'int main(){unsigned v,i,s;while(std::scanf("%u %u %u",&v,&i,&s)==3)'
                     'std::printf("%u\\n",re4dc::bf::certificate::worth_front_world(v,i,s));}\n')
    command = [args.cxx, "-std=c++17", "-O2", "-I"+str(DC / "room"), str(probe), "-o", str(output / "cost-predicate")]
    subprocess.run(command, check=True)
    rows = []
    for room in args.rooms:
        mesh = args.native / room / "ps2-world.re4mesh"
        side = args.native / room / "ps2-world.r4pw"
        source_hashes = {mesh.name: sha(mesh), side.name: sha(side)}
        for group_count in args.groups:
            _, sg, cn, _, stats, _ = producer.build_room(mesh, side, group_count, True, True)
            count = stats["meshlets"] * group_count
            start = (272 + 8*count + 15) & ~15
            assert cn[start:start+4] == b"SCCF"
            normals = struct.unpack_from("<%df" % count, cn, start+544)
            counts = list(struct.iter_unpack("<HH", cn[start+544+4*count:start+544+8*count]))
            groups = []
            for i, ((ni, ns), normal) in enumerate(zip(counts, normals)):
                if not ni:
                    continue
                lo, hi = struct.unpack_from("<BB", sg, 32+16*i+14)
                assert hi >= lo and ns > 0
                groups.append((hi-lo+1, ni, ns, normal > 0))
            result = subprocess.run([str(output / "cost-predicate")],
                                    input="".join("%d %d %d\n" % g[:3] for g in groups),
                                    text=True, capture_output=True, check=True)
            eligible = [bool(int(v)) for v in result.stdout.split()]
            assert len(eligible) == len(groups)
            histogram = collections.Counter(groups)
            row = dict(room=room, groups_per_meshlet=group_count,
                       meshlets=stats["meshlets"], nonempty_groups=len(groups),
                       valid_proof_groups=sum(g[3] for g in groups),
                       cost_eligible_groups=sum(eligible),
                       valid_and_cost_eligible=sum(g[3] and ok for g,ok in zip(groups,eligible)),
                       original_cost_eligible=sum(old_admission(*g[:3]) for g in groups),
                       max_vertices=max(g[0] for g in groups),
                       max_indices=max(g[1] for g in groups),
                       max_strips=max(g[2] for g in groups),
                       front_trailer_bytes=stats["front_trailer_bytes"],
                       source_sha256=source_hashes,
                       count_histogram=[dict(vertices=g[0],indices=g[1],strips=g[2],
                                             valid_proof=g[3],groups=n)
                                        for g,n in sorted(histogram.items())])
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ("count_histogram","source_sha256")}),flush=True)
    report = dict(scope=__doc__,source=args.source_label,rooms=rows,
                  predicate_compile_command=command,
                  source_sha256={"scn21_build.py":sha(Path(producer.__file__)),
                                 "backface_certificate.hpp":sha(DC / "room/backface_certificate.hpp"),
                                 "asset_census.py":sha(Path(__file__))})
    (output / "asset-census.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
