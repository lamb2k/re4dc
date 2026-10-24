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
    def test_actual_raw_gateway_packet_direct_and_defer_cannot_accept_ps2_bin(self):
        model = (GAME / 'platform/native_model.cpp').read_text()
        start = model.index('extern "C" void re4dc_model_submit(const Re4dcModelPart* p){')
        gateway = model[start:model.index('#if RE4DC_NATIVE_ACTOR\n', start)]+'observe_selected(p);\n}\n'
        guard = model[model.index('#if RE4DC_GC_ASSET_GATE\n    // An actor decline'):]
        guard = guard[:guard.index('#endif')+len('#endif')]
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        helpers = ui[ui.index('re4dc_gcasset::SourceUse gcasset_model_pending;'):ui.index('void gcasset_packet_reset()')]
        commit = function(ui, 'extern "C" void re4dc_model_packet_commit(')
        marker = ui.index('// WORLD_SUBMIT_END_IMPLEMENTATION')
        start = ui.index('#if RE4DC_TA_DIRECT', marker)
        finish = ui.index('\n}\n#if RE4DC_SCENERY_SUBMIT_BATCH', start)+2
        direct = 'void direct_account(unsigned vertices){\n'+ui[start:finish]
        start = ui.index('#if RE4DC_GC_ASSET_GATE', ui.index('    node->lighting=lighting;', ui.index('int defer_part(')))
        enqueue = ui[start:ui.index('#endif', start)+len('#endif')]
        fixture = r'''
#include "gc_asset_members.h"
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq_held;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq_held);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
struct Re4dcModelPart{const void*model;const void*info;unsigned serial=0;const void*world=nullptr;const void*view=nullptr;unsigned source_key[3]{};const void*stream=nullptr;const void*uv=nullptr;const void*colors=nullptr;const void*weights=nullptr;const void*shape=nullptr;};
struct Info{const void*data;};
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*info,const void**data){*data=static_cast<const Info*>(info)->data;return 0x01230001;}
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned){return 1;}
#define RE4DC_PROFILE_SCOPE(...)
#define RE4DC_MODEL_DIAG() true
#define PP_PATH(...)
bool re4dc_static_submit(const Re4dcModelPart*){return false;}
struct Handle{unsigned frame;};Handle handle;Handle*model_handle=&handle;
unsigned model_used,model_pending,model_peak,frame,direct_parts,direct_slots,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes;
unsigned char model_packets[1024];void stream_send(const void*,unsigned){}void re4dc_missing(const char*){assert(false);}
#define RE4DC_GCA_TEXTURE(...)
#define RE4DC_GCA_MODEL_TEXTURE(...)
''' + helpers + r'''
#define RE4DC_GCA_MODEL_ACCEPT() gcasset_model_accept()
#define RE4DC_GCA_MODEL_PACKET_ACCEPT(vertices,count) gcasset_model_accept(vertices,count)
''' + commit + '\n' + direct + r'''
struct Node{unsigned asset_serial=0,asset_mask=0;PayloadProof*asset_payload=nullptr;}queued;
void freeze(Node*node,const Re4dcModelPart&view){
''' + enqueue + r'''
}
unsigned mode;
void observe_selected(const Re4dcModelPart*p){if(mode==3){freeze(&queued,*p);return;}gcasset_model_prepare(p);sq_held=true;if(mode==0)re4dc_model_packet_commit(3);else if(mode==1)direct_account(3);else re4dc_model_packet_commit(0);sq_held=false;}
''' + gateway + r'''
void generic_fallback(const Re4dcModelPart*p){
''' + guard + r'''
 observe_selected(p);
}
int main(){unsigned char bin[128]={},foreign[64]={};unsigned one=1,offset=32;memcpy(bin,&one,4);memcpy(bin+16,&offset,4);memcpy(bin+20,"BIN",3);Digest digest=fingerprint(bin+32,96);char id[41];for(unsigned i=0;i<20;++i)sprintf(id+2*i,"%02x",digest.bytes[i]);CatalogRow row{"model",id,digest,PS2};assert(install(&row,1));assert(member_adopt(&bin,bin,sizeof bin,true) && member_capture(bin+32));ModelMember member;assert(member_lookup(bin+32,&member));AssetDescription description;assert(describe_checked(member.asset,&description) && description.provenance==PS2);
 int object;Info info{bin+32};Re4dcModelPart p{&object,&info};p.stream=bin+32;begin(0x111,1,Required);
 mode=2;re4dc_model_submit(&p);member_flush();assert(logs.find("unbound-accepted-model")==std::string::npos);
 for(unsigned field=0;field<4;++field){p.uv=p.colors=p.weights=p.shape=nullptr;if(field==0)p.uv=foreign;if(field==1)p.colors=foreign;if(field==2)p.weights=foreign;if(field==3)p.shape=foreign;
  for(mode=0;mode<2;++mode){re4dc_model_submit(&p);member_flush();}}
 mode=3;re4dc_model_submit(&p);assert(!queued.asset_serial && queued.asset_mask==((1U<<SourceGeometry)|(1U<<Weapon)) && !queued.asset_payload);
 // A replay keeps diagnostic role but cannot turn saved0 into a fresh BIN.
 mode=1;{ReplayScope replay(queued.asset_serial,queued.asset_mask);re4dc_model_submit(&p);}member_flush();
 // A declined complete/replay actor proof cannot leak into the raw walker.
 PayloadProof fake;assert(payload_capture(fake,&fake,foreign,sizeof foreign));source_use={fake.serial,(1U<<SourceGeometry)|(1U<<Weapon),p.model,p.info,&fake};generic_fallback(&p);member_flush();payload_flush_all();
 end(1);assert(logs.find("source_geometry=0")!=std::string::npos && logs.find("weapon=0")!=std::string::npos);assert(logs.find("consumer=0")!=std::string::npos && logs.find("consumer=3")!=std::string::npos);assert(logs.find("errors=0")==std::string::npos && logs.find("GC-ASSET v=")==std::string::npos);
}
'''
        self.compile_run(fixture, direct=True)
        for label, old, new in [
            ('blanket raw BIN', 'source_use={0,mask,p->model,p->info};', 'source_use={member.serial,mask,p->model,p->info};'),
            ('restore positive replay', 'replay_use.payload?re4dc_gcasset::replay_use.serial:0', 'replay_use.serial'),
            ('leaked fallback proof', 're4dc_gcasset::source_use={0,re4dc_gcasset::source_use.mask,p?p->model:nullptr,p?p->info:nullptr};', ''),
        ]:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old),1)
                # Positive-replay mutant needs a historical/manual raw serial;
                # saved0 still cannot turn positive by itself.
                changed=fixture.replace(old,new)
                if label=='restore positive replay':changed=changed.replace('ReplayScope replay(queued.asset_serial,queued.asset_mask)', 'ReplayScope replay(member.serial,queued.asset_mask)')
                self.compile_run(changed,reject=True,direct=True)

    def test_external_uv_weight_color_and_shape_cannot_inherit_ps2(self):
        selection = (GAME / 'platform/include/gc_asset_actor_select.inc').read_text()
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        fixture = r'''
#include "gc_asset_actor.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
struct Lighting{bool ambient_vertex=false,material_vertex=false;};
struct Re4dcModelPart{const void*model;const void*info;const unsigned char*stream,*uv;unsigned stream_bytes=32,position_count=1,normal_count=1;const unsigned char*positions=nullptr,*normals=nullptr;unsigned position_stride=8,normal_stride=8,normal_shift=14,alpha_state=255,flags=0;const Lighting*lighting=nullptr;const unsigned char*colors=nullptr;};
struct Re4dcActorSource{const unsigned char*positions,*normals;unsigned position_count,normal_count,palette_entries,small_normals;};
Re4dcActorSource src{};
extern "C" int re4dc_actor_model_source(const void*,Re4dcActorSource*out){*out=src;return 1;}
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**data){*data=nullptr;return 0x00100000U;}
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned){return 0;}
struct Chunk{unsigned position_count=1,normal_count=1,palette_count=1,uv_bytes=4,stream_bytes=32;const unsigned char*positions,*normals,*uv,*stream,*weights;};
struct RegistryView{unsigned geometry_count=1;}registry;Chunk chunks[1];Chunk registry_gview(unsigned g){return chunks[g];}PayloadProof gcasset_registry[2];
''' + selection + r'''
SourceUse gcasset_model_pending;
''' + function(ui, 'void gcasset_model_prepare(') + '\n' + function(ui, 'void gcasset_model_accept(') + r'''
int main(){unsigned char bytes[512]={71},alien[64]={19};const auto digest=fingerprint(bytes,sizeof bytes);char id[41];for(unsigned i=0;i<20;++i)sprintf(id+2*i,"%02x",digest.bytes[i]);CatalogRow row{"geometry",id,digest,PS2};assert(install(&row,1));
 auto&c=chunks[0];c.positions=bytes+64;c.normals=bytes+128;c.uv=bytes+144;c.stream=bytes+160;c.weights=bytes+256;assert(payload_capture(gcasset_registry[0],&registry,bytes,sizeof bytes));src={c.positions,c.normals,1,1,1,0};int model,info;Re4dcModelPart p{&model,&info,c.stream,c.uv};Lighting lighting;p.lighting=&lighting;
 auto accept=[&](){ActorMainSourceScope scope(&p);gcasset_model_prepare(&p);sq=true;gcasset_model_accept();sq=false;payload_flush_all();member_flush();};
 begin(0x111,1,Required);accept();end(1);assert(logs.find("source_geometry=1")!=std::string::npos && logs.find("errors=0")!=std::string::npos);logs.clear();begin(0x111,2,Required);
 c.uv=alien;p.uv=alien;accept();c.uv=bytes+144;p.uv=c.uv;
 c.weights=alien;accept();c.weights=bytes+256;
 p.colors=alien;p.flags=0x80000000U;p.alpha_state=511;accept();p.alpha_state=255;lighting.ambient_vertex=true;accept();lighting.ambient_vertex=false;lighting.material_vertex=true;accept();lighting.material_vertex=false;p.colors=nullptr;p.flags=0;
 p.positions=alien;p.normals=alien;accept();p.positions=p.normals=nullptr;
 end(2);assert(logs.find("source_geometry=0")!=std::string::npos && logs.find("weapon=0")!=std::string::npos);assert(logs.find("errors=0")==std::string::npos && logs.find("unbound-accepted-model")!=std::string::npos);
}
'''
        self.compile_run(fixture)
        color = 'if((part->alpha_state&256) || (part->lighting &&\n       (part->lighting->ambient_vertex || part->lighting->material_vertex)))return {};'
        for label, old, new in [
            ('external UV', 'gcasset_actor_inside(proof,c.uv,uv_bytes)', '(uv_bytes>0)'),
            ('external weights', 'gcasset_actor_inside(proof,c.weights,c.palette_count*16)', '(c.palette_count>0)'),
            ('external colors', color, '(void)part;'),
            ('foreign shape arrays', 'if(!part->positions || (part->positions==source.positions', 'if(true || (part->positions==source.positions'),
        ]:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old), 1)
                self.compile_run(fixture.replace(old,new),reject=True)

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
struct GcFixtureLighting{bool ambient_vertex=false,material_vertex=false;};
struct Re4dcModelPart{const void*model;const void*info;const unsigned char*stream,*uv;unsigned stream_bytes,position_count,normal_count;const unsigned char*positions=nullptr,*normals=nullptr;unsigned position_stride=8,normal_stride=8,normal_shift=14;unsigned alpha_state=255,flags=0;const GcFixtureLighting*lighting=nullptr;const unsigned char*colors=nullptr;float modelview[12]{},projection[7]{},viewport[6]{};unsigned cull=0;};
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
 // Raw generic fallback stays unknown even with matching model/info and
 // complete stream/position/normal spans: UV/color/weights/shape are unproved.
 clear_frames();logs.clear();current_source={bin+64,bin+128,1,1,1,0};p.stream=bin+160;p.uv=bin+144;assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos && logs.find("kind=model")==std::string::npos);
 assert(member_contains(member.serial,bin+480,32) && !member_contains(member.serial,bin+481,32));
 clear_frames();logs.clear();p.stream=bin+500;assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);p.stream=bin+160;
 clear_frames();logs.clear();current_source.normals=alien;assert(re4dc_actor_submit(&p));flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);current_source.normals=bin+128;
 clear_frames();defer=true;assert(re4dc_actor_submit(&p));assert(!queued.serial && !queued.payload);defer=false;current_source={c.positions,c.normals,1,1,1,0};logs.clear();{ReplayScope replay(member.serial,1U<<SourceGeometry);assert(re4dc_actor_submit(&p));}flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);current_source={bin+64,bin+128,1,1,1,0};
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
            ('unproved raw generic', '    // not a UV extent, and an address prefix cannot supply the missing proof.\n    return {};', '    // not a UV extent, and an address prefix cannot supply the missing proof.\n    return previous?*previous:SourceUse{};'),
            ('mixed replay arrays', 'if(current.payload!=saved.payload || current.serial!=saved.serial)return {};', '(void)current;'),
        ]
        for label, old, new in mutants:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old), 1)
                self.compile_run(fixture.replace(old, new), reject=True)

    def compile_run(self, fixture, reject=False, direct=False):
        with tempfile.TemporaryDirectory(prefix='gc-port23-actor-main-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture)
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_NATIVE_MODEL_REGISTRY=1',
                            '-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1', '-DRE4DC_NMR_MASK=1',
                            *(['-DRE4DC_TA_DIRECT=1','-DRE4DC_PVR_STREAM=1','-DRE4DC_SCENERY_SUBMIT_BATCH=1'] if direct else []),
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(root / 'fixture')], check=True)
            result = subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(root / 'fixture')], capture_output=reject, text=True)
            if reject:self.assertNotEqual(result.returncode, 0, 'compiled main gateway mutant escaped runtime assertions')
            else:result.check_returncode()

    def test_actual_fast_gate0_token_identity(self):
        with tempfile.TemporaryDirectory(prefix='gc-port23-main-off-', dir='/dev/shm') as temporary:
            for unit in ['native_actor_fast.cpp','native_model.cpp']:
                path = 'port/dreamcast/game/platform/'+unit
                old = subprocess.check_output(['git', '-C', str(GAME.parents[2]), 'show', 'd62995038:' + path], text=True)
                current = (GAME / 'platform' / unit).read_text();files=[]
                for label, text in [('old', old), ('current', current)]:
                    path = Path(temporary) / (label + '.cpp');path.write_text(re.sub(r'^#include .*\n', '', text, flags=re.M));files.append(path)
                for coarse,transaction in [(0,0),(1,0),(1,1),(2,1)]:
                    streams = [subprocess.check_output(['g++', '-E', '-P', '-DRE4DC_GC_ASSET_GATE=0',
                        '-DRE4DC_COARSE_ONE_SUBMIT='+str(coarse), '-DRE4DC_ACTOR_TRANSACTION='+str(transaction),
                        '-DRE4DC_ACTOR_DIRECT=1', '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1',
                        '-DRE4DC_NATIVE_ACTOR=1','-DRE4DC_NATIVE_ACTOR_FAST=1','-DRE4DC_MODEL_STREAM_FIX=1',str(path)], text=True) for path in files]
                    tokens=lambda text:re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S',text)
                    self.assertEqual(tokens(streams[0]),tokens(streams[1]))


if __name__ == '__main__':unittest.main()
