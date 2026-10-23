#!/usr/bin/env python3
"""Qualify the production actor ABC2 producer and front dispatch integration.

The full actor TU runs through its existing portable non-SQ branches. The exact
direct Part method bodies and both reset/completion blocks are byte-extracted,
with only hardware emission replaced by counters. This is not full actor draw,
skin/gameplay/visual execution, target timing, or hardware acceptance evidence.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
NATIVE = DC / "game/platform/native_actor_fast.cpp"
HELPER = DC / "game/platform/backface_certificate.cpp"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def method(text, marker):
    start = text.index(marker)
    # CPU1/CPU2 preprocessor alternatives deliberately contain two opening
    # if braces and one shared close. The production indentation supplies the
    # method/block boundary without rewriting either alternative.
    indent = marker[:len(marker) - len(marker.lstrip())]
    end = text.index("\n" + indent + "}", start) + len(indent) + 2
    return text[start:end]


def run(command, out, stem, input_text=None, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, input=input_text, capture_output=True, text=True, timeout=120)
    (out / (stem + ".stdout")).write_text(result.stdout)
    (out / (stem + ".stderr")).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{stem} failed ({result.returncode}): {result.stderr[-6000:]}")
    return result.stdout


def target_controls(args, out, baseline):
    if not (args.sh4_cxx or args.kos_root):
        return {"status": "not requested"}
    if not (args.sh4_cxx and args.kos_root):
        raise ValueError("Full target TU controls need --sh4-cxx and --kos-root together")
    target = out / "target"
    target.mkdir()
    flags = ["-std=gnu++20", "-Wall", "-Wextra", "-Os", "-g0", "-fno-PIC", "-fno-PIE",
             "-fomit-frame-pointer", "-m4-single", "-ml", "-mfsrra", "-mfsca", "-ffunction-sections",
             "-fdata-sections", "-matomic-model=soft-gusa", "-ftls-model=local-exec", "-fno-exceptions",
             "-fno-unwind-tables", "-fno-asynchronous-unwind-tables", "-fno-threadsafe-statics",
             "-D__DREAMCAST__", "-D_arch_dreamcast=1", "-D_arch_sub_pristine=1", "-DRE4DC_GAME"]
    kos = args.kos_root.resolve()
    for include in (kos / "include", kos / "kernel/arch/dreamcast/include", kos / "addons/include"):
        flags += ["-isystem", str(include)]
    for include in (DC / "game/platform/include", DC / "game", args.sdk.resolve() / "include"):
        flags += ["-I" + str(include)]
    macros = dict(CPU_BACKFACE=2, ACTOR_DIRECT=1, COARSE_ONE_SUBMIT=1, NATIVE_ACTOR=1,
                  NATIVE_ACTOR_FAST=1, NATIVE_ACTOR_SKIN=1, NATIVE_ACTOR_SKIN_LAZY=1,
                  ACTOR_TRANSACTION=1, ACTOR_UV16=0, TA_GUARD=0, TA_DIRECT=1, ACTOR_LOG=0)
    flags += [f"-DRE4DC_{name}={value}" for name, value in macros.items()]
    current = NATIVE.read_text()
    receipts = []
    for cones in (0, 1):
        variants = [("base", baseline, []), ("absent", current, []),
                    ("zero", current, ["-DRE4DC_BACKFACE_CONE_FRONT=0"])]
        if cones:
            variants += [("on1", current, ["-DRE4DC_BACKFACE_CONE_FRONT=1"]),
                         ("on2", current, ["-DRE4DC_BACKFACE_CONE_FRONT=2"])]
        for label, source, extra in variants:
            stem = f"cones{cones}-{label}"
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c"])):
                if label.startswith("on") and suffix == "ii":
                    continue
                destination = target / (stem + "." + suffix)
                command = [str(args.sh4_cxx.resolve()), *flags, f"-DRE4DC_ACTOR_BACKFACE_CONE={cones}",
                           *extra, "-x", "c++", "-", *phase, "-o", str(destination)]
                run(command, target, stem + "-" + suffix, input_text=source, cwd=NATIVE.parent)
                receipts.append({"actor_cones": cones, "variant": label, "artifact": destination.name,
                                 "bytes": destination.stat().st_size, "sha256": sha(destination), "command": command})
        for suffix in ("ii", "o"):
            original = (target / f"cones{cones}-base.{suffix}").read_bytes()
            for label in ("absent", "zero"):
                assert original == (target / f"cones{cones}-{label}.{suffix}").read_bytes(), \
                    f"Target OFF identity failed: actor_cones={cones}, variant={label}, artifact={suffix}"
    return {"status": "passed", "receipts": receipts,
            "scope": "Complete production native_actor_fast.cpp target TU, real KOS/SDK headers, DIRECT1 and COARSE_ONE_SUBMIT1; no renderer link or execution."}


def suite(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    text = NATIVE.read_text()
    extractions = {}
    for key, marker in (("BF_ON", "    bool bf_on() const {"),
                        ("STRIP", "    void strip(const u8* index, unsigned n) {"),
                        ("WHOLE", "    bool whole(const u8* index, unsigned count, unsigned triangles) {")):
        extractions[key] = method(text, marker)
    loops = list(re.finditer(r"    for \(unsigned mi = 0; ok && mi < blob->meshlets; \+\+mi\) \{", text))
    assert len(loops) == 2, "Both production draw loops must be accounted for"
    back_marker = "            if (cn.k && abc_eye(f, p.cull, cn.pal, abc_e) && abc_reject(cn, abc_e)) {"
    baseline = subprocess.check_output(["git", "show", f"{args.baseline}:port/dreamcast/game/platform/native_actor_fast.cpp"], cwd=ROOT, text=True)
    original_back = method(baseline, back_marker)
    for name, loop in zip(("REGULAR", "CHUNK"), loops):
        tail = text[loop.end():]
        reset_end = tail.index("        const MeshletInfo& m")
        reset = tail[:reset_end]
        assert reset.count("e.cone_front = false;") == 1
        assert reset_end < tail.index("        if (!ni) continue;")
        extractions["RESET_" + name] = reset
        start = tail.index("        if (abc_candidate && !(any & (kOcCull | kOcNear)))")
        end = tail.index(";", start) + 1
        extractions["FINISH_" + name] = tail[start:end]
        assert method(tail, back_marker) == original_back, "Legacy back test must remain byte-identical"
        assert tail.index(back_marker) < tail.index("abc_front_prepare(") < start
        assert tail.index("abc_front_worth(") < tail.index("abc_front_prepare(")
        gate = tail[tail.index("            if (!(e.direct && p.blend == 0"):tail.index("abc_front_prepare(")]
        for guard in ("!(p.material_flags & 4u)", "p.depth_mode == 0", "abc_front[mi].min_normal > 0.0f"):
            assert guard in gate
        gate_start = tail.index("#if RE4DC_BACKFACE_CONE_FRONT && RE4DC_ACTOR_DIRECT")
        gate_end = tail.index("\n#endif\n        }", gate_start) + len("\n#endif")
        extractions["GATE_" + name] = tail[gate_start:gate_end]
        missing_start = tail.index("#if RE4DC_BACKFACE_CONE_FRONT == 2 && RE4DC_ACTOR_DIRECT", gate_end)
        missing_end = tail.index("\n#endif", missing_start) + len("\n#endif")
        extractions["MISSING_" + name] = tail[missing_start:missing_end]
        clipped_start = tail.index("#if RE4DC_BACKFACE_CONE_FRONT == 2 && RE4DC_ACTOR_BACKFACE_CONE", gate_end)
        clipped_end = tail.index("\n#endif", clipped_start) + len("\n#endif")
        extractions["CLIPPED_" + name] = tail[clipped_start:clipped_end]
    fixture = (HERE / "actor_fixture.cpp").read_text().replace("@NATIVE_SOURCE@", NATIVE.as_posix())
    for key, value in extractions.items():
        fixture = fixture.replace("@" + key + "@", value)
    assert not re.search(r"@[A-Z_]+@", fixture)
    (out / "fixture.cpp").write_text(fixture)
    (out / "dc").mkdir()
    (out / "dc/pvr.h").write_text(
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n"
        "struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n"
        "struct pvr_poly_hdr_t{std::uint32_t words[8];};\n"
        "#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n"
        "int pvr_prim(const void*,std::size_t);\n")
    # Only declarations are needed for host compilation; no SDK function is
    # called. Keep the production ABI header rather than a test substitute.
    sdk = args.sdk.resolve()
    assert (sdk / "include/sh4zam/shz_strip.h").is_file()
    common = [args.cxx, "-std=c++20", "-O2", "-g0", "-fno-fast-math", "-ffp-contract=off",
              "-ffunction-sections", "-fdata-sections", "-DRE4DC_ACTOR_TEST=1",
              "-DRE4DC_CPU_BACKFACE=2", "-DRE4DC_ACTOR_DIRECT=0", "-DRE4DC_ACTOR_BACKFACE_CONE=1",
              "-DRE4DC_COARSE_ONE_SUBMIT=0", "-DRE4DC_ACTOR_LOG=0",
              "-I" + str(out), "-I" + str(DC / "game/platform/include"),
              "-I" + str(DC / "game"), "-I" + str(sdk / "include")]
    report = {"status": "running", "baseline": args.baseline, "arms": [], "off_identity": [],
              "extractions": {key: hashlib.sha256(value.encode()).hexdigest() for key, value in extractions.items()},
              "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (NATIVE, HELPER, DC / "room/backface_certificate.hpp", HERE / "actor_fixture.cpp", HERE / "actor_test.py")},
              "limits": ["The complete production TU is compiled for its existing portable host branches.",
                         "Model-source lookup and hardware emitter calls are explicit fixture boundaries.",
                         "Both draw-loop state blocks and direct Part methods are exact production extracts; full draw execution is not claimed.",
                         "Mode 2 uses the production host FMAC oracle; target instruction/packet qualification is provided by the separate kernel/helper suites.",
                         "No game assets, emulator run, hardware timing or gameplay/visual acceptance is asserted."]}
    try:
        tails = []
        for mode in (0, 1, 2):
            name = f"actor-front{mode}"
            command = common + [f"-DRE4DC_BACKFACE_CONE_FRONT={mode}", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                                "-Wl,--gc-sections", str(out / "fixture.cpp"), str(HELPER), "-o", str(out / name)]
            run(command, out, name + "-compile")
            stdout = run([str(out / name)], out, name + "-run")
            match = re.search(r"PASS mode=(\d+) cases=(\d+) checks=(\d+)", stdout)
            assert match, name + " has no PASS receipt"
            tails.append(re.findall(r"ABC1 capacity=(\d+) hash=([0-9a-f]+)", stdout))
            report["arms"].append({"mode": mode, "command": command, "cases": int(match[2]), "checks": int(match[3]),
                                   "perspective_acceptances": [dict(gathered=bool(int(g)), yaw=float(yaw), pitch=float(pitch),
                                                                    wlo=float(lo), whi=float(hi))
                                       for g, yaw, pitch, lo, hi in re.findall(r"PERSPECTIVE gathered=(\d+) yaw=(-?\d+) pitch=(-?\d+) wlo=([\d.]+) whi=([\d.]+) accepted=1", stdout)],
                                   "binary_sha256": sha(out / name)})
        assert tails[0] == tails[1] == tails[2], "Optional front proof changed the legacy ABC1 tail"
        report["abc1_tails_identical"] = tails[0]
        # Relative production includes resolve through a small symlink mirror.
        base_dir = out / "baseline/game/platform"
        base_dir.mkdir(parents=True)
        base_source = base_dir / "native_actor_fast.cpp"
        base_source.write_text(baseline)
        (base_dir / "include").symlink_to(DC / "game/platform/include", target_is_directory=True)
        (out / "baseline/room").symlink_to(DC / "room", target_is_directory=True)
        for cones in (0, 1):
            # ACTOR_TEST intentionally embeds __LINE__ in converter failure
            # diagnostics. Compare the production TU, without that test-only
            # counter, so newly inserted guarded lines are not binary data.
            flags = [x for x in common if x not in ("-DRE4DC_ACTOR_BACKFACE_CONE=1", "-DRE4DC_ACTOR_TEST=1")]
            flags += ["-DRE4DC_BACKFACE_CONE_FRONT=0", f"-DRE4DC_ACTOR_BACKFACE_CONE={cones}"]
            objects, preprocess = [], []
            for label, source in (("base", base_source), ("current", NATIVE)):
                stem = f"off-cones{cones}-{label}"
                obj = out / (stem + ".o")
                run(flags + ["-c", str(source), "-o", str(obj)], out, stem + "-compile")
                pp = run(flags + ["-E", "-P", str(source)], out, stem + "-preprocess")
                objects.append(sha(obj)); preprocess.append(hashlib.sha256(pp.encode()).hexdigest())
            assert objects[0] == objects[1], f"front=0 cones={cones}: host object bytes changed"
            assert preprocess[0] == preprocess[1], f"front=0 cones={cones}: preprocessed TU changed"
            report["off_identity"].append({"actor_cones": cones, "object_sha256": objects[0], "preprocessed_sha256": preprocess[0]})
        report["target"] = target_controls(args, out, baseline)
        report["status"] = "passed"
    except BaseException as error:
        report["status"] = "failed"; report["error"] = repr(error)
        raise
    finally:
        (out / "actor-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "arms": report["arms"], "off_identity": report["off_identity"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new evidence directory")
    parser.add_argument("--sdk", type=Path, required=True, help="materialized pinned SH4ZAM SDK")
    parser.add_argument("--baseline", default="f3fef82cf212bb379e5cf3119daee0d7a8db7e58")
    parser.add_argument("--cxx", default=shutil.which("g++") or "g++")
    parser.add_argument("--sh4-cxx", type=Path, help="optional official target C++ compiler")
    parser.add_argument("--kos-root", type=Path, help="real KOS source tree for full target TU controls")
    suite(parser.parse_args())
