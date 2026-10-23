#!/usr/bin/env python3
"""Expanded actual SH4 fused-mask, six-phase and actor boundary controls."""
import argparse,sys,random,itertools,json,struct
from pathlib import Path
here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parent/'backface_sh4_kernel'))
import object_test as base
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--objects',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();assert not a.report.exists()
texts=[base.text_section(a.objects/('kernel-trace%d.o'%t)) for t in (0,1)]
# SH's in-place section addends must agree with the real target linker.
for t in (0,1):assert texts[t]==base.text_section(a.objects/('walk-trace%d.elf'%t)),('decoder/linker text mismatch',t)
oracle=base.oracle_load(a.objects/'oracle.so');rng=random.Random(0x64f05ed)
def pattern(t,f):
    ys=[0.,1.]
    for i in range(t):ys.append(2*ys[-1]-ys[-2]+(-1. if (f>>i)&1 else 1.)*(-1. if i&1 else 1.))
    return base.generated_cache(list(enumerate(ys))),bytes(range(t+2))
cases=[]
for f in range(1<<10):
    cache,ix=pattern(10,f)
    for mask,cull in itertools.product((127,255),(1,2)):cases.append((cache,ix,mask,cull,'exhaustive10'))
for t in (1,2,3,4,5,6,7,8,29,30,31,32,33,34,35,59,60,61,62):
    valid=(1<<t)-1;patterns={0,valid,valid//3,(valid//3)*2}
    for i in range(t):
        bit=1<<i;patterns.update((bit,valid^bit))
        for gap in (1,2,3,4):
            m=((1<<gap)-1)<<i;patterns.update((m&valid,valid^(m&valid)))
    for i in range(12):patterns.add(rng.getrandbits(t))
    for f in patterns:
        cache,ix=pattern(t,f)
        for mask in (127,255):cases.append((cache,ix,mask,2,'mask-boundaries'))
# Whole index count exceeds255; parity and gap policy reset at every bit7 EOL.
points=[(float(i),float(i%5)) for i in range(128)]
cache=base.generated_cache(points)
for lengths in ((1,2,3,4,31,32,33,63,64,65,66,127,128,129,255),(64,65,64,3),(1,1,2,2,3,3),(255,64,255)):
    ix=bytearray()
    for n in lengths:
        part=bytearray(i%128 for i in range(n));part[-1]|=128;ix.extend(part)
    for cull in (1,2):cases.append((cache,bytes(ix),383,cull,'whole-short-long-boundaries'))
# Exact caller counts0,1,2,63,64,65,66 and all six phase endings.
for n,mask,cull in itertools.product((0,1,2,3,4,5,6,7,8,9,10,63,64,65,66),(127,255),(1,2)):
    cache=base.generated_cache([(float(i),float((i&1)*2-1)) for i in range(128)])
    cases.append((cache,bytes(range(n)),mask,cull,'index-boundaries'))
counts={};passed=0;steps=0
for cache,ix,mask,cull,kind in cases:
    expected=oracle(cache,ix,mask,cull)
    for trace in (0,1):
        m=base.Machine(texts[trace],cache,ix,mask,cull,trace=bool(trace))
        try:actual=m.run()
        except AssertionError as e:raise AssertionError((kind,len(ix),mask,cull,trace,str(e),list(m.ring))) from e
        assert actual==expected,(kind,len(ix),mask,cull,trace,actual[1],expected[1]);passed+=1;steps=max(steps,m.steps)
    counts[kind]=counts.get(kind,0)+1
result=dict(scope=__doc__,cases=len(cases),comparisons=passed,groups=counts,decoder_internal_relocations_match_actual_linker=True,max_steps=steps,exact_words=True,all_six_phase_endings=True,logical64_crossword_and_parity=True,short_long_eol_boundaries=True,objects={p.name:base.sha(p.read_bytes()) for p in a.objects.glob('*.o')},source=base.sha(Path(__file__).read_bytes()),limits='Host execution of actual target opcodes and unchanged target-lowered C oracle; no guest/hardware or transform saving.')
a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
