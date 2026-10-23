#!/usr/bin/env python3
"""Exercise the real cone build rules without building the game or using assets."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
GAME = DC / "game"
ROOT = DC.parents[1]


def run(output, include, definitions, target="report"):
    fixture = output / ("make-%d.mk" % run.number)
    run.number += 1
    fixture.write_text("""OBJDIR := cone-test-objects
TARGET := cone-test.elf
PLATFORM_OBJS := original-object.o
KOS_CFLAGS := -m4-single -ml -O1 -ffast-math -ffp-contract=fast
PLATFORM_CPPFLAGS := -DFIXTURE=1 -ffast-math -O3
.DEFAULT_GOAL := report
include %s
.PHONY: report
report:
\t@echo OBJECTS=$(PLATFORM_OBJS)
cone-test.elf:
\t@echo LINK $^
cone-test-objects/platform/native_static.o cone-test-objects/platform/native_actor_fast.o cone-test-objects/platform/native_ui.o:
\t@echo FLAGS=$(PLATFORM_CPPFLAGS)
cone-test-objects/ui_bridge.o:
\t@echo FLAGS=$(GAME_CPPFLAGS)
""" % include)
    command = ["make", "--no-print-directory", "-n", "-f", str(fixture), target]
    command.extend("%s=%s" % pair for pair in sorted(definitions.items()))
    result = subprocess.run(command, cwd=GAME, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    return dict(command=command, status=result.returncode, output=result.stdout)


run.number = 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", default="dd8981e8de6dadb94997795867c85e8ede9a876f")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    baseline = output / "baseline-backface.mk"
    baseline.write_bytes(subprocess.check_output(
        ["git", "show", args.baseline + ":port/dreamcast/game/backface.mk"], cwd=ROOT))
    current = GAME / "backface.mk"
    rows = []
    for cpu in (0, 1, 2):
        for actor, scenery in ((0, 0), (1, 0), (0, 1)):
            definitions = dict(CPU_BACKFACE=cpu, GAME_SH4ZAM=1,
                               ACTOR_BACKFACE_CONE=actor, SCENERY_CONE=scenery,
                               BACKFACE_CONE_FRONT=0)
            before = run(output, baseline, definitions)
            after = run(output, current, definitions)
            assert before["status"] == after["status"] == 0, (before, after)
            assert before["output"] == after["output"], (before, after)
            assert "backface_certificate" not in after["output"]
            rows.append(dict(kind="off-object-inventory", settings=definitions,
                             baseline=before, candidate=after))
    for value in (-1, 3, "invalid"):
        row = run(output, current, dict(BACKFACE_CONE_FRONT=value))
        assert row["status"] and "must be 0, 1 or 2" in row["output"], row
        rows.append(dict(kind="invalid-knob", result=row))
    for mode in (1, 2):
        for cpu in (0, 1):
            row = run(output, current, dict(BACKFACE_CONE_FRONT=mode,
                      CPU_BACKFACE=cpu, ACTOR_BACKFACE_CONE=1))
            assert row["status"] and "needs CPU_BACKFACE=2" in row["output"], row
            rows.append(dict(kind="invalid-cpu", result=row))
        row = run(output, current, dict(BACKFACE_CONE_FRONT=mode,
                  CPU_BACKFACE=2, GAME_SH4ZAM=1))
        assert row["status"] and "needs ACTOR_BACKFACE_CONE" in row["output"], row
        rows.append(dict(kind="missing-cone", result=row))
        for cone in ("ACTOR_BACKFACE_CONE", "SCENERY_CONE", "BACKFACE_CONE"):
            settings = dict(BACKFACE_CONE_FRONT=mode, CPU_BACKFACE=2,
                            GAME_SH4ZAM=1)
            settings[cone] = 1
            row = run(output, current, settings)
            assert row["status"] == 0, row
            assert row["output"].count("cone-test-objects/platform/backface_certificate.o") == 1, row
            rows.append(dict(kind="on-object-once", result=row))
            compile_row = run(output, current, settings,
                              "cone-test-objects/platform/backface_certificate.o")
            assert compile_row["status"] == 0, compile_row
            line = next(x for x in compile_row["output"].splitlines() if x.startswith("kos-c++ "))
            assert line.rindex("-fno-fast-math") > line.rindex("-ffast-math"), line
            assert line.rindex("-ffp-contract=off") > line.rindex("-ffp-contract=fast"), line
            assert [word for word in line.split() if word.startswith("-O")][-1] == "-O2", line
            rows.append(dict(kind="strict-flags-last", result=compile_row))
    # The hideout fix owns the room selector and scene-open update. Both knobs
    # must coexist without leaking the front helper definition into UI code.
    for mode in (0, 1, 2):
        for room_list in (None, "0x10d,0x10c"):
            settings = dict(CPU_BACKFACE=2, GAME_SH4ZAM=1,
                            ACTOR_BACKFACE_CONE=1, BACKFACE_CONE_FRONT=mode,
                            BACKFACE_ROOMS=1)
            if room_list is not None:
                settings["BACKFACE_ROOM_LIST"] = room_list
            for name in ("platform/native_static.o", "platform/native_actor_fast.o",
                         "platform/native_ui.o", "ui_bridge.o"):
                row = run(output, current, settings, "cone-test-objects/" + name)
                assert row["status"] == 0, row
                flags = next(line for line in row["output"].splitlines() if line.startswith("echo FLAGS="))
                assert flags.count("-DRE4DC_BACKFACE_ROOMS=1") == 1, row
                if name.startswith("platform/"):
                    assert "-DRE4DC_BACKFACE_ROOM_LIST=" + (room_list or "0x10d") in flags, row
                expected = mode and name in ("platform/native_static.o", "platform/native_actor_fast.o")
                assert ("-DRE4DC_BACKFACE_CONE_FRONT=" in flags) == bool(expected), row
                if mode == 0:
                    before = run(output, baseline, settings, "cone-test-objects/" + name)
                    assert before["status"] == 0 and before["output"] == row["output"], (before, row)
                rows.append(dict(kind="room-selector-coexistence", settings=settings, target=name, result=row))
    for cpu in (0, 1):
        row = run(output, current, dict(CPU_BACKFACE=cpu, BACKFACE_ROOMS=1))
        assert row["status"] and "BACKFACE_ROOMS=1 needs CPU_BACKFACE=2" in row["output"], row
        rows.append(dict(kind="room-selector-invalid-cpu", result=row))
    for value in (-1, 2, "invalid"):
        row = run(output, current, dict(CPU_BACKFACE=2, GAME_SH4ZAM=1, BACKFACE_ROOMS=value))
        assert row["status"] and "BACKFACE_ROOMS must be 0 or 1" in row["output"], row
        rows.append(dict(kind="room-selector-invalid-knob", result=row))
    for mode in (1, 2):
        settings = dict(CPU_BACKFACE=2, GAME_SH4ZAM=1, ACTOR_BACKFACE_CONE=1,
                        BACKFACE_ROOMS=1, BACKFACE_CONE_FRONT=mode)
        row = run(output, current, settings)
        assert row["status"] == 0 and row["output"].count("cone-test-objects/platform/backface_certificate.o") == 1, row
        rows.append(dict(kind="room-selector-front-object-once", result=row))
        row = run(output, current, settings, "cone-test-objects/platform/backface_certificate.o")
        assert row["status"] == 0, row
        line = next(x for x in row["output"].splitlines() if x.startswith("kos-c++ "))
        assert line.rindex("-fno-fast-math") > line.rindex("-ffast-math"), line
        assert line.rindex("-ffp-contract=off") > line.rindex("-ffp-contract=fast"), line
        assert [word for word in line.split() if word.startswith("-O")][-1] == "-O2", line
        rows.append(dict(kind="room-selector-strict-flags-last", result=row))
    makefile = (GAME / "Makefile").read_text()
    inventory = next(x for x in makefile.splitlines() if x.startswith("PLATFORM_SRCS ="))
    assert "$(filter-out" in inventory and "platform/backface_certificate.cpp" in inventory, inventory
    report = dict(scope=__doc__, baseline=args.baseline, checks=len(rows), cases=rows,
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (current, GAME / "Makefile")},
                  limitation="Make dry-runs and object inventory; executable OFF identity is a separate target gate.")
    (output / "make-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS make matrix: %d controls" % len(rows))


if __name__ == "__main__":
    main()
