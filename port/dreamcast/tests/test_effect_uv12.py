"""EF12: actual source GX setup/raw strip UVs through the guarded native FIFO."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_draw_outcomes import function, harness

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
INCLUDE = ROOT / "game/platform/include"


def strip_adapter(esp):
    start = esp.index("// No sprite eligibility, billboard bound or callback substitution for strips.")
    return esp[start:esp.index("\n#if defined(RE4DC_EFFECT_TORCH)", start)].rsplit("\n#endif", 1)[0]


def actual_fixture(source=None):
    packet_stub, packet_code = harness()
    # The native implementation remains the real include. This wrapper observes
    # its input so the independent GX oracle can check the adapter boundary.
    packet_code = packet_code.replace(
        '#include "native_effect_strip21.inc"',
        '#define re4dc_effect_quad_result re4dc_effect_quad_result_native\n'
        '#include "native_effect_strip21.inc"\n'
        '#undef re4dc_effect_quad_result\n'
        'Re4dcEffectQuad observed{}; unsigned native_calls=0;\n'
        'extern "C" re4dc::NativeDrawResult re4dc_effect_quad_result(const Re4dcEffectQuad* q){'
        '++native_calls; observed=*q; return re4dc_effect_quad_result_native(q);}\n')
    packet_code = packet_code.replace(
        'bool frame_ready=true,', 'bool abort_after_send=false; bool frame_ready=true,')
    packet_code = packet_code.replace(
        'sent_bytes=bytes;sent_colors.push_back(',
        'sent_bytes=bytes;if(abort_after_send)stream_aborted=true;sent_colors.push_back(')
    sys = (REPO / "src/game/eff_sys.cpp").read_text()
    esp = source if source is not None else (REPO / "src/game/esp_sub.cpp").read_text()
    strip = (REPO / "src/game/esp01.cpp").read_text()
    source_setup = function(sys, "void EspTexSet(int id, int ptn)")
    source_state = function(esp, "void cEsp::CommonStateSet()")
    adapter = strip_adapter(esp)
    source_draw = strip[strip.index("void EspStrip_draw_poly("):
                        strip.index("\n// Segment count", strip.index("void EspStrip_draw_poly("))]
    code = packet_code + r'''
#include <cmath>
#include <cstdio>
#include "native_draw_result.hpp"
#include "effect_strip_uv21.hpp"
#include "effect_uv12.hpp"
using u8=unsigned char; using s8=signed char; using s16=short; using f32=float;
struct Vec {float x,y,z;}; struct GXColor {u8 r,g,b,a;};
struct GXTexObj {unsigned slot;}; struct GXTlutObj {};
struct TEXHeader {void* data;unsigned width,height,format,wrapS,wrapT;};
struct CLUT {void* data;unsigned format,numEntries;};
struct TEXDescriptor {TEXHeader* textureHeader;CLUT* CLUTHeader;};
struct TEXPalette {unsigned numDescriptors;};
struct EspTexWk {unsigned Owner;TEXPalette* pTpl;TEXHeader* texHdr;
 GXTexObj* pTexObj;GXTlutObj tlut;float mtx[3][4];};
struct System {EspTexWk Esp_tex_tbl[2];} system_value,*g_pEspSys=&system_value;
struct cEsp {u8 m_Id=1,m_Parts_no=255; unsigned m_Tool_flg=0,m_Flg=0,xA4=1;
 unsigned m_Tex_id=0,m_Ptn_no=0,xA5=4,xA6=5;void CommonStateSet();};
struct EspAnmData {};
struct Log {void err(int,int,const char*,...){assert(false);}} log_value,*pLog=&log_value;
GXColor s_effect_col{128,64,32,192};
bool policy_skip=false;
extern "C" int re4dc_fx_essential_strip_cut(const cEsp*){return policy_skip;}
TEXHeader headers[2]={{spill,64,64,4,0,0},{frame_storage,64,64,4,0,0}};
TEXDescriptor descriptors[2]={{&headers[0],nullptr},{&headers[1],nullptr}};
TEXPalette palettes[2]={{2},{2}}; GXTexObj texture_objects[2]={{0},{1}};
TEXDescriptor* TEXGet(TEXPalette*,unsigned ptn){assert(ptn<2);return &descriptors[ptn];}
bool EspGetAnmAddr(int,EspAnmData** out){static EspAnmData anm;*out=&anm;return true;}
float gx_matrix[2][4]{}; unsigned matrix_loads=0,texgen_calls=0,texture_slot=99;
void GXLoadTexObj(const GXTexObj* obj,int map){assert(map==0);texture_slot=obj->slot;}
void GXLoadTlut(const GXTlutObj*,int map){assert(map==0);}
void GXLoadTexMtxImm(const float m[][4],unsigned id,int type){
 assert(id==0x1e && type==1);++matrix_loads;
 for(unsigned r=0;r<2;++r)for(unsigned c=0;c<4;++c)gx_matrix[r][c]=m[r][c];
}
void GXSetCullMode(int mode){assert(mode==0);}
void GXSetAlphaCompare(int a,int b,int c,int d,int e){assert(a==4&&b==1&&c==1&&d==4&&e==1);}
void GXSetZMode(int a,int b,int c){assert(a==1&&b==3&&c==0);}
void GXSetNumTevStages(int n){assert(n==1);}
void GXSetTevOrder(int a,int b,int c,int d){assert(a==0&&b==0&&c==0&&d==4);}
void GXSetNumTexGens(int n){assert(n==1);}
void GXSetTexCoordGen(int a,int b,int c,int d){assert(a==0&&b==1&&c==4&&d==0x1e);++texgen_calls;}
struct Raw {Vec position;float u,v;} raw[4]; unsigned raw_count=0,legacy_calls=0;
void GXBegin(int primitive,int,unsigned count){assert(primitive==0x80&&count==4);raw_count=0;++legacy_calls;}
void GXMatrixIndex1u8(int i){assert(i==0);}
void GXPosition3f32(float x,float y,float z){assert(raw_count<4);raw[raw_count].position={x,y,z};}
void GXTexCoord2f32(float u,float v){raw[raw_count].u=u;raw[raw_count].v=v;++raw_count;}
void projection(float* p){const float a[]={0,1,0,1,0,-.01f,-1.01f};std::memcpy(p,a,sizeof a);}
void viewport(float* p){const float a[]={0,0,640,480,0,1};std::memcpy(p,a,sizeof a);}
#define RE4DC_GXF_GET_PROJECTION(p) projection(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport(p)
''' + source_setup + '\n' + source_state + '\n#line 1 "actual-adapter.cpp"\n' + adapter + \
        '\n#line 1 "actual-source-strip.cpp"\n' + source_draw + \
        '\n#line 1 "effect-uv12-fixture.cpp"\n' + r'''
using Outcome=re4dc::NativeDrawOutcome;
Vec corners[4]={{-1,1,-10},{1,1,-20},{-1,-1,-40},{1,-1,-30}};
void identity(EspTexWk& w){std::memset(w.mtx,0,sizeof w.mtx);
 for(unsigned i=0;i<3;++i)w.mtx[i][i]=1;}
void fresh(){reset();sent_colors.clear();stream_aborted=false;direct_open=false;
 source_draws_finished=false;draining_parts=false;frame_ready=true;missing=false;
 spill_available=true;abort_after_send=false;policy_skip=false;}
void setup(cEsp& e){EspTexSet(e.m_Tex_id,e.m_Ptn_no);e.CommonStateSet();}
void capture_raw(cEsp& e,int no,u8 repeat,int flag){
 const unsigned before=legacy_calls;e.m_Flg|=0x10;
 EspStrip_draw_poly(&e,no,corners,repeat,flag);
 e.m_Flg&=~0x10U;assert(legacy_calls==before+1&&raw_count==4);
 constexpr unsigned order[]={0,1,3,2};
 for(unsigned i=0;i<4;++i)
  assert(!std::memcmp(&raw[i].position,&corners[order[i]],sizeof(Vec)));
}
const char* stage="unknown";unsigned case_no=0;
void close(float actual,float expected){
 if(!(std::isfinite(actual)&&std::fabs(actual-expected)<.00002f)){
  std::fprintf(stderr,"stage=%s case=%u actual=%g expected=%g raw=%g,%g m=%g,%g,%g,%g\n",
   stage,case_no,actual,expected,raw[0].u,raw[0].v,gx_matrix[0][0],gx_matrix[0][1],gx_matrix[0][2],gx_matrix[0][3]);
  assert(false);
 }}
void oracle(const Re4dcEffectQuad& q){
 stage="oracle";
 assert(matrix_loads && texgen_calls && raw_count==4);
 for(unsigned i=0;i<4;++i){
  const float s=raw[i].u,t=raw[i].v;
  const float expected_s=((gx_matrix[0][0]*s+gx_matrix[0][1]*t)+gx_matrix[0][2])+gx_matrix[0][3];
  const float expected_t=((gx_matrix[1][0]*s+gx_matrix[1][1]*t)+gx_matrix[1][2])+gx_matrix[1][3];
  close(q.u[i],expected_s);close(q.v[i],expected_t);
  assert(q.positions[i][0]==raw[i].position.x&&q.positions[i][1]==raw[i].position.y);
  assert(q.positions[i][2]==raw[i].position.z);
 }
}
const pvr_vertex_t* queued_vertices(){
 assert(deferred_first&&deferred_count==1);
 const auto* data=reinterpret_cast<const unsigned char*>(deferred_first)+kEffectQuad21Node;
 const auto* hdr=reinterpret_cast<const pvr_poly_hdr_t*>(data);
 assert(hdr->words[0]==4&&hdr->words[1]==5&&hdr->words[2]==PVR_DEPTHCMP_GEQUAL);
 const unsigned clamp=(observed.wrap_s?0:PVR_UVCLAMP_U)|(observed.wrap_t?0:PVR_UVCLAMP_V);
 assert(hdr->words[3]==PVR_DEPTHWRITE_DISABLE&&hdr->words[4]==clamp);
 assert(hdr->words[5]==PVR_TXRALPHA_ENABLE&&hdr->words[6]==PVR_TXRENV_MODULATEALPHA);
 return reinterpret_cast<const pvr_vertex_t*>(data+32);
}
void compare_packet(const Re4dcEffectQuad& q){
 stage="packet";
 const auto* v=queued_vertices();constexpr unsigned order[]={0,1,2,0,2,3};
 for(unsigned i=0;i<6;++i){
  close(v[i].u,q.u[order[i]]);close(v[i].v,q.v[order[i]]);
  close(v[i].z,1.0f/-q.positions[order[i]][2]);
  assert(v[i].argb==q.color);
 }
 assert(v[5].flags==PVR_CMD_VERTEX_EOL);
}
void compare_clipped_packet(){
 // Independent edge-plane interpolation on the captured GX quad. The fixture
 // projection gives znear=1; only raw vertex0 is moved to depth .25 below.
 // Source triangles are (0,1,2),(0,2,3), with two output triangles each.
 stage="clip";const auto* out=queued_vertices();unsigned n=0;
 const float near=observed.projection[6]/(observed.projection[5]-1);
 auto point=[&](unsigned i){Raw p=raw[i];
  p.u=gx_matrix[0][0]*raw[i].u+gx_matrix[0][1]*raw[i].v+gx_matrix[0][2]+gx_matrix[0][3];
  p.v=gx_matrix[1][0]*raw[i].u+gx_matrix[1][1]*raw[i].v+gx_matrix[1][2]+gx_matrix[1][3];return p;};
 auto edge=[&](Raw a,Raw b){const float f=(-near-a.position.z)/(b.position.z-a.position.z);
  return Raw{{a.position.x+(b.position.x-a.position.x)*f,
              a.position.y+(b.position.y-a.position.y)*f,-near},
             a.u+(b.u-a.u)*f,a.v+(b.v-a.v)*f};};
 for(unsigned last:{2U,3U}){const unsigned mid=last==2?1:2;
  const Raw a=point(0),b=point(mid),c=point(last),ab=edge(a,b),ac=edge(a,c);
  // The existing clipper orders the polygon from its last->first edge.
  const Raw expected[]={ac,ab,b,ac,b,c};
  for(const auto& p:expected){close(out[n].u,p.u);close(out[n].v,p.v);
   close(out[n].z,1.0f/-p.position.z);++n;}
 }
 assert(deferred_first->changed[0]==(n+1)*32);
}
void run_case(cEsp& e,int no,u8 repeat,int flag,bool packet=true){
 ++case_no;
 fresh();setup(e);capture_raw(e,no,repeat,flag);
 const unsigned before=native_calls,old_legacy=legacy_calls;
 auto r=re4dc_esp_strip21_draw_result(&e,no,corners,repeat,flag);
 assert(r.outcome==Outcome::Queued&&r.queued==1&&native_calls==before+1);
 assert(legacy_calls==old_legacy);oracle(observed);
 if(packet)compare_packet(observed);
}
void refused(cEsp& e,int no=0,u8 repeat=1,int flag=0){
 fresh();setup(e);const unsigned before=native_calls;
 auto r=re4dc_esp_strip21_draw_result(&e,no,corners,repeat,flag);
 assert(r.outcome==Outcome::UnsupportedBeforePublication&&r.fallback_allowed());
 assert(native_calls==before&&!deferred_count);
}
int main(){
 auto& w=system_value.Esp_tex_tbl[0];w.Owner=17;w.pTpl=&palettes[0];
 w.texHdr=&headers[0];w.pTexObj=texture_objects;identity(w);
 cEsp e;run_case(e,0,2,0); // legacy full 3x4 identity
 w.mtx[0][0]=0;w.mtx[0][1]=-1;w.mtx[1][0]=1;w.mtx[1][1]=0;
 w.mtx[0][2]=.25f;w.mtx[0][3]=.5f;w.mtx[1][2]=-.125f;w.mtx[1][3]=.75f;
 w.mtx[2][0]=std::numeric_limits<float>::quiet_NaN(); // GX never loads row 2
 run_case(e,0,2,0);run_case(e,1,2,1);
 identity(w);w.mtx[0][2]=.375f;w.mtx[1][2]=-.25f;run_case(e,1,3,0);
 identity(w);w.mtx[0][0]=-2;w.mtx[0][1]=.375f;w.mtx[1][0]=-.5f;
 w.mtx[1][1]=1.5f;w.mtx[0][3]=.125f;run_case(e,2,3,1);
 e.m_Tool_flg=2;run_case(e,1,3,0);e.m_Tool_flg=4;run_case(e,254,255,1);
 e.m_Tool_flg=6;run_case(e,2,3,1);e.m_Tool_flg=0;
 // All repeat/slice/direction/mirror combinations feed the actual GX oracle.
 for(unsigned repeat=1;repeat<=255;++repeat)for(unsigned no=0;no<repeat;++no)
  for(unsigned direction=0;direction<2;++direction)for(unsigned mirror=0;mirror<4;++mirror){
   e.m_Tool_flg=mirror*2;run_case(e,no,repeat,direction);
  }
 e.m_Tool_flg=0;
 e.m_Ptn_no=1;run_case(e,0,1,0);assert(texture_slot==1&&observed.image.pixels==headers[1].data);
 e.m_Ptn_no=0;w.mtx[0][3]=.875f;run_case(e,0,1,0);
 // Same Esp01 identity, different current texture owner and matrix.
 auto& other=system_value.Esp_tex_tbl[1];other.Owner=42;other.pTpl=&palettes[1];
 other.texHdr=&headers[0];other.pTexObj=texture_objects;identity(other);
 other.mtx[0][2]=-.75f;other.mtx[1][3]=.625f;
 e.m_Tex_id=1;run_case(e,0,1,0);assert(observed.u[0]<0);
 e.m_Tex_id=0;
 // The same source-instance address may immediately select a new owner,
 // pattern and current matrix. The already queued packet is a value copy;
 // no source identity or matrix pointer is retained by EFFECT_UV12.
 run_case(e,0,1,0);
 auto* first_snapshot=deferred_first;
 const unsigned snapshot_bytes=first_snapshot->changed[0];
 assert(snapshot_bytes<=13*sizeof(pvr_vertex_t));
 unsigned char snapshot[13*sizeof(pvr_vertex_t)];
 auto* first_packet=reinterpret_cast<const unsigned char*>(first_snapshot)+kEffectQuad21Node;
 std::memcpy(snapshot,first_packet,snapshot_bytes);
 const float previous_u=observed.u[0];
 e.m_Id=2;e.m_Ptn_no=1;w.Owner=42;w.pTpl=&palettes[1];w.texHdr=&headers[1];
 w.mtx[0][3]=4.875f;setup(e);capture_raw(e,0,1,1);
 auto replacement=re4dc_esp_strip21_draw_result(&e,0,corners,1,1);
 assert(replacement.outcome==Outcome::Queued&&replacement.queued==1&&deferred_count==2);
 assert(first_snapshot->next==deferred_last&&observed.u[0]!=previous_u);
 oracle(observed);assert(observed.image.pixels==headers[1].data);
 assert(!std::memcmp(snapshot,first_packet,snapshot_bytes));
 // A subsequent transformed primitive can refuse without losing that prefix.
 const unsigned count_before_refusal=deferred_count;
 auto* last_before_refusal=deferred_last;
 fx_frame=frame;fx_count=RE4DC_EFFECT_SPRITE_MAX;
 replacement=re4dc_esp_strip21_draw_result(&e,0,corners,1,1);
 assert(replacement.outcome==Outcome::Refused&&replacement.fallback_allowed());
 assert(deferred_count==count_before_refusal&&deferred_last==last_before_refusal);
 assert(!std::memcmp(snapshot,first_packet,snapshot_bytes));
 e.m_Id=1;e.m_Ptn_no=0;w.Owner=17;w.pTpl=&palettes[0];w.texHdr=&headers[0];
 // Identity keeps the old broad material admission, including a non-RGB565 header.
 identity(w);headers[0].format=14;headers[0].wrapS=1;run_case(e,0,1,0);
 headers[0].format=4;headers[0].wrapS=0;
 w.mtx[0][3]=.5f;
 headers[0].format=14;refused(e);headers[0].format=4;
 CLUT clut{};descriptors[0].CLUTHeader=&clut;refused(e);descriptors[0].CLUTHeader=nullptr;
 headers[0].wrapS=1;refused(e);headers[0].wrapS=0;
 headers[0].wrapT=1;refused(e);headers[0].wrapT=0;
 s_effect_col.a=1;refused(e);s_effect_col.a=192;
 e.m_Tool_flg=0x80;refused(e);e.m_Tool_flg=0x20000;refused(e);e.m_Tool_flg=0;
 e.xA5=1;refused(e);e.xA5=4;e.xA6=1;refused(e);e.xA6=5;
 e.m_Tool_flg=0x40;refused(e);e.m_Tool_flg=0x4000;refused(e);
 e.m_Tool_flg=0x10000;refused(e);e.m_Tool_flg=0;
 e.m_Flg=0x10;refused(e);e.m_Flg=0;
 for(unsigned row=0;row<2;++row)for(unsigned col=0;col<4;++col)
  for(float bad:{std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),
                 -std::numeric_limits<float>::infinity()}){
   identity(w);w.mtx[row][col]=bad;refused(e);
  }
 identity(w);for(float& value:w.mtx[2])value=std::numeric_limits<float>::quiet_NaN();
 run_case(e,0,1,0); // every unloaded entry can be poisoned
 s_effect_col.a=2;run_case(e,0,1,0);s_effect_col.a=192;
 identity(w);w.mtx[0][0]=std::numeric_limits<float>::max();
 w.mtx[0][1]=std::numeric_limits<float>::max();refused(e,0,1,0);
 identity(w);w.mtx[0][3]=.5f;
 fresh();setup(e);policy_skip=true;const unsigned calls_before_skip=native_calls;
 auto r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::PolicySkip&&!r.fallback_allowed()&&native_calls==calls_before_skip);
 fresh();setup(e);source_draws_finished=true;capture_raw(e,0,1,0);
 r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::Submitted&&r.submitted==1&&sent_bytes==7*32&&!deferred_count);
 oracle(observed);const auto* direct=reinterpret_cast<const pvr_vertex_t*>(sent)+1;
 constexpr unsigned direct_order[]={0,1,2,0,2,3};
 for(unsigned i=0;i<6;++i){close(direct[i].u,observed.u[direct_order[i]]);close(direct[i].v,observed.v[direct_order[i]]);}
 fresh();setup(e);source_draws_finished=true;abort_after_send=true;
 r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::PartialAbort&&r.submitted==1&&sent_bytes);
 // The actual source caller must never replay GX after a terminal publication.
 fresh();setup(e);source_draws_finished=true;abort_after_send=true;
 const unsigned legacy_before_partial=legacy_calls;
 EspStrip_draw_poly(&e,0,corners,1,0);
 assert(sent_bytes&&!deferred_count&&legacy_calls==legacy_before_partial);
 fresh();setup(e);missing=true;const unsigned legacy_before_refusal=legacy_calls;
 EspStrip_draw_poly(&e,0,corners,1,0);
 assert(!deferred_count&&legacy_calls==legacy_before_refusal+1);
 fresh();setup(e);direct_open=true;r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::UnsupportedBeforePublication&&!deferred_count);
 fresh();setup(e);missing=true;r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::Refused&&!deferred_count);
 fresh();setup(e);deferred_top=8192;spill_available=false;
 r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::Refused&&r.fallback_allowed()&&!deferred_count&&!sent_bytes);
 fresh();setup(e);for(auto& p:corners)p.z=1;
 r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::Culled&&!deferred_count);
 corners[0].z=-.25f;corners[1].z=-20;corners[2].z=-40;corners[3].z=-30;
 fresh();setup(e);capture_raw(e,0,1,0);
 r=re4dc_esp_strip21_draw_result(&e,0,corners,1,0);
 assert(r.outcome==Outcome::Queued&&deferred_count==1);
 oracle(observed);const auto count=(deferred_first->changed[0]/32)-1;
 assert(count>0&&count<=12);const auto* clipped=queued_vertices();
 for(unsigned i=0;i<count;++i){assert(clipped[i].z>0&&std::isfinite(clipped[i].u)&&std::isfinite(clipped[i].v));}
 compare_clipped_packet();
 // A noncoplanar quad uses the source diagonal even after the matrix transform.
 corners[0].z=-10;run_case(e,0,1,0);
}
'''
    return packet_stub, code


class EffectUv12(unittest.TestCase):
    def test_disabled_full_source_preprocessing_and_adapter_object_identity(self):
        baseline = subprocess.check_output(
            ["git", "show", "d45eb759:src/game/esp_sub.cpp"], cwd=REPO, text=True)
        current = (REPO / "src/game/esp_sub.cpp").read_text()
        # Complete production TU, including real headers and diagnostic literals.
        # __sh__ preprocessing is possible without pretending the host is SH-4.
        for target in (False, True):
            for outcomes in (0, 1):
                with self.subTest(target=target, outcomes=outcomes):
                    command = ["g++", "-std=gnu++20", "-fpermissive", "-w", "-E", "-P",
                               "-DRE4DC_GAME", "-DRE4DC_EFFECT_SPRITES=1", "-DRE4DC_EFFECT_LEAN=1",
                               "-DRE4DC_FX_STRIP21=1", f"-DRE4DC_NATIVE_DRAW_OUTCOMES={outcomes}",
                               "-include", str(INCLUDE / "re4dc_prelude.h"),
                               "-I" + str(REPO / "include"), "-I" + str(REPO / "src"),
                               "-I" + str(INCLUDE), "-iquote", str(REPO / "src/game")]
                    if target:
                        command += ["-D__sh__"]
                    expanded = []
                    for source, definitions in ((baseline, []), (current, []),
                                                (current, ["-DRE4DC_EFFECT_UV12=0"])):
                        run = subprocess.run(command + definitions + ["-x", "c++", "-"],
                                             input=source, capture_output=True, cwd=REPO, text=True)
                        self.assertEqual(run.returncode, 0, run.stderr)
                        expanded.append(run.stdout)
                    self.assertEqual(expanded[0], expanded[1])
                    self.assertEqual(expanded[0], expanded[2])
        # The actual adapter and native packet implementation also produce the
        # same host object. Fixture-only assertion locations are pinned at
        # extraction boundaries; the complete production-TU comparison above
        # keeps every production diagnostic literal untouched.
        # Whole target-TU/linked-image identity stays local.
        stub, old_code = actual_fixture(baseline)
        _, new_code = actual_fixture(current)
        with tempfile.TemporaryDirectory(prefix="re4dc-effect-uv12-off-") as td:
            tmp = Path(td)
            (tmp / "dc").mkdir()
            (tmp / "dc/pvr.h").write_text(stub)
            outputs = []
            for name, code, definitions in (("base", old_code, []), ("absent", new_code, []),
                                            ("zero", new_code, ["-DRE4DC_EFFECT_UV12=0"])):
                obj = tmp / (name + ".o")
                command = ["g++", "-std=c++20", "-O2", "-g0", "-ffp-contract=off",
                           "-DRE4DC_FX_STRIP21=1", "-DRE4DC_NATIVE_DRAW_OUTCOMES=1",
                           "-DRE4DC_FX_TRIM=1", "-DRE4DC_TA_DIRECT=1", "-DRE4DC_UI_HANDLES=1",
                           "-DRE4DC_EFFECT_SPRITE_MAX=64", "-I" + str(tmp), "-I" + str(INCLUDE),
                           "-I" + str(ROOT / "room"), *definitions,
                           "-x", "c++", "-", "-c", "-o", str(obj)]
                run = subprocess.run(command, input=code, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                outputs.append(obj.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])

    def test_actual_gx_source_adapter_and_native_packet(self):
        stub, code = actual_fixture()
        for sanitize in (False, True):
            with self.subTest(sanitize=sanitize), tempfile.TemporaryDirectory(prefix="re4dc-effect-uv12-") as td:
                tmp = Path(td)
                (tmp / "dc").mkdir()
                (tmp / "dc/pvr.h").write_text(stub)
                cpp = tmp / "fixture.cpp"
                cpp.write_text(code)
                exe = tmp / "fixture"
                args = ["g++", "-std=c++20", "-O2", "-ffp-contract=off",
                        "-DRE4DC_FX_STRIP21=1", "-DRE4DC_NATIVE_DRAW_OUTCOMES=1",
                        "-DRE4DC_EFFECT_UV12=1", "-DRE4DC_FX_TRIM=1", "-DRE4DC_TA_DIRECT=1",
                        "-DRE4DC_UI_HANDLES=1", "-DRE4DC_EFFECT_SPRITE_MAX=64",
                        "-fno-pie", "-no-pie", "-I" + str(tmp), "-I" + str(INCLUDE),
                        "-I" + str(ROOT / "room"), str(cpp),
                        str(ROOT / "room/pvr_geometry.cpp"), "-o", str(exe)]
                if sanitize:
                    args += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
                build = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(build.returncode, 0, build.stderr)
                run = subprocess.run([str(exe)], capture_output=True, text=True,
                                     env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_primary_make_literal_guards_and_flag_scope(self):
        with tempfile.TemporaryDirectory(prefix="re4dc-effect-uv12-make-") as td:
            tmp = Path(td)
            kos = tmp / "kos-stub"
            kos.mkdir()
            (kos / "Makefile.rules").write_text("")
            targets = ["obj/src/game/esp_sub.o", "obj/src/game/esp01.o", "obj/platform/native_ui.o"]
            base = ["make", "--no-print-directory", "-f", "Makefile", "-n",
                    "KOS_BASE=" + str(kos), *targets, "EFFECT_SPRITES=1",
                    "FX_STRIP21=1", "NATIVE_DRAW_OUTCOMES=1", "GAME_FP_CONTRACT=off"]
            outputs = []
            for value in (None, "0", "1"):
                args = base + ([] if value is None else ["EFFECT_UV12=" + value])
                run = subprocess.run(args, capture_output=True, text=True, cwd=ROOT / "game")
                self.assertEqual(run.returncode, 0, run.stderr)
                outputs.append([line for line in run.stdout.splitlines() if line.startswith("kos-c++")])
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(len(outputs[2]), len(targets))
            for i, line in enumerate(outputs[2]):
                self.assertEqual(line.count("-DRE4DC_EFFECT_UV12=1"), int(i == 0))
            self.assertIn("-ffp-contract=off", outputs[2][0])
            for unsafe in ("-ffinite-math-only", "-ffast-math", "-funsafe-math-optimizations"):
                self.assertNotIn(unsafe, outputs[2][0])
            for value in ("", "0 1", "2", "-1", "%", "0%", "1%", "1 ", "0 "):
                run = subprocess.run(base + ["EFFECT_UV12=" + value],
                                     capture_output=True, text=True, cwd=ROOT / "game")
                self.assertNotEqual(run.returncode, 0, value)
                self.assertIn("EFFECT_UV12", run.stderr)
            for missing in ("FX_STRIP21=0", "NATIVE_DRAW_OUTCOMES=0", "EFFECT_SPRITES=0"):
                run = subprocess.run(base + ["EFFECT_UV12=1", missing],
                                     capture_output=True, text=True, cwd=ROOT / "game")
                self.assertNotEqual(run.returncode, 0, missing)


if __name__ == "__main__":
    unittest.main()
