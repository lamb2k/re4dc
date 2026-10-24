"""Shared bounded target execution and demand-traffic/model accounting.

Uses only previously landed world tools. Additional FTRC support is confined
to finite signed-16-bit fixture values. GCC's unsigned-int conversion path is
supported only for exact small nonnegative FLOAT(PR=1)/FCNVDS pairs; general
double arithmetic and invalid/overflow conversions remain unsupported.
Cycles assume perfect D-cache/no DMA/zero SQ. Lines are demand addresses, not
misses. Scalar RN/DN arithmetic is not general hardware FP conformance.
"""
import importlib.util
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPLAY=HERE.parent/'world_replay_lean'
sys.path.insert(0,str(REPLAY))
import target_machine
import pipeline_cost
from memory_trace import summarize
spec=importlib.util.spec_from_file_location('ui_target_price',REPLAY/'target_run.py')
price_helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(price_helpers)


class Machine(target_machine.Machine):
    def __init__(self):
        super().__init__();self.hooks={};self.captures=[]
    def word(self,address,size=4):return int.from_bytes(self.bytes_at(address,size),'little')
    def step(self,pc,delay=False):
        if pc in self.hooks:
            continuation=self.hooks[pc](self)
            if continuation is not None:return continuation
        opcode=self.fetch(pc)
        if opcode&0xf0ff==0xf02d and self.fpscr&(1<<19):
            register=(opcode>>8)&15
            assert register%2==0 and self.fpscr&3==0 and 0<=self.fpul<=32767
            bits=struct.unpack('<Q',struct.pack('<d',float(self.fpul)))[0]
            self.sf(register,bits>>32);self.sf(register+1,bits&0xffffffff)
            self.instruction_pcs.append(pc);self.steps+=1
            return pc+2
        if opcode&0xf0ff==0xf0bd:
            register=(opcode>>8)&15
            assert register%2==0 and self.fpscr&(1<<19) and self.fpscr&3==0
            bits=(self.f(register)<<32)|self.f(register+1)
            value=struct.unpack('<d',struct.pack('<Q',bits))[0]
            assert 0<=value<=32767 and int(value)==value,('unqualified FCNVDS',value)
            self.fpul=struct.unpack('<I',struct.pack('<f',value))[0]
            self.instruction_pcs.append(pc);self.steps+=1
            return pc+2
        if opcode&0xf0ff==0xf03d:
            value=self.fp_value((opcode>>8)&15)
            assert -32768<=value<=32767,('unqualified FTRC',value)
            self.fpul=int(value)&0xffffffff
            self.instruction_pcs.append(pc);self.steps+=1
            return pc+2
        if self.fpscr&(1<<19) and opcode&0xf000==0xf000:
            assert opcode&15 not in (0,1,2,3,4,5,14),('unqualified double arithmetic',hex(pc),hex(opcode))
        return super().step(pc,delay)


def load(path):
    segments,symbols=target_machine.scalar.load_elf(path)
    m=Machine()
    for address,data,_ in segments:m.map(address,data)
    return m,symbols


def traffic(m):
    result=summarize(m.memory_events,m.prefetch_events)
    result['demand_line_visits']=sum(len({a>>5 for a in range(e[3],e[3]+e[4])}) for e in m.memory_events)
    result['repeated_demand_line_visits']=result['demand_line_visits']-result['cached']['unique_data_lines']
    return result


def row(m):
    return dict(instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,traffic=traffic(m))


def price(model,name,m):
    trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
    return price_helpers.price(model,name,trace)


def controls():
    """Known-word controls for the narrow new conversions, plus base traffic controls."""
    result=target_machine.memory_controls();cases=0
    for value in (0,1,9,32,64,255,32767):
        m=Machine();m.fpscr|=1<<19;m.fpul=value
        m.map(0x100000,struct.pack('<3H',0xf22d,0xf2bd,0xf00d))
        m.observe_start();pc=0x100000
        for _ in range(3):pc=m.step(pc)
        m.observe_stop()
        expected=struct.unpack('<I',struct.pack('<f',float(value)))[0]
        assert m.f(0)==m.fpul==expected and m.steps==3 and not m.memory_events
        assert (m.f(2)<<32)|m.f(3)==struct.unpack('<Q',struct.pack('<d',float(value)))[0]
        cases+=1
    for value in (-32768.,-3.75,-0.,0.,.25,255.75,32767.):
        m=Machine();m.map(0x100000,struct.pack('<H',0xf03d))
        m.sf(0,struct.unpack('<I',struct.pack('<f',value))[0]);m.step(0x100000)
        assert m.fpul==int(value)&0xffffffff and m.steps==1
        cases+=1
    for opcode,fpul in ((0xf22d,0xffffffff),(0xf22d,32768)):
        m=Machine();m.fpscr|=1<<19;m.fpul=fpul;m.map(0x100000,struct.pack('<H',opcode))
        try:m.step(0x100000)
        except AssertionError:pass
        else:raise AssertionError('out-of-domain conversion accepted')
    result.update(conversion_cases=cases,conversion_boundaries_rejected=2,
        conversion_scope='Exact small nonnegative FLOAT(PR=1)/FCNVDS, finite signed16 FTRC; no general double arithmetic')
    return result
