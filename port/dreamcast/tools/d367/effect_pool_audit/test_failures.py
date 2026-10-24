#!/usr/bin/env python3
"""Compile/exercise real source bodies against explicit pool/refusal fixtures.

Host sanitizer controls, not console execution or a gameplay trace. The single
allocator-signature adaptation replaces its member operator-new declaration
with a normal function so the host's size_t ABI cannot change the source body.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
from source_tools import function

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def run(args):
    root, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    pool = (root / "src/game/esp.cpp").read_text()
    pool_bodies = [function(pool, "int PullEsp(cEsp** out, int id)"),
                   function(pool, "void PushEsp(cEsp* esp)"),
                   function(pool, "void* cEsp::operator new(unsigned int size)")]
    pool_text = "\n\n".join(pool_bodies).replace(
        "void* cEsp::operator new(unsigned int size)", "void* allocate_slot(unsigned int size)")
    owner_bodies = [function(pool, signature) for signature in (
        "static inline void fxEspOwnBit(cEspSystem* sys, cEsp* esp, int on)",
        "static inline void fxEspMark(cEspSystem* sys, cEsp* esp, int on)",
        'extern "C" void re4dc_esp_info_set(cEsp* esp, const EspInfo* info)')]
    vector_source = (root / "src/game/esp3f.cpp").read_text()
    vector_destructor = function(vector_source, "void cEsp3f::Destruct()")
    cpp = output / "pool.cpp"
    cpp.write_text((HERE / "pool_fixture.cpp.in").read_text()
                   .replace("@SOURCE_BODIES@", pool_text)
                   .replace("@OWNER_BODIES@", "\n\n".join(owner_bodies))
                   .replace("@BUFFER_DESTRUCTOR@", vector_destructor))
    results, commands = [], []
    base_flags = [args.host_cxx, "-std=c++17", "-O1", "-g", "-fno-omit-frame-pointer",
                  "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-pie", "-no-pie",
                  "-DRE4DC_GAME=1"]
    for owner, scan, diagnostic in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1)):
        outputs = {}
        for enabled in (0, 1):
            name = f"pool-r{enabled}-o{owner}-s{scan}-d{diagnostic}"
            exe = output / name
            command = [*base_flags, f"-DRE4DC_ESP_POOL_RECYCLE={enabled}",
                       f"-DRE4DC_ESP_OWNER={owner}", f"-DRE4DC_FX_SCAN={scan}",
                       f"-DRE4DC_ESP_POOL_DIAG={diagnostic}", str(cpp), "-o", str(exe)]
            commands.append(command)
            built = subprocess.run(command, capture_output=True, text=True)
            (output / (name + ".build.log")).write_text(built.stdout + built.stderr)
            assert built.returncode == 0, built.stderr
            for scenario in ("refuse", "free", "forward", "wrap", "forward-children", "wrap-children"):
                checked = subprocess.run([str(exe), scenario], capture_output=True, text=True,
                                         env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
                (output / (name + "-" + scenario + ".log")).write_text(checked.stdout + checked.stderr)
                assert checked.returncode == 0, (name, scenario, checked.stdout, checked.stderr)
                outputs[enabled, scenario] = checked.stdout
                results.append(dict(arm=name, scenario=scenario, stdout=checked.stdout.strip()))
        for scenario in ("refuse", "free", "forward", "forward-children"):
            assert outputs[0, scenario] == outputs[1, scenario], (owner, scan, diagnostic, scenario)
    r117 = (root / "src/st1/r117.cpp").read_text()
    r117_bodies = [function(r117, signature) for signature in (
        "static inline int r117_espEnd(cEsp* esp)",
        'extern "C" void r117_LightSet(int n)',
        'extern "C" void r117_LightDirCalc(int n)',
        'extern "C" void r117_LightRotate(int no, f32 dir)',
        "static void r117_LightMechanismMove()")]
    cpp = output / "r117.cpp"
    cpp.write_text((HERE / "r117_fixture.cpp.in").read_text().replace(
        "@SOURCE_BODIES@", "\n\n".join(r117_bodies)))
    r117_results, normal = [], {}
    for enabled in (0, 1):
        name = f"r117-f{enabled}"
        exe = output / name
        command = [*base_flags, f"-DRE4DC_R117_EFFECT_FAILURE_SAFE={enabled}", str(cpp), "-o", str(exe)]
        commands.append(command)
        built = subprocess.run(command, capture_output=True, text=True)
        (output / (name + ".build.log")).write_text(built.stdout + built.stderr)
        assert built.returncode == 0, built.stderr
        scenarios = [("normal", 0), ("wait", 7)]
        scenarios += [(scenario, mask) for scenario in ("direction", "rotate", "wrong", "solved")
                      for mask in (range(1, 8) if enabled else (7,))]
        for scenario, mask in scenarios:
            checked = subprocess.run([str(exe), scenario, str(mask)], capture_output=True, text=True,
                                     env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
            (output / f"{name}-{scenario}-{mask}.log").write_text(checked.stdout + checked.stderr)
            should_fault = not enabled and scenario != "normal"
            if should_fault:
                assert checked.returncode != 0, (name, scenario, "negative control did not fault")
                assert "runtime error:" in checked.stderr or "AddressSanitizer" in checked.stderr, checked.stderr
            else:
                assert checked.returncode == 0, (name, scenario, checked.stdout, checked.stderr)
            if scenario == "normal": normal[enabled] = checked.stdout
            r117_results.append(dict(arm=name, scenario=scenario, fail_mask=mask,
                                     expected_original_null_fault=should_fault,
                                     stdout_sha256=digest(checked.stdout),
                                     result=checked.stdout.splitlines()[0] if checked.stdout else checked.stderr.splitlines()[0]))
    assert normal[0] == normal[1], "successful R117 outputs changed"
    report = dict(status="PASS", scope=__doc__, pool_runs=len(results), pool_results=results,
                  r117_runs=len(r117_results), r117_results=r117_results,
                  successful_r117_outputs_equal=True, successful_r117_output_sha256=digest(normal[0]),
                  source_head=subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
                  source_sha256={"src/game/esp.cpp": digest(pool), "src/st1/r117.cpp": digest(r117),
                                 "src/game/esp3f.cpp": digest(vector_source)},
                  extracted_pool_bodies_sha256=digest("\n\n".join(pool_bodies)),
                  extracted_owner_bodies_sha256=digest("\n\n".join(owner_bodies)),
                  extracted_buffer_destructor_sha256=digest(vector_destructor),
                  extracted_r117_bodies_sha256=digest("\n\n".join(r117_bodies)),
                  allocator_signature_adaptation_only=True,
                  sanitizers="AddressSanitizer + UndefinedBehaviorSanitizer; LeakSanitizer disabled (sandbox ptrace)",
                  commands=commands)
    (output / "failure-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", pool_runs=len(results), r117_runs=len(r117_results))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-cxx", default="g++")
    run(parser.parse_args())
