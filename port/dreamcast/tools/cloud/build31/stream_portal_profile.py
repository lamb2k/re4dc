#!/usr/bin/env python3
"""Source-only release-chain inputs for the Build31 streamed portal Make gates.

The production rP chain is R21, route play flags, Test 15's inherited recipe,
rr/recipe.conf CH2, then the Build31 validation options. Paths to private data
are passed as inert Make values; this reader does not open them or build an ELF.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[5]
DC = ROOT / "port/dreamcast"
PROFILE = Path(__file__).with_name("portal_completion_profiles.json")
ASSIGNMENT = re.compile(r"[A-Z][A-Z0-9_]*=[^\s$`]+\Z")


def words(value):
    result = shlex.split(value)
    assert all(ASSIGNMENT.fullmatch(word) for word in result), result
    return result


def release_chain(output):
    """Return ordered make assignments from the actual rP scripts and recipe."""
    build = (DC / "tools/d367/build-r21.sh").read_text()
    r21 = build.split("\nR21=(\n", 1)[1].split("\n)\n", 1)[0]
    paths = {"$ASSETS": DC / "game/public-assets", "$ROOT": ROOT,
             "$OBJDIR": output / "obj", "$OUT": output}
    for variable, path in paths.items():
        r21 = r21.replace(variable, str(path))
    base = words(r21)

    route = (DC / "tools/d367/route/route-build.sh").read_text()
    play = re.findall(r'^PLAY="([^"\n]+)"$', route, re.MULTILINE)
    assert len(play) == 1
    route_flags = words(play[0]) + words("PACE_MODE=fast DBG_WARP=1 PC_SAMPLER=1")

    test15 = (DC / "tools/d367/test15/t15-build.sh").read_text()
    # Evaluate only the assignment prelude used by ch2-build.sh; stop before
    # its build function and arm loop. The public script is the source of the
    # inherited T13/T14/T15 and route F/LOOK/BASE/PL settings.
    prelude = test15.split("\nb() {", 1)[0]
    assert 'T15REC="' in prelude and 'PL="' in prelude
    for line in prelude.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line in ("set -u", "export SOURCE_DATE_EPOCH=1760000000"):
            continue
        assert re.fullmatch(r'[A-Z][A-Z0-9_]*=(?:"[^"`]*"|\$\{[^`]*\})', line), line
        assert "$(" not in line and ";" not in line, line
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "T": str(ROOT), "K": str(output / "unused-logs")}
    command = prelude + '\nprintf "%s\\0" "$F" "$LOOK" "$BASE" "$T13" "$T14" "$T15REC" "$PL"\n'
    read = subprocess.run(["bash", "-c", command], env=env, capture_output=True)
    assert read.returncode == 0, read.stderr.decode()
    values = read.stdout.decode().split("\0")
    assert len(values) == 8 and not values[-1], values
    f, look, inherited, t13, t14, t15, pl = (words(value) for value in values[:-1])

    recipe = (DC / "tools/d367/rr/recipe.conf").read_text()
    ch2 = None
    for line in recipe.splitlines():
        if not line.startswith("CH2="):
            continue
        match = re.fullmatch(r'CH2="([^"\n]*)"\s*(?:#.*)?', line)
        assert match, ("unexpected CH2 recipe syntax", line)
        value = match.group(1)
        if value.startswith("$CH2 "):
            assert ch2 is not None
            ch2.extend(words(value[len("$CH2 "):]))
        else:
            assert ch2 is None, "CH2 reset in release recipe"
            ch2 = words(value)
    assert ch2, "missing CH2 release recipe"
    return [*base, *route_flags, *f, *look, *inherited, *t13, *t14,
            *t15, *ch2, "IMAGE_PAD_BYTES=0", *pl]


def candidate(output, overrides=()):
    profile = json.loads(PROFILE.read_text())
    options = words(" ".join(profile["on_options"]))
    return [*release_chain(output), *options, *words(" ".join(overrides))]


def source_only_paths(output):
    """Stage parse-only inputs while preserving every release feature knob.

    These empty files satisfy Make's existence probes only. No source TU is
    compiled against them, so this is never a private-data or target build.
    """
    files = {"ch22/ps2_enemy_ch22_data.inc", "ch23/ps2_enemy_ch23_data.inc",
             "stump/ganado_ps2_stump_runtime.h",
             "sh4zam/include/sh4zam/shz_xmtrx.h",
             "sh4zam/source/sh4/shz_xmtrx_skin_sh4.s"}
    for relative in files:
        path = output / "parse-only" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    paths = {"PS2_ENEMY_CH22_DIR": "ch22", "PS2_ENEMY_CH23_DIR": "ch23",
             "ACTOR_GANADO_PS2_STUMP_DIR": "stump", "SH4ZAM_DIR": "sh4zam"}
    path_overrides = [f"{name}={output / 'parse-only' / relative}"
                      for name, relative in paths.items()]
    return path_overrides


def source_only_candidate(output, overrides=()):
    return candidate(output, [*source_only_paths(output), "SCENERY_STREAM=1",
                              "WORLD_PORTAL_STREAM31=1", *overrides])


def resolved(assignments):
    result = {}
    for assignment in assignments:
        key, value = assignment.split("=", 1)
        result[key] = value
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="path used only for OBJDIR/TARGET values")
    parser.add_argument("--mode", choices=("control", "zero", "on"), default="on")
    parser.add_argument("--override", action="append", default=[],
                        help="final NAME=VALUE assignment, repeatable")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.mode == "on":
        chain = source_only_candidate(output, args.override)
    else:
        zero = ["WORLD_PORTAL_STREAM31=0"] if args.mode == "zero" else []
        chain = candidate(output, [*source_only_paths(output), *zero, *args.override])
    inputs = [DC / "tools/d367/build-r21.sh", DC / "tools/d367/route/route-build.sh",
              DC / "tools/d367/test15/t15-build.sh", DC / "tools/d367/rr/recipe.conf",
              PROFILE]
    print(json.dumps({"mode": args.mode, "chain": chain, "resolved": resolved(chain),
                      "scope": "parse-only files; primary Make and source-guard dry run",
                      "input_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in inputs}},
                     indent=2))
