#!/usr/bin/env python3
"""RAM-only source-helper interpreter + actual observer controls, no SDK build."""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import unittest
import cache_diag as diag

TOOLS=Path(__file__).resolve().parent
DC=TOOLS.parents[2]
GAME=DC/'game'
PATCH=DC/'patches/kos-804b319-cache-p2.patch'
BASE='\n'.join(l[1:] for l in PATCH.read_text().split('@@ -0,0 +1,92 @@\n')[1].splitlines() if l.startswith('+'))+'\n'
MASK=0xffffffff


def helper(source, clock=None, initial=None, ora=False, base=0x8c100000, initial_sr=0x40000001):
    """Execute actual generated ASM source; model architecture, not cycles."""
    clock=clock or {};state=0xac900000
    labels={};ops={};data={};addr=base
    clean=re.sub(r'/\*.*?\*/','',source,flags=re.S)
    for line in clean.splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        if line.endswith(':'):labels[line[:-1]]=addr;continue
        if line.startswith('.align'):addr=(addr+3)&~3;continue
        if line.startswith('.long'):data[addr]=line.split(None,1)[1];addr+=4;continue
        if line.startswith('.'):continue
        ops[addr]=line;addr+=2
    for address,line in ops.items():
        parts=line.split(None,1)
        if len(parts)==1:continue
        op,arg=parts
        if op in ['bt','bf','bra']:
            delta=(labels[arg]-(address+4))//2
            limit=128 if op!='bra' else 2048
            assert -limit<=delta<limit,('branch displacement',line,delta)
        elif op=='mova' or (op=='mov.l' and arg.startswith('.L')):
            label=arg.split(',')[0];distance=labels[label]-((address&~3)+4)
            assert distance%4==0 and 0<=distance<=1020,('literal displacement',line,distance)
    registers=[0x12000000+i for i in range(16)];saved=registers[:]
    sr=initial_sr;original_sr=sr;pc=base;pending=None;steps=0
    counts={state+4*i:0 for i in range(16)}
    for i,v in (initial or {}).items():counts[state+i]=v
    tags=[(i<<10)|3|0x60000000 for i in range(512)];original_tags=tags[:]
    reads=[];writes=[];last_array=None;tcnt_reads=0
    expected=[i for i in range(512) if not(ora and i&128)]
    def region(address):return address&0xe0000000
    def read(address,width):
        nonlocal tcnt_reads,last_array
        if address==0xff00001c:return 0x105|(0x20 if ora else 0)
        if 0xf4000000<=address<0xf4004000:
            assert width==4 and address%32==0
            assert region(pc)==0xa0000000,'array outside P2'
            assert sr&0x100000f0==0x100000f0,'unmasked array'
            i=(address>>5)&511;assert i in expected
            reads.append(i);last_array=steps;return tags[i]
        if address==0xffd80024:
            value=clock.get('start' if tcnt_reads==0 else 'end',100000 if tcnt_reads==0 else 99900)
            tcnt_reads+=1;return value
        if address in [0xffd80004,0xffd80020,0xffd80028]:
            phase='start' if tcnt_reads<2 else 'end'
            name,default={0xffd80004:('tstr',4),0xffd80020:('reload',diag.TMU2_RELOAD),0xffd80028:('tcr',32)}[address]
            return clock.get(phase+'_'+name,default)
        if address&0x1fffffff==state&0x1fffffff or (state&0x1fffffff)<=address&0x1fffffff<(state&0x1fffffff)+64:
            assert region(address)==0xa0000000,'counter read outside P2'
            return counts[address]
        canonical=(address&0x1fffffff)|0x80000000
        assert canonical in data,('unexpected read',hex(address))
        value=data[canonical]
        return 0x8c900000 if value=='_re4dc_cache_p2_diag_counters' else int(value,0)
    def write(address,value):
        nonlocal last_array
        if 0xf4000000<=address<0xf4004000:
            assert region(pc)==0xa0000000 and sr&0x100000f0==0x100000f0
            i=(address>>5)&511;assert i in expected and address%32==0
            assert value==tags[i]&0x1ffffc01,'tag/V changed'
            tags[i]=value;writes.append(i);last_array=steps;return
        assert region(address)==0xa0000000,'counter write outside P2'
        assert address in counts,('unexpected store',hex(address))
        assert writes==expected,'counter before complete sweep'
        counts[address]=value&MASK
    def rn(x):return int(x[1:])
    def val(x):return registers[rn(x)] if re.fullmatch('r[0-9]+',x) else int(x.lstrip('#'),0)&MASK
    def pointer(x):
        m=re.fullmatch(r'@\((\d+),(r\d+)\)',x)
        return registers[rn(m[2])]+int(m[1]) if m else registers[rn(x[1:])]
    while pc!=0x8cfff000:
        assert steps<10000,'nontermination'
        line=ops[(pc&0x1fffffff)|0x80000000]
        mnemonic,*rest=line.split(None,1);arg=rest[0] if rest else ''
        parts=re.split(r',\s*(?![^()]*\))',arg)
        nxt=pc+2;branch=None;delayed=pending is not None
        if mnemonic=='nop':pass
        elif mnemonic=='mova':registers[0]=labels[parts[0]]
        elif mnemonic in ['mov.l','mov.w','mov.b']:
            a,b=parts;width={'mov.l':4,'mov.w':2,'mov.b':1}[mnemonic]
            if a.startswith('.L'):v=read((labels[a]&0x1fffffff)|region(pc),4);registers[rn(b)]=v
            elif a.startswith('@'):registers[rn(b)]=read(pointer(a),width)
            else:write(pointer(b),val(a))
        elif mnemonic=='mov':registers[rn(parts[1])]=val(parts[0])
        elif mnemonic=='stc':registers[rn(parts[1])]=sr
        elif mnemonic=='ldc':
            new=val(parts[0]);
            if writes:assert steps-last_array>=8,'short exit gap'
            sr=new
        elif mnemonic in ['or','and','add','sub','addc']:
            a,b=parts;i=rn(b);v=val(a);old=registers[i]
            if mnemonic=='or':registers[i]=old|v
            elif mnemonic=='and':registers[i]=old&v
            elif mnemonic=='add':registers[i]=(old+v)&MASK
            elif mnemonic=='sub':registers[i]=(old-v)&MASK
            else:
                result=old+v+(sr&1);registers[i]=result&MASK;sr=(sr&~1)|int(result>MASK)
        elif mnemonic=='clrt':sr&=~1
        elif mnemonic=='tst':sr=(sr&~1)|int(val(parts[0])&val(parts[1])==0)
        elif mnemonic=='cmp/eq':sr=(sr&~1)|int(val(parts[0])==val(parts[1]))
        elif mnemonic=='cmp/hs':sr=(sr&~1)|int(val(parts[1])>=val(parts[0]))
        elif mnemonic=='dt':
            i=rn(arg);registers[i]=(registers[i]-1)&MASK;sr=(sr&~1)|int(registers[i]==0)
        elif mnemonic in ['shll8','shll']:
            i=rn(arg);shift=8 if mnemonic=='shll8' else 1
            if shift==1:sr=(sr&~1)|(registers[i]>>31)
            registers[i]=(registers[i]<<shift)&MASK
        elif mnemonic in ['bt','bf']:
            if bool(sr&1)==(mnemonic=='bt'):nxt=(labels[arg]&0x1fffffff)|region(pc)
        elif mnemonic=='bra':branch=(labels[arg]&0x1fffffff)|region(pc)
        elif mnemonic=='jmp':branch=registers[rn(arg[1:])]
        elif mnemonic=='rts':branch=0x8cfff000
        else:raise AssertionError(('unsupported source instruction',line))
        if delayed:
            assert branch is None;pc=pending;pending=None
        else:pc=nxt;pending=branch
        steps+=1
    assert sr==original_sr and registers[8:]==saved[8:],'SR/ABI changed'
    assert reads==writes==expected,'array coverage/order changed'
    assert tags==[x&0x1ffffc01 if i in expected else x for i,x in enumerate(original_tags)]
    return [counts[state+i*4] for i in range(16)]


class Diagnostic(unittest.TestCase):
    def test_default_off_is_exact_helper(self):
        self.assertEqual(hashlib.sha256(BASE.encode()).hexdigest(),diag.BASE_HELPER_SHA256)
        self.assertEqual(diag.instrument(BASE),BASE)
        self.assertEqual(diag.instrument(BASE,False),BASE)
        # All original instructions/data remain in identical order; only two insertions + literals.
        code=diag.instrument(BASE,True).replace(diag.BEGIN,'').replace(diag.end(),'').replace(diag.LITERALS,'')
        self.assertEqual(code,BASE)
        with self.assertRaises(ValueError):diag.instrument(BASE+'\n',True)
    def test_actual_generated_helper_modes(self):
        for base in [0x8c010000,0x8c15ffc0,0x8c6fd824]:
            for sr in [0x40000000,0x40000001,0x400000f0,0x700000f1]:
                for ora in [False,True]:
                    x=helper(diag.instrument(BASE,True),ora=ora,base=base,initial_sr=sr)
                    self.assertEqual(x[:8],[1,1,0,0,100,0,100,0])
                    self.assertEqual(x[8:10],[0,1] if ora else [1,0])
    def test_unavailable_and_rejected_clocks(self):
        cases=[({'start':diag.TMU2_RELOAD+1},3),({'end':diag.TMU2_RELOAD+1},3),({'start_tstr':0},3),({'end_tstr':0},3),({'start_reload':1},3),({'end_reload':1},3),({'start_tcr':33},3),({'end_tcr':33},3),({'start_tcr':0x120},2),({'end_tcr':0x120},2),({'start':5,'end':diag.TMU2_RELOAD},2),({'start_tcr':0x120,'end_tcr':32},2)]
        for clock,index in cases:
            x=helper(diag.instrument(BASE,True),clock)
            self.assertEqual(x[0],1);self.assertEqual(x[1],0);self.assertEqual(x[index],1)
            self.assertEqual(x[4:7],[0,0,0])
    def test_overflow_and_carry(self):
        x=helper(diag.instrument(BASE,True),{'start':100,'end':90},{0:MASK,4:MASK,16:MASK-3,20:1,24:200,32:MASK})
        self.assertEqual(x[:10],[0,0,0,0,6,2,200,35,0,0])
        x=helper(diag.instrument(BASE,True),{'start':100,'end':90},{16:MASK-3,20:MASK})
        self.assertEqual(x[4:8],[6,0,10,16])
        for idx,bit,clock in [(8,4,{'end_tcr':0x120}),(12,8,{'end_tstr':0})]:
            x=helper(diag.instrument(BASE,True),clock,{idx:MASK});self.assertEqual(x[idx//4],0);self.assertEqual(x[7],bit)
    def test_negative_assembly_mutations(self):
        code=diag.instrument(BASE,True)
        for changed in [code.replace('.long 0xa0000000','.long 0x80000000'),code.replace('    ldc r0,sr\n',''),code.replace('    or r0,r4\n',''),code.replace(diag.end(),'').replace('    mov.l .Lccr,r0\n',diag.end()+'    mov.l .Lccr,r0\n')]:
            with self.assertRaises(AssertionError):helper(changed)
        # A missing UNF check falsely times a crossing; the expected classification rejects it.
        broken=code.replace('.long 0x100\n','.long 0\n')
        self.assertEqual(helper(broken,{'end_tcr':0x120})[1],1)
        self.assertEqual(helper(code,{'end_tcr':0x120})[2],1)
    def test_ui_default_off_source_identity(self):
        current=(GAME/'ui_bridge.cpp').read_text()
        stripped=re.sub(r'#if defined\(RE4DC_KOS_CACHE_P2_DIAG\) && RE4DC_KOS_CACHE_P2_DIAG\n.*?#endif\n','',current,flags=re.S)
        old=subprocess.check_output(['git','show','933936ea7f45ba81c09277a780ed00111407aa23:port/dreamcast/game/ui_bridge.cpp'],cwd=GAME,text=True)
        self.assertEqual(stripped,old)
        self.assertEqual(current.count('re4dc_cache_p2_diag_'),3)
    def test_make_guards_and_off_object_list(self):
        make='OBJDIR := /tmp/never-build-audits\nKOS_BASE := /root/work/kos-re4dc-d367\nTARGET := dummy\nPLATFORM_OBJS := /tmp/never-build-audits/platform/wanted.o /tmp/never-build-audits/platform/kos_cache_p2_diag.o\nOBJS = $(PLATFORM_OBJS)\ninclude '+str(GAME/'kos_cache_p2.mk')+'\nprint:\n\t@echo OBJS=$(OBJS)\n'
        for p2,diag_on,ok in [(0,0,True),(1,0,True),(0,1,False),(1,1,True),(1,2,False),(1,'0 1',False),(1,'1 0',False),(1,'%',False),(1,'',False)]:
            p=subprocess.run(['make','-s','-f','-','print',f'KOS_CACHE_P2={p2}',f'KOS_CACHE_P2_DIAG={diag_on}'],input=make,text=True,capture_output=True)
            self.assertEqual(p.returncode==0,ok,p.stderr)
            if ok:self.assertEqual('platform/kos_cache_p2_diag.o' in p.stdout,bool(diag_on))
    def test_pinned_timer_sources_fail_closed(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
            k=Path(d)
            for name in diag.TIMER_INPUTS:
                p=k/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((Path('/root/work/kos-re4dc-d367')/name).read_bytes())
            diag.validate_timer(k)
            (k/next(iter(diag.TIMER_INPUTS))).write_text('changed')
            with self.assertRaises(ValueError):diag.validate_timer(k)
    def test_actual_build_local_preparation(self):
        from prepare import prepare
        with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
            d=Path(d);kos=Path('/root/work/kos-re4dc-d367')
            for enabled in [False,True]:
                out=d/str(int(enabled));receipt=prepare(kos,out,PATCH,enabled)
                source=(out/'tree/kernel/arch/dreamcast/kernel/cache_p2.S').read_text()
                self.assertEqual(source,diag.instrument(BASE,enabled))
                self.assertEqual('diagnostics' in receipt,enabled)
    def test_actual_cpp_observer(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
            d=Path(d);(d/'kos').mkdir();(d/'kos/irq.h').write_text('extern unsigned irq_disable();\nextern void irq_restore(unsigned);\n')
            (d/'kos/cache.h').write_text('#include <cstdint>\n#include <cstddef>\nvoid dcache_wback_range(uintptr_t,size_t);\n')
            test=r"""
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>
unsigned irq_state=0;
unsigned irq_disable(){unsigned old=irq_state;irq_state=0x100000f0;return old;}
void irq_restore(unsigned x){irq_state=x;}
std::vector<std::string> logs;
unsigned flushes=0;bool startup_dirty=true;
unsigned p1_cached_bss[16]{}; // logical cached startup zeros, separate from physical P2 state
extern "C" void re4dc_log(const char* f,...){assert(!irq_state);char b[256];va_list a;va_start(a,f);int n=vsnprintf(b,sizeof(b),f,a);va_end(a);assert(n>0 && n<256);logs.emplace_back(b);}
#define RE4DC_KOS_CACHE_P2_DIAG 1
#define RE4DC_CACHE_DIAG_HOST_TEST 1
#include "OBSERVER"
void dcache_wback_range(uintptr_t address,size_t bytes){
 assert(irq_state==0x100000f0 && bytes==64 && !(address&31));
 assert(address==uintptr_t(&re4dc_cache_p2_diag_counters));++flushes;
 if(startup_dirty){auto* p=(volatile unsigned*)address;for(unsigned i=0;i<16;i++)p[i]=p1_cached_bss[i];}
 startup_dirty=false;
}
void seed(unsigned calls){re4dc_cache_p2_diag_counters.calls=calls;re4dc_cache_p2_diag_counters.timed=calls;re4dc_cache_p2_diag_counters.full512=calls;}
int main(int argc,char**argv){
 const bool cold=argc>1 && argv[1][0]=='c';
 if(cold){
  auto* p=(volatile unsigned*)&re4dc_cache_p2_diag_counters;for(unsigned i=0;i<16;i++)p[i]=0xffffffff;
  re4dc_cache_p2_diag_enter(0x100);assert(logs[0].find("calls=0 timed=0")!=std::string::npos);logs.clear();
 }else startup_dirty=false; // A prior whole helper cleaned P1 and wrote real P2 counts.
 seed(3);re4dc_cache_p2_diag_enter(0x101);assert(logs.size()==2);
 assert(logs[0].find(cold?"room=0100 phase=live":"room=ffff phase=boot")!=std::string::npos);
 assert(logs[0].find("calls=3 timed=3")!=std::string::npos && flushes==1);
 seed(7);re4dc_cache_p2_diag_poll(0x101,149);assert(logs.size()==2 && re4dc_cache_p2_diag_counters.calls==7);
 re4dc_cache_p2_diag_poll(0x101,150);assert(logs.size()==4 && logs[2].find("room=0101 phase=live")!=std::string::npos);assert(logs[3].find("capacity=00000000:0001c000")!=std::string::npos);
 seed(2);re4dc_cache_p2_diag_leave(0x101);seed(4);re4dc_cache_p2_diag_enter(0x103);assert(logs[6].find("room=ffff phase=transition")!=std::string::npos);
 seed(9);irq_state=0x100000f0;unsigned before=logs.size();re4dc_cache_p2_diag_enter(0x104);assert(logs.size()==before && re4dc_cache_p2_diag_counters.calls==9);irq_state=0;re4dc_cache_p2_diag_poll(0x103,150);assert(logs[before].find("hook_reject=1")!=std::string::npos);
 auto* p=(volatile unsigned*)&re4dc_cache_p2_diag_counters;for(unsigned i=0;i<16;i++)p[i]=0xffffffff;
 re4dc_cache_p2_diag_poll(0x103,300);assert(logs.back().size()<256);
 re4dc_cache_p2_diag_poll(0x105,450);assert(logs[logs.size()-2].find("hook_reject=2")!=std::string::npos);
}
""".replace('OBSERVER',str(GAME/'platform/kos_cache_p2_diag.cpp'))
            (d/'test.cpp').write_text(test)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-I',str(d),str(d/'test.cpp'),'-o',str(d/'test')],check=True)
            for mode in ['cold','warm']:subprocess.run([str(d/'test'),mode],check=True)
            observer=GAME/'platform/kos_cache_p2_diag.cpp'
            broken=observer.read_text().replace('        dcache_wback_range(reinterpret_cast<uintptr_t>(&re4dc_cache_p2_diag_counters),\n                           sizeof(re4dc_cache_p2_diag_counters));\n','')
            self.assertNotEqual(broken,observer.read_text())
            (d/'broken.cpp').write_text(broken)
            (d/'broken-test.cpp').write_text(test.replace(str(observer),str(d/'broken.cpp')))
            subprocess.run(['g++','-std=c++17','-O2','-I',str(d),'-I',str(GAME/'platform'),str(d/'broken-test.cpp'),'-o',str(d/'broken-test')],check=True)
            def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
            failed=subprocess.run([str(d/'broken-test'),'cold'],capture_output=True,cwd=d,preexec_fn=no_core)
            self.assertNotEqual(failed.returncode,0,'missing first-writeback mutation falsely passed cold stale-RAM control')

if __name__=='__main__':unittest.main(verbosity=2)
