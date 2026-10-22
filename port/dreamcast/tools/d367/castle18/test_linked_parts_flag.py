#!/usr/bin/env python3
"""Compile the actual source allocation/index functions against a fragmented pool."""
from pathlib import Path
import subprocess,tempfile
T=Path(__file__).resolve().parents[5]
s=(T/'src/game/model.cpp').read_text()
def function(start):
 a=s.index(start);b=s.index('{',a);depth=1;i=b+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
alloc=function('int cModel::makePartsList(int n)')
lookup=function('RE4_INLINE cModel* cModel::getPartsPtr(int no)')
prefix=r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
using u32=uint32_t;
#define RE4_INLINE
#define PTR_OK(x) ((x)!=nullptr)
struct cParts; struct Pool;
struct Log {void err(int,int,const char*,int){assert(false);}} logInstance;
Log* pLog=&logInstance;
struct cModel {
 u32 be_flag=0; int nParts=0;
 union {cModel* pParts; cParts* pList;};
 Pool* pm=nullptr;
 cModel():pParts(nullptr){}
 cModel* getPartsPtr(int);
 int makePartsList(int);
 void releasePartsList(int){pParts=nullptr;nParts=0;}
};
struct cParts:cModel {unsigned payload[24];};
struct Pool {
 cParts contiguous[6], scattered[12]; bool sequential=true; int next=0,fail=-1;
 cParts* createSequential(u32){return sequential?contiguous:nullptr;}
 cParts* create(){if(next==fail)return nullptr;auto p=&scattered[next*2];++next;p->pList=nullptr;return p;}
};
'''
main=r'''
int main(){
 Pool pool; cModel m; m.pm=&pool;
 // First source allocation establishes the old contiguous promise.
 assert(m.makePartsList(4));assert(m.be_flag&0x2000);
 for(int i=0;i<4;i++)assert(m.getPartsPtr(i)==&pool.contiguous[i]);
 m.releasePartsList(0); // Source release does not retire this promise.
 pool.sequential=false;pool.next=0;
 assert(m.makePartsList(4));
 cModel* linked=&pool.scattered[2];
#if RE4DC_PARTS_LINKED_FLAG
 assert(!(m.be_flag&0x2000));
 assert(m.getPartsPtr(1)==linked);
 assert(m.getPartsPtr(3)==&pool.scattered[6]);
#else
 // Reproduce the bug: linked topology but arithmetic indexing into the gap.
 assert(m.be_flag&0x2000);
 assert(m.getPartsPtr(1)==&pool.scattered[1]);
 assert(m.getPartsPtr(1)!=linked);
#endif
 assert(m.getPartsPtr(-1)==&m);
 // A later real contiguous allocation restores arithmetic indexing.
 m.releasePartsList(0);pool.sequential=true;
 assert(m.makePartsList(3));assert(m.be_flag&0x2000);
 assert(m.getPartsPtr(2)==&pool.contiguous[2]);
 // Partial fallback failure retains the existing release/return contract.
 m.releasePartsList(0);pool.sequential=false;pool.next=0;pool.fail=2;
 assert(m.makePartsList(4)==0);assert(m.pParts==nullptr);
}
'''
with tempfile.TemporaryDirectory(prefix='castle-linked-parts-')as d:
 p=Path(d)/'test.cpp';p.write_text(prefix+lookup+'\n'+alloc+'\n'+main)
 for flag in [0,1]:
  exe=Path(d)/f'test-{flag}'
  subprocess.run(['c++','-std=c++17','-O2','-Wall','-Werror',f'-DRE4DC_PARTS_LINKED_FLAG={flag}',str(p),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
print('Actual allocation/index functions: old stale-flag reproduction + fixed fragmented lookup + contiguous reuse + failure cleanup PASS')
