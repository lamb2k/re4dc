#!/usr/bin/env python3
"""Check unchanged short ranges and the exact 65560-byte dispatch boundary."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess


def sections(path):
    data = path.read_bytes()
    assert data[:6] == b"\x7fELF\x01\x01"
    off = struct.unpack_from("<I", data, 32)[0]
    size, count, names_index = struct.unpack_from("<HHH", data, 46)
    rows = [struct.unpack_from("<10I", data, off + i * size) for i in range(count)]
    names = data[rows[names_index][4]:rows[names_index][4] + rows[names_index][5]]
    return {names[row[0]:].split(b"\0", 1)[0].decode(): data[row[4]:row[4] + row[5]]
            for row in rows if row[1] != 8}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prefix", required=True)
    p.add_argument("--kos-root", type=Path, required=True)
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    counts = (0, 1, 31, 32, 33, 65535, 65536, 65559, 65560, 65568, 1048576)
    source = a.output / "thresholds.c"
    source.write_text("#include <kos/cache.h>\n" + "\n".join(
        f"void range_{n}(uintptr_t p) {{ dcache_wback_range(p, {n}); }}" for n in counts) +
        "\nvoid whole(void) { dcache_wback_all(); }\n")
    base = [a.prefix + "gcc", "-m4-single", "-ml", "-fno-PIC", "-fno-PIE",
            "-ffunction-sections", "-fdata-sections", "-D_arch_dreamcast=1", "-D__DREAMCAST__"]
    for path in ("include", "kernel/arch/dreamcast/include", "addons/include"):
        base += ["-isystem", str(a.kos_root / path)]
    result = {}
    for optimization in ("O2", "Os"):
        objects = {}
        for on in (0, 1):
            obj = a.output / (f"{optimization}-{on}.o")
            command = [*base, "-" + optimization,
                       "-I" + str(a.prepared / "tree/kernel/arch/dreamcast/include"),
                       "-DKOS_CACHE_P2=" + str(on), "-c", source, "-o", obj]
            subprocess.run(command, check=True)
            objects[on] = sections(obj)
            text = subprocess.check_output([a.prefix + "objdump", "-dr", obj], text=True)
            (a.output / (f"{optimization}-{on}.disassembly.txt")).write_text(text)
            result[f"{optimization}-{on}"] = dict(command=[str(x) for x in command],
                object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest())
        for n in counts:
            name = ".text.range_" + str(n)
            if n < 65560:
                assert objects[0][name] == objects[1][name], (optimization, n)
                # ELF symbol indices change when the helper declaration adds a
                # symbol. Compare resolved relocations, not those raw indices.
                relocations = []
                for on in (0, 1):
                    text = subprocess.check_output([a.prefix + "objdump", "-r", "-j", name,
                        a.output / (f"{optimization}-{on}.o")], text=True)
                    relocations.append(re.findall(r"^[0-9a-f]+\s+R_SH_.*$", text, re.M))
                assert relocations[0] == relocations[1], (optimization, n)
            else:
                dis = (a.output / (f"{optimization}-1.disassembly.txt")).read_text()
                body = dis.split(f"<" + "_range_" + str(n) + ">:", 1)[1].split("Disassembly of section", 1)[0]
                assert "_arch_dcache_wback_all_p2" in body
                old = (a.output / (f"{optimization}-0.disassembly.txt")).read_text()
                old_body = old.split(f"<" + "_range_" + str(n) + ">:", 1)[1].split("Disassembly of section", 1)[0]
                assert "_arch_dcache_wback_all_p2" not in old_body
        common = ".text.arch_dcache_wback_range"
        if common in objects[0]:
            # -Os outlines the shared branch/short loop. Its raw bytes are
            # unchanged; only the large-arm function relocation changes.
            assert objects[0][common] == objects[1][common]
    report = dict(status="PASS", counts=list(counts), optimizations=["-O2", "-Os"], results=result,
        scope="Raw code/relocation identity below the unchanged threshold; real helper references at/above it")
    (a.output / "thresholds.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", counts=len(counts), optimizations=2)))


if __name__ == "__main__":
    main()
