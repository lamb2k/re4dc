#if defined(RE4DC_HOUSE_ARENA27) && RE4DC_HOUSE_ARENA27
#include "house_arena27.h"
#include "trans.h"
#endif
// game/trans_ot: the draw ordering tables (OT) — 23 tables (OT_MAX) of depth-bucketed linked
// lists of OtData {func, data, kind}; each frame the draw code adds callbacks into a table (by
// camera depth for the world / model tables 17 / 13, or a fixed bucket with AddOtDirect) and the
// render pass runs the tables back to front (ExecOt), so translucent things sort by depth. The
// entries live in the per-frame prim buffer.
#include "types.h"
#include "vec.h"
#include "global.h"
#include "camera.h"
#include "view.h"
#include "geometry.h"
#include "gx.h"
#include "db_log.h"
#include "main_mem.h"
#include "trans_ot.h"
#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
#include "ps2_source_world.h"
#endif
#if defined(RE4DC_OT_MASK) && RE4DC_OT_MASK
#include "trans.h"
extern "C" {
u32 g_OtUsed;
u32 g_OtModels;
#if RE4DC_OT_MASK == 2
unsigned re4dc_otm_exec_skips, re4dc_otm_exec_mismatch;
void re4dc_log(const char* fmt, ...);
#endif
}
// Marks table w as holding an entry (and a model entry when func is ModelRender).
static inline void otMark(OtWork* w, void (*func)(void*))
{
    const u32 bit = 1u << (u32) (w - g_OtWork);
    g_OtUsed |= bit;
    if (func == (void (*)(void*)) ModelRender) {
        g_OtModels |= bit;
    }
}
#define OT_MARK(w, f) otMark((w), (void (*)(void*)) (f))
#else
#define OT_MARK(w, f)
#endif

extern "C" {
void* GetPrimBuff(int size);
}

// The original stores g_NowExecOtType through a reference: that keeps the following loads through the
// OtWork pointer below the store (a plain global store lets ProDG hoist them).
static inline void ISet(int& d, int v)
{
    d = v;
}

// Table `type`. As an inline accessor the constant index stays `addi 0x88` after the symbol load
// instead of folding into `g_OtWork+0x88`.
static inline OtWork* otWork(int type)
{
    return &g_OtWork[type];
}

// Depth of `pos` along the camera look vector.
static inline f32 OtDepth(Camera* cam, Vec* pos, Vec* look, Vec* d)
{
    CameraGetLookVecInverse(cam, look);
    d->x = pos->x - cam->param.pos.x;
    d->y = pos->y - cam->param.pos.y;
    d->z = pos->z - cam->param.pos.z;
    return PSVECDotProduct(look, d);
}

static int Ot_max_tbl[OT_MAX] = {
    10, 10, 10, 10, 10, 10, 10, 10, 3, 4, 3, 6, 8, 0x80, 3, 3, 5, 0x400, 10, 10, 3, 3, 1,
};

OtWork g_OtWork[OT_MAX];
OtMirrorWork g_OtMirrirWk[2];
f32 OT_MUL = 0.05f;
asm(".section .sdata; .balign 8");
int g_NowExecOtType;

// Boot: allocates each table's bucket array (Ot_max_tbl sizes) and clears them.
void InitOt()
{
    OtWork* w = g_OtWork;
    u32 i;

    for (i = 0; i < OT_MAX; i++, w++) {
        w->max = Ot_max_tbl[i];
#line 53 "D:/Bio4/Prog/trans_ot.cpp"
        w->list = (OtData*) MEM_ALLOC(w->max * sizeof(OtData), 1, 13);
        w->prev_kind = 0;
    }
    ClearOt();
}

// Frame start: every table's buckets emptied (and the mirror works).
void ClearOt()
{
    OtWork* w = g_OtWork;
    u32 i;

    for (i = 0; i < OT_MAX; i++, w++) {
        clearOtWork(w);
    }
    CrearOtMirrorWork();
}

// Chains the buckets of one table back-to-front with no entries.
void clearOtWork(OtWork* w)
{
    OtData* p;
    OtData* q;

    w->prev_kind = 0;
#if defined(RE4DC_OT_MASK) && RE4DC_OT_MASK
    g_OtUsed &= ~(1u << (u32) (w - g_OtWork));
    g_OtModels &= ~(1u << (u32) (w - g_OtWork));
#endif
    ISet(g_NowExecOtType, OT_MAX);
    p = &w->list[w->max - 1];
    do {
        q = p;
        p--;
        q->data = 0;
        q->next = p;
    } while (q > w->list);
    q->next = 0;
}

// A new entry from the frame's prim buffer; 0 when it is full.
OtData* MakeOtData(void* data)
{
    OtPrim* p = (OtPrim*) GetPrimBuff(sizeof(OtPrim));

    if ((u32) p < RE4_MEM_LO || (u32) p > RE4_MEM_HI) {
        return 0;
    }
    p->data = data;
    return &p->ot;
}

// Adds a callback into the world table (17) at the bucket of `pos`'s camera depth x 0.05
// (bucket 0 when zlimit is 0); dropped when the depth is below `zlimit`. Returns the bucket,
// 0xFFFF when not added.
int AddOtWorldPos(void* data, void (*func)(void*), Vec* pos, u16 kind, f32 zlimit)
{
    Camera* cam = &pG->Cam;
    OtWork* w = otWork(17);
    OtData* p;
    OtData* q;
    Vec look;
    Vec d;
    int idx;
    u32 no;
    f32 z;

    p = MakeOtData(data);
    if (p == 0) {
        pLog->warn(2, 0, "AddOtWorldPos():PrimBuffer OVERFLOW!!");
        return 0xFFFF;
    }
    idx = 0xFFFF;
    if (zlimit == 0.0f) {
        z = 0.0f;
    } else {
        CameraGetLookVecInverse(cam, &look);
        d.x = pos->x - cam->param.pos.x;
        d.y = pos->y - cam->param.pos.y;
        d.z = pos->z - cam->param.pos.z;
        z = PSVECDotProduct(&look, &d);
    }
    if (z >= zlimit) {
        no = (u16) (z * OT_MUL);
        if (no >= w->max) {
            no = w->max - 1;
        }
        q = &w->list[no];
        idx = no;
        p->data = data;
        p->func = func;
        p->next = q->next;
        p->kind = kind;
        q->next = p;
        OT_MARK(w, func);
    }
    return idx;
}

// AddOtWorldPos for a sphere: frustum-culled by (pos, radius); the depth of the sphere's near side
// must reach `zlimit`.
int AddOtWorldPosRadius(void* data, void (*func)(void*), Vec* pos, f32 radius, u16 kind, f32 zlimit)
{
    OtWork* w = otWork(17);
    Camera* cam;
    OtData* p;
    OtData* q;
    Vec look;
    Vec d;
    GeoSphere sph;
    GeoHexahedron* h;
    u32 no;
    f32 z;

    p = MakeOtData(data);
    if (p == 0) {
        pLog->warn(2, 0, "AddOtWorldPos():PrimBuffer OVERFLOW!!");
        return 0xFFFF;
    }
    cam = &pG->Cam;
    h = (GeoHexahedron*) CameraViewFrustumPtr(cam);
    sph.pos = *pos;
    sph.r = radius;
    if (!collision_sphere_hexahedron(&sph, h)) {
        return 0xFFFF;
    }
    CameraGetLookVecInverse(cam, &look);
    d.x = pos->x - cam->param.pos.x;
    d.y = pos->y - cam->param.pos.y;
    d.z = pos->z - cam->param.pos.z;
    z = PSVECDotProduct(&look, &d);
    if (z + radius < zlimit) {
        if (zlimit != 0.0f) {
            return 0xFFFF;
        }
        z = zlimit;
    }
    no = (u16) (z * OT_MUL);
    if (no >= w->max) {
        no = w->max - 1;
    }
    q = &w->list[no];
    p->data = data;
    p->func = func;
    p->next = q->next;
    p->kind = kind;
    q->next = p;
    OT_MARK(w, func);
    return no;
}

// The same for the model table (13), with buckets of 100 depth units (0x80 buckets).
int AddOtModelPosRadius(void* data, void (*func)(void*), Vec* pos, f32 radius, u16 kind, f32 zlimit)
{
    OtWork* w = otWork(13);
    Camera* cam;
    OtData* p;
    OtData* q;
    Vec look;
    Vec d;
    GeoSphere sph;
    GeoHexahedron* h;
    u32 no;
    f32 z;

    p = MakeOtData(data);
    if (p == 0) {
        pLog->warn(2, 0, "AddOtWorldPos():PrimBuffer OVERFLOW!!");
        return 0xFFFF;
    }
    cam = &pG->Cam;
    h = (GeoHexahedron*) CameraViewFrustumPtr(cam);
    sph.pos = *pos;
    sph.r = radius;
    if (!collision_sphere_hexahedron(&sph, h)) {
        return 0xFFFF;
    }
    CameraGetLookVecInverse(cam, &look);
    d.x = pos->x - cam->param.pos.x;
    d.y = pos->y - cam->param.pos.y;
    d.z = pos->z - cam->param.pos.z;
    z = PSVECDotProduct(&look, &d);
    if (z + radius < zlimit) {
        if (zlimit != 0.0f) {
            return 0xFFFF;
        }
        z = zlimit;
    }
    no = (u16) (z * 0.01f);
    if (no >= w->max) {
        no = w->max - 1;
    }
    q = &w->list[no];
    p->data = data;
    p->func = func;
    p->next = q->next;
    p->kind = kind;
    q->next = p;
    OT_MARK(w, func);
    return no;
}

// Adds a callback into table `ot` at bucket `no` (clamped), optionally frustum-culled by
// (pos, radius). Returns the bucket, 0xFFFF when culled or out of buffer.
extern "C" int AddOtDirect(int ot, void* data, void (*func)(), u32 no, u16 flag, Vec* pos, f32 radius)
{
    OtWork* w;
    OtData* p;
    OtData* q;
    GeoSphere sph;
    GeoHexahedron* h;

    if (radius != 0.0f && pos != 0) {
        h = (GeoHexahedron*) CameraViewFrustumPtr(&pG->Cam);
        sph.pos = *pos;
        sph.r = radius;
        if (!collision_sphere_hexahedron(&sph, h)) {
            return 0xFFFF;
        }
    }
    w = otWork(ot);
    p = MakeOtData(data);
    if (p == 0) {
        pLog->warn(2, 0, "AddOtDirect():PrimBuffer OVERFLOW!!");
        return 0xFFFF;
    }
    if (no >= w->max) {
        no = (u16) (w->max - 1);
    }
    q = &w->list[no];
    p->data = data;
    p->func = (void (*)(void*)) func;
    p->next = q->next;
    p->kind = flag;
    q->next = p;
    OT_MARK(w, func);
    return no;
}

#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
// OT_WALK_CHECK (lane ch4found16 2026-10-16, debug arm, default 0): before each entry's call, the walk checks the
// node (4-byte aligned, in main RAM) and its func (2-byte aligned, in main RAM). The first bad node is reported with
// the entry before it (whose `next` points at it: its owner's func / data / kind and the words around it) and the
// table's walk stops there instead of faulting (r229: ExecOt node 0x8ce3xxxx odd, callback 0x23708b0d).
static int re4dc_otwc_reports;
static bool re4dc_otwc_ok(const void* a, u32 align)
{
    const u32 v = (u32) a;
    return (v & (align - 1)) == 0 && v >= RE4_MEM_LO && v <= RE4_MEM_HI;
}
struct Re4dcPrimTag { u32 addr, size, frame, caller; };
extern "C" { extern Re4dcPrimTag re4dc_prim_tags[2048]; extern u32 re4dc_prim_tag_n; }
// The newest tags (up to 6) whose slot covers `a`, newest first, and the newest buffer flip before each.
static void re4dc_otwc_tags(const char* what, u32 a)
{
    int shown = 0;
    const u32 n = re4dc_prim_tag_n;
    for (u32 k = 0; k < 2048 && k < n && shown < 6; k++) {
        const Re4dcPrimTag& t = re4dc_prim_tags[(n - 1 - k) & 2047];
        if (t.size && a >= t.addr && a < t.addr + t.size) {
            re4dc_log("OTWC   %s %08x in slot %08x+%u frame %u caller %08x (tag -%u)\n", what, (unsigned) a,
                      (unsigned) t.addr, (unsigned) t.size, (unsigned) t.frame, (unsigned) t.caller, (unsigned) k);
            ++shown;
        }
    }
    for (u32 k = 0; k < 2048 && k < n; k++) {
        const Re4dcPrimTag& t = re4dc_prim_tags[(n - 1 - k) & 2047];
        if (!t.size) {
            re4dc_log("OTWC   last flip: start %08x frame %u nPrim %u buf %u (tag -%u), now frame %u\n", (unsigned) t.addr,
                      (unsigned) t.frame, (unsigned) (t.caller & 0x7FFFFFFF), (unsigned) (t.caller >> 31), (unsigned) k,
                      (unsigned) pG->Frame_cnt);
            break;
        }
    }
    if (!shown) re4dc_log("OTWC   %s %08x: no GetPrimBuff slot in the last 2048 tags\n", what, (unsigned) a);
}
static OtData* re4dc_otwc_cur;
static int re4dc_otwc_cur_type = -1, re4dc_otwc_cur_n;
static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p);
// fault.cpp (OT_WALK_CHECK): a fault names the ExecOt entry being called, if any, and the slots that cover it.
extern "C" void re4dc_otwc_fault()
{
    if (g_NowExecOtType == OT_MAX || re4dc_otwc_cur_type < 0) {
        re4dc_log("OTWC fault: outside ExecOt (last table %d)\n", re4dc_otwc_cur_type);
        return;
    }
    OtData* p = re4dc_otwc_cur;
    re4dc_log("OTWC fault in ExecOt: table %d entry %d node %08x\n", re4dc_otwc_cur_type, re4dc_otwc_cur_n,
              (unsigned) (u32) p);
    if (re4dc_otwc_ok(p, 4)) {
        re4dc_log("OTWC   node data %08x func %08x next %08x kind %04x\n", (unsigned) (u32) p->data,
                  (unsigned) (u32) p->func, (unsigned) (u32) p->next, (unsigned) p->kind);
        const u32* q = (const u32*) p - 8;
        for (int i = 0; i < 24; i += 8) {
            re4dc_log("OTWC   %08x: %08x %08x %08x %08x %08x %08x %08x %08x\n", (unsigned) (u32) (q + i), q[i],
                      q[i + 1], q[i + 2], q[i + 3], q[i + 4], q[i + 5], q[i + 6], q[i + 7]);
        }
        re4dc_otwc_tags("node", (u32) p);
        if (re4dc_otwc_ok((const void*) p->func, 4)) re4dc_otwc_tags("func", (u32) p->func);
    }
}
static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p)
{
    if (re4dc_otwc_reports++ >= 6) return;
    re4dc_log("OTWC bad node: table %d entry %d frame %u room %03x node %08x list %08x..%08x max %d\n", type, count,
              (unsigned) pG->Frame_cnt, (unsigned) pG->room_id, (unsigned) (u32) p, (unsigned) (u32) w->list,
              (unsigned) (u32) (w->list + w->max), (int) w->max);
    if (re4dc_otwc_ok(p, 4)) {
        re4dc_otwc_tags("node", (u32) p);
        re4dc_log("OTWC   node data %08x func %08x next %08x kind %04x\n", (unsigned) (u32) p->data,
                  (unsigned) (u32) p->func, (unsigned) (u32) p->next, (unsigned) p->kind);
    }
    if (prev && re4dc_otwc_ok(prev, 4)) {
        const bool head = prev >= w->list && prev < w->list + w->max;
        re4dc_log("OTWC   prev %08x (%s %d) data %08x func %08x kind %04x\n", (unsigned) (u32) prev,
                  head ? "bucket" : "entry", head ? (int) (prev - w->list) : -1, (unsigned) (u32) prev->data,
                  (unsigned) (u32) prev->func, (unsigned) prev->kind);
        re4dc_otwc_tags("prev", (u32) prev);
        const u32* q = (const u32*) prev - 8;
        if (re4dc_otwc_ok(q, 4)) {
            for (int i = 0; i < 24; i += 8) {
                re4dc_log("OTWC   %08x: %08x %08x %08x %08x %08x %08x %08x %08x\n", (unsigned) (u32) (q + i), q[i],
                          q[i + 1], q[i + 2], q[i + 3], q[i + 4], q[i + 5], q[i + 6], q[i + 7]);
            }
        }
    }
}
#endif

// Runs table `type` from the farthest bucket to the nearest, calling each entry's func(data)
// (g_NowExecOtType / prev_kind tell the callbacks their context); alpha compare reset afterwards.
// Returns the number of entries drawn.
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
extern "C" void re4dc_otwc_pad_check(u32 where);   // trans.cpp
#endif
#if defined(RE4DC_OT_PROF) && RE4DC_OT_PROF
// OT_PROF=1 (lane cast16 2026-10-17; diagnostic, default 0): per OT callback (function + data) CPU time and PVR bytes
// (native_ui stream_model_bytes delta) over 120-UI-frame windows; the top 24 by time are logged as OTP lines. A data
// pointer in main RAM also logs its cModel id / type / parts bytes (0x100..0x102; meaningless for non-models).
extern "C" unsigned re4dc_stream_model_bytes_now();
extern "C" unsigned long long re4dc_otp_now_us();
extern "C" unsigned re4dc_ui_frame();
extern "C" void re4dc_log(const char*, ...);
namespace {
struct OtpRow { void* f; void* d; unsigned t, n, us, bytes; };
OtpRow otp_rows[128];
unsigned otp_n, otp_over, otp_last, otp_frames_t0;
void otp_add(void* f, void* d, unsigned t, unsigned us, unsigned bytes)
{
    for (unsigned k = 0; k < otp_n; ++k) {
        OtpRow& r = otp_rows[k];
        if (r.f == f && r.d == d && r.t == t) { r.n++; r.us += us; r.bytes += bytes; return; }
    }
    if (otp_n == 128) { otp_over++; return; }
    OtpRow& r = otp_rows[otp_n++]; r.f = f; r.d = d; r.t = t; r.n = 1; r.us = us; r.bytes = bytes;
}
void otp_window()
{
    const unsigned fr = re4dc_ui_frame();
    if (!otp_last) { otp_last = fr; return; }
    if (fr - otp_last < 120) return;
    unsigned tot_us = 0, tot_b = 0;
    for (unsigned k = 0; k < otp_n; ++k) { tot_us += otp_rows[k].us; tot_b += otp_rows[k].bytes; }
    re4dc_log("OTP f=%u frames=%u rows=%u over=%u total_us=%u total_bytes=%u\n", fr, fr - otp_last, otp_n, otp_over, tot_us, tot_b);
    for (unsigned i = 0; i < 24 && i < otp_n; ++i) {
        unsigned best = i;
        for (unsigned k = i + 1; k < otp_n; ++k) if (otp_rows[k].us > otp_rows[best].us) best = k;
        OtpRow tmp = otp_rows[i]; otp_rows[i] = otp_rows[best]; otp_rows[best] = tmp;
        const OtpRow& r = otp_rows[i];
        const unsigned a = (unsigned) r.d;
        unsigned id = 0xFFFF, ty = 0xFFFF, parts = 0xFFFF;
        if (a >= 0x8C010000u && a < 0x8CFFFE00u) { const u8* m = (const u8*) r.d; id = m[0x100]; ty = m[0x101]; parts = m[0x102]; }
        re4dc_log("OTP  fn=%p data=%p ot=%u calls=%u us=%u bytes=%u id=%x ty=%x parts=%u\n", r.f, r.d, r.t, r.n, r.us, r.bytes, id, ty, parts);
    }
    otp_n = 0; otp_over = 0; otp_last = fr;
}
}
#endif
int ExecOt(int type)
{
#if defined(RE4DC_OT_PROF) && RE4DC_OT_PROF
    if (type == 0) otp_window();
#endif
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
    re4dc_otwc_pad_check(0xE0000000u | (u32) type);   // checkpoint "ExecOt(type)"
#endif
    OtWork* w = &g_OtWork[type];
    OtData* p;
    int count = 0;

    g_NowExecOtType = type;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_callback_continue()){
        w->prev_kind=0;GXSetAlphaCompare(7,0,1,7,0);g_NowExecOtType=OT_MAX;return 0;
    }
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(!re4dc_r11f_callback_continue()) {
        w->prev_kind=0;GXSetAlphaCompare(7,0,1,7,0);g_NowExecOtType=OT_MAX;return 0;
    }
#endif
#if defined(RE4DC_OT_MASK) && RE4DC_OT_MASK
    if (!(g_OtUsed & (1u << type))) {
        // No entry since the clear: the walk below would call nothing.
#if RE4DC_OT_MASK == 2
        re4dc_otm_exec_skips++;
        for (OtData* e = &w->list[w->max - 1]; e; e = e->next) {
            if (e->data) {
                if (re4dc_otm_exec_mismatch++ < 4) {
                    re4dc_log("OTM exec mismatch: table %d has an entry\n", type);
                }
                break;
            }
        }
#else
        w->prev_kind = 0;
        GXSetAlphaCompare(7, 0, 1, 7, 0);
        g_NowExecOtType = OT_MAX;
        return 0;
#endif
    }
#endif
    p = &w->list[w->max - 1];
    w->prev_kind = 0;
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    OtData* otwc_prev = 0;
#endif
    if (p) {
        for (; p; p = p->next) {
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
            if (!re4dc_otwc_ok(p, 4) || (p->data && !re4dc_otwc_ok((const void*) p->func, 2))) {
                re4dc_otwc_report(type, count, w, otwc_prev, p);
                break;
            }
            otwc_prev = p;
            re4dc_otwc_cur = p; re4dc_otwc_cur_type = type; re4dc_otwc_cur_n = count;
#endif
            if (p->data) {
                count++;
#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
                re4dc_source_world_callback_begin(unsigned(type),p,p->func,p->data,p->kind);
#endif
#if defined(RE4DC_OT_PROF) && RE4DC_OT_PROF
                const unsigned long long otp_t0 = re4dc_otp_now_us(); const unsigned otp_b0 = re4dc_stream_model_bytes_now();
#endif
#if defined(RE4DC_HOUSE_ARENA27) && RE4DC_HOUSE_ARENA27
                // Keep the OT walk, observer scopes and source-owner cleanup.
                // Only the actual Leon model callback may emit scene content.
                if(!re4dc_house_arena27_active() ||
                   ((type==0xBU || type==0xDU || type==0x11U) &&
                    p->func==(void (*)(void*))ModelRender && re4dc_house_arena27_model(p->data)))
#endif
                p->func(p->data);
#if defined(RE4DC_OT_PROF) && RE4DC_OT_PROF
                otp_add((void*) p->func, p->data, (unsigned) type, (unsigned) (re4dc_otp_now_us() - otp_t0), re4dc_stream_model_bytes_now() - otp_b0);
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
                re4dc_source_world_callback_end();
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
                if(!re4dc_source_world_callback_continue())break;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
                if(!re4dc_r11f_callback_continue())break;
#endif
                w->prev_kind = p->kind;
            }
        }
    }
    GXSetAlphaCompare(7, 0, 1, 7, 0);
    g_NowExecOtType = OT_MAX;
    return count;
}

// The `kind` of the entry drawn just before the current one in the running table (0 outside ExecOt).
u16 OtGetPrevKind()
{
    if (g_NowExecOtType == OT_MAX) {
        return 0;
    }
    return g_OtWork[g_NowExecOtType].prev_kind;
}

// Clears the two mirror-pass works.
void CrearOtMirrorWork()
{
    int i;

    for (i = 0; i < 2; i++) {
        memclr_asm(&g_OtMirrirWk[i], sizeof(OtMirrorWork));
    }
}

// Dead-stripped by the original linker (STRIP_UNUSED); its message string remains.
static void SetOtMirrorWork(u32 no)
{
    if (no >= 2) {
        pLog->err(0, 0, "SetOtMirrorWork() : invalid no[%d] MAX=%d", no, 2);
    }
}

// Empties bucket `no` of table `type` (entries dropped, not drawn).
void DeleteOtData(u32 type, u32 no)
{
    OtWork* w;
    OtData* q;

    if (type >= OT_MAX) {
        pLog->err(0, 0, "DeleteOtData() : invalid ot_type[%d] MAX=%d", type, OT_MAX);
        return;
    }
    w = &g_OtWork[type];
    if (no >= w->max) {
        pLog->err(0, 0, "DeleteOtData() : invalid no[%d] MAX=%d", no, w->max);
        return;
    }
    q = &w->list[no];
    q->next = q->next->next;
}
