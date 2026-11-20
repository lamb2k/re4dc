// Native effect service (lane eng-e2): see fx.h. Engine bodies of the effect entry points the hosted behaviour calls,
// the sequence players, the sprite arrays and their kernels.
//
// What is simulated, and how it relates to the original (src/game/est.cpp, espgen10.cpp, esp_sub.cpp, esp.cpp):
//   - EstSet: a sequence player on the est table (owner, id) the hosted code registered, with the original's start
//     state (parts, offset, angle, explicit position, option block). Its seed comes from the engine generator.
//   - the sequence player's frame (espgen10_Update): the model check, the matrix from the parts (or the fixed offset),
//     then every record whose Set_time equals the frame counter spawns; the player ends after its last record.
//   - a Kind 0 record spawns one sprite with EspSeqSet's common set-up (position, speed, acceleration, angle and angle
//     speed with their random spreads from the sequence seed, sizes, colours, fade counts, life, animation, release
//     time; the parent: world through the matrix, screen offsets, free, or a part of the model) and the option block's
//     overrides. The per-id SetFreeWork extras (ribbons, trails, models, lights) are not simulated: every id moves as
//     the common sprite (CommonMove + AnmMove), drawn as a camera-facing quad. Kind 1 records (nested generators) and
//     effect models (ids 0xFC..0xFF) are counted, not simulated.
//   - a sprite's tick (cEsp::CommonMove, ColorUpdate, AnmMove): release from the parent, speed integration, size,
//     angle, colour envelope, life end, texture animation; here as kernels over the SoA rows, in that order per
//     sprite, with the same float operations (no contraction), so a sprite given the original's start state follows
//     the original's path to the bit.
//   - deletes by owner info (Core_flg, Core_kind, Core_pEm, model), the death of the followed model.
#include "global.h"
#include "model.h"
#include "esp.h"
#include "espgen.h"
#include "est.h"
#include "at_sub2.h"
#include "atari.h"
#include "math_sub.h"
#include "fx.h"
extern "C" float atan2f(float, float);
#include <string.h>
#include <stdio.h>
#ifdef FX_HOST_CHECK
#define FX_LOG(...) fprintf(stderr, __VA_ARGS__)
#else
#include "e1_engine.h"
#define FX_LOG(...) e1_log(__VA_ARGS__)
#endif

struct FxSprites fx_sprites;
struct FxStats fx_stats;
unsigned (*fx_check_seed)(void);
static FxSprites& S = fx_sprites;

// ---- the engine generator (presentation only): xorshift32, seeded once per room ----
static uint32_t fx_rng_state = 0x2545F491u;
static uint32_t fx_rng()
{
    uint32_t x = fx_rng_state;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    return fx_rng_state = x;
}
// The original's per-instance LCG (rnd.cpp fRandSeed1_1): a float in [-1, 1) from the caller's seed.
static inline f32 seed11(u32* seed)
{
    f32 f;
    *seed = *seed * 0x19660D + 0x3C6EF35F;
    u32 u = (*seed & 0x007FFFFF) | 0x3F800000;
    memcpy(&f, &u, 4);
    f = f * 2.0f - 2.0f - 1.0f;
    return f;
}

// ---- registry: est tables and texture animations the hosted code registered (EspDataLoad) ----
struct EffData { u32 version, ofsTexId, ofsEstList, ofsSstList, ofsPathList, ofsEfmId, ofsTpl, ofsAnm, ofsEstData, ofsSstData, ofsPathData, ofsEfm; };
struct EffIdTbl { u32 num; struct { u16 id, x2; u32 x4; } ent[1]; };
struct EffOfsTbl { u32 num; u32 ofs[1]; };
static const SstData* est_data[0xD3];
static const SstList* est_list[0xD3];
static uint16_t owner_loads[0xD3];
static const EspAnmData* tex_anm[256];
static uint8_t tex_owner[256];

int EspDataLoad(u32 addr, u32 owner, int mode)
{
    const EffData* d = (const EffData*) addr;
    if (!d || owner > 0xD2) return 0;
    if (owner_loads[owner]++) return mode != 1;
    if (d->version != 0xB) { FX_LOG("FX data: owner %lx version %lx refused\n", (unsigned long) owner, (unsigned long) d->version); return 0; }
    const EffIdTbl* ids = (const EffIdTbl*) ((const u8*) d + d->ofsTexId);
    const EffOfsTbl* anms = (const EffOfsTbl*) ((const u8*) d + d->ofsAnm);
    for (u32 i = 0; i < ids->num; i++) {
        const u16 id = ids->ent[i].id;
        if (id < 256) { tex_anm[id] = (const EspAnmData*) ((const u8*) anms + anms->ofs[i]); tex_owner[id] = (u8) owner; }
    }
    est_data[owner] = (const SstData*) ((const u8*) d + d->ofsEstData);
    est_list[owner] = (const SstList*) ((const u8*) d + d->ofsEstList);
    FX_LOG("FX data: owner %02lx est %lu tex %lu\n", (unsigned long) owner, (unsigned long) est_list[owner]->num, (unsigned long) ids->num);
    return 1;
}
extern "C" int EspDataRelease(u32 owner, int flag, int warn)
{
    (void) warn;
    if (owner > 0xD2 || !owner_loads[owner]) return 0;
    if (flag == 1 && --owner_loads[owner]) return 1;
    owner_loads[owner] = 0;
    est_data[owner] = 0;
    est_list[owner] = 0;
    for (unsigned i = 0; i < 256; i++) if (tex_anm[i] && tex_owner[i] == owner) tex_anm[i] = 0;
    return 1;
}
EspSeqData* EspGetEstAddr(u32 owner, int id, int quiet)
{
    (void) quiet;
    if (owner > 0xD2 || !est_list[owner]) return 0;
    const SstList* l = est_list[owner];
    for (u32 i = 0; i < l->num; i++)
        if (l->ent[i].no == (u16) id) return (EspSeqData*) ((const u8*) est_data[owner] + est_data[owner]->ofs[i]);
    return 0;
}

// ---- packed records (the Dreamcast tree's ESQ tables: a 12-byte mask, then the present words of the 300-byte record) ----
struct FxArc { const u8* base; unsigned bytes; const u8* entries; unsigned count; };
static FxArc arcs[8];
static u32 rdw(const u8* p) { u32 v; memcpy(&v, p, 4); return v; }
static u16 rdh(const u8* p) { u16 v; memcpy(&v, p, 2); return v; }
void fx_bind_archive(const void* base, unsigned bytes)
{
    const u8* a = (const u8*) base;
    if (!a || bytes < 16) return;
    const u32 n = rdw(a);
    if (n > (bytes - 16) / 8) return;
    for (u32 i = 0; i < n; i++) {
        if (memcmp(a + 16 + 4 * n + 4 * i, "ESQ", 4)) continue;
        const u32 off = rdw(a + 16 + 4 * i);
        if (off > bytes - 32 || memcmp(a + off, "R4ESQTBL", 8)) return;
        for (FxArc& r : arcs)
            if (!r.base) { r = {a, bytes, a + off + 32, rdw(a + off + 12)}; FX_LOG("FX bind: %u sequences\n", r.count); return; }
    }
}
static void decode(const u8* p, u8* out)
{
    unsigned at = 12;
    for (unsigned i = 0; i < 75; i++) {
        u32 v = 0;
        if (rdw(p + 4 * (i / 32)) & (1u << (i % 32))) { v = rdw(p + at); at += 4; }
        memcpy(out + 4 * i, &v, 4);
    }
}
// Record `no` of sequence `head` into `scratch` (or in place when the archive does not pack it).
static const EspGenWork* record(const EspSeqData* head, unsigned no, EspGenWork* scratch)
{
    const u8* h = (const u8*) head;
    for (const FxArc& r : arcs) {
        if (!r.base || h < r.base || h >= r.base + r.bytes) continue;
        const u32 off = h - r.base;
        unsigned lo = 0, hi = r.count;
        while (lo < hi) { unsigned m = (lo + hi) / 2; if (rdw(r.entries + 12 * m) <= off) lo = m + 1; else hi = m; }
        if (lo && rdw(r.entries + 12 * (lo - 1)) == off) {
            const u32 ref = rdw(h + 48 + 4 * no);
            if (ref & 1) { decode(h + (ref & ~1u), (u8*) scratch); return scratch; }
            return (const EspGenWork*) (h + ref);
        }
    }
    return (const EspGenWork*) (h + 48 + 300 * no);
}

// ---- sequence players (espgen10) ----
struct FxSeq {
    const EspSeqData* head;
    cModel* model;
    u32 guid, seed, pem;
    u16 no, time, coreflg;
    u8 parts, flg, kind, owner, live, has_opt;
    Mtx mat;
    Vec offset, ang;
    EspSeqOpt opt;
};
static FxSeq seqs[FX_SEQ_MAX];
static unsigned seq_n;
static u32 next_uid;

static void kill_sprite(unsigned i)
{
    const unsigned last = --S.n;
    fx_stats.died++;
    if (i == last) return;
#define MV(f) S.f[i] = S.f[last]
    MV(px); MV(py); MV(pz); MV(vx); MV(vy); MV(vz); MV(ax); MV(ay); MV(az); MV(dv);
    MV(rx); MV(ry); MV(rz); MV(wx); MV(wy); MV(wz); MV(sbx); MV(sby); MV(smul); MV(splus); MV(sdamp);
    MV(cr); MV(cg); MV(cb); MV(ca); MV(dr); MV(dg); MV(db); MV(da); MV(c0r); MV(c0g); MV(c0b); MV(c0a);
    MV(colmax); MV(colhold); MV(posstart); MV(sizestart); MV(lifemax); MV(life); MV(anmcnt);
    MV(tex); MV(ptn); MV(anmrate); MV(blend); MV(id); MV(release); MV(owner); MV(tool); MV(parent); MV(model);
    MV(guid); MV(pem); MV(uid);
#undef MV
}

// A point through a 3x4 matrix, and a direction (no translation)
static inline void mul_point(const float* m, float& x, float& y, float& z)
{
    const float a = x, b = y, c = z;
    x = m[0] * a + m[1] * b + m[2] * c + m[3];
    y = m[4] * a + m[5] * b + m[6] * c + m[7];
    z = m[8] * a + m[9] * b + m[10] * c + m[11];
}
static inline void mul_dir(const float* m, float& x, float& y, float& z)
{
    const float a = x, b = y, c = z;
    x = m[0] * a + m[1] * b + m[2] * c;
    y = m[4] * a + m[5] * b + m[6] * c;
    z = m[8] * a + m[9] * b + m[10] * c;
}

// EspSeqSet, the common set-up (esp_sub.cpp): one sprite from record `rec`.
static int spawn(const EspGenWork* rec, FxSeq& q, const Vec* pos)
{
    const u8 id = rec->Id;
    if ((u8) (id + 4) <= 3) { fx_stats.efm++; return 1; }
    if (id == 0x3F || rec->Blend_type > 5) return 0;
    if (S.n >= FX_MAX) { fx_stats.full++; return 0; }
    u32* seed = &q.seed;
    const unsigned i = S.n;
    u32 tool = rec->Tool_flg;
    if (tool & 8) { if (seed11(seed) > 0.0f) tool |= 2; else tool &= ~2u; }
    if (tool & 0x10) { if (seed11(seed) > 0.0f) tool |= 4; else tool &= ~4u; }
    float px = rec->Pos.x + rec->R_pos.x * seed11(seed);
    float py = rec->Pos.y + rec->R_pos.y * seed11(seed);
    float pz = rec->Pos.z + rec->R_pos.z * seed11(seed);
    float vx = rec->Speed.x + rec->R_speed.x * seed11(seed);
    float vy = rec->Speed.y + rec->R_speed.y * seed11(seed);
    float vz = rec->Speed.z + rec->R_speed.z * seed11(seed);
    float ax = rec->Speed_plus.x + rec->R_speed_plus.x * seed11(seed);
    float ay = rec->Speed_plus.y + rec->R_speed_plus.y * seed11(seed);
    float az = rec->Speed_plus.z + rec->R_speed_plus.z * seed11(seed);
    const float d2r = 3.1415927f / 180.0f;
    float rx = (rec->Ang.x + rec->R_ang.x * seed11(seed)) * d2r;
    float ry = (rec->Ang.y + rec->R_ang.y * seed11(seed)) * d2r;
    float rz = (rec->Ang.z + rec->R_ang.z * seed11(seed)) * d2r;
    float wx = (rec->Ang_plus.x + rec->R_ang_plus.x * seed11(seed)) * d2r;
    float wy = (rec->Ang_plus.y + rec->R_ang_plus.y * seed11(seed)) * d2r;
    float wz = (rec->Ang_plus.z + rec->R_ang_plus.z * seed11(seed)) * d2r;
    const float rs = rec->R_size_base * seed11(seed);
    const float* parent = 0;
    cModel* model = q.model;
    const unsigned parts = rec->Parts_no;
    switch (parts) {
    case 0xFF:
        mul_point(&q.mat[0][0], px, py, pz);
        mul_dir(&q.mat[0][0], vx, vy, vz);
        mul_dir(&q.mat[0][0], ax, ay, az);
        model = 0;
        break;
    case 0xF8: case 0xF9: case 0xFA: case 0xFB: case 0xFC: case 0xFD:
        px += q.mat[0][3]; py += q.mat[1][3]; pz += q.mat[2][3];
        model = 0;
        break;
    case 0xFE:
        model = 0;
        break;
    default:
        if (!model || parts >= model->nParts) return 0;
        if (tool & 0x20) {   // rotation only: placed once at the part, then free
            cModel* p = model->getPartsPtr(parts);
            Mtx m2;
            PSMTXIdentity(m2);
            low_RotMatrix(m2, &model->ang);
            Vec v, rp = rec->Pos;
            PSMTXMultVecSR(m2, &rp, &v);
            m2[0][3] = p->mat[0][3] + v.x; m2[1][3] = p->mat[1][3] + v.y; m2[2][3] = p->mat[2][3] + v.z;
            px = py = pz = 0.0f;
            mul_point(&m2[0][0], px, py, pz);
            mul_dir(&m2[0][0], vx, vy, vz);
            mul_dir(&m2[0][0], ax, ay, az);
            px += rec->R_pos.x * seed11(seed);
            py += rec->R_pos.y * seed11(seed);
            pz += rec->R_pos.z * seed11(seed);
            model = 0;
        } else {
            parent = &model->getPartsPtr(parts)->mat[0][0];
            if (pos) { px += pos->x; py += pos->y; pz += pos->z; }
        }
        break;
    }
    float sbx = rec->Size_base_x + rs, sby = rec->Size_base_y + rs;
    u8 c0r = rec->Col_start_r, c0g = rec->Col_start_g, c0b = rec->Col_start_b, c0a = rec->Col_start_a;
    if (q.has_opt) {   // EspSeqOpt: replace, multiply, add (speed 1, size 2, colour 4)
        const EspSeqOpt& o = q.opt;
        if (o.OverWrite_flg & 1) {
            vx = o.Speed.x + rec->R_speed.x * seed11(seed);
            vy = o.Speed.y + rec->R_speed.y * seed11(seed);
            vz = o.Speed.z + rec->R_speed.z * seed11(seed);
        }
        if (o.OverWrite_flg & 2) { sbx = o.Size_base_x; sby = o.Size_base_y; }
        if (o.OverWrite_flg & 4) { c0r = o.Col_start_r; c0g = o.Col_start_g; c0b = o.Col_start_b; c0a = o.Col_start_a; }
        if (o.Mul_flg & 1) { vx *= o.Speed.x; vy *= o.Speed.y; vz *= o.Speed.z; }
        if (o.Mul_flg & 2) { sbx *= o.Size_base_x; sby *= o.Size_base_y; }
        if (o.Add_flg & 1) { vx += o.Speed.x; vy += o.Speed.y; vz += o.Speed.z; }
        if (o.Add_flg & 2) { sbx += o.Size_base_x; sby += o.Size_base_y; }
    }
    S.px[i] = px; S.py[i] = py; S.pz[i] = pz;
    S.vx[i] = vx; S.vy[i] = vy; S.vz[i] = vz;
    S.ax[i] = ax; S.ay[i] = ay; S.az[i] = az; S.dv[i] = rec->D_speed;
    S.rx[i] = rx; S.ry[i] = ry; S.rz[i] = rz; S.wx[i] = wx; S.wy[i] = wy; S.wz[i] = wz;
    S.sbx[i] = sbx; S.sby[i] = sby; S.smul[i] = 1.0f; S.splus[i] = rec->Size_plus; S.sdamp[i] = rec->D_size_plus;
    S.c0r[i] = c0r; S.c0g[i] = c0g; S.c0b[i] = c0b; S.c0a[i] = c0a;
    S.cr[i] = c0r; S.cg[i] = c0g; S.cb[i] = c0b; S.ca[i] = c0a;
    S.dr[i] = rec->Col_d_r; S.dg[i] = rec->Col_d_g; S.db[i] = rec->Col_d_b; S.da[i] = rec->Col_d_a;
    S.colmax[i] = rec->Col_max_cnt; S.colhold[i] = rec->Col_start_cnt; S.posstart[i] = rec->Pos_start_cnt;
    S.sizestart[i] = rec->Size_start_cnt; S.lifemax[i] = rec->Life_max; S.life[i] = rec->Life_time;
    S.tex[i] = rec->Tex_id; S.ptn[i] = rec->Ptn_no; S.anmrate[i] = (u8) (rec->Anm_rate + 0x20); S.anmcnt[i] = rec->Anm_cnt;
    S.blend[i] = rec->Blend_type; S.id[i] = id; S.release[i] = rec->Release_time; S.owner[i] = q.owner; S.tool[i] = tool;
    S.parent[i] = parent; S.model[i] = parent ? model : 0; S.guid[i] = parent && model ? model->serial : 0; S.pem[i] = q.pem;
    S.uid[i] = next_uid++;
    S.n++;
    fx_stats.spawned++;
    if (S.n > fx_stats.peak) fx_stats.peak = S.n;
    return 1;
}

// espgen10_Update: one frame of a sequence player; 0 when it ended
static int seq_update(FxSeq& q)
{
    if (q.model && ((q.model->be_flag & 0x201) != 1 || q.model->serial != q.guid)) return 0;
    const unsigned parts = q.parts;
    if ((parts >= 0xF8 && parts <= 0xFD) || parts == 0xFF) return 0;
    if (parts == 0xFE) {
        PSMTXIdentity(q.mat);
        RotMatrix(q.mat, &q.ang);
        q.mat[0][3] = q.offset.x; q.mat[1][3] = q.offset.y; q.mat[2][3] = q.offset.z;
    } else {
        if (!q.model || parts >= q.model->nParts) return 0;
        if (!(q.flg & 1)) {
            cModel* part = q.model->getPartsPtr(parts);
            Vec ofs, r;
            PSMTXIdentity(q.mat);
            PSVECAdd(&q.ang, &q.model->ang, &r);
            RotMatrix(q.mat, &r);
            PSMTXMultVecSR(q.mat, &q.offset, &ofs);
            q.mat[0][3] = part->mat[0][3] + ofs.x;
            q.mat[1][3] = part->mat[1][3] + ofs.y;
            q.mat[2][3] = part->mat[2][3] + ofs.z;
            if (!(q.head->flags & 1)) q.flg |= 1;
        }
    }
    EspGenWork scratch;
    const EspGenWork* rec = record(q.head, q.no, &scratch);
    if (rec->Set_time < q.time) return 0;
    while (rec->Set_time == q.time) {
        if (rec->Kind == 0) spawn(rec, q, (q.flg & 2) ? &q.offset : 0);
        else fx_stats.kind1++;
        if (++q.no >= q.head->num) return 0;
        rec = record(q.head, q.no, &scratch);
    }
    q.time++;
    return 1;
}

// ---- entry points the hosted behaviour calls (original names, engine bodies) ----
static void est_start(cModel* model, int no, Vec* pos, Vec* rot, const EspSeqData* head, int e, int f, u32 g, u32 owner, void* h)
{
    fx_stats.est_calls++;
    if (!head || !head->num) { fx_stats.est_nodata++; return; }
    if (pG->Status_flg[2] & 0x00080000) e |= 0x2000;
    if (pG->Status_flg[2] & 0x02000000) e |= 1;
    FxSeq* q = 0;
    for (unsigned i = 0; i < FX_SEQ_MAX; i++) if (!seqs[i].live) { q = &seqs[i]; break; }
    if (!q) { fx_stats.seq_full++; return; }
    memset(q, 0, sizeof(*q));
    q->live = 1;
    q->head = head;
    q->model = model;
    q->guid = model ? model->serial : 0;
    q->parts = no == -1 ? head->parts : (u8) no;
    if (pos) { q->flg |= 2; q->offset = *pos; } else q->offset = head->pos;
    if (rot) q->ang = *rot;
    else { q->ang = head->rot; PSVECScale(&q->ang, &q->ang, 3.14f / 180.0f); }
    q->seed = fx_check_seed ? fx_check_seed() : (fx_rng() & 0xFFFFFF);
    q->coreflg = (u16) e; q->kind = (u8) f; q->pem = g; q->owner = (u8) owner;
    if (h) { q->opt = *(const EspSeqOpt*) h; q->has_opt = 1; }
    fx_stats.seq_started++;
    if (seq_n < FX_SEQ_MAX) seq_n++;
}
extern "C" void EstSet(int a, int b, Vec* pos, Vec* rot, int c, int d, int e, int f, u32 g, void* h)
{
    est_start((cModel*) a, b, pos, rot, EspGetEstAddr(c, d, 0), e, f, g, c, h);
}
// The est table of a model's own effect data (em_sub.cpp / em10 EstSetEm form: owner from the work's kind).
void EstSet(cModel* model, int no, Vec* pos, Vec* rot, EspSeqData* head, int e, int f, u32 g, u32 owner, void* h)
{
    est_start(model, no, pos, rot, head, e, f, g, owner, h);
}
// One record spawned at the origin, outside sequence timing (EspEstSetSelect): the laser dot of the weapon object.
int EspEstSetSelect(int owner, int id, int no, cEsp** out, int bNoSuspend)
{
    (void) bNoSuspend;
    if (out) *out = 0;
    const EspSeqData* head = EspGetEstAddr(owner, id, 1);
    if (!head || (u32) no >= head->num) return 0;
    FxSeq q;
    memset(&q, 0, sizeof(q));
    PSMTXIdentity(q.mat);
    q.seed = 0x12345678;
    q.owner = (u8) owner;
    EspGenWork scratch;
    const EspGenWork* rec = record(head, no, &scratch);
    return rec->Kind == 0 && spawn(rec, q, 0);
}
static void delete_match(int a, int b, u32 c, cModel* model)
{
    for (unsigned i = 0; i < S.n;) {
        const bool hit = (!c || S.pem[i] == c) && (!model || (S.model[i] == model && S.guid[i] == model->serial));
        (void) a; (void) b;
        if (hit) { kill_sprite(i); fx_stats.deleted++; } else i++;
    }
}
void EffectEspDelete(int a, int b, u32 c, cModel* model) { delete_match(a, b, c, model); }
void EffectEspgenDelete(int a, int b, int c)
{
    for (unsigned i = 0; i < FX_SEQ_MAX; i++) {
        FxSeq& q = seqs[i];
        if (!q.live) continue;
        if ((a && q.coreflg != a) || (b && q.kind != b) || (c && q.pem != (u32) c)) continue;
        q.live = 0;
    }
}
void EffectEfmDelete(int, int, int) {}
void EffectDeleteAll()
{
    S.n = 0;
    for (unsigned i = 0; i < FX_SEQ_MAX; i++) seqs[i].live = 0;
}
// The surface's effect pair for a weapon (at_sub2.cpp AtEffInfo::getWepEff, read in place): guns share effGun.
static int wep_eff(const AtEffInfo* info, int wep, u32* e1, u32* e2)
{
    const u32* p;
    switch (wep) {
    case 1: case 2: case 3: case 4: case 5: case 6: case 7: case 8: case 9: case 10: case 11: case 12:
    case 0x0F: case 0x11: case 0x21: p = info->effGun; break;
    case 0x13: p = info->eff13; break;
    case 0x16: p = info->eff16; break;
    case 0x17: p = info->eff17; break;
    case 0x0D: p = info->eff0D; break;
    default: return 0;
    }
    *e1 = p[0]; *e2 = p[1];
    return 1;
}
// A bullet's hit on the scenery (est.cpp EspSetEatEffect): the material's hit effect, turned to the surface normal.
void EspSetEatEffect(Vec* pos, Vec* nrm, int type, int wep)
{
    AtEffInfo* info = EatMgr.getEffInfo(type);
    Vec rot;
    if (info != 0 && (info->flag & 1)) {
        rot.x = atan2f(SQRTF(nrm->x * nrm->x + nrm->z * nrm->z), nrm->y);
        rot.y = atan2f(nrm->x, nrm->z);
    } else {
        rot.x = -atan2f(nrm->y, SQRTF(nrm->x * nrm->x + nrm->z * nrm->z));
        rot.y = atan2f(nrm->x, nrm->z);
    }
    rot.z = 0.0f;
    u32 eff1 = 0xD2, eff2 = 1;
    switch (type) {
    case 0:
        EstSet(0, -1, pos, &rot, 0, 0x1F, 0, 0, type, 0);
        break;
    case 1:
        EstSet(0, -1, pos, &rot, 0, 0x1F, 0, 0, 0, 0);
        EstSet(0, -1, pos, &rot, 0, 0x20, 0, 0, 0, 0);
        break;
    case 2: case 4: case 5: case 6: case 7:
        if (!info) break;
        wep_eff(info, wep, &eff1, &eff2);
        if (eff1 != 0xD2 && eff2 != 1) EstSet(0, -1, pos, &rot, eff1, (u8) eff2, 0, 0, 0, 0);
        break;
    }
}
void EspSetWaterHitmark(Vec* pos) { EstSet(0, -1, pos, 0, 1, 0x20, 0, 0, 0, 0); }
void EstSetEm10WaterFall(Vec* pos) { EstSet(0, -1, pos, 0, 0, 0x15, 0, 0, 0, 0); }
static u8 core_kind = 0x45;
u8 EspPullCoreKind() { return core_kind++; }

// ---- per tick ----
void fx_room_init()
{
    S.n = 0;
    for (unsigned i = 0; i < FX_SEQ_MAX; i++) seqs[i].live = 0;
    fx_rng_state = 0x2545F491u;
}
unsigned fx_live_count() { return S.n; }

// The sprite kernels (cEsp::CommonMove, ColorUpdate, AnmMove), field group by field group over the live rows. A
// sprite that dies in one group is marked and skips the later groups, then the dead are compacted, so each live sprite
// sees the original's operations in the original's order.
static uint8_t dead[FX_MAX];
static void sprites_move()
{
    const unsigned n = S.n;
    if (!n) return;
    memset(dead, 0, n);
    // 1. release from the parent: the parent's matrix is baked into position, speed and acceleration
    for (unsigned i = 0; i < n; i++) {
        const float* m = S.parent[i];
        if (!m) continue;
        if (S.model[i]) {
            cModel* md = (cModel*) S.model[i];
            if ((md->be_flag & 0x201) != 1 || md->serial != S.guid[i]) { dead[i] = 1; continue; }
        }
        if (S.release[i] != 0xFF && S.release[i] <= S.life[i]) {
            mul_point(m, S.px[i], S.py[i], S.pz[i]);
            mul_dir(m, S.vx[i], S.vy[i], S.vz[i]);
            mul_dir(m, S.ax[i], S.ay[i], S.az[i]);
            S.parent[i] = 0;
            S.model[i] = 0;
        }
    }
    // 2. motion: pos += speed; speed += acceleration; speed *= damping (once the start count has passed)
    for (unsigned i = 0; i < n; i++) {
        if (S.posstart[i] != 0 && S.posstart[i] > S.life[i]) continue;
        S.px[i] = S.px[i] + S.vx[i]; S.py[i] = S.py[i] + S.vy[i]; S.pz[i] = S.pz[i] + S.vz[i];
        S.vx[i] = S.vx[i] + S.ax[i]; S.vy[i] = S.vy[i] + S.ay[i]; S.vz[i] = S.vz[i] + S.az[i];
        S.vx[i] = S.vx[i] * S.dv[i]; S.vy[i] = S.vy[i] * S.dv[i]; S.vz[i] = S.vz[i] * S.dv[i];
    }
    // 3. size
    for (unsigned i = 0; i < n; i++) {
        if (S.sizestart[i] != 0 && S.sizestart[i] > S.life[i]) continue;
        S.smul[i] = S.smul[i] + S.splus[i];
        S.splus[i] = S.splus[i] * S.sdamp[i];
        if (S.smul[i] <= 0.0f) dead[i] = 1;
    }
    // 4. angle
    for (unsigned i = 0; i < n; i++) {
        S.rx[i] = S.rx[i] + S.wx[i]; S.ry[i] = S.ry[i] + S.wy[i]; S.rz[i] = S.rz[i] + S.wz[i];
    }
    // 5. colour envelope: fade in over colmax, hold colhold, then multiply; dies under alpha 4
    for (unsigned i = 0; i < n; i++) {
        if (dead[i]) continue;
        const unsigned life = S.life[i], cm = S.colmax[i];
        if (cm < life) {
            if (cm + S.colhold[i] <= life) {
                float r = S.cr[i] * S.dr[i], g = S.cg[i] * S.dg[i], b = S.cb[i] * S.db[i], a = S.ca[i] * S.da[i];
                S.cr[i] = r > 255.0f ? 255.0f : r; S.cg[i] = g > 255.0f ? 255.0f : g;
                S.cb[i] = b > 255.0f ? 255.0f : b; S.ca[i] = a > 255.0f ? 255.0f : a;
                if (S.ca[i] < 4.0f) dead[i] = 1;
            }
        } else if (cm != 0) {
            const float rate = (float) life / (float) cm;
            if (S.blend[i] == 3) { S.cr[i] = (float) S.c0r[i] * rate; S.cg[i] = (float) S.c0g[i] * rate; S.cb[i] = (float) S.c0b[i] * rate; }
            S.ca[i] = (float) S.c0a[i] * rate;
        }
    }
    // 6. life end, then the life counter
    for (unsigned i = 0; i < n; i++) {
        if (dead[i]) continue;
        if (S.lifemax[i] != 0 && S.lifemax[i] <= S.life[i]) { dead[i] = 1; continue; }
        S.life[i]++;
    }
    // 7. texture animation (AnmMove): 1/32-frame counter against the pattern's time; loop 0 ends the sprite
    for (unsigned i = 0; i < n; i++) {
        if (dead[i]) continue;
        const EspAnmData* anm = tex_anm[S.tex[i]];
        if (!anm) { if (S.id[i] != 3 && S.id[i] != 9 && S.id[i] != 0xC) { dead[i] = 1; fx_stats.no_tex++; } continue; }
        const u32 time = anm->Data_num == 0 ? 1 : anm->Frame_cnt[anm->Frames + S.ptn[i]];   // the starting pattern's time, as the original
        u16 cnt = (u16) (S.anmcnt[i] + S.anmrate[i]);
        unsigned ptn = S.ptn[i];
        while ((cnt >> 5) > (u16) time) {
            ptn++;
            cnt = (u16) (cnt - (time << 5));
            if (ptn >= anm->Frames) {
                const unsigned loop = anm->Loop & 3;
                if (loop == 0) { dead[i] = 1; break; }
                ptn = loop == 1 ? 0 : anm->Frames - 1;
            }
        }
        S.ptn[i] = (u8) ptn;
        S.anmcnt[i] = cnt;
    }
    // compaction (from the top, so swapped-in rows were already decided)
    for (unsigned i = n; i-- > 0;) if (dead[i]) kill_sprite(i);
}

void fx_move()
{
    for (unsigned i = 0; i < FX_SEQ_MAX; i++) {
        FxSeq& q = seqs[i];
        if (q.live && !seq_update(q)) q.live = 0;
    }
    sprites_move();
}

void fx_report()
{
    FX_LOG("FX est=%lu nodata=%lu seq=%lu seqfull=%lu spawned=%lu full=%lu kind1=%lu efm=%lu died=%lu deleted=%lu notex=%lu peak=%lu\n",
           (unsigned long) fx_stats.est_calls, (unsigned long) fx_stats.est_nodata, (unsigned long) fx_stats.seq_started,
           (unsigned long) fx_stats.seq_full, (unsigned long) fx_stats.spawned, (unsigned long) fx_stats.full,
           (unsigned long) fx_stats.kind1, (unsigned long) fx_stats.efm, (unsigned long) fx_stats.died,
           (unsigned long) fx_stats.deleted, (unsigned long) fx_stats.no_tex, (unsigned long) fx_stats.peak);
}
