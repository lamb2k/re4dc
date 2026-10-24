"""Compile the actual native_ui texture hook bodies with a tiny fake renderer."""
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


def function(source, marker):
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 1
    cursor = opening + 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[start:cursor]


class RuntimeTextureTests(unittest.TestCase):
    def test_actual_payload_scope_latch_and_retirement(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        helpers = ui[ui.index('re4dc_gcasset::SourceUse gcasset_model_pending;'):ui.index('void gcasset_packet_reset()')]
        fixture = (HERE / 'test_payloads.cpp').read_text().replace('// ACTUAL_UI_HELPERS', helpers)
        with tempfile.TemporaryDirectory(prefix='gc-port23-payload-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_weapon_consumer_roles(self):
        classifier = function((GAME / 'model_bridge.cpp').read_text(), 'extern "C" unsigned re4dc_gcasset_weapon_consumer(')
        fixture = r'''
#include "gc_asset_members.h"
#include "gc_asset_payloads.h"
#include <cassert>
struct cModel{unsigned kindid,id;};struct Body{const void* pRight;const void* pLeft;};
struct cPlayer:cModel{::Body* Body;};cPlayer* pPL;
''' + classifier + r'''
int main(){using namespace re4dc_gcasset;int info,other;cModel model{1,0};
  const unsigned ids[]={0x21,0x23,0x24,0x25,0x27,0x28,0x2b,0x2c,0x2d,0x2e,0x2f,0x30,0x31,0x32,0x33,0x34,0x36,0x3c,0x3d,0x1a,0x22,0x29,0x2a,0x3a};
  for(unsigned id:ids){model.id=id;assert(re4dc_gcasset_weapon_consumer(&model,&info,4,OtherOwner));}
  model.id=0x0a;assert(!re4dc_gcasset_weapon_consumer(&model,&info,0x7a,OtherOwner));
  assert(!re4dc_gcasset_weapon_consumer(&model,&info,0x2d,OtherOwner)); // enemy debris counterexample
  assert(re4dc_gcasset_weapon_consumer(&model,&info,0x7a,PlayerOwner));
  assert(!re4dc_gcasset_weapon_consumer(&model,&info,0x79,PlayerOwner));
  assert(re4dc_gcasset_weapon_consumer(&model,&info,4,WeaponOwner));
  model={0,0x4f};assert(re4dc_gcasset_weapon_consumer(&model,&info,0x72,PlayerOwner));
  assert(!re4dc_gcasset_weapon_consumer(&model,&info,0x72,OtherOwner));
  assert(!re4dc_gcasset_weapon_consumer(&model,&info,0x73,PlayerOwner));
  Body body{&info,nullptr};cPlayer player{{0,0},&body};pPL=&player;
  assert(re4dc_gcasset_weapon_consumer(pPL,&info,0x12,PlayerOwner));
  assert(!re4dc_gcasset_weapon_consumer(pPL,&other,0x12,PlayerOwner)); // whole-player is not a weapon
  body.pRight=nullptr;body.pLeft=&info;assert(re4dc_gcasset_weapon_consumer(pPL,&info,0x14,PlayerOwner));
  assert(!re4dc_gcasset_weapon_consumer(nullptr,&info,4,WeaponOwner));
  pPL=nullptr;
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-weapon-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_raw_replay_is_explicitly_unqualified(self):
        model = (GAME / 'platform/native_model.cpp').read_text()
        start = model.index('extern "C" void re4dc_model_submit(const Re4dcModelPart* p){')
        gateway = model[start:model.index('#if RE4DC_NATIVE_ACTOR\n', start)]+'observe_selected(p);\n}\n'
        bridge = function((GAME / 'model_bridge.cpp').read_text(), 'extern "C" unsigned re4dc_gcasset_model_identity(')
        classifier = function((GAME / 'model_bridge.cpp').read_text(), 'extern "C" unsigned re4dc_gcasset_weapon_consumer(')
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        helpers = ui[ui.index('re4dc_gcasset::SourceUse gcasset_model_pending;'):ui.index('void gcasset_packet_reset()')]
        fixture = r'''
#include "gc_asset_members.h"
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <string>
#include <vector>
struct cModel{unsigned kindid,id,type,nParts;};struct cModelInfo{const void* pData;};
struct Body{const void* pRight;const void* pLeft;};struct cPlayer:cModel{::Body* Body;};cPlayer* pPL;
struct Re4dcModelPart{const void* model;const void* info;unsigned serial;const void* world;const void* view;unsigned source_key[3];const void* stream;};
std::string logs;bool sq_held;
extern "C" void re4dc_log(const char* fmt,...){assert(!sq_held);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
#define RE4DC_PROFILE_SCOPE(...) ((void)0)
#define RE4DC_MODEL_DIAG() true
#define PP_PATH(...) ((void)0)
bool re4dc_static_submit(const Re4dcModelPart*){return false;}
''' + bridge + '\n' + classifier + '\n' + helpers + r'''
void observe_selected(const Re4dcModelPart* p){gcasset_model_prepare(p);sq_held=true;gcasset_model_accept();sq_held=false;}
''' + gateway + r'''
std::vector<unsigned char> blob(unsigned byte){std::vector<unsigned char>b(128);unsigned one=1,off=32;std::memcpy(b.data(),&one,4);std::memcpy(b.data()+16,&off,4);std::memcpy(b.data()+20,"BIN",3);b[40]=byte;return b;}
std::string id(const re4dc_gcasset::ModelMember&m){re4dc_gcasset::AssetDescription row;assert(re4dc_gcasset::describe_checked(m.asset,&row));return row.id;}
int main(){using namespace re4dc_gcasset;int ownerA,ownerB;cModel model{};auto a=blob(1),b=blob(2);ModelMember ma,mb;
 install(nullptr,0);begin(0x111,1,Required);assert(member_adopt(&ownerA,a.data(),128,true)&&member_capture(a.data()+32));assert(member_adopt(&ownerB,b.data(),128,true)&&member_capture(b.data()+32));assert(member_lookup(a.data()+32,&ma)&&member_lookup(b.data()+32,&mb));
 cModelInfo info{b.data()+32};Re4dcModelPart queued{&model,&info,0,nullptr,nullptr,{0,0,0},a.data()+32};
 {ReplayScope replay(ma.serial,1U<<SourceGeometry);re4dc_model_submit(&queued);}member_flush();
 assert(logs.find("unbound-accepted-model")!=std::string::npos);assert(logs.find("id="+id(ma))==std::string::npos && logs.find("id="+id(mb))==std::string::npos);
 logs.clear();member_retire(&ownerA);
 {ReplayScope replay(ma.serial,1U<<SourceGeometry);re4dc_model_submit(&queued);}member_flush();
 assert(logs.find("unbound-accepted-model")!=std::string::npos);assert(logs.find("id="+id(mb))==std::string::npos);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-replay-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_NATIVE_STATIC=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_members.cpp'), str(GAME / 'platform/gc_asset_payloads.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_source_gateway_and_deferred_serial(self):
        source = (GAME / 'platform/native_model.cpp').read_text()
        start = source.index('extern "C" void re4dc_model_submit(const Re4dcModelPart* p){')
        finish = source.index('#if RE4DC_NATIVE_ACTOR\n', start)
        gateway = source[start:finish]+'observe_selected(p);\n}\n'
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        start = ui.index('#if RE4DC_GC_ASSET_GATE', ui.index('    node->lighting=lighting;', ui.index('int defer_part(')))
        finish = ui.index('#endif', start)+len('#endif')
        enqueue = ui[start:finish]
        replay = next(line.strip() for line in ui.splitlines() if 'ReplayScope gcasset_replay_scope(' in line)
        fixture = r'''
#include "gc_asset_members.h"
#include "gc_asset_payloads.h"
#include <cassert>
namespace re4dc_gcasset {SourceUse source_use;ReplayUse replay_use;}
struct Re4dcModelPart {const void* model;const void* info;unsigned serial;const void* world;const void* view;unsigned source_key[3];const void* stream;};
struct Info {const void* data;};
unsigned a,b,lookups,selections,expected=0,calls;bool replace;
#define RE4DC_PROFILE_SCOPE(...) ((void)0)
#define RE4DC_MODEL_DIAG() true
#define PP_PATH(...) ((void)0)
int re4dc_static_submit(const Re4dcModelPart*){assert(!re4dc_gcasset::source_use.serial);++calls;return replace;}
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void* info,const void** data){*data=static_cast<const Info*>(info)->data;return 0;}
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned){return 0;}
bool re4dc_gcasset::member_lookup(const void* data,ModelMember* out){++lookups;out->serial=data==&a?77:88;return true;}
void observe_selected(const Re4dcModelPart*){++selections;assert(re4dc_gcasset::source_use.serial==expected);}
''' + gateway + r'''
struct DeferredPart{unsigned asset_serial=0,asset_mask=0;re4dc_gcasset::PayloadProof* asset_payload=nullptr;};
void freeze(DeferredPart* node,const Re4dcModelPart& view){
''' + enqueue + r'''
}
void replay(DeferredPart* deferred_first,const Re4dcModelPart& view){
''' + replay + r'''
  re4dc_model_submit(&view);
}
int main(){
  using namespace re4dc_gcasset;
  int model;Info info{&a};Re4dcModelPart p{&model,&info,0,&a,&a,{1,2,3},&a};
  source_use.serial=99;replace=true;re4dc_model_submit(&p);assert(calls==1&&!selections&&source_use.serial==99);
  replace=false;re4dc_model_submit(&p);assert(calls==2&&selections==1&&lookups==1&&source_use.serial==99);
  source_use={77,1U<<SourceGeometry,p.model,p.info};DeferredPart node;freeze(&node,p);
  assert(node.asset_serial==77);
  info.data=&b;source_use.serial=99;expected=0;replay(&node,p);
  assert(p.stream==&a && info.data==&b && lookups==1 && source_use.serial==99);
  assert(replay_use.serial==0xffffffffU); // replay cannot relabel old A geometry using current B info
  expected=0;re4dc_model_submit(&p);assert(lookups==2);
  // An unqualified/static enqueue carries explicit zero, never a fresh lookup.
  source_use={};DeferredPart unknown;freeze(&unknown,p);expected=0;replay(&unknown,p);assert(lookups==2);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-gateway-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_NATIVE_STATIC=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_source_latch_packet_direct_and_switch(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        helpers = ui[ui.index('re4dc_gcasset::SourceUse gcasset_model_pending;'):ui.index('void gcasset_packet_reset()')]
        commit = function(ui, 'extern "C" void re4dc_model_packet_commit(')
        marker = ui.index('// WORLD_SUBMIT_END_IMPLEMENTATION')
        start = ui.index('#if RE4DC_TA_DIRECT', marker)
        finish = ui.index('\n}\n#if RE4DC_SCENERY_SUBMIT_BATCH', start)+2
        direct = 'void direct_account(unsigned vertices){\n'+ui[start:finish]
        switch = function(ui, 'extern "C" std::uint32_t* re4dc_leon_direct_switch(')
        start = switch.index('    // re4dc_model_direct_end(vertices)')
        finish = switch.index('    model_used=0;', start)+len('    model_used=0;')
        fixture = r'''
#include "gc_asset_members.h"
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace re4dc_gcasset;
struct Re4dcModelPart {const void* model;const void* info;};
bool sq_held;
std::string logs;
extern "C" void re4dc_log(const char* fmt,...){
  assert(!sq_held);char buf[256];va_list ap;va_start(ap,fmt);vsnprintf(buf,sizeof buf,fmt,ap);va_end(ap);logs+=buf;
}
struct Handle{unsigned frame;};Handle handle;Handle* model_handle=&handle;
unsigned model_used,model_pending,model_peak,frame,direct_parts,direct_slots,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes;
unsigned char model_packets[1024];
void stream_send(const void*,unsigned){}
void re4dc_missing(const char*){assert(false);}
#define RE4DC_GCA_TEXTURE(...) ((void)0)
#define RE4DC_GCA_MODEL_TEXTURE(...) ((void)0)
''' + helpers + r'''
#define RE4DC_GCA_MODEL_ACCEPT() gcasset_model_accept()
#define RE4DC_GCA_MODEL_PACKET_ACCEPT(vertices,count) gcasset_model_accept(vertices,count)
''' + commit + '\n' + direct + '\nvoid switch_account(unsigned vertices){\n' + switch[start:finish] + r'''
}
int main(){
  std::vector<unsigned char> blob(128);unsigned one=1,offset=32;int owner,model,info;
  std::memcpy(blob.data(),&one,4);std::memcpy(blob.data()+16,&offset,4);std::memcpy(blob.data()+20,"BIN",3);
  install(nullptr,0);begin(0x111,1,Required);
  assert(member_adopt(&owner,blob.data(),128,true));assert(member_capture(blob.data()+32));
  ModelMember m;assert(member_lookup(blob.data()+32,&m));
  Re4dcModelPart p{&model,&info};source_use={m.serial,1U<<SourceGeometry,p.model,p.info};
  gcasset_model_prepare(&p);re4dc_model_packet_commit(0);member_flush();
  assert(logs.find("GC-ASSET v=")==std::string::npos); // prepared/clipped source emits nothing
  re4dc_model_packet_commit(3);member_flush();assert(logs.find("consumer=source_geometry")!=std::string::npos);
  logs.clear();sq_held=true;direct_account(3);assert(logs.empty());sq_held=false;member_flush();
  sq_held=true;switch_account(3);assert(logs.empty());sq_held=false;member_flush();
  // A replacement/static path runs inside a cleared SourceScope, and cannot
  // inherit even the exact same source caller's identity merely by API/name.
  {SourceScope replacement;gcasset_model_prepare(&p);}
  sq_held=true;direct_account(3);assert(logs.empty());sq_held=false;member_flush();
  assert(logs.find("unbound-accepted-model")!=std::string::npos);
  logs.clear();gcasset_model_prepare(&p);member_retire(&owner);
  sq_held=true;switch_account(3);assert(logs.empty());sq_held=false;member_flush();
  assert(logs.find("unbound-accepted-model")!=std::string::npos); // late retained snapshot cannot survive retire
  // Exact accepted mixed-owner quad batch; no whole-batch first-owner inference.
  end(1);assert(install(nullptr,0));begin(0x113,2,Required);logs.clear();
  PayloadProof a,b;int oa,ob;unsigned char ba[32]={4},bb[32]={5};
  assert(payload_capture(a,&oa,ba,32) && payload_capture(b,&ob,bb,32));
  PayloadQuadUse uses[]={{&a,a.serial,1U<<SourceGeometry},{&b,b.serial,1U<<SourceGeometry}};
  PayloadQuadBatch batch{uses,2,model_packets+model_pending,8};
  {PayloadQuadScope scope(batch);sq_held=true;re4dc_model_packet_commit(0);sq_held=false;}
  payload_flush_all();assert(logs.empty());
  {PayloadQuadScope scope(batch);sq_held=true;re4dc_model_packet_commit(8);sq_held=false;}
  payload_flush_all();assert(logs.find("unique") == std::string::npos);
  unsigned emitted=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++emitted;++at;}assert(emitted==2);
  for(unsigned mode=0;mode<3;++mode){logs.clear();
    if(mode==0)batch.vertices=model_packets+1;
    if(mode==1){batch.vertices=model_packets;batch.vertex_count=7;}
    if(mode==2){batch.vertex_count=8;payload_retire(b);}
    {PayloadQuadScope scope(batch);sq_held=true;re4dc_model_packet_commit(8);sq_held=false;}
    payload_flush_all();assert(logs.find("GC-ASSET v=")==std::string::npos && logs.find("unbound-accepted-payload")!=std::string::npos);
  }
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-source-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_PVR_STREAM=1',
                            '-DRE4DC_TA_DIRECT=1', '-DRE4DC_SCENERY_SUBMIT_BATCH=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'), str(GAME / 'platform/gc_asset_payloads.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_archive_bind_and_retire_bodies(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        bodies = '\n'.join(function(ui, 'extern "C" '+signature) for signature in (
            'int re4dc_ui_bind_core(', 'int re4dc_ui_bind_room(', 'int re4dc_ui_bind_option(',
            'int re4dc_ui_bind_player(', 'int re4dc_ui_bind_weapon(', 'int re4dc_ui_bind_enemy(',
            'void re4dc_ui_unbind_option(', 'void re4dc_ui_unbind_player(',
            'void re4dc_ui_unbind_weapon(', 'void re4dc_ui_unbind_enemy('))
        loader = (GAME.parents[2] / 'src/game/read.cpp').read_text()
        reload = function(loader, 'void CoreDataRead()\n{')
        retire = reload[reload.index('#if defined(RE4DC_GAME)'):reload.index('    pG->pArc =')]
        fixture = r'''
#include "gc_asset_members.h"
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace re4dc_gcasset;
#define RE4DC_GCA_ADOPT(...) ((void)member_adopt(__VA_ARGS__))
#define RE4DC_GCA_RETIRE(...) member_retire(__VA_ARGS__)
extern "C" void re4dc_log(const char*,...){}
unsigned table_count=1,identity_hits;
namespace re4dc { namespace texture {
struct SourceIdentityTable { bool adopt(void*,unsigned){return true;}unsigned count()const{return table_count;}void clear(){} };
}}
using Table=re4dc::texture::SourceIdentityTable;
Table core_identities,room_identities,option_identities,player_identities,weapon_identities;
struct EnemyIdentity{void* archive=nullptr;Table table;};EnemyIdentity enemy_identities[8];
void sources_reset(){}
Digest original;
void check_prepared(void* blob){
    auto* data=static_cast<unsigned char*>(blob)+32;
    assert(member_capture(data));ModelMember m;assert(member_lookup(data,&m));
    AssetDescription row;assert(describe_checked(m.asset,&row));assert(!std::memcmp(row.digest.bytes,original.bytes,32));
}
void re4dc_actor_archive_adopt(const void*,void* blob,unsigned,unsigned){
    check_prepared(blob);static_cast<unsigned char*>(blob)[32]^=1; // simulated relocation/FE mutation
}
void re4dc_actor_archive_retire(const void*){}
void re4dc_model_bind_draw_owner(const void*,void* blob,unsigned,unsigned){check_prepared(blob);}
void re4dc_model_unbind_draw_owner(const void*){}
extern "C" void re4dc_gcasset_retire_archive(const void*);
void* core_reload_base;
#define CORE_DATA_ADDR core_reload_base
void re4dc_effect_unbind(void*){}
''' + bodies + r'''
void actual_core_pre_overwrite(){
''' + retire + r'''
}
std::vector<unsigned char> archive(){
    std::vector<unsigned char> bytes(128);unsigned count=1,offset=32;
    std::memcpy(bytes.data(),&count,4);std::memcpy(bytes.data()+16,&offset,4);
    std::memcpy(bytes.data()+20,"BIN",3);return bytes;
}
int main(){
    auto core=archive(),room=archive(),option=archive(),player=archive(),weapon=archive(),enemy=archive(),plain=archive();
    assert(install(nullptr,0));
    original=fingerprint(core.data()+32,96);
    assert(re4dc_ui_bind_core(core.data(),128));assert(re4dc_ui_bind_room(room.data(),128));
    assert(re4dc_ui_bind_option(option.data(),128));assert(re4dc_ui_bind_player(player.data(),128));
    assert(re4dc_ui_bind_weapon(weapon.data(),128));assert(re4dc_ui_bind_enemy(enemy.data(),128));
    table_count=0;assert(re4dc_ui_bind_enemy(plain.data(),128)); // ordinary archive early return
    ModelMember m;
    assert(member_lookup(player.data()+32,&m) && m.family==PlayerOwner);
    assert(member_lookup(weapon.data()+32,&m) && m.family==WeaponOwner);
    re4dc_ui_unbind_player();assert(!member_lookup(player.data()+32,&m));
    re4dc_ui_unbind_weapon();assert(!member_lookup(weapon.data()+32,&m));
    re4dc_ui_unbind_option();assert(!member_lookup(option.data()+32,&m));
    re4dc_ui_unbind_enemy(enemy.data());assert(!member_lookup(enemy.data()+32,&m));
    re4dc_ui_unbind_enemy(plain.data());assert(!member_lookup(plain.data()+32,&m));
    member_retire_transient();assert(!member_lookup(room.data()+32,&m));
    assert(member_lookup(core.data()+32,&m)); // resident core survives room retirement
    const unsigned before=m.serial;core_reload_base=core.data();actual_core_pre_overwrite();
    assert(!member_lookup(core.data()+32,&m)); // actual loader retires before DVD overwrite
    core[40]=99;original=fingerprint(core.data()+32,96);
    assert(re4dc_ui_bind_core(core.data(),128));assert(member_lookup(core.data()+32,&m));
    AssetDescription row;assert(describe_checked(m.asset,&row));assert(m.serial!=before && !std::memcmp(row.digest.bytes,original.bytes,32));
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-bind-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_GAME=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_members.cpp'), str(GAME / 'platform/gc_asset_payloads.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_direct_and_batched_end_bodies(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        static = (GAME / 'platform/native_static.cpp').read_text()
        marker = ui.index('// WORLD_SUBMIT_END_IMPLEMENTATION')
        begin = ui.index('#if RE4DC_TA_DIRECT', marker)
        close = ui.index('\n}\n#if RE4DC_SCENERY_SUBMIT_BATCH', begin) + 2
        body = ui[begin:close]
        prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
struct Re4dcWorldSubmitBatch { std::uint32_t* sq; };
bool sq_held,direct_open;
unsigned direct_parts,direct_slots,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes,model_used;
unsigned notices;void* model_handle;
void sq_unlock(){assert(sq_held);sq_held=false;}
void re4dc_missing(const char*){std::abort();}
#define RE4DC_GCA_TEXTURE(...) (++notices)
#define RE4DC_GCA_MODEL_TEXTURE(...) (++notices)
#define RE4DC_GCA_MODEL_ACCEPT() ((void)0)
'''
        for batch in (0, 1):
            if batch:
                declaration = 'static void model_direct_account(unsigned vertices){\n'
                remaining = ui.index('#if RE4DC_SCENERY_SUBMIT_BATCH', close)
                wrappers = '\n'.join(function(ui[remaining:], m) for m in (
                    'extern "C" void re4dc_model_direct_end(unsigned vertices)',
                    'extern "C" void re4dc_ps2_world_batch_close(',
                    'extern "C" void re4dc_ps2_world_direct_end_batch('))
                mesh_method = function(static, 'void end_direct(){if(sq){')
            else:
                declaration = 'extern "C" void re4dc_model_direct_end(unsigned vertices){\n'
                wrappers = ''
                mesh_method = function(static[static.index('#else\n    void end_direct'):], 'void end_direct(){if(sq){')
            fixture = prefix + declaration + body + '\n' + wrappers + r'''
struct Mesh {
  std::uint32_t* sq;unsigned slots;Re4dcWorldSubmitBatch* submit_batch;
''' + mesh_method + r'''
};
int main(){
  std::uint32_t dummy=0;Re4dcWorldSubmitBatch batch{&dummy};
  direct_open=sq_held=true;
  Mesh mesh{&dummy,0,nullptr};mesh.end_direct();assert(notices==0);assert(!sq_held);
  direct_open=sq_held=true;mesh.sq=&dummy;mesh.slots=3;mesh.end_direct();assert(notices==1);assert(!sq_held);
#if RE4DC_SCENERY_SUBMIT_BATCH
  direct_open=sq_held=true;mesh.sq=&dummy;mesh.slots=6;mesh.submit_batch=&batch;mesh.end_direct();
  assert(notices==2);assert(sq_held);assert(!direct_open); // account while the shared SQ remains locked
  re4dc_ps2_world_batch_close(&batch);assert(!sq_held);
#else
  (void)batch;
#endif
}
'''
            with tempfile.TemporaryDirectory(prefix='gc-port23-direct-', dir='/dev/shm') as temporary:
                root = Path(temporary)
                (root / 'fixture.cpp').write_text(fixture)
                executable = root / 'fixture'
                subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                                '-DRE4DC_TA_DIRECT=1', '-DRE4DC_SCENERY_SUBMIT_BATCH='+str(batch),
                                str(root / 'fixture.cpp'), '-o', str(executable)], check=True)
                subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_texture_hook_bodies(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        emitted = function(ui, 'void gcasset_texture_emitted(')
        flush = function(ui, 'void gcasset_texture_flush(')
        packet = function(ui, 'void gcasset_packet_emitted(')
        state = ui[ui.index('using GcAssetPacketState='):ui.index('void gcasset_packet_emitted(')]
        effect_send = function(ui, 'void gcasset_fx_stream_send(')
        model_texture = next(line for line in ui.splitlines() if line.startswith('#define RE4DC_GCA_MODEL_TEXTURE(entry)'))
        fixture = r'''
#include "gc_asset_gate.h"
#include "gc_asset_packet_cursor.h"
#include "gc_asset_members.h"
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <string>
struct Package {
  struct Header { unsigned texture_count=1; } head;
  unsigned address;
  const Header& header() const { return head; }
  bool upload_complete() const { return true; }
  void* pvr_texture(unsigned) const { return reinterpret_cast<void*>(std::uintptr_t(address)); }
};
struct Entry { Package package;struct Key { unsigned crc,fnv; } key;bool valid;
  re4dc_gcasset::CheckedAsset asset{};unsigned asset_consumers=0;
};
struct Re4dcModelPart {const void* model;const void* info;};
Entry entries[2];
bool sq_held;
std::string logs;
extern "C" void re4dc_log(const char* fmt,...) {
  assert(!sq_held);char buf[2048];va_list ap;va_start(ap,fmt);vsnprintf(buf,sizeof buf,fmt,ap);va_end(ap);logs+=buf;
}
''' + emitted + '\n' + flush + '\n' + state + '\n' + model_texture + '\n' + packet + r'''
void stream_send(const void* packet,unsigned bytes){gcasset_packet_emitted(packet,bytes,2,gcasset_packet_consumer);}
''' + effect_send + r'''
int main() {
  using namespace re4dc_gcasset;
  entries[0].valid=true;entries[0].package.address=0x1000;entries[0].key={1,2};
  entries[1].valid=true;entries[1].package.address=0x2000;entries[1].key={3,4};
  install(nullptr,0);entries[0].asset=bind_checked("texture","00000001-00000002",Digest{});
  entries[1].asset=bind_checked("texture","00000003-00000004",Digest{});begin(0x111,1,Required);
  std::uint32_t header[8]={0x80000008,0,0,0x1000/8};
  std::uint32_t vertex[8]={0xe0000000};
  gcasset_packet_emitted(header,sizeof header,0,Texture);
  assert(entries[0].asset_consumers==0); // prepared header emits no vertices
  gcasset_packet_emitted(vertex,sizeof vertex,0,Texture);
  assert(entries[0].asset_consumers==(1U<<Texture)); // split packet uses carried header
  assert(logs.find("GC-ASSET v=")==std::string::npos); // no hash/log under emitter
  gcasset_texture_flush(entries[0]);
  assert(logs.find("id=00000001-00000002")!=std::string::npos);
  assert(logs.find("id=00000003-00000004")==std::string::npos); // loaded never emitted
  entries[0].asset_consumers=0;
  gcasset_packet_emitted(header,sizeof header,0,Texture);
  gcasset_packet_reset(); // real scene-open/retirement boundary must clear prior header
  gcasset_packet_emitted(vertex,sizeof vertex,0,Texture);
  assert(entries[0].asset_consumers==0);
  gcasset_fx_stream_send(header,sizeof header);
  assert(entries[0].asset_consumers==0);
  gcasset_fx_stream_send(vertex,sizeof vertex);
  assert(entries[0].asset_consumers&(1U<<EffectPicture)); // actual wrapper preserves carried header identity
  entries[0].asset_consumers=0;gcasset_packet_reset();
  std::uint32_t picture[16]={0x80000008,0,0,0x1000/8};picture[8]=0xe0000000;
  gcasset_packet_emitted(picture,sizeof picture,2,EffectPicture);
  assert(entries[0].asset_consumers& (1U<<EffectPicture));
  entries[0].asset_consumers=0;gcasset_packet_reset();
  std::uint32_t sprite[24]={0xa0000008,0,0,0x1000/8};
  sprite[8]=0xf0000000;sprite[16]=0xbf000000; // cy=-0.5f is payload, never a PCW
  gcasset_fx_stream_send(sprite,sizeof sprite);
  assert(entries[0].asset_consumers& (1U<<EffectPicture));
  assert(gcasset_packet_states[2].textured && !gcasset_packet_states[2].continuation);
  assert(gcasset_packet_states[2].address==0x1000);
  entries[0].asset_consumers=0;gcasset_packet_reset();
  gcasset_fx_stream_send(sprite,32);gcasset_fx_stream_send(sprite+8,32);
  assert(gcasset_packet_states[2].continuation);
  gcasset_fx_stream_send(sprite+16,32);
  assert(entries[0].asset_consumers& (1U<<EffectPicture));
  assert(!gcasset_packet_states[2].continuation);
  // Floating-colour textured polygons also use64-byte vertices. Their tails
  // can resemble another header without changing accepted texture identity.
  entries[0].asset_consumers=0;gcasset_packet_reset();
  std::uint32_t wide[8]={0x80000018,0,0,0x1000/8};
  std::uint32_t tail[8]={0x80000008,0,0,0x2000/8};
  gcasset_packet_emitted(wide,32,2,Texture);gcasset_packet_emitted(vertex,32,2,Texture);
  gcasset_packet_emitted(tail,32,2,Texture);
  assert(gcasset_packet_states[2].address==0x1000 && !gcasset_packet_states[2].continuation);
  assert(entries[0].asset_consumers==(1U<<Texture));
  // A64-byte two-volume header tail resembling a vertex emits no asset.
  entries[0].asset_consumers=0;gcasset_packet_reset();
  wide[0]=0x80000068;gcasset_packet_emitted(wide,32,2,Texture);
  gcasset_packet_emitted(vertex,32,2,Texture);assert(!entries[0].asset_consumers);
  gcasset_packet_emitted(vertex,32,2,Texture);gcasset_packet_emitted(tail,32,2,Texture);
  assert(entries[0].asset_consumers==(1U<<Texture));
  gcasset_model_pending.mask=1U<<Weapon;
  sq_held=true;RE4DC_GCA_MODEL_TEXTURE(&entries[1]);sq_held=false;
  assert(entries[1].asset_consumers==((1U<<Texture)|(1U<<Weapon))); // weapon texture also keeps generic texture acknowledgement
  gcasset_texture_flush(entries[0]);gcasset_texture_flush(entries[1]);
  for(unsigned i=0;i<ConsumerCount;++i) { checked(Consumer(i)); }
  end(1);
  assert(logs.find("unique=2 overflow=0 errors=0")!=std::string::npos);
  logs.clear();begin(0x111,2,Required);
  picture[3]=0x3000/8;gcasset_packet_emitted(picture,sizeof picture,2,Texture);end(1);
  assert(logs.find("unmapped-texture-address")!=std::string::npos);
  logs.clear();begin(0x111,3,Required);
  entries[1].package.address=0x1000;picture[3]=0x1000/8;
  gcasset_packet_emitted(picture,sizeof picture,2,Texture);end(1);
  assert(logs.find("ambiguous-texture-address")!=std::string::npos);
  logs.clear();begin(0x111,4,Required);gcasset_packet_reset();
  gcasset_packet_emitted(sprite,64,2,Texture);gcasset_packet_reset();end(1);
  assert(logs.find("incomplete-packet-continuation")!=std::string::npos);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-runtime-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            str(GAME / 'platform/gc_asset_members.cpp'), str(GAME / 'platform/gc_asset_payloads.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':
    unittest.main()
