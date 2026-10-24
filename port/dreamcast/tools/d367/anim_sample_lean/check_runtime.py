#!/usr/bin/env python3
"""Differential checks of production Hermite samplers on synthetic key streams.

The public Make-derived profile selects the sampler. This extracts the complete
production sampler/decoder block and the real Hermite arithmetic expression;
it does not reimplement interpolation. Host type definitions and pointer-width
adaptation come from the established tools/motion/host helper. The HF_ASM host
edge, when selected, calls the original C sampler and is explicitly not SH4
assembly/FP conformance. No game data is read.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = ROOT / "src/game/motion.cpp"
MATH = ROOT / "src/game/math_sub.cpp"
MODEL = ROOT / "src/game/model.cpp"
HOST = ROOT / "tools/motion/host"
spec = importlib.util.spec_from_file_location("motion_host_prepare", HOST / "prepare.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def function(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 1
    cursor = brace + 1
    while depth:
        depth += (text[cursor] == "{") - (text[cursor] == "}")
        cursor += 1
    return text[start:cursor]


def extract(source):
    options = source[source.index("// ANIM_SAMPLE_LEAN"):source.index("extern const Vec vecZero;")]
    prefix = source[source.index("typedef void (*FccGetData)"):source.index("// Moves every parts'")]
    body = source[source.index("// Evaluates one joint's three axis key streams"):
                  source.index("// Debug speed display:")]
    math = function(MATH.read_text(), "f32 hermite(f32* p, f32* v, f32 t)")
    entry = "static int HermiteInterpolationClamped(HermitePrm* prm, Vec* out, u16* hist)\n{"
    assert body.count(entry) == 1, "clamp entry changed"
    body = body.replace(entry, entry + "\n    ++fixture_clamped_calls;\n    if (fixture_core_site < 9) ++fixture_clamped_sites[fixture_core_site];")
    leaf = "int hfClamped(HermitePrm* prm, Vec* out, u16* hist)\n{"
    assert body.count(leaf) == 1, "clamp helper changed"
    body = body.replace(leaf, leaf + "\n    ++fixture_clamp_kernel_calls;")
    return prepare.host_text(options + "\n" + prefix + "\n" + body + "\n" + math)


def core(source):
    caller = function(source, "void MotionMoveCore(cModel* m, MotionWork* w, int flag)")
    sites = ["&cam->out[" + str(i) + "]" for i in range(5)] + ["&p->ang", "&p->pos", "&p->scale", "&p->ang"]
    position = 0
    for index, argument in enumerate(sites):
        start = caller.index("MOTION_POSE_SAMPLE(pp, " + argument, position)
        line = caller.rfind("\n", 0, start) + 1
        indent = caller[line:start]
        assert not indent.strip(), "sample call isn't a statement"
        addition = indent + f"fixture_sample_event({index}, pp);\n"
        caller = caller[:line] + addition + caller[line:]
        position = start + len(addition) + 1
    template = (HERE / "fixture_core.cpp.in").read_text()
    return template.replace("@MOVE_CORE@", prepare.host_text(caller)).replace("@GET_PARTS@", prepare.host_text(
        function(MODEL.read_text(), "RE4_INLINE cModel* cModel::getPartsPtr(int no)"))).replace("@RAD_LIMIT@", prepare.host_text(
        function(MATH.read_text(), "void VecRadLimit(Vec* v)")))


def macros(row):
    result = []
    for word in row["flags"]:
        if word.startswith(("-DRE4DC_HERMITE_FAST", "-DRE4DC_HF_")):
            result.append(word)
    return result


def mutate(source, name):
    if name == "wrong-last-key":
        old = "        o[axis] = L::v(data, n - 1);"
        new = "        o[axis] = L::v(data, 0);"
    elif name == "lost-fallback":
        old = "        if (idx >= n) return hfReg<T>(prm, out, hist);"
        new = "        if (idx >= n) return 0; // deliberately omit the required fallback"
    elif name == "force-clamp-pose":
        old = "pp->maxFrame <= pp->frame && (pp->flags & 6) != 4 ? HermiteInterpolationClamped : HermiteInterpolation;"
        new = "true ? HermiteInterpolationClamped : HermiteInterpolation;"
    else:
        raise AssertionError(name)
    assert source.count(old) == 1, (name, "control location changed")
    return source.replace(old, new)


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = SOURCE.read_text()
    profile = json.loads(args.profile.read_text())
    template = (HERE / "fixture_sampler.cpp.in").read_text()
    modes = ["reg1"] if args.mode in ("smoke", "negative", "sanitizer") else list(profile["profiles"])
    if args.profiles:
        assert set(args.profiles) <= set(profile["profiles"]), "unknown profile"
        modes = args.profiles
    rows = []
    controls = [None] if args.mode != "negative" else ["wrong-last-key", "lost-fallback", "force-clamp-pose"]
    for control in controls:
        for mode in modes:
            pair = []
            for lean in (0, 1):
                changed = mutate(source, control) if control and lean else source
                fixture = template.replace("@SAMPLER@", extract(changed)).replace("@CORE@", core(changed))
                label = f"{mode}-{control or 'normal'}-lean{lean}"
                cpp, exe, binary = output / (label + ".cpp"), output / label, output / (label + ".bin")
                cpp.write_text(fixture)
                command = [args.cxx, "-std=gnu++17", "-O2", "-fno-strict-aliasing", "-fno-fast-math",
                    "-ffp-contract=off", "-Wno-register", "-Wno-unused-variable", "-Wno-unused-function",
                    "-I", str(HOST / "stub"), "-DRE4DC_GAME=1", f"-DRE4DC_ANIM_SAMPLE_LEAN={lean}",
                    *macros(profile["profiles"][mode]), str(cpp), "-o", str(exe)]
                if control:
                    command[2:2] = ["-DFIXTURE_CORE_ONLY=1"]
                if args.mode == "sanitizer":
                    command[2:2] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g"]
                compiled = subprocess.run(command, capture_output=True)
                (output / (label + ".compile.log")).write_bytes(compiled.stdout + compiled.stderr)
                assert compiled.returncode == 0, (label, "compile", compiled.stderr.decode()[-4000:])
                env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
                executed = subprocess.run([str(exe), str(binary)], capture_output=True, env=env)
                (output / (label + ".stdout")).write_bytes(executed.stdout)
                (output / (label + ".stderr")).write_bytes(executed.stderr)
                if control and lean and executed.returncode != 0:
                    assert b"Assertion" in executed.stderr, (label, "unrelated negative failure")
                    pair.append(None)
                    rows.append(dict(profile=mode, lean=lean, negative_control=control,
                        fixture_sha256=sha(cpp), detected="expected fixture assertion",
                        returncode=executed.returncode, stderr=executed.stderr.decode(), command=command))
                    continue
                assert executed.returncode == 0, (label, "run", executed.stderr.decode()[-4000:])
                assert not executed.stderr, (label, "unexpected diagnostics", executed.stderr.decode()[-2000:])
                stats = json.loads(executed.stdout)
                content = binary.read_bytes()
                pair.append(content)
                rows.append(dict(profile=mode, lean=lean, negative_control=control,
                    fixture_sha256=sha(cpp), output_sha256=sha(binary), output_bytes=len(content),
                    stats=stats, command=command, host_assembly_edge=mode == "asm1"))
            same = pair[0] == pair[1]
            assert same != bool(control), (mode, control, "unexpected differential result")
            print("PASS", mode, control or "normal", len(pair[0]), flush=True)
    assert SOURCE.read_text() == source, "runtime changed during checks"
    receipt = dict(status="PASS", scope=__doc__, source_sha256=sha(SOURCE), profile_sha256=sha(args.profile),
        tool_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                     (Path(__file__), HERE / "fixture_sampler.cpp.in", HERE / "fixture_core.cpp.in", HOST / "prepare.py", HOST / "stub/re4_host_stub.h", MATH, MODEL)},
        adaptations=["Established host fixed-width types and pointer-width adaptation",
                     "Fixture-only u16_un alias matching source unaligned halfword contract",
                     "HF_ASM host edge uses original C sampler; target assembly requires separate checks",
                     "MotionMoveCore native lease pass-through and MAP_32BIT synthetic key image",
                     "Unchanged matrix helpers are deterministic recorded edges; VecRadLimit and getPartsPtr are production bodies",
                     "Fixture-only helper-entry and nine caller-site counters establish route coverage"],
        mode=args.mode, configurations=rows)
    (output / "runtime_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("all", "smoke", "negative", "sanitizer"), default="all")
    parser.add_argument("--profiles", nargs="+")
    parser.add_argument("--cxx", default="g++")
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], configurations=len(result["configurations"]))))


if __name__ == "__main__":
    main()
