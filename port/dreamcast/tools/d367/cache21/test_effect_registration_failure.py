#!/usr/bin/env python3
"""Characterize unmodified EspDataLoad/Release failure state; no runtime patch."""
import argparse, hashlib, json, pathlib, subprocess
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args()
root=pathlib.Path(a.source);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
src=(root/'src/game/eff_sys.cpp').read_text()
def function(signature):
 start=src.index(signature+'\n{');pos=src.index('{',start);depth=1;end=pos+1
 while depth:
  if src[end]=='{':depth+=1
  elif src[end]=='}':depth-=1
  end+=1
 return src[start:end]
structs=src[src.index('struct EffIdTbl {'):src.index('extern "C" {')]
load=function('int EspDataLoad(u32 addr, u32 owner, int flag)');release=function('int EspDataRelease(u32 owner, int flag, int warn)')
prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
using u8=uint8_t;using u16=uint16_t;using u32=uint32_t;
struct TEXPalette{};struct EspAnmData{};
struct cEspSystem{u8 ownerCnt[0xd3];};static cEspSystem system_data;static cEspSystem* g_pEspSys=&system_data;
static unsigned regs,rels,errors,checks;
#define OWNER_ERR(...) (++errors)
#define OWNER_ERR2(...) (++errors)
#define CHECK(x) do{++checks;assert(x);}while(0)
int espTexRegist(TEXPalette*,EspAnmData*,u8,u32){++regs;return 1;}
int estRegist(void*,void*,u32){++regs;return 1;}
int sstRegist(void*,void*,u32){++regs;return 1;}
int pathRegist(void*,void*,u32){++regs;return 1;}
int efmRegist(void*,void*,void*,void*,u8,u32){++regs;return 1;}
int espTexRelease(u32){++rels;return 1;}int estRelease(u32){++rels;return 1;}
int sstRelease(u32){++rels;return 1;}int pathRelease(u32){++rels;return 1;}int efmRelease(u32){++rels;return 1;}
'''
body=r'''
alignas(16) static u8 blob[1024];
static u32 fixture(u32 version){
 memset(&system_data,0,sizeof system_data);memset(blob,0,sizeof blob);regs=rels=errors=0;
 auto*d=reinterpret_cast<EffData*>(blob);d->version=version;
 d->ofsTexId=d->ofsEstList=d->ofsSstList=d->ofsPathList=d->ofsEfmId=d->ofsTpl=d->ofsAnm=d->ofsEstData=d->ofsSstData=d->ofsPathData=d->ofsEfm=128;
 CHECK(reinterpret_cast<uintptr_t>(blob)<=UINT32_MAX);return static_cast<u32>(reinterpret_cast<uintptr_t>(blob));
}
int main(){
 constexpr u32 owner=0x36;u32 addr=fixture(11);
 CHECK(EspDataLoad(0,owner,0)==0);CHECK(system_data.ownerCnt[owner]==0);CHECK(regs==0);
 addr=fixture(11);CHECK(EspDataLoad(addr,owner,0)==1);CHECK(system_data.ownerCnt[owner]==1);CHECK(regs==3);
 CHECK(EspDataLoad(addr,owner,0)==1);CHECK(system_data.ownerCnt[owner]==2);CHECK(regs==3);
 CHECK(EspDataRelease(owner,1,1)==1);CHECK(system_data.ownerCnt[owner]==1);CHECK(rels==0);
 CHECK(EspDataRelease(owner,1,1)==1);CHECK(system_data.ownerCnt[owner]==0);CHECK(rels==5);
 addr=fixture(10);CHECK(EspDataLoad(addr,owner,0)==0);CHECK(system_data.ownerCnt[owner]==1);CHECK(regs==0);
 reinterpret_cast<EffData*>(blob)->version=11;
 CHECK(EspDataLoad(addr,owner,0)==1);CHECK(system_data.ownerCnt[owner]==2);CHECK(regs==0);
 CHECK(EspDataRelease(owner,1,1)==1);CHECK(system_data.ownerCnt[owner]==1);CHECK(rels==0);
 CHECK(EspDataRelease(owner,1,1)==1);CHECK(system_data.ownerCnt[owner]==0);CHECK(rels==5);
 addr=fixture(10);CHECK(EspDataLoad(addr,owner,0)==0);reinterpret_cast<EffData*>(blob)->version=11;
 CHECK(EspDataLoad(addr,owner,1)==0);CHECK(system_data.ownerCnt[owner]==2);CHECK(regs==0);
 addr=fixture(10);CHECK(EspDataLoad(addr,owner,0)==0);CHECK(EspDataRelease(owner,0,1)==1);
 CHECK(system_data.ownerCnt[owner]==0);reinterpret_cast<EffData*>(blob)->version=11;
 CHECK(EspDataLoad(addr,owner,0)==1);CHECK(regs==3);
 addr=fixture(10);CHECK(EspDataLoad(addr,owner,0)==0);CHECK(EspDataRelease(owner,1,1)==1);
 reinterpret_cast<EffData*>(blob)->version=11;CHECK(EspDataLoad(addr,owner,0)==1);CHECK(regs==3);
 addr=fixture(10);CHECK(EspDataLoad(addr,owner,0)==0);
 for(unsigned i=0;i<300;++i)CHECK(EspDataLoad(addr,owner,0)==1);
 CHECK(system_data.ownerCnt[owner]==200);CHECK(regs==0);
 CHECK(EspDataRelease(owner,0,1)==1);CHECK(system_data.ownerCnt[owner]==0);
 addr=fixture(11);CHECK(EspDataRelease(owner,1,0)==0);CHECK(system_data.ownerCnt[owner]==0);CHECK(rels==0);
 std::printf("PASS %u assertions; bad-version retry falsely succeeds without registration\n",checks);
}
'''
cpp=out/'effect-registration.cpp';exe=out/'effect-registration';cpp.write_text(prefix+structs+load+'\n'+release+body)
cmd=['g++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-pie','-no-pie',str(cpp),'-o',str(exe)]
subprocess.run(cmd,check=True);run=subprocess.run([str(exe)],capture_output=True,text=True);(out/'run.log').write_text(run.stdout+run.stderr)
receipt={'source_head':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'extracted_functions_sha256':hashlib.sha256((load+'\n'+release).encode()).hexdigest(),'functions':['EspDataLoad','EspDataRelease'],'native_source_modified':False,'stubs':'registration/release callees instrumented; actual u8 owner counter; low executable address preserves u32 source pointer ABI','command':cmd,'returncode':run.returncode,'result':run.stdout.strip(),'classification':'CONFIRMED source fault; selected malformed gameplay input and console occurrence unproven; no runtime fix'}
(out/'effect-registration-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));raise SystemExit(run.returncode)