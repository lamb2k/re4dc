#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
#include "fallback_audit35.h"
#endif
#line 1
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "fallback_audit29.h"
#endif
#line 1
// game/cloth.cpp: grid cloth simulation (esp4e sheets): a nx*ny grid of points joined by springs,
// pulled down by gravity, drawn as triangle strips with the lights of the room.

#include "light.h"
#include "global.h"
#include "model.h"
#include "camera.h"
#include "gx.h"
#include "tpl.h"
#include "cloth.h"
#include "math_sub.h"
#include "main_mem.h"
#include "trans_ot.h"

extern "C" {
// game/trans_lit.cpp
#if defined(RE4DC_CLOTH_LIGHT_ABI_FIX) && RE4DC_CLOTH_LIGHT_ABI_FIX && !defined(__PPC__)
void commonClothLightSet(cLight** list, int n, Vec* pos, f32 radius);
#else
void commonClothLightSet(cLight** list, int n, Vec pos, f32 radius);
#endif
void OSReport(const char* fmt, ...);
}

Cloth ClothWk[8];
#if defined(RE4DC_CLOTH_SHEET11) && RE4DC_CLOTH_SHEET11
#include <cstdint>
// Render-only publication identity for the existing fixed cloth pool. Retiring
// or replacing the same cell during texture I/O cannot revive its old view.
static unsigned cloth11_incarnation[8]={1,1,1,1,1,1,1,1};
static unsigned cloth11_slot(const Cloth* p){
    const auto a=reinterpret_cast<std::uintptr_t>(p),base=reinterpret_cast<std::uintptr_t>(ClothWk);
    if(a<base || a-base>=sizeof ClothWk || (a-base)%sizeof(Cloth))return 8;
    return unsigned((a-base)/sizeof(Cloth));
}
static unsigned cloth11_epoch(const Cloth* p){const unsigned slot=cloth11_slot(p);return slot<8?cloth11_incarnation[slot]:0;}
static void cloth11_replace(Cloth* p){const unsigned slot=cloth11_slot(p);if(slot<8 && cloth11_incarnation[slot])++cloth11_incarnation[slot];}
#endif

#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
// CLOTH_NATIVE=1 (effects30.mk; render only, approximation): clothTrans draws through immediate GX, which the Dreamcast
// build sinks, so the esp4e cloth sheets (hanging fabric, flags, sacking) were simulated every frame but never drawn.
// Here each sheet goes to the native effect FIFO (native_effect_strip21.inc re4dc_effect_mesh21) as view-space strips,
// two rows at a time from the stack. Lighting approximation: one colour per sheet, the material colour times (the
// scenery ambient + half of each picked light's colour with its range falloff), standing in for GX per-vertex lighting.
// Reads game state only; the simulation and its RNG run as before. A sheet wholly off the view skips its draw-side
// light pick (re4dc_cloth_visible). On a drawn coarse image the sheets are drawn from Trans (trans.cpp ClothDrawNow).
#include <string.h>
extern "C" void re4dc_log(const char* fmt, ...);
#include "native_ui.h"
#include "native_cloth_sheet11.hpp"
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
#include "cloth_material11_source.hpp"
extern "C" void re4dc_cloth_material_retire11(){
    re4dc::cloth_material11::open_slots=0;
    for(auto& cloth:ClothWk)cloth11_replace(&cloth);
}
#endif
#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14
#include "re4dc_xm.h"
#endif
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#include "native_draw_result.hpp"
#endif
// Conservative view test of a sheet's bounding sphere (top-row centre, width + hanging height) in view space:
// behind the camera, beyond 40 m, or outside a 1.6 / 1.3 slope frustum (wider than the game's 4:3 view).
static int re4dc_cloth_visible(const Cloth* pCL)
{
    Vec v;
    PSMTXMultVec(pG->Cam.v_mat, (Vec*) &pCL->center, &v);
    const f32 R = pCL->radius * 2.0f + pCL->Hgap * pCL->divV * pCL->Scale;
    const f32 depth = -v.z;
    if (depth < -R || depth - R > 40000.0f) {
        return 0;
    }
    const f32 d = depth > 0.0f ? depth : 0.0f;
    const f32 ax = v.x < 0.0f ? -v.x : v.x, ay = v.y < 0.0f ? -v.y : v.y;
    if (ax - R > d * 1.6f + R || ay - R > d * 1.3f + R) {
        return 0;
    }
    return 1;
}
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
static re4dc::NativeDrawResult re4dc_cloth_native(Cloth* pCL, cLight** list, Vec* pos, f32 size)
#else
static int re4dc_cloth_native(Cloth* pCL, cLight** list, Vec* pos, f32 size)
#endif
{
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
    const unsigned observed_slot=cloth11_slot(pCL);
    const unsigned observation=re4dc_cloth_observe_begin11({observed_slot,
        cloth11_epoch(pCL),pG->Frame_cnt,
        observed_slot<8?re4dc::cloth_pub11::grid_generation[observed_slot]:0,
        observed_slot<8?unsigned(pCL->pTobjA!=nullptr):0});
    const auto observed_draw=[&]()->re4dc::NativeDrawResult {
#endif
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    bool single_selected11=false,single_started11=false;
    const auto material_draw11=[&]()->re4dc::NativeDrawResult {
#endif
#if RE4DC_CLOTH_SHEET11
    if(cloth11_slot(pCL)>=8)return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(!re4dc::cloth_material11::admitted(cloth11_slot(pCL)) || !re4dc_cloth_frame_open11())return {re4dc::NativeDrawOutcome::PartialAbort};
#endif
    // A queued callback may arrive after Destroy/Init. Do not dereference its
    // texture/grid or enter the recovered GX fallback for a retired pool cell.
    if(!(pCL->be_flag&1))return {re4dc::NativeDrawOutcome::PartialAbort};
    if(!(pCL->be_flag&0x20))return {re4dc::NativeDrawOutcome::PolicySkip};
#endif
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    unsigned copied_words[8];const unsigned* to=nullptr;
    const bool second_material=pCL->pTobjA!=0;
    re4dc::cloth_material11::Source material_source;
    const u32 source_color=(u32(pCL->color.r)<<24)|(u32(pCL->color.g)<<16)|(u32(pCL->color.b)<<8)|pCL->color.a;
    const auto saturated_source=[&](){
        const auto& ambient=LightMgr.getEnvPtr()->AmbientScr;
        if(pCL->x74 || pCL->color.r<64 || pCL->color.g<64 || pCL->color.b<64 || pCL->color.a<64 ||
            ambient.r!=255 || ambient.g!=255 || ambient.b!=255)return false;
        // commonClothLightSet installs its black light when this list is empty:
        // full ambient leaves the source material channels unchanged. Refuse
        // direct/per-vertex and local-ambient light lifetimes in this slice.
        for(unsigned i=0;i<8;++i)if(list[i])return false;
        return true;
    };
    if(second_material){
        if(!saturated_source() || !material_source.capture(pCL->tex,pCL->pTobjA))
            return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
        to=material_source.primary.words;
    }else if(saturated_source() && re4dc_cloth_esp4e_words11(pCL,copied_words) &&
             material_source.capture_single(pCL->tex,copied_words)){
        // Real Esp4e has no secondary. White TEXA/TEXC and full ambient make
        // source SCALE4/clamp constant white for every channel>=64.
        single_selected11=true;to=material_source.primary.words;
    }else if(pCL->tex){
        // Keep the old ordinary material path before an exact selection.
        std::memcpy(copied_words,pCL->tex,sizeof copied_words);to=copied_words;
    }
#else
    const u32* to = (const u32*) pCL->tex;   // gx_stub.cpp GXTexObj: w[0] image, w[1] w<<16|h, w[2] format, w[3] wrap
#endif
#if defined(RE4DC_CLOTH_TILES11) && RE4DC_CLOTH_TILES11
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if (to == 0 || to[0] == 0 || pCL->divH < 2 || pCL->divV < 2) {
#else
    if (to == 0 || to[0] == 0 || pCL->pTobjA != 0 || pCL->divH < 2 || pCL->divV < 2) {
#endif
#else
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if (to == 0 || to[0] == 0 || pCL->divH < 2 || pCL->divV < 2 || pCL->divH > 100) {
#else
    if (to == 0 || to[0] == 0 || pCL->pTobjA != 0 || pCL->divH < 2 || pCL->divV < 2 || pCL->divH > 100) {
#endif
#endif
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
        return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
#else
        return 0;
#endif
    }
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    if(!pCL->pVer)return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
    re4dc::NativeDrawProgress progress;
#endif
    Re4dcEffectMesh21 m;
    memset(&m, 0, sizeof(m));
    m.image.pixels = (const void*) to[0];
    m.image.width = to[1] >> 16;
    m.image.height = to[1] & 0xFFFF;
    m.image.format = to[2];
    m.image.palette_format = 0xFFFFFFFFU;
    if (pCL->tlut != 0 && (m.image.format == 8 || m.image.format == 9)) {
        const u32* tl = (const u32*) pCL->tlut;   // GXTlutObj: w[0] lut, w[1] format, w[2] entries
        m.image.palette = (const void*) tl[0];
        m.image.palette_format = tl[1];
        m.image.palette_bytes = tl[2] * 2;
    }
    m.wrap_s = ((to[3] >> 8) & 0xFF) == 1;
    m.wrap_t = (to[3] & 0xFF) == 1;
    if (pCL->x74 == 0) {
        m.src = 4;   // GX SRCALPHA / INVSRCALPHA = PVR 4 / 5
        m.dst = 5;
    } else {
        m.src = 1;   // additive
        m.dst = 1;
    }
    f32 lr = LightMgr.getEnvPtr()->AmbientScr.r, lg = LightMgr.getEnvPtr()->AmbientScr.g,
        lb = LightMgr.getEnvPtr()->AmbientScr.b;
    for (int i = 0; i < 8; i++) {
        cLight* l = list[i];
        if (l == 0) {
            continue;
        }
        f32 k = (f32) (int) l->DispCol.a * 0.0078125f;
        if (l->xD != 7) {
            k *= 0.5f;
        }
        if (l->Radius > 0.0f) {
            Vec p = l->World;
            f32 d = GetDistance3(pos, &p) - size;
            f32 f = d <= 0.0f ? 1.0f : (l->Radius - d) / l->Radius;
            if (f <= 0.0f) {
                continue;
            }
            k *= f > 1.0f ? 1.0f : f;
        }
        lr += k * l->DispCol.r;
        lg += k * l->DispCol.g;
        lb += k * l->DispCol.b;
    }
    const f32 cr = pCL->color.r * (lr > 255.0f ? 255.0f : lr) * (1.0f / 255.0f);
    const f32 cg = pCL->color.g * (lg > 255.0f ? 255.0f : lg) * (1.0f / 255.0f);
    const f32 cb = pCL->color.b * (lb > 255.0f ? 255.0f : lb) * (1.0f / 255.0f);
    m.color = ((u32) pCL->color.a << 24) | ((u32) cr << 16) | ((u32) cg << 8) | (u32) cb;
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(second_material || single_selected11){
        // Source stage0 is white RGB565 * raster, SCALE4/clamp. Every source
        // material channel>=64 saturates to255 under the admitted lighting.
        // Stage1 modulates by the opaque secondary, leaving it unchanged;
        // alpha255 always passes the source >4 test. Keep source4/5 blend,
        // two-sided geometry and the normal Z-write policy in preparation.
        m.image=single_selected11?material_source.primary.image:material_source.secondary.image;m.color=0xffffffffU;
    }
#endif
    RE4DC_GXF_GET_PROJECTION(m.projection);
    RE4DC_GXF_GET_VIEWPORT(m.viewport);
    Mtx sc, tmp, mv;
    PSMTXScale(sc, pCL->Scale, pCL->Scale, pCL->Scale);
    PSMTXConcat(pCL->mat, sc, tmp);
    PSMTXConcat(pG->Cam.v_mat, tmp, mv);
    const u32 cols = pCL->divH;
#if RE4DC_CLOTH_SHEET11
    if(pCL->divV>50)return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
    // No simulation writes: preflight source finiteness before the first packet.
    for(unsigned i=0;i<3;++i)for(unsigned j=0;j<4;++j)if(!__builtin_isfinite(mv[i][j]))return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
    const Vec* source=pCL->pVer;const unsigned rows=pCL->divV,source_frame=pG->Frame_cnt,source_epoch=cloth11_epoch(pCL);
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    const unsigned source_grid=re4dc::cloth_pub11::grid_generation[cloth11_slot(pCL)];
    if((second_material || single_selected11) && !source_grid)return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
#endif
    if(!source_epoch)return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
    for(unsigned i=0;i<cols*rows;++i)if(!__builtin_isfinite(source[i].x) || !__builtin_isfinite(source[i].y) || !__builtin_isfinite(source[i].z))
        return {re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
    m.cols=cols;m.rows=rows;
    Re4dcClothMaterial11 material;re4dc::NativeDrawResult stop{re4dc::NativeDrawOutcome::Refused};
    const auto source_current=[&](){return cloth11_epoch(pCL)==source_epoch && pG->Frame_cnt==source_frame &&
        pCL->pVer==source && pCL->divH==cols && pCL->divV==rows
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
        && (!(second_material || single_selected11) || source_grid==re4dc::cloth_pub11::grid_generation[cloth11_slot(pCL)])
#endif
        ;};
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    const auto material_current=[&](){
        // Room/pool retirement and grid mutation reject the old view before
        // any embedded source object or archive pixel may be read again.
        if(!source_current())return false;
        unsigned current_words[8];
        if(single_selected11 && (!re4dc_cloth_esp4e_words11(pCL,current_words) ||
            std::memcmp(current_words,material_source.primary.words,sizeof current_words)))return false;
        return (!(second_material || single_selected11) ||
        (pCL->tex==material_source.primary.object && pCL->pTobjA==material_source.secondary.object &&
         source_color==((u32(pCL->color.r)<<24)|(u32(pCL->color.g)<<16)|(u32(pCL->color.b)<<8)|pCL->color.a) &&
         saturated_source() && material_source.current()));};
    const Re4dcClothCheck11 check{&material_current,[](const void* p){
        return (*static_cast<const decltype(material_current)*>(p))();}};
    single_started11=single_selected11;
    const int prepared=(second_material || single_selected11)?re4dc_cloth_material11(&m,&material_source,check,&material,&stop):
        re4dc_cloth_prepare11(&m,&material,&stop);
    if(!prepared && stop.outcome==re4dc::NativeDrawOutcome::PartialAbort)return stop;
    if(!material_current())return {re4dc::NativeDrawOutcome::PartialAbort};
#else
    const int prepared=re4dc_cloth_prepare11(&m,&material,&stop);
#endif
    // Even failed texture I/O may retire/reuse the source. This is terminal,
    // including zero publication: the source GX fallback must not read it.
    if(!source_current())return {re4dc::NativeDrawOutcome::PartialAbort};
    if(!prepared)return stop;
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
    re4dc_cloth_observe_bind11(&material,observation);
#endif
    f32 band[2][100][3];float* top=&band[0][0][0];float* bottom=&band[1][0][0];
#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14
    // Preparation can yield. Check source ownership before and after each
    // callback-free XMTRX batch. The tile start/count bound both row buffers.
    auto transform_batch=[&](unsigned source_row,unsigned first,unsigned count,float* dst)->int{
        if(!source_current())return -1;
        const Vec* input=source+source_row*cols+first;
        if(!re4dc_zam_xm_points14(mv,input,count*sizeof(Vec),sizeof(Vec),
                                   dst,count*3*sizeof(float),3*sizeof(float),count))return 0;
        return source_current()?1:-1;
    };
#endif
#if defined(RE4DC_CLOTH_TILES11) && RE4DC_CLOTH_TILES11
    if(cols>100){
    // Source draws row-major strips. Split each row into at most 100-column
    // strips, sharing the seam column; never finish a whole column tile's rows
    // before moving to the next tile. The same source cell diagonal survives.
    for(unsigned row=0;row+1<rows;++row){
        for(unsigned first=0;first+1<cols;){
            if(!source_current()){progress.add({re4dc::NativeDrawOutcome::PartialAbort});return progress.result;}
            const unsigned columns=cols-first<100?cols-first:100;
#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14
            int transformed=transform_batch(row,first,columns,top);
            if(transformed==1)transformed=transform_batch(row+1,first,columns,bottom);
            if(transformed!=1){progress.add({transformed<0?re4dc::NativeDrawOutcome::PartialAbort:
                re4dc::NativeDrawOutcome::UnsupportedBeforePublication});return progress.result;}
#else
            auto transform_tile=[&](unsigned source_row,float* dst){
                for(unsigned i=0;i<columns;++i){
                    if(!source_current())return false;
                    Vec v;PSMTXMultVec(mv,source+source_row*cols+first+i,&v);
                    dst[3*i]=v.x;dst[3*i+1]=v.y;dst[3*i+2]=v.z;
                }
                return source_current();
            };
            if(!transform_tile(row,top) || !transform_tile(row+1,bottom)){
                progress.add({re4dc::NativeDrawOutcome::PartialAbort});return progress.result;
            }
#endif
            const Re4dcClothBand11 view{top,bottom,columns,first,row};
            const auto result=re4dc_cloth_band11(&material,&view);
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
            if(result.outcome==re4dc::NativeDrawOutcome::PartialAbort){progress.add(result);return progress.result;}
#endif
            if(!source_current()){progress.add({re4dc::NativeDrawOutcome::PartialAbort,result.submitted,result.queued});return progress.result;}
            if(!progress.add(result))return progress.result;
            first+=columns-1;
        }
    }
    return progress.result;
    }
#endif
#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14
    auto transform=[&](unsigned row,float* dst)->int{return transform_batch(row,0,cols,dst);};
    int transformed=transform(0,top);
    if(transformed!=1){progress.add({transformed<0?re4dc::NativeDrawOutcome::PartialAbort:
        re4dc::NativeDrawOutcome::UnsupportedBeforePublication});return progress.result;}
#elif defined(RE4DC_CLOTH_TILES11) && RE4DC_CLOTH_TILES11
    auto transform=[&](unsigned row,float* dst){for(unsigned i=0;i<cols;++i){
        if(!source_current())return false;
        Vec v;PSMTXMultVec(mv,source+row*cols+i,&v);
        dst[3*i]=v.x;dst[3*i+1]=v.y;dst[3*i+2]=v.z;
    }return source_current();};
    if(!transform(0,top)){progress.add({re4dc::NativeDrawOutcome::PartialAbort});return progress.result;}
#else
    auto transform=[&](unsigned row,float* dst){for(unsigned i=0;i<cols;++i){Vec v;PSMTXMultVec(mv,source+row*cols+i,&v);dst[3*i]=v.x;dst[3*i+1]=v.y;dst[3*i+2]=v.z;}};
    transform(0,top);
#endif
    for(unsigned row=0;row+1<rows;++row){
        if(!source_current()){progress.add({re4dc::NativeDrawOutcome::PartialAbort});return progress.result;}
#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14
        transformed=transform(row+1,bottom);
        if(transformed!=1){progress.add({transformed<0?re4dc::NativeDrawOutcome::PartialAbort:
            re4dc::NativeDrawOutcome::UnsupportedBeforePublication});return progress.result;}
        const Re4dcClothBand11 view{top,bottom,cols,0,row};
#elif defined(RE4DC_CLOTH_TILES11) && RE4DC_CLOTH_TILES11
        if(!transform(row+1,bottom)){progress.add({re4dc::NativeDrawOutcome::PartialAbort});return progress.result;}
        const Re4dcClothBand11 view{top,bottom,cols,0,row};
#else
        transform(row+1,bottom);const Re4dcClothBand11 view{top,bottom,cols,0,row};
#endif
        const auto result=re4dc_cloth_band11(&material,&view);
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
        if(result.outcome==re4dc::NativeDrawOutcome::PartialAbort){progress.add(result);return progress.result;}
#endif
        if(!source_current()){progress.add({re4dc::NativeDrawOutcome::PartialAbort,result.submitted,result.queued});return progress.result;}
        if(!progress.add(result))return progress.result;
        float* previous=top;top=bottom;bottom=previous;
    }
    return progress.result;
#else
    f32 band[2 * 100 * 3];
    m.positions = band;
    m.cols = cols;
    m.rows = 2;
    m.v_step = 1.0f / (f32) (pCL->divV - 1);
    for (int row = 0; row + 1 < pCL->divV; row++) {
        for (u32 s = 0; s < 2; s++) {
            const Vec* src = &pCL->pVer[(row + s) * cols];
            f32* dst = band + s * cols * 3;
            for (u32 i = 0; i < cols; i++, src++, dst += 3) {
                Vec v;
                PSMTXMultVec(mv, src, &v);
                dst[0] = v.x;
                dst[1] = v.y;
                dst[2] = v.z;
            }
        }
        m.v_top = row * m.v_step;
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
        if(!progress.add(re4dc_effect_mesh21_result(&m)))return progress.result;
#else
        re4dc_effect_mesh21(&m);
#endif
    }
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    return progress.result;
#else
    return 1;
#endif
#endif
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    };
    const auto material_result11=material_draw11();
    // This selected producer owns the result. A failed cold acquisition or
    // later band cannot replay the previous approximate ordinary producer.
    if(single_started11 && material_result11.fallback_allowed())return {re4dc::NativeDrawOutcome::PartialAbort};
    return material_result11;
#endif
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
    };
    const auto result=observed_draw();
    re4dc_cloth_observe_finish11(observation,result,cloth11_epoch(pCL),pG->Frame_cnt,
        observed_slot<8?re4dc::cloth_pub11::grid_generation[observed_slot]:0);
    return result;
#endif
}
#endif

// clothTrans builds a temporary cModel for the light setup. The real cModel is 0x320 bytes
// (see the KNOWN DEBT note in docs/matching.md: motion/atari fields still live in cEm/cObj), so an
// unused pad local follows it to keep the original frame layout until cModel carries them itself.

f32 K_PARAM = 7.5f;   // spring constant
f32 G_PARAM = 0.5f;   // gravity
f32 T_PARAM = 0.06f;  // time step
static f32 D_PARAM = 0.006f;  // unused (the 0.006 word after T_PARAM in .sdata; name unknown)

// Boot: marks the 8 cloth works free.
void ClothInit()
{
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    re4dc::cloth_material11::open_slots=0;
#endif
#if defined(RE4DC_CLOTH_SHEET11) && RE4DC_CLOTH_SHEET11
    for(auto& cloth:ClothWk)cloth11_replace(&cloth);
#endif
    int i;

    for (i = 0; i < 8; i++) {
        ClothWk[i].be_flag = 0;
    }
}

// Room start: frees every live cloth's grid memory and marks the works free.
void ClothRoomInit()
{
    ClothInit();
}

// Dead-stripped in the DOL (only its strings and its 0.0f pool survive, ahead of Cloth::Set's
// .rodata): a helper that allocates a Vec and normalises into it. Body unknown; this one
// reproduces the string order (__FILE__ before "VECNormalize:[%s/%d]") and the pool.
static Vec* clothAllocNormal(Vec* dir)
{
#line 120 "D:/Bio4/Prog/cloth.cpp"
    Vec* v = (Vec*) MEM_ALLOC(sizeof(Vec), 1, 13);
    VECNormalize(dir, v);
    return v;
}

// Builds an nx x ny cloth: allocates the vertex / normal / speed grids, lays the points out w
// apart horizontally and h vertically hanging from the top row at pos_ / ang, binds the texture
// (and TLUT) and the owner pointer p_; be_flag 0x31 = live, drawn. The top row (or the top four
// rows in the alternate pin mode) stays fixed.
void Cloth::Set(Vec ang, Vec pos_, u8 nx_, u8 ny_, f32 w, GXTexObj* tex_, f32 h, void* p_, f32 d, GXTlutObj* tlut_,
                int flag_)
{
#if defined(RE4DC_CLOTH_SHEET11) && RE4DC_CLOTH_SHEET11
    cloth11_replace(this);
#endif
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    re4dc::cloth_material11::close(cloth11_slot(this));
    const unsigned material_set_epoch11=cloth11_epoch(this);
#endif
    Vec zero = {0.0f, 0.0f, 0.0f};
    Vec n = {0.0f, 0.0f, 1.0f};
    Vec* pp;
    Vec* pn;
    Vec* ps;
    u32 rowSize;
    int i;
    int j;

    Wgap = w;
    Hgap = h;
    Scale = d;
    divH = nx_;
    divV = ny_;
    x70 = flag_;
    RotMatrix(mat, &ang);
    TransMatrix(mat, &pos_);
    rowSize = ny_ * sizeof(Vec);
#line 212 "D:/Bio4/Prog/cloth.cpp"
    m_pMem = MEM_ALLOC(nx_ * rowSize * 3, 1, 13);
    if (m_pMem == 0) {
        OSReport("ClothSet(): Can't allocate memory.\n");
        be_flag = 0;
    }
    pp = (Vec*) m_pMem;
    pVer = pp;
    pn = pp + nx_ * ny_;
    pNor = pn;
    ps = pp + nx_ * 2 * ny_;
    pSpd = ps;
    for (j = 0; j < ny_; j++) {
        for (i = 0; i < nx_; i++) {
            pp->x = i * Wgap;
            pp->y = -j * Hgap;
            if (flag_ != 0 && (j >= 0 && j <= 3)) {
                int m = i % 6;
                pp->z = sinf(m * 6.2831855f / 6.0f) * -2.0f;
            } else {
                pp->z = 0.0f;
            }
            *ps = zero;
            *pn = n;
            pp++;
            ps++;
            pn++;
        }
    }
    for (i = 0; i < 120; i++) {
        calcSpeed(0.9f);
        move();
    }
    center.x = Wgap * divH * 0.5f * Scale;
    center.y = 0.0f;
    center.z = 0.0f;
    PSMTXMultVec(mat, &center, &center);
    radius = Wgap * divH * 0.5f * Scale;
    tex = tex_;
    tlut = tlut_;
    pTobjA = p_;
    be_flag = 0x31;
    colR = 0xFF;
    colG = 0xFF;
    colB = 0xFF;
    colA = 0xFF;
    x74 = 0;
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(cloth11_epoch(this)==material_set_epoch11)
        re4dc::cloth_material11::reopen(cloth11_slot(this),material_set_epoch11);
#endif
}

// Moves the cloth's hanging matrix.
void Cloth::SetPosAng(Vec ang, Vec pos_)
{
#if (defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11) || (defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11)
    re4dc::cloth_pub11::grid_write(cloth11_slot(this));
#endif
    RotMatrix(mat, &ang);
    TransMatrix(mat, &pos_);
}

// Frees the grid memory and the work.
void Cloth::Destroy()
{
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    re4dc::cloth_material11::close(cloth11_slot(this));
#endif
#if defined(RE4DC_CLOTH_SHEET11) && RE4DC_CLOTH_SHEET11
    cloth11_replace(this);
#endif
    Mem_free(m_pMem);
    be_flag = 0;
}

// Relocates an in-file TPL in place (descriptor / image / CLUT offsets -> pointers), once.
void ClothCalcTplAddr(void* tpl)
{
    TEXPalette* pal = (TEXPalette*) tpl;
    TEXDescriptor* d;
    u32 i;

    if (pal == 0) {
        return;
    }
    if ((s32) pal->descriptorArray < 0) {
        return;
    }
    pal->descriptorArray = (TEXDescriptor*) ((u32) pal->descriptorArray + (u32) pal);
    for (i = 0; i < pal->numDescriptors; i++) {
        d = &pal->descriptorArray[i];
        d->textureHeader = (TEXHeader*) ((u32) pal + (u32) d->textureHeader);
        d->textureHeader->data = (void*) ((u32) pal + (u32) d->textureHeader->data);
        if (d->CLUTHeader != 0) {
            d->CLUTHeader = (CLUTHeader*) ((u32) pal + (u32) d->CLUTHeader);
            d->CLUTHeader->data = (void*) ((u32) pal + (u32) d->CLUTHeader->data);
        }
    }
}

// Initialises a GXTexObj (and TLUT for CI formats) from texture `no` of the TPL; 1 on success.
int ClothTexSetUp(void* tpl, GXTexObj* tex, int no, GXTlutObj* tlut)
{
    TEXDescriptor* d;
    TEXHeader* t;
    CLUTHeader* c;
    int ret = 0;

    ClothCalcTplAddr(tpl);
    d = TEXGet((TEXPalette*) tpl, 0);
    t = d->textureHeader;
    if (t->format >= 8 && t->format <= 9) {
        GXInitTexObjCI(tex, t->data, t->width, t->height, t->format, 0, 0, 0, 0);
        ret = 1;
        c = d->CLUTHeader;
        GXInitTlutObj(tlut, c->data, c->format, c->numEntries);
        GXLoadTlut(tlut, 0);
    } else {
        GXInitTexObj(tex, t->data, t->width, t->height, t->format, 0, 0, 0);
    }
    return ret;
}

// One simulation step of the speeds: spring forces (K_PARAM) toward each neighbour's rest
// distance (Wgap / Hgap), gravity G_PARAM, then the speed scaled by `damping`.
#if defined(RE4DC_CLOTH_SPRING) && RE4DC_CLOTH_SPRING
// GAME_CLOTH_SPRING (game30.mk; lane logic 2026-10-04; exact): every spring is evaluated from both of its ends
// (k toward k+1, then k+1 toward k), and the second evaluation is the first one negated bit for bit: p[a] - p[b]
// is -(p[b] - p[a]), the magnitude squares the components, the factor K (len - gap) / len is the same, and
// (-v) * f is -(v * f). Each spring's force is computed once, at its first end (the right spring of k, the down
// spring of row i), and the other end adds its negation (s + (-v) is s - v) in the source's order: left, right,
// up, down, gravity, damping. A neighbour the source skips (the interior of the pinned top row) has computed
// nothing, so its spring is evaluated as before.
static Vec clothDn[256];
static u8 clothDnOk[256];   // the spring below row i-1's point j: 0 not computed, 1 no force, 2 force in clothDn
#if RE4DC_CLOTH_SPRING == 2
#define calcSpeed calcSpeedSrc
#endif
#endif
#if !(defined(RE4DC_CLOTH_SPRING) && RE4DC_CLOTH_SPRING == 1)
void Cloth::calcSpeed(f32 damping)
{
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::ClothSpringSource, 1);
    re4dc::fa35::hit(re4dc::fa35::ClothPoints, unsigned(divH) * unsigned(divV));
#endif
#line 341
    Vec v;
    Vec* p = pVer;
    Vec* s = pSpd;
    int i;
    int j;
    int k;
    int w;
    f32 len;

    for (i = 0; i < divV; i++) {
        for (j = 0; j < divH; j++) {
            if (i == 0 && j != 0 && j != divH - 1) {
                continue;
            }
            w = divH;
            k = j + i * w;
            if (j != 0) {
                PSVECSubtract(&p[k - 1], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Wgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Wgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            if (j != divH - 1) {
                PSVECSubtract(&p[k + 1], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Wgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Wgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            if (i != 0) {
                PSVECSubtract(&p[k - w], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Hgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Hgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            if (i != divV - 1) {
                PSVECSubtract(&p[k + w], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Hgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Hgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            s[k].y -= G_PARAM;
            PSVECScale(&s[k], &s[k], damping);
        }
    }
}
#endif
#if defined(RE4DC_CLOTH_SPRING) && RE4DC_CLOTH_SPRING
#if RE4DC_CLOTH_SPRING == 2
#undef calcSpeed
#endif
// One spring seen from point (px, py, pz): v = n - p, len = |v|; past the rest length `gap` the force
// v * (k (len - gap) / len) is added to the speed (ax, ay, az) and returned in *f. 2 = force, 1 = none.
// The same operations and operands as the source's PSVECSubtract / PSVECMag / PSVECScale / PSVECAdd; the
// point and the speed sit in registers (the source re-read them after every store through s).
static inline __attribute__((always_inline)) int clothSpring(const Vec* n, f32 px, f32 py, f32 pz, f32 gap, f32 kp,
                                                             f32& ax, f32& ay, f32& az, Vec* f)
{
    Vec v;
    f32 len;
    v.x = n->x - px;
    v.y = n->y - py;
    v.z = n->z - pz;
    len = PSVECMag(&v);
    if (len > gap) {
        const f32 r = kp * (len - gap) / len;
        f->x = v.x * r;
        f->y = v.y * r;
        f->z = v.z * r;
        ax = f->x + ax;
        ay = f->y + ay;
        az = f->z + az;
        return 2;
    }
    return 1;
}
#if RE4DC_CLOTH_SPRING == 2
extern "C" void re4dc_log(const char* fmt, ...);
static Vec clothChkIn[2048];
static Vec clothChkNew[2048];
static u32 clothChkCalls, clothChkMis, clothChkBig;
#endif
void Cloth::calcSpeed(f32 damping)
{
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::ClothSpringFast, 1);
    re4dc::fa35::hit(re4dc::fa35::ClothPoints, unsigned(divH) * unsigned(divV));
#endif
#line 432
#if RE4DC_CLOTH_SPRING == 2
    const u32 npt = (u32) divH * divV;
    const int chk = npt <= 2048;
    if (chk) {
        __builtin_memcpy(clothChkIn, pSpd, npt * sizeof(Vec));
    } else {
        clothChkBig++;
    }
#endif
    const Vec* p = pVer;
    Vec* s = pSpd;
    const int w = divH;
    const int nv = divV;
    const f32 kp = K_PARAM;   // K / G / the gaps do not change during the step (s never aliases them)
    const f32 gp = G_PARAM;
    const f32 wg = Wgap;
    const f32 hg = Hgap;
    int i;
    int j;

    for (i = 0; i < nv; i++) {
        Vec rv;
        int rk = 0;   // the spring from the left neighbour: 0 not computed, 1 no force, 2 force in rv
        for (j = 0; j < w; j++) {
            Vec f;
            if (i == 0 && j != 0 && j != w - 1) {
                rk = 0;
                clothDnOk[j] = 0;
                continue;
            }
            const int k = j + i * w;
            const f32 px = p[k].x;
            const f32 py = p[k].y;
            const f32 pz = p[k].z;
            f32 ax = s[k].x;
            f32 ay = s[k].y;
            f32 az = s[k].z;
            if (j != 0) {
                if (rk == 2) {
                    ax = ax - rv.x;
                    ay = ay - rv.y;
                    az = az - rv.z;
                } else if (rk == 0) {
                    clothSpring(&p[k - 1], px, py, pz, wg, kp, ax, ay, az, &f);
                }
            }
            rk = 0;
            if (j != w - 1) {
                rk = clothSpring(&p[k + 1], px, py, pz, wg, kp, ax, ay, az, &rv);
            }
            if (i != 0) {
                const int dk = clothDnOk[j];
                if (dk == 2) {
                    ax = ax - clothDn[j].x;
                    ay = ay - clothDn[j].y;
                    az = az - clothDn[j].z;
                } else if (dk == 0) {
                    clothSpring(&p[k - w], px, py, pz, hg, kp, ax, ay, az, &f);
                }
            }
            clothDnOk[j] = 0;
            if (i != nv - 1) {
                clothDnOk[j] = clothSpring(&p[k + w], px, py, pz, hg, kp, ax, ay, az, &clothDn[j]);
            }
            ay -= gp;
            s[k].x = ax * damping;
            s[k].y = ay * damping;
            s[k].z = az * damping;
        }
    }
#if RE4DC_CLOTH_SPRING == 2
    if (chk) {
        __builtin_memcpy(clothChkNew, pSpd, npt * sizeof(Vec));
        __builtin_memcpy(pSpd, clothChkIn, npt * sizeof(Vec));
        calcSpeedSrc(damping);
        if (__builtin_memcmp(clothChkNew, pSpd, npt * sizeof(Vec)) != 0) {
            clothChkMis++;
        }
        if (++clothChkCalls % 256 == 0) {
            re4dc_log("CSPR calls=%u mismatch=%u big=%u\n", clothChkCalls, clothChkMis, clothChkBig);
        }
    }
#endif
}
#endif

// A free cloth work in *out; 0 when all 8 are used.
int PullCloth(Cloth** out)
{
    Cloth* c = ClothWk;
    int i;

    *out = 0;
    for (i = 0; i < 8; i++) {
        if ((c->be_flag & 1) == 0) {
            *out = c;
            return 1;
        }
        c++;
    }
    return 0;
}

// Integrates the speeds into the vertex positions (time step T_PARAM), skipping the pinned top
// row(s).
void Cloth::move()
{
#if (defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11) || (defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11)
    re4dc::cloth_pub11::grid_write(cloth11_slot(this));
#endif
    Vec v;
    int i;
    int j;

    for (i = 0; i < divV; i++) {
        if (x70 == 0) {
            if (i == 0) {
                continue;
            }
        } else if (i >= 0 && i <= 3) {
            continue;
        }
        for (j = 0; j < divH; j++) {
            int k = j + divH * i;
            PSVECScale(&pSpd[k], &v, T_PARAM);
            PSVECAdd(&pVer[k], &v, &pVer[k]);
        }
    }
}

// Recomputes the vertex normals from the neighbouring points for lighting.
void Cloth::calcNormal()
{
    Vec a;
    Vec b;
    Vec c;
    int i;
    int j;
    int k;

    for (i = 0; i < divV; i++) {
        for (j = 0; j < divH; j++) {
            u8 w = divH;
            k = j + i * w;
            if (i == divV - 1) {
                pNor[k] = pNor[k - w];
            } else if (j == w - 1) {
                pNor[k] = pNor[k - 1];
            } else {
                PSVECSubtract(&pVer[k + 1], &pVer[k], &a);
                PSVECSubtract(&pVer[k + w], &pVer[k], &b);
                PSVECCrossProduct(&b, &a, &c);
#line 622 "D:/Bio4/Prog/cloth.cpp"
                VECNormalize(&c, &pNor[k]);
            }
        }
    }
}

// Pushes grid point (x, y): adds `power` to its z speed and half to y (bullets / wind).
void Cloth::disturbance(f32 power, u32 x, u32 y)
{
    u32 idx = x + divH * y;

    pSpd[idx].z += power;
    pSpd[idx].y += power * 0.5f;
}

#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
static void ClothDraw_log_room()
{
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(!re4dc::cloth_material11::open_slots || !re4dc_cloth_frame_open11())return;
#endif
    int i;
    {   // CLOTH_NATIVE: one line per room with live cloth sheets (proof of coverage)
        static u16 s_room = 0xFFFF;
        int n = 0;
        for (i = 0; i < 8; i++) {
            n += ClothWk[i].m_pMem != 0;
        }
        if (n && s_room != G_ROOM_ID) {
            s_room = G_ROOM_ID;
            re4dc_log("cloth native: room=%03x sheets=%d grid0=%ux%u tex=%08x\n", (unsigned) G_ROOM_ID, n,
                      (unsigned) ClothWk[0].divH, (unsigned) ClothWk[0].divV,
                      ClothWk[0].tex
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
                      && re4dc::cloth_material11::admitted(0)
#endif
                      ? (unsigned) ((const u32*) ClothWk[0].tex)[0] : 0U);
            for (i = 0; i < 8; i++) {
                if (ClothWk[i].m_pMem) {
                    re4dc_log("cloth native: sheet %d be=%02x grid=%ux%u center=%d,%d,%d\n", i,
                              (unsigned) ClothWk[i].be_flag, (unsigned) ClothWk[i].divH,
                              (unsigned) ClothWk[i].divV, (int) ClothWk[i].center.x, (int) ClothWk[i].center.y,
                              (int) ClothWk[i].center.z);
                }
            }
        }
    }
}
#endif

// Draw registration: queues clothTrans in OT 13 for every cloth flagged drawn (be_flag 0x20).
void ClothDraw()
{
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(!re4dc_cloth_frame_open11())return;
#endif
    Cloth* c = ClothWk;
    int i;

#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
    ClothDraw_log_room();
#endif
    for (i = 0; i < 8; i++, c++) {
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
        if(!re4dc::cloth_material11::admitted(unsigned(i)))continue;
#endif
        if (c->be_flag & 0x20) {
            AddOtDirect(0xD, c, (void (*)()) clothTrans, 0, 0x1000, 0, 0.0f);
        }
    }
}

#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
// CLOTH_NATIVE on a drawn coarse image (trans.cpp): no world OT runs, so every drawn sheet is queued now.
void ClothDrawNow()
{
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(!re4dc_cloth_frame_open11())return;
#endif
    ClothDraw_log_room();
    for (int i = 0; i < 8; i++) {
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
        if(!re4dc::cloth_material11::admitted(unsigned(i)))continue;
#endif
        if (ClothWk[i].be_flag & 0x20) {
            clothTrans(&ClothWk[i]);
        }
    }
}
#endif

// Draws the cloth: a temporary cModel picks up the room lights (commonClothLightSet), then one
// two-sided textured triangle strip per row with the vertex normals.
void clothTrans(Cloth* pCL)
{
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(!re4dc::cloth_material11::admitted(cloth11_slot(pCL)) || !re4dc_cloth_frame_open11())return;
#endif
    Mtx texMtx;
    GXTexObj* tex = pCL->tex;
    void* tex2 = pCL->pTobjA;
    GXTlutObj* tlut = pCL->tlut;
#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
    if (!re4dc_cloth_visible(pCL)) {
        return;   // CLOTH_NATIVE: a sheet wholly off the view (draw only)
    }
#endif
    int nStages;
    int i;
    int j;
    int k;
    int t;
    f32 r;

    CameraSetProjection(1);
    PSMTXIdentity(texMtx);
    GXSetCullMode(0);
    GXSetZMode(1, 3, 1);
    GXSetNumChans(1);
    GXSetTevColorIn(0, 0xF, 8, 0xA, 0xF);
    GXSetTevColorOp(0, 0, 0, 2, 1, 0);
    GXSetTevAlphaIn(0, 7, 4, 5, 7);
    GXSetTevAlphaOp(0, 0, 0, 2, 1, 0);
    GXSetTevOrder(0, 0, 0, 4);
    cModel model;
    u8 modelPad[0x320 - sizeof(cModel)];  // see the cModel size note above
    PSMTXIdentity(model.mat);
    {
        static const Vec p0 = {0.0f, 0.0f, 0.0f};
        static const Vec p1 = {10000.0f, 10000.0f, 10000.0f};
        model.LightInfo.init2(1, 0, &p0, &p1, 0x10);
    }
    model.pos = pCL->center;
    LightMgr.setClothN(&model, 8);
    if (model.LightInfo.Size.x > model.LightInfo.Size.y) {
        r = model.LightInfo.Size.x;
    } else {
        r = model.LightInfo.Size.y;
    }
#if defined(RE4DC_CLOTH_LIGHT_ABI_FIX) && RE4DC_CLOTH_LIGHT_ABI_FIX && !defined(__PPC__)
    commonClothLightSet(model.LightInfo.pLight, 8, &model.pos, r);
#else
    commonClothLightSet(model.LightInfo.pLight, 8, model.pos, r);
#endif
    GXSetChanMatColor(4, pCL->color);
#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    const auto native_result=re4dc_cloth_native(pCL, model.LightInfo.pLight, &model.pos, r);
    if (!native_result.fallback_allowed()) {
#else
    if (re4dc_cloth_native(pCL, model.LightInfo.pLight, &model.pos, r)) {
#endif
        return;
    }
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    re4dc::fa29::hit(re4dc::fa29::ClothLegacy);
#endif
#line 750
    GXSetNumTexGens(1);
    GXLoadTexObj(tex, 0);
    if (tlut != 0) {
        GXLoadTlut(tlut, 0);
    }
    GXLoadTexMtxImm(texMtx, 0x1E, 1);
    GXSetTexCoordGen2(0, 1, 4, 0x1E, 0, 0x7D);
    if (pCL->x74 == 0) {
        GXSetBlendMode(1, 4, 5, 0);
    } else {
        GXSetBlendMode(1, 1, 1, 0);
        GXSetZMode(1, 3, 0);
    }
    GXSetAlphaCompare(4, 4, 1, 4, 0xFF);
    nStages = 1;
    if (tex2 != 0) {
        nStages = 2;
        GXSetZCompLoc(0);
        GXSetBlendMode(1, 4, 5, 0);
        GXLoadTexObj((GXTexObj*) tex2, 1);
        GXSetTevOrder(1, 0, 1, 4);
        GXSetTevOp(1, 0);
    }
    GXSetNumTevStages(nStages);
    {
        Mtx scale;
        Mtx tmp;
        PSMTXScale(scale, pCL->Scale, pCL->Scale, pCL->Scale);
        PSMTXConcat(pCL->mat, scale, tmp);
        PSMTXConcat(pG->Cam.v_mat, tmp, scale);
        GXLoadPosMtxImm(scale, 0);
        PSMTXInverse(scale, tmp);
        PSMTXTranspose(tmp, scale);
        GXLoadNrmMtxImm(scale, 0);
    }
    GXSetCurrentMtx(0);
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(10, 1);
    GXSetVtxDesc(13, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 10, 0, 4, 0);
    GXSetVtxAttrFmt(0, 13, 1, 4, 0);
    for (i = 0; i < pCL->divV - 1; i++) {
        GXBegin(0x98, 0, pCL->divH * 2);
        for (j = 0; j < pCL->divH * 2; j++) {
            Vec* pp;
            Vec* pn;
            if (j & 1) {
                k = pCL->divH * (i + 1) + j / 2;
                t = 1;
            } else {
                k = i * pCL->divH + j / 2;
                t = 0;
            }
            pp = &pCL->pVer[k];
            pn = &pCL->pNor[k];
            GXPosition3f32(pp->x, pp->y, pp->z);
            GXNormal3f32(pn->x, pn->y, pn->z);
            GXTexCoord2f32((f32) (j / 2) / (f32) (pCL->divH - 1), (f32) (i + t) / (f32) (pCL->divV - 1));
        }
    }
}
