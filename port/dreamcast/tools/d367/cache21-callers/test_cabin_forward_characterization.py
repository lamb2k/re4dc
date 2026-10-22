#!/usr/bin/env python3
"""Characterize native prepared forward exchange and void caller failures."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
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
    parser.add_argument("--forward-pair",action="store_true")
    args = parser.parse_args()
    floor=18*1024**3+128*1024**2;start_free=shutil.disk_usage('/mnt/c').free
    assert start_free>=floor,'Fresh C: source-test floor refused'
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
    source_files = ("src/game/event.cpp", "src/game/datactrl.cpp", "include/event.h", "include/datactrl.h", "include/cManager.h","include/read.h","src/game/sce_com.cpp","src/game/dvd.cpp","src/game/read.cpp","src/game/emdata.cpp","src/game/eff_sys.cpp","port/dreamcast/game/platform/native_event_file.cpp","port/dreamcast/game/platform/include/native_cabin.h")
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
                    ("setCommand", "getCommand", "getCondition", "setCondition", "setDelete", "isLoadOk", "waitLoadOk", "isUseOk","waitUseOk","checkCommand", "setClear", "checkMallocRelease","checkCondition","setMallocInfo","setLoadToMram","setLoadToAram")]
    controller=[body('src/game/datactrl.cpp','cDataUnit::setName')]
    controller += [body('src/game/datactrl.cpp','cDataCtrl::'+name).replace('cDataCtrl::','Controller::')for name in ('getNewUnit','setData')]
    effects=[body('src/game/emdata.cpp','GetEmEffId'),body('src/game/eff_sys.cpp','EspDataRelease'),body('src/game/emdata.cpp','EspEmDataSwapPush').replace('void EspEmDataSwapPush(', 'void actual_EspEmDataSwapPush(')]
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
             fragment(r'^unsigned carrier_epoch,[^\n]+'),fragment(r'^bool carrier_fault;'),fragment(r'^const char\* carrier_names\[3\]=[^\n]+'),fragment(r'^const unsigned carrier_sizes\[3\]=[^\n]+'),fragment(r'^const unsigned carrier_certificates\[3\]=[^\n]+')]
    carrier+=['extern "C" int '+name+';'for name in(
        're4dc_cabin_source_unit_valid(const void*,unsigned,unsigned,unsigned)',
        're4dc_cabin_source_unit_retire_ready(const void*,unsigned,unsigned,unsigned,const void*)',
        're4dc_cabin_source_unit_release(void*,unsigned)',
        're4dc_cabin_source_allocation(const void*,unsigned,int*)',
        're4dc_cabin_source_range_available(const void*,unsigned,unsigned)',
        're4dc_cabin_source_swap_buffer(unsigned,unsigned,unsigned)',
        're4dc_cabin_source_free(void*,unsigned,int)')]
    carrier+=['extern "C" const void* re4dc_cabin_source_module(const void*,unsigned);',
              'extern "C" unsigned re4dc_cabin_carrier_reserved(const void*);',
              'extern "C" void* re4dc_cabin_source_alloc(unsigned,int);',
              'static bool run(const char*,unsigned,void*,unsigned);',
              'static void re4dc_cabin_event_bound(const void*,const char*){std::abort();}',
              'static void re4dc_cabin_event_deleted(const void*){std::abort();}']
    carrier += [exact('src/game/datactrl.cpp','extern "C" int '+name+'(')for name in('re4dc_cabin_source_unit_valid','re4dc_cabin_source_unit_retire_ready','re4dc_cabin_source_unit_release','re4dc_cabin_source_range_available')]
    carrier += [exact(carrier_path,signature)for signature in(
        'int carrier_index(', 'bool carrier_overlap(', 'CabinCarrier* carrier_token(', 'CabinCarrier* carrier_range(', 'bool carrier_inside(', 'unsigned carrier_number(', 'bool carrier_current(', 'int carrier_fail(',
        'bool carrier_mram_current(', 'bool carrier_backing_current(', 'bool carrier_can_retire(', 'bool carrier_retirement_ready(',
        'extern "C" int re4dc_cabin_carrier_prepare(', 'extern "C" int re4dc_cabin_carrier_clear(', 'extern "C" int re4dc_cabin_carrier_install(', 'extern "C" int re4dc_cabin_carrier_before_free(',
        'extern "C" int re4dc_cabin_carrier_rebase(', 'extern "C" int re4dc_cabin_carrier_park(',
        'extern "C" unsigned re4dc_cabin_carrier_reserved(', 'extern "C" unsigned re4dc_cabin_carrier_preload_epoch(', 'extern "C" int re4dc_cabin_carrier_unit_available(',
        'extern "C" int re4dc_cabin_carrier_mram_move(', 'extern "C" int re4dc_cabin_carrier_event(',
        'extern "C" void re4dc_cabin_carrier_event_deleted(',
        'extern "C" unsigned re4dc_cabin_carrier_reverse_token(', 'extern "C" int re4dc_cabin_carrier_reverse_complete(',
        'extern "C" int re4dc_cabin_carrier_swap_begin(', 'extern "C" int re4dc_cabin_carrier_swap_scope(',
        'extern "C" int re4dc_cabin_carrier_dma_admit(', 'extern "C" int re4dc_cabin_carrier_dma_copy(',
        'extern "C" const void* re4dc_cabin_carrier_dma_callback(', 'extern "C" int re4dc_cabin_carrier_dma_release(',
        'extern "C" int re4dc_cabin_carrier_swap_end(')]
    carrier += [exact(carrier_path,'extern "C" int re4dc_event_file_name('),
                'static int re4dc_event_file_prepare(const char*,unsigned){std::abort();}',
                'static void re4dc_event_file_moved(){std::abort();}']
    forward=[body('src/game/dvd.cpp','MemorySwap').replace('void MemorySwap(', 'void actual_MemorySwap(')]
    source_module=exact('src/game/read.cpp','extern "C" const void* re4dc_cabin_source_module(')
    manager_methods = ["template <class T>\n" + body("include/cManager.h", "cManager<T>::create", "T* cManager<T>::create(int id)"),
                       "template <class T>\n" + body("include/cManager.h", "cManager<T>::countActiveWork")]
    variants = []
    for forward_receipt in ((0,1)if args.forward_pair else(0,)):
        enabled,cabin,release_refs,preflight=1,1,0,0
        out = args.out / f"forward{forward_receipt}-cabin{cabin}"; out.mkdir()
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
        (out / "forward_actual_memoryswap.inc").write_text("\n".join(forward)+"\n")
        (out / "admission_controller_methods.inc").write_text("\n".join(controller)+"\n")
        (out / "admission_actual_effect_methods.inc").write_text("\n".join(effects)+"\n")
        (out / "forward_source_module.inc").write_text(source_module+"\n")
        command = ["g++", "-std=c++17", "-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
                   "-fno-pie", "-no-pie", "-Wall", "-Wextra", "-fpermissive", "-DRE4DC_GAME=1", f"-DRE4DC_CABIN_SOURCE={cabin}",
                   "-DRE4DC_EVENT_FILES=1","-DRE4DC_EVD_ADMISSION_TXN=1", "-DRE4DC_EVD_START_CLEANUP=1", "-DRE4DC_EVD_START_ROLLBACK=1","-DRE4DC_EVD_DEBUG_READ_CLEANUP=0", "-DRE4DC_EVD_EXEC_FAILURE_CLEANUP=0",f"-DRE4DC_EVD_ARAM_ALLOC_RETRY={enabled}",f"-DRE4DC_EVD_READ_RELEASE_REFS={release_refs}",f"-DRE4DC_EVD_READ_ADMISSION_PREFLIGHT={preflight}", "-DRE4DC_EVD_MODULE_VALIDATE_FIRST=1",f"-DRE4DC_EVD_FORWARD_RECEIPT={forward_receipt}", "-I" + str(out), "-I"+str(HERE),str(HERE / "cabin_forward_characterization_host.cpp"), "-o", str(out / "test")]
        assert shutil.disk_usage('/mnt/c').free>=floor,'Fresh C: source compiler admission refused'
        h064.command(command, out / "compile.txt", 30)
        result = h064.command([out / "test"], out / "run.txt", 15); print(result.splitlines()[-1])
        variants.append(dict(aram_alloc_retry=enabled,cabin_source=cabin,read_release_refs=release_refs,read_admission_preflight=preflight,forward_receipt=forward_receipt, output=result))
    receipt = dict(scope="Bounded accepted first-forward receipt OFF/ON: actual fresh/prior EvtReadSub/Mram, Controller setData/getNewUnit, unit load, module validation, effect owner/release, MemorySwap and native epoch/DMA/reverse predicates. Controlled providers/allocators/module lookup/software scheduler remain boundaries. No private-asset/target/guest/whole-epoch acceptance.",
                   selected_head=transaction.git("rev-parse", "HEAD").decode().strip(), fixture_revision=transaction.FIXTURE_REF,
                   source_sha256=pins, selected_methods=selected, variants=variants,
                   test_sha256={p.name: sha(p.read_bytes()) for p in (Path(__file__), HERE / "cabin_forward_characterization_host.cpp",HERE/'event_start_rollback_host.cpp',HERE/'exec_scenario_boundary.inc',HERE/'exec_transport_boundary.inc',HERE/'exec_cabin_boundary.inc',HERE/'admission_actual_effect_boundary.inc')},
                   host_abi_adapters=["Actual recovered GetRead writes a pointer through an int local; host adapter preserves real DatTbl lookup/slot with pointer-width storage.",
                                      "EvtReadExec's sole (void*)addr signed-int cast is normalized to (void*)(u32)addr, preserving native32 bits instead of host64 sign extension. No admission/failure/free decision changed.",
                                      "Actual cDataCtrl method definitions are renamed Controller:: to bind the host projection. Native cDataUnit fields/types are extracted; Host64 layout is not target layout acceptance.",
                                      "ReadModule exposes the exact pArc/size fields used by these source bodies; its other fields and actual module manager are outside this fixture."],
                   executed_evtreadexec_sha256=sha(next(method for method in event_methods if "int EventMgr::EvtReadExec(" in method).encode()))
    receipt['execution_roots']=['EventMgr::EvtReadMram/EvtReadSub/SetRead/EvtFree','cDataCtrl::setData/getNewUnit','cDataUnit::setCommand/setLoadToAram/setClear','GetEmEffId/EspEmDataSwapPush/EspDataRelease','MemorySwap','re4dc_cabin_source_module','native prepare/swap/owned DMA protocol and reverse-token query']
    receipt['unexecuted_compile_closure']='Actual SetEvt/Event/create/scenario and MRAM allocation bodies remain inherited compile closure. Forward mode7 exercises actual EvtFree/setClear refusal; it does not certify successful target deallocation.'
    receipt['transport_boundaries']=[
        'Fresh controls execute actual Controller setData/getNewUnit and FileExistCheck call; the file service returns controlled synthetic size. The ARAM gap allocator and prior explicit destination return controlled logical1000. Source unit storage is initialized explicitly.',
        'Actual setLoadToAram prepares the native carrier. Certified provider run writes synthetic bytes; source allocation/free predicates verify controlled exact pointers/sizes/heaps. Actual target heap, allocator recovery, file I/O and private assets are unqualified.',
        'Actual read.cpp source-module pArc/size predicate executes against a controlled SearchEmModule binding. EmReadSearch is a counted cached-module boundary; actual caller fresh output write and its failure clearing execute.',
        'Actual owner mapping, effect Push/Release count/final dispatch execute for refs1/2. Five effect-subtable release helpers are controlled exact-owner dispatch counters. Effects already released on armed failure are retained as released; no effect rollback is claimed.',
        'Actual MemorySwap and native owner/DMA protocol execute. Software ARQ progress, cache flush, null DVD queue, returnable missing diagnostic and outer borrow scope are controlled boundaries; actual hardware ARQ/callback scheduling and whole-epoch retirement remain open.',
        'Mutation controls cover pre-swap ownership/row/unit/readEm/module/heap changes and post-copy changes, real repeated role2, initial zero epoch and nonmatching rows. Partial second-copy release refusal retains carrier/read lease and displaced module bytes; no stale restore or delete occurs.',
        'Unsupported initial zero-epoch/repeated-role2/nonmatching-row cases deliberately retain legacy publication, including false success outside the bounded accepted receipt. Prior acquisition/reverse/reset and whole caller lifetime are separate open contracts.']
    output_bytes=sum(p.stat().st_size for p in args.out.rglob('*')if p.is_file());assert output_bytes<=20*1024**2
    receipt['resource_guard']={'start_C_free_bytes':start_free,'finish_C_free_bytes':shutil.disk_usage('/mnt/c').free,'floor_bytes':floor,'output_bytes_before_receipt':output_bytes,'output_limit_bytes':20*1024**2}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
