#!/usr/bin/env python3
"""Run exact H064 characterization and an extended actual-source transaction test."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
FIXTURE_REF = "d396bd9e70f7953866e2055b392dda39e0087644"
FIXTURE_DIR = "port/dreamcast/tools/d367/boss21"
FIXTURE_FILES = ("test_motion_lifetime.py", "motion_consumer_audit.py", "motion_event_admission_host.cpp")
METHODS = ("EventMgr::SetEvd", "EventMgr::SetBin", "DatTbl::SetDat", "DatTbl::ChkDat",
           "DatTbl::GetDat", "DatTbl::GetWkNo", "DatTbl::DelDat", "DatTbl::DelAll",
           "EventMgr::GetEvd", "EventMgr::DelBin", "EventMgr::DelEvd", "EventMgr::ToolCoreEvdDel",
           "DatTbl::init", "DatTbl::end", "EventMgr::myRoomInit", "EventMgr::ClearEmWindowFcv")


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def adapt_scaffold(original):
    changes = []

    def replace_once(old, new, purpose):
        nonlocal original
        assert original.count(old) == 1, purpose
        original = original.replace(old, new)
        changes.append(purpose)

    replace_once("void memclr_asm(void*p,unsigned n){std::memset(p,0,n);}",
                 "void memclr_asm(void*p,unsigned n){host_before_clear(p,n);std::memset(p,0,n);}",
                 "Observe parent invisibility at the host memset boundary; memory operation unchanged")
    replace_once("struct Logger{void err(int,int,const char*,...){++errors;}}logger,*pLog=&logger;",
                 "struct Logger{void err(int,int,const char*,...){++errors;}void warn(int,int,const char*,...){}}logger,*pLog=&logger;",
                 "Declare the logger warning boundary used by actual GetEvd")
    replace_once("int SetDat(const char*,void*,u8,void*,u8,int*);int ChkDat(const char*);};",
                 "int SetDat(const char*,void*,u8,void*,u8,int*);int ChkDat(const char*);"
                 "int GetDat(void**,u8*,const char*,int*);int GetWkNo(int*,const char*);"
                 "int DelDat(const char*);int DelAll(int);int init(int);int end();};",
                 "Extend only DatTbl host method declarations")
    replace_once("int SetEvd(char*,void*,void*,int);int SetBin(char*,void*,void*,int);};",
                 "int SetEvd(char*,void*,void*,int);int SetBin(char*,void*,void*,int);"
                 "int GetEvd(void**,char*,int);int DelBin(char*);int DelEvd(char*);void ToolCoreEvdDel();"
                 "int myRoomInit();void ClearEmWindowFcv();DatTbl FuncTbl{},ReadTbl{};"
                 "u32 NowExeEvtKey{},pUnit[32]{};void*emWindowFcv[3]{};};",
                 "Extend only EventMgr host declarations/fields, not target ABI")
    return original, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline-ref", default="54cef5d1560c41d074beee05ffa1ecd38f2ee642")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    fixture = args.out / "h064-fixture" / FIXTURE_DIR
    fixture.mkdir(parents=True)
    fixture_pins = {}
    for name in FIXTURE_FILES:
        data = git("show", f"{FIXTURE_REF}:{FIXTURE_DIR}/{name}")
        (fixture / name).write_bytes(data)
        fixture_pins[name] = sha(data)
    sys.path.insert(0, str(fixture))
    spec = importlib.util.spec_from_file_location("h064_fixture", fixture / FIXTURE_FILES[0])
    h064 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h064)
    h064.REPO = REPO
    baseline = git("rev-parse", args.baseline_ref).decode().strip()
    source, pins, reset_order = h064.export_source(args.out, baseline)
    original_event = (source / "src/game/event.cpp").read_bytes()
    candidate = (REPO / "src/game/event.cpp").read_bytes()
    original_command = h064.command
    variants = []
    scaffold_changes = []
    for variant, enabled, data in (("baseline", 0, original_event), ("disabled", 0, candidate), ("enabled", 1, candidate)):
        (source / "src/game/event.cpp").write_bytes(data)
        output = args.out / variant

        def command(argv, log, timeout=45):
            nonlocal scaffold_changes
            argv = list(map(str, argv))
            original_main = str(fixture / "motion_event_admission_host.cpp")
            if original_main in argv:
                argv[1:1] = ["-DRE4DC_GAME=1", f"-DRE4DC_EVD_ADMISSION_TXN={enabled}"]
                if enabled:
                    s = data.decode()
                    (output / "event_admission_methods.inc").write_text("\n".join(h064.fn(s, name)[0] for name in METHODS) + "\n")
                    adapted, scaffold_changes = adapt_scaffold((fixture / "motion_event_admission_host.cpp").read_text())
                    (output / "h064_event_admission_adapted.cpp").write_text(adapted)
                    argv[argv.index(original_main)] = str(HERE / "event_admission_txn_host.cpp")
            return original_command(argv, log, timeout)

        h064.command = command
        result = h064.build_event(output, source)
        result.update(variant=variant, evd_admission_txn=enabled, event_cpp_sha256=sha(data))
        variants.append(result)
    # Pin actual release/reader bodies separately. They are inspected, not run by
    # this table fixture; no generation/reset ownership proof is inferred.
    reviewed = []
    readers = {
        "src/game/event.cpp": ["EventMgr::EvtFree", "EventMgr::GetEvd", "EventMgr::DelEvd", "EventMgr::myRoomInit", "EventMgr::ToolCoreEvdDel"],
        "src/game/game.cpp": ["gameRoomMemInit"],
        "src/game/main.cpp": ["systemSoftReset", "systemResetCommon"],
        "src/game/scheduler.cpp": ["GetStackSize"],
        "src/game/db_log.cpp": ["cLog::err", "cLog::verr", "cLog::add"],
        "port/dreamcast/game/platform/native_event_file.cpp": ["carrier_current", "carrier_mram_current", "re4dc_cabin_carrier_event", "re4dc_cabin_carrier_reverse_token", "re4dc_cabin_carrier_event_deleted"],
    }
    for path, names in readers.items():
        data = git("show", f"{baseline}:{path}")
        target = args.out / "reader-contracts" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        for name in names:
            text = data.decode()
            if name in ("carrier_current", "carrier_mram_current"):
                # H064's lexical selector also sees a later multiline condition
                # as this name. Bound the reviewed bool declaration before using
                # the unchanged selector; no function body is rewritten.
                begin = text.index("bool " + name + "(")
                end = text.index("\n}", begin) + 2
                body, line = h064.fn(text[begin:end], name)
                line += text.count("\n", 0, begin)
            else:
                body, line = h064.fn(text, name)
            reviewed.append(dict(path=path, name=name, line=line, sha256=sha(body.encode())))
    receipt = dict(
        scope="Actual EventMgr/DatTbl source, UBSan only (negative32 mmap); host class/heap/transport boundaries. No guest, linked program, gameplay performance, whole reset or general generation proof.",
        baseline_revision=baseline, candidate_event_sha256=sha(candidate),
        fixture_revision=FIXTURE_REF, fixture_sha256=fixture_pins,
        baseline_source_sha256=pins, scaffold_changes=scaffold_changes,
        selected_actual_methods=[dict(name=name, sha256=sha(h064.fn(candidate.decode(), name)[0].encode())) for name in METHODS],
        reviewed_reader_release_contracts=reviewed, reset_order_characterization=reset_order,
        variants=variants,
        tests_sha256={p.name: sha(p.read_bytes()) for p in (Path(__file__), HERE / "event_admission_txn_host.cpp")},
    )
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
