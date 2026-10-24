#!/usr/bin/env python3
"""Build14 complete Make-derived OFF identity and pinned SH4 ON/core/link gates."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
BASELINE="9b248c5b40a49e4c954ea834fdf665fdbbc314f0"
KOS_PIN="804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
SDK_PIN="33fa4850cacb30dd0ad35485ef035526ec4ce782"
spec=importlib.util.spec_from_file_location("pmu_make_profile",DC/"tools/d367/ui_draw_lean/build_profile.py")
profile=importlib.util.module_from_spec(spec);sys.modules[spec.name]=profile;spec.loader.exec_module(profile)
UNITS={"qa_menu":("qa_menu.o","qa_menu.cpp"),"census":("world_census24.o","world_census24.cpp"),
       "pmu":("perf_phase_miss.o","perf_phase_miss.cpp"),"pace":("pace.o","pace.cpp")}
QA=["DBG_WARP=1","WARP_AFTER_RESET=1","QA_MENU=1","BENCHMARK=0","PMC_ROW=0"]
STACK=["SCENERY_SELECT_ONLY=1","SCENERY_REPLAY_LEAN=1","SCENERY_SUBMIT_BATCH=1"]
PROFILES={"production":[*QA,*STACK,"WORLD_CENSUS24=0"],
          "census":[*QA,*STACK,"WORLD_CENSUS24=1"],
          "standalone":[*QA,*STACK,"WORLD_CENSUS24=1","PACE_VMU_GPU=0","PHASE_METER=0","DISC_READ_METER=0","TAIL_METER=0"]}

def normalized(value,out,tree):
    return value.replace(str(out),"<PROFILE>").replace(str(tree),"<SOURCE>")

def hashes():
    paths=[DC/"game/Makefile",DC/"game/qa_menu.cpp",DC/"game/world_census24.cpp",DC/"game/perf_phase_miss.cpp",
        DC/"game/world_census24.mk",DC/"game/perf_phase_miss.mk",DC/"game/pace.cpp",DC/"game/pace.mk",
        DC/"game/platform/include/world_census24.h",DC/"game/platform/include/perf_phase_miss.h",
        DC/"game/platform/include/perf_phase_accounting.hpp",Path(__file__),
        DC/"tools/d367/ui_draw_lean/build_profile.py",DC/"tools/d367/world_submit_spike/build_profile.py"]
    return {str(p.relative_to(ROOT)):profile.sha(p) for p in paths}

def derive(out,cxx,kos,sdk,options,units):
    profile.SPECIFICATIONS.update(UNITS);profile.PROFILES["selected"]=list(options)
    flags,receipt=profile.derive(out,cxx,kos,sdk,variants=["selected"],units=units)
    return flags["selected"],receipt

def probe(out,tree,kos,sdk,options):
    out.mkdir(parents=True,exist_ok=False)
    with profile.source_tree(tree):
        assignments,_=profile.recipe_inputs(out)
        query=out/"query.mk"
        query.write_text(".PHONY: ppm14-state\nppm14-state:\n\t@:\n"+"\n".join(
            f"$(info PM14_STATE {name}=$({name}))" for name in
            ("PERF_PHASE_MISS","PERF_PHASE_MISS_EVENT","PLATFORM_OBJS","GAME_LDFLAGS"))+"\n")
        command=["make","--no-print-directory","-n","-f","Makefile","-f",str(query),"ppm14-state",*assignments,*options,
            "KOS_CFLAGS="+shlex.join(profile.target_flags(kos)),"KOS_BASE="+str(kos),
            "KOS_LDFLAGS=-T"+str(kos/"utils/ldscripts/shlelf.xc"),"SH4ZAM_DIR="+str(sdk),
            "--assume-old="+str(out/"obj/modules.mk")]
        run=subprocess.run(command,cwd=tree/"port/dreamcast/game",capture_output=True,text=True)
    text=run.stdout+run.stderr;(out/"make.log").write_text(text)
    state={}
    for line in text.splitlines():
        if line.startswith("PM14_STATE "):
            k,v=line[11:].split("=",1);state[k]=v
    return dict(command=command,returncode=run.returncode,state=state,error=text[-1400:] if run.returncode else None)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("output","sh4-cxx","kos-root","sdk-root","toolchain-receipt"):p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--baseline",default=BASELINE)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    builder=profile.Build(out);prefix=str(cxx).removesuffix("g++")
    compiler=builder.run([cxx,"--version"],label="compiler").decode().splitlines()[0]
    verbose=subprocess.run([str(cxx),"-v"],capture_output=True,text=True).stderr
    assert "15.2.0" in compiler and "Thread model: kos" in verbose
    linker=builder.run([prefix+"ld","--version"],label="linker").decode().splitlines()[0]
    assert "2.45.1" in linker
    newlib=cxx.parent.parent/"sh-elf/include/_newlib_version.h"
    assert '#define _NEWLIB_VERSION "4.6.0"' in newlib.read_text()
    for folder,pin in ((kos,KOS_PIN),(sdk,SDK_PIN)):
        assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=folder,text=True).strip()==pin
    frozen=hashes();tree=out/"baseline-tree";tree.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git","archive",args.baseline],cwd=ROOT))) as archive:
        archive.extractall(tree,filter="data")
    artifacts,receipts,flags_by_name,make_states={}, {}, {}, {}
    def compile_unit(name,unit,flags,old=False,zero=False):
        source=(tree if old else ROOT)/"port/dreamcast/game"/UNITS[unit][1]
        common=[*flags,*( ["-DRE4DC_PERF_PHASE_MISS=0"] if zero else [] ),"-iquote",str(source.parent)]
        row={}
        for suffix,phase in (("ii",["-E","-P"]),("o",["-c","-fstack-usage"])):
            target=out/f"{name}-{unit}.{suffix}"
            builder.run([*common,"-x","c++","-",*phase,"-o",target],cwd=source.parent,source=source.read_bytes(),label=name+"-"+unit+"-"+suffix)
            row[suffix]=dict(bytes=target.stat().st_size,sha256=profile.sha(target))
            if suffix=="o":row[suffix].update(profile.sections(target),stack_usage=profile.stack_usage(target.with_suffix(".su")))
        artifacts.setdefault(name,{})[unit]=row
    off=0
    for kind,options in PROFILES.items():
        units=("qa_menu",) if kind=="production" else ("qa_menu","census")
        for arm,extra in (("baseline",[]),("absent",[]),("zero",["PERF_PHASE_MISS=0"])):
            name=kind+"-"+arm
            if arm=="baseline":
                with profile.source_tree(tree):flags,receipt=derive(out/name,cxx,kos,sdk,options+extra,units)
            else:flags,receipt=derive(out/name,cxx,kos,sdk,options+extra,units)
            flags_by_name[name]=flags;receipts[name]=receipt
            for unit in units:
                if arm!="baseline":
                    a=[normalized(x,out/(kind+"-baseline"),tree) for x in flags_by_name[kind+"-baseline"][unit]]
                    b=[normalized(x,out/name,ROOT) for x in flags[unit]]
                    assert a==b,(name,unit,"flags")
                compile_unit(name,unit,flags[unit],arm=="baseline",arm=="zero")
                if arm!="baseline":
                    for suffix in ("ii","o"):
                        assert (out/f"{name}-{unit}.{suffix}").read_bytes()==(out/f"{kind}-baseline-{unit}.{suffix}").read_bytes(),(name,unit,suffix)
                        off+=1
            q=probe(out/(name+"-make"),tree if arm=="baseline" else ROOT,kos,sdk,options+extra)
            assert q["returncode"]==0,q
            assert not any(x.endswith("/perf_phase_miss.o") for x in q["state"]["PLATFORM_OBJS"].split())
            make_states[name]=q
            if arm!="baseline":
                for field in ("PLATFORM_OBJS","GAME_LDFLAGS"):
                    assert normalized(q["state"][field],out/(name+"-make"),ROOT)==normalized(
                        make_states[kind+"-baseline"]["state"][field],out/(kind+"-baseline-make"),tree)
                assert q["state"]["PERF_PHASE_MISS"]=="0"
        print("PASS OFF",kind,flush=True)
    enabled=[];integer={};links={}
    for kind,event in (("census",15),("census",37),("standalone",15)):
        name=f"{kind}-event{event}"
        options=PROFILES[kind]+["PERF_PHASE_MISS=1",f"PERF_PHASE_MISS_EVENT={event}"]
        units=("qa_menu","census","pmu","pace")
        flags,receipt=derive(out/name,cxx,kos,sdk,options,units);receipts[name]=receipt;flags_by_name[name]=flags
        for unit in units:
            compile_unit(name,unit,flags[unit])
            if unit!="pace":assert flags[unit].count("-DRE4DC_PERF_PHASE_MISS=1")==1
            else:assert not any("RE4DC_PERF_PHASE_MISS" in x for x in flags[unit])
            if unit in ("census","pmu"):
                source=DC/"game"/UNITS[unit][1];assembly=out/f"{name}-{unit}.s"
                builder.run([*flags[unit],"-S",source,"-o",assembly],cwd=source.parent,label=name+"-"+unit+"-assembly")
                floating=[s for s in assembly.read_text().splitlines() if re.match(r"\s+(?:f[a-z0-9./]*(?:\s|$)|(?:lds|sts)(?:\.l)?\s+.*(?:fpscr|fpul))",s)]
                assert not floating,(name,unit,floating)
                integer[name+"-"+unit]=dict(fpu_instructions=0,assembly_sha256=profile.sha(assembly),scope="All compiler-emitted instructions; external callees excluded")
        linked=out/(name+"-combined.o")
        builder.run([prefix+"ld","-m","shlelf","-r",*[out/f"{name}-{u}.o" for u in units],"-o",linked],label=name+"-partial-link")
        undefined=builder.run([prefix+"nm","-u","-C",linked],label=name+"-undefined").decode()
        assert not any("re4dc::ppm14::" in s for s in undefined.splitlines()),undefined
        symbols=builder.run([prefix+"nm","--defined-only",linked],label=name+"-symbols").decode()
        assert sum(s.endswith(" ___wrap_pvr_sync_stats") for s in symbols.splitlines())==1,(name,"wrapper count")
        links[name]=dict(sha256=profile.sha(linked),new_hooks_resolved=True,pvr_sync_stats_wrappers=1)
        q=probe(out/(name+"-make"),ROOT,kos,sdk,options);assert q["returncode"]==0
        assert sum(x.endswith("/perf_phase_miss.o") for x in q["state"]["PLATFORM_OBJS"].split())==1
        make_states[name]=q;enabled.append(name);print("PASS ON",name,flush=True)
    rejects=[]
    for i,change in enumerate(("PERF_PHASE_MISS=2","PERF_PHASE_MISS=0 1","PERF_PHASE_MISS=", "WORLD_CENSUS24=0",
        "PMC_ROW=1","PERF_PHASE_MISS_EVENT=0","PERF_PHASE_MISS_EVENT=4","PERF_PHASE_MISS_EVENT=15 37",
        "PERF_PHASE_MISS_EVENT=","QA_MENU=0","PS2_WORLD_MESH=0","PVR_STREAM=0","MESH_DIRECT=0","TA_DIRECT=0")):
        q=probe(out/f"reject-{i}",ROOT,kos,sdk,PROFILES["census"]+["PERF_PHASE_MISS=1",change])
        assert q["returncode"]!=0,(change,"accepted")
        rejects.append(dict(change=change,**q))
    assert hashes()==frozen,"source changed"
    restoration=json.loads(args.toolchain_receipt.read_text())
    report=dict(status="PASS",scope=__doc__,baseline=args.baseline,source_sha256=frozen,
        compiler=compiler,compiler_sha256=profile.sha(cxx),linker=linker,linker_sha256=profile.sha(Path(prefix+"ld")),
        newlib_header_sha256=profile.sha(newlib),kos=KOS_PIN,sh4zam=SDK_PIN,
        toolchain_provenance=dict(path=str(args.toolchain_receipt),sha256=profile.sha(args.toolchain_receipt),image=restoration.get("image"),
            scope="Verified restored prebuilt with recorded actual hashes; not the lost Build10 binary"),
        off_identity_comparisons=off,enabled_profiles=enabled,artifacts=artifacts,integer_cores=integer,
        partial_links=links,make_states=make_states,make_rejections=rejects,profile_receipts=receipts,
        pinned_pmu=dict(header_sha256=profile.sha(kos/"kernel/arch/dreamcast/include/dc/perfctr.h"),
            implementation_sha256=profile.sha(kos/"kernel/arch/dreamcast/kernel/perfctr.c")),
        limitations="Complete TUs and partial links only; no final game/console run. Diagnostic event behavior is unqualified until target controls respond.")
    (out/"target-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",off_comparisons=off,enabled=enabled,rejections=len(rejects))))

if __name__=="__main__":main()
