#!/usr/bin/env python3
"""Check real Make wiring, five-knob combinations and existing guard contracts."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shlex
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
KNOBS=("SCENERY_SELECT_ONLY","SCENERY_SUBMIT_BATCH","SCENERY_REPLAY_LEAN",
       "ACTOR_SETUP_LEAN","SCENERY_UV_SNAPSHOT")


def guard_cases():
    return [("cone",["SCENERY_CONE=1"],True),
        ("sg0",["SG_SELECT_LEAN=0"],True),("sg2",["SG_SELECT_LEAN=2"],True),
        ("pvs",["PS2_PVS=1","SCENERY_SUBMIT_BATCH=0"],True),
        ("pvs-batch-rejected",["PS2_PVS=1","SCENERY_SUBMIT_BATCH=1"],False),
        ("interior0",["PS2_INTERIOR_CULL=0"],True),
        ("interior1",["PS2_INTERIOR_CULL=1"],True),
        ("interior2",["PS2_INTERIOR_CULL=2"],True),
        ("interior3",["PS2_INTERIOR_CULL=3"],True),
        ("quality0",["QUALITY_ASSETS=0","PS2_PRELOAD_LEAN=0"],True),
        ("quality1",["QUALITY_ASSETS=1"],True),
        ("foliage-full",["FOLIAGE_TRIM=","FOLIAGE_NEAR_FIX=0","FOLIAGE_OPTION=0"],True),
        ("foliage-near",["FOLIAGE_TRIM=1"],True),
        ("foliage-off",["FOLIAGE_TRIM=2"],True),
        ("foliage-invalid",["FOLIAGE_TRIM=0"],False),
        *[(f"trans-{m}",[f"TRANS_POLICY={m}"],True) for m in (0,1,3,15,128,143)],
        ("trans-reserved",["TRANS_POLICY=16"],False),
        ("trans-invalid",["TRANS_POLICY=256"],False)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();payload=json.loads(args.profile.read_text());profile=payload.get("profile",payload)
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cases=[("default",[],True,(0,0,0,0,0),0)]
    for bits in itertools.product((0,1),repeat=5):
        name="s%d-b%d-r%d-a%d-u%d" % bits
        options=["%s=%d" % (k,v) for k,v in zip(KNOBS,bits)]
        for state,extra in (("absent",[]),("zero",["SCENERY_SELECT_LEAN2=0"]),("on",["SCENERY_SELECT_LEAN2=1"])):
            cases.append((name+"-"+state,options+extra,True,bits,int(state=="on")))
    cases.extend((name,options,False,None,None) for name,options in
        (("invalid",["SCENERY_SELECT_LEAN2=2"]),("negative",["SCENERY_SELECT_LEAN2=-1"]),
         ("no-chunk",["SCENERY_SELECT_LEAN2=1","SCENERY_CHUNK=0"])))
    for name,options,accepted in guard_cases():
        bits=[0]*5
        for word in options:
            for i,k in enumerate(KNOBS):
                if word.startswith(k+"="):bits[i]=int(word.split("=",1)[1])
        cases.append((name,["SCENERY_SELECT_LEAN2=1",*options],accepted,tuple(bits),1))
    rows=[]
    for name,options,accepted,bits,on in cases:
        row=dict(name=name,options=options,accepted=accepted)
        for tu in ("native_static","native_ui","native_actor_fast"):
            command=profile[tu]["command"]+options
            run=subprocess.run(command,cwd=DC/"game",text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            (out/(name+"-"+tu+".log")).write_text(run.stdout)
            assert (run.returncode==0)==accepted,(name,tu,run.stdout)
            if accepted:
                commands=[shlex.split(line) for line in run.stdout.replace("\\\n"," ").splitlines() if line.startswith("kos-c++ ")]
                assert len(commands)==1,(name,tu)
                assert ("-DRE4DC_SCENERY_SELECT_LEAN2=1" in commands[0])==bool(on and tu=="native_static"),(name,tu,"new define")
                for knob,mode in zip(KNOBS,bits):
                    touched={"SCENERY_SELECT_ONLY":("native_static",),"SCENERY_SUBMIT_BATCH":("native_static","native_ui"),
                        "SCENERY_REPLAY_LEAN":("native_static",),"ACTOR_SETUP_LEAN":("native_actor_fast",),
                        "SCENERY_UV_SNAPSHOT":("native_static",)}[knob]
                    assert ("-DRE4DC_"+knob+"=1" in commands[0])==bool(mode and tu in touched),(name,tu,knob)
            row[tu]=dict(exit=run.returncode,diagnostics=[s for s in run.stdout.splitlines() if "***" in s])
        rows.append(row)
    report=dict(status="PASS",scope=__doc__,configurations=len(rows),translation_units=3,cases=rows,
        source_sha256=hashlib.sha256((DC/"game/scenery19.mk").read_bytes()).hexdigest())
    (out/"knob-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","configurations","translation_units")}))


if __name__=="__main__":main()
