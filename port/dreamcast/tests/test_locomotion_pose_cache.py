#!/usr/bin/env python3
"""Exercise the actual bounded cache against the source-extracted evaluator.

Synthetic FCC streams only; no private game data. Target differential mode is
still required because host floating-point and target floating-point differ.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PRELUDE = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cassert>
#include <vector>
#include <limits>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t;
using s8=int8_t; using s16=int16_t; using f32=float;
typedef uint16_t u16_un __attribute__((aligned(1)));
struct Vec { float x,y,z; };
struct HermitePrm { float frame,maxFrame; u32 flags; int type; u8* key; };
struct Log { unsigned errors=0; void err(int,int,const char*,...) { ++errors; } } logObject;
Log* pLog=&logObject;
void unsupported(u8*,int,int,float*,float*) { assert(false); }
using Decoder=void(*)(u8*,int,int,float*,float*);
Decoder hfTbl[16]={unsupported,unsupported,unsupported,unsupported,
 unsupported,unsupported,unsupported,unsupported,unsupported,unsupported,
 unsupported,unsupported,unsupported,unsupported,unsupported,unsupported};
'''
CHECKS = r'''
#include "locomotion_pose_cache.h"
static LocomotionPoseCache cache;
unsigned evaluations=0, comparisons=0;
int evaluate(HermitePrm* p,Vec* o,u16* h) { ++evaluations; return hermiteFast(p,o,h); }
template<class T> void append(std::vector<u8>& b,T v) {
 auto p=reinterpret_cast<u8*>(&v); b.insert(b.end(),p,p+sizeof(v));
}
std::vector<u8> stream(int type) {
 std::vector<u8> b;
 for(int axis=0;axis<3;++axis) {
  append<u16>(b,3); append<u16>(b,0); append<u16>(b,4); append<u16>(b,8);
  for(int j=0;j<3;++j) {
   const int value=130*axis-42*j+7;
   if(type==0) { append<float>(b,value*.1f); append<float>(b,j*.2f); append<float>(b,-j*.3f); }
   else { append<s16>(b,value); if(type==5) { append<s16>(b,j*3); append<s16>(b,-j*4); }
          else { append<s8>(b,j*3); append<s8>(b,-j*4); } }
  }
 }
 return b;
}
void compare(LocomotionPoseCache::Pose* pose,HermitePrm p,const u16* input,bool check=false) {
 Vec a{},b{}; u16 ha[3],hb[3]; memcpy(ha,input,6);memcpy(hb,input,6);
 int ra=hermiteFast(&p,&a,ha);
 int rb=check ? cache.sample<true>(pose,0,&p,&b,hb,evaluate) : cache.sample<false>(pose,0,&p,&b,hb,evaluate);
 assert(ra==rb&&!memcmp(&a,&b,sizeof(a))&&!memcmp(ha,hb,6)); ++comparisons;
}
int main() {
 assert(sizeof(cache)<=32768);
 int roomOwner,clipA,clipB,keysA,keysB;
 u32 tick=1;
 const float frames[]={0,0.25f,1.5f,4,6.25f,7.99f,8};
 for(int type:{0,5,6}) {
  auto bytes=stream(type);
  for(unsigned flags:{0u,1u,2u,4u,5u,6u,8u,9u,12u,13u}) for(float frame:frames)
   for(u16 history=0;history<4;++history) {
    HermitePrm p{frame,12,flags,type,bytes.data()};
    auto pose=cache.begin(tick++,0x101,&roomOwner,&clipA,&keysA,p,64);
    u16 h[]={history,history,history};
    compare(pose,p,h); compare(pose,p,h); compare(pose,p,h,true);
   }
 }
 auto bytes=stream(5); HermitePrm p{1.5f,12,0,5,bytes.data()}; u16 h[3]={};
 auto begin=[&]() { return cache.begin(tick,0x101,&roomOwner,&clipA,&keysA,p,64); };
 auto first=begin(); compare(first,p,h); auto n=evaluations; compare(begin(),p,h); assert(evaluations==n);
 // Same streamed slab, different logical clip: must evaluate again.
 compare(cache.begin(tick,0x101,&roomOwner,&clipB,&keysA,p,64),p,h); assert(evaluations==++n);
 compare(cache.begin(tick,0x101,&roomOwner,&clipA,&keysB,p,64),p,h); assert(evaluations==++n);
 compare(cache.begin(tick,0x103,&roomOwner,&clipA,&keysA,p,64),p,h); assert(evaluations==++n);
 compare(cache.begin(++tick,0x101,&roomOwner,&clipA,&keysA,p,64),p,h); assert(evaluations==++n);
 compare(cache.begin(tick,0x101,&clipB,&clipA,&keysA,p,64),p,h); assert(evaluations==++n);
 first=begin(); compare(first,p,h); n=evaluations;
 ++p.flags; compare(begin(),p,h); assert(evaluations==++n); --p.flags;
 p.frame+=.25f; compare(begin(),p,h); assert(evaluations==++n); p.frame-=.25f;
 p.maxFrame+=1; compare(begin(),p,h); assert(evaluations==++n); p.maxFrame-=1;
 // Replacement and serial wrap cannot expose an older channel.
 for(int i=0;i<16;++i) { p.frame=i*.25f; compare(begin(),p,h); }
 cache.serial=~0u; ++tick; compare(begin(),p,h); compare(begin(),p,h);
 cache.epoch=~0u; ++tick; compare(begin(),p,h); compare(begin(),p,h);
 assert(!cache.begin(tick,0x101,&roomOwner,&clipA,&keysA,p,129));
 assert(!cache.begin(tick,0x101,&roomOwner,&clipA,&keysA,p,0));
 p.frame=11.75f; assert(!LocomotionPoseCache::covered(p));
 p.frame=12; assert(!begin()); compare(nullptr,p,h);
 p.frame=std::numeric_limits<float>::quiet_NaN(); assert(!begin());
 p.frame=1.5f; first=begin(); compare(first,p,h);
 // Check mode detects corruption and serves the reference, never the bad hit.
 first->channels[0].value.x+=1; n=cache.mismatches;
 compare(first,p,h,true); assert(cache.mismatches==n+1);
 assert(cache.hits>500 && logObject.errors>0);
 printf("comparisons=%u hits=%u misses=%u target_storage_limit=32768 host_bytes=%zu corruption_detected=1\n",
        comparisons,cache.hits,cache.misses,sizeof(cache));
}
'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', default='g++')
    args = parser.parse_args()
    motion = (ROOT / 'src/game/motion.cpp').read_text()
    # Host pointers are 64-bit; only the alignment predicate needs adapting.
    evaluator = motion[motion.index('const s8 hfStride[16]'):motion.index('#if defined(RE4DC_HF_REG)')]
    evaluator = evaluator.replace('(u32) d & 1', 'uintptr_t(d) & 1')
    with tempfile.TemporaryDirectory(prefix='lpose-host-') as directory:
        source = Path(directory) / 'test.cpp'
        binary = Path(directory) / 'test'
        source.write_text(PRELUDE + evaluator + CHECKS)
        subprocess.run([args.compiler, '-std=c++11', '-O2', '-ffp-contract=off',
                        '-fno-strict-aliasing', '-fsanitize=address,undefined',
                        '-I', str(ROOT / 'src/game'), str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

if __name__ == '__main__':
    main()
