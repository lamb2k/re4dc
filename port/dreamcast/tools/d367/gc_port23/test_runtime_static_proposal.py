"""Controls on the generated, unapplied native_static handoff patch."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function
from static_payload_patch import patched

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class StaticProposalTests(unittest.TestCase):
    def test_proposed_actual_mixed_owner_impostor_flush(self):
        static = patched((GAME / 'platform/native_static.cpp').read_text())
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        helper = ui[ui.index('re4dc_gcasset::SourceUse gcasset_model_pending;'):ui.index('void gcasset_packet_reset()')]
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;bool sq_held;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq_held);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
struct Re4dcModelPart{const void*model;const void*info;};
namespace re4dc{namespace room{struct MeshImpostor{unsigned key_crc,key_fnv,atlas_w,atlas_h,cols,cell_w,cell_h;};}}
struct pvr_vertex_t{unsigned flags;float x,y,z,u,v;unsigned argb,oargb;};
constexpr unsigned PVR_CMD_VERTEX=0xe0000000,PVR_CMD_VERTEX_EOL=0xf0000000;
''' + function(static, 'struct ImpostorQuad {') + r''';
constexpr unsigned kImpostorQuads=48;ImpostorQuad impostor_queue[48];
unsigned impostor_count,impostor_frame=5,impostor_flushed=~0U,impostor_stats[4],frame=5;
unsigned re4dc_ui_frame(){return frame;}
struct Re4dcModelPacket{void*vertices;unsigned capacity;};
pvr_vertex_t model_packets[16];unsigned model_pending,model_used,model_peak,stream_model_bytes,stream_peak_bytes;
struct Handle{unsigned frame;};Handle handle;Handle*model_handle=&handle;
bool bound=true;unsigned submissions;
int re4dc_model_pt_begin(unsigned,unsigned,unsigned,unsigned,int,Re4dcModelPacket*p){p->vertices=model_packets;p->capacity=8;return bound;}
void stream_send(const void*,unsigned){assert(!sq_held);++submissions;}
#define RE4DC_GCA_MODEL_TEXTURE(...) ((void)0)
''' + helper + r'''
#define RE4DC_GCA_MODEL_PACKET_ACCEPT(vertices,count) gcasset_model_accept(vertices,count)
''' + function(ui, 'extern "C" void re4dc_model_packet_commit(') + '\n' + function(static, 'extern "C" void re4dc_static_flush_impostors()') + r'''
unsigned rows(){unsigned n=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++n;++at;}return n;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);PayloadProof proof[3];int owner[3];unsigned char bytes[3][32]={{1},{2},{3}};
 for(unsigned i=0;i<3;++i)assert(payload_capture(proof[i],&owner[i],bytes[i],32));
 re4dc::room::MeshImpostor record{1,2,64,64,1,64,64};
 for(unsigned i=0;i<3;++i){auto&q=impostor_queue[i];q.record=&record;q.asset_use={&proof[i],proof[i].serial,1U<<SourceGeometry};}
 impostor_count=3;re4dc_static_flush_impostors();payload_flush_all();assert(submissions==1 && rows()==2); // capacity rejects third owner
 logs.clear();impostor_frame=++frame;impostor_count=2;bound=false;
 for(unsigned i=0;i<2;++i)impostor_queue[i].record=&record;
 re4dc_static_flush_impostors();payload_flush_all();assert(submissions==1 && logs.empty()); // failed bind emits nothing
 logs.clear();impostor_frame=++frame;impostor_count=2;bound=true;
 for(unsigned i=0;i<2;++i)impostor_queue[i].record=&record;
 payload_retire(proof[0]);re4dc_static_flush_impostors();payload_flush_all();assert(submissions==2 && !rows() && logs.find("unbound-accepted-payload")!=std::string::npos);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-static-proposal-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_PVR_STREAM=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
