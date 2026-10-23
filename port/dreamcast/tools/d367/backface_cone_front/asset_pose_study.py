#!/usr/bin/env python3
"""Check supplied converted groups under explicitly synthetic camera poses.

The input contains production Cone fields, cache-order integer points and actor
EOL indices. Geometry stays in that external file; the result contains counts,
hashes and numerical outcomes only. This is not a game capture or frame test.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import target_test as target


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def unit(v):
    length = math.sqrt(dot(v,v))
    return [x/length for x in v]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups",type=Path,required=True)
    parser.add_argument("--target-build",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    output,source = args.output.resolve(),args.target_build.resolve()
    groups = json.loads(args.groups.read_text())
    program,symbols = target.target.load_elf(source / "caller.elf")
    oracle = target.host.original.oracle_load(source / "oracle.so")
    model = target.pipeline_cost.Model(output / "pipeline",source / "caller.elf")
    rows = []
    for group in groups["groups"]:
        fields = group["cone"]
        cone = target.host.Cone()
        for key,value in fields.items():
            setattr(cone,key,(target.host.ctypes.c_float*3)(*value) if isinstance(value,list) else value)
        normal = unit(fields["axis"])
        tangent = unit(cross([0,1,0] if abs(normal[1]) < 0.9 else [1,0,0],normal))
        center = fields["center"]
        points,indices = group["points"],bytes(group["indices"])
        name = "%s-%s-%s" % (group["model"],group["chunk"],group["meshlet"])
        for angle in (-15,0,15):
            theta = math.radians(angle)
            direction = unit([normal[i]*math.cos(theta)+tangent[i]*math.sin(theta) for i in range(3)])
            x = unit(cross([0,1,0] if abs(direction[1]) < 0.9 else [1,0,0],direction))
            y = cross(direction,x)
            for factor in (1.25,2,4):
                distance = factor*fields["radius"]/fields["cos_lower"]
                w = [-v for v in direction]
                wt = distance+dot(direction,center)
                matrix = target.host.column_matrix(
                    tuple(320*(x[i]+w[i]) for i in range(3))+(320*(wt-dot(x,center)),),
                    tuple(240*(y[i]+w[i]) for i in range(3))+(240*(wt-dot(y,center)),),
                    tuple(w)+(wt,))
                cache = target.host.projected_cache(matrix,points)
                want = oracle(cache,indices,0x17f,1)[0]
                for mode in (0,4):
                    machine = target.scenario(program,symbols,matrix,cone,cache,indices,
                                              1,mode=mode,points=points)
                    got = machine.execute(symbols["_measure_caller"][0])
                    assert got == want,(name,angle,factor,mode)
                    row = dict(group=name,angle_degrees=angle,distance_factor=factor,mode=mode,
                               vertices=len(points),indices=len(indices),strips=group["counts"]["strips"],
                               accepted=machine.read(0x9030,4),outcome=machine.read(0x9034,4),
                               all_front=len(want)==len(indices)*32,instructions=machine.steps,
                               output_sha256=hashlib.sha256(got).hexdigest(),
                               pipeline=model.price("%s-angle%d-distance%s-mode%d" %
                                   (name,angle,str(factor).replace(".","p"),mode),machine))
                    rows.append(row)
                print(json.dumps({k:v for k,v in rows[-1].items() if k not in ("pipeline","output_sha256")} |
                                 {"baseline_cycles":rows[-2]["pipeline"]["model_cycles"],
                                  "certificate_cycles":rows[-1]["pipeline"]["model_cycles"]}),flush=True)
    report = dict(scope=__doc__,input_scope=groups["scope"],cases=rows,
                  input_sha256=hashlib.sha256(args.groups.read_bytes()).hexdigest(),
                  asset_source_sha256=groups.get("source_sha256",{}),
                  certificate_source_sha256=json.loads((source / "source-sha256.json").read_text()),
                  elf_sha256=hashlib.sha256((source / "caller.elf").read_bytes()).hexdigest(),
                  test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  pipeline_model=model.metadata(),
                  limits="Synthetic aligned/tilted cameras and host-generated projected caches on actual supplied converted index/position groups. Mode4 deliberately bypasses production cost admission. No game animation, camera trace, rendering, hardware or frame-rate measurement.")
    (output / "asset-pose-study.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
