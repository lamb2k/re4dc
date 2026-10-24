#!/usr/bin/env python3
"""Compile current complete r10c TU with Make-derived Test22 public settings.

This is not the photographed Test21 executable or a full linked build. It
checks the new knob's recipe/preprocessed/object identity when disabled,
enabled diagnostics composition, and current SH4 virtual-dispatch lowering.
"""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = "ea969bb241f77291d2ca43d706c9dc2d1226ee76"
spec = importlib.util.spec_from_file_location("dam_public_profile", HERE.parent / "world_submit_spike/build_profile.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


@contextmanager
def source_tree(tree):
    saved = [(m, m.ROOT, m.DC) for m in (profile, profile.release_profile)]
    try:
        for m, _, _ in saved:
            m.ROOT, m.DC = tree, tree / "port/dreamcast"
        yield
    finally:
        for m, root, dc in saved:
            m.ROOT, m.DC = root, dc


def modules(output, receipt, tree):
    # Get the real MODULE_ARGS after Make has parsed all target settings. Run
    # only the public source generator, never compile/link/asset shell recipes.
    printer = output / "audit-print.mk"
    printer.write_text(".PHONY: audit-module-args\naudit-module-args:\n\t@printf '%s\\n' $(MODULE_ARGS)\n")
    old_target = str(output / "obj/platform/native_static.o")
    command = ["audit-module-args" if v == old_target else v for v in receipt["command"]]
    command += ["-f", "Makefile", "-f", str(printer)]
    result = subprocess.run(command, cwd=tree / "port/dreamcast/game", text=True, capture_output=True, check=True)
    lines = result.stdout.splitlines()
    args = [shlex.split(line)[2:] for line in lines if line.startswith("printf ")]
    assert len(args) == 1, result.stdout
    command = [sys.executable, str(tree / "port/dreamcast/game/tools/gen_modules.py"),
               str(tree / "config/G4BE08/modules"), str(tree), str(output / "obj"),
               str(output / "obj/modules.mk"), *args[0]]
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    (output / "modules-generator.log").write_text(result.stdout + result.stderr)
    return dict(command=command, manifest_sha256=profile.sha(output / "obj/modules.mk"),
                scope="Make-derived source manifest only; no overlay built")


def derive(tree, output, compiler, kos, sdk):
    with source_tree(tree):
        _, base = profile.derive(output, compiler, kos, sdk)
        generator = modules(output, base["native_static"], tree)
    return base, generator


def expand(tree, output, compiler, sdk, receipt, options, label, tu="r10c"):
    with source_tree(tree):
        source = dict(receipt["native_static"])
        source["command"] = [*source["command"], *options]
        if tu == "r10c":
            target, path = "mod/st1_2/src/st1/r10c.o", "../../../src/st1/r10c.cpp"
        elif tu == "r10c_census":
            target, path = "src/st1/r10c.o", "../../../src/st1/r10c.cpp"
        else:
            target, path = "src/game/em_set.o", "../../../src/game/em_set.cpp"
        return profile.expand(output, compiler, sdk, output / "kos-overlay", source,
                              label, target, path)


def normalized(flags, tree, out):
    return [v.replace(str(out), "<PROFILE>").replace(str(tree), "<ROOT>") for v in flags]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--baseline", default=BASE)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    tree = out / "baseline-tree"
    tree.mkdir()
    archive = subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(tree, filter="data")
    current_profile, current_modules = derive(ROOT, out / "profile", compiler, kos, sdk)
    old_profile, old_modules = derive(tree, out / "baseline-profile", compiler, kos, sdk)
    path = ROOT / "src/st1/r10c.cpp"
    old_source = (tree / "src/st1/r10c.cpp").read_bytes()
    source = path.read_bytes()
    builder = profile.Build(out)
    records, recipes = {}, {}
    for diag in (0, 1):
        options = ["ISSUE52_ACTOR_DIAG=" + str(diag)]
        base_flags, base_rec = expand(tree, out / "baseline-profile", compiler, sdk, old_profile,
                                      options, "base-diag" + str(diag))
        arms = {}
        for arm, knob in (("absent", None), ("zero", 0), ("on", 1)):
            opts = options + ([] if knob is None else ["R10C_SPAWN_LIVE_GUARD=" + str(knob)])
            flags, rec = expand(ROOT, out / "profile", compiler, sdk, current_profile, opts,
                                arm + "-diag" + str(diag))
            compare = [f for f in flags if f != "-DRE4DC_R10C_SPAWN_LIVE_GUARD=1"]
            assert normalized(compare, ROOT, out / "profile") == normalized(base_flags, tree, out / "baseline-profile")
            assert ("-DRE4DC_R10C_SPAWN_LIVE_GUARD=1" in flags) == (knob == 1)
            assert "-DRE4DC_ROUTE_CH21_FULL=1" in flags
            arms[arm] = flags
            recipes[arm + "-diag" + str(diag)] = rec
        # Compile all sources in one include context: only r10c.cpp/game30.mk
        # change in the runtime patch. No header/body substitution is hidden.
        for arm in ("baseline", "absent", "zero", "on"):
            label = arm + "-diag" + str(diag)
            common = arms["absent" if arm == "baseline" else arm]
            if arm == "zero":
                common = common + ["-DRE4DC_R10C_SPAWN_LIVE_GUARD=0"]
            data = old_source if arm == "baseline" else source
            record = {}
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                target = out / (label + "." + suffix)
                builder.run([*common, "-x", "c++", "-", *phase, "-o", target],
                            cwd=path.parent, source=data, label=label)
                record[suffix] = dict(sha256=profile.sha(target), bytes=target.stat().st_size)
                if suffix == "o":
                    record[suffix].update(profile.sections(target))
                    record[suffix]["stack"] = profile.stack_usage(target.with_suffix(".su"))
            records[label] = record
        for suffix in ("ii", "o"):
            expected = (out / ("baseline-diag%d.%s" % (diag, suffix))).read_bytes()
            for arm in ("absent", "zero"):
                assert (out / ("%s-diag%d.%s" % (arm, diag, suffix))).read_bytes() == expected
    # Check the new room-only define does not bleed into the common factory.
    peer_off, _ = expand(ROOT, out / "profile", compiler, sdk, current_profile, [], "peer-off", "em_set")
    peer_on, _ = expand(ROOT, out / "profile", compiler, sdk, current_profile,
                       ["R10C_SPAWN_LIVE_GUARD=1"], "peer-on", "em_set")
    assert peer_off == peer_on
    census, _ = expand(ROOT, out / "profile", compiler, sdk, current_profile,
                       ["R10C_SPAWN_LIVE_GUARD=1"], "census-on", "r10c_census")
    assert "-DRE4DC_R10C_SPAWN_LIVE_GUARD=1" in census
    # The only enabled use relies on the already-existing NULL recovery path.
    command = [*current_profile["native_static"]["command"], "R10C_SPAWN_LIVE_GUARD=1", "EM_READ_RETRY=0"]
    rejection = subprocess.run(command, cwd=ROOT / "port/dreamcast/game", text=True, capture_output=True)
    assert rejection.returncode and "requires EM_READ_RETRY=1" in rejection.stderr
    (out / "unsupported-profile.log").write_text(rejection.stdout + rejection.stderr)
    command = [*current_profile["native_static"]["command"], "R10C_SPAWN_LIVE_GUARD=2"]
    invalid = subprocess.run(command, cwd=ROOT / "port/dreamcast/game", text=True, capture_output=True)
    assert invalid.returncode and "must be 0 or 1" in invalid.stderr
    # Independent current-header dispatch, not an original Test21 binary.
    probe = '#include "em.h"\nextern "C" void dam_dispatch_probe(cEm* em){em->setNoSuspend(1);}\n'
    target = out / "dispatch-probe.o"
    builder.run([*arms["absent"], "-x", "c++", "-", "-c", "-o", target],
                cwd=path.parent, source=probe.encode(), label="dispatch-probe")
    objdump = compiler.with_name("sh-elf-objdump")
    assembly = subprocess.check_output([str(objdump), "-d", str(target)], text=True)
    (out / "dispatch-probe.s").write_text(assembly)
    assert "mov.l\t@r4,r" in assembly and "@(24,r" in assembly, assembly
    receipt = dict(status="PASS", scope=__doc__, baseline=args.baseline,
                   compiler_version=subprocess.check_output([str(compiler), "--version"], text=True).splitlines()[0],
                   source_sha256=hashlib.sha256(source).hexdigest(), old_source_sha256=hashlib.sha256(old_source).hexdigest(),
                   modules=dict(current=current_modules, baseline=old_modules),
                   recipes=recipes, builds=records, off_full_tu_preprocessed_and_objects_identical=True,
                   diagnostics_variants=[0, 1], new_define_room_only=True, retry_zero_rejected=True,
                   census_object_define=True, invalid_knob_rejected=True,
                   dispatch_probe=dict(sha256=profile.sha(target), disassembly=assembly,
                                       provenance="Fresh current-source SH4 object; not public Test21 ELF/overlay"))
    (out / "target-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_identity=True, diagnostics_variants=[0, 1],
                         room_only=True, retry_zero_rejected=True)))


if __name__ == "__main__":
    main()
