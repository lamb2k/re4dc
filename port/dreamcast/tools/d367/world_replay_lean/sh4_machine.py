# Test-only helper retained from commit 8c7226467dba68ac8ee16652accc10f683562685.
# This copies no renderer runtime or PR56 ancestry into the integration branch.
"""Scalar SH4 extension of the existing exact strip interpreter.

Only encountered, documented scalar opcodes are added. FTRV/FSRRA are not
implemented: the fixture supplies synthetic projected caches and observes all
reciprocal values. Unsupported instructions and unmapped accesses fail closed.
"""
import math
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backface_sh4_kernel"))
import object_test as base  # noqa: E402


class Machine(base.Machine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fpul = 0
        self.mach = 0
        self.macl = 0
        self.instruction_pcs = []

    def fetch(self, pc):
        # Opcode fetches are distinct from data reads, even if a program loads
        # its own current instruction word. The replay traffic observer uses
        # read() only for data; no cache/timing semantics change here.
        return base.Machine.read(self, pc & base.U32, 2)

    def fp_value(self, register):
        bits = self.f(register)
        if self.fpscr & (1 << 18) and bits & 0x7F800000 == 0:
            bits &= 0x80000000
        return base.asfloat(bits)

    def arithmetic(self, op, a, b):
        assert self.fpscr & 3 == 0, "RZ/reserved arithmetic is outside this interpreter's qualification"
        return super().arithmetic(op, a, b)

    def step(self, pc, delay=False):
        self.instruction_pcs.append(pc)
        w = self.fetch(pc)
        n, m = (w >> 8) & 15, (w >> 4) & 15
        r = self.reg
        target = None
        if w in (0x0008, 0x0018):
            self.t = int(w == 0x0018)
        elif w & 0xF000 == 0x9000:
            r[n] = base.signed(self.read(pc + 4 + (w & 255) * 2, 2), 16) & base.U32
        elif w & 0xF00F == 0x6000:
            r[n] = base.signed(self.read(r[m], 1), 8) & base.U32
        elif w & 0xF00F == 0x6001:
            r[n] = base.signed(self.read(r[m], 2), 16) & base.U32
        elif w & 0xF00F == 0x6005:
            address = r[m]
            r[n] = base.signed(self.read(address, 2), 16) & base.U32
            if n != m:
                r[m] = (address + 2) & base.U32
        elif w & 0xF00F == 0x2000:
            self.write(r[n], r[m], 1)
        elif w & 0xF00F == 0x2001:
            self.write(r[n], r[m], 2)
        elif w & 0xF00F == 0x600D:
            r[n] = r[m] & 65535
        elif w & 0xF00F == 0x600E:
            r[n] = base.signed(r[m] & 255, 8) & base.U32
        elif w & 0xF00F == 0x600F:
            r[n] = base.signed(r[m] & 65535, 16) & base.U32
        elif w & 0xF00F == 0x600B:
            r[n] = -r[m] & base.U32
        elif w & 0xF00F == 0x600A:
            source, carry = r[m], self.t
            r[n] = (-source - carry) & base.U32
            self.t = int(source != 0 or carry != 0)
        elif w & 0xF00F == 0x6009:
            r[n] = ((r[m] << 16) | (r[m] >> 16)) & base.U32
        elif w & 0xF00F == 0x6008:
            r[n] = (r[m] & 0xFFFF0000) | ((r[m] & 255) << 8) | ((r[m] >> 8) & 255)
        elif w & 0xF00F == 0x3007:
            self.t = int(base.signed(r[n]) > base.signed(r[m]))
        elif w & 0xF00F == 0x3003:
            self.t = int(base.signed(r[n]) >= base.signed(r[m]))
        elif w & 0xF00F == 0x300E:
            value = r[n] + r[m] + self.t
            r[n], self.t = value & base.U32, int(value > base.U32)
        elif w & 0xF0FF == 0x0029:
            r[n] = self.t
        elif w & 0xF0FF in (0x4019, 0x4029):
            r[n] >>= 8 if w & 0xF0FF == 0x4019 else 16
        elif w & 0xF0FF == 0x4021:
            self.t = r[n] & 1
            r[n] = (base.signed(r[n]) >> 1) & base.U32
        elif w & 0xFF00 == 0xC700:
            r[0] = ((pc + 4) & ~3) + (w & 255) * 4
        elif w & 0xFF00 in (0x8000, 0x8100):
            size = 1 if w & 0xFF00 == 0x8000 else 2
            self.write(r[m] + (w & 15) * size, r[0], size)
        elif w & 0xFF00 in (0x8400, 0x8500):
            size = 1 if w & 0xFF00 == 0x8400 else 2
            r[0] = base.signed(self.read(r[m] + (w & 15) * size, size), size * 8) & base.U32
        elif w & 0xF00F == 0x000E:
            r[n] = self.read(r[0] + r[m], 4)
        elif w & 0xF00F == 0x0006:
            self.write(r[0] + r[n], r[m], 4)
        elif w & 0xF00F == 0x0004:
            self.write(r[0] + r[n], r[m], 1)
        elif w & 0xF00F == 0x0005:
            self.write(r[0] + r[n], r[m], 2)
        elif w & 0xF00F == 0x0007:
            self.macl = r[n] * r[m] & base.U32
        elif w & 0xF00F == 0x3005:
            product = (r[n] & base.U32) * (r[m] & base.U32)
            self.mach, self.macl = product >> 32, product & base.U32
        elif w & 0xF0FF == 0x000A:
            r[n] = self.mach
        elif w & 0xF0FF == 0x001A:
            r[n] = self.macl
        elif w & 0xF000 == 0xB000:
            self.pr = pc + 4
            target = pc + 4 + base.signed(w & 4095, 12) * 2
        elif w & 0xF0FF in (0x0003, 0x0023):
            target = (pc + 4 + r[n]) & base.U32
            if w & 0xF0FF == 0x0003:
                self.pr = pc + 4
        elif w & 0xF0FF == 0x405A:
            self.fpul = r[n]
        elif w & 0xF0FF == 0x005A:
            r[n] = self.fpul
        elif w & 0xF0FF == 0xF01D:
            self.fpul = self.f(n)
        elif w & 0xF0FF == 0xF00D:
            self.sf(n, self.fpul)
        elif w & 0xF0FF == 0xF02D:
            assert self.fpscr & 3 == 0, "RZ integer conversion is not modeled"
            self.sf(n, base.fbits(float(base.signed(self.fpul))))
        elif w & 0xF0FF == 0xF09D:
            self.sf(n, 0x3F800000)
        elif w & 0xF0FF == 0xF05D:
            self.sf(n, self.f(n) & 0x7FFFFFFF)
        elif w & 0xF00F in (0xF000, 0xF003):
            assert self.fpscr & 3 == 0, "RZ/reserved arithmetic is not modeled"
            a, b = self.fp_value(n), self.fp_value(m)
            if w & 15 == 0:
                value = a + b
            elif b:
                value = a / b
            else:
                value = math.nan if not a else math.copysign(math.inf, a * math.copysign(1.0, b))
            bits = base.fbits(value)
            if self.fpscr & (1 << 18) and bits & 0x7F800000 == 0:
                bits &= 0x80000000
            self.sf(n, bits)
        elif w & 0xF0FF == 0xF06D:
            assert self.fpscr & 3 == 0, "RZ square root is not modeled"
            value = self.fp_value(n)
            self.sf(n, base.fbits(math.sqrt(value) if value >= 0 else math.nan))
        elif w & 0xF00F == 0xF004:
            self.t = int(self.fp_value(n) == self.fp_value(m))
        elif w & 0xF00F == 0xF005:
            self.t = int(self.fp_value(n) > self.fp_value(m))
        elif w & 0xF00F == 0xF00A:
            assert not self.fpscr & (1 << 20)
            self.write(r[n], self.f(m), 4)
        elif w & 0xF00F == 0xF006:
            assert not self.fpscr & (1 << 20)
            self.sf(n, self.read(r[0] + r[m], 4))
        elif w & 0xF00F == 0xF007:
            assert not self.fpscr & (1 << 20)
            self.write(r[0] + r[n], self.f(m), 4)
        else:
            # The original interpreter recursively calls self.step for branch
            # delay slots, so the trace already contains each instruction once.
            if w & 0xF00F == 0xF00E:
                assert self.fpscr & 3 == 0, "RZ FMAC is not modeled"
            # The existing backface base interpreter predates fetch(). Mark
            # exactly its first opcode read, then let the observer clear it.
            self._base_fetch_pending = pc
            return super().step(pc, delay)
        self.steps += 1
        if target is not None:
            assert not delay
            self.step(pc + 2, True)
            return target
        return pc + 2

    def execute(self, entry, argument=0x9000):
        self.pc, self.pr, self.reg[4] = entry, 0xFFFFFFF0, argument
        self.steps = 0
        self.instruction_pcs = []
        while self.pc != 0xFFFFFFF0:
            self.pc = self.step(self.pc)
            assert self.steps < 2000000, ("instruction bound", hex(self.pc))
        assert len(self.instruction_pcs) == self.steps
        assert self.reg[15] == self.initial_regs[15]
        assert self.reg[8:15] == self.initial_regs[8:15]
        assert self.fpscr == self.initial_fpscr
        assert self.fp[0][12:16] == self.initial_fp[0][12:16]
        assert self.fp[1] == self.initial_fp[1]
        return bytes(self.output)


def load_elf(path):
    blob = path.read_bytes()
    assert blob[:6] == b"\x7fELF\x01\x01"
    phoff, shoff = struct.unpack_from("<II", blob, 28)
    phsize, phnum, shsize, shnum = struct.unpack_from("<4H", blob, 42)
    segments = []
    for i in range(phnum):
        p = struct.unpack_from("<8I", blob, phoff + i * phsize)
        kind, offset, vaddr, _, filesz, memsz, flags, _ = p
        if kind == 1 and vaddr < 0x1000000:
            segments.append((vaddr, blob[offset:offset + filesz] + bytes(memsz - filesz), flags))
    sections = [struct.unpack_from("<10I", blob, shoff + i * shsize) for i in range(shnum)]
    symbols = {}
    for sec in sections:
        if sec[1] != 2:
            continue
        names = sections[sec[6]]
        strings = blob[names[4]:names[4] + names[5]]
        for at in range(sec[4], sec[4] + sec[5], 16):
            name, value, size, info, other, index = struct.unpack_from("<IIIBBH", blob, at)
            if index:
                symbols[strings[name:].split(b"\0", 1)[0].decode()] = (value, size, info)
    return segments, symbols


def unsigned_multiply_controls():
    """Check the compiler's unsigned /3 sequence and both multiply results.

    SH-4 Software Manual, DMULU.L and STS: DMULU.L writes the full unsigned
    product to MACH:MACL; STS copies the selected register. Neither changes T.
    MUL.L writes only MACL. These are bounded opcode checks, not timing claims.
    """
    import random

    values = (0, 1, 2, 0x5555, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, base.U32)
    rng = random.Random(0xD367)
    pairs = [(a, b) for a in values for b in values]
    pairs += [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(64)]
    # dmulu.l r7,r2; sts mach,r4; sts macl,r5
    machine = Machine(struct.pack("<3H", 0x3275, 0x040A, 0x051A), b"", b"", 255, 2)
    assert machine.mach == machine.macl == 0
    entry = 0x100000
    multiply_cases = 0

    def run_three(opcodes):
        machine.map(entry, struct.pack("<3H", *opcodes))
        machine.steps = 0
        machine.instruction_pcs = []
        pc = entry
        for _ in range(3):
            pc = machine.step(pc)
        assert pc == entry + 6
        assert machine.steps == len(machine.instruction_pcs) == 3
        assert machine.instruction_pcs == [entry, entry + 2, entry + 4]

    for a, b in pairs:
        for t in (0, 1):
            machine.reg[2], machine.reg[7], machine.t = a, b, t
            machine.mach, machine.macl = 0x12345678, 0x87654321
            before = list(machine.reg)
            run_three((0x3275, 0x040A, 0x051A))
            expected = a * b
            assert (machine.mach, machine.macl) == (expected >> 32, expected & base.U32)
            assert (machine.reg[4], machine.reg[5]) == (machine.mach, machine.macl)
            assert machine.t == t
            assert all(machine.reg[i] == before[i] for i in range(16) if i not in (4, 5))
            multiply_cases += 1

    # Same-register source decoding, including the unsigned high-bit cases.
    for a in values:
        machine.reg[2], machine.t = a, 1
        run_three((0x3225, 0x040A, 0x051A))
        assert (machine.reg[4], machine.reg[5]) == (a * a >> 32, a * a & base.U32)
        assert machine.reg[2] == a and machine.t == 1
        multiply_cases += 1

    low_only_cases = 0
    for a, b in pairs[:64]:
        machine.reg[2], machine.reg[7], machine.t = a, b, 1
        machine.mach = 0x89ABCDEF
        run_three((0x0277, 0x040A, 0x051A))  # mul.l r7,r2; sts mach,r4; sts macl,r5
        assert machine.reg[4] == machine.mach == 0x89ABCDEF
        assert machine.reg[5] == machine.macl == a * b & base.U32
        assert (machine.reg[2], machine.reg[7], machine.t) == (a, b, 1)
        low_only_cases += 1

    # This exact DMULU.L / STS MACH / SHLR sequence implements unsigned /3.
    divide_values = list(range(20)) + [255, 256, 65534, 65535, 65536,
                                    0x7FFFFFFF, 0x80000000, 0xFFFFFFFD,
                                    0xFFFFFFFE, base.U32]
    divide_values += [rng.getrandbits(32) for _ in range(64)]
    for a in divide_values:
        machine.reg[2], machine.reg[7], machine.t = a, 0xAAAAAAAB, 1
        run_three((0x3275, 0x070A, 0x4701))
        assert machine.reg[7] == a // 3
        assert machine.reg[2] == a
        assert (machine.mach, machine.macl) == (a * 0xAAAAAAAB >> 32,
                                               a * 0xAAAAAAAB & base.U32)
        assert machine.t == machine.mach & 1  # SHLR alone changes T.

    return {"status": "PASS", "unsigned_multiply_cases": multiply_cases,
            "low_only_multiply_cases": low_only_cases,
            "unsigned_divide_three_cases": len(divide_values),
            "scope": "Bounded actual-opcode arithmetic and trace controls; no timing or hardware claim",
            "manual": "https://www.renesas.com/en/document/mas/sh-4-software-manual"}
