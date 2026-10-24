"""Actual hand owner/copy bodies, simulated providers, real gate metadata."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class HandOwnerTests(unittest.TestCase):
    def test_four_actual_derivation_scopes_off_tokens(self):
        path = 'port/dreamcast/game/platform/native_actor_fast.cpp'
        old = subprocess.check_output(['git', '-C', str(GAME.parents[2]), 'show', '61bf74306:' + path], text=True)
        new = (GAME / 'platform/native_actor_fast.cpp').read_text()
        self.assertEqual(new.count('HandDerivationScope gcasset_mutation('), 4)
        self.assertEqual(new.count('Re4dcActorStreamMutation mutation('), 4)
        # Compare the actual file's preprocessor token stream; external include
        # bodies are unchanged and omitted from both sides of this local check.
        with tempfile.TemporaryDirectory(prefix='gc-port23-hand-fast-off-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            files = []
            for label, text in [('old', old), ('new', new)]:
                target = root / (label + '.cpp');target.write_text(re.sub(r'^#include .*\n', '', text, flags=re.M));files.append(target)
            for cone, limit in [(0, 0), (0, 300), (1, 300), (2, 300)]:
                outputs = [subprocess.check_output(['g++', '-E', '-P', '-DRE4DC_GC_ASSET_GATE=0',
                    '-DRE4DC_GC_ASSET_LEON_HAND_PACK=1', '-DRE4DC_ACTOR_TRANSACTION=1',
                    '-DRE4DC_ACTOR_PRELIT=1', '-DRE4DC_ACTOR_BACKFACE_CONE=' + str(cone),
                    '-DRE4DC_ACTOR_LOD_PART_MAX=' + str(limit), str(target)], text=True) for target in files]
                tokens = lambda text: re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S', text)
                self.assertEqual(tokens(outputs[0]), tokens(outputs[1]))

    def test_actual_direct_worker_aica_selection_derivation_and_replay(self):
        hands = (GAME / 'coarse_actor_leon_hands.inc').read_text()
        hands = re.sub(r'^#include <[^>]+>\n', '', hands, flags=re.M)
        selection = (GAME / 'platform/include/gc_asset_actor_select.inc').read_text()
        fixture = r'''
#include "gc_asset_actor.h"
#include "gc_asset_hand_derivation.h"
#include "coarse_actor_preflight.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/types.h>
using namespace re4dc_gcasset;
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**data){*data=nullptr;return 0x00100000U;}
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned){return 0;}
std::string logs;bool locked,sq,g2,partial;unsigned io;void(*before_write)(void*);void(*before_free)();
extern "C" void re4dc_log(const char*fmt,...){assert(!sq && !g2 && !io);char text[256];va_list args;va_start(args,fmt);vsnprintf(text,sizeof text,fmt,args);va_end(args);logs+=text;}
struct Re4dcIoScope{Re4dcIoScope(){assert(!locked && !sq && !g2);++io;}~Re4dcIoScope(){--io;}};
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0,PRIO_DEFAULT=1;
unsigned char disk[800],aram[26000];unsigned cursor[64],opened;
file_t fs_open(const char*,int){assert(opened+1<64);return ++opened;}
off_t fs_total(file_t){return sizeof disk;}
off_t fs_seek(file_t f,unsigned offset,int){cursor[f]=offset;return offset;}
ssize_t fs_read(file_t f,void* to,unsigned bytes){assert(cursor[f]+bytes<=sizeof disk);if(before_write)before_write(to);const unsigned got=partial?bytes-1:bytes;memcpy(to,disk+cursor[f],got);cursor[f]+=got;return got;}
int fs_close(file_t){return 0;}
using mutex_t=int;
#define MUTEX_INITIALIZER 0
void mutex_lock(mutex_t*){assert(!locked);locked=true;}void mutex_unlock(mutex_t*){assert(locked);locked=false;}
int mutex_trylock(mutex_t*){if(locked)return -1;locked=true;return 0;}
struct kthread_t{void*(*entry)(void*);void* argument;bool done=false;};
struct kthread_attr_t{void*stack_ptr;unsigned stack_size,prio;const char*label;};
kthread_t* thd_create_ex(kthread_attr_t*,void*(*entry)(void*),void*arg){return new kthread_t{entry,arg};}
void run_job(kthread_t* thread){assert(thread && !thread->done);thread->entry(thread->argument);thread->done=true;}
void thd_join(kthread_t*thread,void*){assert(thread && thread->done);delete thread;}
unsigned long long timer_us_gettime64(){static unsigned time;return ++time;}
unsigned snd_mem_malloc(unsigned bytes){assert(bytes+32<=sizeof aram);return 32;}
void snd_mem_free(unsigned){if(before_free)before_free();}
void spu_memload(unsigned at,const void*from,unsigned bytes){g2=true;assert(at+bytes<=sizeof aram);memcpy(aram+at,from,bytes);g2=false;}
void spu_memread(void*to,unsigned at,unsigned bytes){g2=true;assert(at+bytes<=sizeof aram);if(before_write)before_write(to);memcpy(to,aram+at,bytes);g2=false;}
extern "C" void* re4dc_motion_alloc(unsigned bytes){return malloc(bytes);}
extern "C" void re4dc_motion_free(void*at){if(before_free)before_free();free(at);}
extern "C" {unsigned char re4dc_dvd_buff[0x20000];}
struct ModelData{const void*vtxOrig;unsigned nVtx,nNrm,weight_ext_num,weight_palette_num;};struct cModelInfo{ModelData*pData;};
unsigned fingerprint(const void*){return 1;}
namespace leon4k{struct Weight{unsigned char data[16];};struct Chunk{unsigned source_info,position_count,normal_count,palette_count,triangles,stream_bytes;const unsigned char*positions,*normals,*uv,*stream;const Weight*weights;};Chunk chunks[8];}
struct Re4dcModelPart{const void*model;const void*info;const unsigned char*stream,*uv;unsigned stream_bytes,position_count,normal_count;};
struct Re4dcActorSource{const unsigned char*positions,*normals;unsigned position_count,normal_count,palette_entries,small_normals;};
''' + hands + r'''
namespace leon_hand_pack{void reset_role_ids(unsigned){}}
''' + selection + r'''
void verify_write(void*target){using namespace leon_hand_pack;for(unsigned side=0;side<2;++side)if(target==slot[side])assert(!gcasset_hand_slot[side].serial);}
void verify_free(){using namespace leon_hand_pack;assert(!gcasset_hand_job.proof.source);if(aica)for(auto cell:gcasset_hand_cell)assert(!cell.source);}
int main(){using namespace leon_hand_pack;
 unsigned header[8]={kMagic,(1U<<16)|kVersion,(1U<<16)|4U,kSlotBytes[0],kSlotBytes[1],160,sizeof disk,0};memcpy(disk,header,32);
 Row row{5,2,1,1,1,1};memcpy(disk+32,&row,sizeof row);
 Blob spec[4]{};for(unsigned b=0;b<4;++b){auto&x=spec[b];x.role=b==1?6:5;x.flags=b<2?1:0;x.pc=x.nc=x.pal=x.tri=1;x.stream=32;x.offset32=(160+b*160)/32;unsigned sizes[5]={8,8,4,32,16};for(unsigned i=0;i<5;++i)x.size[i]=sizes[i];memset(disk+160+b*160,int(b+1),160);}
 memcpy(disk+44,spec,sizeof spec);Src source{1,0,2};memcpy(disk+140,&source,sizeof source);
 assert(install(nullptr,0));begin_startup_closed(1,Required);gcasset_hand_startup();assert(gcasset_hand_source.serial);
 before_write=verify_write;re4dc_leon_hands_room_enter();assert(gcasset_hand_ready && gcasset_hand_chunk_current(0) && gcasset_hand_chunk_current(1));
 assert(!leon_hand_asset(5));leon_cur_key=0;assert(leon_cur[5]);assert(leon_hand_pick(5,nullptr,leon4k::chunks[5],{}).chunk==&leon4k::chunks[5]);
 auto part=[](){const auto&c=leon4k::chunks[5];return Re4dcModelPart{&c,&c,c.stream,c.uv,c.stream_bytes,c.position_count,c.normal_count};};
 auto source_for=[](){const auto&c=leon4k::chunks[5];return Re4dcActorSource{c.positions,c.normals,c.position_count,c.normal_count,c.palette_count,0};};
 auto p=part();auto s=source_for();const unsigned original=gcasset_hand_slot[0].serial;
 {ActorSourceScope scope(&p,&s);assert(scope.selected.serial==original);sq=true;scope.accepted();sq=false;}payload_flush_all();assert(logs.find("kind=geometry")!=std::string::npos);
 // Actual direct loader failure revokes before a partial overwrite.
 mutex_lock(&lh_mutex);partial=true;assert(!load_now(0,2));partial=false;assert(!gcasset_hand_slot[0].serial);assert(load_now(0,0));mutex_unlock(&lh_mutex);
 // Actual AICA issued-store/readback chain selects a fresh copy generation.
 mutex_lock(&lh_mutex);prefetch(2);assert(load(0,2));mutex_unlock(&lh_mutex);assert(gcasset_hand_chunk_current(0) && gcasset_hand_slot[0].serial!=original);
 p=part();s=source_for();logs.clear();{ReplayScope replay(original,1U<<SourceGeometry,&gcasset_hand_slot[0]);ActorSourceScope scope(&p,&s);assert(scope.selected.serial==original);sq=true;scope.accepted();sq=false;}payload_flush_all();assert(logs.find("unbound-accepted-payload")!=std::string::npos && logs.find("GC-ASSET v=")==std::string::npos);
 // Real job allocation/range/thread, joined before cache and slot publication.
 mutex_lock(&lh_mutex);want[0]=3;assert(job_start(3));mutex_unlock(&lh_mutex);run_job(job_thd);
 mutex_lock(&lh_mutex);job_poll();mutex_unlock(&lh_mutex);assert(slot_blob[0]==3 && gcasset_hand_chunk_current(0));
 // A stale/mismatched pending range cannot publish even after production copies bytes.
 mutex_lock(&lh_mutex);want[0]=2;assert(job_start(2));++gcasset_hand_job.offset;mutex_unlock(&lh_mutex);run_job(job_thd);
 mutex_lock(&lh_mutex);job_poll();mutex_unlock(&lh_mutex);assert(slot_blob[0]==2 && !gcasset_hand_slot[0].serial);
 mutex_lock(&lh_mutex);assert(load_now(0,0));mutex_unlock(&lh_mutex);const unsigned derived=gcasset_hand_slot[0].serial;
 // Actual exported observer keeps source-copy serial across controlled stream derivation.
 const auto&c=leon4k::chunks[5];sq=true;{HandDerivationScope mutation(c.stream,c.stream_bytes);assert(!gcasset_hand_slot[0].serial);const_cast<unsigned char*>(c.stream)[0]^=1;mutation.complete();}sq=false;assert(gcasset_hand_slot[0].serial==derived);
 sq=true;{HandDerivationScope mutation(c.stream,c.stream_bytes);}sq=false;assert(!gcasset_hand_slot[0].serial);
 mutex_lock(&lh_mutex);assert(load_now(0,0));mutex_unlock(&lh_mutex);assert(gcasset_hand_chunk_current(0));
 // Yield invalidates cell/job identities before foreign audio can reuse AICA.
 before_free=verify_free;re4dc_leon_hands_yield();assert(!aica && gcasset_hand_chunk_current(0));before_free=nullptr;
 retire_catalog();assert(!gcasset_hand_chunk_current(0));
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-hand-owner-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_LEON_HAND_RETAIN=0', '-DRE4DC_GC_ASSET_LEON_HAND_PACK=1',
                            '-I', str(GAME), '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
