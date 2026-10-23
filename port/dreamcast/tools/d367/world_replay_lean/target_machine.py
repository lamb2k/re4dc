"""Qualified scalar target interpreter and data-traffic observer for this lane.

The additional operations below are retained from the published setup/submit
test harnesses. No FTRV/FSRRA approximation is added. Unsupported opcodes and
unmapped memory accesses fail closed; setup fixtures cannot claim renderer or
whole-frame execution.
"""
import struct

import sh4_machine as scalar
from memory_trace import Observer


class ArithmeticMachine(scalar.Machine):
    def __init__(self):
        self.minimum_sp = 0x500000
        super().__init__(b"", b"", b"", 255, 0, fpscr=0x40000)
        self.sr = 0x40000000

    def read(self, address, size):
        return super().read(address & 0xffffffff, size)

    def write(self, address, value, size):
        return super().write(address & 0xffffffff, value, size)

    def bytes_at(self, address, size):
        return bytes(self.mem[address + i] for i in range(size))

    def step(self, pc, delay=False):
        self.minimum_sp = min(self.minimum_sp, self.reg[15])
        opcode = self.fetch(pc)
        n, m = (opcode >> 8) & 15, (opcode >> 4) & 15
        if opcode & 0xf00f in (0x000c, 0x000d):
            size = 1 if opcode & 15 == 12 else 2
            self.reg[n] = scalar.base.signed(self.read(self.reg[0] + self.reg[m], size), size*8) & 0xffffffff
        elif opcode & 0xf00f == 0x200e:  # MULU.W
            self.macl = (self.reg[n] & 65535) * (self.reg[m] & 65535)
        elif opcode & 0xf00f == 0x300a:  # SUBC
            a, b, borrow = self.reg[n], self.reg[m], self.t
            self.reg[n] = (a - b - borrow) & 0xffffffff
            self.t = int(a < b + borrow)
        elif opcode & 0xf0ff == 0x0002:  # STC SR,Rn
            self.reg[n] = (self.sr & ~1) | self.t
        elif opcode & 0xf0ff == 0x400e:  # LDC Rm,SR; no bank switch
            value = self.reg[n] & 0x700083f3
            assert (value ^ self.sr) & (1 << 29) == 0
            self.sr, self.t = value, value & 1
        elif opcode & 0xff00 == 0xcb00:  # OR #imm,R0
            self.reg[0] |= opcode & 255
        elif opcode & 0xf0ff == 0x0083 and not 0xe0000000 <= self.reg[n] < 0xe4000000:
            # PREF of cached RAM changes no architectural register or memory
            # value. Requests are observed separately; no fill is invented.
            pass
        else:
            result = super().step(pc, delay)
            self.minimum_sp = min(self.minimum_sp, self.reg[15])
            return result
        self.instruction_pcs.append(pc)
        self.steps += 1
        self.minimum_sp = min(self.minimum_sp, self.reg[15])
        return pc + 2


class Machine(Observer, ArithmeticMachine):
    pass


def memory_controls():
    controls = []
    # Plain register move is fetched through multiple interpreter dispatchers
    # but contributes no data access. The next load/store are exactly one each.
    machine = Machine()
    machine.map(0x100000, struct.pack("<4H", 0x6213, 0x6212, 0x2322, 0x0009))
    machine.map(0x2000, struct.pack("<I", 0x89abcdef))
    machine.map(0x3000, bytes(4))
    machine.reg[1], machine.reg[3] = 0x2000, 0x3000
    machine.observe_start()
    pc = 0x100000
    for _ in range(4):
        pc = machine.step(pc)
    result = machine.observe_stop()
    assert machine.memory_events == [(1,0x100002,"read",0x2000,4),
                                      (2,0x100004,"write",0x3000,4)]
    assert result["cached"]["load_instructions"] == result["cached"]["store_instructions"] == 1
    controls.append("fetches excluded; scalar load/store retained")

    # PC-relative literal is still a data access even inside executable text.
    machine = Machine()
    machine.map(0x100000, struct.pack("<2HI", 0xd100, 0x0009, 0x12345678))
    machine.observe_start(); machine.step(0x100000); machine.observe_stop()
    assert machine.reg[1] == 0x12345678
    assert machine.memory_events == [(0,0x100000,"read",0x100004,4)]
    controls.append("PC-relative literal classified as data")

    machine = Machine();machine.map(0x100000,struct.pack("<H",0x6211));machine.reg[1]=0x100000
    machine.observe_start();machine.step(0x100000);machine.observe_stop()
    assert machine.reg[2] == 0x6211
    assert machine.memory_events == [(0,0x100000,"read",0x100000,2)]
    controls.append("data read of current opcode word retained")

    # Delay-slot store must be attached to the retired delay-slot instruction,
    # not to the preceding branch.
    machine = Machine()
    machine.map(0x100000, struct.pack("<3H", 0xa000, 0x2122, 0x0009))
    machine.map(0x2020, bytes(4)); machine.reg[1]=0x2020;machine.reg[2]=7
    machine.observe_start();machine.step(0x100000);result=machine.observe_stop()
    assert machine.memory_events == [(1,0x100002,"write",0x2020,4)]
    assert result["cached"]["unique_data_lines"] == 1
    controls.append("delay slot attributed exactly once")

    # Double FMOV is one retired memory instruction transferring eight bytes.
    machine = Machine();machine.fpscr |= 1 << 20
    machine.map(0x100000, struct.pack("<H",0xf218))
    machine.map(0x2000, struct.pack("<2I",0x01234567,0x89abcdef));machine.reg[1]=0x2000
    machine.observe_start();machine.step(0x100000);result=machine.observe_stop()
    assert machine.memory_events == [(0,0x100000,"read",0x2000,8)]
    assert result["cached"]["load_instructions"] == 1 and result["cached"]["load_bytes"] == 8
    controls.append("double-register move counted as one 8-byte load")

    # Newlib's wrapped index is resolved before line classification.
    machine = Machine();machine.map(0x100000,struct.pack("<2H",0x0126,0x031e))
    machine.map(0x2000,bytes(4));machine.reg[0]=0xfffffffc;machine.reg[1]=0x2004;machine.reg[2]=0x81234567
    machine.observe_start();machine.step(0x100000);machine.step(0x100002);machine.observe_stop()
    assert machine.memory_events == [(0,0x100000,"write",0x2000,4),(1,0x100002,"read",0x2000,4)]
    controls.append("32-bit effective address wrap")

    # SQ stores are data writes but do not occupy normal data-cache lines.
    machine=Machine();machine.map(0x100000,struct.pack("<H",0x2122));machine.reg[1]=0xe0000000
    machine.observe_start();machine.step(0x100000);result=machine.observe_stop()
    assert result["cached"]["unique_data_lines"] == 0
    assert result["store_queue"]["store_instructions"] == 1
    controls.append("store queues excluded from cached footprint")

    machine=Machine();machine.map(0x100000,struct.pack("<H",0x0183));machine.reg[1]=0x2000
    machine.observe_start();machine.step(0x100000);result=machine.observe_stop()
    assert not machine.memory_events and result["cached"]["unique_data_lines"] == 0
    assert result["prefetch"]["requests"] == result["prefetch"]["unique_requested_lines"] == 1
    controls.append("cached PREF counted separately from demand loads")
    return dict(status="PASS",controls=controls)


if __name__ == "__main__":
    import json
    print(json.dumps(memory_controls(), indent=2))
