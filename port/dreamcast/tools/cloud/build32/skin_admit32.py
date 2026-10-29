#!/usr/bin/env python3
"""Build32 transactional skin admission: production producer/registry/consumer host fixture."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
TRANS = ROOT / "src/game/trans.cpp"
PLATFORM = ROOT / "port/dreamcast/game/platform"
ACTOR = PLATFORM / "native_actor_fast.cpp"
INC = PLATFORM / "include"
BASE = "39ed524a3b0a4727148aaa5a45eaaea4d211cede"


def base_text(path: Path) -> str:
    return subprocess.check_output(["git", "show", f"{BASE}:{path.relative_to(ROOT)}"], cwd=ROOT).decode()


def function(source: str, prefix: str) -> str:
    start = source.index(prefix)
    while True:
        brace = source.index("{", start)
        semicolon = source.find(";", start, brace)
        if semicolon == -1:
            break
        start = source.index(prefix, semicolon + 1)
    closing = re.search(r"^}", source[brace + 1:], re.MULTILINE)
    assert closing, prefix
    end = brace + 1 + closing.end()
    return source[start:end] + "\n"


def region(source: str, start: str, end: str) -> str:
    return source[source.index(start):source.index(end, source.index(start))]


def source_file(path: Path, baseline: bool) -> str:
    return base_text(path) if baseline else path.read_text()


def fixture(baseline: bool) -> str:
    t = source_file(TRANS, baseline)
    a = source_file(ACTOR, baseline)
    template = (HERE / "skin_admit32_fixture.cpp.in").read_text()
    registry = region(a, "struct SkinEntry {", "// ---------------------------------------------------------- info context --")
    for name in ("native_actor_owner_pool.inc", "native_actor_owner_registry.inc",
                 "native_actor_skin_reserve.inc", "native_actor_skin_admit32.inc"):
        marker = f'#include "include/{name}"'
        if marker in registry:
            registry = registry.replace(marker, source_file(INC / name, baseline))
    owner = function(source_file(INC / "native_actor_owner_workspace.inc", baseline),
                     'extern "C" void re4dc_actor_owner_retire()')
    funcs = [function(a, 'extern "C" int re4dc_actor_skin_register('),
             function(a, 'extern "C" const float* re4dc_actor_skin_palette('),
             function(t, "void SetPrimBuffPtr()"), function(t, "void* GetPrimBuff(int size)"),
             function(t, 'extern "C" void* re4dc_prim_tail(unsigned bytes, unsigned reserve)'),
             function(t, "int re4dc_skin_defer(cModelInfo* info, ModelData* d)"),
             function(t, "int re4dc_skin_defer_lazy(cModelInfo* info, ModelData* d)"),
             function(t, "static int skinDeferPending(cModel* m, cModelInfo* info, ModelData* d, int* mtxBuilt)"),
             function(t, 'extern "C" void re4dc_skin_palette_resolve(const float* palette)')]
    lazy_head = region(t, "struct SkinLazyHead {", "#if RE4DC_SKIN_PALETTE_LAZY == 2")
    code = template.replace("// @REGISTRY@", registry).replace("// @OWNER_RETIRE@", owner)
    code = code.replace("// @FUNCTIONS@", "\n".join(funcs))
    code = code.replace("// @LAZY_HEAD@", lazy_head)
    assert not any(x in code for x in ("// @REGISTRY@", "// @OWNER_RETIRE@", "// @FUNCTIONS@", "// @LAZY_HEAD@"))
    return code


def run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    p = subprocess.run(command, capture_output=True, text=True, env=env)
    if p.returncode:
        raise RuntimeError(f"{' '.join(command)}\n{p.stdout[-5000:]}\n{p.stderr[-12000:]}")
    return p.stdout


def make_control() -> None:
    fragment = ROOT / "port/dreamcast/game/skin_admit32.mk"
    lines = f"OBJDIR := fixture\ninclude {fragment}\nprint:;@echo $(GAME_CPPFLAGS):$(PLATFORM_CPPFLAGS)\n"

    def check(*flags: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["make", "--no-print-directory", "-f", "-", "print", *flags],
                              input=lines, capture_output=True, text=True,
                              cwd=ROOT / "port/dreamcast/game")

    absent, zero = check(), check("SKIN_ADMISSION32=0")
    assert absent.returncode == zero.returncode == 0 and absent.stdout == zero.stdout == ":\n"
    profile = ["ACTOR_TRANSACTION=1", "NATIVE_ACTOR_FAST=1", "NATIVE_ACTOR_SKIN_LAZY=1",
               "SKIN_PALETTE_LAZY=1", "SKIN_ADMISSION32=1"]
    enabled = check(*profile)
    assert enabled.returncode == 0, enabled.stderr
    # Target-specific variables are proven by recipe expansion separately.
    rules = f"OBJDIR := fixture\ninclude {fragment}\nfixture/src/game/trans.o:;@echo $(GAME_CPPFLAGS)\nfixture/platform/native_actor_fast.o:;@echo $(PLATFORM_CPPFLAGS)\n"
    for target in ("fixture/src/game/trans.o", "fixture/platform/native_actor_fast.o"):
        p = subprocess.run(["make", "--no-print-directory", "-f", "-", target, *profile],
                           input=rules, capture_output=True, text=True,
                           cwd=ROOT / "port/dreamcast/game")
        assert p.returncode == 0 and p.stdout.count("-DRE4DC_SKIN_ADMISSION32=1") == 1, p.stderr
    for bad in ("2", "", "0 1", "%", "0%", "1%"):
        assert check(*profile[:-1], "SKIN_ADMISSION32=" + bad).returncode != 0
    for dep in ("ACTOR_TRANSACTION", "NATIVE_ACTOR_FAST", "NATIVE_ACTOR_SKIN_LAZY", "SKIN_PALETTE_LAZY"):
        assert check(*(x for x in profile if not x.startswith(dep + "=")), dep + "=0").returncode != 0
    # Exercise the primary Makefile too: the fragment must be included once,
    # and its target-local definition must not escape to native_ui.o.
    # No private asset target is built or supplied; its directory is unused.
    with tempfile.TemporaryDirectory(prefix="skin-admit32-make-") as tmp:
        (Path(tmp) / "Makefile.rules").write_text("")
        deps = ["ACTOR_TRANSACTION=1", "NATIVE_ACTOR=1", "NATIVE_ACTOR_FAST=1",
                "NATIVE_ACTOR_SKIN=1", "NATIVE_ACTOR_SKIN_LAZY=1", "SKIN_PALETTE_LAZY=1",
                "COARSE_SOURCE_ACTORS=1", "COARSE_LEON=1", "COARSE_GANADO=1",
                "COARSE_GANADO_CAST=1", "COARSE_ONE_SUBMIT=1", "COARSE_SKIN_FTRV=1",
                "COARSE=1", "PACE_CATCHUP=2", "PACE_TRANS_SKIP=4063", "GAME_ATCHK=1",
                "GAME_ATCHK_LIST=1", "COARSE_ACTOR_ASSET_DIR=" + tmp,
                "D349_RENDERER_STACK=1", "PVR_STREAM=1"]
        targets = ["obj/src/game/trans.o", "obj/platform/native_actor_fast.o", "obj/platform/native_ui.o"]
        arms = []
        for extra in ([], ["SKIN_ADMISSION32=0"], ["SKIN_ADMISSION32=1"]):
            result = subprocess.run(["make", "-f", "Makefile", "-n", "KOS_BASE=" + tmp,
                                     *deps, *targets, *extra], cwd=ROOT / "port/dreamcast/game",
                                    capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            arms.append([line for line in result.stdout.splitlines() if line.startswith("kos-c++")])
        assert arms[0] == arms[1] and len(arms[2]) == len(targets)
        for i, line in enumerate(arms[2]):
            assert line.count("-DRE4DC_SKIN_ADMISSION32=1") == int(i < 2), line


def main() -> None:
    make_control()
    digest = hashlib.sha256((TRANS.read_bytes() + ACTOR.read_bytes() +
                             (INC / "native_actor_skin_admit32.inc").read_bytes())).hexdigest()[:16]
    with tempfile.TemporaryDirectory(prefix="re4dc-skin-admit32-") as directory:
        out = Path(directory)
        baseline = out / "baseline.cpp"
        current = out / "current.cpp"
        baseline.write_text(fixture(True))
        current.write_text(fixture(False))
        flags = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wno-unused-parameter",
                 "-DRE4DC_GAME=1", "-DRE4DC_PRIMITIVE_BUFFERS=1", "-DRE4DC_ACTOR_TRANSACTION=1",
                 "-DRE4DC_ACTOR_SKIN_RESERVE=1", "-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1",
                 "-DRE4DC_SKIN_PALETTE_LAZY=1", "-DRE4DC_NATIVE_ACTOR_SKIN=1"]
        for pool in (0, 1):
            common = [*flags, f"-DRE4DC_ACTOR_SKIN_OWNER_POOL={pool}"]
            pre = []
            objs = []
            for path, mode in ((baseline, "base"), (current, "absent"), (current, "zero")):
                opts = common + (["-DRE4DC_SKIN_ADMISSION32=0"] if mode == "zero" else [])
                pre.append(run(["g++", *opts, "-E", "-P", str(path)]))
                obj = out / f"{pool}-{mode}.o"
                built = subprocess.run(["g++", "-std=c++20", "-O2", "-x", "c++", "-c", "-", "-o", str(obj)],
                                       input=pre[-1], capture_output=True, text=True)
                if built.returncode:
                    raise RuntimeError(built.stderr[-12000:])
                objs.append(obj.read_bytes())
            assert pre[0] == pre[1] == pre[2], f"OFF preprocessing differs: pool={pool}"
            assert objs[0] == objs[1] == objs[2], f"OFF object differs: pool={pool}"
            for sanitized in (False, True):
                exe = out / f"on-{pool}-{int(sanitized)}"
                opts = common + ["-DRE4DC_SKIN_ADMISSION32=1"]
                if sanitized:
                    opts += ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]
                run(["g++", *opts, str(current), "-o", str(exe)])
                result = run([str(exe)], env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
                print(f"PASS pool={pool} sanitizer={int(sanitized)} {result.strip()}")
            print(f"PASS pool={pool} baseline/absent/zero preprocessor and object identical bytes={len(objs[0])}")
    print(f"PASS skin_admit32 source={digest} Make control")


if __name__ == "__main__":
    main()
