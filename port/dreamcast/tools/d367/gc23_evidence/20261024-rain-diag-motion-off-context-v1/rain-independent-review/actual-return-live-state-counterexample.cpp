
#include <cstdint>
#include <cstring>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
using u32=uint32_t;using u8=uint8_t;using s8=int8_t;using f32=float;using u16=uint16_t;
#define RE4DC_RAIN_PS2 1
#define RE4DC_RAIN_DC 1
#define RE4DC_RAIN_DC_N 320
#define RAIN_DC_DRAWN 320
using Mtx=float[3][4];using Mtx44=float[4][4];
struct Vec{float x,y,z;};struct Model{};using cModel=Model;struct EspSeqData{};struct EspSeqOpt{};
struct Camera {struct {Vec at,pos;}param;Vec up;Mtx v_mat{};Mtx44 ProjMat{};};
struct Global{u32 room_id=0x10c,Frame_cnt=1,Stop_flg=0,Status_flg[4]{};u8 Rno0=3;Camera Cam;};Global global;Global* pG=&global;
struct {float width=512,height=448;} Screen;bool pause_filter=false;unsigned moved=0,initialized=0,queued=0,sent=0;
void Filter06Render();void Filter06Trans();void Filter06RoomInit();int Render_checkBlurPermission();
struct cParticle06{Vec m_Pos{},m_Spd{};u8 m_Alpha=0;void init(u32){++initialized;}void move(){++moved;}};
cParticle06 particles[2048];
bool alloc_fail=false;
#define MEM_ALLOC(a,b,c) (alloc_fail ? nullptr : (void*)particles)
struct Logger{template<class...T>void err(T...){}}logger;Logger* pLog=&logger;
unsigned random_calls=0;void(*random_action)()=nullptr;float fRand1_1(){++random_calls;if(random_action){auto f=random_action;random_action=nullptr;f();}return 0.0f;}
void memclr_asm(void* p,unsigned n){std::memset(p,0,n);}
struct Filter06Work{cParticle06*p;u32 num;Vec spd;u8 col[4],cur[4];float colF[3],alphaF,rate,spread,rangeLR,rangeUp,rangeDepth,scale;u8 alphaMin;};
Filter06Work flt06{};Vec cam_vec_LR{};
void PSVECSubtract(const Vec*,const Vec*,Vec*){}void PSVECCrossProduct(const Vec*,const Vec*,Vec*){}void VECNormalize(Vec*,Vec*){}
void PSMTXCopy(const Mtx&a,Mtx&b){std::memcpy(b,a,sizeof(Mtx));}
void GXGetViewportv(float* v){for(int i=0;i<6;i++)v[i]=0;v[2]=512;v[3]=448;}
void(*callback)()=nullptr;bool accept_ot=true;
void AddOtDirect(int,void*,void(*f)(),int,int,int,float){if(accept_ot){callback=f;++queued;}}
void Filter00Trans(){}void Filter01Trans(){}void Filter02Trans(){}void Filter03Trans(){}void Filter04Trans(){}void Filter05Trans(){}
void Filter07Trans(){}void Filter08Trans(){}void Filter0aTrans(){}void Filter0bTrans(){}int Filter09GetbUse(){return pause_filter;}
const u32 kRainPs2Lines=100;int s_rain_pending=0;Mtx s_rain_view{};Mtx44 s_rain_proj{};float s_rain_viewport[6]{};
struct RainDcDrop{float x,y,d,len,w,a;};struct Re4dcRainStreak{float x,y0,y1,z,w;u32 tail,head;};
RainDcDrop s_raindc[320];Re4dcRainStreak s_raindc_out[320];
u32 s_raindc_seed=0x2545F491U,s_raindc_frame=0,s_raindc_pending=0,s_raindc_ready=0,s_raindc_alpha=0,s_raindc_frames=0,s_raindc_sent=0;float s_raindc_area=0;
unsigned report_override=0xffffffffU;void(*native_action)()=nullptr;
unsigned re4dc_rain_dc_streaks(const Re4dcRainStreak*,unsigned n){unsigned result=report_override==0xffffffffU?n:report_override;if(native_action){auto f=native_action;native_action=nullptr;f();}sent+=result;return result;}
void dcache_wback_range(uintptr_t,unsigned);
#if RE4DC_RAIN_R10C_DC
u32 s_raindc_queued_room=0,s_raindc_queued_frame=0;
static_assert(sizeof(s_raindc_queued_room)+sizeof(s_raindc_queued_frame)==8,"ticket must remain8B");
#endif
template<class...T>void re4dc_log(T...){}
struct EspGenWork{u8 Kind=1,Espgen_id=0x44,Id=1,Work8[4]{10,0,0,0};float Size_base_x=1;u8 Tex_id=0,Blend_type=0,Col_start_r=170,Col_start_g=170,Col_start_b=170,Col_start_a=80;float Col_d_a=.1f;Vec Speed{},R_speed{};};
struct Espgen44Work{u8 type=0;};struct EspgenWork{struct{u8 owner=1;}info;u8 flag=1,id=0x44;Espgen44Work storage;void* work=&storage;};
template<class...T>void Filter05SetParamF(T...){}template<class...T>void Filter05SetParamM(T...){}

#define RE4DC_D349_RENDERER_STACK 1
unsigned drains=0;void re4dc_model_finish_source_draws(){++drains;}
void re4dc_rain_flush();


static int Filter06Ps2Rain()
{
    return pG->room_id == 0x11B && flt06.num == 1600 && flt06.col[0] == 170 && flt06.col[1] == 170 &&
           flt06.col[2] == 170 && flt06.col[3] == 60;
}
#if RE4DC_RAIN_R10C_DC || RE4DC_RAIN_R10C_DIAG
static int Filter06R10cRain()
{
    return pG->room_id == 0x10C && flt06.p != 0 && flt06.num == 1100 &&
           flt06.col[0] == 170 && flt06.col[1] == 170 && flt06.col[2] == 170 && flt06.col[3] == 80 &&
           flt06.rate == 1.0f && flt06.scale == 1.0f && flt06.spd.x == 21.0f &&
           flt06.spd.y == -250.0f && flt06.spd.z == 0.0f && flt06.alphaMin == 0;
}
#endif
#if RE4DC_RAIN_R10C_DC
static void RainDcR10cCancel()
{
    if (s_raindc_queued_room == 0x10C) {
        s_raindc_pending = 0;
        s_raindc_queued_room = 0;
        s_raindc_queued_frame = 0;
    }
}
#endif
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
// Private observation only. No archive-owner, TA acknowledgement or present proof.
#if !defined(RE4DC_GAME) || defined(__PPC__)
#error RAIN_R10C_DIAG requires the native Dreamcast game
#endif
struct RainDiagRecord {
    u32 seq, abi_flags, setter_generation, callback_generation;
    u32 controller, record, head, observed_owner;
    u32 setter_frame, callback_frame, queue_frame, event_frame;
    u32 rooms, event_reason, state_flags, particle_count;
    u32 alpha_ids, native_requested, native_accepted, accepted_total;
    u16 counts[24];
};
extern "C" {
volatile RainDiagRecord re4dc_rain_r10c_diag __attribute__((aligned(32)));
}
static_assert(sizeof(RainDiagRecord) == 128, "rain diagnostic payload");
static_assert(__builtin_offsetof(RainDiagRecord, counts) == 80, "rain diagnostic counters");
enum {
    RD_FEATURE = 1, RD_CAUSAL = 2, RD_SIGNATURE = 4, RD_PENDING = 8,
    RD_WOULD = 16, RD_STOP = 32, RD_INDOOR = 64, RD_BLUR_KNOWN = 128,
    RD_BLUR_OK = 256, RD_SAMPLE = 8192, RD_QUEUE_KEY = 16384,
    RD_FAULT = 0x80000000U, RD_LAST = 0xfffffffeU,
    RD_SET = 1, RD_BIND = 2, RD_ROOM = 3, RD_TRANS = 4, RD_CALLBACK = 5,
    RD_QUEUE = 6, RD_CONSUME = 7, RD_RETURN = 8, RD_JOIN_LOST = 9,
    RD_CANCEL = 10, RD_DESTRUCT = 11, RD_ALLOC = 12, RD_REJECT = 13,
    RD_STALE = 1, RD_PROFILE = 2, RD_ALPHA = 4, RD_INSIDE = 8,
    RD_BLUR = 16, RD_WIDTH = 32, RD_HEIGHT = 64, RD_PAUSE = 128,
    RD_ZERO = 256
};
enum {
    RDC_SET, RDC_BOUND, RDC_DESTRUCT, RDC_ROOM, RDC_ALLOC, RDC_TRANS,
    RDC_ZERO, RDC_INDOOR, RDC_STOP, RDC_CALLBACK, RDC_CANDIDATE,
    RDC_PROFILE, RDC_ALPHA, RDC_QUEUE, RDC_CANCEL_SET, RDC_CANCEL_ROOM,
    RDC_CANCEL_CALLBACK, RDC_STALE, RDC_STATE, RDC_CONSUMED,
    RDC_STOP_FLUSH, RDC_RETURN_ZERO, RDC_RETURN_POSITIVE, RDC_BIND_REJECT
};
static volatile RainDiagRecord* RainDiag()
{
#if defined(RE4DC_RAIN_DIAG_HOST_TEST)
    extern volatile RainDiagRecord* re4dc_rain_diag_host_p2();
    return re4dc_rain_diag_host_p2();
#else
    return (volatile RainDiagRecord*) ((uintptr_t) &re4dc_rain_r10c_diag | 0xa0000000U);
#endif
}
static void RainDiagBarrier() { __asm__ volatile("" ::: "memory"); }
static int RainDiagOpen(u32 event, u32 reason)
{
    volatile RainDiagRecord* d = RainDiag();
    if (d->abi_flags != 1 || (d->seq & 1) || d->seq >= RD_LAST) return 0;
    if (d->seq == RD_LAST - 2) {
        ++d->seq; RainDiagBarrier(); d->abi_flags |= RD_FAULT;
        RainDiagBarrier(); ++d->seq; return 0;
    }
    ++d->seq; RainDiagBarrier();
    d->state_flags &= ~(RD_SAMPLE | RD_BLUR_KNOWN | RD_BLUR_OK);
    d->event_reason = event | (reason << 16);
    return 1;
}
static void RainDiagCount(u32 counter)
{
    volatile RainDiagRecord* d = RainDiag();
    if (d->counts[counter] >= 0xfffe) {
        d->counts[counter] = 0xffff; d->abi_flags |= RD_FAULT;
    } else ++d->counts[counter];
}
static void RainDiagSnapshot()
{
    volatile RainDiagRecord* d = RainDiag();
    d->event_frame = pG->Frame_cnt;
    d->rooms = ((d->state_flags & RD_QUEUE_KEY) ? d->rooms & 0xffff0000U : 0xffff0000U) |
               (pG->room_id & 0xffff);
    d->particle_count = flt06.num;
    d->alpha_ids = (d->alpha_ids & 0xffff0000U) | flt06.cur[3] | ((u32) flt06.col[3] << 8);
    d->state_flags &= ~(RD_FEATURE | RD_SIGNATURE | RD_PENDING | RD_WOULD | RD_STOP | RD_INDOOR);
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    d->state_flags |= RD_FEATURE;
    if (s_raindc_pending && s_raindc_queued_room == 0x10c) d->state_flags |= RD_PENDING;
#endif
    if (Filter06R10cRain()) d->state_flags |= RD_SIGNATURE;
    if (!(d->state_flags & RD_FEATURE) && (d->state_flags & RD_SIGNATURE) && flt06.cur[3]) d->state_flags |= RD_WOULD;
    if (pG->Stop_flg & 0x08000000) d->state_flags |= RD_STOP;
    if (pG->Status_flg[1] & 0x02000000) d->state_flags |= RD_INDOOR;
}
static void RainDiagClose()
{
    RainDiagSnapshot();
    if (RainDiag()->abi_flags != 1) RainDiag()->state_flags &= ~RD_SAMPLE;
    RainDiagBarrier(); ++RainDiag()->seq;
}
static void RainDiagClearCause()
{
    volatile RainDiagRecord* d = RainDiag();
    d->state_flags &= ~(RD_CAUSAL | RD_QUEUE_KEY | RD_SAMPLE);
    d->controller = d->record = d->head = d->callback_generation = 0;
    d->observed_owner = 0xffffffffU;
    d->setter_frame = d->callback_frame = d->queue_frame = 0;
    d->alpha_ids &= 0xffff;
}
static void RainDiagForget()
{
    RainDiagClearCause();
    volatile RainDiagRecord* d = RainDiag();
    if (d->setter_generation >= 0xfffffffeU) {
        d->setter_generation = 0xffffffffU; d->abi_flags |= RD_FAULT;
    } else ++d->setter_generation;
}
static void RainDiagBoot()
{
    // Only Filter06Init calls this: systemRestartInit -> FilterInit, before source updates.
    // Four isolated BSS lines: cold dirty P1 zeros become physical; warm P1 stays clean.
    dcache_wback_range((uintptr_t) &re4dc_rain_r10c_diag, sizeof(re4dc_rain_r10c_diag));
    volatile RainDiagRecord* d = RainDiag();
    volatile u32* words = (volatile u32*) d;
    u32 any = 0;
    for (u32 i = 0; i < 32; ++i) any |= words[i];
    if (any) return; // Includes ABI0/nonzero-sequence warm and every faulted record. Never thaw.
    // Closed writers never zero this object. All-zero after BSS coherence is initial boot only.
    d->seq = 1; RainDiagBarrier(); d->abi_flags = 1;
    d->observed_owner = 0xffffffffU; d->rooms = 0xffffffffU;
    RainDiagBarrier(); d->seq = 2;
}
static void RainDiagInvalidate(u32 event, u32 counter, u32 cancel_counter, u32 reason)
{
    if (!RainDiagOpen(event, reason)) return;
    RainDiagCount(counter);
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    if (s_raindc_pending && s_raindc_queued_room == 0x10c) RainDiagCount(cancel_counter);
#endif
    RainDiagForget(); RainDiagClose();
}
extern "C" u32 re4dc_rain_diag_generation()
{
    volatile RainDiagRecord* d = RainDiag();
    return d->abi_flags == 1 && !(d->seq & 1) && d->seq < RD_LAST ? d->setter_generation : 0xffffffffU;
}
extern "C" void re4dc_rain_diag_bind44(u32 before, const void* controller, const void* record,
                                       const void* head, u32 owner, u32 valid, u32 ids)
{
    if (!RainDiagOpen(RD_BIND, 0)) return;
    volatile RainDiagRecord* d = RainDiag();
    if (valid && controller && record && head && before < 0xfffffffeU &&
        d->setter_generation == before + 1 && flt06.p && flt06.num) {
        d->controller = (u32) (uintptr_t) controller;
        d->record = (u32) (uintptr_t) record;
        d->head = (u32) (uintptr_t) head;
        d->observed_owner = owner <= 0xd0 ? owner : 0xffffffffU;
        d->setter_frame = pG->Frame_cnt;
        d->alpha_ids = (ids << 16) | (d->alpha_ids & 0xffff);
        d->state_flags |= RD_CAUSAL;
        RainDiagCount(RDC_BOUND);
    } else {
        RainDiagClearCause(); RainDiagCount(RDC_BIND_REJECT);
    }
    RainDiagClose();
}
extern "C" void re4dc_rain_diag_destruct44(const void* controller)
{
    if (!RainDiagOpen(RD_DESTRUCT, 0)) return;
    volatile RainDiagRecord* d = RainDiag();
    d->state_flags &= ~(RD_CAUSAL | RD_QUEUE_KEY);
    d->controller = (u32) (uintptr_t) controller; d->record = d->head = 0;
    d->observed_owner = 0xffffffffU;
    RainDiagCount(RDC_DESTRUCT); RainDiagClose();
}
static void RainDiagEvent(u32 event, u32 counter, u32 reason)
{
    if (!RainDiagOpen(event, reason)) return;
    RainDiagCount(counter); RainDiagClose();
}
static void RainDiagBlur(int allowed)
{
    if (!RainDiagOpen(RD_TRANS, allowed ? 0 : RD_BLUR)) return;
    RainDiag()->state_flags |= RD_BLUR_KNOWN;
    if (allowed) RainDiag()->state_flags |= RD_BLUR_OK;
    else RainDiag()->state_flags &= ~RD_BLUR_OK;
    RainDiagClose();
}
static void RainDiagCallback()
{
    if (!RainDiagOpen(RD_CALLBACK, 0)) return;
    volatile RainDiagRecord* d = RainDiag();
    d->state_flags &= ~RD_QUEUE_KEY;
    d->queue_frame = 0;
    d->callback_generation = d->setter_generation;
    d->callback_frame = pG->Frame_cnt;
    RainDiagCount(RDC_CALLBACK);
    if (!Filter06R10cRain()) RainDiagCount(RDC_PROFILE);
    else if (!flt06.cur[3]) RainDiagCount(RDC_ALPHA);
    else RainDiagCount(RDC_CANDIDATE);
    RainDiagClose();
}
static void RainDiagQueue()
{
    if (!RainDiagOpen(RD_QUEUE, 0)) return;
    RainDiag()->state_flags |= RD_QUEUE_KEY;
    RainDiag()->queue_frame = pG->Frame_cnt;
    RainDiag()->rooms = (0x10cU << 16) | (pG->room_id & 0xffff);
    RainDiagCount(RDC_QUEUE); RainDiagClose();
}
static int RainDiagCheck(u32 reason, int rejected)
{
    if (rejected && RainDiagOpen(RD_REJECT, reason)) {
        RainDiagCount(reason == RD_STALE ? RDC_STALE : RDC_STATE); RainDiagClose();
    }
    return rejected;
}
static void RainDiagCancelCallback()
{
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    if (s_raindc_pending && s_raindc_queued_room == 0x10c)
        RainDiagEvent(RD_CANCEL, RDC_CANCEL_CALLBACK, 0);
#endif
}
struct RainDiagNativeKey { u32 seq, generation, frame, room, queue_frame, queue_room, requested, reported; };
static_assert(sizeof(RainDiagNativeKey) == 32, "rain diagnostic planned scalar locals");
static void RainDiagConsume(RainDiagNativeKey* key, u32 queue_room, u32 queue_frame)
{
    key->seq = RD_LAST; key->generation = key->frame = key->room = 0;
    key->queue_room = queue_room; key->queue_frame = queue_frame;
    key->requested = key->reported = 0;
    if (!RainDiagOpen(RD_CONSUME, 0)) return;
    RainDiagCount(RDC_CONSUMED);
    if (queue_room == 0x10c && (pG->Stop_flg & 0x08000000)) RainDiagCount(RDC_STOP_FLUSH);
    RainDiagClose();
    key->seq = RainDiag()->seq; key->generation = RainDiag()->setter_generation;
    key->frame = pG->Frame_cnt; key->room = pG->room_id;
}
static void RainDiagReturned(const RainDiagNativeKey* key)
{
    volatile RainDiagRecord* d = RainDiag();
    if (d->abi_flags != 1 || (d->seq & 1) || d->seq >= RD_LAST) return;
    // Sequence witnesses every already-published identity/state field; never copy a 128B record.
    if (d->seq == key->seq && key->generation != 0 && d->setter_generation == key->generation &&
        d->callback_generation == key->generation && d->callback_frame == key->frame &&
        d->queue_frame == key->queue_frame && key->queue_frame == key->frame &&
        d->event_frame == key->frame && pG->Frame_cnt == key->frame &&
        key->queue_room == 0x10c && key->room == 0x10c && pG->room_id == key->room &&
        d->rooms == ((key->queue_room << 16) | key->room) &&
        (d->state_flags & (RD_FEATURE | RD_QUEUE_KEY)) == (RD_FEATURE | RD_QUEUE_KEY) &&
        key->reported <= key->requested) {
        if (!RainDiagOpen(RD_RETURN, 0)) return;
        d->native_requested = key->requested; d->native_accepted = key->reported;
        d->state_flags |= RD_SAMPLE;
    } else {
        if (!RainDiagOpen(RD_JOIN_LOST, 0)) return;
        d->native_requested = d->native_accepted = 0;
        RainDiagCount(RDC_BIND_REJECT);
    }
    // Native API-reported counts only: submit_pvr does not forward pvr_prim acknowledgement.
    if (key->reported >= 0xffffffffU - d->accepted_total) {
        d->accepted_total = 0xffffffffU; d->abi_flags |= RD_FAULT;
    } else d->accepted_total += key->reported;
    RainDiagCount(key->reported ? RDC_RETURN_POSITIVE : RDC_RETURN_ZERO);
    RainDiagClose();
}
#endif

static f32 RainDcUnit()
{
    u32 x = s_raindc_seed;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    s_raindc_seed = x;
    return (f32) (x >> 8) * (1.0f / 16777216.0f);
}
static void RainDcSpawn(RainDcDrop* p, int top)
{
    const f32 u = RainDcUnit();
    p->d = 700.0f + 5300.0f * u;                    // view depth, mm
    p->len = 40000.0f / p->d;                       // 57 px near .. 12 px far (the PS2 sheet's streaks: 30-60 px)
    if (p->len < 12.0f) {
        p->len = 12.0f;
    }
    p->w = p->d < 1500.0f ? 1.5f : 1.0f;
    p->a = 110.0f - 60.0f * u;                      // near streaks brighter
    p->x = RainDcUnit() * 640.0f;
    p->y = top ? -p->len - RainDcUnit() * 60.0f : RainDcUnit() * (480.0f + p->len) - p->len;
}
static void RainDcFlush()
{
    if (!s_raindc_pending) {
        return;
    }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    const int r10c = s_raindc_queued_room == 0x10C;
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    if (r10c && (RainDiagCheck(RD_STALE, s_raindc_queued_frame != pG->Frame_cnt) ||
                 RainDiagCheck(RD_PROFILE, !Filter06R10cRain()) || RainDiagCheck(RD_ALPHA, flt06.cur[3] == 0) ||
                 RainDiagCheck(RD_INSIDE, (pG->Status_flg[1] & 0x02000000) != 0) ||
                 RainDiagCheck(RD_BLUR, !Render_checkBlurPermission()) ||
                 RainDiagCheck(RD_WIDTH, Screen.width != 512.0f) ||
                 RainDiagCheck(RD_HEIGHT, Screen.height != 448.0f) || RainDiagCheck(RD_PAUSE, Filter09GetbUse()))) {
        RainDcR10cCancel();
        if (RainDiagOpen(RD_CANCEL, RainDiag()->event_reason >> 16)) {
            RainDiag()->state_flags &= ~RD_QUEUE_KEY; RainDiag()->queue_frame = 0; RainDiagClose();
        }
        return;
    }
#else
    if (r10c && (s_raindc_queued_frame != pG->Frame_cnt || !Filter06R10cRain() || flt06.cur[3] == 0 ||
                 (pG->Status_flg[1] & 0x02000000) || !Render_checkBlurPermission() ||
                 Screen.width != 512.0f || Screen.height != 448.0f || Filter09GetbUse())) {
        RainDcR10cCancel();
        return;
    }
#endif
#endif
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagNativeKey diag_key;
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    diag_key.queue_room = s_raindc_queued_room; diag_key.queue_frame = s_raindc_queued_frame;
#else
    diag_key.queue_room = diag_key.queue_frame = 0;
#endif
#endif
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    s_raindc_queued_room = 0;
    s_raindc_queued_frame = 0;
#endif
    s_raindc_pending = 0;
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagConsume(&diag_key, diag_key.queue_room, diag_key.queue_frame);
#endif
    u32 now = pG->Frame_cnt, dt = now - s_raindc_frame;
    s_raindc_frame = now;
    if (!s_raindc_ready) {
        for (u32 i = 0; i < RE4DC_RAIN_DC_N; ++i) {
            RainDcSpawn(&s_raindc[i], 0);
        }
        s_raindc_ready = 1;
        dt = 0;
    }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    if (r10c && (pG->Stop_flg & 0x08000000)) {
        dt = 0; // source Stop freezes motion/alpha but still draws
    }
#endif
    if (dt > 4) {
        dt = 4;
    }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    const f32 fade = r10c ? (f32) (s_raindc_alpha > 80 ? 80 : s_raindc_alpha) * (1.0f / 80.0f) :
                           (f32) (s_raindc_alpha > 60 ? 60 : s_raindc_alpha) * (1.0f / 60.0f);
#else
    const f32 fade = (f32) (s_raindc_alpha > 60 ? 60 : s_raindc_alpha) * (1.0f / 60.0f);
#endif
    u32 n = 0;
    f32 area = 0.0f;
    for (u32 i = 0; i < RE4DC_RAIN_DC_N; ++i) {
        RainDcDrop* p = &s_raindc[i];
        p->y += p->len * 1.1f * (f32) dt;          // about 50 px a frame near, as the PS2 sheet's scroll
        if (p->y > 480.0f) {
            RainDcSpawn(p, 1);
        }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
        // Experimental sheet-informed profile (r10c 210/120 versus night 180/100), not pixel equivalence.
        const u32 a = r10c ? (u32) (p->a * fade * 1.2f) : (u32) (p->a * fade);
#else
        const u32 a = (u32) (p->a * fade);
#endif
        if (a == 0 || i >= (u32) RAIN_DC_DRAWN) {
            continue;
        }
        Re4dcRainStreak* s = &s_raindc_out[n++];
        s->x = p->x;
        s->y0 = p->y;
        s->y1 = p->y + p->len;
        s->z = 1.0f / p->d;
        s->w = p->w;
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
        const u32 rgb = r10c ? 0xD2D2D2U : 0xB4B4B4U;
        s->tail = ((a >> 2) << 24) | rgb;
        s->head = (a << 24) | rgb;
#else
        s->tail = ((a >> 2) << 24) | 0xB4B4B4U;     // PS2 sheet colour 180
        s->head = (a << 24) | 0xB4B4B4U;
#endif
        const f32 t = s->y0 > 0.0f ? s->y0 : 0.0f, b = s->y1 < 480.0f ? s->y1 : 480.0f;
        if (b > t) {
            area += (b - t) * s->w;                     // screen area submitted (before depth rejection)
        }
    }
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    diag_key.requested = n;
    diag_key.reported = re4dc_rain_dc_streaks(s_raindc_out, n);
    s_raindc_sent += diag_key.reported;
    RainDiagReturned(&diag_key);
#else
    s_raindc_sent += re4dc_rain_dc_streaks(s_raindc_out, n);
#endif
    s_raindc_area += area;
    if (++s_raindc_frames % 120 == 1) {
        re4dc_log("rain dc: frame=%u room=%x streaks=%u sent=%u alpha=%u area_px=%u mean_screens_x1e4=%u\n",
                  (unsigned) pG->Frame_cnt, (unsigned) pG->room_id, (unsigned) n, (unsigned) s_raindc_sent,
                  (unsigned) s_raindc_alpha, (unsigned) area,
                  (unsigned) (s_raindc_area / (f32) s_raindc_frames * (10000.0f / 307200.0f)));
    }
}
void Filter06Init()
{
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagBoot();
#endif
    Filter06RoomInit();
}
void Filter06RoomInit()
{
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagInvalidate(RD_ROOM, RDC_ROOM, RDC_CANCEL_ROOM, 0);
#endif
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    RainDcR10cCancel();
#endif
    memclr_asm(&flt06, sizeof(flt06));
    flt06.col[0] = 0;
    flt06.col[1] = 0;
    flt06.col[2] = 0;
    flt06.col[3] = 0;
    flt06.cur[0] = 0;
    flt06.cur[1] = 0;
    flt06.cur[2] = 0;
    flt06.cur[3] = 0;
    flt06.colF[0] = 0.0f;
    flt06.colF[1] = 0.0f;
    flt06.colF[2] = 0.0f;
    flt06.alphaF = 0.0f;
    flt06.spread = 5000.0f;
    flt06.rangeLR = 2500.0f;
    flt06.rangeUp = 2500.0f;
    flt06.rangeDepth = 5000.0f;
    flt06.p = 0;
}
void Filter06Trans()
{
    static int use_filter6 = 1;
    u32 i;

#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagEvent(RD_TRANS, RDC_TRANS, 0);
#endif
    if (use_filter6 == 0) {
        return;
    }
    if (flt06.num == 0) {
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        RainDiagEvent(RD_TRANS, RDC_ZERO, RD_ZERO);
#endif
        return;
    }
    if (pG->Status_flg[1] & 0x02000000) {
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        RainDiagEvent(RD_TRANS, RDC_INDOOR, RD_INSIDE);
#endif
        return;
    }
    PSVECSubtract(&pG->Cam.param.at, &pG->Cam.param.pos, &cam_vec_LR);
    PSVECCrossProduct(&cam_vec_LR, &pG->Cam.up, &cam_vec_LR);
#line 246
    VECNormalize(&cam_vec_LR, &cam_vec_LR);
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    if (pG->Stop_flg & 0x08000000) RainDiagEvent(RD_TRANS, RDC_STOP, 0);
#endif
    if (!(pG->Stop_flg & 0x08000000)) {
#if defined(RE4DC_RAIN_PS2) && RE4DC_RAIN_PS2
        // RAIN_PS2: in a room with the PS2 recipe only the drawn subset moves (no other reader of the positions).
        const u32 moved = Filter06Ps2Rain() ? kRainPs2Lines : flt06.num;
        for (i = 0; i < moved; i++) {
            flt06.p[i].move();
        }
#else
        for (i = 0; i < flt06.num; i++) {
            flt06.p[i].move();
        }
#endif
        flt06.colF[0] = (f32) flt06.col[0];
        flt06.colF[1] = (f32) flt06.col[1];
        flt06.colF[2] = (f32) flt06.col[2];
        flt06.alphaF += ((f32) (int) flt06.col[3] - flt06.alphaF) * flt06.rate;
        flt06.cur[0] = (u8) flt06.colF[0];
        flt06.cur[1] = (u8) flt06.colF[1];
        flt06.cur[2] = (u8) flt06.colF[2];
        flt06.cur[3] = (u8) flt06.alphaF;
    }
    if (Render_checkBlurPermission()) {
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        RainDiagBlur(1);
#endif
        AddOtDirect(0x12, (void*) 0xCDCDCDCD, Filter06Render, 7, 0x400, 0, 0.0f);
    }
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    else RainDiagBlur(0);
#endif
}
void Filter06SetParam(u32 level, int r, int g, int b, int a, f32 rate, Vec* spd, f32 alpha, Vec* spdRand, f32 scale,
                      int alphaMin)
{
    u32 i;

#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagInvalidate(RD_SET, RDC_SET, RDC_CANCEL_SET, level == 0 ? RD_ZERO : 0);
#endif
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    RainDcR10cCancel();
#endif
    flt06.num = level;
    if (level > 0x800) {
        flt06.num = 0x800;
    }
    if (flt06.p == 0) {
        cParticle06* p;

#line 280
        p = (cParticle06*) MEM_ALLOC(0x10000, 1, 13);
        flt06.p = p;
        if (p == 0) {
            flt06.num = 0;
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
            RainDiagEvent(RD_ALLOC, RDC_ALLOC, 0);
#endif
            pLog->err(0, 0, "Filter06: not enough memory.");
            return;
        }
    }
    for (i = 0; i < flt06.num; i++) {
        flt06.p[i].init(i);
        flt06.p[i].m_Spd = *spd;
        flt06.p[i].m_Spd.x += spdRand->x * fRand1_1();
        flt06.p[i].m_Spd.y += spdRand->y * fRand1_1();
        flt06.p[i].m_Spd.z += spdRand->z * fRand1_1();
    }
    flt06.col[0] = r;
    flt06.col[1] = g;
    flt06.col[2] = b;
    flt06.col[3] = a;
    flt06.alphaF = alpha;
    flt06.rate = rate;
    flt06.spd = *spd;
    flt06.scale = scale;
    flt06.alphaMin = alphaMin;
}
void Filter06Render()
{
    u32 i;
    cParticle06* p;
    f32 scale;

#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagCallback();
#endif
#if defined(RE4DC_RAIN_PS2) && RE4DC_RAIN_PS2
    if (Filter06Ps2Rain()) {
        PSMTXCopy(pG->Cam.v_mat, s_rain_view);
        for (int r = 0; r < 4; ++r) {
            for (int c = 0; c < 4; ++c) {
                s_rain_proj[r][c] = pG->Cam.ProjMat[r][c];
            }
        }
        GXGetViewportv(s_rain_viewport);
        s_rain_pending = 1;
    }
#if defined(RE4DC_RAIN_DC) && RE4DC_RAIN_DC
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    // Stamp in the actual OT callback, not the preceding Trans registration.
    // main.cpp increments Frame_cnt only after Render returns; ADEB flush is synchronous inside Render.
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
    RainDiagCancelCallback();
#endif
    RainDcR10cCancel();
    if (Filter06R10cRain() && flt06.cur[3] != 0) {
        s_raindc_queued_room = 0x10C;
        s_raindc_queued_frame = pG->Frame_cnt;
        s_raindc_pending = 1;
        s_raindc_alpha = flt06.cur[3];
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        RainDiagQueue();
#endif
    }
#endif
    if ((pG->room_id == 0x11A || pG->room_id == 0x11B) && flt06.num != 0 && flt06.cur[3] != 0) {
        s_raindc_pending = 1;
        s_raindc_alpha = flt06.cur[3];
    }
#endif
#endif
}

void FilterTrans()
{
    if (Render_checkBlurPermission()) {
        if (Screen.width == 512.0f && Screen.height == 448.0f && !Filter09GetbUse()) {
            Filter00Trans();
            Filter01Trans();
            Filter08Trans();
            Filter02Trans();
            Filter03Trans();
            Filter04Trans();
            Filter05Trans();
            Filter06Trans();
            Filter07Trans();
            Filter0aTrans();
            Filter0bTrans();
        }
    }
}
int Render_checkBlurPermission()
{
    u8 mode = pG->Rno0;
    if (mode == 3 || mode == 4 || mode == 6) {
        return 1;
    }
    return 0;
}
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
void Espgen44_Destruct(EspgenWork* w)
{
    Espgen44Work* p = (Espgen44Work*) w->work;

    switch (p->type) {
    case 0:
        Filter05SetParamF(0.0f, 0.0f, 0.0f, 0, 0, 0, 0, 0, 0, 0);
        break;
    case 1: {
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        re4dc_rain_diag_destruct44(w);
#endif
        Vec zero = {0.0f, 0.0f, 0.0f};
        Filter06SetParam(0, 0, 0, 0, 0, 0.0f, &zero, 0.0f, &zero, 0.0f, 0);
        break;
    }
    }
}
int Espgen44_SetFreeWork(EspgenWork* w, EspGenWork* rec, EspSeqData* head, cModel* model, u16 parts, Mtx* mtx,
                         Vec* pos, Vec* rot, EspSeqOpt* pSct)
{
    Espgen44Work* p = (Espgen44Work*) w->work;
    if (rec->Id == 0) {
        p->type = 0;
    } else {
        p->type = 1;
    }

    switch (p->type) {
    case 0: {
        int level = (s8) rec->Work8[0] * 100 + 100;
        f32 scale = rec->Size_base_x * 0.005f;
        int kind = rec->Tex_id;
        Filter05SetParamM(level, rec->Col_start_r, rec->Col_start_g, rec->Col_start_b, rec->Col_start_a, rec->Col_d_a, 0.0f, scale, rec->Blend_type, kind);
        break;
    }
    case 1: {
        int level = (s8) rec->Work8[0] * 100 + 100;
        f32 scale = rec->Size_base_x * 0.005f;
        int kind = rec->Work8[1];
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        const u32 before = re4dc_rain_diag_generation();
#endif
        Filter06SetParam(level, rec->Col_start_r, rec->Col_start_g, rec->Col_start_b, rec->Col_start_a, rec->Col_d_a, &rec->Speed, 0.0f, &rec->R_speed, scale,
                         kind);
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        re4dc_rain_diag_bind44(before, w, rec, head, w->info.owner,
            (w->flag & 3) == 1 && w->id == 0x44 && rec->Kind == 1 && rec->Espgen_id == 0x44 && rec->Id != 0,
            ((u32) rec->Id << 8) | rec->Kind);
#endif
        break;
    }
    }
    return 1;
}
// Mock boundary: actual ADEB hook calls the real extracted RainDcFlush here.
void re4dc_rain_flush(){RainDcFlush();}
#if RE4DC_RAIN_R10C_DIAG
RainDiagRecord physical{};bool dirty=true;unsigned writebacks=0;
volatile RainDiagRecord* re4dc_rain_diag_host_p2(){return &physical;}
void dcache_wback_range(uintptr_t address,unsigned n){assert(address==(uintptr_t)&re4dc_rain_r10c_diag&&n==128);++writebacks;if(dirty){std::memcpy(&physical,(const void*)&re4dc_rain_r10c_diag,128);dirty=false;}}
void reset_diag(){std::memset(&physical,0,sizeof physical);std::memset((void*)&re4dc_rain_r10c_diag,0,128);dirty=true;writebacks=0;}
#else
void dcache_wback_range(uintptr_t,unsigned){}void reset_diag(){}
#endif
void reset(){reset_diag();random_action=nullptr;native_action=nullptr;report_override=0xffffffffU;global=Global{};flt06=Filter06Work{};Screen.width=512;Screen.height=448;pause_filter=false;accept_ot=true;alloc_fail=false;moved=queued=initialized=sent=random_calls=drains=0;callback=nullptr;s_raindc_pending=s_raindc_ready=s_raindc_sent=s_raindc_frames=0;s_raindc_frame=0;s_raindc_seed=0x2545F491U;s_raindc_area=0;std::memset(s_raindc,0,sizeof(s_raindc));
#if RE4DC_RAIN_R10C_DC
s_raindc_queued_room=s_raindc_queued_frame=0;
#endif
}
void setter(){EspGenWork record;record.Size_base_x=200;record.Col_d_a=1;record.Speed={21,-250,0};record.R_speed={0,0,0};EspgenWork owner;EspSeqData head;assert(Espgen44_SetFreeWork(&owner,&record,&head,nullptr,0,nullptr,nullptr,nullptr,nullptr)==1);}
void setup(){reset();Filter06Init();setter();}
void run_callback(){if(callback){auto f=callback;callback=nullptr;f();}}
void image(){FilterTrans();run_callback();GXSetDrawSync(0xADEB);}
void night(){reset();Filter06Init();pG->room_id=0x11b;flt06.num=1600;flt06.p=particles;flt06.col[0]=flt06.col[1]=flt06.col[2]=170;flt06.col[3]=60;flt06.rate=1;flt06.cur[3]=0;
for(unsigned j=0;j<20;++j){pG->Frame_cnt+=j%7;flt06.col[3]=j%2?60:30;pG->room_id=j%3?0x11b:0x11a;pG->Stop_flg=j%5==0?0x08000000:0;image();std::fwrite(s_raindc,sizeof(s_raindc),1,stdout);std::fwrite(s_raindc_out,sizeof(s_raindc_out),1,stdout);std::fwrite(&s_raindc_seed,sizeof(s_raindc_seed),1,stdout);std::fwrite(&s_raindc_area,sizeof(s_raindc_area),1,stdout);}
std::fwrite(&moved,sizeof(moved),1,stdout);std::fwrite(&sent,sizeof(sent),1,stdout);}
int legacy_main(int argc,char**argv){if(argc>1){night();return 0;}
setup();assert(flt06.num==1100&&initialized==1100&&random_calls==3300);image();assert(moved==1100&&queued==1&&drains==1);
#if RE4DC_RAIN_R10C_DC
assert(sent==320&&s_raindc_pending==0&&s_raindc_queued_room==0);
unsigned n=sent;GXSetDrawSync(0xADEB);assert(sent==n);
// Reject every wrong retained source-signature field, including null allocation.
for(int field=0;field<13;field++){setup();flt06.cur[3]=80;
switch(field){case 0:pG->room_id=0x10d;break;case 1:flt06.p=nullptr;break;case 2:flt06.num=1099;break;case 3:flt06.col[0]--;break;case 4:flt06.col[1]--;break;case 5:flt06.col[2]--;break;case 6:flt06.col[3]--;break;case 7:flt06.rate=.5f;break;case 8:flt06.scale=2;break;case 9:flt06.spd.x++;break;case 10:flt06.spd.y++;break;case 11:flt06.spd.z++;break;case 12:flt06.alphaMin=1;break;}
Filter06Render();GXSetDrawSync(0xADEB);assert(sent==0&&s_raindc_pending==0);}
// Both dispatcher refusal and post-callback loss of permission fail closed.
for(int phase=0;phase<2;phase++)for(int gate=0;gate<6;gate++){setup();flt06.cur[3]=80;if(phase)Filter06Render();
switch(gate){case 0:pG->Status_flg[1]=0x02000000;break;case 1:pause_filter=true;break;case 2:Screen.width=640;break;case 3:Screen.height=480;break;case 4:pG->Rno0=2;break;case 5:accept_ot=false;break;}
if(!phase){FilterTrans();run_callback();}if(phase&&gate==5){ // OT refusal precedes callback; cannot revoke an already completed callback.
GXSetDrawSync(0xADEB);assert(sent==320);continue;}
GXSetDrawSync(0xADEB);assert(sent==0&&s_raindc_pending==0);}
// Source failure/no visible alpha; source-authoritative fade uses80 and experimental120/100 gain.
setup();alloc_fail=true;flt06.p=nullptr;setter();assert(flt06.num==0);image();assert(sent==0);
setup();flt06.cur[3]=0;Filter06Render();GXSetDrawSync(0xADEB);assert(sent==0);
setup();flt06.cur[3]=20;Filter06Render();GXSetDrawSync(0xADEB);assert(sent==320);assert((s_raindc_out[0].head>>24)==(u32)(s_raindc[0].a*.25f*1.2f));assert((s_raindc_out[0].head&0xffffff)==0xd2d2d2);
// Normal callback-time tag equals the render frame, including0/UINT_MAX; stale frames/rooms are consumed.
for(u32 frame:{0U,1U,0xffffffffU}){setup();pG->Frame_cnt=frame;flt06.cur[3]=80;Filter06Render();assert(s_raindc_queued_frame==frame);GXSetDrawSync(0xAAAA);assert(sent==0&&s_raindc_pending==1);GXSetDrawSync(0xADEB);assert(sent==320);}
for(int loss=0;loss<7;loss++){setup();flt06.cur[3]=80;Filter06Render();
switch(loss){case 0:++pG->Frame_cnt;break;case 1:pG->room_id=0x10d;break;case 2:flt06.num--;break;case 3:flt06.cur[3]=0;break;case 4:Filter06RoomInit();assert(s_raindc_pending==0);break;case 5:{Vec zero{};Filter06SetParam(0,0,0,0,0,0,&zero,0,&zero,0,0);assert(s_raindc_pending==0);break;}case 6:setter();assert(s_raindc_pending==0);flt06.cur[3]=80;break;}
GXSetDrawSync(0xADEB);assert(sent==0&&s_raindc_pending==0);pG->room_id=0x10c;pG->Frame_cnt=1;GXSetDrawSync(0xADEB);assert(sent==0);}
// Destroy actual controller cancels; a replacement wrong-profile callback cancels prior ticket.
setup();flt06.cur[3]=80;Filter06Render();EspgenWork owner;owner.storage.type=1;Espgen44_Destruct(&owner);assert(s_raindc_pending==0);GXSetDrawSync(0xADEB);assert(sent==0);
setup();flt06.cur[3]=80;Filter06Render();flt06.rate=0;Filter06Render();assert(s_raindc_pending==0);
// Stop freezes source and private pool motion while continuing native draw; no catchup when unpaused.
setup();image();RainDcDrop before[320];std::memcpy(before,s_raindc,sizeof(before));n=sent;unsigned m=moved;float alpha=flt06.alphaF;u32 seed=s_raindc_seed;pG->Stop_flg=0x08000000;pG->Frame_cnt+=100;image();assert(sent==n+320&&moved==m&&flt06.alphaF==alpha&&seed==s_raindc_seed&&std::memcmp(before,s_raindc,sizeof(before))==0);pG->Stop_flg=0;++pG->Frame_cnt;image();assert(s_raindc_frame==pG->Frame_cnt);
// A real night replacement callback does not lose its new untagged ticket.
setup();flt06.cur[3]=80;Filter06Render();pG->room_id=0x11b;flt06.num=1600;flt06.col[3]=60;flt06.cur[3]=60;Filter06Render();GXSetDrawSync(0xADEB);assert(sent==320&&(s_raindc_out[0].head&0xffffff)==0xb4b4b4);
std::puts("PASS r10c signature/dispatcher/alloc/fade/frame+room/rebind/destruct/stop/consume/reused-night");
#else
assert(sent==0&&s_raindc_pending==0);std::puts("PASS off leaves r10c unadmitted");
#endif
return 0;
}
#if RE4DC_RAIN_R10C_DIAG
bool valid_sample(){return physical.abi_flags==1&&!(physical.seq&1)&&physical.seq<RD_LAST&&(physical.state_flags&RD_SAMPLE)&&(physical.event_reason&0xffff)==RD_RETURN&&physical.callback_generation==physical.setter_generation&&physical.callback_frame==physical.queue_frame&&physical.queue_frame==physical.event_frame&&(physical.rooms&0xffff)==0x10c&&(physical.rooms>>16)==0x10c;}
void same_record(const RainDiagRecord& before){assert(std::memcmp(&before,&physical,128)==0);}
void bytecopy(RainDiagRecord& to){std::memcpy(&to,&physical,128);}
void rebind_action(){setter();flt06.cur[3]=80;}
void callback_action(){Filter06Render();}
void frame_action(){++pG->Frame_cnt;}
void room_action(){pG->room_id=0x10d;}
void callback_gen_action(){++physical.callback_generation;}
void queue_frame_action(){++physical.queue_frame;}
void tests_diag(){
// First P2 backing may be stale while startup cached BSS zero is dirty. Only boot writes back.
reset();std::memset(&physical,0x55,128);Filter06Init();assert(writebacks==1&&physical.abi_flags==1&&physical.setter_generation==1&&physical.counts[RDC_ROOM]==1);
setter();FilterTrans();run_callback();GXSetDrawSync(0xADEB);
#if RE4DC_RAIN_R10C_DC
assert(valid_sample()&&physical.native_requested==320&&physical.native_accepted==320&&physical.accepted_total==320);
assert((physical.state_flags&RD_PENDING)==0&&(physical.state_flags&RD_QUEUE_KEY));
assert(physical.counts[RDC_BOUND]==1&&physical.counts[RDC_QUEUE]==1&&physical.counts[RDC_CONSUMED]==1);
#endif
// Warm clean cached zeros cannot overwrite already-published P2 counts.
unsigned bound=physical.counts[RDC_BOUND];Filter06Init();assert(writebacks==2&&physical.counts[RDC_BOUND]==bound&&physical.counts[RDC_ROOM]==2);
// Arbitrary ABI0/nonzero record is not boot and cannot thaw through warm init or any hook.
setup();physical.abi_flags=0;RainDiagRecord before;bytecopy(before);Filter06Init();setter();Filter06Render();RainDiagNativeKey key{};RainDiagReturned(&key);same_record(before);
// Each fault class at an ordinary nonterminal even freezes all future writes.
for(int fault=0;fault<4;fault++){setup();
 if(fault==0){physical.counts[RDC_TRANS]=0xfffe;Filter06Trans();}
 if(fault==1){physical.setter_generation=0xfffffffe;setter();}
 if(fault==2){physical.accepted_total=0xfffffffe;key={};key.reported=1;RainDiagReturned(&key);}
 if(fault==3){physical.seq=RD_LAST-2;Filter06Trans();assert(physical.seq==RD_LAST);}
 assert(physical.abi_flags!=1&&!(physical.seq&1));bytecopy(before);Filter06Init();setter();Filter06Render();RainDiagReturned(&key);same_record(before);}
// No ABI0 or unsupported ABI can initialize even if seq is0 but other bytes are nonzero.
for(u32 abi:{0U,2U,0x10001U}){setup();physical.abi_flags=abi;physical.seq=0;bytecopy(before);Filter06Init();same_record(before);}
// Actual dispatcher/callback candidate exists in OFF; no native call is manufactured there.
setup();image();assert(physical.counts[RDC_CALLBACK]==1&&physical.counts[RDC_CANDIDATE]==1);
assert((physical.state_flags&RD_CAUSAL)&&!(physical.state_flags&0x80000000U));
#if RE4DC_RAIN_R10C_DC
assert(valid_sample());unsigned total=physical.accepted_total;setter();assert(!valid_sample()&&physical.accepted_total==total);flt06.cur[3]=80;Filter06Render();assert(!valid_sample()&&!(physical.state_flags&RD_SAMPLE));
setup();image();Filter06Trans();assert(!(physical.state_flags&RD_SAMPLE));
// Actual native return value, including0/partial, is recorded; never n substituted for return.
for(unsigned ret:{0U,17U,320U}){setup();report_override=ret;image();assert(valid_sample()&&physical.native_requested==320&&physical.native_accepted==ret&&physical.accepted_total==ret);assert(physical.counts[ret?RDC_RETURN_POSITIVE:RDC_RETURN_ZERO]==1);}
setup();report_override=321;image();assert(!valid_sample()&&!(physical.state_flags&RD_SAMPLE)&&physical.accepted_total==321);
// A new setter or identical same-frame replacement callback during the call cannot borrow its return.
for(auto action:{rebind_action,callback_action,frame_action,room_action,callback_gen_action,queue_frame_action}){setup();native_action=action;image();assert(!valid_sample()&&!(physical.state_flags&RD_SAMPLE)&&physical.accepted_total==320);}
// Queue source frame is captured at callback; stale loss is observed and not consumed as a return.
setup();flt06.cur[3]=80;Filter06Render();++pG->Frame_cnt;GXSetDrawSync(0xADEB);assert(!valid_sample()&&physical.counts[RDC_STALE]==1&&physical.counts[RDC_CONSUMED]==0&&!(physical.state_flags&RD_QUEUE_KEY));
// Source setter generation remains distinct across recycled record/controller addresses.
setup();u32 gen=physical.setter_generation;setter();assert(physical.setter_generation==gen+1&&(physical.state_flags&RD_CAUSAL)&&!valid_sample());
// Unknown owner is retained as unknown, not archive authentication.
setup();u32 before_gen=re4dc_rain_diag_generation();setter();re4dc_rain_diag_bind44(before_gen,(void*)1,(void*)2,(void*)3,0xd2,1,0x101);assert(physical.observed_owner==0xffffffffU);
// Wrong record/controller signature rejects actual call-site binding.
for(int bad=0;bad<5;bad++){setup();EspGenWork rec;rec.Size_base_x=200;rec.Col_d_a=1;rec.Speed={21,-250,0};EspgenWork owner;EspSeqData head;
 if(bad==0)rec.Kind=0;if(bad==1)rec.Espgen_id=0x43;if(bad==2)owner.id=0x43;if(bad==3)owner.flag=3;if(bad==4)alloc_fail=true,flt06.p=nullptr;
 Espgen44_SetFreeWork(&owner,&rec,&head,nullptr,0,nullptr,nullptr,nullptr,nullptr);assert(!(physical.state_flags&RD_CAUSAL)&&physical.counts[RDC_BIND_REJECT]>0);}
// A nested setter can finish and bind, but the outer call cannot relabel its overwritten state as that nested cause.
setup();random_action=setter;setter();assert(!(physical.state_flags&RD_CAUSAL)&&physical.counts[RDC_BIND_REJECT]>0);
// Direct setters have no authenticated Espgen44 caller and invalidate prior provenance.
setup();Vec zero{};Filter06SetParam(1100,170,170,170,80,1,&zero,0,&zero,1,0);assert(!(physical.state_flags&RD_CAUSAL)&&!valid_sample());
// Counter fields name real invocation/retirement edges. Stop still draws, source/private motion freezes.
setup();image();pG->Stop_flg=0x08000000;++pG->Frame_cnt;image();assert(valid_sample()&&physical.counts[RDC_STOP]==1&&physical.counts[RDC_STOP_FLUSH]==1);
setup();flt06.cur[3]=80;Filter06Render();setter();assert(physical.counts[RDC_CANCEL_SET]==1&&!valid_sample());
setup();flt06.cur[3]=80;Filter06Render();Filter06RoomInit();assert(physical.counts[RDC_CANCEL_ROOM]==1&&!valid_sample());
setup();flt06.cur[3]=80;Filter06Render();Filter06Render();assert(physical.counts[RDC_CANCEL_CALLBACK]==1&&!valid_sample());
setup();EspgenWork owner;owner.storage.type=1;Espgen44_Destruct(&owner);assert(physical.counts[RDC_DESTRUCT]==1&&!(physical.state_flags&RD_CAUSAL));
#else
assert(!valid_sample()&&physical.counts[RDC_QUEUE]==0&&physical.counts[RDC_CONSUMED]==0&&physical.accepted_total==0);
#endif
std::puts("PASS actual diagnostic cold/warm/ABI/faultfreeze/causal/return/queue/stop controls");
}
#endif
int original_test_main(int argc,char**argv){if(argc>1)return legacy_main(argc,argv);assert(legacy_main(0,nullptr)==0);
#if RE4DC_RAIN_R10C_DIAG
tests_diag();
#endif
}

void change_live_num(){flt06.num=1099;}
void change_live_alpha(){flt06.cur[3]=17;}
void change_live_target(){flt06.col[3]=79;}
void change_live_stop(){pG->Stop_flg|=0x08000000;}
void change_live_indoor(){pG->Status_flg[1]|=0x02000000;}

int main(){unsigned reproduced=0;
for(auto action:{change_live_num,change_live_alpha,change_live_target,change_live_stop,change_live_indoor}){
 setup();native_action=action;image();assert(sent==320);assert(valid_sample()&&(physical.state_flags&RD_SAMPLE));
 assert(physical.native_accepted==320);++reproduced;
}
std::printf("REPRODUCED %u native-return samples retain RD_SAMPLE while post-call live key changes are freshly snapshotted\n",reproduced);
}
