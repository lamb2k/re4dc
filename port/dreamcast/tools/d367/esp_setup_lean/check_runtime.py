#!/usr/bin/env python3
"""Production-extracted Build 6 host semantic checks (no game data or target FP claim).

Compare OFF/ON effective header + sprite bodies, FIFO/admission/accounting,
and actual late Essential/trim state with the new early predicate and hook.
The KOS header compiler, texture resolver and stream transport are host shims.
The unchanged common-transform prefix and projection/texture admission are
controlled boundaries, not a synthetic reimplementation of EspCommonTrans.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
ESP = ROOT / "src/game/esp_sub.cpp"
NATIVE = DC / "game/platform/native_ui.cpp"
INCLUDE = DC / "game/platform/include"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError("Command failed:\n" + " ".join(map(str, command)) + "\n" + result.stdout + result.stderr)
    return result


def function(source, signature):
    """Extract an actual function, ignoring braces inside comments and strings."""
    start = source.index(signature)
    begin = source.index("{", start)
    token = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
    depth = 0
    for match in token.finditer(source, begin):
        if match.group() == "{":
            depth += 1
        elif match.group() == "}":
            depth -= 1
            if not depth:
                return source[start:match.end()]
    raise AssertionError("unclosed function: " + signature)


def conditional(source, marker, offset=0):
    start = source.index(marker, offset)
    depth = 0
    for match in re.finditer(r"^\s*#\s*(if|ifdef|ifndef|endif)\b[^\n]*", source[start:], re.M):
        depth += -1 if match.group(1) == "endif" else 1
        if not depth:
            return source[start:start + match.end()] + "\n"
    raise AssertionError("unclosed conditional: " + marker)


def definitions(profile, unit):
    data = json.loads(profile.read_text())
    assert data["fx_level"] in (0, 3) and data["fx_trim"] == 1
    command = ["g++", "-dM", "-E", "-x", "c++", "-I" + str(INCLUDE)]
    command.extend(flag for flag in data[unit]["flags"] if flag.startswith("-D"))
    for name, expected in data[unit]["generated_headers"].items():
        header = Path(name)
        assert sha(header) == expected, "Make-derived header changed: " + name
        command += ["-include", name]
    output = run(command + ["-"], input="").stdout
    macros = {line.split(None, 2)[1]: line for line in output.splitlines()
              if line.startswith("#define RE4DC_")}
    # Source defaults outside the extracted seams remain source-derived.
    source = NATIVE.read_text() if unit == "native_ui" else ESP.read_text()
    for name in ("RE4DC_UI_HANDLES", "RE4DC_TA_GUARD", "RE4DC_FX_QUEUE_MARGIN"):
        if name not in macros:
            match = re.search(r"^#define " + name + r"\s+[^\n]+", source, re.M)
            if match:
                macros[name] = match.group()
    assert macros["RE4DC_FX_LEVEL"].split()[-1] == "0"
    assert macros["RE4DC_FX_ESSENTIAL_BOOT"].split()[-1] == str(int(data["fx_level"] == 3))
    return "\n".join(macros[name] for name in sorted(macros)) + "\n", data


def queue_source():
    source = NATIVE.read_text()
    batch = conditional(source, "#if defined(RE4DC_ESP_SETUP_LEAN)")
    begin = source.index("DeferredLighting* const kSpriteTag=")
    stop = source.index("#if defined(RE4DC_EFFECT_HAZE_LEAN)", begin)
    prefix = source[begin:stop]
    begin = source.index("#if defined(RE4DC_ESP_SETUP_BATCH)\nbool fx_packet(")
    stop = source.index("\n}\n}\n#if defined(RE4DC_EFFECT_ROOM)", begin) + 2
    packet = prefix + source[begin:stop] + "\n"
    submit = function(source, 'extern "C" int re4dc_effect_sprite(')
    drain_begin = source.index("#if defined(RE4DC_ESP_SETUP_BATCH)\n        if(deferred_first->lighting==kSpriteTag")
    drain_end = source.index("#if defined(RE4DC_EFFECT_HAZE_LEAN)", drain_begin)
    batches = "\n".join((INCLUDE / name).read_text() for name in
                        ("native_effect_haze_batch.inc", "native_effect_stage1_batch.inc"))
    template = (HERE / "runtime_queue.cpp.in").read_text()
    replacements = dict(BATCH_ENABLE=batch, PACKET=packet, SUBMIT=submit, BATCHES=batches,
                        DRAIN=source[drain_begin:drain_end],
                        RESET_FUNCTION=function(source, "void reset_deferred()"))
    for key, value in replacements.items():
        template = template.replace("@" + key + "@", value)
    assert not re.search(r"@[A-Z_]+@", template)
    return template


def essential_source():
    source = ESP.read_text()
    begin = source.index("struct FxTrim {")
    stop = source.index("static int FxLevelSpriteBase(", begin)
    common_begin = source.index("void EspCommonTrans(cEsp* esp)")
    common_end = source.index("\nvoid ", common_begin + 1)
    common = source[common_begin:common_end]
    hook = conditional(common, "#if defined(RE4DC_ESP_ESSENTIAL_EARLY)")
    # The actual hook stays after original shared state updates and before per-sprite matrix work.
    assert common.index("esp->ChannelSet()") < common.index(hook.rstrip()) < common.index("sx = esp->m_Size_base_x")
    macro = re.search(r"^#define ESP_PARTS_SCREEN[^\n]*", source, re.M).group()
    template = (HERE / "runtime_essential.cpp.in").read_text()
    for key, value in dict(ESSENTIAL=source[begin:stop], SCREEN_MACRO=macro, EARLY_HOOK=hook).items():
        template = template.replace("@" + key + "@", value)
    assert not re.search(r"@[A-Z_]+@", template)
    return template


def build_run(output, name, source, prefix, knob, overrides=()):
    cpp, exe, trace = (output / (name + suffix) for suffix in (".cpp", ".bin", ".trace"))
    controls = "#undef RE4DC_ESP_SETUP_LEAN\n#define RE4DC_ESP_SETUP_LEAN " + str(knob) + "\n"
    for macro, value in overrides:
        controls += "#undef " + macro + "\n#define " + macro + " " + str(value) + "\n"
    cpp.write_text(prefix + controls + source)
    command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-fno-pie", "-no-pie",
               "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-I" + str(INCLUDE),
               str(cpp), "-o", str(exe)]
    build = run(command)
    runtime_env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1")
    execution = run([str(exe), str(trace)], env=runtime_env)
    assert not execution.stderr, execution.stderr
    return dict(stats=json.loads(execution.stdout), trace_sha256=sha(trace), trace_bytes=trace.stat().st_size,
                fixture_sha256=sha(cpp), trace=trace, command=command,
                compile_diagnostics=build.stderr)


def pair(output, name, source, prefix, overrides=()):
    result = [build_run(output, name + suffix, source, prefix, value, overrides)
              for suffix, value in (("-off", 0), ("-on", 1))]
    assert result[0]["trace"].read_bytes() == result[1]["trace"].read_bytes(), name + " semantic trace mismatch"
    return dict(name=name, controls=dict(overrides), trace_sha256=result[0]["trace_sha256"],
                trace_bytes=result[0]["trace_bytes"], off=result[0]["stats"], on=result[1]["stats"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-fx0", type=Path, required=True)
    parser.add_argument("--profile-fx3", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, default=HERE / "runtime_receipt.json")
    reuse = parser.add_mutually_exclusive_group()
    reuse.add_argument("--reuse-essential-receipt", type=Path,
                       help="Rerun only native queue changes after proving Essential dependencies unchanged")
    reuse.add_argument("--reuse-native-receipt", type=Path,
                       help="Rerun only Essential changes after proving native queue dependencies unchanged")
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    queue, essential = queue_source(), essential_source()
    results, profiles, reused, negative = [], {}, None, []
    reuse_path = args.reuse_essential_receipt or args.reuse_native_receipt
    reused_essential = bool(args.reuse_essential_receipt)
    reused_native = bool(args.reuse_native_receipt)
    if reuse_path:
        prior = json.loads(reuse_path.read_text())
        assert prior["status"] == "PASS"
        dependencies = (ESP, HERE / "runtime_essential.cpp.in", INCLUDE / "native_ui.h") if reused_essential else (
            NATIVE, HERE / "runtime_queue.cpp.in", INCLUDE / "native_ui.h",
            INCLUDE / "native_effect_haze_batch.inc", INCLUDE / "native_effect_stage1_batch.inc",
            INCLUDE / "fx_sprite_trim.inc", INCLUDE / "fx_sprite_trim_table.inc")
        for path in dependencies:
            assert prior["source_sha256"][str(path.relative_to(ROOT))] == sha(path), "changed reused dependency: " + str(path)
        for level, profile in ((0, args.profile_fx0), (3, args.profile_fx3)):
            assert prior["profiles"][str(level)]["sha256"] == sha(profile)
        names = {"essential-fx0", "essential-fx3", "re4dc_fx_trim_log", "re4dc_esp_census", "re4dc_mist_cut"} if reused_essential else {
            "queue-fx0", "queue-fx3", "re4dc_ta_guard", "re4dc_ta_hash", "re4dc_ta_bin_diag", "re4dc_ta_material_diag"}
        results = [item for item in prior["comparisons"] if item["name"] in names]
        assert {item["name"] for item in results} == names
        negative_names = {"frame-stamps", "keep-class"} if reused_essential else {"color-key", "previous-owner", "reset-owner"}
        negative = [item for item in prior["negative_controls"] if item["name"] in negative_names]
        assert {item["name"] for item in negative} == negative_names
        archive = output / ("reused-essential-receipt.json" if reused_essential else "reused-native-receipt.json")
        archive.write_bytes(reuse_path.read_bytes())
        reused = dict(receipt=str(archive), sha256=sha(archive), comparisons=sorted(names),
                      reason="Reused suite source, fixture and profile dependencies are byte-identical; only the other runtime path changed")
    for level, profile in ((0, args.profile_fx0), (3, args.profile_fx3)):
        queue_defines, metadata = definitions(profile, "native_ui")
        essential_defines, _ = definitions(profile, "esp_sub")
        assert metadata["fx_level"] == level
        profiles[str(level)] = dict(path=str(profile.resolve()), sha256=sha(profile),
                                    fx_level=level, fx_trim=1, essential_boot=metadata["essential_boot"])
        if not reused_native:
            results.append(pair(output, f"queue-fx{level}", queue, queue_defines))
        if not reused_essential:
            results.append(pair(output, f"essential-fx{level}", essential, essential_defines))
        if level == 3:
            for name in ("RE4DC_TA_GUARD", "RE4DC_TA_HASH", "RE4DC_TA_BIN_DIAG", "RE4DC_TA_MATERIAL_DIAG"):
                if reused_native:
                    continue
                check = pair(output, name.lower(), queue, queue_defines, ((name, 1),))
                assert check["on"]["body_only"] == 0
                results.append(check)
            for name in ("RE4DC_FX_TRIM_LOG", "RE4DC_ESP_CENSUS", "RE4DC_MIST_CUT"):
                if reused_essential:
                    continue
                check = pair(output, name.lower(), essential, essential_defines, ((name, 1),))
                assert check["on"]["tail_visits"] == check["off"]["tail_visits"]
                results.append(check)
    # Negative controls remove one actual safety condition from the extracted production text.
    # A passing mutation is an inadequate fixture, not an acceptable runtime variant.
    queue_defines, _ = definitions(args.profile_fx3, "native_ui")
    essential_defines, _ = definitions(args.profile_fx3, "esp_sub")
    mutations = [
        ("color-key", queue, " && fx_hdr_key.color==s.color", "", queue_defines, "queue-fx3-off.trace"),
        ("previous-owner", queue, "fx_hdr_key.owner==previous &&", "", queue_defines, "queue-fx3-off.trace"),
        ("reset-owner", queue, "fx_setup_forget(); // queue addresses", "; // queue addresses", queue_defines, "queue-fx3-off.trace"),
        ("frame-stamps", essential, " && s_esp_setup_trim_frame == pG->Frame_cnt && s_esp_setup_ess_frame == pG->Frame_cnt", "", essential_defines, "essential-fx3-off.trace"),
        ("keep-class", essential, "if (c == ESS_KEEP) return 0;", "if (c == ESS_KEEP) return 1;", essential_defines, "essential-fx3-off.trace"),
    ]
    for name, source, before, after, prefix, oracle in mutations:
        if reuse_path and name in negative_names:
            continue
        assert before in source, "mutation pattern changed: " + name
        # The keep mutation targets the final occurrence (the new predicate, not the late oracle).
        if name == "keep-class":
            index = source.rindex(before); changed = source[:index] + after + source[index + len(before):]
        else:
            changed = source.replace(before, after, 1)
        result = build_run(output, "mutation-" + name, changed, prefix, 1)
        assert result["trace"].read_bytes() != (output / oracle).read_bytes(), "undetected mutation: " + name
        negative.append(dict(name=name, detected=True))
    source_paths = [ESP, NATIVE, INCLUDE / "native_effect_haze_batch.inc", INCLUDE / "native_effect_stage1_batch.inc",
                    INCLUDE / "fx_sprite_trim.inc", INCLUDE / "fx_sprite_trim_table.inc", INCLUDE / "native_ui.h",
                    HERE / "check_runtime.py", HERE / "runtime_queue.cpp.in", HERE / "runtime_essential.cpp.in"]
    receipt = dict(status="PASS", scope=__doc__, compiler=run(["g++", "--version"]).stdout.splitlines()[0],
                   sanitizer="address,undefined; LeakSanitizer disabled because this sandbox cannot inspect /proc tasks", profiles=profiles, comparisons=results, negative_controls=negative,
                   reused_unchanged_checks=reused,
                   source_sha256={str(path.relative_to(ROOT)): sha(path) for path in source_paths},
                   limitations=["No game data, Flycast or console execution.",
                       "Host FP and synthetic texture/stream stubs; no target FP or KOS bit-encoding proof.",
                       "Effective ordered header+body payload equality; redundant header bytes intentionally differ.",
                       "Early hook test controls the unchanged matrix/projection/texture-admission boundary; it does not execute all EspCommonTrans callbacks."])
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", comparisons=len(results), negative_controls=len(negative), receipt=str(args.receipt))))


if __name__ == "__main__":
    main()
