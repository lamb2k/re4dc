#!/usr/bin/env python3
"""Exercise the actual ReadWepData/ReleaseWepData bodies with synthetic DVD/module backing.

No game assets. This proves source control flow, not target gameplay or physical I/O timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]


def body(text, signature):
    start = text.index(signature)
    begin = text.index('{', start)
    depth, end = 1, begin + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


PREFIX = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <sys/mman.h>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t;
#define RE4DC_GAME 1
#define RE4DC_LEON_HAND_PACK 1
#define BitChk16(f,b) ((f)&(b))
#define BitOn16(f,b) ((f)|=(b))
#define SET_DRS_NAME(name) ((void)0)
#define WEP_DATA_MAX 0x100000u
#define DLL_BSS_MAX 0x10000u
#define HALT() throw std::runtime_error("synthetic DVD failure")
struct OSModuleHeader { u32 bssSize; void(*prolog)(); };
struct ReadModule { u16 id=0,flag=0; void*pArc=nullptr; OSModuleHeader*pModule=nullptr; u32 size=0,bssSize=0; };
struct ReadFile { u16 file,dll; u32 flag; };
struct Global { u8 pl_type=0,weapon_no=0,weapon_type=0,weapon_no_old=0xff; void*pWep=nullptr; } global,*pG=&global;
struct {void*pWepBuf=nullptr;} Game;
struct {u32 heap=0x100000,weapon=0x80000;} re4dc_mem;
ReadModule WepReadModule;
u8 oldWepId;
#if RE4DC_WEAPON_ARCHIVE_REUSE
static u16 wepResidentFile;
#endif
static u8*resident,*overflow;
static void*wepHeap4;
static int reads,links,prologs,unlinks,binds,unbinds,hands,frees;
static bool alloc_fail,read_fail;
static u32 next_need=256;
static u8*last_data;
int re4dc_wep_heap4_failed;
#define WEP_DATA_ADDR resident
struct DvdReadInfo {u32 size[1][2];void*addr[1][2];};
static void prolog(){++prologs;}
static void InitModule(ReadModule*m){++unlinks;*m={};}
static void re4dc_ui_unbind_weapon(){++unbinds;}
static int re4dc_ui_bind_weapon(void*,u32){++binds;return 1;}
static void re4dc_missing(const char*){assert(false);}
static void OSFreeToHeap(int,void*p){assert(p==overflow);++frees;}
static void*wepHeap4Alloc(u32){return alloc_fail?nullptr:overflow;}
static u32 re4dc_dvd_mram_parts(const char*){return next_need;}
static void DLL_Link(OSModuleHeader*,void*){++links;}
static void re4dc_leon_hands_weapon(const char*){++hands;}
static void OSReport(const char*,...){}
static void eprintf(int,int,int,int,const char*,...){}
static void TaskSleep(int){assert(false);}
struct {int handle=4;} Heap[5];
struct {const char*name;} FileTbl[512];
struct Log {void err(int,int,const char*,...){}} log_obj,*pLog=&log_obj;
static int dvd_read(const char*,u8*data,...){
 ++reads;last_data=data;std::memset(data,0,256);
 *reinterpret_cast<u32*>(data+4)=64;
 auto*m=reinterpret_cast<OSModuleHeader*>(data+64);m->bssSize=0;m->prolog=prolog;
 return reads;
}
#define DVD_READ_N dvd_read
struct {int ReadCheckInfo(int,DvdReadInfo*i){
 if(read_fail)return -1;i->size[0][0]=256;i->size[0][1]=0;i->addr[0][0]=last_data;return 1;
}} Dvd;
'''

TESTS = r'''
static int cases;
static void reset(){
 global={};WepReadModule={};oldWepId=0xff;
#if RE4DC_WEAPON_ARCHIVE_REUSE
 wepResidentFile=0;
#endif
 wepHeap4=nullptr;reads=links=prologs=unlinks=binds=unbinds=hands=frees=0;
 next_need=256;alloc_fail=read_fail=false;re4dc_wep_heap4_failed=0;
 Game.pWepBuf=resident;
 for(auto&f:FileTbl)f.name="em/wep02.drs";
}
static void equip(unsigned no,unsigned type=0){
 pG->weapon_no=no;pG->weapon_type=type;ReadWepData(no,type);
}
static void expect_reads(int enabled,int control){
 const int expected=RE4DC_WEAPON_ARCHIVE_REUSE?enabled:control;
 if(reads!=expected)std::fprintf(stderr,"case=%d reads=%d expected=%d\n",cases,reads,expected);
 assert(reads==expected);
}
int main(){
 resident=static_cast<u8*>(mmap(nullptr,0x100000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_32BIT,-1,0));
 overflow=static_cast<u8*>(mmap(nullptr,0x100000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_32BIT,-1,0));
 assert(resident!=MAP_FAILED&&overflow!=MAP_FAILED);
 assert(uintptr_t(resident)<UINT32_MAX&&uintptr_t(overflow)<UINT32_MAX);
 // Same archive requested repeatedly: retain module, effects' source and existing texture bind.
 reset();equip(7);for(int i=0;i<20;++i)equip(2);expect_reads(2,21);
 assert(links==reads&&prologs==reads&&binds==reads&&hands==reads);++cases;
 // Re-equip shared grenade/egg archive: logical identity must follow the requested item.
 reset();equip(7);for(unsigned n:{0x19u,0x16u,0x17u,0x20u}){
  equip(n);assert(pG->weapon_no_old==n);
 }expect_reads(2,5);++cases;
 // One resident weapon is not a multi-archive cache: alternate files still reload.
 reset();equip(2);equip(7);equip(2);expect_reads(3,3);++cases;
 // Explicit release (room/movie/player reset) invalidates same-file reuse.
 reset();equip(2);ReleaseWepData();assert(oldWepId==0xff);equip(2);expect_reads(2,2);++cases;
 // Another character family may use the same mapped number with a different file.
 reset();const auto saved=wep_data_ada[2];wep_data_ada[2]={77,78,0};
 equip(2);pG->pl_type=2;equip(2);expect_reads(2,1);wep_data_ada[2]=saved;++cases;
 // Lost linked state/backing cannot satisfy a cache hit.
 reset();equip(2);WepReadModule.flag=0;equip(2);expect_reads(2,1);++cases;
 reset();equip(2);pG->pWep=nullptr;equip(2);expect_reads(2,1);++cases;
 reset();equip(2);WepReadModule.pArc=nullptr;equip(2);expect_reads(2,1);++cases;
 // A DVD failure must not publish a reusable archive identity.
 reset();read_fail=true;bool caught=false;try{equip(2);}catch(const std::runtime_error&){caught=true;}
 assert(caught);read_fail=false;equip(2);expect_reads(2,1);++cases;
 // Unsupported table entry neither publishes nor destroys the resident key.
 reset();equip(2);const auto saved_empty=wep_data_leon[0];wep_data_leon[0]={0,0,0};
 equip(0);assert(reads==1);equip(2);expect_reads(1,1);wep_data_leon[0]=saved_empty;++cases;
 // Continue semantics: shared archive re-equip publishes the latest logical weapon identity.
 reset();equip(0x19);equip(0x16);
 assert(pG->weapon_no_old==(RE4DC_WEAPON_ARCHIVE_REUSE?pG->weapon_no:0x19));++cases;
#if RE4DC_WEAPON_HEAP4
 // Failed overflow admission cannot leave a valid reuse key; normal retry must really read.
 reset();next_need=0x80001;alloc_fail=true;equip(2);assert(reads==0&&oldWepId==0xff);
 alloc_fail=false;equip(2);assert(reads==1&&wepHeap4==overflow);
 equip(2);expect_reads(1,1);ReleaseWepData();assert(wepHeap4==nullptr&&frees==1);
 equip(2);expect_reads(2,2);++cases;
 // Overflow body after a real switch is retained until an actual release.
 reset();equip(7);next_need=0x80001;equip(2);equip(2);expect_reads(2,3);
 assert(frees==(RE4DC_WEAPON_ARCHIVE_REUSE?0:1));ReleaseWepData();++cases;
#endif
 std::printf("PASS %d actual-source cases reuse=%d heap4=%d\n",cases,RE4DC_WEAPON_ARCHIVE_REUSE,RE4DC_WEAPON_HEAP4);
 munmap(resident,0x100000);munmap(overflow,0x100000);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'src/game/read.cpp'
    text = source.read_text()
    tables = text[text.index('ReadFile wep_data_leon[46]'):text.index('// Loads the weapon module for weapon')]
    functions = '\n'.join(body(text, sig) for sig in ('void ReleaseWepData()\n{', 'void ReadWepData(u32 no, u32 type)\n{'))
    cpp = args.out / 'extracted.cpp'
    cpp.write_text(PREFIX + tables + functions + TESTS)
    outcomes = []
    for reuse in (0, 1):
        for heap in (0, 1):
            exe = args.out / f'weapon-{reuse}-{heap}'
            command = ['g++', '-std=c++17', '-O1', '-g', '-fpermissive', '-fsanitize=address,undefined',
                       '-fno-omit-frame-pointer', '-no-pie', f'-DRE4DC_WEAPON_ARCHIVE_REUSE={reuse}',
                       f'-DRE4DC_WEAPON_HEAP4={heap}', str(cpp), '-o', str(exe)]
            build = subprocess.run(command, text=True, capture_output=True)
            (args.out / f'build-{reuse}-{heap}.txt').write_text(build.stdout + build.stderr)
            build.check_returncode()
            run = subprocess.run([str(exe)], text=True, capture_output=True)
            (args.out / f'run-{reuse}-{heap}.txt').write_text(run.stdout + run.stderr)
            run.check_returncode()
            print(run.stdout, end='')
            outcomes.append({'reuse': reuse, 'heap4': heap, 'result': run.stdout.strip()})
    receipt = {'source': str(source.relative_to(ROOT)), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'scope': 'actual function bodies, synthetic low-address DVD/module/heap backing; no target acceptance',
               'outcomes': outcomes}
    (args.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
