"""EFM class-index parity against the source slot loop and production manager/bridge.

The host adapts only cUnit's sized-delete argument to 64-bit size_t and uses the
bridge workAt because a 64-bit Pool header cannot have the SH-4's +64 slot table.
The EFM excerpt, manager methods and demand-backing publication are production code.
"""
from pathlib import Path
import argparse
import hashlib
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
STUB = ROOT / "port/dreamcast/tests/efm_identity/stub"
FIXTURE = ROOT / "port/dreamcast/tests/efm_identity/fixture.cpp"
BRIDGE = "port/dreamcast/game/parts_bridge.cpp"
EFM = "src/game/esp_efm.cpp"
MANAGER = "include/cManager.h"
BASELINE = "8f5a269e5e06dd4ec02857cf5beb0e71f3c4561b"


def run(cmd, cwd=ROOT, **kw):
    p = subprocess.run([str(x) for x in cmd], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    if p.returncode:
        raise AssertionError(f"command failed ({p.returncode}): {' '.join(map(str, cmd))}\n{p.stdout}")
    return p.stdout


def source(path, baseline=False):
    return run(["git", "show", f"{BASELINE}:{path}"]) if baseline else (ROOT / path).read_text()


def manager_copy(text, out):
    old = "void operator delete(void*, unsigned int) {}"
    assert text.count(old) == 1
    out.write_text(text.replace(old, "void operator delete(void*, unsigned long) {}"))


def efm_slice(text, instrument=False):
    start = text.index("// Destroys every Efm object whose EfmCore matches")
    end = text.index("// Destroys every Efm object that is neither permanent", start)
    result = text[start:end]
    if instrument:
        anchor = "void EfmDeleteSub(cObj* obj)\n{"
        assert result.count(anchor) == 1
        result = result.replace(anchor, anchor + "\n    fixture_visit(obj);", 1)
    return result


def build_fixture(tmp, sanitize, scan):
    manager_copy(source(MANAGER), tmp / "cManager.h")
    (tmp / "efm_source_slice.inc").write_text(efm_slice(source(EFM), True))
    flags = ["-std=gnu++17", "-fpermissive", f"-DRE4DC_FX_SCAN={scan}",
             "-I" + str(tmp), "-I" + str(STUB), "-idirafter", str(ROOT / "include")]
    if sanitize:
        flags += ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined",
                  "-fno-sanitize=vptr"]
    else:
        flags += ["-O2", "-g0"]
    exe = tmp / f"efm-{scan}-{'san' if sanitize else 'normal'}"
    run(["g++", *flags, FIXTURE, ROOT / BRIDGE, "-o", exe])
    env = dict(os.environ)
    # LeakSanitizer cannot inspect /proc task entries in the managed executor.
    env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    return run([exe], env=env).strip()


OFF_PREFIX = '''#include "host.h"
extern "C" { u32 re4dc_alive_gen[4]; u32 re4dc_frozen_pools; }
u16 g_Core_flg; u8 g_Core_kind; cModel* g_Core_pEm;
void EfmDeleteSub(cObj*); void EfmDelete(int,int,int);
#undef RE4DC_WORKAT_INLINE
#define RE4DC_WORKAT_INLINE 1
#include "efm_source_slice.inc"
'''
OFF_MANAGER = '''#include "host.h"
cObj* a(cObjMgr* m) { return m->create(4); }
cObj* b(cObjMgr* m) { return m->createBack(5); }
cObj* c(cObjMgr* m) { return m->create(9,1); }
int d(cObjMgr* m) { return m->roomInit() + m->arrayPush(4) + m->arrayPop(); }
'''


def make_flags(tmp):
    kos = tmp / "kos-stub"
    kos.mkdir()
    (kos / "Makefile.rules").write_text("")
    game = ROOT / "port/dreamcast/game"
    targets = ["obj/src/game/esp_efm.o", "obj/src/game/obj.o",
               "obj/mod/st1_1/src/st1/r101.o", "obj/parts_bridge.o",
               "obj/platform/native_static.o"]
    args = ["make", "-f", "Makefile", "-n",
            f"KOS_BASE={kos}", "GAME_FX_SCAN=1", "GAME_ATCHK=1",
            "GAME_ATCHK_LIST=1", "GAME_WORKAT_INLINE=1", "GAME_ESP_OWNER=1",
            "OBJECT_DEMAND=1", "ENEMY_DEMAND=1", *targets]
    def commands(value):
        cmd = args + ([f"GAME_EFM_CLASS_IDENTITY={value}"] if value is not None else [])
        out = run(cmd, cwd=game)
        return [line for line in out.splitlines() if line.startswith("kos-c++")]
    absent, zero, enabled = commands(None), commands(0), commands(1)
    assert absent == zero and len(enabled) == len(targets)
    assert all("-DRE4DC_EFM_CLASS_IDENTITY=" not in x for x in absent)
    assert all(x.count("-DRE4DC_EFM_CLASS_IDENTITY=1") == 1 for x in enabled)
    empty = subprocess.run([str(x) for x in args + ["GAME_EFM_CLASS_IDENTITY="]],
                           cwd=game, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    assert empty.returncode != 0 and "must be exactly 0 or 1" in empty.stdout
    return len(enabled)


def off_identity(tmp):
    outputs = {}
    for baseline in (True, False):
        branch = tmp / ("baseline" if baseline else "current")
        branch.mkdir()
        manager_copy(source(MANAGER, baseline), branch / "cManager.h")
        (branch / "efm_source_slice.inc").write_text(efm_slice(source(EFM, baseline)))
        (branch / "off_efm.cpp").write_text(OFF_PREFIX)
        (branch / "off_manager.cpp").write_text(OFF_MANAGER)
        (branch / "parts_bridge.cpp").write_text(source(BRIDGE, baseline))
        flags = ["-std=gnu++17", "-fpermissive", "-O2", "-g0",
                 "-DRE4DC_EFM_CLASS_IDENTITY=0", "-DRE4DC_FX_SCAN=1",
                 "-I" + str(branch), "-I" + str(STUB), "-idirafter", str(ROOT / "include")]
        checks = []
        for stem in ("off_efm", "off_manager", "parts_bridge"):
            cpp = branch / (stem + ".cpp")
            pp = run(["g++", *flags, "-E", "-P", cpp])
            pp_path = branch / (stem + ".ii")
            pp_path.write_text(pp)
            obj = branch / (stem + ".o")
            run(["g++", *flags, "-c", pp_path, "-o", obj])
            # Compare every -E -P byte, including whitespace left by a disabled
            # invocation; both branches use the same host checkout root.
            checks.append((hashlib.sha256(pp.encode()).hexdigest(),
                           hashlib.sha256(obj.read_bytes()).hexdigest()))
        outputs[baseline] = checks
    assert outputs[True] == outputs[False], f"OFF identity mismatch: {outputs}"
    return [x[1][:16] for x in outputs[True]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--normal-only", action="store_true")
    ap.add_argument("--sanitizer-only", action="store_true")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="efm-class-") as td:
        tmp = Path(td)
        if not args.sanitizer_only:
            for scan in (1, 2): print(build_fixture(tmp, False, scan))
        if not args.normal_only:
            for scan in (1, 2): print(build_fixture(tmp, True, scan))
        print("EFM OFF preprocessor/object SHA16:", *off_identity(tmp))
        print("EFM Make absent/zero/ON flag arms:", make_flags(tmp), "consumer commands")


if __name__ == "__main__":
    main()
