#!/usr/bin/env python3
"""Characterize fresh descriptor admission and existing module-role failures."""
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
    parser.add_argument("--preflight-pair",action="store_true")
    parser.add_argument("--actual-effects",action="store_true")
    parser.add_argument("--module-validate-pair",action="store_true")
    parser.add_argument("--with-preflight",action="store_true")
    args = parser.parse_args()
    assert not(args.preflight_pair and args.module_validate_pair)
    assert not args.module_validate_pair or args.actual_effects
    assert not(args.with_preflight and args.preflight_pair)
    floor=16*1024**3+128*1024**2
    start_free=shutil.disk_usage('/mnt/c').free
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
    source_files = ("src/game/event.cpp", "src/game/datactrl.cpp", "include/event.h", "include/datactrl.h", "include/cManager.h","src/game/sce_com.cpp","src/game/emdata.cpp","src/game/eff_sys.cpp")
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
                    ("setCommand", "getCommand", "getCondition", "setCondition", "setDelete", "isLoadOk", "waitLoadOk", "isUseOk","waitUseOk","checkCommand", "setClear", "checkMallocRelease")]
    controller=[body('src/game/datactrl.cpp','cDataUnit::setName')]
    controller += [body('src/game/datactrl.cpp','cDataCtrl::'+name).replace('cDataCtrl::','Controller::')for name in ('getNewUnit','setData')]
    effects=[body('src/game/emdata.cpp','GetEmEffId'),body('src/game/eff_sys.cpp','EspDataRelease'),body('src/game/emdata.cpp','EspEmDataSwapPush').replace('void EspEmDataSwapPush(', 'void actual_EspEmDataSwapPush(')]
    task_flag=re.search(r'^static inline void SceTaskFlagSet[^\n]+',source['src/game/sce_com.cpp'],re.M)[0]
    selected.append(dict(path='src/game/sce_com.cpp',name='SceTaskFlagSet',sha256=sha(task_flag.encode())))
    scenario=[body('src/game/sce_com.cpp','SceEventStart'),task_flag,body('src/game/sce_com.cpp','SceEventEnd')]
    scenario=[method.replace('void SceEventStart(int mode)','void actual_SceEventStart(int mode)').replace('void SceEventEnd(int mode)','void actual_SceEventEnd(int mode)')for method in scenario]
    manager_methods = ["template <class T>\n" + body("include/cManager.h", "cManager<T>::create", "T* cManager<T>::create(int id)"),
                       "template <class T>\n" + body("include/cManager.h", "cManager<T>::countActiveWork")]
    variants = []
    for enabled,cabin in (((0,0),(1,0),(0,1),(1,1))if args.preflight_pair or args.module_validate_pair else((0,0),(0,1))):
        preflight=enabled if args.preflight_pair else int(args.with_preflight);module_validate=enabled if args.module_validate_pair else 0
        out = args.out / f"preflight{preflight}-module{module_validate}-cabin{cabin}"; out.mkdir()
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
        (out / "admission_controller_methods.inc").write_text("\n".join(controller)+"\n")
        (out / "admission_actual_effect_methods.inc").write_text("\n".join(effects)+"\n")
        command = ["g++", "-std=c++17", "-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
                   "-fno-pie", "-no-pie", "-Wall", "-Wextra", "-fpermissive", "-DRE4DC_GAME=1", f"-DRE4DC_CABIN_SOURCE={cabin}",
                   "-DRE4DC_EVD_ADMISSION_TXN=1", "-DRE4DC_EVD_START_CLEANUP=1", "-DRE4DC_EVD_START_ROLLBACK=1","-DRE4DC_EVD_DEBUG_READ_CLEANUP=0", "-DRE4DC_EVD_EXEC_FAILURE_CLEANUP=0",f"-DRE4DC_EVD_READ_ADMISSION_PREFLIGHT={preflight}",f"-DRE4DC_EVD_MODULE_VALIDATE_FIRST={module_validate}", "-I" + str(out), "-I"+str(HERE),str(HERE / "read_admission_characterization_host.cpp"), "-o", str(out / "test")]
        if args.actual_effects:command.append('-DRE4DC_READ_ACTUAL_EFFECT=1')
        assert shutil.disk_usage('/mnt/c').free>=floor,'C: source-test floor refused before compiler'
        h064.command(command, out / "compile.txt", 30)
        result = h064.command([out / "test"], out / "run.txt", 15); print(result, end="")
        variants.append(dict(evd_admission_txn=1,start_cleanup=1,start_rollback=1,read_admission_preflight=preflight,module_validate_first=module_validate,cabin_source=cabin,actual_effects=args.actual_effects, output=result))
    receipt = dict(scope="Actual EvtReadSub/Mram/SetRead/GetRead/table plus dataCtrl setData/getNewUnit and unit command/wait/clear/delete. File existence/size, unit availability, transport completion, module/effect/swap and native carrier policies are explicit boundaries. Bounded preflight source test only; no whole acquisition epoch/target/guest/hardware acceptance.",
                   selected_head=transaction.git("rev-parse", "HEAD").decode().strip(), fixture_revision=transaction.FIXTURE_REF,
                   source_sha256=pins, selected_methods=selected, variants=variants,
                   test_sha256={p.name: sha(p.read_bytes()) for p in (Path(__file__), HERE / "read_admission_characterization_host.cpp",HERE/'event_start_rollback_host.cpp',HERE/'exec_scenario_boundary.inc',HERE/'exec_transport_boundary.inc',HERE/'exec_cabin_boundary.inc',HERE/'admission_actual_effect_boundary.inc')},
                   host_abi_adapters=["Actual recovered GetRead writes a pointer through an int local; host adapter preserves real DatTbl lookup/slot with pointer-width storage.",
                                      "EvtReadExec's sole (void*)addr signed-int cast is normalized to (void*)(u32)addr, preserving native32 bits instead of host64 sign extension. No admission/failure/free decision changed."],
                   executed_evtreadexec_sha256=sha(next(method for method in event_methods if "int EventMgr::EvtReadExec(" in method).encode()))
    receipt['execution_roots']=['EvtReadMram/EvtReadSub','cDataCtrl::setData/getNewUnit','cDataUnit::setClear/setDelete']
    receipt['controller_binding_adapter']='Rename cDataCtrl method bindings to projected Controller with identical accessed fields. Actual bodies and allocation decisions execute; Host64 layout is not native ABI acceptance.'
    receipt['unexecuted_compile_closure']='Event/create/scenario/reverse bodies compile for inherited fixture closure but are not exercised.'
    output_bytes=sum(p.stat().st_size for p in args.out.rglob('*')if p.is_file())
    assert output_bytes<=20*1024**2,'Source-test output budget exceeded'
    receipt['resource_guard']={'start_C_free_bytes':start_free,'finish_C_free_bytes':shutil.disk_usage('/mnt/c').free,'floor_bytes':floor,'output_bytes_before_receipt':output_bytes,'output_limit_bytes':20*1024**2}
    receipt['transport_boundaries']=[
        'DVD FileExistCheck returns one synthetic size; no private asset is opened. Actual setData/getNewUnit choose and publish the descriptor. Unit-availability is an explicit accepting boundary.',
        'Actual command/check/wait/clear/delete execute; setLoadToMram synthesizes completion. No target allocation/backing or scheduling is qualified.',
        'Module lookup, effect Push/Pop and void MemorySwap are explicit controlled boundaries. Missing/undersized/refused cases characterize actual caller mutations, not actual effect release or byte exchange implementations.',
        'Actual setClear preserves active descriptor bit; actual setDelete clears it. Whether per-room retention is intended is not decided by this fixture.',
        'Prior module metadata controls are deliberately seeded source states. No gameplay failure occurrence or whole lifetime/epoch guarantee is claimed.']
    if args.actual_effects:
        receipt['execution_roots']+=['GetEmEffId/EspEmDataSwapPush/EspDataRelease']
        receipt['actual_effect_boundaries']='Actual owner mapping, effect owner-count decrement and final-release dispatch execute for module0x11. Texture/est/sst/path/model helper bodies are explicit exact-owner boundaries. Push definition binding alone is renamed for counting; no release decision is replaced.'
        receipt['scope']=receipt['scope'].replace('module/effect/swap','module/Pop/swap and effect-subtable')
        receipt['transport_boundaries'][2]='Actual owner mapping, Push and EspDataRelease count/final-dispatch execute. Module lookup, Pop, void MemorySwap and five effect-subtable release helpers are exact controlled boundaries.'
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
