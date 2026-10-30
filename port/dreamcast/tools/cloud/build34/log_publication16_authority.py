#!/usr/bin/env python3
"""Read-only installed archive / retained ELF soft-gUSA exception audit.

Never builds or runs a programme. This is exception-entry authority evidence,
not target atomic code generation, NMI, timing, cache or hardware acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kos", type=Path, required=True)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--tool-prefix", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    archive = args.kos / "lib/dreamcast/libkallisti.a"
    source = args.kos / "kernel/arch/dreamcast/kernel/irq.c"
    entry = args.kos / "kernel/arch/dreamcast/kernel/entry.s"
    assert "irq_srt_addr->pc = irq_srt_addr->r[0] + irq_srt_addr->r[15];" in source.read_text()
    source_text = source.read_text()
    assert source_text.index("irq_srt_addr->pc = irq_srt_addr->r[0]") < source_text.index("switch(code)")
    head = subprocess.check_output(["git", "-C", str(args.kos), "rev-parse", "HEAD"], text=True).strip()
    members = subprocess.check_output([args.tool_prefix + "ar", "t", str(archive)], text=True)
    assert "irq.o" in members.splitlines()
    instruction_sets = []
    for label, path in (("installed-archive", archive), ("retained-elf", args.elf)):
        result = subprocess.check_output([args.tool_prefix + "objdump", "-d", "--disassemble=_irq_handle_exception", str(path)], text=True)
        (args.output / (label + "-irq.txt")).write_text(result)
        match = re.search(r"^([0-9a-f]+) <_irq_handle_exception>:\n", result, re.M)
        assert match, label
        base = int(match[1], 16)
        block = result[match.end():].split("\n\n", 1)[0]
        instructions = {}
        for line in block.splitlines():
            item = re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]{2}) ([0-9a-f]{2})\s+(.+)$", line)
            if item:
                instructions[int(item[1], 16) - base] = (item[2] + item[3], item[4])
        expected = {2: "80e2", 0x12: "2331", 0x14: "528d", 0xbc: "5362", 0xc0: "2952",
                    0xc2: "5263", 0xc4: "2033", 0xc6: "a789", 0xc8: "2c31", 0xca: "a5af", 0xcc: "1225"}
        for offset, opcode in expected.items():
            assert instructions[offset][0] == opcode, (label, offset, instructions.get(offset))
        assert "<_irq_handle_exception+0xbc>" in instructions[0x14][1]
        assert "<_irq_handle_exception+0x18>" in instructions[0xca][1]
        instruction_sets.append(instructions)
    # The installed archive's entry and rollback code is present in the
    # retained linked programme, before the first dispatch path at +0x34.
    assert all(instruction_sets[0][offset][0] == instruction_sets[1][offset][0] for offset in range(0, 0xd0, 2))
    receipt = dict(status="PASS_READ_ONLY_INSTALLED_EXCEPTION_AUTHORITY", kos_head=head,
                   paths={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (archive, source, entry, args.elf)},
                   rollback_test_offset="+0x12/+0x14", rollback_block="+0xbc..+0xcc",
                   rollback_rejoins="+0x18", dispatch_begins="+0x34",
                   installed_and_linked_entry_bytes_identical="0..0xcf",
                   limits=["retained ELF is authority evidence, not this candidate's target build",
                           "future target must verify compiler atomic lowering and selected exception archive again",
                           "NMI/bypass entry, IRQ time, cache/raw-RAM and hardware remain unqualified"])
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
