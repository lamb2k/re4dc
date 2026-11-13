#!/usr/bin/env python3
"""Bounded host gates for WORLD_EMPTY_PREP01; never claims target/console acceptance.

The fixture extracts the complete modified production emit_pick, chunk_emit,
chunk_restart and geometry-borrow members. Resource APIs and the SH-4/PVR
boundary are spies. Source identity checks preprocess the whole translation
unit with includes elided equally in both arms, retaining token line locations.
A target object/link identity gate is still required before integration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

BASE_SHA = "65fe3d1f96ab269c136053725850101be9d3e692"
REL = "port/dreamcast/game/platform/native_static.cpp"
DEPS = ("SCENERY_CHUNK", "MESH_FASTPATH", "MESH_DIRECT", "PS2_WORLD_MESH")
ROOT = Path(__file__).resolve().parents[4]
BASELINE_FILE = None
OUTPUT_DIR = None


def run(argv, *, data=None, okay=True, cwd=None):
    result = subprocess.run(argv, input=data, text=True, capture_output=True, cwd=cwd)
    if okay and result.returncode:
        raise AssertionError(f"command failed ({result.returncode}): {argv}\n{result.stdout[-1500:]}\n{result.stderr}")
    return result


def function(source, marker, *, after=0):
    """Extract a full member, respecting comments and quoted braces."""
    start = source.index(marker, after)
    at = source.index("{", start)
    depth, state, quote = 0, "code", ""
    i = at
    while i < len(source):
        c, following = source[i], source[i:i+2]
        if state == "line":
            if c == "\n":
                state = "code"
        elif state == "block":
            if following == "*/":
                state = "code"
                i += 1
        elif state == "quote":
            if c == "\\":
                i += 1
            elif c == quote:
                state = "code"
        elif following == "//":
            state = "line"
            i += 1
        elif following == "/*":
            state = "block"
            i += 1
        elif c in "\"'":
            state, quote = "quote", c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if not depth:
                return start, source[start:i+1]
        i += 1
    raise AssertionError(f"unterminated member {marker}")


def logical_line(source, offset):
    line = 1
    for text in source[:offset].splitlines(keepends=True):
        marker = re.match(r"\s*#\s*line\s+(\d+)", text)
        line = int(marker[1]) if marker else line + text.count("\n")
    return line


def located(source, offset, body):
    return (f'#line {logical_line(source, offset)} "platform/native_static.cpp"\n'
            + body + '\n#line 1 "world_empty_prep01_host.cpp"\n')


def control(source):
    start = source.find("// WORLD_EMPTY_PREP01 keeps binding/publication")
    if start < 0:
        return ""
    return source[start:source.index("#line 1\n", start)]


def fixture_source(source):
    template = (Path(__file__).parent / "fixtures/world_empty_prep01_host.cpp").read_text()
    emit_at, emit = function(source, "    int emit_pick(const Pick& pk){")
    restart_at, restart = function(source, "    [[gnu::always_inline]] void chunk_restart(){")
    chunk_at = source.index("#if RE4DC_SCENERY_EMIT_PREFETCH\n    __attribute__((noinline)) int chunk_emit", restart_at)
    chunk_end = chunk_at + re.search(r"\n#endif\n(?:#line 4447\n)?    int run\(\)\{", source[chunk_at:]).start()
    chunk = source[chunk_at:chunk_end]
    gather_at, gather = function(source, "    bool borrow_gather(){")
    borrow_at, borrow = function(source, "    bool borrow(){", after=source.index("struct MeshDraw"))
    gather = gather.replace("bool borrow_gather()", "bool borrow_gather_source()", 1)
    borrow = borrow.replace("bool borrow()", "bool borrow_source()", 1)
    end_at = source.index("            e.end_direct();\n#if RE4DC_WORLD_MUTATION31")
    end_end = source.index("\n#if RE4DC_WORLD_PAGES31", end_at)
    replacements = {
        "@WORLD_CONTROL_PRELUDE@": '#line 1 "platform/native_static.cpp"\n' + control(source)
            + '#line 1 "world_empty_prep01_host.cpp"\n',
        "@WORLD_GEOMETRY_BORROW@": located(source, gather_at, gather) + located(source, borrow_at, borrow),
        "@WORLD_CONSUMER_MEMBERS@": located(source, emit_at, emit) + located(source, restart_at, restart)
            + located(source, chunk_at, chunk),
        "@WORLD_AFTER_END@": located(source, end_at, source[end_at:end_end]),
    }
    for key, value in replacements.items():
        assert template.count(key) == 1
        template = template.replace(key, value)
    return template


def tokenize(text):
    return re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|\d+(?:\.\d*)?|\S', text)


def preprocess(source, flags, *, locations=False):
    # Preserve every physical line and original directive except unavailable
    # includes. Same treatment in both arms; this is a source gate, not a TU build.
    text = re.sub(r"(?m)^[ \t]*#[ \t]*include[^\n]*", "", source)
    text = '#line 1 "platform/native_static.cpp"\n' + text
    args = ["g++", "-std=c++17", "-E", "-x", "c++", "-"]
    args.extend(f"-D{k}={v}" for k, v in flags.items())
    result = run(args, data=text).stdout
    if not locations:
        return tokenize(re.sub(r"(?m)^#.*$", "", result))
    out, line, file = [], 1, ""
    for text in result.splitlines():
        marker = re.match(r'#\s+(\d+)\s+"([^"]+)"', text)
        if marker:
            line, file = int(marker[1]), marker[2]
        else:
            tokens = tokenize(text)
            if tokens:
                out.append((file, line, tokens))
            line += 1
    return out


class WorldEmptyPrep01(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for executable in ("g++", "make"):
            if not shutil.which(executable):
                raise RuntimeError(f"{executable} is required; no fallback verdict")
        cls.source = (ROOT / REL).read_text()
        if BASELINE_FILE:
            cls.baseline = Path(BASELINE_FILE).read_text()
        else:
            cls.baseline = run(["git", "-C", str(ROOT), "show", f"{BASE_SHA}:{REL}"]).stdout
        cls.temp = tempfile.TemporaryDirectory(prefix="re4dc-world-empty01-")
        cls.work = Path(cls.temp.name)
        cls.include = ROOT / "port/dreamcast/game/platform/include"
        cls.arms = {}
        cls.objects = {}
        for source_name, source in (("baseline", cls.baseline), ("candidate", cls.source)):
            variants = [(0, 1, 1)] if source_name == "baseline" else [
                (0, 1, 1), (1, 1, 1), (0, 0, 1), (1, 0, 1), (0, 1, 0), (1, 1, 0)]
            # Same source pathname in every build: no file-name identity noise.
            cpp = cls.work / "consumer.cpp"
            cpp.write_text(fixture_source(source))
            for enabled, mutation, stream in variants:
                tag = f"{source_name}-k{enabled}-m{mutation}-s{stream}"
                obj, exe = cls.work / (tag + ".o"), cls.work / tag
                flags = [f"-DRE4DC_WORLD_EMPTY_PREP01={enabled}",
                         f"-DRE4DC_WORLD_MUTATION31={mutation}", f"-DRE4DC_SCENERY_STREAM={stream}"]
                run(["g++", "-std=c++17", "-O2", "-g0", "-Wall", "-Wextra",
                     "-Wno-unused-variable", "-Wno-unused-but-set-variable", *flags,
                     "-I", str(cls.include), "-c", str(cpp), "-o", str(obj)])
                run(["g++", str(obj), "-o", str(exe)])
                result = run([str(exe)])
                cls.arms[(source_name, enabled, mutation, stream)] = {
                    row["case"]: row for row in map(json.loads, result.stdout.splitlines())}
                cls.objects[tag] = obj.read_bytes()
        if OUTPUT_DIR:
            Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            (Path(OUTPUT_DIR) / "consumer-results.json").write_text(json.dumps({
                "/".join(map(str, key)): value for key, value in cls.arms.items()}, indent=2) + "\n")
            (Path(OUTPUT_DIR) / "provenance.json").write_text(json.dumps({
                "base_sha": BASE_SHA,
                "baseline_sha256": hashlib.sha256(cls.baseline.encode()).hexdigest(),
                "candidate_sha256": hashlib.sha256(cls.source.encode()).hexdigest(),
                "host_object_sha256": {key: hashlib.sha256(value).hexdigest() for key, value in cls.objects.items()},
                "scope": "complete extracted consumer; source includes elided for full-file token/line gate",
                "not_proven": ["SH-4 object/ELF identity", "target performance", "private incidence", "runtime/console acceptance"]
            }, indent=2) + "\n")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def pair(self, mutation=1, stream=1):
        return (self.arms[("candidate", 0, mutation, stream)],
                self.arms[("candidate", 1, mutation, stream)])

    def test_disabled_complete_consumer_object_and_behavior_identity(self):
        self.assertEqual(self.objects["baseline-k0-m1-s1"], self.objects["candidate-k0-m1-s1"])
        self.assertEqual(self.arms[("baseline", 0, 1, 1)], self.arms[("candidate", 0, 1, 1)])

    def test_disabled_whole_source_tokens_and_logical_lines(self):
        core = {"RE4DC_"+name: 1 for name in DEPS}
        core.update(RE4DC_NATIVE_STATIC=1, RE4DC_NATIVE_MESH=1, RE4DC_PS2_WORLD_DRAW=1,
                    RE4DC_PS2_WORLD_LEAN=23, RE4DC_SCENERY_SELECT_ONLY=1,
                    RE4DC_SCENERY_REPLAY_LEAN=1, RE4DC_SCENERY_SUBMIT_BATCH=1,
                    RE4DC_SCENERY_STREAM=1, RE4DC_MESH_PRIME_LAZY=1,
                    RE4DC_MESH_LOD=1, RE4DC_MESH_VP_SCHED=1,
                    RE4DC_MESH_STRIP_LEAN=1, RE4DC_HW_LEAN=1, __sh__=1)
        prepared = dict(core, RE4DC_WORLD_PREPARED09=1, RE4DC_WORLD_PART_PLAN29=1,
                        RE4DC_WORLD_PAGES31=1, RE4DC_WORLD_MUTATION31=1,
                        RE4DC_MOVIE_WORLD_ARENA=1, RE4DC_STATIC_OBJ_LIFETIME05=1,
                        RE4DC_WORLD_CENSUS24=1, RE4DC_SCN_CENSUS=1)
        no_chunk = dict(core, RE4DC_SCENERY_CHUNK=0, RE4DC_SCENERY_SELECT_ONLY=0,
                        RE4DC_SCENERY_REPLAY_LEAN=0, RE4DC_SCENERY_SUBMIT_BATCH=0,
                        RE4DC_SCENERY_STREAM=0)
        for profile in ({}, no_chunk, core, prepared):
            expected_tokens = preprocess(self.baseline, profile)
            expected_locations = preprocess(self.baseline, profile, locations=True)
            for zero in ({}, {"RE4DC_WORLD_EMPTY_PREP01": 0}):
                with self.subTest(profile=profile, explicit_zero=bool(zero)):
                    flags = dict(profile, **zero)
                    self.assertEqual(expected_tokens, preprocess(self.source, flags))
                    self.assertEqual(expected_locations, preprocess(self.source, flags, locations=True))

    def test_new_source_and_make_controls(self):
        guard = control(self.source)
        self.assertTrue(guard)
        for value in (0, 1):
            result = run(["g++", "-E", "-x", "c++", "-", f"-DRE4DC_WORLD_EMPTY_PREP01={value}",
                          *[f"-DRE4DC_{d}=1" for d in DEPS]], data=guard)
            self.assertEqual(result.returncode, 0)
        for value in (-1, 2):
            result = run(["g++", "-E", "-x", "c++", "-", f"-DRE4DC_WORLD_EMPTY_PREP01={value}",
                          *[f"-DRE4DC_{d}=1" for d in DEPS]], data=guard, okay=False)
            self.assertNotEqual(result.returncode, 0)
        for missing in DEPS:
            result = run(["g++", "-E", "-x", "c++", "-", "-DRE4DC_WORLD_EMPTY_PREP01=1",
                          *[f"-DRE4DC_{d}={int(d != missing)}" for d in DEPS]], data=guard, okay=False)
            self.assertNotEqual(result.returncode, 0)
        makefile = self.work / "control.mk"
        mk = ROOT / "port/dreamcast/game/work_removal_world01.mk"
        makefile.write_text("OBJDIR := obj\nPLATFORM_CPPFLAGS := KEEP\nGAME_CPPFLAGS := GAME\n"
            f"include {mk}\n"
            "obj/platform/native_static.o other:\n"
            "\t@printf '%s|%s\\n' '$(PLATFORM_CPPFLAGS)' '$(GAME_CPPFLAGS)'\n")
        valid = [f"{d}=1" for d in DEPS]
        for zero in ([], ["WORLD_EMPTY_PREP01=0"]):
            result = run(["make", "--no-print-directory", "-f", str(makefile), *zero,
                          "obj/platform/native_static.o", "other"])
            self.assertEqual(result.stdout, "KEEP|GAME\nKEEP|GAME\n")
        result = run(["make", "--no-print-directory", "-f", str(makefile), "WORLD_EMPTY_PREP01=1",
                      *valid, "obj/platform/native_static.o", "other"])
        self.assertEqual(result.stdout, "KEEP -DRE4DC_WORLD_EMPTY_PREP01=1|GAME\nKEEP|GAME\n")
        for value in ("", "-1", "2", "yes"):
            result = run(["make", "--no-print-directory", "-f", str(makefile),
                          "WORLD_EMPTY_PREP01="+value, *valid, "other"], okay=False)
            self.assertNotEqual(result.returncode, 0)
        for missing in DEPS:
            result = run(["make", "--no-print-directory", "-f", str(makefile), "WORLD_EMPTY_PREP01=1",
                          *[f"{d}={int(d != missing)}" for d in DEPS], "other"], okay=False)
            self.assertNotEqual(result.returncode, 0)

    def test_empty_success_preserves_binding_accounting_and_no_witness(self):
        for mutation, stream in ((1, 1), (0, 1), (1, 0)):
            off, on = self.pair(mutation, stream)
            for name in ("empty_indexed", "empty_plain", "two_empty_same_part"):
                a, b = off[name], on[name]
                with self.subTest(mutation=mutation, stream=stream, case=name):
                    for field in ("result", "submitted", "input", "output", "completion", "witness",
                                  "bind", "header", "owner", "camera", "end", "close", "abort", "ta",
                                  "groups_visible", "batches", "census_empty_or_drawn", "census_corners"):
                        self.assertEqual(a[field], b[field], field)
                    self.assertEqual(b["result"], 1)
                    self.assertEqual(b["completion"], 2)  # real Completion::Culled
                    self.assertFalse(b["witness"])
                    self.assertEqual(b["header"], 1)
                    for field in ("gather", "borrow", "acquire", "constants", "prime", "corners",
                                  "package", "transforms", "strips"):
                        self.assertEqual(b[field], 0, field)
                    self.assertGreater(a["borrow"], 0)

    def test_bind_owner_and_mutation_refusals_unchanged(self):
        for mutation, stream in ((1, 1), (0, 1), (1, 0)):
            off, on = self.pair(mutation, stream)
            names = ["bind_refused_empty", "owner_refused_empty", "post_header_refused_empty"]
            if mutation:
                names += ["pre_bind_mutation_empty", "post_bind_mutation_empty"]
            for name in names:
                self.assertEqual(off[name], on[name], name)
                self.assertLessEqual(on[name]["result"], 0)
                self.assertFalse(on[name]["witness"])
                self.assertEqual(on[name]["borrow"], 0)
            if mutation:
                # Empty completion still reaches the unchanged post-end fence.
                a, b = off["post_end_mutation_empty"], on["post_end_mutation_empty"]
                for field in ("result", "abort", "end", "close", "ta", "witness"):
                    self.assertEqual(a[field], b[field], field)
                self.assertEqual(b["result"], -1)

    def test_only_empty_geometry_resource_refusal_is_removed(self):
        for mutation, stream in ((1, 1), (0, 1), (1, 0)):
            off, on = self.pair(mutation, stream)
            for kind in ("scratch_exhausted", "gather_unavailable"):
                a, b = off[kind+"_empty"], on[kind+"_empty"]
                self.assertEqual(a["result"], -1)
                self.assertEqual(b["result"], 1)
                for field in ("bind", "header", "owner", "camera", "ta", "end", "close"):
                    self.assertEqual(a[field], b[field], field)
                self.assertEqual(b["output"], 0)
                self.assertEqual(b["completion"], 2)
                self.assertFalse(b["witness"])
                self.assertEqual(b["reserve_rejects"], 0)
                self.assertEqual(off[kind+"_live"], on[kind+"_live"])

    def test_nonempty_suffix_partial_abort_and_restart(self):
        for mutation, stream in ((1, 1), (0, 1), (1, 0)):
            off, on = self.pair(mutation, stream)
            for name in ("nonempty_indexed", "nonempty_plain", "subset_indexed", "subset_plain",
                         "partial_emit_failure", "post_strip_mutation"):
                self.assertEqual(off[name], on[name], name)
            for name in ("empty_then_live", "live_then_empty", "empty_part_then_live_part"):
                a, b = off[name], on[name]
                for field in ("result", "submitted", "input", "output", "completion", "witness",
                              "bind", "header", "owner", "camera", "ta", "end", "close", "abort",
                              "transforms", "prime", "census_empty_or_drawn", "census_corners"):
                    self.assertEqual(a[field], b[field], name + "/" + field)
            self.assertEqual(on["partial_emit_failure"]["result"], -1)
            self.assertEqual(on["partial_emit_failure"]["completion"], 4)  # Partial
            self.assertFalse(on["partial_emit_failure"]["witness"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-file")
    parser.add_argument("--output-dir")
    args, remaining = parser.parse_known_args()
    BASELINE_FILE, OUTPUT_DIR = args.baseline_file, args.output_dir
    unittest.main(argv=[__file__, *remaining])
