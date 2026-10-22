#!/usr/bin/env python3
from pathlib import Path
import re,subprocess,tempfile,json,hashlib,argparse
parser=argparse.ArgumentParser(description='Check deferred OR/Goto ordering against the original setter')
parser.add_argument('--root',type=Path);parser.add_argument('--evidence',type=Path);args=parser.parse_args()
T=args.root or Path(__file__).resolve().parents[5];G=args.evidence
if G:G.mkdir(parents=True,exist_ok=True)
p=T/'src/em10/em10.cpp';s=p.read_text();a=s.index('void cEm10::setGoto(Vec* pos, int range)');b=s.index('\n// Sends the Ganado to the switch',a);body=s[a:b]
host=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
using u32=uint32_t;using f32=float;
struct Vec {float x,y,z;};
struct Em10Work {u32 flags;int Goto_mode;Vec x5F0,Goto_pos;};
struct cEm10 {u32 flag;Em10Work work;void setGoto(Vec*,int);};
#define EM10_WK(e) (&((e)->work))
struct Floor {bool missing=false;int calls=0;float getFloor(Vec* v,float a,float b,int c,int d){assert(a==600&&b==100000&&c==0&&d==0);calls++;return missing?-100000:v->x-v->z;}} SatMgr;
'''
tests=r'''
static bool eq(Vec a,Vec b){return a.x==b.x&&a.y==b.y&&a.z==b.z;}
static bool eq(cEm10 a,cEm10 b){return a.flag==b.flag&&a.work.flags==b.work.flags&&a.work.Goto_mode==b.work.Goto_mode&&eq(a.work.x5F0,b.work.x5F0)&&eq(a.work.Goto_pos,b.work.Goto_pos);}
int main(){int cases=0,counterexamples=0;
 for(int base=0;base<2;base++)for(int bits=0;bits<8;bits++)for(int floor=0;floor<2;floor++)for(int seq=0;seq<256;seq++){
  SatMgr.missing=floor;
  cEm10 initial{u32(0x100|(base?0x40:0)),{u32(((bits&1)?0x100:0)|((bits&2)?0x4000:0)|((bits&4)?0x800000:0)),7,{1,2,3},{4,5,6}}};
  cEm10 original=initial,reduced=initial,bad=initial;u32 pending=0,first=0,last=0;bool valid=false;Vec target{};int mode=0,n=seq;
  for(int i=0;i<4;i++,n>>=2){int op=n&3;if(op<2){u32 f=op?0x40:0x20;original.flag|=f;pending|=f;}else{Vec v{float(i*100+7),float(i*10+20),float(i*3-9)};int m=op==2?13:0;original.setGoto(&v,m);if(!valid)first=pending;last=pending;valid=true;target=v;mode=m;}}
  if(valid){reduced.flag|=first;reduced.setGoto(&target,mode);bad.flag|=last;bad.setGoto(&target,mode);}
  reduced.flag|=pending;bad.flag|=pending;
  assert(eq(original,reduced));if(!eq(original,bad))counterexamples++;cases++;
 }
 assert(counterexamples>0);printf("original setter reduction: %d sequences PASS; last-snapshot counterexamples=%d\n",cases,counterexamples);
}
'''
source=host+body+tests
with tempfile.TemporaryDirectory(prefix='castle-goto-order-')as d:
 cpp=Path(d)/'original.cpp';exe=Path(d)/'check';cpp.write_text(source)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(cpp),'-o',str(exe)],check=True)
 r=subprocess.run([str(exe)],check=True,text=True,capture_output=True)
 if G:(G/'original-setter-order-test.cpp').write_text(source)
 report={'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'extracted_setter_sha256':hashlib.sha256(body.encode()).hexdigest(),'host_cpp_sha256':hashlib.sha256(source.encode()).hexdigest(),'result':r.stdout.strip(),'scope':'proposed OR/Goto reduction against the original setter; queue implementation is not yet written','coverage':['base flag40 absent/present','work100,4000,800000 combinations','floor found/missing','all length4 OR20/OR40/Goto13/Goto0 sequences','negative last-Goto snapshot counterexamples']}
 if G:(G/'original-setter-order-test.json').write_text(json.dumps(report,indent=2)+'\n')
 print(r.stdout)
