"""Current source composition controls, distinct from preserved historical proofs.

Host preprocessing/function tests only; no KOS/SH4/image/TA acceptance. The full
native_ui GC0 file intentionally contains inert disabled-hook expressions, so
we require exact cloud-owned functions/blocks instead of masking those tokens.
"""
from pathlib import Path
import re,subprocess,tempfile,unittest
def function(source,anchor):
    # Definitions only: stream_open/send also have forward declarations.
    for match in re.finditer(re.escape(anchor),source):
        start=match.start();opening=source.index('{',start)
        if ';' in source[start:opening]:continue
        depth=1;end=opening+1
        while depth:
            depth+=(source[end]=='{')-(source[end]=='}');end+=1
        return source[start:end]
    raise ValueError('Missing actual definition '+anchor)
from composition_references import frozen_source,GC_UNIT,PVS_COMPOSITION,CLOUD_INTEGRATION,ROOT
GAME=ROOT/'port/dreamcast/game'
CLOUD=['ESP_SETUP_LEAN','ACTOR_BYTES_LEAN','ANIM_SAMPLE_LEAN','UI_DRAW_LEAN']
PROFILES=[dict.fromkeys(CLOUD,0)]+[{**dict.fromkeys(CLOUD,0),k:1} for k in CLOUD]+[dict.fromkeys(CLOUD,1)]
FLAGS=dict(GC_ASSET_GATE=0,GC_ASSET_MOTION_UNKNOWN=0,PS2_PVS_BATCH_COMPOSE=0,PS2_PVS=0,
           SCENERY_SUBMIT_BATCH=0,PVR_STREAM=1,D349_RENDERER_STACK=1,EFFECT_SPRITES=1,
           ESP_SPRITE_FAST=1,NATIVE_ACTOR=1,NATIVE_ACTOR_FAST=1,NATIVE_ACTOR_SKIN_LAZY=1,
           NATIVE_MES=1,MODEL_STREAM_FIX=1,ACTOR_DIRECT=1,COARSE_ONE_SUBMIT=1,BRIDGE_LEAN=1)
TOKENS=r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S'
def tokens(s):return re.findall(TOKENS,s)
def pp(source,overrides):
    flags={**FLAGS,**overrides};source=re.sub(r'^\s*#include .*\n','',source,flags=re.M)
    p=subprocess.run(['g++','-x','c++','-E','-P',*['-DRE4DC_'+k+'='+str(v) for k,v in flags.items()],'-'],input=source,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    return p.stdout
def ui_blocks(source):
    lines=source.splitlines(keepends=True);out=[]
    for start,line in enumerate(lines):
        if line.strip()!='#if RE4DC_UI_DRAW_LEAN':continue
        depth=1;end=start+1
        while depth:
            text=lines[end].strip()
            if re.match(r'#\s*(if|ifdef|ifndef)\b',text):depth+=1
            elif re.match(r'#\s*endif\b',text):depth-=1
            end+=1
        out.append(''.join(lines[start:end]))
    assert len(out)==8
    return out
class CurrentComposition(unittest.TestCase):
    def test_current_cloud0_single_and_all_on_gc0_paths(self):
        ui=(GAME/'platform/native_ui.cpp').read_text();old_ui=frozen_source(CLOUD_INTEGRATION,'platform/native_ui.cpp')
        # Exact current animation source; no runtime/pointer authority is inferred.
        self.assertEqual((ROOT/'src/game/motion.cpp').read_text(),frozen_source(CLOUD_INTEGRATION,'src/game/motion.cpp'))
        self.assertEqual(ui_blocks(ui),ui_blocks(old_ui))
        for profile in PROFILES:
            for path in ['platform/native_actor_fast.cpp','ui_bridge.cpp']:
                with self.subTest(profile=profile,path=path):
                    self.assertEqual(tokens(pp((GAME/path).read_text(),profile)),tokens(pp(frozen_source(CLOUD_INTEGRATION,path),profile)))
            current=pp(ui,profile);old=pp(old_ui,profile)
            for name in ['void fx_send(','bool fx_packet(' if profile['ESP_SETUP_LEAN'] else 'void fx_packet(','void glyph_draw_run(']:
                with self.subTest(profile=profile,function=name):self.assertEqual(tokens(function(current,name)),tokens(function(old,name)))
    def test_current_lifecycle_and_audit_projection_matches_frozen9f6(self):
        source=(GAME/'ui_bridge.cpp').read_text()
        expected=frozen_source(CLOUD_INTEGRATION,'ui_bridge.cpp')
        include='#include "platform/include/gc_asset_lifecycle.h"\n'
        guard='''#if RE4DC_GC_ASSET_GATE
    if(pG)re4dc_gcasset_room_enter((unsigned(pG->stage_no)<<8)|pG->room_no);
    else re4dc_gcasset::unresolved(re4dc_gcasset::Ui,"room-without-global");
#endif
'''
        def project(text):
            self.assertEqual(text.count(include),1);self.assertEqual(text.count(guard),1)
            return text.replace(include,'').replace(guard,'')
        self.assertEqual(project(source),expected)
        self.assertEqual(source.count('re4dc_cache_p2_diag_'),3)
        enter=next(line for line in source.splitlines(keepends=True) if 're4dc_cache_p2_diag_enter(' in line)
        for wrong in [source.replace(enter,''),source.replace(guard,guard.replace('#if RE4DC_GC_ASSET_GATE','#if 1'))]:
            with self.assertRaises(AssertionError):self.assertEqual(project(wrong),expected)
    def test_current_gc_wire_mask_and_exact_motion_guard_inventory(self):
        from test_motion_unknown import project_ui_motion0
        current=(GAME/'platform/native_ui.cpp').read_text();old=frozen_source(GC_UNIT,'platform/native_ui.cpp')
        self.assertEqual(function(current,'constexpr unsigned gcasset_wired_mask()'),function(old,'constexpr unsigned gcasset_wired_mask()'))
        # Exact approved guarded insertions still exist in CURRENT source, too.
        project_ui_motion0(current)
        for wrong in [current.replace('#if RE4DC_GC_ASSET_MOTION_UNKNOWN\n    re4dc_gcasset::motion_prepare();','#if RE4DC_GC_ASSET_GATE\n    re4dc_gcasset::motion_prepare();'),current.replace('#if RE4DC_GC_ASSET_MOTION_UNKNOWN\n    re4dc_gcasset::motion_prepare();\n#endif','    re4dc_gcasset::motion_prepare();')]:
            with self.assertRaises(AssertionError):project_ui_motion0(wrong)
    def test_current_pvs2_static_gate0_matches_frozen8ce_dedup_matrix(self):
        flags=dict(MESH_LOD=1,QUALITY=1,MESH_TEXTURES=1,NATIVE_STATIC=1,NATIVE_MESH=1,PS2_WORLD_MESH=1,PS2_WORLD_ROOMS=1,SCENERY_CONE=1,SCENERY_PIECE_STATE=1,PS2_PVS=2,PS2_STRIP_GROUPS=1,TRANS_POLICY=139,PS2_WORLD_DYNAMIC=1,QUALITY_ASSETS=1,PS2_INTERIOR_CULL=1,TREE_IMPOSTOR=1,FAR_SHELL=1)
        for name in ['native_static.cpp','far_shell.inc','room_file.c']:
            path='platform/'+name
            for mode in range(4):
                with self.subTest(path=path,dedup=mode):self.assertEqual(tokens(pp((GAME/path).read_text(),{**flags,'SCENERY_DEDUP':mode})),tokens(pp(frozen_source(PVS_COMPOSITION,path),{**flags,'SCENERY_DEDUP':mode})))
    def assert_full_gc_packets(self,source):
        out=pp(source,dict(ESP_SETUP_LEAN=1,GC_ASSET_GATE=1))
        self.assertNotIn('kSpriteBodyTag',out);self.assertNotIn('body_only',function(out,'void fx_send('))
        self.assertIn('gcasset_fx_stream_send(packet,kSpritePacket)',function(out,'void fx_send(').replace(' ',''))
        return out
    def test_gc1_esp_has_full_headers_and_gc0_retains_cloud_batch(self):
        source=(GAME/'platform/native_ui.cpp').read_text();self.assert_full_gc_packets(source)
        off=pp(source,dict(ESP_SETUP_LEAN=1,GC_ASSET_GATE=0));self.assertIn('kSpriteBodyTag',off);self.assertIn('body_only',function(off,'void fx_send('))
        self.assertEqual(source.count('    !RE4DC_GC_ASSET_GATE\n#define RE4DC_ESP_SETUP_BATCH'),1)
        with self.assertRaises(AssertionError):self.assert_full_gc_packets(source.replace('    !RE4DC_GC_ASSET_GATE\n#define RE4DC_ESP_SETUP_BATCH','    1\n#define RE4DC_ESP_SETUP_BATCH'))
    def cold_fixture(self):
        source=(GAME/'platform/native_ui.cpp').read_text()
        packet=(GAME/'platform/include/gc_asset_packet_cursor.h').read_text().replace('#pragma once','')
        pre=r'''
#include <cassert>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <cstring>
#define RE4DC_GC_ASSET_GATE 1
#define RE4DC_D349_RENDERER_STACK 1
#define RE4DC_PVR_STREAM 1
#define RE4DC_TAIL_GPU_SCOPE(x) ((void)0)
namespace re4dc_gcasset {enum Consumer {Texture,EffectPicture,Font};unsigned faults;
void unresolved(Consumer,const char*);}
'''+packet+r'''
struct Package {bool upload_complete(){return true;}struct Header{unsigned texture_count=1;}h;const Header&header(){return h;}void*pvr_texture(unsigned){return reinterpret_cast<void*>(0x1000);}};
struct Entry {bool valid=true;Package package;unsigned asset_consumers=0;}entries[1];
using GcAssetPacketState=re4dc_gcasset::PacketCursor;
GcAssetPacketState gcasset_packet_states[5];
re4dc_gcasset::Consumer gcasset_packet_consumer=re4dc_gcasset::Texture;
struct GcAssetGeneratedPacket {const void*packet;unsigned bytes,address;re4dc_gcasset::Consumer consumer;bool verified,accepted=false;};
GcAssetGeneratedPacket*gcasset_generated_packet=nullptr;
bool stream_scene=false,locked=false;int stream_list=2,desired_list=2;unsigned frame_pvr_calls,frame_pvr_bytes,opens,submitted;
constexpr int PVR_LIST_OP_POLY=0,PVR_LIST_PT_POLY=4;void*PVR_TA_INPUT=nullptr;
void sq_unlock(){assert(locked);locked=false;}void*sq_lock(void*p){assert(!locked);locked=true;return p;}
[[noreturn]] void re4dc_missing(const char*){std::abort();}
void pvr_scene_begin(){++opens;}int pvr_list_begin(int){locked=true;return 0;}
namespace re4dc {namespace profile {enum {SubmitOP,SubmitPT,SubmitTR};struct Scope{Scope(int){}};}
namespace render {void submit_pvr(const void*,unsigned bytes){assert(locked);submitted+=bytes;}}}
namespace re4dc_gcasset {void unresolved(Consumer,const char*){assert(!locked);++faults;}}
'''
        return pre+'\n'+function(source,'void gcasset_texture_emitted(')+'\n'+function(source,'void gcasset_packet_reset()')+'\n'+function(source,'void gcasset_packet_emitted(')+r'''
#define RE4DC_GCA_PACKET(...) gcasset_packet_emitted(__VA_ARGS__)
'''+function(source,'void stream_open()')+'\n'+function(source,'void stream_send(')+'\n'+function(source,'void gcasset_fx_stream_send(')+r'''
int main(){
 std::uint32_t packet[24]={0xa0000008,0,0,0x200};packet[8]=0xf0000000;packet[16]=0xbf000000;
 gcasset_packet_consumer=re4dc_gcasset::Font;
 gcasset_fx_stream_send(packet,sizeof packet);
 assert(opens==1 && stream_scene && !locked && submitted==96);
 assert(gcasset_packet_consumer==re4dc_gcasset::Font);
 assert(entries[0].asset_consumers==((1U<<re4dc_gcasset::Texture)|(1U<<re4dc_gcasset::EffectPicture)));
 assert(!re4dc_gcasset::faults && !gcasset_packet_states[2].continuation);
 entries[0].asset_consumers=0;gcasset_fx_stream_send(packet,sizeof packet);
 assert(opens==1 && submitted==192 && entries[0].asset_consumers&(1U<<re4dc_gcasset::EffectPicture));
 entries[0].asset_consumers=0;gcasset_packet_consumer=re4dc_gcasset::Texture;stream_send(packet,sizeof packet);
 assert(entries[0].asset_consumers==(1U<<re4dc_gcasset::Texture));
 entries[0].asset_consumers=0;gcasset_fx_stream_send(packet+8,64);
 assert(!entries[0].asset_consumers); // body-only continuation cannot invent another checked source
}
'''
    def cpp(self,source,reject=False):
        with tempfile.TemporaryDirectory(prefix='current-gc-cloud-',dir='/dev/shm') as t:
            p=Path(t);(p/'unit.cpp').write_text(source)
            built=subprocess.run(['g++','-std=c++17','-O2',str(p/'unit.cpp'),'-o',str(p/'run')],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(p/'run')],cwd=p,capture_output=True,text=True)
            self.assertEqual(ran.returncode==0,not reject,ran.stderr)
    def test_actual_cold_stream_effect_consumer_and_packet_cursor(self):self.cpp(self.cold_fixture())
    def test_cold_consumer_reset_and_wrong_wrapper_mutants(self):
        src=self.cold_fixture()
        for old,new in [('void gcasset_packet_reset(){','void gcasset_packet_reset(){gcasset_packet_consumer=re4dc_gcasset::Texture;'),('gcasset_packet_consumer=re4dc_gcasset::EffectPicture;','gcasset_packet_consumer=re4dc_gcasset::Texture;')]:
            self.assertEqual(src.count(old),1);self.cpp(src.replace(old,new),True)
if __name__=='__main__':unittest.main()