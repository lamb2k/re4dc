"""Bounded exact actor source proofs, without origin inference from adapters."""
from pathlib import Path
import hashlib
import struct
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class ActorAssetTests(unittest.TestCase):
    def test_actual_replacement_weapon_class_and_frozen_replay(self):
        selection = (GAME / 'platform/include/gc_asset_actor_select.inc').read_text()
        bridge = (GAME / 'model_bridge.cpp').read_text()
        fixture = r'''
#include "gc_asset_actor.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace re4dc_gcasset;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
struct cModel{unsigned kindid=0,id=0x10,type=0,nParts=1;};struct cModelInfo{const void*pData=nullptr;};
struct Body{cModelInfo*pRight=nullptr,*pLeft=nullptr;};struct Player:cModel{struct Body*Body=nullptr;}player;Player*pPL=&player;
''' + function(bridge, 'extern "C" unsigned re4dc_gcasset_model_identity(') + '\n' + function(bridge, 'extern "C" unsigned re4dc_gcasset_weapon_consumer(') + r'''
struct Re4dcModelPart{const void*model;const void*info;const unsigned char*stream,*uv;unsigned stream_bytes,position_count,normal_count;};
struct Re4dcActorSource{const unsigned char*positions,*normals;unsigned position_count,normal_count,palette_entries,small_normals;};
struct Chunk{unsigned position_count=1,normal_count=1,palette_count=1,uv_bytes=4,stream_bytes=32;const unsigned char*positions,*normals,*uv,*stream,*weights;};
struct RegistryView{unsigned geometry_count=1;}registry;Chunk chunks[1];Chunk registry_gview(unsigned g){return chunks[g];}PayloadProof gcasset_registry[2];
''' + selection + r'''
void put(std::vector<unsigned char>&a,unsigned offset,unsigned value){memcpy(a.data()+offset,&value,4);}
std::vector<unsigned char> archive(unsigned arc){unsigned count=arc-3,at=16+count*8;std::vector<unsigned char>a(at+96);put(a,0,count);put(a,16+4*(count-1),at);put(a,16+4*count+4*(count-1),0x004e4942);a[at]=37;return a;}
const void* adopt(std::vector<unsigned char>&a,OwnerFamily family){assert(member_adopt(&a,a.data(),a.size(),true,family));unsigned count;memcpy(&count,a.data(),4);const void*data=a.data()+16+count*8;assert(member_capture(data));return data;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);unsigned char replacement[512]={91};auto&c=chunks[0];c.positions=replacement;c.normals=replacement+64;c.uv=replacement+128;c.stream=replacement+160;c.weights=replacement+256;assert(payload_capture(gcasset_registry[0],&registry,replacement,sizeof replacement));
 cModel model;cModelInfo info;Re4dcModelPart p{&model,&info,c.stream,c.uv,32,1,1};Re4dcActorSource source{c.positions,c.normals,1,1,1,0};
 const unsigned geometry=1U<<SourceGeometry,weapon=geometry|(1U<<Weapon);
 auto selected=[&](){sq=true;auto use=re4dc_gcasset_actor_select(&p,&source);sq=false;return use;};
 auto check=[&](unsigned kind,unsigned id,unsigned mask){model.kindid=kind;model.id=id;assert(selected().mask==mask);};
 // Held, dropped launcher, thrown and player-backed projectiles are consumer
 // classes even when current m_pWep is absent. No source pointer is provenance.
 for(unsigned id:{0x21U,0x23U,0x24U,0x25U,0x27U,0x28U,0x2bU,0x2cU,0x2dU,0x2eU,0x2fU,0x30U,0x31U,0x32U,0x33U,0x34U,0x36U,0x3cU,0x3dU,0x1aU,0x22U,0x29U,0x2aU,0x3aU})check(1,id,weapon);
 check(0,0x10,geometry);check(1,2,geometry);check(1,0x0a,0);check(0,0x4f,0);
 auto shell=archive(0x7a),mine=archive(0x72),other=archive(4);const void*shell_data=adopt(shell,PlayerOwner);const void*mine_data=adopt(mine,PlayerOwner);const void*other_data=adopt(other,OtherOwner);
 info.pData=shell_data;check(1,0x0a,weapon);check(0,0x4f,geometry);info.pData=mine_data;check(0,0x4f,weapon);check(1,0x0a,geometry);info.pData=other_data;check(1,0x0a,geometry);check(0,0x4f,geometry);
 member_retire(&other);adopt(other,WeaponOwner);check(1,2,weapon);
 Body body;player.Body=&body;body.pRight=&info;p.model=&player;player.kindid=0;player.id=0;assert(selected().mask==weapon);body.pRight=nullptr;assert(selected().mask==weapon); // weapon-family original member
 info.pData=nullptr;assert(selected().mask==geometry);body.pLeft=&info;assert(selected().mask==weapon);body.pLeft=nullptr;p.model=&model;
 // Accepted replacement emits its own whole-source identity for BOTH classes;
 // the original BIN is used only for consumer attribution.
 info.pData=shell_data;model.kindid=1;model.id=0x0a;const auto saved=selected();assert(saved.payload==&gcasset_registry[0] && saved.mask==weapon);
 sq=true;{ActorSourceScope scope(&p,&source);scope.accepted();}sq=false;payload_flush_all();end(1);assert(logs.find("source_geometry=1")!=std::string::npos && logs.find("weapon=1")!=std::string::npos);assert(logs.find("kind=geometry")!=std::string::npos && logs.find("kind=model_bin")==std::string::npos);
 AssetDescription row;assert(describe_checked(saved.payload->asset,&row));assert(row.provenance==Unknown && !memcmp(row.digest.bytes,fingerprint(replacement,sizeof replacement).bytes,32));
 // Retirement removes ambiguous classification; saved replay keeps the exact
 // earlier class mask, never recapturing a new current model/BIN role.
 member_retire(&shell);assert(!selected().serial);info.pData=nullptr;model.kindid=0;model.id=0x10;
 {ReplayScope replay(saved.serial,saved.mask,saved.payload);auto use=selected();assert(use.serial==saved.serial && use.payload==saved.payload && use.mask==weapon);}
 begin(0x111,2,Required);logs.clear();payload_retire(gcasset_registry[0]);sq=true;{ReplayScope replay(saved.serial,saved.mask,saved.payload);ActorSourceScope scope(&p,&source);scope.accepted();}sq=false;payload_flush_all();assert(logs.find("unbound-accepted-payload")!=std::string::npos && logs.find("GC-ASSET v=")==std::string::npos);
}
'''
        definitions = ['-DRE4DC_NATIVE_MODEL_REGISTRY=1', '-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1', '-DRE4DC_NMR_MASK=1']
        self.compile_run(fixture, definitions, bridge_stubs=False)
        # These mutants compile the same actual bodies; each must fail an
        # executed assertion, rather than merely fail a text-presence check.
        ambiguous = 'if(!bound && ((kind==1 && id==0x0a) || (kind==0 && id==0x4f)))return 0;'
        replay = function(selection, '    if(replay_use.serial!=0xffffffffU)')
        for label, old, new in [('drop Weapon', '?1U<<Weapon:0U', '?0U:0U'),
                                ('unbound shared class', ambiguous, 'if(!bound && kind==255 && id==255)return 0;'),
                                ('recapture replay', replay, '')]:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old), 1)
                self.compile_run(fixture.replace(old, new), definitions, bridge_stubs=False, reject=True)

    def test_actual_compiled_capture_and_selection(self):
        compiled = (GAME / 'platform/include/gc_asset_actor_compiled.inc').read_text()
        selection = (GAME / 'platform/include/gc_asset_actor_select.inc').read_text()
        fixture = r'''
#include "gc_asset_actor.h"
#include "coarse_actor_preflight.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include <string>
using namespace re4dc_gcasset;
std::string logs;extern "C" void re4dc_log(const char*fmt,...){char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
struct Re4dcModelPart{const void*model;const void*info;const unsigned char*stream,*uv;unsigned stream_bytes,position_count,normal_count;};
struct Re4dcActorSource{const unsigned char*positions,*normals;unsigned position_count,normal_count,palette_entries,small_normals;};
namespace leon4k{struct Chunk{unsigned source_info,position_count=1,normal_count=1,palette_count=1,triangles=1,stream_bytes=32;const unsigned char*positions,*normals,*uv,*stream,*weights;};Chunk chunks[8];float bind[2][12]{};}
unsigned char arrays[8][5][32]{};
re4dc_source::ChunkInput input_for(unsigned k){return {{arrays[k][0],8},{arrays[k][1],8},{arrays[k][2],4},{arrays[k][3],32},{arrays[k][4],16},1,1,1,1,119};}
#define RE4DC_OWNER_INPUT(ns,prefix,c,bones) input_for(c.source_info)
namespace leon_hair_runs{unsigned char uv[4]={1,2,3,4},stream[32]={9};struct Run{const unsigned char*stream;unsigned bytes;};Run runs[]={{stream,32}};}
#define RE4DC_LEON_HAIR_UV_DATA leon_hair_runs::uv
#define RE4DC_LEON_HAIR_UV_SIZE sizeof(leon_hair_runs::uv)
''' + compiled + '\n' + selection + r'''
int main(){assert(install(nullptr,0));begin_startup_closed(1,Required);
 for(unsigned k=0;k<8;++k){auto&c=leon4k::chunks[k];c.source_info=k;c.positions=arrays[k][0];c.normals=arrays[k][1];c.uv=arrays[k][2];c.stream=arrays[k][3];c.weights=arrays[k][4];arrays[k][3][0]=k;}
 re4dc_gcasset_actor_startup();assert(gcasset_compiled_actor.serial);const unsigned serial=gcasset_compiled_actor.serial;re4dc_gcasset_actor_startup();assert(gcasset_compiled_actor.serial==serial);assert(logs.find("GC-ASSET v=")==std::string::npos);
 const auto&c=leon4k::chunks[0];Re4dcModelPart p{&p,&p,c.stream,c.uv,32,1,1};Re4dcActorSource s{c.positions,c.normals,1,1,1,0};assert(re4dc_gcasset_actor_select(&p,&s).serial==serial);
 const auto&hair=leon4k::chunks[7];p.stream=leon_hair_runs::stream;p.uv=leon_hair_runs::uv;s.positions=hair.positions;s.normals=hair.normals;assert(re4dc_gcasset_actor_select(&p,&s).serial==serial);
 // Dynamic hand descriptors are absent from the compiled identity.
 const auto&hand=leon4k::chunks[5];p.stream=hand.stream;p.uv=hand.uv;s.positions=hand.positions;s.normals=hand.normals;assert(!re4dc_gcasset_actor_select(&p,&s).serial);
 // Descriptor pointer rebinding cannot bless unhashed arrays with this token.
 auto&mutable_c=leon4k::chunks[0];mutable_c.positions=arrays[5][0];p.stream=mutable_c.stream;p.uv=mutable_c.uv;s.positions=mutable_c.positions;s.normals=mutable_c.normals;assert(!re4dc_gcasset_actor_select(&p,&s).serial);
 AssetDescription row;assert(describe_checked(gcasset_compiled_actor.asset,&row) && row.provenance==Unknown);retire_catalog();assert(!describe_checked(gcasset_compiled_actor.asset,&row));
}
'''
        self.compile_run(fixture, ['-DRE4DC_ACTOR_TRANSACTION=1', '-DRE4DC_LEON_HAND_PACK=1', '-DRE4DC_LEON_LOD=0'])

    def test_actual_pack_selection_and_shared_window_acknowledgement(self):
        selection = (GAME / 'platform/include/gc_asset_actor_select.inc').read_text()
        fast = (GAME / 'platform/native_actor_fast.cpp').read_text()
        accepted = function(fast, '    if (e.direct) {\n#if RE4DC_GC_ASSET_GATE\n        if(e.slots)gcasset_actor_scope.accepted();')
        fixture = r'''
#include "gc_asset_actor.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
struct Re4dcModelPart{const void*model;const void*info;const unsigned char*stream,*uv;unsigned stream_bytes,position_count,normal_count;};
struct Re4dcActorSource{const unsigned char*positions,*normals;unsigned position_count,normal_count,palette_entries,small_normals;};
struct Chunk{unsigned position_count=1,normal_count=1,palette_count=1,uv_bytes=4,stream_bytes=32;const unsigned char*positions,*normals,*uv,*stream,*weights;};
struct RegistryView{unsigned geometry_count=2;}registry;Chunk chunks[2];Chunk registry_gview(unsigned g){return chunks[g];}
PayloadProof gcasset_registry[2],gcasset_pl08;
struct P8{bool published=false;struct View{unsigned bytes[5];}view[3];}pl08_pack;Chunk pl08_pack_chunks[3];
''' + selection + r'''
struct Window{unsigned*sq;unsigned slots=0,primed=0;};struct Emission{bool direct=true;unsigned slots=0,primed=0,input=0,output=0;unsigned*sq;};
void re4dc_model_packet_abort(){}void re4dc_model_result(unsigned,unsigned,unsigned){}void one_close(Window&){}
int acknowledge(ActorSourceScope& gcasset_actor_scope,Emission e,Window&w){bool ok=true;
''' + accepted + r'''
return 0;}
unsigned rows(){unsigned n=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++at;++n;}return n;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);unsigned char data[3][512]={{1},{2},{3}};
 for(unsigned i=0;i<2;++i){auto&c=chunks[i];c.positions=data[i];c.normals=data[i]+64;c.uv=data[i]+128;c.stream=data[i]+160;c.weights=data[i]+256;assert(payload_capture(gcasset_registry[i],&gcasset_registry[i],data[i],512));}
 Re4dcModelPart p{&p,&p,chunks[0].stream,chunks[0].uv,32,1,1};Re4dcActorSource s{chunks[0].positions,chunks[0].normals,1,1,1,0};Window w{};Emission e{};unsigned queue[32];e.sq=queue;w.sq=queue;
 source_use.serial=99;{ActorSourceScope scope(&p,&s);assert(scope.selected.payload==&gcasset_registry[0]);sq=true;e.slots=3;acknowledge(scope,e,w);sq=false;}assert(source_use.serial==99);
 // A second owner shares the real OneWindow: it still gets its own acknowledgement.
 p.stream=chunks[1].stream;p.uv=chunks[1].uv;s.positions=chunks[1].positions;s.normals=chunks[1].normals;
 {ActorSourceScope scope(&p,&s);assert(scope.selected.payload==&gcasset_registry[1]);sq=true;acknowledge(scope,e,w);sq=false;}payload_flush_all();assert(rows()==2 && w.slots==6);
 end(1);begin(0x111,2,Required);logs.clear();{ActorSourceScope scope(&p,&s);sq=true;e.slots=0;acknowledge(scope,e,w);sq=false;}payload_flush_all();assert(logs.empty());
 // Mixed arrays or an out-of-range stream cannot inherit the previous owner.
 p.stream=chunks[0].stream;{ActorSourceScope scope(&p,&s);assert(!scope.selected.serial);sq=true;e.slots=3;acknowledge(scope,e,w);sq=false;}payload_flush_all();assert(!rows() && logs.find("unbound-accepted-payload")!=std::string::npos);
 logs.clear();p.stream=chunks[1].stream+30;assert(!re4dc_gcasset_actor_select(&p,&s).serial);p.stream=chunks[1].stream;
 // Replay preserves its frozen payload serial, even while current source arrays match another live owner.
 {ReplayScope replay(gcasset_registry[0].serial,1U<<SourceGeometry,&gcasset_registry[0]);ActorSourceScope scope(&p,&s);
  assert(scope.selected.payload==&gcasset_registry[0] && scope.selected.serial==gcasset_registry[0].serial);}
 {ReplayScope replay(0,0);ActorSourceScope scope(&p,&s);assert(!scope.selected.serial);}
 {ActorSourceScope scope(&p,&s);payload_retire(gcasset_registry[1]);sq=true;acknowledge(scope,e,w);sq=false;}payload_flush_all();assert(!rows() && logs.find("unbound-accepted-payload")!=std::string::npos);
}
'''
        self.compile_run(fixture, ['-DRE4DC_NATIVE_MODEL_REGISTRY=1', '-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1',
                                   '-DRE4DC_NMR_MASK=1', '-DRE4DC_ACTOR_PL08=1', '-DRE4DC_ACTOR_PL08_PACK=1'])

    def test_actual_registry_and_pl08_capture_retire_hooks(self):
        registry = (GAME / 'coarse_actor_registry_pack.inc').read_text()
        pl08 = (GAME / 'coarse_actor_pl08_pack.inc').read_text()
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;
extern "C" void re4dc_log(const char*fmt,...){char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
PayloadProof gcasset_registry[2],gcasset_pl08;
''' + function(registry, 'void gcasset_registry_capture(') + '\n' + function(registry, 'void gcasset_registry_retire(') + r'''
namespace leon4k{struct Weight{};struct Chunk{unsigned source_info,position_count,normal_count,palette_count,triangles,stream_bytes;const unsigned char*positions,*normals,*uv,*stream;const Weight*weights;};}
struct Pl08ChunkView{const unsigned char*array[5];unsigned bytes[5];unsigned source_info,position_count,normal_count,palette_count,triangles;};
struct Pl08PackLife{unsigned char*base;}pl08_pack;
constexpr unsigned kPl08PackBytes=64;leon4k::Chunk pl08_pack_chunks[3];
unsigned frees;void re4dc_static_free(unsigned char*){assert(!gcasset_pl08.serial);++frees;}
''' + function(pl08, 'void pl08_hook_published(const Pl08ChunkView* v) {') + '\n' + function(pl08, 'void pl08_hook_free(') + r'''
int main(){assert(install(nullptr,0));begin(0x111,1,Required);unsigned char a[64]={1},b[64]={2},c[64]={3};
 gcasset_registry_capture(0,a,sizeof a);gcasset_registry_capture(1,b,sizeof b);assert(gcasset_registry[0].serial && gcasset_registry[1].serial);assert(logs.find("GC-ASSET v=")==std::string::npos);
 AssetDescription row;assert(describe_checked(gcasset_registry[1].asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(b,sizeof b).bytes,32));
 const unsigned old=gcasset_registry[0].serial;gcasset_registry_retire();assert(!gcasset_registry[0].serial && !gcasset_registry[1].serial);
 a[0]=4;gcasset_registry_capture(0,a,sizeof a);assert(gcasset_registry[0].serial>old);assert(describe_checked(gcasset_registry[0].asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(a,sizeof a).bytes,32));gcasset_registry_retire();
 pl08_pack.base=c;Pl08ChunkView view[3]{};pl08_hook_published(view);assert(gcasset_pl08.serial);const unsigned p8serial=gcasset_pl08.serial;assert(describe_checked(gcasset_pl08.asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(c,sizeof c).bytes,32));
 pl08_hook_published(nullptr);assert(!gcasset_pl08.serial);c[0]=5;pl08_hook_published(view);assert(gcasset_pl08.serial>p8serial);assert(describe_checked(gcasset_pl08.asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(c,sizeof c).bytes,32));pl08_hook_free(c);assert(frees==1);
}
'''
        self.compile_run(fixture)
        # Actual capture is before preflight/skin work; actual failure/free and
        # room leave revoke the two proofs. This audit complements the executed
        # hook bodies; it is not a claim that accepted actor paths are complete.
        self.assertLess(registry.index('gcasset_registry_capture(0,base,a.size)'), registry.index('why=pack_preflight(base,detail,geometries)'))
        leave = function(registry, 'extern "C" void re4dc_registry_room_leave()')
        self.assertLess(leave.index('gcasset_registry_retire()'), leave.index('re4dc_static_free(pack.cell)'))

    def compile_run(self, fixture, definitions=(), bridge_stubs=True, reject=False):
        if bridge_stubs:
            fixture += '''
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**data){*data=nullptr;return 0x00100000U;}
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned){return 0;}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-actor-source-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', *definitions, '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            str(GAME / 'platform/gc_asset_members.cpp'), str(GAME / 'platform/gc_asset_payloads.cpp'),
                            '-o', str(executable)], check=True)
            result = subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], capture_output=reject, text=True)
            if reject:self.assertNotEqual(result.returncode, 0, 'compiled negative mutant escaped runtime controls')
            else:result.check_returncode()

    def test_compiled_fragment_identity_and_retirement(self):
        spans = [b'ab', b'c']
        encoded = b'GCFRAG01'+struct.pack('<II', len(spans), 0)
        encoded += b''.join(struct.pack('<I', len(span))+span for span in spans)
        digest = hashlib.sha256(encoded).digest()
        large = [b'x'*513, b'y'*900]
        large_digest = hashlib.sha256(b'GCFRAG01'+struct.pack('<II', 2, 0)+b''.join(struct.pack('<I', len(s))+s for s in large)).digest()
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;bool sq;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);int owner,other;PayloadProof proof,alias;
 PayloadSpan spans[]={{"ab",2},{"c",1}};assert(payload_capture_fragments(proof,&owner,spans,2));
 AssetDescription row;assert(describe_checked(proof.asset,&row));unsigned char expected[]={DIGEST};assert(!memcmp(expected,row.digest.bytes,32));assert(row.provenance==Unknown);
 const unsigned serial=proof.serial;{PayloadScope scope(proof,&owner);sq=true;payload_accept(source_use.payload,source_use.serial,1U<<SourceGeometry);sq=false;}payload_flush_all();assert(logs.find("consumer=source_geometry")!=std::string::npos);
 payload_retire(proof);logs.clear();sq=true;payload_accept(&proof,serial,1U<<Weapon);sq=false;payload_flush_all();assert(logs.find("unbound-accepted-payload")!=std::string::npos);
 PayloadSpan other_split[]={{"a",1},{"bc",2}};assert(payload_capture_fragments(proof,&owner,other_split,2));assert(describe_checked(proof.asset,&row));assert(memcmp(expected,row.digest.bytes,32)); // lengths are authoritative
 assert(!payload_capture_fragments(alias,&owner,spans,2));assert(!proof.serial); // conflicting same owner revokes old
 assert(!payload_capture_fragments(proof,&owner,nullptr,2));assert(!payload_capture_fragments(proof,&owner,spans,49));
 PayloadSpan bad[]={{nullptr,1}};assert(!payload_capture_fragments(proof,&owner,bad,1));bad[0]={"a",0};assert(!payload_capture_fragments(proof,&owner,bad,1));bad[0]={"a",40U*1024*1024};assert(!payload_capture_fragments(proof,&owner,bad,1));
 char large_a[513],large_b[900];memset(large_a,'x',sizeof large_a);memset(large_b,'y',sizeof large_b);PayloadSpan large[]={{large_a,sizeof large_a},{large_b,sizeof large_b}};
 assert(payload_capture_fragments(proof,&other,large,2));assert(proof.serial>serial);assert(describe_checked(proof.asset,&row));unsigned char expected_large[]={LARGE_DIGEST};assert(!memcmp(expected_large,row.digest.bytes,32));
 retire_catalog();logs.clear();payload_accept(&proof,proof.serial,1U<<SourceGeometry);payload_flush_all();assert(logs.find("catalog-token")!=std::string::npos);
}
'''.replace('LARGE_DIGEST', ','.join(map(str, large_digest))).replace('DIGEST', ','.join(map(str, digest)))
        self.compile_run(fixture)


if __name__ == '__main__':unittest.main()
