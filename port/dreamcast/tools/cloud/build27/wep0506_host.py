#!/usr/bin/env python3
"""Exercise complete wep05/wep06 source with synthetic weapon services.

This is a control-flow and callback-contract fixture. The target build validates
the real headers, layout, ABI, module symbols and native code. No game assets are
read, generated or included in this test.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCES = (
    "src/wep05/objCivilian.cpp",
    "src/wep05/wep05.cpp",
    "src/wep06/wep06.cpp",
)
BASELINE = "6be0a66ab59fa597a55aae7379fb09777d357bc1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--sanitize", action="store_true")
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    headers = out / "headers"
    headers.mkdir()
    prefix = HERE / "weapon_fixture_prefix.hpp"
    for header in ("wep_mod.h", "light.h", "item.h", "motion.h", "esp.h", "snd.h", "pad.h", "rnd.h"):
        (headers / header).write_text('#pragma once\n#include "weapon_fixture_prefix.hpp"\n')
    copies = []
    adaptations = []
    for rel in SOURCES:
        raw = (ROOT / rel).read_text()
        # The original game uses a 32-bit integer carrier for effect-owner
        # pointers. Keep the full host pointer at that explicit service boundary.
        before = "(int) this"
        after = "(std::intptr_t) this"
        count = raw.count(before)
        if count:
            adaptations.append({"source": rel, "from": before, "to": after, "count": count})
            raw = raw.replace(before, after)
        copy = out / (rel.replace("/", "_") + ".inc")
        copy.write_text('#line 1 "' + rel + '"\n' + raw)
        copies.append(copy)
    template = (HERE / "wep0506_fixture.cpp.in").read_text()
    for token, path in zip(("@CIVILIAN@", "@WEP05@", "@WEP06@"), copies):
        assert template.count(token) == 1
        template = template.replace(token, str(path))
    generated = out / "wep0506_fixture.cpp"
    generated.write_text(template)
    command = ["g++", "-std=c++17", "-O2", "-g", "-Wall", "-Wextra",
               "-I" + str(headers), "-I" + str(HERE), str(generated), "-o", str(out / "wep0506_fixture")]
    if args.sanitize:
        command[3:3] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
    compiled = subprocess.run(command, text=True, capture_output=True)
    (out / "compile.log").write_text(compiled.stdout + compiled.stderr)
    compiled.check_returncode()
    env = dict(os.environ)
    if args.sanitize:
        env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1"
    ran = subprocess.run([str(out / "wep0506_fixture")], text=True, capture_output=True, env=env)
    (out / "run.log").write_text(ran.stdout + ran.stderr)
    ran.check_returncode()
    results = json.loads(ran.stdout)
    wiring = runpy.run_path(str(ROOT / "port/dreamcast/tools/assetpipe/wiring.py"))
    production = [ROOT / p for p in SOURCES] + [ROOT / "src/wep/pl_handgun.cpp"]
    unchanged = {}
    for path in production:
        rel = str(path.relative_to(ROOT))
        old = subprocess.check_output(["git", "show", BASELINE + ":" + rel], cwd=ROOT)
        unchanged[rel] = old == path.read_bytes()
    assert all(unchanged.values()), "Fixture qualification expects unchanged recovered weapon source"
    provenance = production + [
        ROOT / "config/G4BE08/modules.py",
        ROOT / "config/G4BE08/modules/wep05/rel.json",
        ROOT / "config/G4BE08/modules/wep06/rel.json",
        ROOT / "config/G4BE08/modules/wep05/splits.txt",
        ROOT / "config/G4BE08/modules/wep06/splits.txt",
        ROOT / "port/dreamcast/game/tools/gen_modules.py",
        ROOT / "include/types.h", ROOT / "include/global.h",
        ROOT / "include/cManager.h", ROOT / "src/game/obj.cpp",
        prefix, HERE / "wep0506_fixture.cpp.in", Path(__file__),
    ]
    results.update({
        "baseline": BASELINE,
        "sanitized": args.sanitize,
        "scope": __doc__,
        "compile_command": command,
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in provenance},
        "unchanged_production_source": unchanged,
        "generated_source_sha256": digest(generated),
        "host_only_pointer_cast_adaptations": adaptations,
        "port_lint": {mod: wiring["lint_module"](ROOT, mod) for mod in ("wep05", "wep06")},
        "manual_lint_qualification": (
            "Placement-new value initialization is safe for these cObj classes: "
            "cManager::createBack clears storage first; cObjMgr sets serial/id after "
            "ObjInitFunc and list insertion follows. There is no cEm subArc input to erase. "
            "No direct sparse EmMgr array accesses, hardcoded vptr offsets or file-static asm aliases."
        ),
        "limits": [
            "Synthetic class declarations and services are control boundaries, not target layout/ABI proof.",
            "Host u32 pointer carriers and the validity interval are widened; real SH4 bounds come from include/types.h.",
            "Model/motion/sound/effect/collision services record calls; no private assets or game tick loop execute.",
            "PlHandgunMove is a recorded registration target here; its unchanged production body is compiled by the target module gate.",
            "This fixture makes no gameplay, appearance, whole-frame or hardware timing claim.",
        ],
    })
    (out / "wep0506-host.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: v for k, v in results.items() if k in ("status", "cases", "sanitized", "coverage")}))


if __name__ == "__main__":
    main()
