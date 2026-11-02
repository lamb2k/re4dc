#!/usr/bin/env python3
"""Compile the actual new predicate and source shadow selector against controlled light state.

Checks the useful safety relation: an empty result never removes a source receive pass.
Kind/frustum are deliberately unproved by the predicate: those cases remain conservative.
No private assets, target stubs, or emulation required. The source selector's manager writes
are instrumented so the new predicate must stay read-only.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def function(path, signature):
    s = path.read_text()
    start = s.index(signature)
    at = s.index('{', start)
    depth = 0
    for end in range(at, len(s)):
        depth += (s[end] == '{') - (s[end] == '}')
        if not depth:
            return s[start:end + 1]
    raise AssertionError('unterminated function')


def main():
    native = ROOT / 'port/dreamcast/game/coarse_actor_transaction.inc'
    source = ROOT / 'src/game/shadow.cpp'
    code = r'''
#include <cstdint>
#include <cassert>
#include <cstdio>
using u8=uint8_t; using u32=uint32_t;
struct ShadowLightWork { int mode; };
struct cLight { unsigned be_flag; int Type,xD; unsigned xF,Kind; void* work; };
struct cModel { unsigned id; struct { unsigned EnableMask,SelectMask; } LightInfo; };
struct Re4dcActorPlan { unsigned appearance; };
struct ShadowMng { cLight* pLight; cModel* pModel[8]; unsigned num; };
static bool kind_on=true,in_frustum=true;
static unsigned manager_writes=0;
struct { unsigned nArray=0,size=sizeof(cLight); void* pArray=nullptr;
 int checkKind(unsigned)const{return kind_on;} } LightMgr;
struct Log { void err(int,int,const char*,...){assert(false);} } logger;
Log* pLog=&logger;
cModel* pPL=nullptr;
void make_fix_light(ShadowMng*){}
int shadowChkInFrustum(ShadowMng*,cModel*){return in_frustum;}
ShadowMng* getShadowMng(){static ShadowMng out{};out={};++manager_writes;return &out;}
'''
    code += function(source, 'ShadowMng* GetCastShadowMngPtr(cModel* m)') + '\n'
    code += function(native, 'int actor_shadow_candidates(const cModel* m)') + '\n'
    code += function(native, 'bool actor_shadow_empty_leon(cModel* m,const Re4dcActorPlan& p)') + '\n'
    code += r'''
int main(){
 cLight lights[1025]{};ShadowLightWork work{};cModel model{},other{};
 pPL=&model;model.LightInfo.EnableMask=1;Re4dcActorPlan plan{0x108};
 unsigned cases=0;
 for(unsigned idx: {0u,31u,32u})for(unsigned flags=0;flags<4;++flags)
 for(int type: {0,4})for(int mode=0;mode<=5;++mode)for(int dimension: {1,2})
 for(unsigned enable: {0u,1u})for(unsigned selected: {0u,1u})
 for(unsigned kind: {0u,1u})for(unsigned frustum: {0u,1u}){
  for(auto& l:lights)l={};
  work.mode=mode;lights[idx]={flags,type,dimension,enable,0,&work};
  LightMgr.nArray=idx+1;LightMgr.pArray=lights;LightMgr.size=sizeof(cLight);
  model.LightInfo.SelectMask=selected?(idx<32?1u<<idx:0u):0;
  kind_on=kind;in_frustum=frustum;manager_writes=0;
  int count=actor_shadow_candidates(&model);assert(manager_writes==0);
  bool empty=actor_shadow_empty_leon(&model,plan);assert(manager_writes==0);
  ShadowMng* projected=GetCastShadowMngPtr(&model);
  assert(!empty || !projected);assert(!projected || count>0);
  if(idx>=32 && flags==3 && type==4 && mode>=1 && mode<=4 && dimension==2 && enable)
   assert(count==1); // source mask only covers indices0..31
  ++cases;
 }
 LightMgr.nArray=0;LightMgr.pArray=nullptr;assert(actor_shadow_empty_leon(&model,plan));
 plan.appearance=0x100;assert(actor_shadow_empty_leon(&model,plan));
 plan.appearance=0x108;assert(!actor_shadow_empty_leon(&other,plan));
 plan.appearance=0x200;assert(!actor_shadow_empty_leon(&model,plan));plan.appearance=0x108;
 model.id=1;assert(!actor_shadow_empty_leon(&model,plan));model.id=0;
 LightMgr.nArray=1;assert(actor_shadow_candidates(&model)<0);
 LightMgr.pArray=lights;LightMgr.size=sizeof(cLight)+1;assert(actor_shadow_candidates(&model)<0);
 LightMgr.size=sizeof(cLight);LightMgr.nArray=1025;assert(actor_shadow_candidates(&model)<0);
 LightMgr.nArray=1;model.LightInfo.SelectMask=1;lights[0]={3,4,2,1,0,nullptr};
 assert(actor_shadow_candidates(&model)<0);assert(!actor_shadow_empty_leon(&model,plan));
 assert(actor_shadow_candidates(nullptr)<0);
 std::printf("PASS %u source-selector states; empty never removes projection; invalid/foreign roles fail closed\n",cases);
}
'''
    with tempfile.TemporaryDirectory(prefix='re4dc-shadow-empty-') as d:
        p = Path(d)
        (p / 'test.cpp').write_text('#include <initializer_list>\n' + code)
        subprocess.run(['c++', '-std=c++17', '-O2', '-Wall', '-Wextra', str(p / 'test.cpp'), '-o', str(p / 'test')], check=True)
        subprocess.run([str(p / 'test')], check=True)


if __name__ == '__main__':
    main()
