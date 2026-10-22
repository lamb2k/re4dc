#!/usr/bin/env python3
"""Actual-opcode proof that rejected/clipped input does not even write SQ."""
import argparse,json,sys,struct,hashlib
from pathlib import Path
here=Path(__file__).resolve().parent
caller=(here/'caller_test.py').read_text();defs=caller.split('p=argparse.ArgumentParser(description=__doc__)',1)[0]
namespace={'__file__':str(here/'caller_test.py'),'__doc__':__doc__};exec(compile(defs,str(here/'caller_test.py'),'exec'),namespace)
base=namespace['base'];WalkMachine=namespace['WalkMachine']
class GuardMachine(WalkMachine):
    def __init__(self,*args,**kwargs):self.sq_events=0;super().__init__(*args,**kwargs)
    def write(self,address,value,length):
        if 0xe0000000<=address<0xe0010000:self.sq_events+=1
        super().write(address,value,length)
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--objects',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();assert not a.report.exists()
cache=base.generated_cache([(float(i),float(i%5)) for i in range(256)])
passed=0
for position in (0,1,2,31,32,63):
    for n in (3,32,64,65,119,255):
        pos=min(position,n-1)
        for mode in ('depth-all','screen-all','depth-cross','limit-zero','limit-depth'):
            oc=bytearray(256);limit=255
            if mode=='depth-all':oc[:]=bytes([1])*256
            elif mode=='screen-all':oc[:]=bytes([4])*256
            elif mode=='depth-cross':oc[pos]=1
            elif mode=='limit-zero':limit=n-1
            else:oc[0]=1;limit=n-1
            for trace in (0,1):
                path=a.objects/('walk-trace%d.elf'%trace)
                m=GuardMachine(base.text_section(path),cache,bytes([n])+bytes(range(n)),bytes(oc),limit,2,trace=bool(trace));m.pc=struct.unpack_from('<I',path.read_bytes(),24)[0]
                result=m.run();assert not result[0] and m.sq_events==0,(n,pos,mode,trace,m.sq_events)
                assert m.written==[0,0],(n,pos,mode,trace,m.written)
                passed+=1
result=dict(scope=__doc__,comparisons=passed,no_store_queue_writes_before_reject_or_clip=True,no_partial_uncommitted_bursts=True,sizes=[3,32,64,65,119,255],depth_cross_positions=[0,1,2,31,32,63],caller_source=base.sha((here/'caller_test.py').read_bytes()),interpreter_source=base.sha((here.parent/'backface_sh4_kernel/object_test.py').read_bytes()),files={p.name:base.sha(p.read_bytes()) for p in a.objects.glob('walk-trace*.elf')},limits='Bounded host execution of actual SH4 opcodes; not hardware.')
a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
