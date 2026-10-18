#!/usr/bin/env python3
"""Actual full-source preparation scope + actual Trans loop with the real frame ledger.
Synthetic source objects; no target ABI, visual, or hardware acceptance.
"""
from pathlib import Path
import subprocess, tempfile
ROOT=Path(__file__).resolve().parents[3]
INC=ROOT/'port/dreamcast/game/platform/include'
s=(ROOT/'src/game/trans.cpp').read_text()
start=s.index('    func = emTrans;\n    for (u = EmMgr.pAlive; u != 0;) {')
end=s.index('    }\n#if RE4DC_PACE_CATCHUP >= 2',start)
loop=s[start:end]
assert loop.count('func((cModel*) cur);')==1 and loop.count('SourceActorFullPreparation')==1
code=r"""
#include <cassert>
#include <cstdio>
#include <vector>
#include <sys/mman.h>
#define RE4DC_ACTOR_R300_FULL_SOURCE 1
#define RE4DC_ACTOR_TRANSACTION 1
#define RE4DC_PACE_CHECK 0
#include "coarse_source_frame.h"
using re4dc_source::FrameIdentity;using re4dc_source::ModelIdentity;using re4dc_source::ModelPath;
struct cUnit{cUnit*pNext=nullptr;};struct cModel:cUnit{unsigned serial=0;};
struct Global{unsigned Rno0=3,stage_no=3,room_no=0,System_flg=0xc40,Status_flg[3]{};} global;
Global*pG=&global;cModel*pPL=nullptr;unsigned re4dc_pace_drop_models;
struct Manager{cUnit*pAlive=nullptr;}EmMgr;
re4dc_source::FrameLedger sourceActorLedger;bool sourceActorActive,sourceActorFullPass,identity_ok=true,ram_ok=true;
FrameIdentity current{180,0x300,1,1,1,1};unsigned failures,mode;std::vector<unsigned>calls;
bool sourceActorIdentity(FrameIdentity&out){out=current;return identity_ok;}
bool sourceActorRam(cModel*m){return m && ram_ok;}
ModelIdentity sourceActorModel(cModel*m){return{reinterpret_cast<std::uintptr_t>(m),m->serial,m==pPL?0u:2u};}
void sourceActorFailure(unsigned){++failures;}
void sourceActorRetire(){sourceActorFullPass=false;sourceActorActive=false;sourceActorLedger.retire();}
#include "source_actor_full_transition.inc"
void emTrans(cModel*m){calls.push_back(m->serial);if(calls.size()==1){if(mode==1)++m->serial;if(mode==2)++current.primitive_epoch;if(mode==3)++current.enemy_generation;if(mode==4)identity_ok=false;if(mode==5)sourceActorRetire();}assert(!sourceActorFullReady());}
"""+'\nvoid original_trans_loop(){void(*func)(cModel*);cUnit*u;\n'+loop+'\n}\n'+r"""
int main(){
 cModel models[3];pPL=&models[0];
 for(unsigned bits=0;bits<2048;bits++){
  global={};pPL=&models[0];re4dc_pace_drop_models=bool(bits&4);
  if(bits&8)pPL=nullptr;if(bits&16)global.Rno0=2;if(bits&32)global.stage_no=2;if(bits&64)global.room_no=1;
  if(bits&128)global.System_flg&=~0x400u;if(bits&256)global.System_flg|=0x100000u;if(bits&512)global.Status_flg[2]|=0x04000000u;
  if(bits&1024)global.System_flg|=0x800u; // unrelated source presentation bit is preserved
  assert(sourceActorFullEligible(bits&1,bits&2)==(!(bits&0x17f) && (!(bits&128) || (bits&512))));
 }
 void*page=mmap(nullptr,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);assert(page!=MAP_FAILED);
 for(mode=0;mode<=8;mode++){
  global={};pPL=&models[0];re4dc_pace_drop_models=0;current={180,0x300,1,1,1,1};identity_ok=ram_ok=true;calls.clear();failures=0;
  for(unsigned i=0;i<3;i++){models[i].serial=i+1;models[i].pNext=i<2?&models[i+1]:nullptr;}
  EmMgr.pAlive=&models[0];sourceActorRetire();std::size_t bytes;assert(re4dc_source::FrameLedger::storage_bytes(3,bytes));
  assert(sourceActorLedger.begin(page,bytes,3,current));for(auto&m:models)assert(sourceActorLedger.append(current,sourceActorModel(&m),ModelPath::Source,0));assert(sourceActorLedger.seal(current));sourceActorActive=sourceActorFullPass=true;
  if(mode==6){models[0].pNext=&models[2];} // original walk omits a planned member
  if(mode==7){models[0].pNext=&models[2];models[2].pNext=&models[1];models[1].pNext=nullptr;} // changed original order
  if(mode==8)ram_ok=false;
  assert(!sourceActorFullReady());original_trans_loop();
  assert(calls.size()==(mode==6?2u:3u)); // proof failure never replays or drops an original callback
  if(mode==0){assert(sourceActorFullReady() && !failures);for(auto&m:models)assert(sourceActorLedger.membership(current,sourceActorModel(&m))==re4dc_source::Membership::SourceHandled);}
  else assert(!sourceActorFullReady() && !sourceActorFullPass);
  sourceActorRetire();assert(!mprotect(page,4096,PROT_NONE));assert(!sourceActorFullReady());{SourceActorFullPreparation retired(&models[0]);}assert(!mprotect(page,4096,PROT_READ|PROT_WRITE));
 }
 munmap(page,4096);std::puts("PASS 2048 eligibility states; actual original-loop once/order, serial/frame/generation/retirement/order/missing/invalid failures, retired borrowed-page guard");
}
"""
with tempfile.TemporaryDirectory(prefix='r300-source-owner-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-O1','-I'+str(INC),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
