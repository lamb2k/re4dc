#!/usr/bin/env python3
"""Run the actual Build27 equip admission/load/refusal bodies with synthetic I/O.

This reuses the low-address synthetic archive strategy of the existing
cache21/test_weapon_archive_reuse.py. Source selectors are compared against
the original base; no private game assets or game services are executed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASELINE = "6be0a66ab59fa597a55aae7379fb09777d357bc1"


def block(text, signature, semicolon=False):
    start = text.index(signature)
    at = text.index("{", start)
    end, depth = at + 1, 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    if semicolon:
        assert text[end] == ";"
        end += 1
    return text[start:end]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--sanitize", action="store_true")
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    names = ["src/game/read.cpp", "src/game/item.cpp", "src/game/pl_wep.cpp",
             "src/game/sscrn.cpp", "src/game/dvd.cpp", "port/dreamcast/game/platform/modules.cpp",
             "src/game/t_option.cpp"]
    sources = {name: (ROOT / name).read_text() for name in names}
    read, item = sources[names[0]], sources[names[1]]
    modules = sources["port/dreamcast/game/platform/modules.cpp"]
    parts = {}
    parts["tables"] = "\n".join([
        block(read, key + "[46]", True)
        for key in ("ReadFile wep_data_leon", "ReadFile wep_data_ada",
                    "static ReadFile wep_data_hunk", "static ReadFile wep_data_wesker", "ReadFile wep_data_klauser")
    ])
    parts["item_types"] = block(item, "struct WepInfo {", True)
    parts["item_table"] = block(item, "const WepInfo wep_info[]", True)
    parts["file_table"] = block(sources["src/game/dvd.cpp"], "FileTblEntry FileTbl[]", True)
    metadata = {}
    roster = []
    for name in ("wep00", "wep02", "wep05", "wep06", "wep12"):
        rel = "config/G4BE08/modules/" + name + "/rel.json"
        data = (ROOT / rel).read_text()
        metadata[rel] = sha(data)
        roster.append('{%du,"%s"}' % (json.loads(data)["module_id"], name))
    parts["roster"] = ",\n".join(roster)
    parts["module_helpers"] = "\n".join(block(modules, signature) for signature in (
        "static int moduleIndex(u32 id)",
        'extern "C" int re4dc_weapon27_module_id_present(unsigned id)',
        'extern "C" int re4dc_weapon27_module_file_present(const char* rel)',
    ))
    parts["selector"] = block(read, "static ReadFile* wep27_read_file(u32 no, u32 type)")
    parts["available"] = block(read, 'extern "C" int re4dc_weapon27_available(unsigned no, unsigned type)')
    parts["item_methods"] = "\n".join(block(item, signature) for signature in (
        "u8 WeaponId2WeaponNo(u16 id)", "u8 WeaponId2WeaponType(u16 id)", "u16 WeaponNo2WeaponId(u8 no, u8 type)",
        "u16 bareHand()", "static inline int itemUse(ItemWork* p, int type)",
        "u16 cItemMgr::weaponId(ItemWork* p)", "int cItemMgr::arm(ItemWork* p)",
        "void cItemMgr::debugWeapon(int id)",
    ))
    parts["read_methods"] = "\n".join(block(read, signature) for signature in (
        "void InitModule(ReadModule* m)\n{", "void ReleaseWepData()\n{",
        "static void wep27_refuse_data()", "void re4dc_weapon27_revert(int oldNo, int oldType, int no, int type)",
        "void ReadWepData(u32 no, u32 type)\n{",
    ))
    parts["weapon_load"] = block(sources["src/game/pl_wep.cpp"], "void cPlayer::weaponLoad(int no, int type)")
    original = subprocess.check_output(["git", "show", BASELINE + ":src/game/read.cpp"], cwd=ROOT, text=True)
    original_load = block(original, "void ReadWepData(u32 no, u32 type)\n{")
    start = original_load.index("    switch (pG->pl_type)")
    stop = original_load.index("    if (e->file == 0)", start)
    parts["original_selector"] = (
        "static ReadFile* original_selector(u32 no,u32 type) {\nReadFile* e;\n"
        + original_load[start:stop] + "return e;\n}"
    )
    sscrn = sources["src/game/sscrn.cpp"]
    restore_blocks = []
    marker = "#if RE4DC_WEAPON_HEAP4 || (defined(RE4DC_WEP_MODULES_27) && RE4DC_WEP_MODULES_27)"
    at = 0
    for n in range(2):
        at = sscrn.index(marker, at)
        end = sscrn.index("#endif", at) + len("#endif")
        restore_blocks.append("static void sscrn_restore_%d(int& wepLv) {\n%s\n}" % (n, sscrn[at:end]))
        at = end
    parts["sscrn_restore"] = "\n".join(restore_blocks)
    option = sources["src/game/t_option.cpp"]
    end_marker = "                ItemMgr.debugWeapon(WeaponNo2WeaponId(pT->cursor, pT->rno[3]));"
    end = option.index(end_marker) + len(end_marker)
    start = option.rfind("                cPlayer* pl = pPL;", 0, end)
    assert start >= 0 and "if (!re4dc_wep_reverted)" in option[start:end]
    parts["debug_caller"] = "static void debug_caller(Task* pT) {\n" + option[start:end] + "\n}"
    template = (HERE / "equip_fixture.cpp.in").read_text()
    for key, value in parts.items():
        token = "@" + key.upper() + "@"
        assert template.count(token) == 1, token
        template = template.replace(token, value)
    generated = out / "equip_fixture.cpp"
    generated.write_text(template)
    outcomes = []
    for heap in (0, 1):
        for reuse in (0, 1):
            exe = out / ("equip-h%d-r%d" % (heap, reuse))
            command = ["g++", "-std=c++17", "-O2", "-g", "-fpermissive",
                       "-DRE4DC_WEP_MODULES_27=1", "-DRE4DC_GAME=1",
                       "-DRE4DC_WEAPON_HEAP4=" + str(heap),
                       "-DRE4DC_WEAPON_ARCHIVE_REUSE=" + str(reuse),
                       str(generated), "-o", str(exe)]
            if args.sanitize:
                command[3:3] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
            compiled = subprocess.run(command, text=True, capture_output=True)
            (out / (exe.name + ".compile.log")).write_text(compiled.stdout + compiled.stderr)
            compiled.check_returncode()
            env = dict(os.environ)
            if args.sanitize:
                env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1"
            ran = subprocess.run([str(exe)], text=True, capture_output=True, env=env)
            (out / (exe.name + ".run.log")).write_text(ran.stdout + ran.stderr)
            ran.check_returncode()
            result = json.loads(ran.stdout)
            outcomes.append(dict(result, compile_command=command))
            print(json.dumps(result))
    # Refuse a stale receipt if a collaborator edits a source while tests run.
    for rel, text in sources.items():
        assert (ROOT / rel).read_text() == text, "Source changed during qualification: " + rel
    receipt = {
        "status": "PASS", "baseline": BASELINE, "sanitized": args.sanitize,
        "scope": __doc__, "outcomes": outcomes,
        "source_sha256": dict({rel: sha(text) for rel, text in sources.items()}, **metadata),
        "extracted_sha256": {key: sha(value) for key, value in parts.items()},
        "fixture_template_sha256": sha((HERE / "equip_fixture.cpp.in").read_text()),
        "runner_sha256": sha(Path(__file__).read_text()),
        "generated_sha256": sha(template),
        "boundaries": [
            "Actual current ReadFile/FileTbl/wep_info data, module lookup, selectors, item arm/debug, load, InitModule, ReleaseWepData, refusal/revert and caller methods execute.",
            "Module roster is a small synthetic admission set with real metadata ids; actual full image roster and SH4 ABI are separate target gates.",
            "DVD emits synthetic low-address archive headers; native OSLink, module prolog/epilog, allocator, texture/motion/effect retirement and inventory metadata services are explicit recorded boundaries.",
            "32-bit archive pointer arithmetic is retained with MAP_32BIT backing; -fpermissive accepts the deliberate host pointer-to-u32 casts and proves no native ABI property.",
            "The selector oracle is extracted from the original base, not independently reimplemented; invalid indices are tested only on the new bounded helper.",
            "No game data, gameplay tick equivalence, audio/video or physical I/O timing is exercised.",
        ],
    }
    (out / "equip-contract.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
