#!/usr/bin/env python3
"""Exercise the real held-queue functions with a minimal source-state host model."""
from pathlib import Path
import subprocess, tempfile
ROOT = Path(__file__).resolve().parents[5]
SOURCE = (ROOT / 'src/game/em_set.cpp').read_text()
def function(name):
    import re
    m = re.search(r'^(?:static (?:inline )?|extern "C" )?(?:int|void) '+name+r'\([^;]*?\)\n\{', SOURCE, re.M)
    assert m, name
    start, pos, depth = m.start(), m.end(), 1
    while depth:
        depth += (SOURCE[pos] == '{') - (SOURCE[pos] == '}')
        pos += 1
    return SOURCE[start:pos]
HOST = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t;
using f32=float;
struct Vec { float x=0,y=0,z=0; };
struct cEm { int id=0, emset_no=0, active=0, alive=0; Vec pos;
 int isAlive(){return alive;} int checkStatus(int){return active;} };
struct EmListData { int be_flag=0,id=0,room=0; int pos[3]={}; } list[256];
struct Global { int stage_no=2,room_no=5,room_id=0x205; u32 Frame_cnt=0; } global,*pG=&global;
cEm player,*pPL=&player, pool[32]; cEm* errEm=nullptr; cEm* emSetWork(u32 i){return pool+i;}
struct { u32 nArray=32; } EmMgr;
#define EM_LIST(n) (&list[n])
#define EM_STATUS_ACTIVE 1
#define RE4DC_ALIVE_CAP_N 4
#define RE4DC_ALIVE_CAP_LOG 0
#define ALIVE_CAP_FRESH 16
static u8 aliveCapHeld[64],aliveCapSent[64]; static int aliveCapN,aliveCapReleasing;
static u32 aliveCapLast,aliveCapFreshF[16]; static cEm* aliveCapFreshEm[16]; static u8 aliveCapFreshNo[16];
static int aliveCapRoom(){return 1;} static int aliveCapKeep(int){return 0;}
static void EmListSetAlive(int no,int){list[no].be_flag|=1;}
'''
MEMBER = function('aliveCapGanado') + '\n#if NOVIS\n'+function('aliveCapEnemy')+'\n#else\n#define aliveCapEnemy aliveCapGanado\n#endif\n'
CODE = '\n'.join(function(n) for n in ['aliveCapWaitingK','aliveCapPush','aliveCapNoteFresh','aliveCapLive','re4dc_aliveCapHeldEntry','re4dc_aliveCapHeldCount','re4dc_aliveCapDefer'])
SPAWN=r'''
cEm* EmSetFromList2(int no,int) {
 assert(aliveCapLive()<4);
 for(auto& e:pool) if(!e.alive) {e.id=list[no].id;e.emset_no=no;e.alive=1;e.active=1;
 list[no].be_flag|=2;aliveCapNoteFresh(&e,no);return &e;} return nullptr;
}
'''
TEST=r'''
int main(){
 // Stage2-only inclusion; unrelated enemies and all Ganado identities retain policy.
 for(int stage=1;stage<=4;stage++){pG->stage_no=stage;
 for(int id=0;id<256;id++) assert(bool(aliveCapEnemy(id)) ==
 ((id>=0x10&&id<=0x20)||(NOVIS&&stage==2&&id==0x2d)));}
 pG->stage_no=2;
 // Back-to-back creation counts not-yet-ACTIVE enemies, including mixed Novis.
 for(int i=0;i<4;i++){pool[i].id=(i%2&&NOVIS)?0x2d:0x11;pool[i].alive=1;pool[i].emset_no=i;
 aliveCapNoteFresh(pool+i,i);assert(aliveCapLive()==i+1);}
 // Dead/inactive work does not consume a slot once its fresh lease is removed.
 for(int i=0;i<4;i++)pool[i].active=1;
 assert(aliveCapLive()==4);
 list[9]={1,NOVIS?0x2d:0x11,0x205,{0,0,0}};
 list[10]={1,0x11,0x205,{100,0,100}};
 assert(re4dc_aliveCapDefer(9,list[9].id)==1);
 assert(re4dc_aliveCapDefer(9,list[9].id)==1&&aliveCapN==1);
 assert(re4dc_aliveCapDefer(10,list[10].id)==1&&aliveCapN==2);
 assert(list[9].be_flag==1&&list[10].be_flag==1); // never set/dead/deleted
 assert(re4dc_aliveCapHeldEntry(9));
 assert(re4dc_aliveCapHeldCount(0x10,0x20)==(NOVIS?1:2));
 assert(re4dc_aliveCapHeldCount(0x2d,-1)==(NOVIS?1:0));
 pool[0].alive=0;
 // Busy pauses / cooldown preserve both sends; one free slot releases one only.
 pG->Frame_cnt=100;re4dc_aliveCapMove(1);assert(aliveCapN==2);
 re4dc_aliveCapMove(0);assert(aliveCapN==1&&aliveCapLive()==4);
 assert(list[10].be_flag==3); // farthest queued send, original alive bit retained
 pG->Frame_cnt=200;re4dc_aliveCapMove(0);assert(aliveCapN==1); // full
 pool[1].alive=0;re4dc_aliveCapMove(0);assert(aliveCapN==0&&aliveCapLive()==4);
 assert(list[9].be_flag==3&&!re4dc_aliveCapHeldEntry(9));
 puts("mixed fresh/start/send queue and release: PASS");
}
'''
with tempfile.TemporaryDirectory(prefix='castle-cap-host-') as tmp:
    for enabled in [0,1]:
        p=Path(tmp)/f'cap{enabled}.cpp'
        p.write_text(HOST+MEMBER+CODE+SPAWN+function('re4dc_aliveCapMove')+TEST)
        exe=p.with_suffix('')
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',f'-DNOVIS={enabled}',str(p),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
print('Source-extracted cap host checks passed in old and combined modes')
