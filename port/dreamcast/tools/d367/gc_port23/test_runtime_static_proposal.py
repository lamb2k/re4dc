"""Current actual partial movie reload and mixed-owner accepted batch controls."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function


HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class StaticProposalTests(unittest.TestCase):
    def test_proposed_actual_movie_reload_refusals(self):
        source = (GAME / 'platform/native_static.cpp').read_text()
        fixture = r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
#define RE4DC_GCAP_RETIRE(v) payload_retire((v).asset_proof)
#define RE4DC_GCAP_CAPTURE(v,b,n,l,s) ((void)payload_capture((v).asset_proof,&(v),b,n,l,s))
struct Ps2Head{char magic[4];unsigned version,parts,meshes,placements,crc;};
struct Ps2Part{unsigned pass,cull,width,height;};struct Ps2Placement{unsigned mesh;float affine[12];};
struct Package{struct Head{unsigned part_count=1,mesh_count=1;}head;bool fail=false,closed=true;const Head&header(){return head;}bool adopt(unsigned char*data,unsigned,bool,bool){data[0]^=0x10;closed=false;return !fail;}void close(){closed=true;}};
struct World{unsigned room=0x111,want=0x111,nplacements=0;Package package;const Ps2Part*parts=nullptr;const Ps2Placement*placements=nullptr;void*gather=nullptr;bool camera=false;PayloadProof asset_proof;}ps2w;
namespace re4dc{namespace render{bool is_finite(float x){return x==x;}}namespace room{struct CompactVertex12{};}}
namespace movie_world{enum class Phase{returning};unsigned fnv(const void*,unsigned){return 1;}}
constexpr unsigned kLutBytes=0,kGatherBytes=0;
alignas(32) unsigned char arena[256];
struct Movie{movie_world::Phase phase=movie_world::Phase::returning;unsigned capacity;void*base=arena;}ps2_movie;
struct Files{unsigned mesh=32,side=sizeof(Ps2Head)+sizeof(Ps2Part)+sizeof(Ps2Placement),mesh_crc=1,mesh_fnv=1,side_crc=1,side_fnv=1;}ps2_movie_files;
struct MovieWorldRead{~MovieWorldRead(){}};struct Re4dcIoScope{~Re4dcIoScope(){}};
void gcasset_invalidate_world(){if(ps2w.asset_proof.owner)payload_invalidate(ps2w.asset_proof,&ps2w);}
bool ps2_movie_current(){return true;}bool ps2_movie_layout(unsigned){return true;}
using file_t=int;constexpr int O_RDONLY=0,FILEHND_INVALID=-1;
std::vector<unsigned char> mesh(32,2),side(ps2_movie_files.side);bool short_read=false;unsigned reads;
file_t fs_open(const char*path,int){return strstr(path,"r4pw")?2:1;}int fs_close(file_t){return 0;}
ssize_t fs_total(file_t fd){return fd==1?mesh.size():side.size();}
bool read_package(file_t fd,void*dest,unsigned count,unsigned){assert(!ps2w.asset_proof.serial);++reads;if(short_read)return false;const auto&bytes=fd==1?mesh:side;memcpy(dest,bytes.data(),count);return true;}
unsigned ps2_crc32(const void*,unsigned){return 1;}
''' + function(source, 'bool ps2_movie_reload(){') + r'''
void prepare(){Ps2Head h{{'R','4','P','W'},1,1,1,1,1};Ps2Part p{0,0,16,16};Ps2Placement placement{};memcpy(side.data(),&h,sizeof h);memcpy(side.data()+sizeof h,&p,sizeof p);memcpy(side.data()+sizeof h+sizeof p,&placement,sizeof placement);ps2_movie.capacity=((ps2_movie_files.mesh+31)&~31U)+((ps2_movie_files.side+31)&~31U);}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);prepare();unsigned char source[32]={7};assert(payload_capture(ps2w.asset_proof,&ps2w,source,sizeof source));assert(ps2w.asset_proof.serial);
 assert(ps2_movie_reload());assert(!ps2w.asset_proof.serial); // mesh+R4PW cannot authenticate retained prepared sidecars
 short_read=true;assert(!ps2_movie_reload());assert(!ps2w.asset_proof.serial);short_read=false;
 ps2w.package.fail=true;assert(!ps2_movie_reload());assert(!ps2w.asset_proof.serial);ps2w.package.fail=false;
 reinterpret_cast<Ps2Head*>(side.data())->version=2;assert(!ps2_movie_reload());assert(!ps2w.asset_proof.serial && ps2w.package.closed);
 prepare();reinterpret_cast<Ps2Part*>(side.data()+sizeof(Ps2Head))->pass=3;assert(!ps2_movie_reload());assert(!ps2w.asset_proof.serial);
 prepare();reinterpret_cast<Ps2Placement*>(side.data()+sizeof(Ps2Head)+sizeof(Ps2Part))->mesh=1;assert(!ps2_movie_reload());assert(!ps2w.asset_proof.serial);
 prepare();mesh[1]^=1;assert(ps2_movie_reload());assert(!ps2w.asset_proof.serial && reads>=10);payload_retire(ps2w.asset_proof);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-reload-proposal-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_MOVIE_WORLD_ARENA=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_proposed_actual_mixed_owner_impostor_flush(self):
        static = (GAME / 'platform/native_static.cpp').read_text()
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        helper = ui[ui.index('re4dc_gcasset::SourceUse gcasset_model_pending;'):ui.index('void gcasset_packet_reset()')]
        fixture = r'''
#include "gc_asset_static.h"
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
 for(unsigned i=0;i<3;++i){auto&q=impostor_queue[i];q.record=&record;q.source={&proof[i],proof[i].serial,1U<<SourceGeometry};}
 impostor_count=3;re4dc_static_flush_impostors();payload_flush_all();assert(submissions==1 && rows()==2); // capacity rejects third owner
 logs.clear();impostor_frame=++frame;impostor_count=2;bound=false;
 for(unsigned i=0;i<2;++i)impostor_queue[i].record=&record;
 re4dc_static_flush_impostors();payload_flush_all();assert(submissions==1 && logs.empty()); // failed bind emits nothing
 logs.clear();impostor_frame=++frame;impostor_count=2;bound=true;
 for(unsigned i=0;i<2;++i)impostor_queue[i].record=&record;
 payload_retire(proof[0]);re4dc_static_flush_impostors();payload_flush_all();assert(submissions==2 && !rows() && logs.find("unbound-accepted-payload")!=std::string::npos); logs.clear();begin(0x111,2,Required);impostor_frame=++frame;impostor_count=2;
 for(unsigned i=0;i<2;++i)impostor_queue[i].record=&record;
 impostor_queue[0].source.mask=(1U<<SourceGeometry)|(1U<<Weapon);
 re4dc_static_flush_impostors();payload_flush_all();end(2);assert(submissions==3 && rows()==1 && logs.find("consumer=3")!=std::string::npos && logs.find("source_geometry=1")!=std::string::npos && logs.find("weapon=0")!=std::string::npos);
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
