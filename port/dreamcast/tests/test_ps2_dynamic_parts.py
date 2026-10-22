"""Exercise the actual scenery-part adapter's owner and lifetime rules on host."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which('g++'), 'host compiler required')
class DynamicParts(unittest.TestCase):
    def test_pose_and_owner_lifetime(self):
        source = (Path(__file__).resolve().parents[1] /
                  'game/platform/native_static.cpp').read_text()
        state = source[source.index('namespace dyn {'):]
        state = state[:state.index('\n}\n#endif\n#if defined(RE4DC_ENEMY_VIS_CULL)') + 2]
        functions = source[source.index('extern "C" void re4dc_ps2_dyn_bind('):]
        functions = functions[:functions.index('\n#endif\n#endif\n#if RE4DC_PS2_WORLD_ROOMS')] + '\n#endif\n'
        preamble = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cstddef>
#define RE4DC_PS2_WORLD_PARTS 1
static unsigned frame_no, allocations;
unsigned re4dc_ui_frame(){return frame_no;}
void* re4dc_static_alloc(unsigned n){++allocations;return std::calloc(1,n);}
void re4dc_static_free(void* p){assert(p && allocations);--allocations;std::free(p);}
int re4dc_static_heap_free(){return 100000;}
void re4dc_log(const char*,...){}
bool inverse(const float*,float*){return false;}
void concat(const float*,const float*,float*){}
struct {unsigned room=0x104;} ps2w;
'''
        cases = r'''
struct Part {Part* next;float pose[9];};
struct Object {unsigned flag,serial;float mat[12];};
int main(){
 dyn::reset();
 dyn::nslots=2;dyn::slots=(dyn::Slot*)re4dc_static_alloc(2*sizeof(dyn::Slot));
 static unsigned char ids[2]={5,7};dyn::ids=ids;dyn::slot_of[5]=0;dyn::slot_of[7]=1;
 Object obj[2]={{3,10,{}},{3,11,{}}};
 Part tail{nullptr,{}},head{&tail,{}};
 auto bind=[&](unsigned id,Object& o,Part* p,unsigned count){
  re4dc_ps2_dyn_bind(0x104,id,&o,&o.flag,&o.serial,o.mat);
  re4dc_ps2_dyn_parts(0x104,id,&o,p,count,offsetof(Part,next),offsetof(Part,pose));
 };
 // Reverse bind order still finds both owners and rejects another room.
 bind(7,obj[1],&head,2);bind(5,obj[0],&head,2);
 assert(!re4dc_ps2_dyn_source(0x104,&obj[0],10));
 assert(!re4dc_ps2_dyn_source(0x105,&obj[0],10));
 tail.pose[4]=1.2f;++frame_no;
 assert(re4dc_ps2_dyn_source(0x104,&obj[0],10));
 assert(re4dc_ps2_dyn_source(0x104,&obj[1],11));
 // The whole placement stays source-owned when animation returns to rest.
 tail.pose[4]=0;++frame_no;
 assert(re4dc_ps2_dyn_source(0x104,&obj[0],10));
 obj[0].flag=1;++frame_no;assert(dyn::query(5)==1);
 obj[0].flag=3;obj[0].serial=12;++frame_no;
 assert(!re4dc_ps2_dyn_source(0x104,&obj[0],12));
 assert(dyn::query(5)==0);
 // Reuse drops the old pose array; the new owner starts at its own rest pose.
 const unsigned before=allocations;
 bind(5,obj[0],&head,2);assert(allocations==before && dyn::nobjects==2);
 assert(!re4dc_ps2_dyn_source(0x104,&obj[0],12));
 ++frame_no;head.pose[0]=3;assert(re4dc_ps2_dyn_source(0x104,&obj[0],12));
 // A different scenery ID can reuse the same object-pool address. The old
 // ID has a stale serial but must not mask the new binding in the sorted table.
 ++obj[0].serial;bind(7,obj[0],&head,2);
 ++frame_no;head.pose[0]=4;
 assert(re4dc_ps2_dyn_source(0x104,&obj[0],13));
 // An incomplete part chain never publishes a partial allocation.
 bind(5,obj[0],&tail,2);assert(dyn::slots[0].parts==nullptr);
 dyn::reset();assert(!allocations && !dyn::nobjects && !dyn::ids);
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            cpp=Path(temporary)/'test.cpp';exe=Path(temporary)/'test'
            cpp.write_text(preamble+state+functions+cases)
            subprocess.run(['g++','-std=c++17','-O1','-fsanitize=address,undefined',str(cpp),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)


if __name__ == '__main__':
    unittest.main()
