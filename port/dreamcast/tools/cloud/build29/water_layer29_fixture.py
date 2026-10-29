#!/usr/bin/env python3
"""Compile the production EF13 selector and draw consumer against the original tables."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "src/game/espgen45.cpp"
PRODUCER = ROOT / "port/dreamcast/tools/d367/water/water_layer29_source.py"
METADATA = ROOT / "src/game/water_layer29_source.inc"
BASE = "c027b26e32229dc9035b9fe2e1ac399bd9ee20b0"


def between(s, a, b):
    return s[s.index(a):s.index(b, s.index(a))]


PRELUDE = r'''
#include <cassert>
#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
using u8=uint8_t; using u16=uint16_t; using s16=int16_t;
using u32=uint32_t; using s32=int32_t; using f32=float;
using Mtx=float[3][4];
static u32 G_ROOM_ID=0x107, now_frame=1, now_tick=0;
static int now_level=0, area_off=-1, disp_off=-1, native_fail_after=-1;
static unsigned native_calls=0, fallback_calls=0, ot_calls=0;
struct GXColor { u8 r,g,b,a; };
struct Image { const void* pixels; u32 width,height,format; const void* palette; u32 palette_format,palette_bytes; };
struct Re4dcWaterLayer {
    Image image; float mv[3][4]; float eye_x,eye_z,half_x,half_z;
    float u_per_mm,v_per_mm,u0,v0,projection[7],viewport[6];
    unsigned argb; unsigned char src,dst,pad[2];
};
struct TEXHeader { const void* data; u32 width,height,format; };
struct PaletteHeader { const void* data; u32 format,numEntries; };
struct TEXDescriptor { TEXHeader* textureHeader; PaletteHeader* CLUTHeader; };
struct TPL { u32 numDescriptors; TEXDescriptor descriptor[60]; int id; };
struct EspAnmData { u32 Frames,Data_num,Frame_cnt[128]; };
struct EspTexWk { u8 Owner; TPL* pTpl; EspAnmData* pAnm; };
struct EspSys { EspTexWk Esp_tex_tbl[256]; };
static EspSys system_tex{}; static EspSys* g_pEspSys=&system_tex;
static TPL tpls[256]{}; static TEXHeader texhdr[256]{};
static EspAnmData animation{}; static char pixel[256]{};
static int last_tex=-1, last_pattern=-1;
static TEXDescriptor* TEXGet(TPL* tpl,u32 pattern) {
    assert(pattern<tpl->numDescriptors);last_tex=tpl->id;last_pattern=pattern;
    return &tpl->descriptor[pattern];
}
struct EspgenWork { u32 flag; };
static EspgenWork water_work{1}; static EspgenWork* g_pWater45=&water_work;
struct Game { struct { Mtx v_mat; } Cam; u32 prim_cnt; };
static Game game{}; static Game* pG=&game;
extern "C" unsigned re4dc_ui_frame(void) { return now_frame; }
extern "C" u32 re4dc_vi_retrace_count(void) { return now_tick*2; }
extern "C" int re4dc_fx_level_get(void) { return now_level; }
extern "C" int re4dc_water42_live(void) { return 1; }
extern "C" void re4dc_log(const char*, ...) {}
extern "C" int GetSstDispFlag(u32 id) { return int(id)!=disp_off; }
static int EffGetAreaState(int area) { return area!=area_off; }
static int EffIsSetFinalCol() { return now_tick&1; }
static void EffGetFinalCol(GXColor* c) { *c={201,223,187,243}; }
static void CameraCurrentProjection() {}
static void GXGetProjectionv(float* p) { for(int i=0;i<7;i++)p[i]=float(i+1)*0.125f; }
static void GXGetViewportv(float* p) { for(int i=0;i<6;i++)p[i]=float(i+1)*16.0f; }
static void PSMTXInverse(const Mtx& a,Mtx& b) { memcpy(b,a,sizeof(Mtx)); }
static void PSMTXConcat(const Mtx&,const Mtx& b,Mtx& c) { memcpy(c,b,sizeof(Mtx)); }
extern "C" void re4dc_water45_draw(EspgenWork*) { ++fallback_calls; }
static void AddOtDirect(int,void*,void(*)(),int,int,void*,float) { ++ot_calls; }
static unsigned bits(float f){unsigned u;memcpy(&u,&f,4);return u;}
extern "C" int re4dc_water_layer(const Re4dcWaterLayer* L) {
    const unsigned call=native_calls++;
    if(native_fail_after>=0 && int(call)>=native_fail_after)return 0;
    printf("L %02x %02d %08x %u %u %u %u %u %d %d %d",L->src,L->dst,L->argb,
           unsigned(L->image.width),unsigned(L->image.height),unsigned(L->image.format),
           unsigned(L->image.palette_format),unsigned(L->image.palette_bytes),L->image.palette?1:0,
           L->image.pixels?last_tex:-1,L->image.pixels?last_pattern:-1);
    for(const auto& row:L->mv)for(float f:row)printf(" %08x",bits(f));
    const float vals[]={L->eye_x,L->eye_z,L->half_x,L->half_z,L->u_per_mm,L->v_per_mm,L->u0,L->v0};
    for(float f:vals)printf(" %08x",bits(f));
    for(float f:L->projection)printf(" %08x",bits(f));
    for(float f:L->viewport)printf(" %08x",bits(f));
    puts("");return 1;
}
static u32 s_wps2_frame=~0U; static u8 s_wps2_dummy;
#define RE4_MEM_LO 0
#define RE4_MEM_HI UINTPTR_MAX
'''

CASES = r'''
int main() {
    for(int i=0;i<256;i++) {
        tpls[i].numDescriptors=60;tpls[i].id=i;
        texhdr[i]={&pixel[i],64,64,6};
        for(auto& d:tpls[i].descriptor){d.textureHeader=&texhdr[i];d.CLUTHeader=nullptr;}
        system_tex.Esp_tex_tbl[i]={0,&tpls[i],&animation};
    }
    animation.Frames=60;animation.Data_num=0;
    game.Cam.v_mat[0][0]=game.Cam.v_mat[1][1]=game.Cam.v_mat[2][2]=1.0f;
    game.prim_cnt=0x1000;
    for(u32 room:{0x107u,0x108u,0x10au,0x10bu,0x11au,0x11bu,0x10cu,0x10du,0x10eu,0x100u}) {
        for(u32 tick:{0u,3u,73u}) {
            for(int level:{0,1,2}) {
                G_ROOM_ID=room;now_tick=tick;now_level=level;
                area_off=tick==3?31:-1;disp_off=tick==73?9:-1;
                ++now_frame;native_calls=0;
                const int rows=re4dc_water_ps2_rows();
                printf("CASE %03x %u %d rows=%d\n",unsigned(room),unsigned(tick),level,rows);
                const unsigned before=ot_calls;
                re4dc_water_ps2_queue();
                assert(ot_calls-before==unsigned(rows?1:0));
                if(rows)re4dc_water_ps2_draw(nullptr);
            }
        }
    }
    puts("ENDCANON");
#if RE4DC_WATER_LAYER29
    printf("FOOTPRINT main=%zu ext=%zu definition=%zu view=%zu store=%zu\n",
           sizeof(WaterPs2Row),sizeof(WaterPs2ExtRow),sizeof(Water29Definition),
           sizeof(Water29View),sizeof(Water29Store));
    Water29View v;
    assert(Water29Select(0x100,&v)==WATER29_UNBOUND);
#if RE4DC_WATER_PS2_ROOMS & 1
    WaterPs2Row row=kWaterPs2[0];
    Water29Definition d{};
    Water29SourceBytes main_source{&row,sizeof(row),22,7};
    d.magic=WATER29_MAGIC;d.version=WATER29_VERSION;d.extent=sizeof(d);
    d.room=0x107;d.source_key=Water29SourceKey(d.room);d.owner=22;d.incarnation=7;
    d.result=WATER29_BOUND;d.main_count=1;d.main_bytes=sizeof(row);d.main_rows=&row;
    alignas(Water29Definition) u8 unaligned[sizeof(Water29Definition)+1];
    memcpy(unaligned+1,&d,sizeof(d));
    auto* bad_header=(const Water29Definition*)(unaligned+1);
    assert(re4dc_water29_bind(bad_header,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    assert(water29Load(bad_header,sizeof(d),&main_source,nullptr,0x107,d.source_key,&v)==WATER29_REFUSED);
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_BOUND);
    const float x=row.x;row.x=123456.0f;
    assert(Water29Select(0x107,&v)==WATER29_BOUND && v.main_count==1 && v.main_rows[0].x==x);
    d.version=2;assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    assert(Water29Select(0x107,&v)==WATER29_BOUND && v.main_rows[0].x==x);
    d.version=1;d.main_bytes=sizeof(row)-1;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.main_bytes=sizeof(row);main_source.bytes=sizeof(row)-1;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    main_source.bytes=sizeof(row);main_source.owner=23;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    main_source.owner=22;
    d.main_rows=(const WaterPs2Row*)((const u8*)&row+1);
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.main_rows=(const WaterPs2Row*)(uintptr_t(1));
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.main_rows=&row;
    d.main_bytes=sizeof(row);d.main_count=33;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.main_count=1;d.source_key^=1;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.source_key^=1;d.room=0x108;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.room=0x107;
    assert(re4dc_water29_bind(&d,sizeof(d)-1,&main_source,nullptr)==WATER29_REFUSED);
    assert(re4dc_water29_bind(&d,0,&main_source,nullptr)==WATER29_REFUSED);
    assert(Water29Select(0x107,&v)==WATER29_BOUND && v.main_rows[0].x==x);
    re4dc_water29_retire(22,6);assert(Water29Select(0x107,&v)==WATER29_BOUND && v.main_count==1);
    re4dc_water29_retire(22,7);assert(Water29Select(0x107,&v)==WATER29_BOUND && v.main_count==2);
    d.main_count=0;d.main_bytes=0;d.main_rows=nullptr;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.result=WATER29_NO_WATER;d.main_count=1;d.main_bytes=sizeof(row);d.main_rows=&row;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    d.result=WATER29_BOUND;
    d.main_count=1;d.main_bytes=sizeof(row);d.main_rows=&row;
    d.incarnation=8;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    main_source.incarnation=8;
    const float hx=row.hx;row.hx=0.0f;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    row.hx=hx;row.x=__builtin_inff();
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    row.x=123456.0f;
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_BOUND);
    assert(Water29Select(0x107,&v)==WATER29_BOUND && v.incarnation==8 && v.main_rows[0].x==row.x);
    re4dc_water29_retire(22,7);
    assert(Water29Select(0x107,&v)==WATER29_BOUND && v.incarnation==8);
    re4dc_water29_retire(22,8);
    // A new publication may source a shifted span inside the destination.
    // The second row overlaps the destination, so this must use memmove.
    Water29Store overlap{};
    overlap.main_rows[1]=kWaterPs2[0];overlap.main_rows[2]=kWaterPs2[1];
    const float first_x=overlap.main_rows[1].x, second_x=overlap.main_rows[2].x;
    Water29Definition shifted=d;
    shifted.incarnation=9;shifted.main_rows=&overlap.main_rows[1];
    shifted.main_count=2;shifted.main_bytes=2*sizeof(WaterPs2Row);
    Water29SourceBytes overlap_source{overlap.main_rows,sizeof(overlap.main_rows),22,9};
    Water29View published{};
    assert(water29Publish(&overlap,&shifted,sizeof(shifted),&overlap_source,nullptr,
                          0x107,shifted.source_key,&published)==WATER29_BOUND);
    assert(overlap.main_rows[0].x==first_x && overlap.main_rows[1].x==second_x &&
           published.main_rows==overlap.main_rows);
#if RE4DC_WATER_PS2_EXT
    WaterPs2ExtRow extrow=kWaterPs2Ext[0];
    Water29Definition extdef{};
    Water29SourceBytes ext_source{&extrow,sizeof(extrow),42,1};
    extdef.magic=WATER29_MAGIC;extdef.version=WATER29_VERSION;extdef.extent=sizeof(extdef);
    extdef.room=0x10c;extdef.source_key=Water29SourceKey(extdef.room);
    extdef.owner=42;extdef.incarnation=1;extdef.result=WATER29_BOUND;
    extdef.ext_count=1;extdef.ext_bytes=sizeof(extrow);extdef.ext_rows=&extrow;
    const float ax=extrow.ax[0];extrow.ax[0]=__builtin_nanf("");
    assert(re4dc_water29_bind(&extdef,sizeof(extdef),nullptr,&ext_source)==WATER29_REFUSED);
    extrow.ax[0]=ax;
    assert(re4dc_water29_bind(&extdef,sizeof(extdef),nullptr,&ext_source)==WATER29_BOUND);
    const float px=extrow.p[0];extrow.p[0]=0.0f;
    assert(Water29Select(0x10c,&v)==WATER29_BOUND && v.ext_count==1 && v.ext_rows[0].p[0]==px);
    re4dc_water29_retire(42,1);
    assert(Water29Select(0x10c,&v)==WATER29_BOUND && v.ext_count==14);
#endif
#else
    WaterPs2Row row=kWaterPs2[0];
    Water29Definition d{};
    Water29SourceBytes main_source{&row,sizeof(row),22,7};
    d.magic=WATER29_MAGIC;d.version=WATER29_VERSION;d.extent=sizeof(d);
    d.room=0x107;d.source_key=Water29SourceKey(d.room);d.owner=22;d.incarnation=7;
    d.result=WATER29_BOUND;d.main_count=1;d.main_bytes=sizeof(row);d.main_rows=&row;
    assert(Water29Select(0x107,&v)==WATER29_UNBOUND);
    assert(re4dc_water29_bind(&d,sizeof(d),&main_source,nullptr)==WATER29_REFUSED);
    assert(Water29Select(0x107,&v)==WATER29_REFUSED);
#endif

    // Explicit no-water suppresses the source generator, while an unsupported
    // room remains unbound. Retirement restores the compiled r10b definition.
    Water29Definition no{};
    no.magic=WATER29_MAGIC;no.version=WATER29_VERSION;no.extent=sizeof(no);
    no.room=0x10b;no.source_key=Water29SourceKey(no.room);no.owner=33;no.incarnation=1;
    no.result=WATER29_NO_WATER;
    assert(re4dc_water29_bind(&no,sizeof(no),nullptr,nullptr)==WATER29_NO_WATER);
    G_ROOM_ID=0x10b;assert(Water29Select(G_ROOM_ID,&v)==WATER29_NO_WATER);
    assert(re4dc_water_ps2_rows()==0);
    unsigned ot=ot_calls;re4dc_water45_queue(&water_work);assert(ot_calls==ot);
    re4dc_water29_retire(33,1);
    assert(re4dc_water_ps2_rows()==1);

    // Total native refusal can use the existing source generator surface.
    native_fail_after=0;native_calls=0;unsigned fallback=fallback_calls;
    now_level=0;now_tick=0;area_off=-1;disp_off=-1;++now_frame;
    re4dc_water_ps2_draw(nullptr);
    assert(fallback_calls==fallback+1 && s_water29_last_admission==WATER29_TOTAL_REFUSAL);
    native_fail_after=1;native_calls=0;fallback=fallback_calls;
    ++now_frame;re4dc_water_ps2_draw(nullptr);
    assert(s_water29_partial>0 && fallback_calls==fallback &&
           s_water29_last_admission==WATER29_PARTIAL_REFUSAL);
    native_fail_after=-1;
    puts("PASS EF13 binding, refusal, no-water, retirement");
#endif
}
'''


def production_cpp(src):
        main = between(src, "struct WaterPs2Row {", "#ifndef RE4DC_WATER_PS2_FLIP")
        room = between(src, "static int WaterPs2RoomOn(u32 room)", "#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT\n// WATER_PS2_EXT")
        ext = between(src, "struct WaterPs2ExtRow {", "#ifndef RE4DC_WATER_PS2_EXT_ROOMS")
        ext_begin = src.index("static int WaterPs2ExtRoomOn(u32 room)")
        ext_room = src[ext_begin:src.index('\n}\n', ext_begin)+3]
        layer = (between(src, '#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29\n#include "water_layer29.h"', "// 1 when the current room")
                 if '#include "water_layer29.h"' in src else '')
        rows = between(src, 'extern "C" int re4dc_water_ps2_rows(void)', "// The pattern cEsp::AnmMove")
        pattern = between(src, "static u32 WaterPs2Pattern(", "// OT callback")
        draw = between(src, 'extern "C" void re4dc_water_ps2_draw(void*)', "// EspgenTrans")
        queue = between(src, 'extern "C" void re4dc_water_ps2_queue(void)', "// The surface's OT entry")
        queue = queue.rsplit('#endif', 1)[0]
        water45 = between(src, 'extern "C" void re4dc_water45_queue(EspgenWork* w)', "#endif\n\n// The surface's OT entry") if False else src[src.index('extern "C" void re4dc_water45_queue(EspgenWork* w)'):]
        water45 = water45[:water45.index('\n}\n')+3]
        return PRELUDE + main + room + ext + ext_room + layer + rows + pattern + draw + queue + water45 + CASES


class WaterLayer29Test(unittest.TestCase):
    def test_primary_makefile_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            kos = Path(tmp) / "kos-stub"
            kos.mkdir()
            (kos / "Makefile.rules").write_text("")
            targets = ["obj/src/game/espgen45.o", "obj/src/game/espgen.o",
                       "obj/platform/native_ui.o"]
            args = ["make", "-f", "Makefile", "-n", f"KOS_BASE={kos}",
                    "ROUTE_CH13=1", "WATER_PS2=1", "WATER45_NATIVE=1", *targets]
            def run(extra):
                return subprocess.run(args + extra, cwd=ROOT / "port/dreamcast/game",
                                      text=True, capture_output=True)
            arms = [run([]), run(["WATER_LAYER29=0"]), run(["WATER_LAYER29=1"])]
            for arm in arms:
                self.assertEqual(arm.returncode, 0, arm.stderr)
            commands = [[s for s in arm.stdout.splitlines() if s.startswith("kos-c++")]
                        for arm in arms]
            self.assertEqual(commands[0], commands[1])
            self.assertEqual(len(commands[2]), len(targets))
            for i, command in enumerate(commands[2]):
                self.assertEqual(command.count("-DRE4DC_WATER_LAYER29=1"), int(i == 0))
            for extra in (["WATER_LAYER29="], ["WATER_LAYER29=0 1"],
                          ["WATER_LAYER29=2"], ["WATER_LAYER29=%"],
                          ["WATER_LAYER29=0%"], ["WATER_LAYER29=1%"],
                          ["WATER_LAYER29=1", "ROUTE_CH13=0"],
                          ["WATER_LAYER29=1", "WATER_PS2=0"]):
                self.assertNotEqual(run(extra).returncode, 0, extra)

    def test_public_source_producer(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "water_layer29_source.inc"
            subprocess.run([sys.executable, str(PRODUCER), "--out", str(out)], check=True)
            self.assertEqual(METADATA.read_bytes(), out.read_bytes())
            bad_main = Path(tmp) / "bad_main.inc"
            original = (ROOT / "src/game/water_ps2_table.inc").read_text()
            bad_main.write_text(original.replace("r107.ps2.eff0", "r108.ps2.eff0", 1))
            check = subprocess.run([sys.executable, str(PRODUCER), "--main", str(bad_main),
                                    "--out", str(out)], capture_output=True, text=True)
            self.assertNotEqual(check.returncode, 0)

    def test_production_adapter_and_consumer(self):
        cpp = production_cpp(SOURCE.read_text())
        sanitizer = os.environ.get("WATER29_SANITIZE") == "1"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.cpp"
            path.write_text(cpp)
            for ext_enabled, main_mask, ext_mask in ((1, 0x3f, 7), (0, 0x3f, 0), (1, 0x3e, 7)):
              outputs = []
              for enabled in (0, 1):
                exe = Path(tmp) / f"water-{enabled}"
                cmd = ["g++", "-std=c++17", "-O1" if sanitizer else "-O2", "-g",
                       "-Wall", "-Wextra", "-Wno-unused-variable", "-Wno-unused-function",
                       "-Wno-address", "-Wno-type-limits",
                       "-Wno-missing-field-initializers", "-DRE4DC_WATER_PS2=1",
                       f"-DRE4DC_WATER_PS2_EXT={ext_enabled}", "-DRE4DC_WATER45_NATIVE=1",
                       f"-DRE4DC_WATER_PS2_ROOMS={main_mask}", f"-DRE4DC_WATER_PS2_EXT_ROOMS={ext_mask}",
                       "-DRE4DC_WATER_PS2_FLIP=8",
                       f"-DRE4DC_WATER_LAYER29={enabled}",
                       f"-I{ROOT / 'src/game'}", str(path), "-o", str(exe)]
                if sanitizer:
                    cmd += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
                subprocess.run(cmd, check=True)
                out = subprocess.check_output([str(exe)], text=True)
                outputs.append(out)
              self.assertEqual(outputs[0].split("ENDCANON")[0], outputs[1].split("ENDCANON")[0])
              self.assertIn("PASS EF13 binding", outputs[1])
              self.assertIn("FOOTPRINT main=", outputs[1])
              print(f"EF13 ext={ext_enabled} main_mask={main_mask:#x}: " +
                    next(line for line in outputs[1].splitlines() if line.startswith("FOOTPRINT")))

    def test_pinned_feature_off_preprocessing(self):
        baseline = subprocess.check_output(["git", "show", f"{BASE}:src/game/espgen45.cpp"],
                                           cwd=ROOT, text=True)
        with tempfile.TemporaryDirectory() as tmp:
            base_file = Path(tmp) / "base.cpp"
            new_file = Path(tmp) / "new.cpp"
            # Exclude fixture assertions: libstdc++'s assert embeds the source
            # line of each synthetic CASES call even when production tokens match.
            base_file.write_text(production_cpp(baseline).split("\nint main() {")[0])
            new_file.write_text(production_cpp(SOURCE.read_text()).split("\nint main() {")[0])
            for ext_enabled, main_mask, ext_mask in ((1, 0x3f, 7), (0, 0x3f, 0), (1, 0x3e, 7)):
                flags = ["-DRE4DC_WATER_PS2=1", f"-DRE4DC_WATER_PS2_EXT={ext_enabled}",
                         "-DRE4DC_WATER45_NATIVE=1", f"-DRE4DC_WATER_PS2_ROOMS={main_mask}",
                         f"-DRE4DC_WATER_PS2_EXT_ROOMS={ext_mask}", "-DRE4DC_WATER_PS2_FLIP=8",
                         "-DRE4DC_WATER_LAYER29=0", f"-I{ROOT / 'src/game'}"]
                original = subprocess.check_output(["g++", "-E", "-P", *flags, str(base_file)], text=True)
                updated = subprocess.check_output(["g++", "-E", "-P", *flags, str(new_file)], text=True)
                self.assertEqual(original, updated)
                absent = [f for f in flags if not f.startswith("-DRE4DC_WATER_LAYER29=")]
                self.assertEqual(original, subprocess.check_output(
                    ["g++", "-E", "-P", *absent, str(new_file)], text=True))
                same_name = Path(tmp) / "source.cpp"
                object_file = Path(tmp) / "source.o"
                same_name.write_text(base_file.read_text())
                subprocess.run(["g++", "-O2", "-w", "-c", *flags, str(same_name), "-o", str(object_file)], check=True)
                old_object = object_file.read_bytes()
                same_name.write_text(new_file.read_text())
                subprocess.run(["g++", "-O2", "-w", "-c", *flags, str(same_name), "-o", str(object_file)], check=True)
                self.assertEqual(old_object, object_file.read_bytes())


if __name__ == "__main__":
    unittest.main()
