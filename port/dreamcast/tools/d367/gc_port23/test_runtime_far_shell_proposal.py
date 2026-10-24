"""Exercise actual far-shell loader/draw bodies from the unapplied proposal."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from far_shell_payload_patch import patched
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class FarShellProposalTests(unittest.TestCase):
    def test_proposed_off_preprocessed_identity(self):
        source = (GAME / 'platform/far_shell.inc').read_text()
        for part in (1, 2):
            command = ['g++', '-x', 'c++', '-E', '-P', '-DRE4DC_GC_ASSET_GATE=0',
                       '-DRE4DC_FAR_SHELL_PART='+str(part), '-']
            original = subprocess.run(command, input=source, text=True, capture_output=True, check=True).stdout
            proposed = subprocess.run(command, input=patched(source), text=True, capture_output=True, check=True).stdout
            self.assertEqual(original.split(), proposed.split())

    def test_actual_proposed_load_draw_retire(self):
        source = patched((GAME / 'platform/far_shell.inc').read_text())
        types = source[source.index('struct Head {'):source.index('// Residency policy')]
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>
using namespace re4dc_gcasset;
bool sq_held;std::string logs;
extern "C" void re4dc_log(const char* fmt,...){assert(!sq_held);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
namespace farshell {
''' + types + r'''
}
using namespace farshell;
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
std::vector<unsigned char> file;unsigned position;bool missing,read_fail;unsigned frees;
file_t fs_open(const char*,int){position=0;return missing?-1:1;}
unsigned fs_total(file_t){return file.size();}
int fs_close(file_t){return 0;}
int fs_seek(file_t,unsigned at,int){position=at;return at;}
ssize_t fs_read(file_t,void*out,unsigned bytes){if(read_fail || bytes>file.size()-position)return 0;memcpy(out,file.data()+position,bytes);position+=bytes;return bytes;}
int re4dc_static_heap_free(){return 100000;}
void* re4dc_static_alloc(unsigned bytes){return malloc(bytes);}
void re4dc_static_free(void* p){assert(!sq_held && !asset_proof.serial);++frees;free(p);}
unsigned ps2_crc32(const void*,unsigned){return 1;}
namespace re4dc_gcasset{bool ensure_disc_catalog(){assert(!sq_held);return true;}}
''' + function(source, 'void close()') + '\n' + function(source, 'void open(unsigned room)') + r'''
struct World{unsigned room=0x111;bool camera=true;float projection[7]={0,1,0,1,0,0,-1};float viewport[4]={0,0,640,480};float view[12]={1,0,0,0,0,1,0,0,0,0,1,0};}ps2w;
int far_shell_mode=1;constexpr float kBias=.97f,RE4DC_SCREEN_WF=640,RE4DC_SCREEN_HF=480;
namespace re4dc{namespace render{struct DrawBounds{float lo[3],hi[3];};bool is_finite(float x){return x==x;}bool group_visible(const DrawBounds&,const float*,const float*,const float*,float,float,int){return true;}}}
struct pvr_vertex_t{unsigned flags;float x,y,z,u,v;unsigned argb,oargb;};
struct Re4dcModelDirect{std::uint32_t*sq;float u_scale,v_scale;void*scratch;unsigned scratch_capacity;};
constexpr unsigned PVR_CMD_VERTEX=0xe0000000,PVR_CMD_VERTEX_EOL=0xf0000000;
alignas(32) unsigned sq_memory[128];pvr_vertex_t scratch[4];bool accept=true;unsigned submissions;
int re4dc_ps2_world_direct_begin(const unsigned*,Re4dcModelDirect*out){if(!accept)return 0;*out={sq_memory,1,1,scratch,4};sq_held=true;return 1;}
void sq_flush(unsigned*){assert(sq_held);}
void re4dc_model_direct_end(unsigned slots){assert(sq_held);if(slots){++submissions;payload_accept(source_use.payload,source_use.serial,source_use.mask);}sq_held=false;}
''' + function(source, 'extern "C" int re4dc_far_shell_draw(') + r'''
unsigned rows(){unsigned count=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++count;++at;}return count;}
void build(){file.assign(sizeof(Head)+sizeof(Mat)+sizeof(Group)+3*sizeof(Vert)+4,0);Head h{{'F','S','H','1'},1,1,1,3,4,1,0x111};memcpy(file.data(),&h,sizeof h);Group g{};g.lo[0]=g.lo[1]=-1;g.hi[0]=g.hi[1]=1;g.lo[2]=-11;g.hi[2]=-9;g.origin[2]=-10;g.scale=1;g.vcount=3;g.strip_bytes=4;memcpy(file.data()+sizeof(Head)+sizeof(Mat),&g,sizeof g);unsigned char*strip=file.data()+file.size()-4;strip[0]=3;strip[1]=0;strip[2]=1;strip[3]=2;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);build();open(0x111);assert(st.h && asset_proof.serial);
 // Capture excludes generated LUT/alignment: exact complete file only.
 AssetDescription desc;assert(describe_checked(asset_proof.asset,&desc));assert(!memcmp(desc.digest.bytes,fingerprint(file.data(),file.size()).bytes,32));
 const unsigned first=asset_proof.serial;assert(re4dc_far_shell_draw(5,25));assert(submissions==1);payload_flush_all();assert(rows()==1);
 logs.clear();accept=false;re4dc_far_shell_draw(5,25);payload_flush_all();assert(submissions==1 && logs.empty());accept=true;
 // No vertices accepted when every source vertex is behind near plane.
 auto*group=const_cast<Group*>(st.groups);group->origin[2]=0;re4dc_far_shell_draw(5,25);payload_flush_all();assert(submissions==1);group->origin[2]=-10;
 payload_retire(asset_proof);re4dc_far_shell_draw(5,25);payload_flush_all();assert(submissions==2 && logs.find("unbound-accepted-payload")!=std::string::npos);
 close();assert(!st.block);file.back()=1;open(0x111);assert(asset_proof.serial>first);assert(describe_checked(asset_proof.asset,&desc));assert(!memcmp(desc.digest.bytes,fingerprint(file.data(),file.size()).bytes,32));
 close();read_fail=true;open(0x111);assert(!st.block && !asset_proof.serial);read_fail=false;
 build();reinterpret_cast<Head*>(file.data())->room=0x113;open(0x111);assert(!st.block && !asset_proof.serial);
 missing=true;open(0x111);assert(!st.block && !asset_proof.serial && !sq_held && frees>=3);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-far-shell-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_TA_HASH=0',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
