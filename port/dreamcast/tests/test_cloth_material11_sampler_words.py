"""Sampler word-type regression; optional tiny SH-4 actual-header compile.

Host: python3 -B port/dreamcast/tests/test_cloth_material11_sampler_words.py
Target (explicit serialized SDK grant only): set RE4DC_TEST_SH4_CXX to the
pinned sh-elf-g++ and RE4DC_TEST_SH4_OUT to a NEW evidence directory.
The target arm compiles the same tiny fixture against old/current headers,
preserves both logs, and never links or executes target code.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
INC = ROOT / "game/platform/include"
BASE = "020a4c38d061860612020764bb1e8ad008d66092"
HEADER = "cloth_material11_sampler.hpp"


class SamplerWords11(unittest.TestCase):
    def test_unsigned_and_distinct_32_bit_words_normal_and_sanitized(self):
        code = r'''
#include <cassert>
#include <cstdint>
#include <type_traits>
#include "cloth_material11_sampler.hpp"
using namespace re4dc::cloth_material11;
static_assert(std::is_same_v<std::uint32_t,unsigned>);
static_assert(!std::is_same_v<char32_t,unsigned> && sizeof(char32_t)==4);
template<class Word> void exercise(){
 Word words[8]{};for(unsigned i=0;i<5;++i)words[i]=Word(i*31+9);words[3]=0;
 const Word before[5]={words[0],words[1],words[2],words[3],words[4]};
 const auto qualified=[&](){unsigned copy[8];for(unsigned i=0;i<8;++i)copy[i]=unsigned(words[i]);return linear_clamp(copy);};
 init_sampler(words,0);assert(qualified()&&words[5]==sampler_capture&&words[6]==linear_filters&&words[7]==2);
 for(unsigned i=0;i<5;++i)assert(words[i]==before[i]);
 for(unsigned bc=0;bc<2;++bc)for(unsigned edge=0;edge<2;++edge){
  lod_sampler(words,1,1,0,0,0,bc,edge,0);assert(qualified()&&words[7]==(bc|(edge<<1)));
 }
 lod_sampler(words,0,1,0,0,0,0,1,0);assert(!qualified()&&words[5]==sampler_capture&&!words[6]&&!words[7]);
 lod_sampler(words,1,1,0,0,0,0,1,0);assert(qualified());
 init_sampler(words,1);assert(!qualified()&&!words[6]&&words[7]==2);
 words[5]=0;lod_sampler(words,1,1,0,0,0,0,1,0);assert(!qualified()&&!words[5]&&!words[6]&&!words[7]);
 for(unsigned i=0;i<5;++i)assert(words[i]==before[i]);
}
int main(){exercise<std::uint32_t>();exercise<char32_t>();}
'''
        with tempfile.TemporaryDirectory(prefix="cloth-sampler11-words-") as td:
            tmp = Path(td)
            source, exe = tmp / "words.cpp", tmp / "words"
            source.write_text(code)
            for sanitize in (False, True):
                with self.subTest(sanitize=sanitize):
                    command = ["g++", "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + str(INC), str(source), "-o", str(exe)]
                    if sanitize:
                        command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
                    run = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    run = subprocess.run([str(exe)], capture_output=True, text=True, env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
                    self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            # Negative control: the old pointer signature admits unsigned but
            # rejects a distinct unsigned 32-bit type despite the same layout.
            old = tmp / "old"
            old.mkdir()
            (old / HEADER).write_bytes(subprocess.check_output(["git", "show", BASE + ":port/dreamcast/game/platform/include/" + HEADER], cwd=REPO))
            for word, accepted in (("std::uint32_t", True), ("char32_t", False)):
                source.write_text('#include <cstdint>\n#include "' + HEADER + '"\nvoid probe(){' + word + ' words[8]{};re4dc::cloth_material11::init_sampler(words,0);}\n')
                run = subprocess.run(["g++", "-std=c++20", "-I" + str(old), "-c", str(source), "-o", str(tmp / "old.o")], capture_output=True, text=True)
                self.assertEqual(run.returncode == 0, accepted, run.stderr)

    def test_signed_short_and_wide_words_are_rejected_by_both_writers(self):
        with tempfile.TemporaryDirectory(prefix="cloth-sampler11-reject-") as td:
            tmp = Path(td)
            source = tmp / "rejected.cpp"
            for word in ("std::int32_t", "std::uint16_t", "std::uint64_t", "std::int64_t"):
                for call in ("init_sampler(words,0)", "lod_sampler(words,1,1,0,0,0,0,1,0)"):
                    with self.subTest(word=word, call=call):
                        source.write_text('#include <cstdint>\n#include "' + HEADER + '"\nvoid rejected(){' + word + ' words[8]{};re4dc::cloth_material11::' + call + ';}\n')
                        run = subprocess.run(["g++", "-std=c++20", "-I" + str(INC), "-c", str(source), "-o", str(tmp / "rejected.o")], capture_output=True, text=True)
                        self.assertNotEqual(run.returncode, 0)
                        self.assertIn("GX sampler needs unsigned 32-bit words", run.stderr)

    @unittest.skipUnless(os.environ.get("RE4DC_TEST_SH4_CXX"), "explicit tiny SH-4 SDK grant required")
    def test_actual_project_types_and_gx_object_sh4_compile(self):
        compiler = Path(os.environ["RE4DC_TEST_SH4_CXX"])
        output = Path(os.environ["RE4DC_TEST_SH4_OUT"])
        output.mkdir(parents=True, exist_ok=False)
        old = output / "old-include"
        old.mkdir()
        (old / HEADER).write_bytes(subprocess.check_output(["git", "show", BASE + ":port/dreamcast/game/platform/include/" + HEADER], cwd=REPO))
        source = ROOT / "tests/cloth_material11_sh4_compile.cpp"
        report = {"compiler": str(compiler), "version": subprocess.check_output([str(compiler), "--version"], text=True),
                  "fixture_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "arms": []}
        for name, include in (("old", old), ("current", INC)):
            obj = output / (name + ".o")
            command = [str(compiler), "-std=gnu++20", "-O2", "-g0", "-ml", "-m4-single-only", "-Wall", "-Wextra",
                       "-I" + str(include), "-I" + str(INC), "-I" + str(REPO / "include"), "-c", str(source), "-o", str(obj)]
            run = subprocess.run(command, capture_output=True, text=True)
            (output / (name + ".stdout.txt")).write_text(run.stdout)
            (output / (name + ".stderr.txt")).write_text(run.stderr)
            arm = {"name": name, "command": command, "returncode": run.returncode}
            if obj.exists():
                arm["object_sha256"] = hashlib.sha256(obj.read_bytes()).hexdigest()
                arm["elf_header"] = subprocess.check_output([str(compiler.with_name("sh-elf-readelf")), "-h", str(obj)], text=True)
            report["arms"].append(arm)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        self.assertNotEqual(report["arms"][0]["returncode"], 0, "old header must reproduce the actual u32 pointer mismatch")
        self.assertIn("unsigned int*", (output / "old.stderr.txt").read_text())
        self.assertEqual(report["arms"][1]["returncode"], 0, (output / "current.stderr.txt").read_text())
        self.assertIn("Renesas / SuperH SH", report["arms"][1]["elf_header"])
        print("SH-4 sampler actual-header compile PASS:", output)


if __name__ == "__main__":
    unittest.main()
