#!/usr/bin/env python3
"""Compile Make-derived Test22 cache users and pinned KOS controls; no assets/run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
sys.path.insert(0, str(HERE.parent / "world_setup_spike"))
import release_profile
from prepare import INPUTS, CALLERS, prepare
from check_objects import check


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Runner:
    def __init__(self, output):
        self.output, self.commands = output, []

    def run(self, command, label, cwd=None):
        command = [str(x) for x in command]
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=dict(os.environ, SOURCE_DATE_EPOCH="1760000000"))
        (self.output / (label + ".stdout")).write_bytes(result.stdout)
        (self.output / (label + ".stderr")).write_bytes(result.stderr)
        self.commands.append(dict(command=command, cwd=str(cwd) if cwd else None,
                                  label=label, returncode=result.returncode))
        (self.output / "commands.json").write_text(json.dumps(self.commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(label + ": " + result.stderr.decode(errors="replace")[-8000:])
        return result.stdout


def headers_from_make(output):
    for line in output.replace("\\\n", " ").splitlines():
        if not line.startswith("printf "):
            continue
        words = shlex.split(line)
        at = next(i for i, word in enumerate(words) if word in (">", ">>"))
        target = Path(words[at + 1])
        if not str(target).endswith(".h.tmp"):
            continue
        target = target.with_suffix("")
        fmt = bytes(words[1], "utf8").decode("unicode_escape")
        text = fmt % tuple(words[2:at])
        target.parent.mkdir(parents=True, exist_ok=True)
        if words[at] == ">>":
            text = target.read_text() + text
        target.write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--kos-root", type=Path, required=True)
    p.add_argument("--sh4-cxx", type=Path, required=True)
    p.add_argument("--sdk-root", type=Path, required=True)
    p.add_argument("--base", default="ea969bb241f77291d2ca43d706c9dc2d1226ee76",
                   help="unchanged RE4 commit for the knob-off Make comparison")
    a = p.parse_args()
    output, kos = a.output.resolve(), a.kos_root.resolve()
    cxx, sdk = a.sh4_cxx.resolve(), a.sdk_root.resolve()
    prefix = str(cxx).removesuffix("g++")
    output.mkdir(parents=True, exist_ok=False)
    run = Runner(output)
    _, profile = release_profile.derive(output / "profile", cxx, kos, sdk)
    base_command = profile["command"]
    old_target = output / "profile/obj/platform/native_static.o"
    patch = DC / "patches/kos-804b319-cache-p2.patch"
    prepared = output / "profile/obj/koscache-p2"
    preparation = prepare(kos, prepared, patch)
    overlay = prepared / "tree/kernel/arch/dreamcast/include"
    baseline_make = output / "Makefile.baseline"
    baseline_make.write_bytes(subprocess.check_output(
        ["git", "show", a.base + ":port/dreamcast/game/Makefile"], cwd=ROOT))
    results = {}

    def command_for(name, knobs, baseline=False, kos_unit=False):
        target = output / "profile/obj" / ("koscache-p2" if kos_unit else "platform") / (name + ".o")
        command = [str(target) if x == str(old_target) else x for x in base_command]
        command += knobs
        if baseline:
            command += ["-f", str(baseline_make)]
        label = name + "-make-" + ("base" if baseline else "_".join(knobs) or "absent")
        text = run.run(command, label, cwd=DC / "game").decode()
        headers_from_make(text)
        lines = [shlex.split(line) for line in text.replace("\\\n", " ").splitlines()
                 if line.startswith("kos-c++ ") or line.startswith("kos-cc ")]
        assert len(lines) == 1, (label, lines)
        command = lines[0]
        assert command[-2:] == ["-o", str(target)], command
        source = Path(command[-3])
        if not source.is_absolute():
            source = (DC / "game" / source).resolve()
        flags = [x for x in command[1:-4] if x not in ("-MMD", "-MP")]
        for i, word in enumerate(flags):
            if word.startswith("-I") and not Path(word[2:]).is_absolute():
                flags[i] = "-I" + str((DC / "game" / word[2:]).resolve())
            elif i and flags[i - 1] in ("-include", "-isystem") and not Path(word).is_absolute():
                flags[i] = str((DC / "game" / word).resolve())
        if not kos_unit:
            flags += ["-I" + str(sdk / "include")]
        return [str(cxx if command[0] == "kos-c++" else prefix + "gcc"), *flags], source, command

    def build(label, flags, source):
        obj, pre = output / (label + ".o"), output / (label + ".i")
        run.run([*flags, "-E", "-P", source, "-o", pre], label + "-preprocess")
        run.run([*flags, "-H", "-fstack-usage", "-c", source, "-o", obj], label + "-compile")
        run.run([prefix + "objdump", "-dr", obj], label + "-disassembly")
        symbols = run.run([prefix + "nm", "-S", obj], label + "-symbols").decode()
        return dict(preprocessed_sha256=sha(pre), object_sha256=sha(obj), object_bytes=obj.stat().st_size,
                    helper_reference=" U _arch_dcache_wback_all_p2" in symbols,
                    object=str(obj), stack_usage=obj.with_suffix(".su").read_text().splitlines())

    # Every game-side user, with existing linewise experiment both off and on.
    for name in ("misc", "modules", "subscreen_backing"):
        results[name] = {}
        for linewise in (0, 1):
            arms = {}
            commands = {}
            for arm in ("base", "absent", "zero", "on"):
                knobs = [f"CACHE_LINEWISE={linewise}"]
                if arm in ("zero", "on"):
                    knobs += ["KOS_CACHE_P2=" + ("1" if arm == "on" else "0")]
                flags, source, command = command_for(name, knobs, baseline=arm == "base")
                label = f"{name}-l{linewise}-{arm}"
                arms[arm] = build(label, flags, source)
                commands[arm] = command
                if arm == "on":
                    trace = (output / (label + "-compile.stderr")).read_text()
                    assert str(overlay / "arch/cache.h") in trace, label
                    assert str(kos / "kernel/arch/dreamcast/include/arch/cache.h") not in trace, label
                    assert arms[arm]["helper_reference"] == (linewise == 0), (label, arms[arm])
            for arm in ("absent", "zero"):
                assert commands[arm] == commands["base"], (name, arm, "compile command changed")
                assert arms[arm]["preprocessed_sha256"] == arms["base"]["preprocessed_sha256"], (name, arm)
                assert arms[arm]["object_sha256"] == arms["base"]["object_sha256"], (name, arm)
            if linewise:
                assert arms["on"]["object_sha256"] == arms["base"]["object_sha256"], name
            results[name][f"linewise{linewise}"] = arms

    # All inline whole-cache users in the pinned library. The enabled flags are
    # the actual new Make rules, not manually reconstructed include overrides.
    for relative in sorted(CALLERS):
        name = Path(relative).stem
        flags, source, _ = command_for(name, ["KOS_CACHE_P2=1"], kos_unit=True)
        old_flags = [x for x in flags if not x.startswith(("-DKOS_CACHE_P2=", "-I" + str(overlay)))]
        at = old_flags.index("-include")
        assert old_flags[at + 1] == str(prepared / "require_p2.h")
        old_flags[at:at + 2] = []
        arms = {}
        for arm, selected in (("base", old_flags),
                              ("absent", old_flags + ["-I" + str(overlay)]),
                              ("zero", old_flags + ["-I" + str(overlay), "-DKOS_CACHE_P2=0"]),
                              ("on", flags)):
            arms[arm] = build("kos-" + name + "-" + arm, selected, source)
            if arm in ("absent", "zero"):
                assert arms[arm]["preprocessed_sha256"] == arms["base"]["preprocessed_sha256"], (name, arm)
                assert arms[arm]["object_sha256"] == arms["base"]["object_sha256"], (name, arm)
        assert arms["on"]["helper_reference"], name
        trace = (output / ("kos-" + name + "-on-compile.stderr")).read_text()
        assert str(overlay / "arch/cache.h") in trace
        assert str(kos / "kernel/arch/dreamcast/include/arch/cache.h") not in trace
        (prepared / (name + ".o")).write_bytes(Path(arms["on"]["object"]).read_bytes())
        results["kos-" + name] = arms

    helper = prepared / "tree/kernel/arch/dreamcast/kernel/cache_p2.S"
    run.run([prefix + "gcc", "-m4-single", "-ml", "-DKOS_CACHE_P2=1", "-c", helper,
             "-o", prepared / "cache_p2.o"], "helper")
    run.run([prefix + "objdump", "-dr", prepared / "cache_p2.o"], "helper-disassembly")
    check(prefix, prepared)
    # Demonstrate normal-before-archive symbol precedence with every matching
    # original object present. A full libkallisti/release image is not available.
    archive = output / "original-cache-callers.a"
    run.run([prefix + "ar", "rcs", archive,
             *[output / ("kos-" + Path(x).stem + "-base.o") for x in sorted(CALLERS)]], "archive")
    merged = output / "override-check.o"
    run.run([prefix + "ld", "-EL", "-r", "-Map=" + str(output / "override.map"), "-o", merged,
             *[prepared / (Path(x).stem + ".o") for x in sorted(CALLERS)],
             prepared / "cache_p2.o", archive], "override-link")
    override_map = (output / "override.map").read_text()
    assert not any("original-cache-callers.a(" in line for line in override_map.splitlines())
    merged_symbols = run.run([prefix + "nm", merged], "override-symbols").decode()
    assert " U _arch_dcache_wback_all_p2" not in merged_symbols
    assert " T _arch_dcache_wback_all_p2" in merged_symbols
    report = dict(status="PASS", scope=__doc__, base=subprocess.check_output(
        ["git", "rev-parse", a.base], cwd=ROOT, text=True).strip(), preparation=preparation,
        profile=profile, results=results, helper_object_sha256=sha(prepared / "cache_p2.o"),
        override_link_sha256=sha(merged), limitations=["No full libkallisti archive or release image linked",
        "No game assets, Flycast or physical Dreamcast execution", "Debug records omitted for raw-object identity"])
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", translation_units=len(results), output=str(output))))


if __name__ == "__main__":
    main()
