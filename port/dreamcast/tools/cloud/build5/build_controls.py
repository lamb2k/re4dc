#!/usr/bin/env python3
"""Build 5: complete Make-derived Test22 OFF identities and composition.

The base Make tree is archived from the named integration commit. Actual
recipes and generated headers must agree with absent/zero, with ON adding
only the native_static define. Complete preprocessed TUs and executable
objects compare byte for byte. Line markers/debug line records are omitted.
Identical compiler inputs across combinations reuse an explicitly recorded
artifact; baseline/current and absent/explicit-CPP-zero are distinct inputs.
"""
import argparse
from contextlib import contextmanager
import hashlib
import io
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
BASELINE="dc87c4658d65ba992d266e3cb1893ecd485da661"
KNOBS=("SCENERY_SELECT_ONLY","SCENERY_SUBMIT_BATCH","SCENERY_REPLAY_LEAN",
       "SCENERY_SELECT_LEAN2","SCENERY_UV_SNAPSHOT")
sys.path.insert(0,str(DC/"tools/d367/world_select_lean2"))
import build_profile as profile_tools


@contextmanager
def source_tree(tree):
    modules=(profile_tools,profile_tools.helpers,profile_tools.helpers.release_profile)
    saved=[(m,m.ROOT,m.DC) for m in modules]
    try:
        for m in modules:m.ROOT,m.DC=tree,tree/"port/dreamcast"
        yield
    finally:
        for m,root,dc in saved:m.ROOT,m.DC=root,dc


def normalized(flags,profile,tree):
    return [x.replace(str(profile),"<PROFILE>").replace(str(tree),"<SOURCE>") for x in flags]


def headers(profile,root):
    return {str(Path(p).relative_to(root)):digest for p,digest in profile["generated_headers"].items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--sh4-cxx",type=Path,required=True)
    parser.add_argument("--kos-root",type=Path,required=True)
    parser.add_argument("--sdk-root",type=Path,required=True)
    parser.add_argument("--baseline",default=BASELINE)
    parser.add_argument("--profile-only",action="store_true")
    parser.add_argument("--quick",action="store_true",help="Compile only the all-prior-knobs-enabled combination")
    parser.add_argument("--knob",action="append",default=[],help="Extra Make assignment for a focused surrounding configuration")
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    compiler,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    flags,profile=profile_tools.derive(out/"release-profile",compiler,kos,sdk,actor=True)
    if args.profile_only:
        (out/"profile.json").write_text(json.dumps(dict(flags=flags,profile=profile),indent=2)+"\n")
        print(json.dumps(dict(status="PASS",profile=str(out/"profile.json"))));return
    tree=out/"baseline-tree";tree.mkdir()
    archive=subprocess.check_output(["git","archive",args.baseline],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:stream.extractall(tree,filter="data")
    with source_tree(tree):
        _,old_profile=profile_tools.derive(out/"baseline-profile",compiler,kos,sdk,actor=True)
    baseline_platform=out/"baseline-platform";(baseline_platform/"include").mkdir(parents=True)
    for p in (tree/"port/dreamcast/game/platform/include").glob("scenery_*"):
        if p.is_file():shutil.copyfile(p,baseline_platform/"include"/p.name)
    sources={}
    for tu in ("native_static","native_ui","native_actor_fast"):
        path=DC/"game/platform"/(tu+".cpp")
        sources[tu]=(path,(tree/path.relative_to(ROOT)).read_bytes(),path.read_bytes())
    watched=[p[0] for p in sources.values()]+[DC/"game/scenery19.mk",*sorted((DC/"game/platform/include").glob("scenery_*"))]
    hashes={str(p.relative_to(ROOT)):profile_tools.sha(p) for p in watched if p.is_file()}
    builder=profile_tools.Build(out);cache={};cache_receipts=[]

    def compile_one(label,common,content,cwd,suffix):
        target=out/(label+"."+suffix)
        phase=["-E","-P"] if suffix=="ii" else ["-c","-fstack-usage"]
        key=hashlib.sha256(json.dumps([common,str(cwd),phase],separators=(",",":")).encode()+content).hexdigest()
        if key in cache:
            prior=cache[key];shutil.copyfile(prior,target)
            if suffix=="o":shutil.copyfile(prior.with_suffix(".su"),target.with_suffix(".su"))
            cache_receipts.append(dict(target=target.name,reused_from=prior.name,input_sha256=key))
        else:
            builder.run([*common,"-x","c++","-",*phase,"-o",target],cwd=cwd,source=content,label=label)
            cache[key]=target
        result=dict(bytes=target.stat().st_size,sha256=profile_tools.sha(target),compiler_input_sha256=key)
        if suffix=="o":
            result.update(profile_tools.sections(target))
            result["stack_usage"]=profile_tools.stack_usage(target.with_suffix(".su"))
        return result

    production={};make_checks={}
    combinations=[(1,1,1,1,1)] if args.quick else itertools.product((0,1),repeat=5)
    for bits in combinations:
        name="s%d-b%d-r%d-q%d-u%d" % bits
        options=["%s=%d" % (k,v) for k,v in zip(KNOBS,bits)]+args.knob
        with source_tree(tree):
            base_flags,base_rec=profile_tools.expand_existing(out/"baseline-profile",compiler,sdk,old_profile,
                options,actor=True,prefix=name)
        arm_flags={};arm_receipts={}
        for arm,extra in (("absent",[]),("zero",["SCENERY_EMIT_PREFETCH=0"]),("on",["SCENERY_EMIT_PREFETCH=1"])):
            arm_flags[arm],arm_receipts[arm]=profile_tools.expand_existing(out/"release-profile",compiler,sdk,profile,
                options+extra,actor=True,prefix=name+"-"+arm)
        production[name]={};make_checks[name]={}
        for tu,(path,old,current) in sources.items():
            baseline=normalized(base_flags[tu],out/"baseline-profile",tree)
            for arm in ("absent","zero","on"):
                actual=normalized(arm_flags[arm][tu],out/"release-profile",ROOT)
                expected=baseline+(["-DRE4DC_SCENERY_EMIT_PREFETCH=1"] if arm=="on" and tu=="native_static" else [])
                if arm=="on" and tu=="native_static":
                    assert actual.count("-DRE4DC_SCENERY_EMIT_PREFETCH=1")==1,(name,tu,"missing define")
                    actual=[x for x in actual if x!="-DRE4DC_SCENERY_EMIT_PREFETCH=1"]
                    expected=baseline
                assert actual==expected,(name,tu,arm,"Make flags OFF/ON wiring")
                assert headers(arm_receipts[arm][tu],out/"release-profile")==headers(base_rec[tu],out/"baseline-profile"),(name,tu,arm,"generated headers")
            make_checks[name][tu]=dict(flags_identical_off=True,generated_headers_identical=True,on_adds_only_static_define=True,
                absent_flags_sha256=hashlib.sha256(json.dumps(baseline).encode()).hexdigest())
            records={}
            for arm in ("baseline","absent","zero","on"):
                content=old if arm=="baseline" else current
                common=arm_flags["absent" if arm=="baseline" else arm][tu]+["-iquote",str(path.parent)]
                if arm=="zero" and tu=="native_static":common.append("-DRE4DC_SCENERY_EMIT_PREFETCH=0")
                cwd=baseline_platform if arm=="baseline" else path.parent
                label=name+"-"+tu+"-"+arm
                for suffix in ("ii","o"):
                    records[arm+"."+suffix]=compile_one(label,common,content,cwd,suffix)
                    if arm in ("absent","zero") or (arm=="on" and tu!="native_static"):
                        before=out/(name+"-"+tu+"-baseline."+suffix)
                        assert (out/(label+"."+suffix)).read_bytes()==before.read_bytes(),(label,suffix,"OFF/unaffected-TU identity")
            production[name][tu]=records
        print("PASS",name,flush=True)
    for path,digest in hashes.items():assert profile_tools.sha(ROOT/path)==digest,(path,"source changed during build")
    report=dict(status="PASS",baseline=args.baseline,knob="SCENERY_EMIT_PREFETCH",scope=__doc__,
        configurations=len(production),extra_make_assignments=args.knob,translation_units=3,off_identity_comparisons=len(production)*3*2*2,
        enabled_unaffected_tu_identities=len(production)*2*2,unique_compiler_invocations=len(cache),
        compiler=builder.run([compiler,"--version"],label="compiler").decode().splitlines()[0],
        source_sha256=hashes,profile=profile,make_identity=make_checks,production=production,artifact_reuse=cache_receipts)
    (out/"build-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","configurations","translation_units","off_identity_comparisons","enabled_unaffected_tu_identities","unique_compiler_invocations")}))


if __name__=="__main__":main()
