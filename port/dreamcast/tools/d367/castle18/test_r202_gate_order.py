#!/usr/bin/env python3
"""Exercise actual r202 ordering header and Makefile plumbing, not a replacement implementation."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,tempfile
T=Path(__file__).resolve().parents[5]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args()
header=T/'port/dreamcast/game/platform/include'
code=r"""
#include "alive_cap_r202_gate.h"
#include <cassert>
#include <set>
#include <vector>
using S=std::set<unsigned>;
const unsigned ids[]={0x21,0x2a,0x2b,0x2c,0x2e,0x2f,0x31,0x32};
struct Result {S created,held;};
Result start(unsigned room,unsigned mask) {
    S eligible;
    for(unsigned j=0;j<8;j++) if(mask&(1u<<j))eligible.insert(ids[j]);
    Result r;
    // These two source patrols are created by r202 init before the start-list loop.
    for(unsigned no:{0x2cu,0x32u})if(eligible.count(no))r.created.insert(no);
    for(unsigned order=0;order<256;order++) {
        const unsigned no=re4dc_r202_gate::entry(room,order);
        if(!eligible.count(no)||r.created.count(no))continue;
        if(r.created.size()<4)r.created.insert(no);else r.held.insert(no);
    }
    S all=r.created;all.insert(r.held.begin(),r.held.end());
    assert(all==eligible&&r.created.size()<=4);
    for(unsigned no:r.held)assert(!r.created.count(no));
    return r;
}
int main() {
    const unsigned rooms[]={0,0x100,0x101,0x200,0x201,0x203,0x204,0x207,0x208,0x205,0x300,0xffffffffu};
    for(unsigned room:rooms)for(unsigned i=0;i<256;i++)assert(re4dc_r202_gate::entry(room,i)==i);
    S visited;
    for(unsigned i=0;i<256;i++) {
        const unsigned no=re4dc_r202_gate::entry(0x202,i);
        assert(no<256&&visited.insert(no).second);
        if(i!=0x21&&i!=0x2e)assert(no==i);
    }
    assert(visited.size()==256);
    Result old=start(0x201,255),next=start(0x202,255);
    assert(old.created==(S{0x21,0x2a,0x2c,0x32})&&old.held.count(0x2e));
    assert(next.created==(S{0x2a,0x2c,0x2e,0x32}));
    assert(next.held==(S{0x21,0x2b,0x2f,0x31}));
    for(unsigned mask=0;mask<256;mask++) {
        Result r=start(0x202,mask);
        for(unsigned j:{1u,4u})if(mask&(1u<<j))assert(r.created.count(ids[j]));
        start(0x201,mask);
    }
}
"""
with tempfile.TemporaryDirectory(prefix='castle18-r202-order-')as tmp:
 d=Path(tmp);(d/'test.cpp').write_text(code);exe=d/'test'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(header),str(d/'test.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
 make=(T/'port/dreamcast/game/Makefile').read_text()
 block=re.search(r'# ALIVE_CAP_R202_GATE_BEGIN.*?# ALIVE_CAP_R202_GATE_END\n',make,re.S).group()
 (d/'makefile').write_text("ALIVE_CAP ?= 4\nOBJDIR := obj\n"+block+"\nall: obj/src/game/em_set.o\nobj/src/game/em_set.o:\n\t@printf '%s\\n' '$(GAME_CPPFLAGS)'\n.PHONY: all obj/src/game/em_set.o\n")
 cases=[]
 for args,ok,flag in [([],True,False),(['ALIVE_CAP_R202_GATE=0'],True,False),(['ALIVE_CAP_R202_GATE=1'],True,True),(['ALIVE_CAP_R202_GATE=2'],False,False),(['ALIVE_CAP_R202_GATE='],False,False),(['ALIVE_CAP_R202_GATE=1','ALIVE_CAP=0'],False,False),(['ALIVE_CAP_R202_GATE=1','ALIVE_CAP=6'],False,False)]:
  x=subprocess.run(['make','-s','-f',str(d/'makefile'),'all',*args],text=True,capture_output=True)
  assert (x.returncode==0)==ok,(args,x.stdout,x.stderr)
  if ok:assert ('-DRE4DC_ALIVE_CAP_R202_GATE=1'in x.stdout)==flag
  cases.append({'args':args,'expected_success':ok,'output':x.stdout.strip()or x.stderr.strip()})
 original=subprocess.check_output(['git','show','e2082a65:src/game/em_set.cpp'],cwd=T,text=True)
 current=(T/'src/game/em_set.cpp').read_text()
 include='#if defined(RE4DC_ALIVE_CAP_R202_GATE) && RE4DC_ALIVE_CAP_R202_GATE\n#include "alive_cap_r202_gate.h"\n#endif\n'
 assert include in current;current=current.replace(include,'',1)
 prefix=re.search(r'#if defined\(RE4DC_ALIVE_CAP_R202_GATE\) && RE4DC_ALIVE_CAP_R202_GATE\n    // Keep the original list filters.*?#endif',current,re.S).group()
 current=current.replace(prefix,'    for (i = 0; i < 256; i++) {',1)
 assert current==original,'Default-off creation/eligibility/death/cap body changed'
 proof={'status':'PASS','source_header_sha256':hashlib.sha256((header/'alive_cap_r202_gate.h').read_bytes()).hexdigest(),'permutation_entries':256,'unaffected_rooms_tested':len([0,0x100,0x101,0x200,0x201,0x203,0x204,0x207,0x208,0x205,0x300,0xffffffff]),'eligibility_masks_tested':256,'source_live_plus_held_preserved':True,'source_initial_four_off':['21','2a','2c','32'],'source_initial_four_on':['2a','2c','2e','32'],'source_creation_body_default_off_exact':True,'knob_cases':cases,'limits':'Host order/eligibility/knob invariants, not actual guest cap, script progress, memory or off payload identity acceptance.'}
 if a.out:a.out.write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps(proof,indent=2))
