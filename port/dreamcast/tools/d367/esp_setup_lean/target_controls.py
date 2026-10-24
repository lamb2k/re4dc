#!/usr/bin/env python3
"""Bound the extra interpreter operations used by the real packet fixture.

These controls cover positive image-dimension conversions, MOVCA's four-byte
architectural store, ROTR carry, and independently known sprite body words.
No FTRV/FSRRA model or PVR/cache behavior is introduced.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode=True
import measure_target as target


def run(args):
    controls=[]
    for value in (0,1,63,64,256,1024,0x7fffffff):
        m=target.Machine();m.fpscr|=1<<19;m.fpul=value
        m.map(0x100000,struct.pack("<2H",0xf22d,0xf2bd))
        m.observe_start();m.step(0x100000);m.step(0x100002);m.observe_stop()
        assert m.fpul==struct.unpack("<I",struct.pack("<f",float(value)))[0]
        assert not m.memory_events
    controls.append("FLOAT positive signed integer to DR2, then FCNVDS to single; 7 boundary inputs")
    for value in (0,1,2,0x80000000,0xffffffff):
        m=target.Machine();m.reg[3]=value;m.map(0x100000,struct.pack("<H",0x4305))
        m.step(0x100000)
        assert m.reg[3]==((value>>1)|((value&1)<<31)) and m.t==value&1
    controls.append("ROTR result and T carry; 5 boundary inputs")
    for delay in (False,True):
        m=target.Machine();m.reg[1]=0x2040;m.reg[0]=0xa1b2c3d4;m.map(0x2040,bytes(4))
        code=(0xa000,0x01c3) if delay else (0x01c3,0x0009)
        m.map(0x100000,struct.pack("<2H",*code));m.observe_start();m.step(0x100000);m.observe_stop()
        assert m.word(0x2040)==0xa1b2c3d4 and len(m.memory_events)==1
        assert m.memory_events[0]==(int(delay),0x100000+2*int(delay),"write",0x2040,4)
    controls.append("MOVCA.L ordinary and delay slot: exactly one four-byte store; no cache fill invented")
    build=json.loads(args.build.read_text())
    expected=struct.pack("<I11f4I",0xf0000000,80,90,.1,120,90,.1,120,130,.1,80,130,
                         0,0,0x3f800000,0x3f803f80)
    for arm in build["arms"].values():
        machine,_,layout,entry=target.load(Path(arm["elf"]));target.prepare(machine,layout)
        node=layout["nodes"];target.call(machine,layout,entry,node,node)
        assert machine.bytes_at(node+layout["packet_offset"]+32,64)==expected
    controls.append("All four compiled arms match independently known position/depth/UV sprite body bytes")
    report=dict(status="PASS",scope=__doc__,controls=controls,build_sha256=target.profile.sha(args.build),
                script_sha256=target.profile.sha(Path(__file__)),
                target_runner_sha256=target.profile.sha(Path(target.__file__)))
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args())
