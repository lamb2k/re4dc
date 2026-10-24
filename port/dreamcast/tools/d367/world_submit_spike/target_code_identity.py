#!/usr/bin/env python3
"""Tie the isolated UI cost bodies to the complete production TU objects.

No executable instruction difference is accepted. A moved literal pointer to
the identical three-value PVR cull table may differ because the fixture removes
cold loading code. That relocation and all twelve table bytes are checked.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]


def elf(path):
    data=path.read_bytes()
    assert data[:6]==b"\x7fELF\x01\x01"
    offset=struct.unpack_from("<I",data,32)[0]
    size,count,names=struct.unpack_from("<3H",data,46)
    rows=[struct.unpack_from("<10I",data,offset+i*size) for i in range(count)]
    row=rows[names];strings=data[row[4]:row[4]+row[5]]
    names=[strings[row[0]:].split(b"\0",1)[0].decode() for row in rows]
    return data,rows,names


def body(path,name):
    data,rows,names=elf(path)
    index=names.index(name);row=rows[index]
    code=data[row[4]:row[4]+row[5]];relocations={}
    for rel in rows:
        if rel[1]!=4 or rel[7]!=index:continue
        symbols=rows[rel[6]]
        for at in range(rel[4],rel[4]+rel[5],12):
            offset,info,addend=struct.unpack_from("<IIi",data,at)
            symbol=struct.unpack_from("<IIIBBH",data,symbols[4]+(info>>8)*16)
            target=rows[symbol[5]]
            location=struct.unpack_from("<I",code,offset)[0]+symbol[1]+addend
            relocations[offset]=dict(kind=info&255,target=names[symbol[5]],
                location=location,payload=data[target[4]+location:target[4]+location+12])
    return code,relocations


def compare(production,fixture,name):
    a,ar=body(production,name);b,br=body(fixture,name)
    assert len(a)==len(b),(name,"body size")
    differences=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    ac=bytearray(a);bc=bytearray(b);moved=[]
    for at in sorted({i&~3 for i in differences}):
        assert at in ar and at in br,(name,"nonrelocation instruction difference",at)
        x,y=ar[at],br[at]
        expected=struct.pack("<3I",0,2,3)  # NONE, CCW, CW in pinned KOS pvr.h
        assert x["kind"]==y["kind"]==1 and x["target"]==y["target"]==".rodata"
        assert x["payload"]==y["payload"]==expected,(name,"cull table changed",at)
        ac[at:at+4]=bc[at:at+4]=bytes(4)
        moved.append(dict(offset=at,kind="R_SH_DIR32",target=".rodata",
                          production_offset=x["location"],fixture_offset=y["location"],
                          identical_cull_table=[0,2,3]))
    assert ac==bc,(name,"normalized instruction bytes")
    return dict(section=name,bytes=len(a),raw_equal=a==b,
                production_sha256=hashlib.sha256(a).hexdigest(),
                fixture_sha256=hashlib.sha256(b).hexdigest(),
                normalized_sha256=hashlib.sha256(ac).hexdigest(),moved_cull_literals=moved)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production",type=Path,required=True)
    parser.add_argument("--target",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    production=json.loads((args.production/"build-controls.json").read_text())
    target=json.loads((args.target/"target-build-controls.json").read_text())
    assert production["baseline"]==target["baseline"]
    for name,expected in production["source_sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,(name,"production source changed")
    names={"baseline":["re4dc_ps2_world_direct_begin","re4dc_model_direct_end"],
           "batch":["re4dc_ps2_world_direct_begin_batch","re4dc_ps2_world_direct_begin",
                    "re4dc_ps2_world_direct_end_batch","re4dc_ps2_world_batch_close",
                    "re4dc_model_direct_end","_ZL20model_direct_accountj"]}
    arms={}
    for arm,functions in names.items():
        before=args.production/("native_ui-"+("on" if arm=="batch" else "baseline")+".o")
        after=args.target/(arm+"-fixture.o")
        arms[arm]=[compare(before,after,".text."+name) for name in functions]
    runtime=[ROOT/"port/dreamcast/game/platform/native_static.cpp",
             ROOT/"port/dreamcast/game/platform/native_ui.cpp",
             ROOT/"port/dreamcast/game/platform/include/scenery_submit_batch.h",
             ROOT/"port/dreamcast/game/scenery19.mk"]
    report=dict(status="PASS",scope=__doc__,arms=arms,
        checked_current_runtime_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime},
        production_receipt_sha256=hashlib.sha256((args.production/"build-controls.json").read_bytes()).hexdigest(),
        target_receipt_sha256=hashlib.sha256((args.target/"target-build-controls.json").read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        sr_model_audit=dict(stc_sr=dict(issue=2,latency=2),ldc_sr=dict(issue=4,latency=4),
            group="CO, no pairing",manual="SH7091 Programming Manual, Figure 8.2, pages 152-153",
            source="port/dreamcast/tools/hwmodel/hwsim.c",external_bus_latency_modeled=False))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":"PASS","bodies":sum(map(len,arms.values()))}))


if __name__=="__main__":main()
