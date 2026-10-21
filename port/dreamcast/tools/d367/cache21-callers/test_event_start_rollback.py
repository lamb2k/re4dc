#!/usr/bin/env python3
"""Test failed start rollback with actual SetEvt/create/table/release source."""
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
    source_files = ("src/game/event.cpp", "src/game/datactrl.cpp", "include/event.h", "include/datactrl.h", "include/cManager.h")
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
    event_methods += [body("src/game/event.cpp", name) for name in ("EventMgr::EvtReadExec", "EventMgr::EvtFree", "EventMgr::DelRead", "EventMgr::IsAliveEvt")]
    # Native32 int->pointer preserves the address bits. Host64 sign-extends a
    # negative int, so normalize only that cast, without changing any decision.
    cast = "EvtMgr.SetEvt((void*) addr, (u32*) &evt)"
    assert sum(method.count(cast) for method in event_methods) == 1
    event_methods = [method.replace(cast, "EvtMgr.SetEvt((void*) (u32) addr, (u32*) &evt)") for method in event_methods]
    unit_methods = [body("src/game/datactrl.cpp", "cDataUnit::" + name) for name in
                    ("setCommand", "getCommand", "getCondition", "isLoadOk", "waitLoadOk", "checkCommand", "setClear", "checkMallocRelease")]
    manager_methods = ["template <class T>\n" + body("include/cManager.h", "cManager<T>::create", "T* cManager<T>::create(int id)"),
                       "template <class T>\n" + body("include/cManager.h", "cManager<T>::countActiveWork")]
    variants = []
    for enabled in (0, 1):
        out = args.out / f"rollback{enabled}"; out.mkdir()
        adapted, changes = transaction.adapt_scaffold((fixture / "motion_event_admission_host.cpp").read_text())
        adapted = adapted.replace("void warn(int,int,const char*,...){}}logger", "void warn(int,int,const char*,...){}void mes(int,int,const char*,...){}}logger")
        assert "void mes(" in adapted
        old = "u32 NowExeEvtKey{},pUnit[32]{};void*emWindowFcv[3]{};};"
        new = ("union{u32 NowExeEvtKey;char NowExeEvtName[48];};u32 pUnit[32]{};void*emWindowFcv[3]{};"
               "Event*create(int);void destroyNow(Event*);int SetEvt(void*,u32*);int SetEvt(char*,Event**);int DelEvt(void*,int);"
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
        command = ["g++", "-std=c++17", "-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
                   "-fno-pie", "-no-pie", "-Wall", "-Wextra", "-fpermissive", "-DRE4DC_GAME=1", "-DRE4DC_CABIN_SOURCE=0",
                   "-DRE4DC_EVD_ADMISSION_TXN=1", "-DRE4DC_EVD_START_CLEANUP=1", f"-DRE4DC_EVD_START_ROLLBACK={enabled}", "-I" + str(out), str(HERE / "event_start_rollback_host.cpp"), "-o", str(out / "test")]
        h064.command(command, out / "compile.txt", 30)
        result = h064.command([out / "test"], out / "run.txt", 15); print(result, end="")
        variants.append(dict(evd_admission_txn=1,start_cleanup=1,start_rollback=enabled, output=result))
    receipt = dict(scope="Actual failed-create rollback, prior-owner/shared-bin preservation and outer caller characterization; UBSan, negative32 mmap. Init positive control, manager constructor/list, input transport, final-free are boundaries. Init-failure/reset/target/high-water are not accepted here.",
                   selected_head=transaction.git("rev-parse", "HEAD").decode().strip(), fixture_revision=transaction.FIXTURE_REF,
                   source_sha256=pins, selected_methods=selected, variants=variants,
                   test_sha256={p.name: sha(p.read_bytes()) for p in (Path(__file__), HERE / "event_start_rollback_host.cpp")},
                   host_abi_adapters=["Actual recovered GetRead writes a pointer through an int local; host adapter preserves real DatTbl lookup/slot with pointer-width storage.",
                                      "EvtReadExec's sole (void*)addr signed-int cast is normalized to (void*)(u32)addr, preserving native32 bits instead of host64 sign extension. No admission/failure/free decision changed."],
                   executed_evtreadexec_sha256=sha(next(method for method in event_methods if "int EventMgr::EvtReadExec(" in method).encode()))
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
