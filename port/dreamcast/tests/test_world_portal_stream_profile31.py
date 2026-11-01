#!/usr/bin/env python3
"""Full release-chain Make and trans.cpp source guards for Build31 stream ON."""
from pathlib import Path
import importlib.util
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
GAME = ROOT / "port/dreamcast/game"
TRANS = ROOT / "src/game/trans.cpp"
NATIVE = GAME / "platform/native_static.cpp"
BUILDER = ROOT / "port/dreamcast/tools/cloud/build31/stream_portal_profile.py"
spec = importlib.util.spec_from_file_location("stream_portal_profile31", BUILDER)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def make(tmp, assignments, target, *, dry=True):
    obj = tmp / "obj"
    obj.mkdir(exist_ok=True)
    modules = obj / "modules.mk"
    modules.touch()
    kos = tmp / "kos-stub"
    kos.mkdir(exist_ok=True)
    (kos / "Makefile.rules").touch()
    command = ["make", "--no-print-directory", "-f", "Makefile",
               "-n" if dry else "-s", f"--assume-old={modules}",
               f"KOS_BASE={kos}", f"KOS_LDFLAGS=-T{kos}/utils/ldscripts/shlelf.xc",
               *assignments, str(obj / target)]
    return subprocess.run(command, cwd=GAME, text=True, capture_output=True)


def compile_args(output, source):
    lines = [shlex.split(line) for line in output.splitlines()
             if line.startswith("kos-c++ ")]
    matches = [line for line in lines if "-c" in line and
               line[line.index("-c") + 1] == source]
    assert len(matches) == 1, (source, matches)
    return matches[0]


def accepted(tmp, assignments, target):
    result = make(tmp, assignments, target)
    assert result.returncode == 0, (target, result.stdout[-2500:], result.stderr[-2500:])
    return result.stdout


def actual_trans_guard(tmp, trans_args, *, expected):
    source = TRANS.read_text()
    marker = "#if RE4DC_COARSE\n#if RE4DC_PACE_CATCHUP < 2 || !(RE4DC_PACE_TRANS_SKIP & 2048)"
    guard = source[source.index(marker):source.index("// port/dreamcast/game/coarse.cpp", source.index(marker))]
    # The final #endif closes the enclosing COARSE conditional. The two
    # definitions come from the actual trans.o Make command; pace.h comes from
    # the actual Make header recipe, so the target-conditional guard sees the
    # same three values as the target TU.
    guard += "#endif\nint admitted;\n"
    definitions = [word for word in trans_args if word.startswith("-DRE4DC_")]
    for required in ("-DRE4DC_COARSE=1", "-DRE4DC_PACE_TRANS_SKIP=4063"):
        if expected:
            assert required in definitions, required
    assert any(word.startswith("-DRE4DC_COARSE=") for word in definitions)
    assert any(word.startswith("-DRE4DC_PACE_TRANS_SKIP=") for word in definitions)
    pace = tmp / "obj/pace.h"
    assert "#define RE4DC_PACE_CATCHUP 2\n" in pace.read_text()
    checked = subprocess.run(["g++", "-E", "-P", "-x", "c++", "-include", str(pace),
                              *definitions, "-"], input=guard, text=True, capture_output=True)
    assert (checked.returncode == 0) == expected, (checked.stdout, checked.stderr)
    if not expected:
        assert "COARSE needs PACE_CATCHUP=2 and the qualified PACE_TRANS_SKIP mask (bit 2048)" in checked.stderr


def actual_native_guard(native_args):
    source = NATIVE.read_text()
    start = source.index("#ifndef RE4DC_WORLD_PORTAL_COMPLETION\n")
    end = source.index("#ifndef RE4DC_SCENERY_SUBMIT_BATCH\n", start)
    guard = source[start:end] + "int admitted;\n"
    definitions = [word for word in native_args if word.startswith("-DRE4DC_")]

    def check(values, expected, diagnostic=None):
        result = subprocess.run(["g++", "-E", "-P", "-x", "c++", *values, "-"],
                                input=guard, text=True, capture_output=True)
        assert (result.returncode == 0) == expected, result.stderr
        if diagnostic is not None:
            assert diagnostic in result.stderr, result.stderr

    # Qualify the literal production guards with the complete definitions from
    # the primary Make command, not a separately maintained synthetic profile.
    check(definitions, True)
    for key, value, diagnostic in (
            ("WORLD_PORTAL_STREAM31", "0", "SCENERY_STREAM with PS2_PVS needs WORLD_PORTAL_STREAM31"),
            ("SCENERY_CLIP_GATHER", "1", "clip remains unqualified"),
            ("SCENERY_CLIP_INDEXED26", "1", "clip remains unqualified")):
        prefix = "-DRE4DC_" + key + "="
        changed = [word for word in definitions if not word.startswith(prefix)]
        changed.append(prefix + value)
        check(changed, False, diagnostic)


def check(tmp):
    paths = profile.source_only_paths(tmp)
    release = profile.release_chain(tmp)
    options = profile.candidate(tmp, paths)
    on = profile.source_only_candidate(tmp)
    assert on == [*options, "SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=1"]
    resolved = profile.resolved(on)
    assert {key: resolved.get(key) for key in ("PVR_PIPELINE", "PACE_CATCHUP",
            "PACE_TRANS_SKIP", "PACE_STEADY", "COARSE", "SCENERY_STREAM",
            "WORLD_PORTAL_STREAM31")} == dict(PVR_PIPELINE="2", PACE_CATCHUP="2",
            PACE_TRANS_SKIP="4063", PACE_STEADY="1", COARSE="1",
            SCENERY_STREAM="1", WORLD_PORTAL_STREAM31="1")
    assert "PACE_HOLD_LOG" not in resolved or resolved["PACE_HOLD_LOG"] == "0"
    assert len(release) > 500, "release chain was shortened"

    native = "platform/native_static.o"
    trans = "src/game/trans.o"
    native_source = "platform/native_static.cpp"
    trans_source = "../../../src/game/trans.cpp"
    absent = compile_args(accepted(tmp, options, native), native_source)
    zero = compile_args(accepted(tmp, [*options, "WORLD_PORTAL_STREAM31=0"], native), native_source)
    assert absent == zero and not any("RE4DC_WORLD_PORTAL_STREAM31" in arg for arg in absent)
    enabled = compile_args(accepted(tmp, on, native), native_source)
    assert enabled.count("-DRE4DC_WORLD_PORTAL_STREAM31=1") == 1
    assert enabled.count("-DRE4DC_SCENERY_STREAM=1") == 1
    assert enabled.count("-DRE4DC_WORLD_PORTAL_COMPLETION=1") == 1
    for fact in ("TA_DIRECT", "PS2_WORLD_HDR_CACHE", "MESH_FASTPATH", "PVR_STREAM"):
        assert enabled.count(f"-DRE4DC_{fact}=1") == 1, fact
    actual_native_guard(enabled)
    # These two pacing values are per-TU flags in pace.mk. In particular,
    # PACE_HOLD_LOG=0 is a Make default, absent from the source assignment list.
    ui_args = compile_args(accepted(tmp, on, "platform/native_ui.o"),
                           "platform/native_ui.cpp")
    assert ui_args.count("-DRE4DC_PACE_STEADY=1") == 1
    assert ui_args.count("-DRE4DC_PACE_HOLD_LOG=0") == 1

    paged = [*on, "WORLD_PAGES31=1", "WORLD_PREPARED09=1",
             "WORLD_PART_PLAN29=1", "MOVIE_WORLD_ARENA=1",
             "STATIC_OBJ_LIFETIME05=1"]
    page_args = compile_args(accepted(tmp, paged, native), native_source)
    assert page_args.count("-DRE4DC_WORLD_PAGES31=1") == 1
    assert page_args.count("-DRE4DC_WORLD_PORTAL_STREAM31=1") == 1
    actual_native_guard(page_args)

    # Primary Make catches the old pipeline=1 control because Test 15 enables
    # steady pacing. This also proves the old paired profile cannot be called ON.
    old = make(tmp, [*on, "PVR_PIPELINE=1", "PACE_TRANS_SKIP=1"], native)
    assert old.returncode != 0 and "PACE_STEADY / PACE_HOLD_LOG need PVR_PIPELINE=2" in old.stderr
    # Make only checks that the skip mask is nonzero. The actual trans.cpp
    # preprocessor guard supplies the required bit-2048 refusal.
    bad_mask = [*on, "PACE_TRANS_SKIP=1"]
    bad_trans = compile_args(accepted(tmp, bad_mask, trans), trans_source)
    assert "-DRE4DC_PACE_TRANS_SKIP=1" in bad_trans
    generated = make(tmp, on, "pace.h", dry=False)
    assert generated.returncode == 0, generated.stderr[-2500:]
    good_trans = compile_args(accepted(tmp, on, trans), trans_source)
    assert "-include" in good_trans and str(tmp / "obj/pace.h") in good_trans
    actual_trans_guard(tmp, good_trans, expected=True)
    actual_trans_guard(tmp, bad_trans, expected=False)
    no_catchup = make(tmp, [*on, "PACE_CATCHUP=1"], native)
    assert no_catchup.returncode != 0 and "COARSE needs PACE_CATCHUP=2" in no_catchup.stderr

    for values in (["SCENERY_STREAM=1"], ["WORLD_PORTAL_STREAM31=1"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=1", "SCENERY_CLIP_GATHER=1"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=1", "SCENERY_CLIP_INDEXED26=1"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=1", "SCENERY_EMIT_PREFETCH=1"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=1", "PS2_PVS_BATCH_COMPOSE=0"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=1", "WORLD_PORTAL_COMPLETION=0"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31="],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=%"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=0 1"],
                   ["SCENERY_STREAM=1", "WORLD_PORTAL_STREAM31=2"]):
        assert make(tmp, [*options, *values], native).returncode != 0, values

    solo = [*options, "PS2_PVS=0", "PS2_PVS_BATCH_COMPOSE=0",
            "WORLD_PORTAL29=0", "WORLD_PORTAL_COMPLETION=0", "SCENERY_STREAM=1",
            "WORLD_PORTAL_STREAM31=0"]
    solo_args = compile_args(accepted(tmp, solo, native), native_source)
    assert "-DRE4DC_SCENERY_STREAM=1" in solo_args
    assert not any("RE4DC_WORLD_PORTAL_STREAM31" in arg for arg in solo_args)
    print("full release-chain primary Make OFF/ON and refusals pass")
    print("actual trans.cpp COARSE/pacing guard current-mask pass; old-mask refusal pass")
    print("actual native_static.cpp portal guard ON/paged pass; disabled/clip refusals pass")
    print("actual native_ui.cpp pacing definitions STEADY=1 and HOLD_LOG=0 pass")


def main():
    with tempfile.TemporaryDirectory(prefix="world-portal-stream-profile31-") as td:
        check(Path(td))


if __name__ == "__main__":
    main()
