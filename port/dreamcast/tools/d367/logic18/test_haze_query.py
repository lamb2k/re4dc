#!/usr/bin/env python3
from pathlib import Path
import argparse, subprocess, tempfile
ap=argparse.ArgumentParser(description='Compare source-extracted reference/indexed haze lookup over room IDs and predicate edges.')
ap.add_argument('--source',type=Path,required=True)
args=ap.parse_args()
p=args.source;s=p.read_text();a=s.index('struct Ps2fxHaze {');b=s.index('\n#if RE4DC_PS2_FX_POPULATION\n// PS2 r112',a);body=s[a:b]
head='''#include <cstdint>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
using u32=uint32_t; using u16=uint16_t; using u8=uint8_t; using f32=float;
struct cEsp { int m_Id; struct { int owner; } info; u8 m_Col_start_r,m_Col_start_g,m_Col_start_b; };
static u16 G_ROOM_ID; static int re4dc_ps2fx=1;
#define PS2FX_HAZE 1
#define RE4DC_PS2_FX_ROOMS 1
#define RE4DC_PS2_FX_STAGE1 1
#define RE4DC_PS2_FX_POPULATION 1
#define RE4DC_WATER45_NATIVE 1
'''
tail=r'''
static unsigned long checks;
static void check(Ref::cPs2fxEsp15& a, Opt::cPs2fxEsp15& b) {
 const auto x=Ref::Ps2fxHazeFor(&a);const auto y=Opt::Ps2fxHazeFor(&b);
 int xi=x ? int(x-Ref::kPs2Haze):-1, yi=y ? int(y-Opt::kPs2Haze):-1;
 ++checks; if(xi!=yi) {printf("Mismatch room=%x ref=%d index=%d\n",G_ROOM_ID,xi,yi);exit(1);}
}
int main() {
 Ref::cPs2fxEsp15 a{}; Opt::cPs2fxEsp15 b{};
 a.m_Id=b.m_Id=0x15;a.info.owner=b.info.owner=0xd0;
 for(unsigned r=0;r<65536;r++){G_ROOM_ID=r;check(a,b);}
 for(int ri=0;ri<PS2FX_HAZE_ROOMS;ri++) {
  const auto &h=Ref::kPs2Haze[ri];G_ROOM_ID=h.room;
  float values[]={h.gc_range, h.gc_range+1, h.gc_range-1,std::nextafter(h.gc_range+1,INFINITY),std::nextafter(h.gc_range-1,-INFINITY),0,INFINITY,-INFINITY,NAN};
  for(float v:values) for(int owner:{0,1,0xd0,0xff}) for(int id:{0x15,0x48}) for(int colour=0;colour<4;colour++) for(int frame=0;frame<256;frame++) {
   a.m_Id=b.m_Id=id;a.info.owner=b.info.owner=owner;a.m_Free.Range=b.m_Free.Range=v;
   a.m_Free.Room_del_frame=b.m_Free.Room_del_frame=frame;
   a.m_Col_start_r=b.m_Col_start_r=h.gc_r+(colour==1);
   a.m_Col_start_g=b.m_Col_start_g=h.gc_g+(colour==2);
   a.m_Col_start_b=b.m_Col_start_b=h.gc_b+(colour==3);
   check(a,b);re4dc_ps2fx=0;check(a,b);re4dc_ps2fx=1;
  }
 }
 printf("PASS %lu source-extracted query comparisons; exhaustive room ids, table rows and predicate edges\n",checks);
}
'''
head='#include <initializer_list>\n'+head
tmp=tempfile.TemporaryDirectory(prefix='logic18-haze-');out=Path(tmp.name)/'query.cpp';out.write_text(head+'\n#define RE4DC_FX_HAZE_INDEX 0\nnamespace Ref {\n'+body+'\n}\n#undef RE4DC_FX_HAZE_INDEX\n#define RE4DC_FX_HAZE_INDEX 1\nnamespace Opt {\n'+body+'\n}\n'+tail)
exe=Path(tmp.name)/"query"
subprocess.run(["g++","-O2","-std=c++20",str(out),"-o",str(exe)],check=True)
subprocess.run([str(exe)],check=True)
