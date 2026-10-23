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
        self.macl = 0
        self.instruction_pcs = []

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
        w = self.read(pc, 2)
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
