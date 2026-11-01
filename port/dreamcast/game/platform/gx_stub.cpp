#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "include/fallback_audit29.h"
#endif
#line 1
// GX compatibility state for recovered source consumers. Common ID quads now
// connect directly to native_ui and the shared Package/storage/PVR mechanisms.
// Remaining GX primitives, 3D materials and effects are still unbound; accepting
// a GX call here is not evidence that its output has been rendered.
#include <string.h>
#include <cstdint>
#include <cmath>
#include "../../room/source_lighting.hpp"
#ifndef RE4DC_D349_RENDERER_STACK
#define RE4DC_D349_RENDERER_STACK 0
#endif

#include "re4dc_platform.h"
#include "native_ui.h"
#if (defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11) || (defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12)
#include "include/cloth_material11_sampler.hpp"
#endif
extern "C" void re4dc_model_finish_source_draws();
#if defined(RE4DC_RAIN_PS2) && RE4DC_RAIN_PS2
extern "C" void re4dc_rain_flush();
#endif
// D367 frontend30 COPY_LEAN (obj/frontend30.h; default off = previous image):
// the GX state getters/light objects copy aligned words instead of calling
// memcpy (a libcall at these sizes on SH-4; D367 LD ~0.9 ms/frame).
#ifndef RE4DC_COPY_LEAN
#define RE4DC_COPY_LEAN 0
#endif
#if RE4DC_COPY_LEAN
typedef std::uint32_t __attribute__((may_alias)) GxWord;
static inline void gx_words(void* to, const void* from, unsigned bytes)
{
    GxWord* d = (GxWord*) to;
    const GxWord* s = (const GxWord*) from;
    for (unsigned i = 0; i < bytes / 4; ++i) d[i] = s[i];
}
#define GX_COPY(d, s, n) gx_words((d), (s), (n))
#else
#define GX_COPY(d, s, n) memcpy((d), (s), (n))
#endif

typedef signed char s8;
typedef unsigned char u8;
typedef unsigned short u16;
typedef signed long s32;
typedef std::uint32_t u32;
typedef float f32;

struct GXColor { u8 r, g, b, a; };
struct GXColorS10 { short r, g, b, a; };
struct GXTexObj { u32 w[8]; };    // 0x20: w[0] = image, w[1] = width<<16|height, w[2] = format
struct GXTlutObj { u32 w[3]; };
struct GXLightObj { u32 w[16]; };

// The write-gather pipe the immediate-mode vertex macros write to
// (include/gx.h GXWGFifo->f32 = ...). On the GameCube it is the FIFO port at
// 0xCC008000; here it is memory, and the vertex data is discarded until the
// renderer captures it.
union WGPipe {
    u8 u8_; u16 u16_; u32 u32_; s8 s8_; short s16_; s32 s32_; f32 f32_;
};
extern "C" volatile WGPipe GXWGFifo[1] __attribute__((aligned(32)));
volatile WGPipe GXWGFifo[1] __attribute__((aligned(32)));

#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
// GC_CENSUS_TRIM (lane t2exact, ../gx_fast.h): the same state words, exported for the inline readers / writer.
#if (RE4DC_GXF_JITTER+0) != (RE4DC_RES_ALTERNATE+0)
#error GC_CENSUS_TRIM: RE4DC_GXF_JITTER must equal RE4DC_RES_ALTERNATE (census_trim.mk)
#endif
extern "C" { f32 re4dc_gxf_projection[7]; f32 re4dc_gxf_viewport[6] = {0, 0, 640, 480, 0, 1}; }
#define g_projection re4dc_gxf_projection
#define g_viewport re4dc_gxf_viewport
#else
static f32 g_projection[7];
static f32 g_viewport[6] = {0, 0, 640, 480, 0, 1};
#endif
static u32 g_stat_begin, g_stat_verts;
// Only the material alpha needed by the source model adapter. Not a TEV VM.
static unsigned g_model_alpha=255, g_model_alpha_source;

#if RE4DC_D349_RENDERER_STACK
static re4dc::render::SourceLighting g_lighting;
static void light_floats(GXLightObj* l,unsigned offset,float a,float b,float c){
    const float values[]={a,b,c};GX_COPY(l->w+offset,values,sizeof(values));
}
#endif
extern "C" {
void re4dc_gx_model_lighting(re4dc::render::SourceLighting* out){
#if RE4DC_D349_RENDERER_STACK
    *out=g_lighting;
#else
    *out={};
#endif
}
#if RE4DC_D349_RENDERER_STACK
const re4dc::render::SourceLighting* re4dc_gx_model_lighting_ref(void){return &g_lighting;}
#endif

void* GXInit(void* base, u32 size) { (void) size; re4dc_ui_init(); re4dc_log("GXInit: native ID UI; 3D remains unbound\n"); return base; }
void* GXSetCurrentGXThread(void) { return 0; }

u32 re4dc_gx_begin_count(void) { return g_stat_begin; }
u32 re4dc_gx_vertex_count(void) { return g_stat_verts; }

#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
void GXBegin(int type, int vtxfmt, u16 nverts) { re4dc::fa29::hit(re4dc::fa29::GxImmediate,nverts); (void) type; (void) vtxfmt; g_stat_begin++; g_stat_verts += nverts; }
#else
#line 101
void GXBegin(int type, int vtxfmt, u16 nverts) { (void) type; (void) vtxfmt; g_stat_begin++; g_stat_verts += nverts; }
#endif
#line 102
void GXBeginDisplayList(void* list, u32 size) { (void) list; (void) size; }
u32 GXEndDisplayList(void) { return 0; }
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
void GXCallDisplayList(void* list, u32 nbytes) { re4dc::fa29::hit(re4dc::fa29::GxDisplayList,nbytes); (void) list; (void) nbytes; }
#else
#line 104
void GXCallDisplayList(void* list, u32 nbytes) { (void) list; (void) nbytes; }
#endif
#line 105
void GXClearBoundingBox(void) {}
void GXClearVtxDesc(void) {}
void GXSetVtxDesc(int attr, int type) { (void) attr; (void) type; }
void GXSetVtxAttrFmt(int fmt, int attr, int cnt, int type, u8 frac) { (void) fmt; (void) attr; (void) cnt; (void) type; (void) frac; }
void GXSetArray(int attr, void* base, u8 stride) { (void) attr; (void) base; (void) stride; }
void GXInvalidateVtxCache(void) {}
void GXInvalidateTexAll(void) {}

void GXCopyDisp(void* dest, u8 clear) { (void) dest; (void) clear; }
void GXCopyTex(void* dest, u8 clear) { (void) dest; (void) clear; }
void GXSetTexCopySrc(u16 l, u16 t, u16 w, u16 h) { (void) l; (void) t; (void) w; (void) h; }
void GXSetTexCopyDst(u16 w, u16 h, int fmt, u8 mip) { (void) w; (void) h; (void) fmt; (void) mip; }
void GXSetDispCopySrc(u16 l, u16 t, u16 w, u16 h) { (void) l; (void) t; (void) w; (void) h; }
void GXSetDispCopyDst(u16 w, u16 h) { (void) w; (void) h; }
u32 GXSetDispCopyYScale(f32 s) { (void) s; return 480; }
void GXSetDispCopyGamma(int g) { (void) g; }
void GXSetCopyFilter(u8 aa, const u8 pat[12][2], u8 vf, const u8 vfilter[7]) { (void) aa; (void) pat; (void) vf; (void) vfilter; }
void GXSetCopyClear(GXColor c, u32 z) { (void) c; (void) z; }
void GXSetPixelFmt(int pix, int z) { (void) pix; (void) z; }
void GXSetDither(u8 d) { (void) d; }
void GXDrawDone(void) {}
void GXPixModeSync(void) {}
void GXSetDrawSync(u16 token) {
#if RE4DC_D349_RENDERER_STACK
    // Render() emits this before returning to SetPrimBuffPtr / next Trans().
    // Consume every borrowed pose now, never at the later Render_swap.
    if(token==0xADEB)re4dc_model_finish_source_draws();
#if defined(RE4DC_RAIN_PS2) && RE4DC_RAIN_PS2
    if(token==0xADEB)re4dc_rain_flush();   // filter06.cpp RAIN_PS2: the rain lines, straight into the open TR list
#endif
#endif
    (void)token;
}
void* GXSetDrawSyncCallback(void* cb) { (void) cb; return 0; }
void GXPeekZ(u16 x, u16 y, u32* z) { (void) x; (void) y; *z = 0xFFFFFF; }

void GXSetViewport(f32 l, f32 t, f32 w, f32 h, f32 n, f32 f) { g_viewport[0] = l; g_viewport[1] = t; g_viewport[2] = w; g_viewport[3] = h; g_viewport[4] = n; g_viewport[5] = f; }
void GXSetViewportJitter(f32 l, f32 t, f32 w, f32 h, f32 n, f32 f, u32 field) { (void) field; GXSetViewport(l, t, w, h, n, f); }
#if defined(RE4DC_RES_ALTERNATE) && RE4DC_RES_ALTERNATE
// RENDER_OPTION alternating lines (res_mode.cpp): odd frames sample half a render line lower (the GameCube's
// GXSetViewportJitter idea); re4dc_res_vjitter is the half line as a fraction of the screen height.
extern "C" float re4dc_res_vjitter;
void GXGetViewportv(f32* vp)
{
    GX_COPY(vp, g_viewport, sizeof(g_viewport));
    vp[1] += re4dc_res_vjitter * g_viewport[3];  // re4dc_res_vjitter: render lines / screen lines (no divide here)
}
#else
void GXGetViewportv(f32* vp) { GX_COPY(vp, g_viewport, sizeof(g_viewport)); }
#endif
void GXSetScissor(u32 l, u32 t, u32 w, u32 h) { (void) l; (void) t; (void) w; (void) h; }
void GXSetProjection(const f32 mtx[4][4], int type)
{
    // The SDK keeps [type, m00, m02|m03, m11, m12|m13, m22, m23].
    g_projection[0] = (f32) type;
    g_projection[1] = mtx[0][0];
    g_projection[3] = mtx[1][1];
    g_projection[5] = mtx[2][2];
    g_projection[6] = mtx[2][3];
    if (type == 0) {  // perspective
        g_projection[2] = mtx[0][2];
        g_projection[4] = mtx[1][2];
    } else {
        g_projection[2] = mtx[0][3];
        g_projection[4] = mtx[1][3];
    }
}
void GXGetProjectionv(f32* p) { GX_COPY(p, g_projection, sizeof(g_projection)); }

// The SDK's GXProject: model-view transform, then the compact projection and
// viewport, as the game's screen-position helpers expect (HUD, targets, text).
void GXProject(f32 x, f32 y, f32 z, const f32 mtx[3][4], const f32* pm, const f32* vp, f32* sx, f32* sy, f32* sz)
{
    f32 vx = mtx[0][0] * x + mtx[0][1] * y + mtx[0][2] * z + mtx[0][3];
    f32 vy = mtx[1][0] * x + mtx[1][1] * y + mtx[1][2] * z + mtx[1][3];
    f32 vz = mtx[2][0] * x + mtx[2][1] * y + mtx[2][2] * z + mtx[2][3];
    f32 px, py, pz, pw;
    if (pm[0] == 0.0f) {
        px = pm[1] * vx + pm[2] * vz;
        py = pm[3] * vy + pm[4] * vz;
        pz = pm[5] * vz + pm[6];
        pw = -vz;
        if (pw == 0.0f) pw = 1e-6f;
        pw = 1.0f / pw;
    } else {
        px = pm[1] * vx + pm[2];
        py = pm[3] * vy + pm[4];
        pz = pm[5] * vz + pm[6];
        pw = 1.0f;
    }
    *sx = vp[2] / 2.0f * px * pw + vp[0] + vp[2] / 2.0f;
    *sy = -(vp[3] / 2.0f) * py * pw + vp[1] + vp[3] / 2.0f;
    *sz = (vp[5] - vp[4]) * pz * pw + vp[5];
}

void GXLoadPosMtxImm(const f32 mtx[3][4], u32 id) { (void) mtx; (void) id; }
void GXLoadNrmMtxImm(const f32 mtx[3][4], u32 id) {
#if RE4DC_D349_RENDERER_STACK
    if(id==0)GX_COPY(g_lighting.normal_matrix,mtx,sizeof(g_lighting.normal_matrix));
#endif
    (void)mtx;(void)id;
}
void GXLoadTexMtxImm(const f32 mtx[][4], u32 id, int type) { (void) mtx; (void) id; (void) type; }
void GXSetCurrentMtx(u32 id) { (void) id; }

void GXSetNumChans(u8 n) { (void) n; }
void GXSetChanCtrl(int chan, u8 enable, int amb, int mat, u32 mask, int diff, int attn) {
    // GX_ALPHA0 / GX_COLOR0A0. RGB or channel one changes must not alter it.
    if(chan==2 || chan==4) g_model_alpha_source=enable || (mat!=0 && mat!=1)?2U:unsigned(mat);
#if RE4DC_D349_RENDERER_STACK
    if(chan==0 || chan==4){g_lighting.enable=enable;g_lighting.ambient_vertex=amb;
        g_lighting.material_vertex=mat;g_lighting.mask=mask;g_lighting.diffuse=diff;g_lighting.attenuation=attn;}
#endif
    (void) amb; (void) mask; (void) diff; (void) attn;
}
void GXSetChanAmbColor(int chan, GXColor c) {
#if RE4DC_D349_RENDERER_STACK
    if(chan==0 || chan==4)memcpy(g_lighting.ambient,&c,4);
#endif
    (void)chan;(void)c;
}
void GXSetChanMatColor(int chan, GXColor c) {
    if(chan==2 || chan==4)g_model_alpha=c.a;
#if RE4DC_D349_RENDERER_STACK
    if(chan==0 || chan==4)memcpy(g_lighting.material,&c,4);
#endif
}
unsigned re4dc_gx_model_alpha() { return g_model_alpha | (g_model_alpha_source<<8); }
void GXSetNumTexGens(u8 n) { (void) n; }
void GXSetTexCoordGen2(int dst, int func, int src, u32 mtx, u8 norm, u32 pt) { (void) dst; (void) func; (void) src; (void) mtx; (void) norm; (void) pt; }
void GXEnableTexOffsets(int coord, u8 line, u8 point) { (void) coord; (void) line; (void) point; }
void GXSetNumTevStages(u8 n) { (void) n; }
void GXSetTevOrder(int stage, int coord, int map, int color) { (void) stage; (void) coord; (void) map; (void) color; }
void GXSetTevOp(int id, int mode) { (void) id; (void) mode; }
void GXSetTevColorIn(int s, int a, int b, int c, int d) { (void) s; (void) a; (void) b; (void) c; (void) d; }
void GXSetTevAlphaIn(int s, int a, int b, int c, int d) { (void) s; (void) a; (void) b; (void) c; (void) d; }
void GXSetTevColorOp(int s, int op, int bias, int scale, u8 clamp, int out) {
#if RE4DC_D349_RENDERER_STACK
    const float scales[]={1,2,4,0.5f};
    if(out==0 && scale>=0 && scale<4)g_lighting.tev_scale=scales[scale];
#endif
    (void)s;(void)op;(void)bias;(void)clamp;
}
void GXSetTevAlphaOp(int s, int op, int bias, int scale, u8 clamp, int out) { (void) s; (void) op; (void) bias; (void) scale; (void) clamp; (void) out; }
void GXSetTevColor(int id, GXColor c) { (void) id; (void) c; }
void GXSetTevColorS10(int id, GXColorS10 c) { (void) id; (void) c; }
void GXSetTevKColor(int id, GXColor c) { (void) id; (void) c; }
void GXSetTevKColorSel(int s, int sel) { (void) s; (void) sel; }
void GXSetTevKAlphaSel(int s, int sel) { (void) s; (void) sel; }
void GXSetTevSwapMode(int s, int ras, int tex) { (void) s; (void) ras; (void) tex; }
void GXSetTevSwapModeTable(int t, int r, int g, int b, int a) { (void) t; (void) r; (void) g; (void) b; (void) a; }
void GXSetTevDirect(int s) { (void) s; }
void GXSetTevIndWarp(int s, int ind, u8 so, u8 rm, int m) { (void) s; (void) ind; (void) so; (void) rm; (void) m; }
void GXSetTevIndBumpXYZ(int s, int ind, int m) { (void) s; (void) ind; (void) m; }
void GXSetNumIndStages(u8 n) { (void) n; }
void GXSetIndTexOrder(int s, int coord, int map) { (void) s; (void) coord; (void) map; }
void GXSetIndTexMtx(int id, const f32 off[2][3], s8 exp) { (void) id; (void) off; (void) exp; }
void GXSetIndTexCoordScale(int s, int ss, int st) { (void) s; (void) ss; (void) st; }
void __GXSetIndirectMask(u32 mask) { (void) mask; }
void GXSetAlphaCompare(int c0, u8 r0, int op, int c1, u8 r1) { (void) c0; (void) r0; (void) op; (void) c1; (void) r1; }
void GXSetZMode(u8 en, int func, u8 upd) { (void) en; (void) func; (void) upd; }
void GXSetZCompLoc(u8 before) { (void) before; }
void GXSetBlendMode(int type, int src, int dst, int op) { (void) type; (void) src; (void) dst; (void) op; }
void GXSetColorUpdate(u8 e) { (void) e; }
void GXSetAlphaUpdate(u8 e) { (void) e; }
void GXSetDstAlpha(u8 e, u8 a) { (void) e; (void) a; }
void GXSetCullMode(int m) { (void) m; }
void GXSetLineWidth(u8 w, int ofs) { (void) w; (void) ofs; }
#if RE4DC_NATIVE_FOG
extern "C" void re4dc_fog_capture(int type, float start, float end, unsigned rgba);
// Native model headers take PVR table fog from this state (native_static.cpp).
void GXSetFog(int type, f32 s, f32 e, f32 n, f32 f, GXColor c) {
    (void) n; (void) f;
    re4dc_fog_capture(type, s, e, ((u32) c.r << 24) | ((u32) c.g << 16) | ((u32) c.b << 8) | c.a);
}
#else
void GXSetFog(int type, f32 s, f32 e, f32 n, f32 f, GXColor c) { (void) type; (void) s; (void) e; (void) n; (void) f; (void) c; }
#endif

void GXInitTexObj(GXTexObj* o, void* image, u16 w, u16 h, int fmt, int ws, int wt, u8 mip)
{
    memset(o, 0, sizeof(*o));
    o->w[0] = (u32) image; o->w[1] = ((u32) w << 16) | h; o->w[2] = (u32) fmt; o->w[3] = ((u32) ws << 8) | (u32) wt | ((u32) mip << 16);
#if (defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11) || (defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12)
    re4dc::cloth_material11::init_sampler(o->w,mip);
#endif
}
void GXInitTexObjCI(GXTexObj* o, void* image, u16 w, u16 h, int fmt, int ws, int wt, u8 mip, u32 tlut)
{
    GXInitTexObj(o, image, w, h, fmt, ws, wt, mip);
    o->w[4] = tlut;
}
#if (defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11) || (defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12)
void GXInitTexObjLOD(GXTexObj* o, int minf, int magf, f32 minl, f32 maxl, f32 bias, u8 bc, u8 edge, int aniso) {
    re4dc::cloth_material11::lod_sampler(o->w,minf,magf,minl,maxl,bias,bc,edge,aniso);
}
#else
void GXInitTexObjLOD(GXTexObj* o, int minf, int magf, f32 minl, f32 maxl, f32 bias, u8 bc, u8 edge, int aniso) { (void) o; (void) minf; (void) magf; (void) minl; (void) maxl; (void) bias; (void) bc; (void) edge; (void) aniso; }
#endif
void* GXGetTexObjData(GXTexObj* o) { return (void*) o->w[0]; }
void GXLoadTexObj(GXTexObj* o, int id) { (void) o; (void) id; }
void GXInitTlutObj(GXTlutObj* t, void* lut, int fmt, u16 n) { t->w[0] = (u32) lut; t->w[1] = (u32) fmt; t->w[2] = n; }
void GXLoadTlut(GXTlutObj* t, u32 name) { (void) t; (void) name; }
u32 GXGetTexBufferSize(u16 w, u16 h, u32 fmt, u8 mip, u8 maxlod)
{
    (void) mip; (void) maxlod;
    u32 bpp = (fmt == 6) ? 32 : (fmt == 0 || fmt == 8) ? 4 : (fmt == 1 || fmt == 2 || fmt == 9 || fmt == 14) ? 8 : 16;
    return ((u32) w * h * bpp + 7) / 8;
}

#if RE4DC_D349_RENDERER_STACK
void GXInitLightAttn(GXLightObj* l,f32 a0,f32 a1,f32 a2,f32 k0,f32 k1,f32 k2){
    light_floats(l,4,a0,a1,a2);light_floats(l,7,k0,k1,k2);
}
void GXInitLightAttnK(GXLightObj* l,f32 k0,f32 k1,f32 k2){light_floats(l,7,k0,k1,k2);}
void GXInitLightSpot(GXLightObj* l,f32 cutoff,int fn){
    if(cutoff<=0 || cutoff>90)fn=0;
    const float cr=std::cos(3.1415927f*cutoff/180.f);
    float a0=1,a1=0,a2=0,d;
    switch(fn){
    case 1:a0=-1000*cr;a1=1000;break;
    case 2:a1=1/(1-cr);a0=-cr*a1;break;
    case 3:a2=1/(1-cr);a0=0;a1=-cr*a2;break;
    case 4:d=1/((1-cr)*(1-cr));a0=cr*(cr-2)*d;a1=2*d;a2=-d;break;
    case 5:d=1/((1-cr)*(1-cr));a2=-4*d;a0=a2*cr;a1=4*(1+cr)*d;break;
    case 6:d=1/((1-cr)*(1-cr));a0=1-2*cr*cr*d;a1=4*cr*d;a2=-2*d;break;
    }
    light_floats(l,4,a0,a1,a2);
}
void GXInitLightDistAttn(GXLightObj* l,f32 d,f32 b,int fn){
    if(d<0 || b<=0 || b>=1)fn=0;
    float k1=0,k2=0;
    switch(fn){case 1:k1=(1-b)/(b*d);break;
    case 2:k1=0.5f*(1-b)/(b*d);k2=0.5f*(1-b)/(b*d*d);break;
    case 3:k2=(1-b)/(b*d*d);break;}
    light_floats(l,7,1,k1,k2);
}
void GXInitLightPos(GXLightObj* l,f32 x,f32 y,f32 z){light_floats(l,10,x,y,z);}
void GXInitLightDir(GXLightObj* l,f32 x,f32 y,f32 z){light_floats(l,13,-x,-y,-z);}
void GXInitLightColor(GXLightObj* l,GXColor c){l->w[3]=(u32(c.r)<<24)|(u32(c.g)<<16)|(u32(c.b)<<8)|c.a;}
void GXLoadLightObjImm(GXLightObj* l,u32 id){
    if(!id || (id&(id-1)) || id>128)return;
    unsigned slot=0;while((1U<<slot)!=id)++slot;
    auto& out=g_lighting.lights[slot];
    GX_COPY(out.a,l->w+4,12);GX_COPY(out.k,l->w+7,12);
    GX_COPY(out.position,l->w+10,12);GX_COPY(out.direction,l->w+13,12);
    for(unsigned i=0;i<4;++i)out.color[i]=l->w[3]>>(24-i*8);
}
#else
void GXInitLightAttn(GXLightObj* l, f32 a0, f32 a1, f32 a2, f32 k0, f32 k1, f32 k2) { (void) l; (void) a0; (void) a1; (void) a2; (void) k0; (void) k1; (void) k2; }
void GXInitLightAttnK(GXLightObj* l, f32 k0, f32 k1, f32 k2) { (void) l; (void) k0; (void) k1; (void) k2; }
void GXInitLightSpot(GXLightObj* l, f32 cutoff, int fn) { (void) l; (void) cutoff; (void) fn; }
void GXInitLightDistAttn(GXLightObj* l, f32 d, f32 b, int fn) { (void) l; (void) d; (void) b; (void) fn; }
void GXInitLightPos(GXLightObj* l, f32 x, f32 y, f32 z) { (void) l; (void) x; (void) y; (void) z; }
void GXInitLightDir(GXLightObj* l, f32 x, f32 y, f32 z) { (void) l; (void) x; (void) y; (void) z; }
void GXInitLightColor(GXLightObj* l, GXColor c) { (void) l; (void) c; }
void GXLoadLightObjImm(GXLightObj* l, u32 id) { (void) l; (void) id; }

#endif

void GXDrawTorus(f32 rc, u8 numc, u8 numt) { (void) rc; (void) numc; (void) numt; }

}  // extern "C"
