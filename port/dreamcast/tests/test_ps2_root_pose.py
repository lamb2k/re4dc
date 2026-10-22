"""Compile the actual guarded dyn adapter and affine helpers under sanitizers."""
from pathlib import Path
import shutil,subprocess,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('g++'),'host compiler required')
class RootPose(unittest.TestCase):
 def test_native_adapter(self):
  source=(ROOT/'game/platform/native_static.cpp').read_text()
  helpers=source[source.index('void concat(const float*'):source.index('// Combined screen matrix',source.index('bool inverse(const float*'))]
  state=source[source.index('namespace dyn {'):];state=state[:state.index('\n}\n#endif\n#if defined(RE4DC_ENEMY_VIS_CULL)')+2]
  functions=source[source.index('extern "C" void re4dc_ps2_dyn_bind('):];functions=functions[:functions.index('\n#endif\n#endif\n#if RE4DC_PS2_WORLD_ROOMS')]+'\n#endif\n'
  intact=source[source.index('extern "C" int re4dc_ps2_placements_intact('):];intact=intact[:intact.index('\n}\n#endif\nstd::uint32_t ps2_crc32')+2]
  preamble=r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cstddef>
#include <limits>
#define RE4DC_PS2_WORLD_PARTS 1
#define RE4DC_PS2_WORLD_DYNAMIC 1
#define RE4DC_PS2_WORLD_ROOT_POSE 1
#define RE4DC_PS2_WORLD_LEAN 1
namespace lean {constexpr unsigned kMode=16;struct{unsigned dyn_fast;}st;}
static unsigned frame_no,allocations;static bool fail_alloc;
unsigned re4dc_ui_frame(){return frame_no;}
void* re4dc_static_alloc(unsigned n){if(fail_alloc)return nullptr;++allocations;return std::calloc(1,n);}
void re4dc_static_free(void* p){assert(p && allocations);--allocations;std::free(p);}
int re4dc_static_heap_free(){return 100000;}
void re4dc_log(const char*,...){}
struct {unsigned room=0x104;}ps2w;
'''
  cases=r'''
struct Part{Part* next=nullptr;float pose[9]={};float mat[12]={1,0,0,0,0,1,0,0,0,0,1,0};};
struct Object{unsigned flag=7,serial=10;float mat[12]={1,0,0,0,0,1,0,0,0,0,1,0};};
void near(float a,float b){assert(std::fabs(a-b)<0.002f);}
void point(const float* m,const float* p,float* out){for(unsigned r=0;r<3;++r)out[r]=m[4*r]*p[0]+m[4*r+1]*p[1]+m[4*r+2]*p[2]+m[4*r+3];}
void setup(){dyn::reset();dyn::nslots=2;dyn::slots=(dyn::Slot*)re4dc_static_alloc(2*sizeof(dyn::Slot));static unsigned char ids[2]={5,7};dyn::ids=ids;dyn::nids=2;dyn::slot_of[5]=0;dyn::slot_of[7]=1;}
void bind(unsigned id,Object& o,Part& p,unsigned count=1){re4dc_ps2_dyn_bind(0x104,id,&o,&o.flag,&o.serial,o.mat);re4dc_ps2_dyn_parts(0x104,id,&o,&p,count,offsetof(Part,next),offsetof(Part,pose),offsetof(Part,mat));}
int main(){
 setup();Object o;Part p;float rest[12]={0,0,-2,17,0,3,0,-5,-4,0,0,31};std::memcpy(p.mat,rest,sizeof(rest));
 bind(5,o,p);const unsigned char fields[2]={0,0};assert(re4dc_ps2_placements_intact(0x104,fields,1));assert(dyn::query(5)==0);assert(!re4dc_ps2_dyn_source(0x104,&o,10));
 // A root moving away from its captured bind world needs the PS2 mesh, not source BINs.
 float current[12]={2,0,0,-30,0,-5,0,40,0,0,3,50};std::memcpy(p.mat,current,sizeof(current));p.pose[4]=1.2f;++frame_no;
 assert(dyn::query(5)==2);assert(!re4dc_ps2_placements_intact(0x104,fields,1));assert(!re4dc_ps2_dyn_source(0x104,&o,10));
 float local[3]={2,-3,5},baked[3],actual[3],expected[3];point(rest,local,baked);point(dyn::delta[dyn::moved_of[5]],baked,actual);point(current,local,expected);for(unsigned k=0;k<3;++k)near(actual[k],expected[k]);
 // Returning to the bind pose returns to the PS2 baked placement.
 std::memcpy(p.mat,rest,sizeof(rest));++frame_no;assert(dyn::query(5)==0);
 // Simultaneous object and local-root motion is already included in root world.
 float object_before[12]={1,0,0,100,0,1,0,-20,0,0,1,30};
 float child_before[12]={1,0,0,3,0,1,0,4,0,0,1,5};
 float object_after[12]={0,-1,0,40,1,0,0,50,0,0,1,-60};
 float child_after[12]={0,0,1,7,0,1,0,8,-1,0,0,9};
 std::memcpy(o.mat,object_before,sizeof(o.mat));concat(o.mat,child_before,p.mat);bind(5,o,p);
 point(p.mat,local,baked);assert(dyn::query(5)==0);
 std::memcpy(o.mat,object_after,sizeof(o.mat));concat(o.mat,child_after,p.mat);++frame_no;
 assert(dyn::query(5)==2);point(dyn::delta[dyn::moved_of[5]],baked,actual);point(p.mat,local,expected);
 for(unsigned k=0;k<3;++k)near(actual[k],expected[k]);
 // Visibility and owner serial are checked before touching borrowed parts.
 o.flag=1;++frame_no;assert(dyn::query(5)==1);assert(!re4dc_ps2_placements_intact(0x104,fields,1));o.flag=3;++frame_no;assert(dyn::query(5)==1);o.flag=7;
 o.serial=11;++frame_no;assert(dyn::query(5)==1);assert(!re4dc_ps2_placements_intact(0x104,fields,1));assert(!re4dc_ps2_dyn_source(0x104,&o,11));
 // Rebinding captures the new rest and does not retain last owner's pose.
 bind(5,o,p);assert(dyn::query(5)==0);p.mat[3]+=7;++frame_no;assert(dyn::query(5)==2);
 assert(!re4dc_ps2_dyn_source(0x105,&o,11));assert(!re4dc_ps2_dyn_source(0x104,&p,11));
 // Pool-address reuse under a second id cannot return a stale binding.
 ++o.serial;bind(7,o,p);++frame_no;p.mat[7]+=9;assert(dyn::query(5)==1);assert(dyn::query(7)==2);assert(!re4dc_ps2_dyn_source(0x104,&o,12));
 // NaN, singular bind, unavailable witness, and exhausted delta storage hide.
 p.mat[0]=std::numeric_limits<float>::quiet_NaN();++frame_no;assert(dyn::query(7)==1);
 p.mat[0]=0;p.mat[1]=0;p.mat[2]=0;bind(7,o,p);++frame_no;assert(dyn::query(7)==1);
 p=Part();bind(7,o,p);p.mat[3]+=1;++frame_no;dyn::frame=frame_no;dyn::nmoved=dyn::kMoved;std::memset(dyn::state,0,sizeof(dyn::state));assert(dyn::query(7)==1);
 ++o.serial;re4dc_ps2_dyn_bind(0x104,7,&o,&o.flag,&o.serial,o.mat);fail_alloc=true;re4dc_ps2_dyn_parts(0x104,7,&o,&p,1,offsetof(Part,next),offsetof(Part,pose),offsetof(Part,mat));fail_alloc=false;++frame_no;assert(dyn::query(7)==1);
 // A short chain refuses its allocation; the existing multi-bone path is unchanged.
 Part tail; p.next=&tail;bind(7,o,p,2);tail.pose[0]=3;++frame_no;assert(re4dc_ps2_dyn_source(0x104,&o,o.serial));assert(dyn::query(7)==3);
 tail.pose[0]=0;++frame_no;assert(dyn::query(7)==3);
 bind(7,o,tail,2);assert(dyn::slots[1].parts==nullptr);
 dyn::reset();assert(!allocations && !dyn::nobjects && !dyn::ids);
}
'''
  with tempfile.TemporaryDirectory() as temp:
   cpp=Path(temp)/'test.cpp';exe=Path(temp)/'test';cpp.write_text(preamble+helpers+state+functions+intact+cases)
   subprocess.run(['g++','-std=c++17','-O1','-fsanitize=address,undefined',str(cpp),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)

if __name__=='__main__':unittest.main()
