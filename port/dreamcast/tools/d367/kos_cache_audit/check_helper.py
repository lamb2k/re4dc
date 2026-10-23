#!/usr/bin/env python3
"""Execute linked helper opcodes in a narrow SH4/cache-contract model.

This checks emitted control flow, masks, access regions, SR/ABI and cache-entry
coverage. It is not an SH4 timing, bus/pipeline, exception or hardware emulator.
Unknown instructions abort. Physical Dreamcast validation remains necessary.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess


def sx(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def execute(code, base, ccr, initial_sr, seed):
    rng = random.Random(seed)
    registers = [rng.getrandbits(32) for _ in range(16)]
    initial_registers = registers[:]
    tags = [rng.getrandbits(32) for _ in range(512)]
    initial_tags = tags[:]
    cache_data = [rng.getrandbits(256) for _ in range(512)]
    initial_data = cache_data[:]
    sr, pc, pr = initial_sr, base, 0x8cfff000
    pending = None
    steps, last_array = 0, None
    writes, reads, writebacks = [], [], []
    touched = []

    def p2(address):
        return address & 0xe0000000 == 0xa0000000

    def read(address, width):
        nonlocal last_array
        if address == 0xff00001c:
            assert width == 4
            touched.append("CCR")
            return ccr
        if 0xf4000000 <= address < 0xf4004000:
            assert width == 4 and address & 31 == 0, "non-associative longword required"
            assert p2(pc), "cache array read outside P2"
            assert sr & 0x100000f0 == 0x100000f0, "unprotected cache array read"
            index = (address >> 5) & 511
            assert not (ccr & 0x20 and index & 128), "OC RAM entry accessed"
            reads.append(index)
            last_array = steps
            return tags[index]
        physical = address & 0x1fffffff
        offset = physical - (base & 0x1fffffff)
        assert 0 <= offset and offset + width <= len(code), ("unexpected data read", hex(address))
        # All PC-relative literals after P2 entry are read through P2 too.
        if last_array is not None:
            assert p2(address), "cached data read during/after sweep"
        return int.from_bytes(code[offset:offset + width], "little")

    def write(address, value):
        nonlocal last_array
        assert 0xf4000000 <= address < 0xf4004000, ("unexpected store", hex(address))
        assert address & 31 == 0 and p2(pc), "non-associative P2 array store required"
        assert sr & 0x100000f0 == 0x100000f0, "unprotected cache array store"
        assert value & ~0x1ffffc01 == 0, "U/reserved bits written"
        index = (address >> 5) & 511
        assert not (ccr & 0x20 and index & 128), "OC RAM entry written"
        assert value == tags[index] & 0x1ffffc01, "tag/V changed"
        if tags[index] & 3 == 3:
            writebacks.append(index)
        tags[index] = value
        writes.append(index)
        last_array = steps

    while pc != pr:
        assert steps < 10000, "helper did not terminate"
        physical = pc & 0x1fffffff
        offset = physical - (base & 0x1fffffff)
        assert 0 <= offset < len(code) - 1, ("bad PC", hex(pc))
        op = int.from_bytes(code[offset:offset + 2], "little")
        n, m = op >> 8 & 15, op >> 4 & 15
        next_pc, next_pending = pc + 2, None
        is_delay = pending is not None
        if op == 0x0009:
            pass
        elif op == 0x000b:
            next_pending = pr
        elif op & 0xff00 == 0xc700:
            registers[0] = (pc & ~3) + 4 + (op & 255) * 4
        elif op & 0xf000 == 0xd000:
            registers[n] = read((pc & ~3) + 4 + (op & 255) * 4, 4)
        elif op & 0xf00f == 0x200b:
            registers[n] |= registers[m]
        elif op & 0xf00f == 0x2009:
            registers[n] &= registers[m]
        elif op & 0xf0ff == 0x402b:
            next_pending = registers[n]
        elif op & 0xf0ff == 0x0002:
            registers[n] = sr
        elif op & 0xf0ff == 0x400e:
            if last_array is not None and registers[n] & 0x100000f0 != 0x100000f0:
                assert steps - last_array >= 8, "IRQ enabled before P2 exit gap"
            sr = registers[n]
        elif op & 0xf00f == 0x6003:
            registers[n] = registers[m]
        elif op & 0xf00f == 0x6002:
            registers[n] = read(registers[m], 4)
        elif op & 0xf00f == 0x2002:
            write(registers[n], registers[m])
        elif op & 0xff00 == 0xc800:
            sr = sr & ~1 | int(registers[0] & (op & 255) == 0)
        elif op & 0xff00 in (0x8900, 0x8b00):
            take = bool(sr & 1) == (op & 0xff00 == 0x8900)
            if take:
                next_pc = pc + 4 + sx(op & 255, 8) * 2
        elif op & 0xf000 == 0xe000:
            registers[n] = sx(op & 255, 8) & 0xffffffff
        elif op & 0xf000 == 0xa000:
            next_pending = pc + 4 + sx(op & 4095, 12) * 2
        elif op & 0xf0ff == 0x4018:
            registers[n] = registers[n] << 8 & 0xffffffff
        elif op & 0xf0ff == 0x4000:
            sr = sr & ~1 | registers[n] >> 31
            registers[n] = registers[n] << 1 & 0xffffffff
        elif op & 0xf0ff == 0x4010:
            registers[n] = registers[n] - 1 & 0xffffffff
            sr = sr & ~1 | int(registers[n] == 0)
        elif op & 0xf000 == 0x7000:
            registers[n] = (registers[n] + sx(op & 255, 8)) & 0xffffffff
        elif op & 0xf00f == 0x300c:
            registers[n] = registers[n] + registers[m] & 0xffffffff
        else:
            raise AssertionError(("unimplemented instruction", hex(pc), hex(op)))
        if is_delay:
            assert next_pending is None, "branch in delay slot"
            next_pc, pending = pending, None
        else:
            pending = next_pending
        if last_array is not None and p2(pc) and not p2(next_pc):
            assert steps - last_array >= 8, "returned from P2 too early"
        pc = next_pc
        steps += 1
    expected = [i for i in range(512) if not (ccr & 0x20 and i & 128)]
    assert reads == writes == expected
    assert writebacks == [i for i in expected if initial_tags[i] & 3 == 3]
    assert tags == [value & 0x1ffffc01 if i in expected else value for i, value in enumerate(initial_tags)]
    assert cache_data == initial_data, "cache data/RAM changed"
    assert registers[8:] == initial_registers[8:], "callee-saved GPR/SP changed"
    assert sr == initial_sr, "SR changed"
    return dict(instructions=steps, array_reads=len(reads), array_writes=len(writes),
                writebacks=len(writebacks), final_exit_gap=steps - last_array)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prefix", required=True)
    p.add_argument("--object", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    cases = []
    for base in (0x8c010000, 0x8c15ffc0, 0x8c6fd824):
        elf, binary = a.output / (f"{base:x}.elf"), a.output / (f"{base:x}.bin")
        subprocess.run([a.prefix + "ld", "-EL", "-Ttext=" + hex(base), "-e", "_arch_dcache_wback_all_p2",
                        "-o", elf, a.object], check=True)
        subprocess.run([a.prefix + "objcopy", "-j", ".text", "-O", "binary", elf, binary], check=True)
        code = binary.read_bytes()
        disassembly = subprocess.check_output([a.prefix + "objdump", "-d", elf], text=True)
        (a.output / (f"{base:x}.disassembly.txt")).write_text(disassembly)
        for ora in (0, 1):
            for oix in (0, 1):
                ccr = 0x105 | ora * 0x20 | oix * 0x80
                for sr in (0x40000000, 0x40000001, 0x400000f0, 0x700000f1):
                    for seed in range(8):
                        result = execute(code, base, ccr, sr, seed)
                        cases.append(dict(base=hex(base), ora=ora, oix=oix, sr=hex(sr), seed=seed, **result))
        # Deliberately redirect the helper's P2-mask literal back to P1. This
        # must trip the same architecture check the old C loop violates.
        altered = code.replace(struct.pack("<I", 0xa0000000), struct.pack("<I", 0x80000000))
        assert altered != code
        try:
            execute(altered, base, 0x105, 0x40000000, 0)
        except AssertionError as error:
            assert "outside P2" in str(error), error
        else:
            raise AssertionError("negative P1 control passed")
    report = dict(status="PASS", scope=__doc__, cases=len(cases), results=cases,
                  negative_controls="P1 literal mutation rejected at first OC array read, all three links")
    (a.output / "helper-contract.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(cases))))


if __name__ == "__main__":
    main()
