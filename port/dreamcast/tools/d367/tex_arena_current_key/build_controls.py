#!/usr/bin/env python3
"""Make-derived native_ui SH-4 identity and enabled-build controls.

The archived integration base, current absent knobs, and explicit zero knobs
must produce identical complete preprocessed output and object bytes. Enabled
arms compile the fix and final-refusal diagnostic separately and together.
This uses public recipe fallbacks and does not link or run a release image.
"""
from __future__ import annotations

import argparse
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
DC = ROOT / "port/dreamcast"
BASELINE = "db222fc618045fc1da2bb3c7222743f83612ed1b"
KOS_PIN = "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
SDK_PIN = "33fa4850cacb30dd0ad35485ef035526ec4ce782"
KNOBS = ("TEX_ARENA_CURRENT_KEY", "TEX_FINAL_REFUSAL_LOG")
SOURCE = Path("port/dreamcast/game/platform/native_ui.cpp")
spec = importlib.util.spec_from_file_location("texture_fix_public_make", DC / "tools/cloud/build18/build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(value: str, output: Path, tree: Path, sdk: Path) -> str:
    # SDK can live inside the current checkout while both arms share it. The
    # baseline source directory also starts with the profile name; longest,
    # semantically specific prefixes must be replaced first.
    return value.replace(str(sdk), "<SDK>").replace(str(tree), "<SOURCE>").replace(str(output), "<PROFILE>")


def dependencies(path: Path, tree: Path, cwd: Path) -> dict[str, str]:
    body = path.read_text().replace("\\\n", " ").split(":", 1)[1]
    result = {}
    for word in shlex.split(body):
        source = Path(word)
        source = (source if source.is_absolute() else cwd / source).resolve()
        if source.is_file() and source.is_relative_to(tree):
            result[str(source.relative_to(tree))] = sha(source)
    return result


def probe(out: Path, tree: Path, kos: Path, sdk: Path, options: list[str]) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    names = (*KNOBS, "VRAM_ROOM_ARENA", "CORE_PIN", "UI_VRAM", "VRAM_PAGES")
    query = out / "query.mk"
    query.write_text(".PHONY: tex-arena-state\ntex-arena-state:\n\t@:\n" + "\n".join(
        f"$(info TEX_ARENA_STATE {name}=$({name}))" for name in names) + "\n")
    command, _ = profile.make_command(out, tree, kos, sdk, options, "tex-arena-state")
    command[3:3] = ["-f", "Makefile", "-f", str(query)]
    result = subprocess.run(command, cwd=tree / "port/dreamcast/game", capture_output=True, text=True)
    output = result.stdout + result.stderr
    (out / "make.log").write_text(output)
    state = dict(line[len("TEX_ARENA_STATE "):].split("=", 1) for line in output.splitlines()
                 if line.startswith("TEX_ARENA_STATE "))
    return dict(argv=command, returncode=result.returncode, state=state,
                error=output[-3000:] if result.returncode else None)


def run(args: argparse.Namespace) -> dict:
    out = args.output.resolve()
    if out.is_relative_to(ROOT):
        raise ValueError("Choose --output outside the checkout; generated controls are not source artifacts.")
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(out)
    prefix = str(cxx).removesuffix("g++")
    compiler = builder.run([cxx, "--version"], label="compiler").decode().splitlines()[0]
    verbose = subprocess.run([str(cxx), "-v"], capture_output=True, text=True).stderr
    if "15.2.0" not in compiler or "Thread model: kos" not in verbose:
        raise RuntimeError("The retained GCC 15.2.0 KOS toolchain is required.")
    linker = builder.run([prefix + "ld", "--version"], label="linker").decode().splitlines()[0]
    if "2.45.1" not in linker:
        raise RuntimeError("The retained binutils 2.45.1 linker is required.")
    for folder, pin in ((kos, KOS_PIN), (sdk, SDK_PIN)):
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip()
        if actual != pin:
            raise RuntimeError(f"Unexpected dependency revision: {folder}: {actual}; expected {pin}")

    watched = [ROOT / SOURCE, DC / "game/Makefile", Path(__file__),
               DC / "tools/cloud/build18/build_profile.py", DC / "tools/d367/ui_draw_lean/build_profile.py",
               DC / "tools/d367/world_submit_spike/build_profile.py"]
    frozen = {str(path.relative_to(ROOT)): sha(path) for path in watched}
    tree = out / "baseline-tree"
    tree.mkdir()
    archive_bytes = subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
        archive.extractall(tree, filter="data")

    arms = [
        ("baseline", [], None),
        ("absent", [], None),
        ("zero", [f"{knob}=0" for knob in KNOBS], (0, 0)),
        ("fix", [f"{KNOBS[0]}=1", f"{KNOBS[1]}=0"], (1, 0)),
        ("log", [f"{KNOBS[0]}=0", f"{KNOBS[1]}=1"], (0, 1)),
        ("both", [f"{knob}=1" for knob in KNOBS], (1, 1)),
    ]
    artifacts, profiles, flags_by_arm, states, closure = {}, {}, {}, {}, {}
    comparisons = 0
    for name, options, expected in arms:
        source_tree = tree if name == "baseline" else ROOT
        destination = out / name
        flags, receipt, sources = profile.derive(destination, cxx, kos, sdk, options,
                                                 tree=source_tree, units=("native_ui",))
        common = flags["native_ui"]
        flags_by_arm[name], profiles[name] = common, receipt
        if name in ("absent", "zero"):
            reference = [normalized(word, out / "baseline", tree, sdk) for word in flags_by_arm["baseline"]]
            current = [normalized(word, destination, ROOT, sdk) for word in common]
            if current != reference:
                raise AssertionError((name, "Make flags differ from integration base"))
        elif name in ("fix", "log", "both"):
            reference = [normalized(word, out / "absent", ROOT, sdk) for word in flags_by_arm["absent"]]
            additions = [f"-DRE4DC_{knob}=1" for knob, enabled in zip(KNOBS, expected) if enabled]
            current = [normalized(word, destination, ROOT, sdk) for word in common if word not in additions]
            if current != reference or any(common.count(word) != 1 for word in additions):
                raise AssertionError((name, "Make must add only the enabled per-object definitions"))

        source = sources["native_ui"]
        # Also exercise explicitly defined CPP zero, not only omitted Make flags.
        explicit_zero = [f"-DRE4DC_{knob}=0" for knob in KNOBS] if name == "zero" else []
        compile_flags = [*common, *explicit_zero, "-iquote", str(source.parent)]
        artifacts[name] = {}
        for suffix, phase in (("ii", ["-E", "-P"]),
                              ("o", ["-c", "-fstack-usage", "-MMD", "-MF", out / f"{name}.d"])):
            target = out / f"{name}.{suffix}"
            builder.run([*compile_flags, "-x", "c++", "-", *phase, "-o", target],
                        cwd=source.parent, source=source.read_bytes(), label=f"{name}-{suffix}")
            row = dict(bytes=target.stat().st_size, sha256=sha(target))
            if suffix == "o":
                row.update(profile.sections(target), stack_usage=profile.stack_usage(target.with_suffix(".su")))
                closure[name] = dependencies(out / f"{name}.d", source_tree, source.parent)
            artifacts[name][suffix] = row
            if name in ("absent", "zero"):
                if target.read_bytes() != (out / f"baseline.{suffix}").read_bytes():
                    raise AssertionError((name, suffix, "complete TU OFF identity mismatch"))
                comparisons += 1
        states[name] = probe(out / f"{name}-make", source_tree, kos, sdk, options)
        if states[name]["returncode"]:
            raise AssertionError(states[name])
        if name != "baseline":
            values = expected or (0, 0)
            for knob, value in zip(KNOBS, values):
                if states[name]["state"][knob] != str(value):
                    raise AssertionError((name, knob, "unexpected effective value"))
        if states[name]["state"]["VRAM_ROOM_ARENA"] != "1":
            raise AssertionError((name, "the current public recipe must exercise the arena"))
        print("PASS", name, flush=True)

    rejections = []
    for knob in KNOBS:
        for index, value in enumerate(("2", "-1", "", "0 1")):
            state = probe(out / f"reject-{knob}-{index}", ROOT, kos, sdk, [f"{knob}={value}"])
            if state["returncode"] == 0:
                raise AssertionError((knob, value, "invalid Make setting accepted"))
            rejections.append(dict(knob=knob, value=value, **state))
    for index, options in enumerate((
        ["TEX_ARENA_CURRENT_KEY=1", "VRAM_ROOM_ARENA=0"],
        ["TEX_ARENA_CURRENT_KEY=1", "VRAM_PAGES=0"],
        ["TEX_ARENA_CURRENT_KEY=1", "UI_VRAM=0"],
        ["TEX_FINAL_REFUSAL_LOG=1", "VRAM_PAGES=0"],
        ["TEX_FINAL_REFUSAL_LOG=1", "UI_VRAM=0"],
    )):
        state = probe(out / f"reject-prerequisite-{index}", ROOT, kos, sdk, options)
        if state["returncode"] == 0:
            raise AssertionError((options, "missing Make prerequisite accepted"))
        rejections.append(dict(options=options, **state))
    if {str(path.relative_to(ROOT)): sha(path) for path in watched} != frozen:
        raise RuntimeError("Production or gate source changed during compilation; rerun on frozen inputs.")

    deltas = {}
    for name in ("fix", "log", "both"):
        deltas[name] = {field: artifacts[name]["o"][field] - artifacts["baseline"]["o"][field]
                        for field in ("executable_bytes", "allocated_bytes", "zero_fill_bytes")}
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline, source_sha256=frozen,
                  compiler=compiler, compiler_sha256=sha(cxx), linker=linker, kos=KOS_PIN, sdk=SDK_PIN,
                  off_identity_comparisons=comparisons, artifacts=artifacts, deltas=deltas,
                  profile_receipts=profiles, dependency_sha256=closure, make_states=states,
                  make_rejections=rejections,
                  limitations="Complete public-configuration target TU/object controls with debug records omitted. No full game link/image identity, runtime performance, private assets, rendered pixels, or console acceptance.")
    if args.toolchain_receipt:
        report["toolchain_receipt"] = dict(path=str(args.toolchain_receipt.resolve()), sha256=sha(args.toolchain_receipt))
    (out / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_identity_comparisons=comparisons, deltas=deltas,
                          receipt=str(out / "target-controls.json")), indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--toolchain-receipt", type=Path)
    parser.add_argument("--baseline", default=BASELINE)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
