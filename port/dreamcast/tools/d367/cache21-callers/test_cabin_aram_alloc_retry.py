#!/usr/bin/env python3
"""Qualify exact cabin epoch and prior-ARAM allocation refusal restoration."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(HERE.parent / 'cache21-fixes'))
import test_event_admission_txn as transaction


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--release-refs-pair",action="store_true")
    parser.add_argument("--preflight-pair",action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    fixture = args.out / "h064-fixture" / transaction.FIXTURE_DIR
    fixture.mkdir(parents=True)
    pins = {}
    for name in transaction.FIXTURE_FILES:
        data = transaction.git("show", f"{transaction.FIXTURE_REF}:{transaction.FIXTURE_DIR}/{name}")
        (fixture / name).write_bytes(data); pins[name] = sha(data)
    sys.path.insert(0, str(fixture))
    spec = importlib.util.spec_from_file_location("h064_caller_fixture", fixture / "test_motion_lifetime.py")
    h064 = importlib.util.module_from_spec(spec); spec.loader.exec_module(h064)
    source_files = ("src/game/event.cpp", "src/game/datactrl.cpp", "include/event.h", "include/datactrl.h", "include/cManager.h","src/game/sce_com.cpp","port/dreamcast/game/platform/native_event_file.cpp","port/dreamcast/game/platform/include/native_cabin.h")
    source = {}
    for name in source_files:
        data = (REPO / name).read_bytes(); source[name] = data.decode(); pins[name] = sha(data)
        target = args.out / "source" / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    selected = []

    def body(path, name, signature=None):
        text = source[path]
        if signature:
            begin = text.index(signature)
            end = begin + re.search(r"^}", text[begin:], re.M).end()
            result, line = h064.fn(text[begin:end], name)
            line += text.count("\n", 0, begin)
        else:
            result, line = h064.fn(text, name)
        selected.append(dict(path=path, name=name, signature=signature, line=line, sha256=sha(result.encode())))
        return result

    event_methods = [body("src/game/event.cpp", name) for name in transaction.METHODS]
    event_methods += [body("src/game/event.cpp", "EventMgr::SetEvt", signature)
                      for signature in ("int EventMgr::SetEvt(void* data, u32* key)", "int EventMgr::SetEvt(char* nm, Event** out)")]
    event_methods += [body("src/game/event.cpp", name) for name in ("EventMgr::EvtReadExec", "EventMgr::EvtFree", "EventMgr::DelRead", "EventMgr::IsAliveEvt","EventMgr::GetBin","EventMgr::EvtReadMram","EventMgr::EvtReadSub","EventMgr::SetRead")]
    # Native32 int->pointer preserves the address bits. Host64 sign-extends a
    # negative int, so normalize only that cast, without changing any decision.
    cast = "EvtMgr.SetEvt((void*) addr, (u32*) &evt)"
    assert sum(method.count(cast) for method in event_methods) == 1
    event_methods = [method.replace(cast, "EvtMgr.SetEvt((void*) (u32) addr, (u32*) &evt)") for method in event_methods]
    unit_methods = [body("src/game/datactrl.cpp", "cDataUnit::" + name) for name in
                    ("setCommand", "getCommand", "getCondition", "isLoadOk", "waitLoadOk", "isUseOk","waitUseOk","checkCommand", "setClear", "checkMallocRelease","checkCondition","setMallocInfo","setLoadToMram")]
    task_flag=re.search(r'^static inline void SceTaskFlagSet[^\n]+',source['src/game/sce_com.cpp'],re.M)[0]
    selected.append(dict(path='src/game/sce_com.cpp',name='SceTaskFlagSet',sha256=sha(task_flag.encode())))
    scenario=[body('src/game/sce_com.cpp','SceEventStart'),task_flag,body('src/game/sce_com.cpp','SceEventEnd')]
    scenario=[method.replace('void SceEventStart(int mode)','void actual_SceEventStart(int mode)').replace('void SceEventEnd(int mode)','void actual_SceEventEnd(int mode)')for method in scenario]
    carrier_path='port/dreamcast/game/platform/native_event_file.cpp'
    def exact(path,signature):
        text=source[path];begin=text.index(signature);masked=h064.fn.__globals__['mask'](text);opening=masked.index('{',begin)
        depth=1;end=opening+1
        while depth:depth+=(masked[end]=='{')-(masked[end]=='}');end+=1
        result=text[begin:end];selected.append(dict(path=path,signature=signature,line=text.count('\n',0,begin)+1,sha256=sha(result.encode())))
        return result
    def fragment(pattern):
        result=re.search(pattern,source[carrier_path],re.M|re.S)[0]
        selected.append(dict(path=carrier_path,fragment=pattern,sha256=sha(result.encode())));return result
    carrier=[fragment(r'enum CarrierState \{[^}]+};'),fragment(r'struct CabinCarrier \{.*?^};'),fragment(r'struct CabinCarrierDma \{.*?^};'),
             fragment(r'^CabinCarrier carriers\[3\]\{\};'),fragment(r'^CabinCarrierDma carrier_dma\[16\]\{\};'),
             fragment(r'^unsigned carrier_epoch,[^\n]+'),fragment(r'^bool carrier_fault;'),fragment(r'^const char\* carrier_names\[3\]=[^\n]+'),fragment(r'^const unsigned carrier_certificates\[3\]=[^\n]+')]
    carrier+=['extern "C" int '+name+';'for name in(
        're4dc_cabin_source_unit_valid(const void*,unsigned,unsigned,unsigned)',
        're4dc_cabin_source_unit_retire_ready(const void*,unsigned,unsigned,unsigned,const void*)',
        're4dc_cabin_source_unit_release(void*,unsigned)',
        're4dc_cabin_source_allocation(const void*,unsigned,int*)',
        're4dc_cabin_source_free(void*,unsigned,int)')]
    carrier+=['extern "C" const void* re4dc_cabin_source_module(const void*,unsigned);',
              'static bool run(const char*,unsigned,void*,unsigned);',
              'static void re4dc_cabin_event_bound(const void*,const char*){std::abort();}',
              'static void re4dc_cabin_event_deleted(const void*){std::abort();}']
    carrier += [exact('src/game/datactrl.cpp','extern "C" int '+name+'(')for name in('re4dc_cabin_source_unit_valid','re4dc_cabin_source_unit_retire_ready','re4dc_cabin_source_unit_release')]
    carrier += [exact(carrier_path,signature)for signature in(
        'int carrier_index(', 'bool carrier_overlap(', 'unsigned carrier_number(', 'bool carrier_current(', 'int carrier_fail(',
        'bool carrier_mram_current(', 'bool carrier_backing_current(', 'bool carrier_can_retire(', 'bool carrier_retirement_ready(',
        'extern "C" int re4dc_cabin_carrier_clear(', 'extern "C" int re4dc_cabin_carrier_install(', 'extern "C" int re4dc_cabin_carrier_before_free(',
        'extern "C" unsigned re4dc_cabin_carrier_reserved(', 'extern "C" unsigned re4dc_cabin_carrier_preload_epoch(',
        'extern "C" int re4dc_cabin_carrier_mram_move(', 'extern "C" int re4dc_cabin_carrier_event(',
        'extern "C" void re4dc_cabin_carrier_event_deleted(',
        'extern "C" unsigned re4dc_cabin_carrier_reverse_token(', 'extern "C" int re4dc_cabin_carrier_reverse_complete(')]
    manager_methods = ["template <class T>\n" + body("include/cManager.h", "cManager<T>::create", "T* cManager<T>::create(int id)"),
                       "template <class T>\n" + body("include/cManager.h", "cManager<T>::countActiveWork")]
    variants = []
    assert not(args.release_refs_pair and args.preflight_pair)
    for enabled,cabin,release_refs,preflight in (((1,1,0,0),(1,1,0,1))if args.preflight_pair else((1,1,0,0),(1,1,1,0))if args.release_refs_pair else((0,1,0,0),(1,1,0,0))):
        out = args.out / f"retry{enabled}-cabin{cabin}-refs{release_refs}-preflight{preflight}"; out.mkdir()
        adapted, changes = transaction.adapt_scaffold((fixture / "motion_event_admission_host.cpp").read_text())
        adapted = adapted.replace("void warn(int,int,const char*,...){}}logger", "void warn(int,int,const char*,...){}void mes(int,int,const char*,...){}}logger")
        assert "void mes(" in adapted
        old = "u32 NowExeEvtKey{},pUnit[32]{};void*emWindowFcv[3]{};};"
        new = ("union{u32 NowExeEvtKey;char NowExeEvtName[48];};u32 pUnit[32]{};void*emWindowFcv[3]{};"
               "Event*create(int);void destroyNow(Event*);int EvtReadSub(char*,int,int,int*,int,u32);int SetRead(char*,int*,void*);char* NameChange(char*);int GetBin(void**,const char*,int);int SetEvt(void*,u32*);int SetEvt(char*,Event**);int DelEvt(void*,int);"
               "int EvtReadExec(char*,int,u32);int EvtReadMram(char*,int,int*,int,u32);int EvtFree(char*);"
               "int GetRead(void**,int*,char*);int DelRead(char*);int IsAliveEvt(u32*,int,int);"
               "Event*pArray{};u32 nArray{},size{};EvtReadEm readEm[8]{};};")
        assert adapted.count(old) == 1; adapted = adapted.replace(old, new)
        adapted = adapted.replace('#include "event_admission_methods.inc"', 'extern EventMgr EvtMgr;\n#include "event_admission_methods.inc"')
        (out / "h064_event_caller_adapted.cpp").write_text(adapted)
        types = [re.search(r"struct " + name + r"\s*\{.*?^};", source["include/event.h"], re.S | re.M)[0]
                 for name in ("DatTblEntry", "EvtHeader", "EvtBinEntry", "EvtReadEm")]
        (out / "event_admission_types.inc").write_text("\n".join(types) + "\n")
        (out / "event_admission_methods.inc").write_text("\n".join(event_methods) + "\n")
        (out / "caller_manager_methods.inc").write_text("\n".join(manager_methods) + "\n")
        (out / "caller_dataunit_types.inc").write_text(re.search(r"class cDataUnit\s*\{.*?^};", source["include/datactrl.h"], re.S | re.M)[0] + "\n")
        (out / "caller_dataunit_methods.inc").write_text("\n".join(unit_methods) + "\n")
        (out / "exec_actual_scenario.inc").write_text("\n".join(scenario)+"\n")
        (out / "aram_actual_carrier.inc").write_text("\n".join(carrier)+"\n")
        command = ["g++", "-std=c++17", "-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
                   "-fno-pie", "-no-pie", "-Wall", "-Wextra", "-fpermissive", "-DRE4DC_GAME=1", f"-DRE4DC_CABIN_SOURCE={cabin}",
                   "-DRE4DC_EVENT_FILES=1","-DRE4DC_EVD_ADMISSION_TXN=1", "-DRE4DC_EVD_START_CLEANUP=1", "-DRE4DC_EVD_START_ROLLBACK=1","-DRE4DC_EVD_DEBUG_READ_CLEANUP=0", "-DRE4DC_EVD_EXEC_FAILURE_CLEANUP=0",f"-DRE4DC_EVD_ARAM_ALLOC_RETRY={enabled}",f"-DRE4DC_EVD_READ_RELEASE_REFS={release_refs}",f"-DRE4DC_EVD_READ_ADMISSION_PREFLIGHT={preflight}", "-I" + str(out), "-I"+str(HERE),str(HERE / "cabin_aram_alloc_retry_host.cpp"), "-o", str(out / "test")]
        h064.command(command, out / "compile.txt", 30)
        result = h064.command([out / "test"], out / "run.txt", 15); print(result, end="")
        variants.append(dict(aram_alloc_retry=enabled,cabin_source=cabin,read_release_refs=release_refs,read_admission_preflight=preflight, output=result))
    receipt = dict(scope="Actual EvtReadSub/Mram plus cDataUnit command/condition/wait/setLoadToMram/allocation metadata/clear and native carrier epoch/install/retirement/refusal predicates; exact source-unit checks. Allocation/provider I/O/heap/free and unrelated actor/scenario services are boundaries. No whole-reset/target/high-water proof.",
                   selected_head=transaction.git("rev-parse", "HEAD").decode().strip(), fixture_revision=transaction.FIXTURE_REF,
                   source_sha256=pins, selected_methods=selected, variants=variants,
                   test_sha256={p.name: sha(p.read_bytes()) for p in (Path(__file__), HERE / "cabin_aram_alloc_retry_host.cpp",HERE/'event_start_rollback_host.cpp',HERE/'exec_scenario_boundary.inc',HERE/'exec_transport_boundary.inc',HERE/'exec_cabin_boundary.inc')},
                   host_abi_adapters=["Actual recovered GetRead writes a pointer through an int local; host adapter preserves real DatTbl lookup/slot with pointer-width storage.",
                                      "EvtReadExec's sole (void*)addr signed-int cast is normalized to (void*)(u32)addr, preserving native32 bits instead of host64 sign extension. No admission/failure/free decision changed."],
                   executed_evtreadexec_sha256=sha(next(method for method in event_methods if "int EventMgr::EvtReadExec(" in method).encode()))
    receipt['execution_roots']=['EventMgr::EvtReadMram/EvtReadSub','EventMgr::EvtFree','cDataUnit::setClear','re4dc_cabin_carrier_preload_epoch']
    receipt['unexecuted_compile_closure']='Actual SetEvt/Event/create/scenario/reverse source bodies remain in the inherited fixture compile closure but are not exercised by this allocation-refusal unit.'
    receipt['transport_boundaries']=[
        'Actual setLoadToMram/command/condition/wait/allocation metadata/clear execute. Allocation returns NULL or the exact controlled host mapping; real target allocator/recovery/stdout scheduling is not certified.',
        'Actual source-unit valid/retire-ready/release and native carrier query/install/clear/retirement/before-free predicates execute. Allocation/provider/free/module service boundaries verify exact pointer/size/heap and synthetic input identities.',
        'Certified provider run is an explicit boundary that writes synthetic bytes, not a private game asset or actual target file qualification.',
        'The query body is exported independently for observational predicate tests in both host arms; whole native-TU disabled object identity separately proves absence with the switch off.',
        'Nine allocation-boundary epoch/row/unit/reader mutations are adversarial controls. They prove refusal to restore/clear current changed state, not absence of every possible callback/reset interleaving.',
        'Source unit storage is explicitly zeroed as in actual initDataUnit. Host64 structures/negative32 pointer conversions remain projections, not native layout/whole-program acceptance.',
        ('EVD_READ_RELEASE_REFS OFF preserves the characterized Count2-clears-unit gap; ON retains exact unit/carrier/readEm for non-final logical releases and exercises the real final Event binding refusal/unbind/retry. Count is not a native reader lease. Module exchange/whole reset remain unqualified.' if args.release_refs_pair else 'Count2 successful release still leaves Count1 registration over a cleared unit in the existing source path. This is a separate characterized shared-release gap, not accepted as repaired.')]
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
