#!/usr/bin/env python3
"""Compile complete world TUs with the selection's existing guard variants.

Each accepted configuration comes from Make. Baseline, absent, explicit-zero
and enabled are compiled independently. The ordinary 32-way matrix is covered
by build_controls.py; this gate varies the surrounding compatibility options.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
BASELINE="75229c8fa54d4a939095666036c8ee1c8f52e2fe"
import build_profile
from verify_knobs import guard_cases


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--sh4-cxx",type=Path,required=True)
    p.add_argument("--kos-root",type=Path,required=True)
    p.add_argument("--sdk-root",type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    compiler,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    static=DC/"game/platform/native_static.cpp"
    current=static.read_bytes()
    old=subprocess.check_output(["git","show",BASELINE+":"+str(static.relative_to(ROOT))],cwd=ROOT)
    original=out/"baseline-platform";(original/"include").mkdir(parents=True)
    for name in ("scenery_chunk_select.inc","scenery_part_far.inc","scenery_submit_batch.h"):
        path=static.parent/"include"/name
        (original/"include"/name).write_bytes(subprocess.check_output(["git","show",BASELINE+":"+str(path.relative_to(ROOT))],cwd=ROOT))
    selected={"cone","sg0","sg2","pvs","interior0","interior2","interior3","quality0",
              "foliage-full","foliage-near","trans-0","trans-143"}
    builder=build_profile.Build(out);rows={}
    hashes={str(path.relative_to(ROOT)):build_profile.sha(path) for path in (static,static.parent/"include/scenery_chunk_select.inc",static.parent/"include/scenery_select_lean2.inc",DC/"game/scenery19.mk",Path(__file__),HERE/"build_profile.py")}
    for name,options,accepted in guard_cases():
        if name not in selected:continue
        assert accepted
        profile_dir=out/(name+"-profile")
        _,profile=build_profile.derive(profile_dir,compiler,kos,sdk)
        # A surrounding setting such as QUALITY_ASSETS legitimately changes a
        # generated header. Materialize its own first recipe into this fresh,
        # private profile directory; OFF and ON must then agree within it.
        generated=set(path for name in ("native_static","native_ui")
            for path in profile[name]["generated_headers"])
        for path in generated:
            target=Path(path)
            assert target.is_relative_to(profile_dir/"obj")
            target.unlink()
        common=["SCENERY_SELECT_ONLY=1","SCENERY_SUBMIT_BATCH=0","SCENERY_REPLAY_LEAN=1","SCENERY_UV_SNAPSHOT=1","ACTOR_SETUP_LEAN=1",*options]
        before,before_receipt=build_profile.expand_existing(profile_dir,compiler,sdk,profile,common,prefix=name+"-off")
        after,after_receipt=build_profile.expand_existing(profile_dir,compiler,sdk,profile,common+["SCENERY_SELECT_LEAN2=1"],prefix=name+"-on")
        assert [x for x in after["native_static"] if x!="-DRE4DC_SCENERY_SELECT_LEAN2=1"]==before["native_static"]
        records={}
        for arm in ("baseline","absent","zero","on"):
            flags=(after if arm=="on" else before)["native_static"]+["-iquote",str(static.parent)]
            if arm=="zero":flags.append("-DRE4DC_SCENERY_SELECT_LEAN2=0")
            source=old if arm=="baseline" else current
            cwd=original if arm=="baseline" else static.parent
            for suffix,phase in (("ii",["-E","-P"]),("o",["-c","-fstack-usage"])):
                label=name+"-"+arm;target=out/(label+"."+suffix)
                builder.run([*flags,"-x","c++","-",*phase,"-o",target],cwd=cwd,source=source,label=label)
                record=dict(bytes=target.stat().st_size,sha256=build_profile.sha(target))
                if suffix=="o":record.update(build_profile.sections(target));record["stack_usage"]=build_profile.stack_usage(target.with_suffix(".su"))
                if arm in ("absent","zero"):
                    assert target.read_bytes()==(out/(name+"-baseline."+suffix)).read_bytes(),(name,arm,suffix,"OFF identity")
                records[arm+"."+suffix]=record
        rows[name]=dict(options=common,production=records,off_recipe=before_receipt["native_static"],on_recipe=after_receipt["native_static"])
        print("PASS",name,flush=True)
    assert len(rows)==len(selected)
    for path,digest in hashes.items():assert build_profile.sha(ROOT/path)==digest,(path,"source changed")
    report=dict(status="PASS",scope=__doc__,baseline=BASELINE,profiles=len(rows),off_identity_comparisons=len(rows)*4,
        source_sha256=hashes,production=rows)
    (out/"guard-build-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","profiles","off_identity_comparisons")}))


if __name__=="__main__":main()
