#!/usr/bin/env python3
"""Compare the actual atari.cpp line consumer with its current gather/reference arm.

The host fixture supplies synthetic SAT blocks and the platform line assembly's
documented leaf-list result. It extracts the production overlap, walk wrappers,
hitCheck2, recursive walker and polygon consumer without rewriting their bodies.
"""

from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "src/game/atari.cpp"
FIXTURE = Path(__file__).with_name("line_resume29_fixture.cpp")


def between(text: str, first: str, last: str) -> str:
    start = text.index(first)
    return text[start:text.index(last, start)]


def production_source(text: str, candidate: bool) -> str:
    sections = [
        between(text, "int cSatBlock::lineOverlap(", "// XZ segment a-b"),
        between(text, "#if defined(RE4DC_LINE_WALK) && RE4DC_LINE_WALK\n// GAME_LINE_WALK", "// Segment a-b against every active piece"),
        between(text, "int cSatMgr::hitCheck2(", "// Line test through the block chain"),
        between(text, "int blkPolyLineCk(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn)\n{", "#if defined(RE4DC_LINE_LEAF) && RE4DC_LINE_LEAF\n// GAME_LINE_LEAF"),
        between(text, "int blkPolyLineCkCore(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn)\n{", "// Releases a piece"),
    ]
    # The target's 32-bit layout asserts cannot hold in a 64-bit host fixture.
    sections[1] = re.sub(r"static_assert\(.*?;\n", "", sections[1], flags=re.S)
    # `u32` is pointer-width in the host shim; the source's bit helper copies
    # only four bytes and therefore needs fixed-width local storage here.
    sections[1] = sections[1].replace("    u32 x;\n    u32 y;\n    __builtin_memcpy", "    uint32_t x;\n    uint32_t y;\n    __builtin_memcpy")
    # Count calls without changing any source operand, branch, or side effect.
    sections[0] = sections[0].replace("{\n", "{\n    ++overlapCalls;\n", 1)
    if candidate:
        assert "lineResume29Run" in sections[1]
        assert "lineResume29Next" in sections[2]
    assert "blkPolyLineCkCore" in sections[4]
    return "\n".join(sections)


def off_preprocessed(tmp: Path, source: str, piece: int, define_zero: bool) -> bytes:
    (tmp / "line_resume29_production.inc").write_text(source)
    cmd = ["g++", "-std=gnu++17", "-E", "-P", "-ffp-contract=off",
           "-DRE4DC_LINE_WALK=2", "-DRE4DC_LINE_WALK_PF=2",
           f"-DRE4DC_LINE_PIECE={piece}", f"-DRE4DC_LINE_YROW={2 if piece else 0}"]
    if define_zero:
        cmd.append("-DRE4DC_LINE_RESUME=0")
    cmd += ["-I", str(ROOT / "src/game"), "-I", str(tmp), str(FIXTURE)]
    return subprocess.check_output(cmd, cwd=ROOT)


def off_object(tmp: Path, source: str, piece: int, define_zero: bool) -> bytes:
    (tmp / "line_resume29_production.inc").write_text(source)
    out = tmp / "off.o"
    cmd = ["g++", "-std=gnu++17", "-O2", "-ffp-contract=off", "-fno-fast-math",
           "-DRE4DC_LINE_WALK=2", "-DRE4DC_LINE_WALK_PF=2",
           f"-DRE4DC_LINE_PIECE={piece}", f"-DRE4DC_LINE_YROW={2 if piece else 0}"]
    if define_zero:
        cmd.append("-DRE4DC_LINE_RESUME=0")
    cmd += ["-I", str(ROOT / "src/game"), "-I", str(tmp), "-c", str(FIXTURE), "-o", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return out.read_bytes()


def run_arm(tmp: Path, mode: str, piece: int, sanitize: bool, check: bool) -> str:
    out = tmp / f"{mode}-{piece}-{'check' if check else 'product'}{'-san' if sanitize else ''}"
    flags = ["-std=gnu++17", "-O1" if sanitize else "-O2", "-ffp-contract=off", "-fno-fast-math", "-Wno-unused-function"]
    if sanitize:
        flags += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    cmd = ["g++", *flags, f"-DRE4DC_LINE_WALK={2 if check else 1}",
           f"-DRE4DC_LINE_WALK_PF={2 if check else 1}",
           f"-DRE4DC_LINE_PIECE={piece}", f"-DRE4DC_LINE_YROW={piece}",
           f"-DRE4DC_LINE_RESUME={1 if mode == 'resume' else 0}",
           "-I", str(ROOT / "src/game"), "-I", str(tmp), str(FIXTURE), "-o", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    env = os.environ.copy()
    if sanitize:
        # This managed executor's ptrace layer prevents LeakSanitizer's /proc
        # thread walk; address and undefined-behavior instrumentation still run.
        env["ASAN_OPTIONS"] = "detect_leaks=0"
    result = subprocess.run([str(out)], text=True, capture_output=True, env=env)
    if result.returncode:
        raise AssertionError(f"{out.name} rc={result.returncode}\n{result.stderr}")
    return result.stdout


def make_flags(tmp: Path) -> None:
    kos = tmp / "kos-stub"
    kos.mkdir()
    (kos / "Makefile.rules").write_text("")
    game = ROOT / "port/dreamcast/game"

    def command(resume=None, walk="1"):
        args = ["make", "-f", "Makefile", "-n", f"KOS_BASE={kos}",
                f"GAME_LINE_WALK={walk}"]
        if resume is not None:
            args.append(f"GAME_LINE_RESUME={resume}")
        args.append("obj/src/game/atari.o")
        result = subprocess.run(args, cwd=game, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        commands = [line for line in result.stdout.splitlines()
                    if line.startswith("kos-c++") and "src/game/atari.cpp" in line]
        return result.returncode, commands, result.stdout

    absent, zero, one, two = (command(v, w) for v, w in
                              ((None, "1"), ("0", "1"), ("1", "1"), ("1", "2")))
    assert absent[0] == zero[0] == one[0] == two[0] == 0
    assert absent[1] == zero[1] and len(one[1]) == len(two[1]) == 1
    assert "RE4DC_LINE_RESUME" not in absent[1][0]
    assert one[1][0].count("-DRE4DC_LINE_RESUME=1") == 1
    assert two[1][0].count("-DRE4DC_LINE_RESUME=1") == 1
    for value in ("", "00", "2", "0 1", "%", "x1"):
        result = command(value)
        assert result[0] != 0 and "GAME_LINE_RESUME must be exactly 0 or 1" in result[2], value
    for value in ("", "0", "3", "1 2", "%"):
        result = command("1", value)
        assert result[0] != 0 and "GAME_LINE_RESUME=1 needs GAME_LINE_WALK exactly 1 or 2" in result[2], value
    print("actual Make line control absent/zero identity, ON WALK1/2, literal invalid refusals pass")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="line-resume29-") as td:
        tmp = Path(td)
        make_flags(tmp)
        candidate = production_source(SOURCE.read_text(), True)
        base_text = subprocess.check_output(["git", "show", "e693945933cf088a13782e756fc356008cdba4b8:src/game/atari.cpp"], cwd=ROOT, text=True)
        baseline = production_source(base_text, False)
        for piece in (0, 2):
            original_absent = off_preprocessed(tmp, baseline, piece, False)
            current_absent = off_preprocessed(tmp, candidate, piece, False)
            current_zero = off_preprocessed(tmp, candidate, piece, True)
            if original_absent != current_absent or current_absent != current_zero:
                raise AssertionError(f"piece={piece}: original/absent/zero preprocessed consumer differs")
            print(f"piece={piece}: original/absent/zero preprocessed consumer identical")
            original_obj = off_object(tmp, baseline, piece, False)
            absent_obj = off_object(tmp, candidate, piece, False)
            zero_obj = off_object(tmp, candidate, piece, True)
            if original_obj != absent_obj or absent_obj != zero_obj:
                raise AssertionError(f"piece={piece}: original/absent/zero host object differs")
            print(f"piece={piece}: original/absent/zero host object identical ({len(original_obj)} bytes)")
            (tmp / "line_resume29_production.inc").write_text(candidate)
            for check in (False, True):
                enabled_piece = 0 if piece == 0 else 2 if check else 1
                for sanitize in (False, True):
                    reference = run_arm(tmp, "reference", enabled_piece, sanitize, check)
                    resumed = run_arm(tmp, "resume", enabled_piece, sanitize, check)
                    if reference != resumed:
                        a = reference.splitlines()
                        b = resumed.splitlines()
                        for i, (left, right) in enumerate(zip(a, b)):
                            if left != right:
                                raise AssertionError(f"piece={enabled_piece} check={check} sanitizer={sanitize} case={i}\nreference: {left}\nresume:    {right}")
                        raise AssertionError(f"output length differs: {len(a)} vs {len(b)}")
                    print(f"walk={2 if check else 1} piece/yrow={enabled_piece} pf={2 if check else 1} sanitizer={int(sanitize)}: {len(reference.splitlines())} consumer cases match")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, subprocess.CalledProcessError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
