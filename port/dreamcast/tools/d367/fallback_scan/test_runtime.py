#!/usr/bin/env python3
"""Compile the actual renderer and draw converted synthetic ModelData bytes."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import convert
from test_convert import fixture, raw

HERE = Path(__file__).resolve().parent
DREAMCAST = HERE.parents[2]


@unittest.skipUnless(shutil.which("g++"), "host C++ compiler required")
class ProductionRuntime(unittest.TestCase):
    def test_actual_actor_admission_and_baked_draw(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp/"dc").mkdir()
            (tmp/"dc/pvr.h").write_text("""#pragma once
#include <cstddef>
#include <cstdint>
struct pvr_vertex_t {std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};
struct pvr_poly_hdr_t {std::uint32_t words[8];};
#define PVR_CMD_VERTEX 0xe0000000U
#define PVR_CMD_VERTEX_EOL 0xf0000000U
int pvr_prim(const void*,std::size_t);
""")
            data, context = fixture()
            (tmp/"original.bin").write_bytes(data)
            (tmp/"fold.bin").write_bytes(convert.convert(data, raw(context), True, False)[0])
            probe = copy.deepcopy(context)
            probe["parts"][0]["lighting"].update(material_rgb=[255,255,255], model_id=0x41)
            (tmp/"probe.bin").write_bytes(convert.convert(data, raw(probe), False, True)[0])
            vertex = copy.deepcopy(context)
            vertex["parts"][0]["lighting"].update(ambient_vertex=True, material_vertex=True)
            (tmp/"vertex.bin").write_bytes(convert.convert(data, raw(vertex), False, True)[0])
            sanitizers = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"] if os.environ.get("SCAN29_SANITIZE") == "1" else []
            for scan, fast, lean, headroom in ((0,0,0,0),(1,0,0,0),(1,0,1,0),(0,1,0,0),(1,1,0,0),(1,1,1,0),(1,0,1,1)):
                exe = tmp/f"runtime-{scan}-{fast}-{lean}-{headroom}"
                cmd = ["g++", "-std=c++20", "-O1", "-g", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                    *sanitizers, "-DRE4DC_LEON_SOURCE_LIGHT=1", "-DRE4DC_ACTOR_PROBE_LIGHT=2",
                    f"-DRE4DC_FALLBACK_SCAN29={scan}", f"-DRE4DC_ACTOR_LIGHT_FAST_ONLY={fast}",
                    f"-DRE4DC_MEMSET_LEAN={lean}", f"-DRE4DC_ACTOR_NO_CLEAR={lean}",
                    f"-DRE4DC_LEON_LIGHT_HEADROOM={headroom}",
                    "-I"+str(tmp), "-I"+str(DREAMCAST/"game/platform/include"),
                    str(HERE/"test_runtime.cpp"), str(DREAMCAST/"room/source_lighting.cpp"),
                    str(DREAMCAST/"room/pvr_geometry.cpp"), "-o", str(exe)]
                built = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(built.returncode, 0, built.stderr)
                run = subprocess.run([str(exe), *(str(tmp/(name+".bin")) for name in ("original","fold","probe","vertex"))],
                    capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                print(run.stdout.strip())


if __name__ == "__main__":
    unittest.main()
