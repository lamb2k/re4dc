#!/usr/bin/env python3
"""Exercise em0 failed-start cleanup through actual read and scenario callers."""
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
    source_files = ("src/game/event.cpp", "src/game/datactrl.cpp", "include/event.h", "include/datactrl.h", "include/cManager.h","src/game/sce_com.cpp")
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
                    ("setCommand", "getCommand", "getCondition", "isLoadOk", "waitLoadOk", "isUseOk","waitUseOk","checkCommand", "setClear", "checkMallocRelease")]
    task_flag=re.search(r'^static inline void SceTaskFlagSet[^\n]+',source['src/game/sce_com.cpp'],re.M)[0]
    selected.append(dict(path='src/game/sce_com.cpp',name='SceTaskFlagSet',sha256=sha(task_flag.encode())))
    scenario=[body('src/game/sce_com.cpp','SceEventStart'),task_flag,body('src/game/sce_com.cpp','SceEventEnd')]
    scenario=[method.replace('void SceEventStart(int mode)','void actual_SceEventStart(int mode)').replace('void SceEventEnd(int mode)','void actual_SceEventEnd(int mode)')for method in scenario]
    manager_methods = ["template <class T>\n" + body("include/cManager.h", "cManager<T>::create", "T* cManager<T>::create(int id)"),
                       "template <class T>\n" + body("include/cManager.h", "cManager<T>::countActiveWork")]
    variants = []
    for enabled,cabin in ((0,0),(1,0),(0,1),(1,1)):
        out = args.out / f"exec{enabled}-cabin{cabin}"; out.mkdir()
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
        command = ["g++", "-std=c++17", "-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
                   "-fno-pie", "-no-pie", "-Wall", "-Wextra", "-fpermissive", "-DRE4DC_GAME=1", f"-DRE4DC_CABIN_SOURCE={cabin}",
                   "-DRE4DC_EVD_ADMISSION_TXN=1", "-DRE4DC_EVD_START_CLEANUP=1", "-DRE4DC_EVD_START_ROLLBACK=1","-DRE4DC_EVD_DEBUG_READ_CLEANUP=0", f"-DRE4DC_EVD_EXEC_FAILURE_CLEANUP={enabled}", "-I" + str(out), "-I"+str(HERE),str(HERE / "event_exec_failure_host.cpp"), "-o", str(out / "test")]
        h064.command(command, out / "compile.txt", 30)
        result = h064.command([out / "test"], out / "run.txt", 15); print(result, end="")
        variants.append(dict(evd_admission_txn=1,start_cleanup=1,start_rollback=1,exec_failure_cleanup=enabled,cabin_source=cabin, output=result))
    receipt = dict(scope="Actual em0 EvtReadSub/EvtReadExec/SetEvt/create/table/release and SceEventStart/End caller bodies. Transport completion, native carrier refusal decision, constructor/list, world/actor/camera/audio/scenario services and final free are boundaries. No module swap/read-failure/reset/target/high-water acceptance.",
                   selected_head=transaction.git("rev-parse", "HEAD").decode().strip(), fixture_revision=transaction.FIXTURE_REF,
                   source_sha256=pins, selected_methods=selected, variants=variants,
                   test_sha256={p.name: sha(p.read_bytes()) for p in (Path(__file__), HERE / "event_exec_failure_host.cpp",HERE/'event_start_rollback_host.cpp',HERE/'exec_scenario_boundary.inc',HERE/'exec_transport_boundary.inc',HERE/'exec_cabin_boundary.inc')},
                   host_abi_adapters=["Actual recovered GetRead writes a pointer through an int local; host adapter preserves real DatTbl lookup/slot with pointer-width storage.",
                                      "EvtReadExec's sole (void*)addr signed-int cast is normalized to (void*)(u32)addr, preserving native32 bits instead of host64 sign extension. No admission/failure/free decision changed."],
                   executed_evtreadexec_sha256=sha(next(method for method in event_methods if "int EventMgr::EvtReadExec(" in method).encode()))
    receipt['scenario_binding_adapters']={
        'purpose':'Rename only actual bracket definition bindings to count caller entries; source bracket bodies/decisions execute.',
        'executed_sha256':sha('\n'.join(scenario).encode())}
    receipt['transport_boundaries']=[
        'Actual EvtReadSub/EvtReadMram/setCommand/checkCommand/waitUseOk/waitLoadOk/setClear execute. setLoadToMram is explicit synthetic transport completion, not target allocator/install/ARAM carrier proof.',
        'Prior ARAM input becomes synthetic MRAM through that completion boundary; ReadTbl bytes/Count/readEm and no-free obligations execute in actual caller bodies. This does not certify actual target ARAM backing conversion.',
        'Native carrier reserved/clear admission is an explicit refusal boundary. Actual EvtFree and actual setClear propagate refusal and preserve the read; existing native carrier-policy predicates are not requalified here.',
        'Event::init is a positive control boundary; prior actual init failures are separately qualified by event-start-rollback-init.json.',
        'em!=0 negative control exchanges synthetic buffers at a transport boundary and verifies unchanged source false-success/keep behavior. No module reversal repair is claimed.',
        'Injected read reference transfer at create and unrelated flag updates during transport are adversarial source-state controls, not gameplay occurrence evidence.']
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
