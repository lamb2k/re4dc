#!/usr/bin/env python3
"""Bounded disassembly review of the full-production native_static objects.

This counts instructions on explicitly selected paths, including delay slots.
It does not execute the renderer, price cycles, or include called UI/KOS/libc
bodies. Section hashes deliberately pin this review to the inspected compiler
output: a changed object requires a new review, not silent reuse of offsets.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess


SECTIONS = {
    "bind": ".text._ZN12_GLOBAL__N_17Emitter4bindEv.part.0",
    "emit": ".text._ZN12_GLOBAL__N_18MeshDraw10chunk_emitEPKNS0_4PickEj",
    "flush": ".text._ZZN12_GLOBAL__N_1L8ps2_passEjfENKUlvE_clEv",
    "end": ".text._ZN12_GLOBAL__N_17Emitter10end_directEv",
}
REVIEWED = {
    ("baseline", "bind"): "b684e7f96c85ac40bfc2db7300ad0260b47f9fb1eb77c459bbbb104c2e3ad0b7",
    ("baseline", "emit"): "f5253200b9ce1ccdbe95d3a245173f8f7ebd1765f54c3333181733af507c0f18",
    ("baseline", "flush"): "7891a1d896b599189384bd00fde79f6cce2032b239a7dbae7f1e6dae63e1e7f7",
    ("on", "bind"): "b451ffaaf5e1cc253da7ac7f216293739a4e5d62df2bff8ee6032f3c674ab1e8",
    ("on", "emit"): "429b3efa3ef65fe44fa8e5a66acf90bc420df37b034fed9ea1c6dd6d761f3da4",
    ("on", "flush"): "b66a7bedab2de5689d370f2edab21fdc3516b6c3fe7af9c726ac36b9caea1e28",
    ("on", "end"): "6104c4476b46620d4618226d4d78b68c518fd7aa2d83e08c9a2e9b9bc8a31721",
}


def sections(path):
    data = path.read_bytes()
    assert data[:6] == b"\x7fELF\x01\x01", "expected ELF32 little endian"
    offset = struct.unpack_from("<I", data, 32)[0]
    size, count, strings_index = struct.unpack_from("<3H", data, 46)
    headers = [struct.unpack_from("<10I", data, offset + i * size)
               for i in range(count)]
    strings_header = headers[strings_index]
    strings = data[strings_header[4]:strings_header[4] + strings_header[5]]
    result = {}
    for h in headers:
        name = strings[h[0]:strings.find(b"\0", h[0])].decode()
        if h[1] != 8:  # SHT_NOBITS has no file payload.
            result[name] = data[h[4]:h[4] + h[5]]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--objdump", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    raw, instructions, receipts = {}, {}, {}
    for profile in ("baseline", "on"):
        obj = args.build_dir / f"native_static-{profile}.o"
        obj_sections = sections(obj)
        receipts[profile] = {"object": str(obj.resolve()),
                             "sha256": hashlib.sha256(obj.read_bytes()).hexdigest(),
                             "sections": {}}
        for name, section in SECTIONS.items():
            if (profile, name) not in REVIEWED:
                continue
            payload = obj_sections[section]
            digest = hashlib.sha256(payload).hexdigest()
            assert digest == REVIEWED[profile, name], (
                f"{profile}/{name} changed; re-review paths before counting")
            raw[profile, name] = payload
            disassembly = subprocess.check_output(
                [str(args.objdump), "-dr", "-C", "-j", section, str(obj)],
                text=True)
            file = args.output / f"native_static-{profile}-{name}.disasm.txt"
            file.write_text(disassembly)
            rows = {}
            for line in disassembly.splitlines():
                match = re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]{2}) "
                                 r"([0-9a-f]{2})\s+(.+)", line)
                if match:
                    rows[int(match[1], 16)] = match[4]
            instructions[profile, name] = rows
            receipts[profile]["sections"][name] = {
                "section": section, "bytes": len(payload), "sha256": digest,
                "disassembly": str(file.resolve())}

    def path(profile, name, *spans):
        addresses = [address for start, end in spans
                     for address in range(start, end + 1, 2)]
        assert all(address in instructions[profile, name] for address in addresses)
        return {"instructions": len(addresses), "section": SECTIONS[name],
                "inclusive_hex_spans": [[hex(a), hex(b)] for a, b in spans]}

    # Conditions: direct PS2 draw, live token in ON, successful first bind;
    # existing camera record takes its unchanged initial fast branch. All
    # external bodies are excluded. No source-owner callbacks in this profile.
    bind = {
        "baseline": path("baseline", "bind", (0, 0x22), (0x64, 0x86), (0x8c, 0xee)),
        "on": path("on", "bind", (0, 0x22), (0x64, 0xf4)),
    }
    # Unmarked row skips the optional LUT construction. Memset/memcpy bodies
    # are excluded; argument sizes are reported separately below.
    setup = {
        "baseline": path("baseline", "flush", (0x62, 0xea), (0x106, 0x1a8)),
        "on": path("on", "flush", (0x66, 0xee), (0x10a, 0x1b2)),
    }
    end = {
        "baseline": [path("baseline", "flush", (0x1aa, 0x1ba))],
        "on": [path("on", "flush", (0x1b4, 0x1ba)),
               path("on", "end", (0, 0x24))],
    }
    empty_end = {
        "baseline": [path("baseline", "flush", (0x1aa, 0x1b0))],
        "on": [path("on", "flush", (0x1b4, 0x1ba)),
               path("on", "end", (0, 0xc), (0x20, 0x24))],
    }
    # Prologue, final failed loop test and normal epilogue. The final
    # batch_close CALL is counted, its UI implementation is not counted.
    fixed = {
        "baseline": path("baseline", "flush", (0, 0x60), (0x23e, 0x258)),
        "on": path("on", "flush", (0, 0x64), (0x244, 0x268)),
    }
    differences = [a for a in range(0, len(raw["baseline", "emit"]), 2)
                   if raw["baseline", "emit"][a:a + 2] != raw["on", "emit"][a:a + 2]]
    # Each changed encoding is the same load instruction with a displacement
    # shifted by the four-byte token member; no added control flow.
    assert differences == [0xb0, 0x14c, 0x158, 0x15c, 0x266, 0x270, 0x2e2,
                           0x2f4, 0x338, 0x492, 0x4fe, 0x516]
    assert raw["baseline", "emit"][0x118:0x138] == raw["on", "emit"][0x118:0x138]
    u16 = lambda profile, offset: struct.unpack_from("<H", raw[profile, "flush"], offset)[0]
    assert [u16(p, 0x1d8) for p in ("baseline", "on")] == [776, 776]
    assert [u16(p, 0x1da) for p in ("baseline", "on")] == [209, 213]
    assert [u16(p, 0x1d0) for p in ("baseline", "on")] == [816, 820]
    delta = lambda values: values["on"]["instructions"] - values["baseline"]["instructions"]
    end_delta = sum(p["instructions"] for p in end["on"]) - sum(p["instructions"] for p in end["baseline"])
    empty_delta = sum(p["instructions"] for p in empty_end["on"]) - sum(p["instructions"] for p in empty_end["baseline"])
    assert (delta(bind), delta(setup), end_delta, empty_delta, delta(fixed)) == (5, 3, 14, 10, 7)
    report = {
        "status": "PASS bounded disassembly path review",
        "method": "Static instruction counts from hashed full-TU production objects; not an execution or cycle benchmark.",
        "build_controls": str((args.build_dir / "build-controls.json").resolve()),
        "objects": receipts,
        "paths": {"first_bind": bind, "row_setup": setup, "nonempty_logical_end": end,
                  "empty_logical_end": empty_end, "fixed_flush": fixed},
        "added_instructions": {"first_bind": delta(bind), "row_setup": delta(setup),
                               "nonempty_logical_end": end_delta,
                               "empty_logical_end": empty_delta,
                               "fixed_flush": delta(fixed),
                               "successful_nonempty_row_including_first_bind": delta(bind) + delta(setup) + end_delta},
        "memory": {"whole_meshdraw_clear_bytes": [776, 776],
                   "emitter_member_clear_bytes": [209, 213],
                   "flush_stack_allocation_bytes": [816, 820],
                   "new_end_wrapper_saved_register_bytes": 8},
        "chunk_emit": {"section_bytes": [2024, 2024],
                       "already_bound_guard_identical": True,
                       "changed_load_displacements_hex": [hex(x) for x in differences]},
        "limits": ["No cycles assigned to instruction deltas or four additional cleared bytes per row.",
                   "UI, KOS, libc, geometry and real PVR scheduling/contended mutex costs are outside this review.",
                   "Counts apply to the reviewed primary production configuration and successful normal replay path.",
                   "This cannot be subtracted directly from a cycle benchmark or establish net r101 frame time."]}
    destination = args.output / "static-review.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "added_instructions": report["added_instructions"],
                      "receipt": str(destination.resolve())}, indent=2))


if __name__ == "__main__":
    main()
