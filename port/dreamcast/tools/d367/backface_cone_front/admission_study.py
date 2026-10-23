#!/usr/bin/env python3
"""Measure actual SH4 actor proof break-even points on public synthetic groups.

This is an ungated cost study, not a claim that its groups occur in game data.
Reuse a target_test.py build so the measured production snapshot is explicit.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import target_test as target


def workloads():
    matrix = next(f[1] for f in target.fixtures()
                  if f[0] == "front-nonplanar-rotated-grid64")
    for side in (3, 4, 5, 6, 8):
        points = [(128*x-64*(side-1), 128*y-64*(side-1),
                   4*((x*x+y*y) % 5)-8)
                  for y in range(side) for x in range(side)]
        triangles = bytes(v for y in range(side-1) for x in range(side-1)
                          for v in (y*side+x, y*side+x+1, (y*side+x+side) | 128,
                                    y*side+x+1, y*side+x+side+1, (y*side+x+side) | 128))
        quads = bytes(v for y in range(side-1) for x in range(side-1)
                      for v in (y*side+x, y*side+x+1, y*side+x+side,
                                (y*side+x+side+1) | 128))
        rows = bytes(v for y in range(side-1) for x in range(side)
                     for v in (y*side+x, ((y+1)*side+x) | (128 if x == side-1 else 0)))
        for label, indices, cull in (("triangles", triangles, 1), ("quads", quads, 1), ("rows", rows, 2)):
            yield "%dx%d-%s" % (side, side, label), matrix, points, indices, cull


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-cc", default="gcc")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source, output = args.target_build.resolve(), args.output.resolve()
    program, symbols = target.target.load_elf(source / "caller.elf")
    model = target.pipeline_cost.Model(output / "pipeline", source / "caller.elf", args.host_cc)
    oracle = target.host.original.oracle_load(source / "oracle.so")
    records = []
    for name, matrix, points, indices, cull in workloads():
        cone = target.host.cone_for(points, indices)
        cache = target.host.projected_cache(matrix, points)
        want = oracle(cache, indices, 0x17f, cull)[0]
        assert len(want) == 32*len(indices), name
        for batch in (1, 6):
            for mode in (0, 4, 3):
                machine = target.scenario(program, symbols, matrix, cone, cache, indices,
                                          cull, batch, mode, points=points)
                got = machine.execute(symbols["_measure_caller"][0])
                assert got == want*batch, (name, batch, mode)
                accepted = machine.read(0x9030, 4)
                if mode == 3:
                    assert accepted == batch
                record = dict(case=name, vertices=len(points), indices=len(indices),
                              strips=sum(bool(v & 128) for v in indices), batch=batch,
                              mode=mode, accepted=accepted, instructions=machine.steps,
                              pipeline=model.price("%s-batch%d-mode%d" % (name,batch,mode),machine),
                              packet_sha256=hashlib.sha256(got).hexdigest())
                records.append(record)
            sample = records[-3:]
            print(json.dumps({"case":name,"vertices":len(points),"indices":len(indices),
                              "strips":sample[0]["strips"],"batch":batch,
                              "baseline":sample[0]["pipeline"]["model_cycles"],
                              "certificate":sample[1]["pipeline"]["model_cycles"],
                              "copy":sample[2]["pipeline"]["model_cycles"],
                              "accepted":sample[1]["accepted"]}),flush=True)
    report = dict(scope=__doc__, cases=records, pipeline_model=model.metadata(),
                  target_build=str(source),
                  source_sha256=json.loads((source / "source-sha256.json").read_text()),
                  elf_sha256=hashlib.sha256((source / "caller.elf").read_bytes()).hexdigest(),
                  test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  limits="Synthetic CPU scheduling with perfect caches; no projection, real asset coverage, memory/PVR/bus, scene or frame-rate measurement. Mode4 bypasses production admission explicitly; mode3 is copy-only lower bound.")
    (output / "admission-study.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
