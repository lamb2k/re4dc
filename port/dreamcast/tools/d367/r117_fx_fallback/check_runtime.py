#!/usr/bin/env python3
"""Host semantic checks of extracted production r117 discovery/draw/filter/admission.

Controlled boundaries: model/pool fields, texture residency, matrix arithmetic,
packet encoding and transport. Actual functions qualify all source groups,
prepare/consume tickets, match copies, filter Essential, and admit batch/scalar
sprites. No game data, full engine, Flycast, or Dreamcast run is represented.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
spec = importlib.util.spec_from_file_location("r117_source_extract", HERE.parent / "esp_setup_lean/check_runtime.py")
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=False)
    esp_path = ROOT / "src/game/esp_sub.cpp"
    ui_path = ROOT / "port/dreamcast/game/platform/native_ui.cpp"
    include = ROOT / "port/dreamcast/game/platform/include"
    esp, ui = esp_path.read_text(), ui_path.read_text()
    function, conditional = extract.function, extract.conditional
    start = esp.index("struct Ps2fxPuzzleGroup {")
    render = function(esp, 'extern "C" void re4dc_ps2_fx_stage1_render(')
    puzzle = esp[start:esp.index(render) + len(render)]
    # Check actual engine hook order around the controlled transform boundary.
    begin = esp.index("void EspCommonTrans(cEsp* esp)")
    common = esp[begin:esp.index("\nvoid ", begin + 1)]
    assert common.index("Ps2fxClass(esp)") < common.index("esp->ChannelSet()") < common.index("FxEssentialSetupCut(esp,")
    emit = function(esp, "static void EspSpriteEmit(")
    assert emit.index("FxLevelSprite(esp,") < emit.index("re4dc_effect_sprite(")
    assert "FxTrimSprite(esp," in function(esp, "static int FxLevelSprite(")
    replacements = dict(
        PS2FX_ENUM=re.search(r"enum \{ PS2FX_CLAMP[^\n]+", esp).group(),
        KNOB_GUARD=conditional(esp, "#if defined(RE4DC_R117_FX_QUALIFIED_FALLBACK)"),
        TRIM_TABLE=esp[esp.index("struct FxTrim {"):esp.index("#if defined(RE4DC_FX_TRIM_LOG)", esp.index("struct FxTrim {"))],
        ESSENTIAL_TABLE=esp[esp.index("enum { ESS_KEEP"):esp.index('extern "C" {', esp.index("enum { ESS_KEEP"))],
        EARLY_STATE=conditional(esp, "#if defined(RE4DC_ESP_SETUP_LEAN) && RE4DC_ESP_SETUP_LEAN &&"),
        ESSENTIAL_CUT=function(esp, "static int FxEssentialCut("),
        EARLY_CUT=conditional(esp, "#if defined(RE4DC_ESP_ESSENTIAL_EARLY)\n// Only stateless"),
        TRIM_SPRITE=function(esp, "static int FxTrimSprite("),
        BATCH=(include / "native_effect_stage1_batch.inc").read_text(),
        SPRITE=function(ui, 'extern "C" int re4dc_effect_sprite('),
        PUZZLE=puzzle)
    source = (HERE / "runtime.cpp.in").read_text()
    for key, value in replacements.items():source = source.replace("@" + key + "@", value)
    assert not re.search(r"@[A-Z_]+@", source)
    inputs = [esp_path, ui_path, ROOT / "src/game/ps2_fx_population.h",
        include / "native_effect_stage1_batch.inc", include / "fx_r200_entry_cap.h",
        HERE / "runtime.cpp.in", HERE / "check_runtime.py"]
    hashes = {str(path.relative_to(ROOT)):sha(path) for path in inputs}
    results = []
    for knob in (0, 1):
        for early in (0, 1):
            for r200 in (0, 1):
                name = f"fallback{knob}-early{early}-r200{r200}"
                cpp, exe = out / (name + ".cpp"), out / (name + ".bin")
                cpp.write_text(source)
                command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-ffp-contract=off",
                    "-fno-pie", "-no-pie", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-DRE4DC_R117_FX_QUALIFIED_FALLBACK=" + str(knob),
                    "-DRE4DC_ESP_SETUP_LEAN=" + str(early), "-DRE4DC_FX_R200_ENTRY_CAP=" + str(r200),
                    "-I" + str(ROOT / "src/game"), "-I" + str(include), str(cpp), "-o", str(exe)]
                build = subprocess.run(command, capture_output=True, text=True)
                (out / (name + "-build.log")).write_text(build.stdout + build.stderr)
                assert build.returncode == 0, name + ": " + build.stderr
                env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1")
                run = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
                (out / (name + "-run.log")).write_text(run.stdout + run.stderr)
                assert run.returncode == 0 and not run.stderr, name + ": " + run.stdout + run.stderr
                results.append(dict(name=name, stats=json.loads(run.stdout), command=command,
                                    source_sha256=sha(cpp), compile_diagnostics=build.stderr))
                print("PASS", name, flush=True)
    assert hashes == {str(path.relative_to(ROOT)):sha(path) for path in inputs}
    report = dict(status="PASS", scope=__doc__, source_sha256=hashes,
        compiler=subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
        source_hook_order_checked=True, results=results)
    (out / "runtime-receipt.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
