"""Main actor gateway, original/replacement selection and cached geometry guard."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class ActorMainTests(unittest.TestCase):
    def test_actual_main_defer_cache_and_acceptance(self):
        fast = (GAME / 'platform/native_actor_fast.cpp').read_text()
        selection = (GAME / 'platform/include/gc_asset_actor_select.inc').read_text()
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        frames = fast[fast.index('struct GcAssetFrameUse'):fast.index('#endif', fast.index('struct GcAssetFrameUse'))]
        prepare = function(fast, 'Frame* prepare_frame(')
        prepare = prepare[:prepare.index('    f.near_distance =')] + '    (void)near_distance;(void)far_distance;return &f;\n}\n'
        one = function(fast, 'Frame& one_frame(')
        one = one[:one.index('    f.near_distance =')] + '    (void)near_distance;(void)far_distance;(void)se;(void)src;(void)memo;return f;\n}\n'
        main = function(fast, 'extern "C" int re4dc_actor_submit(')
        main = main[:main.index('#if defined(RE4DC_RIGID_CENSUS)')] + r'''
    (void)f;(void)base;if(emit){gcasset_model_prepare(&p);sq=true;gcasset_model_accept();sq=false;}return 1;
}
'''
        chunks = function(fast, 'extern "C" unsigned re4dc_actor_submit_chunks(')
        fallback = chunks[chunks.index('        int r = one_chunk(p, w);'):]
        fallback = fallback[:fallback.index('#if')]
        fixture = r'''
#include "gc_asset_actor.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cmath>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
using u8=unsigned char;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
struct Re4dcModelPart{const void*model;const void*info;const unsigned char*stream,*uv;unsigned stream_bytes,position_count,normal_count;const unsigned char*positions=nullptr,*normals=nullptr;unsigned position_stride=8,normal_stride=8,normal_shift=14;float modelview[12]{},projection[7]{},viewport[6]{};unsigned cull=0;};
struct Re4dcActorSource{const unsigned char*positions,*normals;unsigned position_count,normal_count,palette_entries,small_normals;};
Re4dcActorSource current_source{};bool source_live=true;unsigned resolutions;
extern "C" int re4dc_actor_model_source(const void*,Re4dcActorSource*out){assert(!sq);++resolutions;*out=current_source;return source_live;}
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**data){*data=nullptr;return 0x00100000U;}
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned){return 0;}
struct Chunk{unsigned position_count=1,normal_count=1,palette_count=1,uv_bytes=4,stream_bytes=32;const unsigned char*positions,*normals,*uv,*stream,*weights;};
struct RegistryView{unsigned geometry_count=1;}registry;Chunk chunks[1];Chunk registry_gview(unsigned g){return chunks[g];}PayloadProof gcasset_registry[2];
''' + selection + r'''
struct Frame{const void*info=nullptr;unsigned frame=~0U;float modelview[12]{},projection[7]{},viewport[6]{};};
constexpr unsigned kFrames=4;Frame frames[kFrames];unsigned frame_victim,frame_serial=1;
''' + frames + r'''
bool same_words(const float*a,const float*b,unsigned n){return !memcmp(a,b,n*4);}
struct SkinEntry{};struct OneScreen{};
''' + prepare + '\n' + one + r'''
SourceUse gcasset_model_pending;
''' + function(ui, 'void gcasset_model_prepare(') + '\n' + function(ui, 'void gcasset_model_accept(') + r'''
struct Stats{unsigned parts=0,declined=0,handled=0,deferred=0,culled_parts=0;}stats;
#define PXF_BEGIN(...)
#define PXF_EXIT(...)
#define RE4DC_CENSUS_DEC(...)
#define G1PC_PART(...)
constexpr bool kCrowd=false,kLodBuild=false;constexpr unsigned kLodPending=1;
unsigned workspace_top;bool qualify=true,emit=true,defer=false,convert_ok=true;
bool qualifies(const Re4dcModelPart&){return qualify;}
namespace re4dc{namespace render{bool is_finite(float x){return std::isfinite(x);}}}
struct BlobHeader{unsigned flags=0;}blob;
const BlobHeader*blob_of(const Re4dcModelPart&){return convert_ok?&blob:nullptr;}
const BlobHeader*convert(const Re4dcModelPart&){return nullptr;}
void relod(const Re4dcModelPart&,bool){}int re4dc_actor_model_class(const void*,const void*){return 0;}
void re4dc_model_result(unsigned,unsigned,unsigned){}
SourceUse queued;
bool re4dc_model_defer_part(const Re4dcModelPart*){if(defer)queued=source_use;return defer;}
''' + main + r'''
struct OneWindow{};unsigned closes;
int one_chunk(Re4dcModelPart&,OneWindow&){return -1;}void one_close(OneWindow&){++closes;}
int actual_fallback(Re4dcModelPart&p){OneWindow w;
''' + fallback + r'''
 return r;
}
void put(unsigned char*a,unsigned at,unsigned value){memcpy(a+at,&value,4);}
void flush(){payload_flush_all();member_flush();}
void clear_frames(){++frame_serial;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);int model,info;unsigned char replacement[512]={51},original[536]={};
 auto&c=chunks[0];c.positions=replacement+64;c.normals=replacement+128;c.uv=replacement+144;c.stream=replacement+160;c.weights=replacement+256;assert(payload_capture(gcasset_registry[0],&registry,replacement,sizeof replacement));
 put(original,0,1);put(original,16,24);put(original,20,0x004e4942);assert(member_adopt(&original,original,sizeof original,true));const unsigned char*bin=original+24;assert(member_capture(bin));ModelMember member;assert(member_lookup(bin,&member));
 SourceUse outer{member.serial,1U<<SourceGeometry,&model,&info};Re4dcModelPart p{&model,&info,c.stream,c.uv,32,1,1};p.projection[5]=-1;p.projection[6]=-2;
 current_source={c.positions,c.normals,1,1,1,0};source_use=outer;
 // Main/fallback replacement must replace an ambient original BIN context.
 assert(actual_fallback(p) && closes==1);flush();assert(source_use.serial==outer.serial && source_use.payload==nullptr);assert(logs.find("kind=geometry")!=std::string::npos && logs.find("kind=model")==std::string::npos);end(1);begin(0x111,2,Required);
 // No emission, cull, rejection and conversion failure cannot count a use.
 logs.clear();emit=false;assert(re4dc_actor_submit(&p));flush();assert(logs.empty());emit=true;p.cull=3;assert(re4dc_actor_submit(&p));flush();assert(logs.empty());p.cull=0;qualify=false;assert(!re4dc_actor_submit(&p));qualify=true;convert_ok=false;assert(!re4dc_actor_submit(&p));convert_ok=true;flush();assert(logs.empty());
 // Defer occurs before Frame preparation. Replay freezes the exact saved
 // replacement serial/mask, even when current source resolution later fails.
 clear_frames();defer=true;assert(re4dc_actor_submit(&p));assert(queued.payload==&gcasset_registry[0]);const auto saved=queued;defer=false;
 {ReplayScope replay(saved.serial,saved.mask,saved.payload);assert(re4dc_actor_submit(&p));}flush();
 logs.clear();current_source={bin+64,bin+128,1,1,1,0};{ReplayScope replay(saved.serial,saved.mask,saved.payload);assert(re4dc_actor_submit(&p));}flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);current_source={c.positions,c.normals,1,1,1,0};
 logs.clear();source_live=false;{ReplayScope replay(saved.serial,saved.mask,saved.payload);assert(re4dc_actor_submit(&p));}flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);source_live=true;
 // Explicit foreign/prepared arrays cannot inherit original or replacement.
 clear_frames();logs.clear();unsigned char alien[64]{};p.positions=alien;p.normals=alien;assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);p.positions=p.normals=nullptr;
 // Original fallback needs the same model/info AND full stream/source spans.
 clear_frames();logs.clear();current_source={bin+64,bin+128,1,1,1,0};p.stream=bin+160;p.uv=bin+144;assert(re4dc_actor_submit(&p));flush();assert(logs.find("kind=model")!=std::string::npos);
 assert(member_contains(member.serial,bin+480,32) && !member_contains(member.serial,bin+481,32));
 clear_frames();logs.clear();p.stream=bin+500;assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);p.stream=bin+160;
 clear_frames();logs.clear();current_source.normals=alien;assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);current_source.normals=bin+128;
 clear_frames();defer=true;assert(re4dc_actor_submit(&p));const auto raw_saved=queued;assert(raw_saved.serial==member.serial && !raw_saved.payload);defer=false;current_source={c.positions,c.normals,1,1,1,0};logs.clear();{ReplayScope replay(raw_saved.serial,raw_saved.mask);assert(re4dc_actor_submit(&p));}flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);current_source={bin+64,bin+128,1,1,1,0};
 clear_frames();logs.clear();int other_info;outer.info=&other_info;source_use=outer;assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);outer.info=&info;source_use=outer;
 // Same Frame key after replacement generation change must fail BOTH the
 // actual UI acknowledgement and the explicit ActorSourceScope path.
 clear_frames();logs.clear();current_source={c.positions,c.normals,1,1,1,0};p.stream=c.stream;p.uv=c.uv;assert(re4dc_actor_submit(&p));flush();logs.clear();payload_retire(gcasset_registry[0]);replacement[0]=52;assert(payload_capture(gcasset_registry[0],&registry,replacement,sizeof replacement));assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);
 logs.clear();source_use=outer;SkinEntry skin;OneScreen screen;{ActorSourceScope scope(&p,&current_source);sq=true;one_frame(p,1,2,skin,current_source,screen);scope.accepted();sq=false;}flush();assert(logs.find("unbound-accepted-payload")!=std::string::npos);
 // Fresh cache generation can qualify the current source; stale saved hand
 // or package generation cannot select a new owner on replay.
 clear_frames();logs.clear();assert(re4dc_actor_submit(&p));flush();assert(logs.find("kind=geometry")!=std::string::npos);
 logs.clear();{ReplayScope replay(saved.serial,saved.mask,saved.payload);assert(re4dc_actor_submit(&p));}flush();assert(logs.find("unbound-accepted-model")!=std::string::npos || logs.find("unbound-accepted-payload")!=std::string::npos);
 member_retire(&original);assert(!member_contains(member.serial,bin+64,8));
}
'''
        fixture = fixture.replace('#include "gc_asset_actor.h"', (GAME / 'platform/include/gc_asset_actor.h').read_text().replace('#pragma once\n', ''))
        self.compile_run(fixture)
        mutants = [
            ('ambient original', '    re4dc_gcasset::ActorMainSourceScope gcasset_main_scope(&p);', ''),
            ('cached generation', 'if(!saved.serial || saved.serial!=use.serial || saved.mask!=use.mask || saved.payload!=use.payload)use={};', '(void)saved;(void)use;'),
            ('accepted snapshot bypass', 'payload_accept(current?selected.payload:nullptr,current?selected.serial:0,', 'payload_accept(((void)current,selected.payload),selected.serial,'),
            ('partial original stream', '!member_contains(previous->serial,part->stream,part->stream_bytes)', 'false'),
            ('mixed replay arrays', 'if(current.payload!=saved.payload || current.serial!=saved.serial)return {};', '(void)current;'),
        ]
        for label, old, new in mutants:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old), 1)
                self.compile_run(fixture.replace(old, new), reject=True)

    def compile_run(self, fixture, reject=False):
        with tempfile.TemporaryDirectory(prefix='gc-port23-actor-main-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture)
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_NATIVE_MODEL_REGISTRY=1',
                            '-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1', '-DRE4DC_NMR_MASK=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(root / 'fixture')], check=True)
            result = subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(root / 'fixture')], capture_output=reject, text=True)
            if reject:self.assertNotEqual(result.returncode, 0, 'compiled main gateway mutant escaped runtime assertions')
            else:result.check_returncode()

    def test_actual_fast_gate0_token_identity(self):
        path = 'port/dreamcast/game/platform/native_actor_fast.cpp'
        old = subprocess.check_output(['git', '-C', str(GAME.parents[2]), 'show', 'd62995038:' + path], text=True)
        current = (GAME / 'platform/native_actor_fast.cpp').read_text()
        with tempfile.TemporaryDirectory(prefix='gc-port23-main-off-', dir='/dev/shm') as temporary:
            files=[]
            for label, text in [('old', old), ('current', current)]:
                path = Path(temporary) / (label + '.cpp');path.write_text(re.sub(r'^#include .*\n', '', text, flags=re.M));files.append(path)
            for coarse,transaction in [(0,0),(1,0),(1,1),(2,1)]:
                streams = [subprocess.check_output(['g++', '-E', '-P', '-DRE4DC_GC_ASSET_GATE=0',
                    '-DRE4DC_COARSE_ONE_SUBMIT='+str(coarse), '-DRE4DC_ACTOR_TRANSACTION='+str(transaction),
                    '-DRE4DC_ACTOR_DIRECT=1', '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1', str(path)], text=True) for path in files]
                tokens=lambda text:re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S',text)
                self.assertEqual(tokens(streams[0]),tokens(streams[1]))


if __name__ == '__main__':unittest.main()
