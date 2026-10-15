// game/motion: skeletal animation playback (D:/Bio4/Prog/motion.cpp). A MotionWork plays a
// MotionData (per joint: kind byte, Fcc key type, and per-axis Hermite key streams) on a cModel's
// parts. MotionSetCore starts a motion (optionally through a sequence table of 10.6 fixed-point
// frames with SE/free bytes, with `hokan` frames of blend from the previous pose); MotionMove
// advances it each game frame: root speed applied to the model (Mot_attr bit 0), a second
// blended MotionWork (blend/Brate), the per-parts keys (MotionMoveCore), leg IK, the pose
// interpolation (MotionHokan) and the quaternion blend table. Fcc_get_data_* decode the ten key
// stream layouts (f32 / s16 values and tangents).
#include "motion.h"
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "native_motion.h"
#define MOTION_KEY(w, i) native_keys[i]
#else
#define MOTION_KEY(w, i) w->pHermite_data[i]
#endif
#include "global.h"
#include "db_log.h"
#include "math_sub.h"
#include "main_mem.h"
#include "player.h"
#include "eprintf.h"

extern const Vec vecZero;
extern "C" void* memset(void* dst, int c, unsigned int n);

// Matrix copy written out as loops (the original never calls PSMTXCopy for these).
// Shape matters (all four sites byte-identical only this way): dst pointer first, the row
// counter `i_ = 2` between the two pointers, `for (; i_ != -1; i_--)` (a `while (i_--)` leaves
// the folded `li 2` behind the source pointer), `d_++` before `s_++` (gcse numbers the
// hoisted `+16` pseudos in that order).
#define MTX_COPY(src, dst)               \
    {                                    \
        MtxPtr d_ = (dst);               \
        int i_ = 2;                      \
        MtxPtr s_ = (src);               \
        int j_;                          \
        f32* sp_;                        \
        f32* dp_;                        \
        for (; i_ != -1; i_--) {         \
            dp_ = *d_;                   \
            sp_ = *s_;                   \
            for (j_ = 0; j_ < 4; j_++) { \
                *dp_++ = *sp_++;         \
            }                            \
            d_++;                        \
            s_++;                        \
        }                                \
    }

// Root key history for the current flip state: hist[flip][rot = 0 / pos = 1]
#define MOT_HIST(w, flip, n) ((u16*) ((u8*) (w) + ((flip) * 12 + 8 + (n) * 6)))

// Fixed 10.6 sequence frame -> float
#define SEQ_FRAME(k) ((f32)((k) >> 6) + (f32)((k) & 0x3F) * 0.015625f)

typedef void (*FccGetData)(u8* data, int i0, int i1, f32* val, f32* tan);

extern "C" {
void Fcc_get_data_000(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_001(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_002(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_010(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_011(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_012(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_020(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_021(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_022(u8* d, int i0, int i1, f32* v, f32* t);
void Fcc_get_data_033(u8* d, int i0, int i1, f32* v, f32* t);
void dummy(u8* d, int i0, int i1, f32* v, f32* t);
}

// Moves every parts' world position/matrix by the model's displacement since the last pose
// computation (Pos_world), without recomputing the pose (cheap follow after setPos-style moves).
void PartsWorldPosCalc(cModel* m)
{
    cModel* p;
    Vec d;

    p = m->pParts;
    PSVECSubtract(&m->pos, &MOTION(m)->Pos_world, &d);
    m->mat[0][3] += d.x;
    m->mat[1][3] += d.y;
    m->mat[2][3] += d.z;
    if (PSVECMag(&d) != 0.0f) {
        for (; p != 0; p = p->pParts) {
            PSVECAdd(&p->world, &d, &p->world);
            p->mat[0][3] += d.x;
            p->mat[1][3] += d.y;
            p->mat[2][3] += d.z;
        }
        MOTION(m)->Pos_world = m->pos;
    }
}

// Drops the blended second motion.
void MotionBlendOff(cModel* m)
{
    MOTION(m)->blend = 0;
}

// Pauses the motion (Mot_attr bit 3: the sequence frame stops advancing).
void MotionPause(cModel* m)
{
    MOTION(m)->Mot_attr |= 8;
}

// Removes the motion: every parts back to its bind pose (position from the bind matrices, zero
// rotation, unit scale unless flag bit 0), the attach camera reset, pMot = NULL.
void MotionClear(cModel* m, int flag)
{
    MotionWork* w = MOTION(m);
    cModel* p;
    Mtx tmp;
    Mtx inv;
    int i;
    int j;

    for (p = m->pParts; p != 0; p = p->pParts) {
        if (m != p->pParent) {
            PSMTXInverse(PARTS_BIND_MAT(p), tmp);
            PSMTXConcat(PARTS_BIND_MAT(p->pParent), tmp, inv);
        } else {
            PSMTXInverse(PARTS_BIND_MAT(p), inv);
        }
        p->pos.x = inv[0][3];
        p->pos.y = inv[1][3];
        p->pos.z = inv[2][3];
        p->ang.x = 0.0f;
        p->ang.y = 0.0f;
        p->ang.z = 0.0f;
        if (!(flag & 1)) {
            p->scale.x = 1.0f;
            p->scale.y = 1.0f;
            p->scale.z = 1.0f;
        }
    }
    if (w->pAttachCam != 0) {
        for (i = 0; i < 5; i++) {
            w->pAttachCam->parts[i] = 0xFF;
        }
        w->pAttachCam->type = 0;
        for (j = 0; j < 5; j++) {
            memclr_asm(&w->pAttachCam->out[j], sizeof(Vec));
        }
    }
    MOTION(m)->pMot = 0;
}

// Starts motion `data` on work w (usually MOTION(m)): resets root pos/rot state, Mot_attr = flags
// (bit 0 apply root speed, 1 reverse, 2 loop, 6 flip left/right, ...), the sequence (seq table
// or linear over maxFrame+1 frames) starting at `frame`, the joint tables and key stream
// pointers (relocated once), IK chains (unless Mot_flag 0x10000000), the root pos/rot joint
// indices and attach camera channels, clears the key histories, sets the `hokan` blend frames
// (saving the current l_mat as prevMat), and samples the root at the start/end to get the
// motion's total displacement (Pos_dist/Ang_dist) for looping. Mot_flag 0x20000000 keeps the
// blend motion.
void MotionSetCore(cModel* m, void* w_, void* data_, int seq_, int hokan, int flags, int frame)
{
    MotionWork* w = (MotionWork*) w_;
    MotionData* data = (MotionData*) data_;
    u16* seq = (u16*) seq_;
    HermitePrm prm;
    HermitePrm* pp = &prm;
    u16 hist0[3] = { 0, 0, 0 };
    u16 hist1[3] = { 0, 0, 0 };
    Vec v0;
    Vec v1;
    Vec v2;
    u32* tbl;
    cModel* p;
    AttachCamera* cam;
    int f;
    int i;

    if (!(w->Mot_flag & 0x20000000)) {
        MOTION(m)->blend = 0;
    }
    w->Pos_old = vecZero;
    w->Pos = w->Pos_old;
    w->Pos_dist = vecZero;
    w->Ang_old = vecZero;
    w->Ang = w->Ang_old;
    w->Ang_dist = vecZero;
    w->pMot = data;
    w->Mot_attr = flags;
    w->Mot_state = 0;
    w->Mot_flag = (w->Mot_flag & 0x7FFFFFFF) | 0x04000000;
    if (data == 0) {
        if ((s32) pG->Debug_flg[0] >= 0) {
#line 273
            pLog->err(0, 0, "MotionSetCore():%d pMot == NULL", __LINE__);
        }
        return;
    }
    if (seq == 0) {
        w->pSeq_top = 0;
        w->Seq_frame_num = data->maxFrame & 0x3FFF;
        if (!(flags & 4)) {
            w->Seq_frame_num++;
        }
        if ((u32) frame >= w->Seq_frame_num) {
            frame = (u16) (w->Seq_frame_num - 1);
        }
        w->Seq.Se = 0;
        w->Seq.Free = 0;
        w->Seq_frame = (f32) (u16) frame;
        w->Seq_old.Se = 0;
        w->Seq_old.Free = 0;
        w->Seq_old2.Se = 0;
        w->Seq_old2.Free = 0;
    } else {
        w->pSeq_top = (MotionSeqKey*) (seq + 2);
        w->Seq_frame_num = seq[0];
        if ((u32) frame >= w->Seq_frame_num) {
            frame = (u16) (w->Seq_frame_num - 1);
        }
        w->Seq_frame = (f32) (u16) frame;
        w->Mot_attr = (((u8*) seq)[2] & 1) ? (flags | 0x1000) : (flags & 0xEFFF);
    }
    if (w->pSeq_top == 0) {
        w->Seq.frame = (u16) (w->Seq_frame * 64.0f);
        w->Seq_old.frame = (u16) (w->Seq_frame * 64.0f);
    } else {
        MotionSeqKey k = w->pSeq_top[(u16) w->Seq_frame];

        w->Seq = k;
        w->Seq_old = k;
        w->Seq_old2 = k;
        w->Seq_old2.Se = 0;
        w->Seq_old2.Free = 0;
    }
    w->Mot_frame_max = (f32) w->pMot->maxFrame;
    w->Joint_num = w->pMot->nParts;
    w->pJoint_kind = (u16*) ((u8*) w->pMot + 3);
    w->pJoint_no = (u8*) w->pMot + (w->Joint_num * 2 + 3);
    if (!(w->Mot_flag & 0x10000000)) {
        IKInit(m, w);
    }
    // Two statements: the end pointer lives in `tbl` (r10) before the align (one expression ties the
    // partsNo reload to the sum and allocates it).
    tbl = (u32*) ((u32) w->pJoint_no + w->Joint_num);
    tbl = (u32*) (((u32) tbl + 3) & ~3);
    tbl++;
#if defined(RE4DC_GAME) && !defined(__PPC__)
    u32* native_keys = tbl;
    Re4dcMotionLease keys(data, &native_keys, tbl);
    if (!keys.external())
#endif
    if ((s32) tbl[0] >= 0) {
        for (i = 0; i < w->Joint_num; i++) {
            tbl[i] += (u32) w->pMot;
        }
    }
    w->pHermite_data = tbl;
    w->Null_rot = 0xFFFF;
    w->Null_pos = 0xFFFF;
    if (w->pAttachCam != 0) {
        for (i = 0; i < 5; i++) {
            w->pAttachCam->parts[i] = 0xFF;
        }
        w->pAttachCam->type = 0;
        for (i = 0; i < 5; i++) {
            memclr_asm(&w->pAttachCam->out[i], sizeof(Vec));
        }
    }
    for (i = 0; i < w->Joint_num; i++) {
        u16 info = w->pJoint_kind[i];
        int kind = info & 0xFF;
        int ch = (info >> 8) & 0xF;
        u8 pno;

        if (kind == 1) {
            w->Null_pos = i;
            continue;
        }
        if (kind == 0x40) {
            w->Null_rot = i;
            continue;
        }
        if (w->pAttachCam == 0) {
            continue;
        }
        if (ch != 6 && ch != 7) {
            continue;
        }
        if (w->Mot_attr & 0x100) {
            continue;
        }
        if (ch == 6) {
            w->pAttachCam->type = 1;
        } else if (ch == 7) {
            w->pAttachCam->type = 2;
        }
        pno = w->pJoint_no[i];
        if (kind == 4) {
            if (pno == 0) {
                w->pAttachCam->parts[0] = i;
            } else if (pno == 1) {
                w->pAttachCam->parts[1] = i;
            } else if (pno == 4) {
                w->pAttachCam->parts[4] = i;
            }
        } else if (kind == 2) {
            if (pno == 2) {
                w->pAttachCam->parts[2] = i;
            } else if (pno == 3) {
                w->pAttachCam->parts[3] = i;
            }
        }
    }
    for (p = m->pParts; p != 0; p = p->pParts) {
        if (MOTION_PARTS(p)->flags & 0x04000000) {
            continue;
        }
        memclr_asm(MOTION_PARTS(p)->hist[0], 6);
        memclr_asm(MOTION_PARTS(p)->hist[1], 6);
        memclr_asm(MOTION_PARTS(p)->hist[2], 6);
        memclr_asm(MOTION_PARTS(p)->hist[3], 6);
        memclr_asm(MOTION_PARTS(p)->hist[4], 6);
        memclr_asm(MOTION_PARTS(p)->hist[5], 6);
    }
    w->Key_hist[0][0][0] = w->Key_hist[0][0][1] = w->Key_hist[0][0][2] = 0;
    w->Key_hist[0][1][0] = w->Key_hist[0][1][1] = w->Key_hist[0][1][2] = 0;
    w->Key_hist[1][0][0] = w->Key_hist[1][0][1] = w->Key_hist[1][0][2] = 0;
    w->Key_hist[1][1][0] = w->Key_hist[1][1][1] = w->Key_hist[1][1][2] = 0;
    if (w->pAttachCam != 0) {
        memclr_asm(w->pAttachCam->hist[0], 6);
        memclr_asm(w->pAttachCam->hist[1], 6);
        memclr_asm(w->pAttachCam->hist[2], 6);
        memclr_asm(w->pAttachCam->hist[3], 6);
        memclr_asm(w->pAttachCam->hist[4], 6);
    }
    if (hokan != 0) {
        w->Hokan_frame = hokan;
        w->Hokan_cnt = hokan;
        for (p = m->pParts; p != 0; p = p->pParts) {
            PSMTXCopy(p->l_mat, p->prevMat);
        }
    } else {
        w->Hokan_frame = 0;
        w->Hokan_cnt = 0;
    }
    w->Mot_state = 0;
    if (w->Mot_attr & 2) {
        f = frame + 1;
        if (f >= w->Seq_frame_num) {
            f = w->Seq_frame_num - 1;
        }
    } else {
        f = frame - 1;
        if (f < 0) {
            f = 0;
        }
    }
    u32 zero = 0;
    pp->flags = zero;
    pp->maxFrame = w->Mot_frame_max;
    if (w->Mot_attr & 2) {
        if (!(w->Mot_attr & 0x1000)) {
            asm("" : : "r"(zero));  // COMPILER-DIFF: dead use makes the zero global (r11), w->flags takes r0
            pp->flags = 2;
        }
    } else {
        if (w->Mot_attr & 0x1000) {
            pp->flags = 2;
        } else {
            pp->flags = 0;
        }
    }
    if (w->pSeq_top == 0) {
        w->Mot_frame = (f32) f;
    } else {
        u16 k = w->pSeq_top[f].frame;
        w->Mot_frame = (f32) (k >> 6) + (f32) (k & 0x3F) * 0.0015625f;
    }
    w->Mot_frame_sav = w->Mot_frame;
    w->Mot_frame_old = w->Mot_frame;
    pp->frame = w->Mot_frame;
    if (w->Null_pos != 0xFFFF) {
        pp->type = w->pJoint_kind[w->Null_pos] >> 12;
        pp->key = (u8*) MOTION_KEY(w, w->Null_pos);
        HermiteInterpolation(pp, &w->Pos, hist0);
        w->Pos_old = w->Pos;
    }
    if (w->Null_rot != 0xFFFF) {
        pp->type = w->pJoint_kind[w->Null_rot] >> 12;
        pp->key = (u8*) MOTION_KEY(w, w->Null_rot);
        HermiteInterpolation(pp, &w->Ang, hist1);
        w->Ang_old = w->Ang;
    }
    if (w->Null_pos != 0xFFFF) {
        pp->frame = 0.0f;
        pp->type = w->pJoint_kind[w->Null_pos] >> 12;
        pp->key = (u8*) MOTION_KEY(w, w->Null_pos);
        HermiteInterpolation(pp, &v0, hist0);
        pp->frame = w->Mot_frame_max;
        pp->flags |= 2;
        HermiteInterpolation(pp, &v1, hist0);
        PSVECSubtract(&v1, &v0, &w->Pos_dist);
    }
    if (w->Null_rot != 0xFFFF) {
        pp->frame = 0.0f;
        pp->type = w->pJoint_kind[w->Null_rot] >> 12;
        pp->key = (u8*) MOTION_KEY(w, w->Null_rot);
        HermiteInterpolation(pp, &v0, hist1);
        pp->frame = w->Mot_frame_max;
        pp->flags |= 2;
        HermiteInterpolation(pp, &v1, hist1);
        PSVECSubtract(&v1, &v0, &w->Ang_dist);
        VecRadLimit(&w->Ang_dist);
    }
    cam = w->pAttachCam;
    if (cam != 0) {
        if (cam->type != 0) {
            if (cam->parts[4] != 0xFF) {
                pp->frame = 0.0f;
                pp->type = w->pJoint_kind[cam->parts[4]] >> 12;
                pp->key = (u8*) MOTION_KEY(w, cam->parts[4]);
                HermiteInterpolation(pp, &v2, hist0);
            }
            cam->frame = 0;
            asm volatile("" : : : "memory");  // COMPILER-DIFF: anchor, the type load stays after the frame store
            if (cam->type == 1) {
                cam->pMat = &m->mat;
            } else if (cam->type == 2) {
                MTX_COPY(m->mat, cam->mat);
                cam->pMat = &cam->mat;
            }
        }
        if (w->pAttachCam != 0) {
            if (w->pAttachCam->type != 0) {
                CamCtrl.registAttachCamera(w->pAttachCam, m);
            } else {
                CamCtrl.deleteAttachCamera(w->pAttachCam, m);
            }
        }
    }
}

// One frame of the model's motion: with Mot_attr bit 0 moves the model by the root speed (mixed
// with the blend motion by Brate), evaluates the main motion (MotionMoveCore + sequence step),
// then the blend motion either as a matrix slerp (matBlend) or, for Mot_flag sign-bit blends, as
// an additive pose; runs the leg IK on the unscaled model, the hokan interpolation and the
// quaternion blend table (blendTbl: dst = slerp(c, a, percent)). Returns Mot_state (1/2 looped,
// 4/8 ended).
u16 MotionMove(cModel* m)
{
    static int new_add = 1;
    cModel* p;
    Vec spd;
    Vec rot;
    Vec spd2;
    Vec rot2;
    f32 rate;
    f32 inv;

    if (MOTION(m)->blend != 0) {
        MOTION(m)->blend->Seq_speed = MOTION(m)->Seq_speed;
    }
    if (MOTION(m)->Mot_attr & 1) {
        MotionGetSpeed(m, MOTION(m), 0, &spd, &rot);
        if (MOTION(m)->blend != 0) {
            MOTION(m)->blend->Mot_flag |= 0x08000000;
            rate = MOTION(m)->blend->Brate;
            if (!(MOTION(m)->blend->Mot_flag & 0x80000000)) {
                if (rate != 0.0f) {
                    MOTION(m)->blend->Hokan_cnt = 0;
                    MotionGetSpeed(m, MOTION(m)->blend, 0, &spd2, &rot2);
                    inv = 1.0f - rate;
                    VecLinearCombination(&spd2, &spd, rate, inv, &spd);
                    VecLinearCombination(&rot2, &rot, rate, inv, &rot);
                }
            } else {
                if (rate != 0.0f) {
                    MOTION(m)->blend->Hokan_cnt = 0;
                    MotionGetSpeed(m, MOTION(m)->blend, 0, &spd2, &rot2);
                    VecLinearCombination(&spd2, &spd, rate, 1.0f, &spd);
                    VecLinearCombination(&rot2, &rot, rate, 1.0f, &rot);
                }
            }
        }
        MotionAddSpeed(m, MOTION(m), &spd, &rot);
    }
    MotionMoveCore(m, MOTION(m), 0);
    MotionSequenceCtrl(MOTION(m));
    m->partsMatCalc();
    MOTION(m)->Mot_attr &= ~0x2000;
    if (MOTION(m)->blend != 0) {
        MOTION(m)->blend->Mot_flag |= 0x08000000;
        rate = MOTION(m)->blend->Brate;
        if ((s32) MOTION(m)->blend->Mot_flag >= 0) {
            if (rate != 0.0f) {
                MotionMoveCore(m, MOTION(m)->blend, 0);
                MotionSequenceCtrl(MOTION(m)->blend);
                cModel_matBlend(m, MOTION(m)->blend->Brate);
            } else {
                MotionSequenceCtrl(MOTION(m)->blend);
            }
        } else {
            MOTION(m)->Mot_attr |= 0x2000;
            for (p = m->pParts; p != 0; p = p->pParts) {
                if (MOTION_PARTS(p)->flags & 0x03000000) {
                    continue;
                }
                MOTION_PARTS(p)->pos = p->pos;
                MOTION_PARTS(p)->rot = p->ang;
                MOTION_PARTS(p)->scale = p->scale;
                memclr_asm(&p->ang, sizeof(Vec));
                memclr_asm(&p->pos, sizeof(Vec));
                if (new_add) {
                    memclr_asm(&p->scale, sizeof(Vec));
                }
            }
            MotionMoveCore(m, MOTION(m)->blend, 0);
            MotionSequenceCtrl(MOTION(m)->blend);
            for (p = m->pParts; p != 0; p = p->pParts) {
                if (MOTION_PARTS(p)->flags & 0x03000000) {
                    continue;
                }
                if (new_add) {
                    PSVECAdd(&MOTION_PARTS(p)->pos, &p->pos, &p->pos);
                    PSVECAdd(&MOTION_PARTS(p)->rot, &p->ang, &p->ang);
                    PSVECAdd(&MOTION_PARTS(p)->scale, &p->scale, &p->scale);
                } else {
                    Vec rotAdd;
                    Vec rotScl;
                    Vec posAdd;
                    Vec posScl;

                    PSVECScale(&p->ang, &rotScl, rate);
                    PSVECScale(&p->pos, &posScl, rate);
                    PSVECAdd(&MOTION_PARTS(p)->pos, &posScl, &posAdd);
                    PSVECAdd(&MOTION_PARTS(p)->rot, &rotScl, &rotAdd);
                    p->pos = posAdd;
                    p->ang = rotAdd;
                    RotMatrix(p->l_mat, &p->ang);
                    TransMatrix(p->l_mat, &p->pos);
                    ScaleMatrix(p->l_mat, &p->scale);
                    PSMTXCopy(p->l_mat, p->mat);
                }
            }
            if (new_add) {
                cModel_matBlend(m, MOTION(m)->blend->Brate);
            }
        }
    }
    {
        Mtx tmp;
        Mtx save;

        MTX_COPY(m->mat, save);
        if (m->scale.x != 0.0f || m->scale.y != 0.0f || m->scale.z != 0.0f) {
            PSMTXScale(tmp, 1.0f / m->scale.x, 1.0f / m->scale.y, 1.0f / m->scale.z);
        } else {
            PSMTXIdentity(tmp);
        }
        PSMTXConcat(m->mat, tmp, tmp);
        MTX_COPY(tmp, m->mat);
        m->partsWorldCalc();
        InverseKinematics(m, 1);
        MTX_COPY(save, m->mat);
        m->partsWorldCalc();
    }
    if (MOTION(m)->Hokan_cnt != 0) {
        MotionHokan(m, MOTION(m));
        m->partsWorldCalc();
    }
    if (MOTION(m)->blendTbl != 0) {
        int n = *(s32*) MOTION(m)->blendTbl;
        u16* tbl = MOTION(m)->blendTbl + 2;
        int i;

        {
            Mtx m0;
            Mtx m1;
            Mtx mq;
            Quaternion q0;
            Quaternion q1;
            Quaternion q2;
            Mtx inv;
            cModel* dst;
            cModel* a;
            cModel* c;
            int per;
            f32 r;

            for (i = 0; i < n; i++) {
                dst = m->getPartsPtr(*tbl++);
                a = m->getPartsPtr(*tbl++);
                c = m->getPartsPtr(*tbl++);
                per = *tbl++;
                r = (f32) per / 100.0f;
                if (MOTION_PARTS(dst)->flags & 0x10000) {
                    MOTION_PARTS(dst)->flags &= ~0x10000;
                    continue;
                }
                MOTION_PARTS(dst)->flags &= ~0x10000000;
                PSMTXIdentity(m0);
                m0[0][0] = a->mat[0][0];
                m0[0][1] = a->mat[0][1];
                m0[0][2] = a->mat[0][2];
                m0[1][0] = a->mat[1][0];
                m0[1][1] = a->mat[1][1];
                m0[1][2] = a->mat[1][2];
                m0[2][0] = a->mat[2][0];
                m0[2][1] = a->mat[2][1];
                m0[2][2] = a->mat[2][2];
                C_QUATMtx(&q0, m0);
                PSMTXIdentity(m1);
                m1[0][0] = c->mat[0][0];
                m1[0][1] = c->mat[0][1];
                m1[0][2] = c->mat[0][2];
                m1[1][0] = c->mat[1][0];
                m1[1][1] = c->mat[1][1];
                m1[1][2] = c->mat[1][2];
                m1[2][0] = c->mat[2][0];
                m1[2][1] = c->mat[2][1];
                m1[2][2] = c->mat[2][2];
                C_QUATMtx(&q1, m1);
                C_QUATSlerp(&q1, &q0, &q2, r);
                PSMTXQuat(mq, &q2);
                dst->mat[0][0] = mq[0][0];
                dst->mat[0][1] = mq[0][1];
                dst->mat[0][2] = mq[0][2];
                dst->mat[1][0] = mq[1][0];
                dst->mat[1][1] = mq[1][1];
                dst->mat[1][2] = mq[1][2];
                dst->mat[2][0] = mq[2][0];
                dst->mat[2][1] = mq[2][1];
                dst->mat[2][2] = mq[2][2];
                dst->r_scale.x = c->r_scale.x * (1.0f - r) + a->r_scale.x * r;
                dst->r_scale.y = c->r_scale.y * (1.0f - r) + a->r_scale.y * r;
                dst->r_scale.z = c->r_scale.z * (1.0f - r) + a->r_scale.z * r;
                ScaleMatrix(dst->mat, &dst->r_scale);
                PSMTXInverse(dst->pParent->mat, inv);
                PSMTXConcat(inv, dst->mat, dst->l_mat);
            }
        }
    }
    m->ang.y = LIMIT_ANGLE(m->ang.y);
    return MOTION(m)->Mot_state;
}

// Advances a secondary MotionWork (no root speed): pose, sequence, hokan. Returns its Mot_state.
u16 MotionMoveSub(cModel* m, MotionWork* w)
{
    MotionMoveCore(m, w, 0);
    MotionSequenceCtrl(w);
    if (w->Hokan_cnt != 0) {
        MotionHokan(m, w);
    }
    return w->Mot_state;
}

// Evaluates the pose at the current sequence frame: for each motion joint decodes the Hermite
// keys of the axes it animates (kind bit 1 rotation, else rot + pos + scale) into the parts'
// ang/pos/scale (with the left/right flip remap and mirroring when Mot_attr 0x40), skipping parts
// flagged 0x20000000; attach-camera channels 6/7 go to the AttachCamera outputs. Rebuilds the
// model matrix unless Mot_flag 0x40000000.
void MotionMoveCore(cModel* m, MotionWork* w, int flag)
{
    HermitePrm prm;
    HermitePrm* pp = &prm;
    AttachCamera* cam;
    cModel* p;
    u16* flipTbl = MOTION(m)->flip;
    int n = w->Joint_num;
    int i = 0;
    int flip;

    if (w->pMot == 0) {
        return;
    }
#if defined(RE4DC_GAME) && !defined(__PPC__)
    u32* native_keys = w->pHermite_data;
    Re4dcMotionLease keys(w->pMot, &native_keys, native_keys);
#endif
    if (!(w->Mot_attr & 0x8000)) {
        w->Mot_frame = SEQ_FRAME(w->Seq.frame);
    } else {
        w->Mot_frame = w->Seq_frame;
    }
    w->Mot_frame_old = w->Mot_frame_sav;
    w->Mot_frame_sav = w->Mot_frame;
    pp->frame = w->Mot_frame;
    pp->maxFrame = w->Mot_frame_max;
    pp->flags = 0;
    if (w->Mot_attr & 4) {
        if (w->pSeq_top == 0) {
            pp->flags = 4;
        }
    }
    if (w->Mot_attr & 2) {
        if (!(w->Mot_attr & 0x1000)) {
            pp->flags |= 2;
        } else {
            pp->flags &= ~2;
        }
    } else {
        if (w->Mot_attr & 0x1000) {
            pp->flags |= 2;
        } else {
            pp->flags &= ~2;
        }
    }
    if (!(w->Mot_flag & 0x40000000)) {
        RotMatrix(m->mat, &m->ang);
        TransMatrix(m->mat, &m->pos);
        ScaleMatrix(m->mat, &m->scale);
    }
    flip = 0;
    if (w->Mot_flag & 0x08000000) {
        flip = 1;
    }
    w->Mot_flag &= ~0x04000000;
    cam = 0;
    if (w->pAttachCam != 0 && w->pAttachCam->type != 0) {
        cam = w->pAttachCam;
    }
    if ((w->Mot_attr & 0x40) && flipTbl == 0) {
        w->Mot_attr &= ~0x40;
#line 1067
        pLog->err(0, 0, "MotionMoveCore():%d Flip Info Error!", __LINE__);
    }
    do {
#if defined(RE4DC_HF_PF) && RE4DC_HF_PF
        if (i + 1 < n) {
            __builtin_prefetch((const void*) MOTION_KEY(w, i + 1));   // GAME_HF_PF: the next joint's first key header
        }
#endif
        int kind = w->pJoint_kind[i] & 0xFF;
        u16 info = w->pJoint_kind[i];
        int ch = (info >> 8) & 0xF;
        int pno = w->pJoint_no[i];

        if (ch == 6 || ch == 7) {
            if (cam == 0) {
                continue;
            }
            pp->type = info >> 12;
            pp->key = (u8*) MOTION_KEY(w, i);
            if (i == cam->parts[0]) {
                HermiteInterpolation(pp, &cam->out[0], cam->hist[0]);
                if (w->Mot_attr & 0x40) {
                    cam->out[0].x = -cam->out[0].x;
                }
            } else if (i == cam->parts[1]) {
                HermiteInterpolation(pp, &cam->out[1], cam->hist[1]);
                if (w->Mot_attr & 0x40) {
                    cam->out[1].x = -cam->out[1].x;
                }
            } else if (i == cam->parts[2]) {
                HermiteInterpolation(pp, &cam->out[2], cam->hist[2]);
                if (w->Mot_attr & 0x40) {
                    cam->out[2].y = -cam->out[2].y;
                }
            } else if (i == cam->parts[3]) {
                HermiteInterpolation(pp, &cam->out[3], cam->hist[3]);
            } else if (i == cam->parts[4]) {
                HermiteInterpolation(pp, &cam->out[4], cam->hist[4]);
                cam->frame = (u8) (cam->out[4].y / 100.0f);
            }
            continue;
        }
        if (w->Mot_attr & 0x40) {
            u16 fp = flipTbl[pno];
            if (fp != 0xFFFF) {
                pno = (s16) fp;
            }
        }
        if (pno >= m->nParts) {
            static const char* kind_str[] = { "Em", "Obj", "Scr", "Shadow", "Mirror" };

            if (pPL == m) {
                pLog->err(0, 0, "MotionMoveCore(): Pl, Invalid parts %d.", pno);
            } else {
                pLog->err(0, 0, "MotionMoveCore(): %s[%0xh], Invalid parts %d. [0x%x]", kind_str[m->kindid], m->id, pno, m);
            }
        }
        p = m->getPartsPtr(pno);
        if (p == 0) {
            continue;
        }
        if (MOTION_PARTS(p)->flags & 0x20000000) {
            continue;
        }
        MOTION_PARTS(p)->flags |= 0x10010000;
        if ((s32) w->Mot_flag < 0) {
            MOTION_PARTS(p)->flags |= 0x80000000;
        }
        pp->type = w->pJoint_kind[i] >> 12;
        pp->key = (u8*) MOTION_KEY(w, i);
        if (MOTION_PARTS(p)->flags & 0x04000000) {
            pp->flags |= 8;
        } else {
            pp->flags &= ~8;
        }
        if (kind & 2) {
            HermiteInterpolation(pp, &p->ang, flip ? MOTION_PARTS(p)->hist[3] : MOTION_PARTS(p)->hist[0]);
            VecRadLimit(&p->ang);
            if (w->Mot_attr & 0x40) {
                p->ang.y = -p->ang.y;
                p->ang.z = -p->ang.z;
            }
        } else if (kind & 4) {
            HermiteInterpolation(pp, &p->pos, flip ? MOTION_PARTS(p)->hist[4] : MOTION_PARTS(p)->hist[1]);
            if (w->Mot_attr & 0x40) {
                p->pos.x = -p->pos.x;
            }
        } else if (kind & 8) {
            HermiteInterpolation(pp, &p->scale, flip ? MOTION_PARTS(p)->hist[5] : MOTION_PARTS(p)->hist[2]);
        } else if (kind & 0x30) {
            HermiteInterpolation(pp, &p->ang, flip ? MOTION_PARTS(p)->hist[3] : MOTION_PARTS(p)->hist[0]);
            VecRadLimit(&p->ang);
            if (w->Mot_attr & 0x40) {
                p->ang.y = -p->ang.y;
                p->ang.z = -p->ang.z;
            }
        }
    } while (++i < n);
}

// |d| < eps.
// The caller forms `1.0f - v`: with the subtraction inside the inline body the argument copy
// (a load) precedes the constant load in RTL and sched1 keeps that order (equal prio/weight).
static inline int nearZero(f32 d, f32 eps)
{
    if (fabsf(d) < eps) {
        return 1;
    }
    return 0;
}

// Pose interpolation over the Hokan_frame frames after a motion change: each parts' l_mat is
// blended between prevMat and the new pose (translation linear, rotation by quaternion slerp,
// scale linear or cancelled by the parent's scale with flag 0x20000).
void MotionHokan(cModel* m, MotionWork* w)
{
    static int g_scale_cancel = 1;
    static f32 epsilon = 0.00002f;
    static f32 EPS = 0.1f;
    cModel* p;
    Vec pos;
    Quaternion q0;
    Quaternion q1;
    Quaternion q2;
    Mtx m0;
    Mtx m1;
    Vec c0;
    Vec c1;
    Vec c2;
    f32 t;
    f32 u;
    f32 s0, s1, s2;
    f32 n0, n1, n2;
    f32 sx, sz, sy;

    w->Hokan_cnt--;
    t = (f32) (w->Hokan_frame - w->Hokan_cnt);
    t /= (f32) w->Hokan_frame;
    u = 1.0f - t;
    for (p = m->pParts; p != 0; p = p->pParts) {
        if (!(MOTION(m)->Mot_attr & 0x2000)) {
            if (!(MOTION_PARTS(p)->flags & 0x10000000)) {
                continue;
            }
            MOTION_PARTS(p)->flags &= ~0x10000000;
        } else {
            if ((s32) MOTION_PARTS(p)->flags >= 0) {
                continue;
            }
        }
        pos.x = p->prevMat[0][3] * u + p->l_mat[0][3] * t;
        pos.y = p->prevMat[1][3] * u + p->l_mat[1][3] * t;
        pos.z = p->prevMat[2][3] * u + p->l_mat[2][3] * t;
        c0.x = p->prevMat[0][0];
        c0.y = p->prevMat[1][0];
        c0.z = p->prevMat[2][0];
        c1.x = p->prevMat[0][1];
        c1.y = p->prevMat[1][1];
        c1.z = p->prevMat[2][1];
        c2.x = p->prevMat[0][2];
        c2.y = p->prevMat[1][2];
        c2.z = p->prevMat[2][2];
        s0 = PSVECMag(&c0);
        s1 = PSVECMag(&c1);
        s2 = PSVECMag(&c2);
        if (s0 != 0.0f) {
            PSVECScale(&c0, &c0, 1.0f / s0);
        }
        if (s1 != 0.0f) {
            PSVECScale(&c1, &c1, 1.0f / s1);
        }
        if (s2 != 0.0f) {
            PSVECScale(&c2, &c2, 1.0f / s2);
        }
        m0[0][0] = c0.x;
        m0[1][0] = c0.y;
        m0[2][0] = c0.z;
        m0[0][1] = c1.x;
        m0[1][1] = c1.y;
        m0[2][1] = c1.z;
        m0[0][2] = c2.x;
        m0[1][2] = c2.y;
        m0[2][2] = c2.z;
        c0.x = p->l_mat[0][0];
        c0.y = p->l_mat[1][0];
        c0.z = p->l_mat[2][0];
        c1.x = p->l_mat[0][1];
        c1.y = p->l_mat[1][1];
        c1.z = p->l_mat[2][1];
        c2.x = p->l_mat[0][2];
        c2.y = p->l_mat[1][2];
        c2.z = p->l_mat[2][2];
        n0 = PSVECMag(&c0);
        n1 = PSVECMag(&c1);
        n2 = PSVECMag(&c2);
        if (n0 != 0.0f) {
            PSVECScale(&c0, &c0, 1.0f / n0);
        }
        if (n1 != 0.0f) {
            PSVECScale(&c1, &c1, 1.0f / n1);
        }
        if (n2 != 0.0f) {
            PSVECScale(&c2, &c2, 1.0f / n2);
        }
        m1[0][0] = c0.x;
        m1[1][0] = c0.y;
        m1[2][0] = c0.z;
        m1[0][1] = c1.x;
        m1[1][1] = c1.y;
        m1[2][1] = c1.z;
        m1[0][2] = c2.x;
        m1[1][2] = c2.y;
        m1[2][2] = c2.z;
        C_QUATMtx(&q0, m0);
        C_QUATMtx(&q1, m1);
        C_QUATSlerp(&q0, &q1, &q2, t);
        PSMTXQuat(p->l_mat, &q2);
        if (g_scale_cancel) {
            // `one` is loaded before the first scale load (the target's constant load comes first).
            f32 one = 1.0f;
            if (!(nearZero(one - p->scale.x, epsilon) && nearZero(one - p->scale.y, epsilon) && nearZero(one - p->scale.z, epsilon))) {
                if (nearZero(1.0f - p->pParent->r_scale.x * p->scale.x, EPS) && nearZero(1.0f - p->pParent->r_scale.y * p->scale.y, EPS) &&
                    nearZero(1.0f - p->pParent->r_scale.z * p->scale.z, EPS)) {
                    MOTION_PARTS(p)->flags |= 0x20000;
                }
            }
        } else {
            MOTION_PARTS(p)->flags &= ~0x20000;
        }
        if (MOTION_PARTS(p)->flags & 0x20000) {
            // Source order x, y, z: sched1 issues first the load where the pParent pointer dies (the last one).
            sx = 1.0f / p->pParent->scale.x;
            sy = 1.0f / p->pParent->scale.y;
            sz = 1.0f / p->pParent->scale.z;
        } else {
            sx = s0 * u + n0 * t;
            sy = s1 * u + n1 * t;
            sz = s2 * u + n2 * t;
        }
        // Before the products: the store is ready early and wins the LSU slot on LUID (equal priority).
        MOTION_PARTS(p)->flags &= ~0x20000;
        p->l_mat[0][0] *= sx;
        p->l_mat[1][0] *= sx;
        p->l_mat[2][0] *= sx;
        p->l_mat[0][1] *= sy;
        p->l_mat[1][1] *= sy;
        p->l_mat[2][1] *= sy;
        p->l_mat[0][2] *= sz;
        p->l_mat[1][2] *= sz;
        p->l_mat[2][2] *= sz;
        p->r_scale = p->scale;
        p->scale.x = sx;
        p->scale.y = sy;
        p->scale.z = sz;
        TransMatrix(p->l_mat, &pos);
        {
            MtxPtr pm;
            asm("" : "=r"(pm) : "0"(p->prevMat));  // COMPILER-DIFF: launder, the extra insn on the r4 path ranks both addi r4 above mr r3
            PSMTXCopy(p->l_mat, pm);
        }
    }
}

// Root displacement of this frame: samples the root pos/rot joints at the current frame, subtracts
// the previous sample (adding/subtracting Pos_dist/Ang_dist across a loop), rotates the position
// delta by the previous root yaw into model space, mirrors it for flipped motions, and with
// Mot_attr 0x400 blends the XZ speed from the previous motion's speed over the hokan frames.
void MotionGetSpeed(cModel* m, MotionWork* w, int flag, Vec* pos, Vec* rot)
{
    HermitePrm prm;
    HermitePrm* pp = &prm;
    Vec a = { 0.0f, 0.0f, 0.0f };
    Vec b = { 0.0f, 0.0f, 0.0f };
    Mtx rm;
    int flip;

#if defined(RE4DC_GAME) && !defined(__PPC__)
    u32* native_keys = w->pHermite_data;
    Re4dcMotionLease keys(w->pMot, &native_keys, native_keys);
#endif
    w->Mot_frame = SEQ_FRAME(w->Seq.frame);
    pp->flags = 0;
    w->Ang_old = w->Ang;
    w->Pos_old = w->Pos;
    if (w->Mot_attr & 2) {
        if (w->Mot_attr & 0x1000) {
            pp->flags = 0;
        } else {
            pp->flags = 2;
        }
    } else {
        if (w->Mot_attr & 0x1000) {
            pp->flags = 2;
        } else {
            pp->flags = 0;
        }
    }
    flip = 0;
    if (w->Mot_flag & 0x08000000) {
        flip = 1;
    }
    if (w->Null_pos != 0xFFFF) {
        pp->frame = w->Mot_frame;
        pp->maxFrame = w->Mot_frame_max;
        pp->key = (u8*) MOTION_KEY(w, w->Null_pos);
        pp->type = w->pJoint_kind[w->Null_pos] >> 12;
        HermiteInterpolation(pp, &a, MOT_HIST(w, flip, 1));
    }
    if (w->Null_rot != 0xFFFF) {
        pp->frame = w->Mot_frame;
        pp->maxFrame = w->Mot_frame_max;
        pp->key = (u8*) MOTION_KEY(w, w->Null_rot);
        pp->type = w->pJoint_kind[w->Null_rot] >> 12;
        HermiteInterpolation(pp, &b, MOT_HIST(w, flip, 0));
    }
    PSVECSubtract(&b, &w->Ang_old, rot);
    PSVECSubtract(&a, &w->Pos_old, pos);
    if (w->Mot_state & 1) {
        PSVECAdd(pos, &w->Pos_dist, pos);
        PSVECAdd(rot, &w->Ang_dist, rot);
    } else if (w->Mot_state & 2) {
        PSVECSubtract(pos, &w->Pos_dist, pos);
        PSVECSubtract(rot, &w->Ang_dist, rot);
    }
    PSMTXRotRad(rm, 'y', w->Ang_old.y);
    rm[0][2] = -rm[0][2];
    rm[2][0] = -rm[2][0];
    PSMTXMultVecSR(rm, pos, pos);
    if (w->Mot_attr & 0x40) {
        if (MOTION(m)->flip == 0) {
            w->Mot_attr &= ~0x40;
#line 1642
            pLog->err(0, 0, "MotionMoveCore():%d Flip Info Error!", __LINE__);
        } else {
            rot->y = -rot->y;
            rot->z = -rot->z;
            pos->x = -pos->x;
        }
    }
    if (w->Mot_attr & 0x400) {
        int cnt = w->Hokan_cnt;

        if (cnt - 1 > 0) {
            int mx = w->Hokan_frame + 1;
            f32 t = (f32) (mx - cnt) / (f32) w->Hokan_frame;
            f32 u = 1.0f - t;
            pos->x = w->Pos_move_old.x * u + pos->x * t;
            pos->z = w->Pos_move_old.z * u + pos->z * t;
        }
    }
    if (!(flag & 8)) {
        w->Pos_move_old = *pos;
        w->Ang = b;
        w->Pos = a;
    }
}

// Applies a root delta to the model: position rotated by the model matrix, rotation added.
void MotionAddSpeed(cModel* m, MotionWork* w, Vec* pos, Vec* rot)
{
    Vec t;

    PSMTXMultVecSR(m->mat, pos, &t);
    PSVECAdd(&m->pos, &t, &m->pos);
    PSVECAdd(&m->ang, rot, &m->ang);
}

// Root position/rotation keys at the previous sequence frame (Seq_old), without touching the state.
void MotionGetPosition(cModel* m, Vec* pos, Vec* rot)
{
    MotionWork* w = MOTION(m);
    HermitePrm prm;
    HermitePrm* pp;
    int flip;

#if defined(RE4DC_GAME) && !defined(__PPC__)
    u32* native_keys = w->pHermite_data;
    Re4dcMotionLease keys(w->pMot, &native_keys, native_keys);
#endif
    pos->x = pos->y = pos->z = 0.0f;
    rot->x = rot->y = rot->z = 0.0f;
    w->Mot_frame = SEQ_FRAME(w->Seq_old.frame);
    pp = &prm;
    pp->flags = 0;
    asm("" : : "r"(pp));  // COMPILER-DIFF: pp must outrank w for r31
    if (w->Mot_attr & 2) {
        if (!(w->Mot_attr & 0x1000)) {
            pp->flags = 2;
        }
    } else {
        if (w->Mot_attr & 0x1000) {
            pp->flags = 2;
        } else {
            pp->flags = 0;
        }
    }
    flip = 0;
    if (w->Mot_flag & 0x08000000) {
        flip = 1;
    }
    if (w->Null_pos != 0xFFFF) {
        pp->frame = w->Mot_frame;
        pp->maxFrame = w->Mot_frame_max;
        pp->key = (u8*) MOTION_KEY(w, w->Null_pos);
        pp->type = w->pJoint_kind[w->Null_pos] >> 12;
        HermiteInterpolation(pp, pos, MOT_HIST(w, flip, 1));
    }
    if (w->Null_rot != 0xFFFF) {
        pp->frame = w->Mot_frame;
        pp->maxFrame = w->Mot_frame_max;
        pp->key = (u8*) MOTION_KEY(w, w->Null_rot);
        pp->type = w->pJoint_kind[w->Null_rot] >> 12;
        HermiteInterpolation(pp, rot, MOT_HIST(w, flip, 0));
    }
}

// Advances the sequence frame by Seq_speed * pG->mot_speed per frame (unless paused): forward or
// reverse (Mot_attr bit 1), looping (bit 2: Mot_state 1/2) or clamping at the end (Mot_state
// 4/8); then resolves the motion frame (10.6 fixed) from the sequence table with interpolation
// between table entries, or linearly. Returns Mot_state.
u16 MotionSequenceCtrl(MotionWork* w)
{
    f32 f;

    w->Seq_old2 = w->Seq_old;
    if (!(w->Mot_attr & 8)) {
        w->Mot_state = 0;
        if (w->Mot_attr & 2) {
            if (w->Mot_attr & 4) {
                if (w->Seq_frame <= 0.0f) {
                    w->Mot_state = 2;
                    f = w->Seq_frame + (f32) (int) w->Seq_frame_num;
                } else {
                    f = w->Seq_frame - w->Seq_speed * pG->mot_speed;
                }
                w->Seq_frame = f;
            } else {
                if (w->Seq_frame <= 0.0f) {
                    w->Mot_state = 8;
                    w->Seq_frame = 0.0f;
                } else {
                    f = w->Seq_frame - w->Seq_speed * pG->mot_speed;
                    w->Seq_frame = f;
                }
            }
        } else {
            w->Seq_frame = w->Seq_frame + w->Seq_speed * pG->mot_speed;
            if (w->Mot_attr & 4) {
                u16 max = w->Seq_frame_num;

                if (w->Seq_frame >= (f32) max) {
                    w->Mot_state = 1;
                    w->Seq_frame = w->Seq_frame - (f32) (int) max;
                }
            } else {
                u16 max = w->Seq_frame_num;

                if (w->Seq_frame >= (f32) max) {
                    w->Mot_state = 4;
                    w->Seq_frame = (f32) (max - 1);
                }
            }
        }
        w->Seq_old = w->Seq;
        if (w->pSeq_top == 0) {
            w->Seq.frame = (u16) (w->Seq_frame * 64.0f);
        } else {
            // One `sf` variable carries seqFrame, the fraction (`sf -= (f32)(int)fi`) and the
            // else-arm product (`sf *=`): 9 refs rank it above mf and the 0x43300000 double.
            f32 sf = w->Seq_frame;
            u16 fi = (u16) sf;

            w->Seq = w->pSeq_top[fi];
            if ((f32) fi != sf) {
                u16 nx = (u16) (sf + 1.0f);

                sf -= (f32) (int) fi;
                if (nx >= w->Seq_frame_num) {
                    f32 mf = w->Mot_frame_max * 64.0f;

                    if (mf == (f32) (int) w->pSeq_top[fi].frame) {
                        w->Seq.frame = (u16) (sf * 64.0f);
                    } else if (w->pSeq_top[0].frame == 0) {
                        w->Seq.frame = w->pSeq_top[fi].frame + (u16) (sf * (mf - (f32) (int) w->pSeq_top[fi].frame));
                    }
                } else {
                    sf *= (f32) (w->pSeq_top[nx].frame - w->pSeq_top[fi].frame);
                    w->Seq.frame = w->pSeq_top[fi].frame + (u16) sf;
                }
            }
            if ((f32) (int) w->Seq.frame > w->Mot_frame_max * 64.0f) {
                pLog->err(0, 0, "MotSeqCtrl(@0x%08x): %.2f Invalid Seq. Frame", w, (f32) (int) w->Seq.frame * 0.015625f);
            }
        }
    } else {
        w->Seq_old = w->Seq;
        w->Seq.Se = 0;
        w->Mot_state &= 0xFFF0;
    }
    return w->Mot_state;
}

// Frame count word of an FCV (camera curve) block.
u16 FcvGetMaxFrame(u16* data)
{
    return data[0];
}

// Last frame of the motion (-1 without motion).
f32 MotionGetMaxFrame(MotionWork* w)
{
    if (w->pMot == 0) {
        return -1.0f;
    }
    return w->Mot_frame_max;
}

// Current motion frame (-1 without motion).
f32 MotionGetCurrentFrame(MotionWork* w)
{
    if (w->pMot == 0) {
        return -1.0f;
    }
    return w->Mot_frame;
}

// 1 when the motion passed `frame` since the previous update (handles loops); 0 on the first
// frame after a set (Mot_flag 0x04000000). Used to trigger footsteps/attacks at key frames.
int MotionCheckCrossFrame(MotionWork* w, f32 frame)
{
    f32 cur;
    f32 prev;

    if (w->pMot == 0) {
        return 0;
    }
    if (w->Mot_flag & 0x04000000) {
        return 0;
    }
    cur = w->Mot_frame;
    prev = w->Mot_frame_old;
    if (frame == 0.0f && cur == 0.0f && prev == 0.0f) {
        return 1;
    }
    if (cur >= prev) {
        if (frame <= cur && frame > prev) {
            return 1;
        }
        return 0;
    }
    if (frame > prev || frame <= cur) {
        return 1;
    }
    return 0;
}

// Mot_state of the model's motion, -1 when none is set.
int MotionGetState(cModel* m)
{
    MotionWork* w = MOTION(m);

    if (w->pMot == 0) {
        return -1;
    }
    return w->Mot_state;
}

// Evaluates one joint's three axis key streams at prm->frame: finds the key pair around the frame
// starting from the per-axis history index (hist, updated unless flags bit 3), wraps for looping
// motions (flags 4), holds the last key past the end, and Hermite-interpolates value/tangent pairs
// decoded by Fcc_get_data_tbl[prm->type]. Returns 1 when a history index was invalid.
#if defined(RE4DC_HERMITE_FAST) && RE4DC_HERMITE_FAST
// GAME_HERMITE_FAST: the body below is the reference (HermiteInterpolation_ref); the public entry point
// after it is the restructured twin.
#define HermiteInterpolation HermiteInterpolation_ref
#endif
int HermiteInterpolation(HermitePrm* prm, Vec* out, u16* hist)
{
    static FccGetData Fcc_get_data_tbl[16] = {
        Fcc_get_data_000, Fcc_get_data_001, Fcc_get_data_002, dummy,
        Fcc_get_data_010, Fcc_get_data_011, Fcc_get_data_012, dummy,
        Fcc_get_data_020, Fcc_get_data_021, Fcc_get_data_022, dummy,
        dummy,            dummy,            dummy,            Fcc_get_data_033,
    };
    f32 r = 0.0f;
    f32 frame = prm->frame;
    u8* p = prm->key;
    f32* o = (f32*) out;
    u16* hp = hist - 1;
    f32 f0 = r;
    f32 f1 = r;
    int ret = 0;
    int axis = 0;
    u16_un* frames;
    u8* data;
    f32 val[2];
    f32 tan[2];
    int n;
    int last = 0;
    int idx;
    int cnt;
    int found;

    for (; axis <= 2; axis++) {
        n = *(u16_un*) p;
        frames = (u16_un*) (p + 2);
        data = p + n * 2 + 2;
        hp++;
        p = data + Fcc_next_axis_addr(prm->type, n);
        cnt = n;
        found = 0;
        if (prm->maxFrame <= frame) {
            if ((prm->flags & 6) == 4) {
                frame -= prm->maxFrame;
                if (!(prm->flags & 8)) {
                    *hp = 0;
                }
            } else {
                Fcc_get_data_tbl[prm->type](data, n - 1, 0, val, tan);
                cnt = 0;
                found = 1;
                r = val[0];
            }
        }
        if (!(prm->flags & 8)) {
            idx = *hp;
        } else {
            idx = 0;
        }
        {
            // The target keeps `n - 1` in a local (r0) and copies it to `last` BEFORE the compare
            // (gcse's pre_insert_copies shape); a plain copy is coalesced by regmove. The r0 pin plus
            // the codeless use in the error arm keep m live past the compare, so combine cannot fold
            // the copy and regmove's forward scan stops at the branch (COMPILER-DIFF: gcse copy kept).
            register int m PPC_REG("r0") = n - 1;
            last = m;
            asm("" : : "r"(last));                    // COMPILER-DIFF: last must outrank n for r30
            if (idx > m) {
                asm("" : : "r"(m));                   // COMPILER-DIFF: keep-alive for the r0 temp
                pLog->err(0, 0, "H.I.(): axis=%d, hist=%d nFrm=%d, Invalid key history.", axis, idx, n);
                idx = 0;
                ret = 1;
            }
        }
        if (cnt != 0) {
            asm("" : "+r"(idx));  // COMPILER-DIFF: the table lis is issued before the fp init
            u16_un* fp = (u16_un*) (idx * 2 + (u32) frames);

            do {
                f0 = (f32) *fp;
                if (f0 == frame) {
                    Fcc_get_data_tbl[prm->type](data, idx, 0, val, tan);
                    r = val[0];
                    if (!(prm->flags & 8)) {
                        *hp = idx;
                    }
                    found = 1;
                    break;
                }
                if (f0 < frame) {
                    int nx = idx + 1;

                    if (nx > last) {
                        nx = 0;
                    }
                    f1 = (f32) frames[nx];
                    if (frame < f1) {
                        Fcc_get_data_tbl[prm->type](data, idx, nx, val, tan);
                        if (!(prm->flags & 8)) {
                            *hp = idx;
                        }
                        break;
                    }
                }
                if ((prm->flags & 1) || f0 > frame) {
                    fp--;
                    idx--;
                    if (idx < 0) {
                        fp = (u16*) (last * 2 + (u32) frames);
                        idx = last;
                    }
                } else {
                    idx++;
                    fp++;
                    if (idx > last) {
                        fp = frames;
                        idx = 0;
                    }
                }
            } while (--cnt);
        }
        if (!found) {
            r = hermite(val, tan, (frame - f0) / (f1 - f0));
        }
        o[axis] = r;
    }
    return ret;
}
#if defined(RE4DC_HERMITE_FAST) && RE4DC_HERMITE_FAST
#undef HermiteInterpolation
// GAME_HERMITE_FAST (game30.mk; the 30 fps rethink, step 2): HermiteInterpolation_ref restructured,
// exact. Same search, history reads / writes, error log and return value; f0, f1, val and tan persist
// across the three axes exactly as there (a stale pair feeds the blend when a search runs out). Only the
// mechanics change:
//   - the key layouts 5 (s16 / s16), 0 (f32 / f32), 6 (s16 / s8) and 10 (s8 / s8) decode inline with the
//     Fcc_get_data_* conversions: FCC_S16 composes the little-endian s16 at d[i] (= an aligned s16 load
//     when d[i] is even), FCC_F32 the little-endian word (two halfwords when 2-aligned), FCC_S8 the byte;
//     each times 0.0001f where the original scales. Odd addresses and the other layouts call the table;
//   - hermite's expression inline (the same operations in the same order, GAME_FP_CONTRACT=off);
//   - Fcc_next_axis_addr from a stride table (-1 for the unused layouts, as there).
namespace {
FccGetData const hfTbl[16] = {
    Fcc_get_data_000, Fcc_get_data_001, Fcc_get_data_002, dummy,
    Fcc_get_data_010, Fcc_get_data_011, Fcc_get_data_012, dummy,
    Fcc_get_data_020, Fcc_get_data_021, Fcc_get_data_022, dummy,
    dummy,            dummy,            dummy,            Fcc_get_data_033,
};
const s8 hfStride[16] = {12, 8, 6, -1, 10, 6, 4, -1, 9, 5, 3, -1, -1, -1, -1, 4};
inline f32 hfS16(const u8* d)
{
    return (f32) * (const s16*) d * 0.0001f;
}
inline f32 hfS8(const u8* d)
{
    return (f32) (s8) d[0] * 0.0001f;
}
inline f32 hfF32(const u8* d)
{
    const u32 w = (u32) ((const u16*) d)[0] | ((u32) ((const u16*) d)[1] << 16);
    f32 f;
    __builtin_memcpy(&f, &w, 4);
    return f;
}
// GAME_HF_INLINE (game30.mk; lane gskel; exact): hfGet inline at its three sites (GCC kept it out of
// line: ~1,000 calls per square tick through the stack-resident val / tan arrays).
#if defined(RE4DC_HF_INLINE) && RE4DC_HF_INLINE
__attribute__((always_inline))
#endif
inline void hfGet(int type, u8* d, int i0, int i1, f32* v, f32* t)
{
    if (!((u32) d & 1)) {
        switch (type) {
        case 5:
            v[0] = hfS16(d + i0 * 6);
            v[1] = hfS16(d + i1 * 6);
            t[0] = hfS16(d + i0 * 6 + 4);
            t[1] = hfS16(d + i1 * 6 + 2);
            return;
        case 0:
            v[0] = hfF32(d + i0 * 12);
            v[1] = hfF32(d + i1 * 12);
            t[0] = hfF32(d + i0 * 12 + 8);
            t[1] = hfF32(d + i1 * 12 + 4);
            return;
        case 6:
            v[0] = hfS16(d + i0 * 4);
            v[1] = hfS16(d + i1 * 4);
            t[0] = hfS8(d + i0 * 4 + 3);
            t[1] = hfS8(d + i1 * 4 + 2);
            return;
        default:
            break;
        }
    }
    if (type == 10) {
        v[0] = hfS8(d + i0 * 3);
        v[1] = hfS8(d + i1 * 3);
        t[0] = hfS8(d + i0 * 3 + 2);
        t[1] = hfS8(d + i1 * 3 + 1);
        return;
    }
    hfTbl[type](d, i0, i1, v, t);
}
inline f32 hfHermite(const f32* p, const f32* v, f32 t)
{
    f32 t2 = t * t;
    f32 t3 = t * t2;
    f32 h01 = -(t3 + t3) + 3.0f * t2;
    f32 h11 = t3 - t2;
    f32 h10 = h11 - t2 + t;
    f32 h00 = -h01 + 1.0f;

    return p[0] * h00 + p[1] * h01 + v[0] * h10 + v[1] * h11;
}
int hermiteFast(HermitePrm* prm, Vec* out, u16* hist)
{
    f32 r = 0.0f;
    f32 frame = prm->frame;
    const f32 maxFrame = prm->maxFrame;
    const u32 flags = prm->flags;
    const int type = prm->type;
    const int stride = hfStride[type];
    u8* p = prm->key;
    f32* o = (f32*) out;
    u16* hp = hist - 1;
    f32 f0 = r;
    f32 f1 = r;
    int ret = 0;
    f32 val[2];
    f32 tan[2];

    for (int axis = 0; axis <= 2; axis++) {
        const int n = *(const u16_un*) p;
        const u16_un* frames = (const u16_un*) (p + 2);
        u8* data = p + n * 2 + 2;
        hp++;
        p = data + (stride < 0 ? -1 : n * stride);
#if defined(RE4DC_HF_PF) && RE4DC_HF_PF
        if (axis < 2 && stride >= 0) {
            __builtin_prefetch(p);   // GAME_HF_PF: the next axis' header (its demand load missed on nearly every axis)
        }
#endif
        int cnt = n;
        int found = 0;
        if (maxFrame <= frame) {
            if ((flags & 6) == 4) {
                frame -= maxFrame;
                if (!(flags & 8)) {
                    *hp = 0;
                }
            } else {
                hfGet(type, data, n - 1, 0, val, tan);
                cnt = 0;
                found = 1;
                r = val[0];
            }
        }
        int idx = !(flags & 8) ? *hp : 0;
        const int last = n - 1;
        if (idx > last) {
            pLog->err(0, 0, "H.I.(): axis=%d, hist=%d nFrm=%d, Invalid key history.", axis, idx, n);
            idx = 0;
            ret = 1;
        }
        if (cnt != 0) {
            const u16_un* fp = frames + idx;
            do {
                f0 = (f32) *fp;
                if (f0 == frame) {
                    hfGet(type, data, idx, 0, val, tan);
                    r = val[0];
                    if (!(flags & 8)) {
                        *hp = idx;
                    }
                    found = 1;
                    break;
                }
                if (f0 < frame) {
                    int nx = idx + 1;
                    if (nx > last) {
                        nx = 0;
                    }
                    f1 = (f32) frames[nx];
                    if (frame < f1) {
                        hfGet(type, data, idx, nx, val, tan);
                        if (!(flags & 8)) {
                            *hp = idx;
                        }
                        break;
                    }
                }
                if ((flags & 1) || f0 > frame) {
                    fp--;
                    idx--;
                    if (idx < 0) {
                        fp = frames + last;
                        idx = last;
                    }
                } else {
                    idx++;
                    fp++;
                    if (idx > last) {
                        fp = frames;
                        idx = 0;
                    }
                }
            } while (--cnt);
        }
        if (!found) {
            r = hfHermite(val, tan, (frame - f0) / (f1 - f0));
        }
        o[axis] = r;
    }
    return ret;
}

#if defined(RE4DC_HF_REG) && RE4DC_HF_REG
#if defined(RE4DC_HF_ASM) && RE4DC_HF_ASM
#error GAME_HF_REG and GAME_HF_ASM both replace hermiteSelected
#endif
// GAME_HF_REG (game30.mk; lane logic 2026-10-04; exact): hermiteFast once per common key layout (5, 0, 6:
// 95% of the calls) at an even key address, where every axis header, frame array and value field is
// 2-aligned (strides 6 / 12 / 4 keep the evenness): the frame and count halfwords are plain aligned loads
// (hermiteFast composes them byte by byte: u16_un), the stride is a constant (no mul.l), and the value /
// tangent pair lives in registers instead of the stack arrays the table fallback needs. The search, the
// history reads / writes, the clamp / loop handling, the decode conversions (hfS16 / hfS8 / hfF32: the same
// loads and the same * 0.0001f) and hfHermite's expression are hermiteFast's, in the same order; f0 / f1 /
// the pair persist across the three axes as there. The two rare cases that need hermiteFast's own state
// (an invalid history index: its error log and return value 1; a search that runs out: the blend of a stale,
// possibly uninitialised pair) put the three history words back and hand the whole call to hermiteFast,
// which recomputes the earlier axes from the same inputs (a pure function of prm, the history and the key
// data): no call inside the loop, so the pair stays in caller-saved registers. Odd keys and the other
// layouts take hermiteFast. =2 (check build): hermiteFast runs first on a copy of the history and every
// output word, history slot and return value is compared ("HFR" lines; bails counted).
template <int T>
struct HfLayout;
template <>
struct HfLayout<5> {
    enum { S = 6 };
    static f32 v(const u8* d, int i) { return hfS16(d + i * 6); }
    static f32 t0(const u8* d, int i) { return hfS16(d + i * 6 + 4); }
    static f32 t1(const u8* d, int i) { return hfS16(d + i * 6 + 2); }
};
template <>
struct HfLayout<0> {
    enum { S = 12 };
    static f32 v(const u8* d, int i) { return hfF32(d + i * 12); }
    static f32 t0(const u8* d, int i) { return hfF32(d + i * 12 + 8); }
    static f32 t1(const u8* d, int i) { return hfF32(d + i * 12 + 4); }
};
template <>
struct HfLayout<6> {
    enum { S = 4 };
    static f32 v(const u8* d, int i) { return hfS16(d + i * 4); }
    static f32 t0(const u8* d, int i) { return hfS8(d + i * 4 + 3); }
    static f32 t1(const u8* d, int i) { return hfS8(d + i * 4 + 2); }
};
#if RE4DC_HF_REG == 2
extern "C" void re4dc_log(const char*, ...);
u32 hfrCalls, hfrFast, hfrBail, hfrMisOut, hfrMisHist, hfrMisRet;
#endif
template <int T>
__attribute__((noinline)) int hfReg(HermitePrm* prm, Vec* out, u16* hist)
{
    typedef HfLayout<T> L;
    f32 frame = prm->frame;
    const f32 maxFrame = prm->maxFrame;
    const u32 flags = prm->flags;
    const u8* p = prm->key;
    f32* o = (f32*) out;
    f32 r = 0.0f;
    f32 f0 = r;
    f32 f1 = r;
    f32 v0, v1, t0, t1;   // hermiteFast's val[0], val[1], tan[0], tan[1]
    const u16 hs0 = hist[0], hs1 = hist[1], hs2 = hist[2];   // put back when the call goes to hermiteFast

    for (int axis = 0; axis <= 2; axis++) {
        const int n = *(const u16*) p;
        const u16* frames = (const u16*) p + 1;
        const u8* data = (const u8*) (frames + n);
        u16* hp = hist + axis;
        p = data + n * L::S;
#if defined(RE4DC_HF_PF) && RE4DC_HF_PF
        if (axis < 2) {
            __builtin_prefetch(p);   // as GAME_HF_PF in hermiteFast: the next axis' header
        }
#endif
        int cnt = n;
        int found = 0;
        if (maxFrame <= frame) {
            if ((flags & 6) == 4) {
                frame -= maxFrame;
                if (!(flags & 8)) {
                    *hp = 0;
                }
            } else {
                v0 = L::v(data, n - 1);
                v1 = L::v(data, 0);
                t0 = L::t0(data, n - 1);
                t1 = L::t1(data, 0);
                cnt = 0;
                found = 1;
                r = v0;
            }
        }
        int idx = !(flags & 8) ? *hp : 0;
        const int last = n - 1;
        if (idx > last) {
            goto bail;   // hermiteFast logs it, restarts the axis at 0 and returns 1
        }
        if (cnt != 0) {
            const u16* fp = frames + idx;
            do {
                f0 = (f32) *fp;
                if (f0 == frame) {
                    v0 = L::v(data, idx);
                    v1 = L::v(data, 0);
                    t0 = L::t0(data, idx);
                    t1 = L::t1(data, 0);
                    r = v0;
                    if (!(flags & 8)) {
                        *hp = idx;
                    }
                    found = 1;
                    break;
                }
                if (f0 < frame) {
                    int nx = idx + 1;
                    if (nx > last) {
                        nx = 0;
                    }
                    f1 = (f32) frames[nx];
                    if (frame < f1) {
                        v0 = L::v(data, idx);
                        v1 = L::v(data, nx);
                        t0 = L::t0(data, idx);
                        t1 = L::t1(data, nx);
                        if (!(flags & 8)) {
                            *hp = idx;
                        }
                        break;
                    }
                }
                if ((flags & 1) || f0 > frame) {
                    fp--;
                    idx--;
                    if (idx < 0) {
                        fp = frames + last;
                        idx = last;
                    }
                } else {
                    idx++;
                    fp++;
                    if (idx > last) {
                        fp = frames;
                        idx = 0;
                    }
                }
                if (--cnt == 0) {
                    goto bail;   // ran out: hermiteFast blends its stale pair
                }
            } while (true);
        }
        if (!found) {
            const f32 t = (frame - f0) / (f1 - f0);
            const f32 tt2 = t * t;
            const f32 tt3 = t * tt2;
            const f32 h01 = -(tt3 + tt3) + 3.0f * tt2;
            const f32 h11 = tt3 - tt2;
            const f32 h10 = h11 - tt2 + t;
            const f32 h00 = -h01 + 1.0f;

            r = v0 * h00 + v1 * h01 + t0 * h10 + t1 * h11;   // hfHermite(val, tan, t)
        }
        o[axis] = r;
    }
    return 0;
bail:
#if RE4DC_HF_REG == 2
    hfrBail++;
#endif
    hist[0] = hs0;
    hist[1] = hs1;
    hist[2] = hs2;
    return hermiteFast(prm, out, hist);
}
int hermiteReg(HermitePrm* prm, Vec* out, u16* hist)
{
#if RE4DC_HF_REG == 2
    const u16 h0[3] = {hist[0], hist[1], hist[2]};
    Vec ro;
    const int rr = hermiteFast(prm, &ro, hist);
    const u16 rh[3] = {hist[0], hist[1], hist[2]};
    hist[0] = h0[0];
    hist[1] = h0[1];
    hist[2] = h0[2];
    int fr;
    if (!((u32) prm->key & 1) && (prm->type == 5 || prm->type == 0 || prm->type == 6)) {
        hfrFast++;
    }
#define HFR_RET(x) fr = (x); goto check
#else
#define HFR_RET(x) return (x)
#endif
    if (!((u32) prm->key & 1)) {
        switch (prm->type) {
        case 5:
            HFR_RET(hfReg<5>(prm, out, hist));
        case 0:
            HFR_RET(hfReg<0>(prm, out, hist));
        case 6:
            HFR_RET(hfReg<6>(prm, out, hist));
        default:
            break;
        }
    }
    HFR_RET(hermiteFast(prm, out, hist));
#undef HFR_RET
#if RE4DC_HF_REG == 2
check:
    {
        u32 a[3], b[3];
        __builtin_memcpy(a, &ro, 12);
        __builtin_memcpy(b, out, 12);
        hfrMisOut += (a[0] != b[0]) + (a[1] != b[1]) + (a[2] != b[2]);
        hfrMisHist += (rh[0] != hist[0]) + (rh[1] != hist[1]) + (rh[2] != hist[2]);
        hfrMisRet += rr != fr;
        if ((++hfrCalls & 0xFFF) == 0) {
            re4dc_log("HFR calls=%u fast=%u bail=%u mismatch_out=%u mismatch_hist=%u mismatch_ret=%u\n", hfrCalls,
                      hfrFast, hfrBail, hfrMisOut, hfrMisHist, hfrMisRet);
        }
        return fr;
    }
#endif
}
#define hermiteSelected hermiteReg
#endif

#if defined(RE4DC_HF_ASM) && RE4DC_HF_ASM
extern "C" int re4dc_hf_run(HermitePrm*, Vec*, u16*);
extern "C" void re4dc_log(const char*, ...);
static_assert(__builtin_offsetof(HermitePrm, frame) == 0);
static_assert(__builtin_offsetof(HermitePrm, maxFrame) == 4);
static_assert(__builtin_offsetof(HermitePrm, flags) == 8);
static_assert(__builtin_offsetof(HermitePrm, type) == 12);
static_assert(__builtin_offsetof(HermitePrm, key) == 16);
static_assert(sizeof(Vec) == 12 && sizeof(u16) == 2);
#if RE4DC_HF_ASM == 2
u32 hfaCalls, hfaRun, hfaCold, hfaType[16], hfaMisOut, hfaMisHist, hfaMisRet;
// Check-mode-only boundary cases exercise the actual SH-4 kernel before a
// gameplay call: all supported layouts, 2/4-byte key alignment, history search,
// reverse/ignore-history flags, wrap/clamp and restoration on cold exits.
static void hfaPut16(u8* p, u16 x) { p[0]=(u8)x; p[1]=(u8)(x>>8); }
static void hfaPutFloat(u8* p, f32 x) { __builtin_memcpy(p,&x,4); }
static void hfaSelfTest()
{
    u32 checked=0, cold=0;
    const int types[3]={0,5,6};
    const u32 flags[8]={0,1,4,5,8,9,12,13};
    const f32 frames[7]={0.0f,1.5f,4.0f,6.25f,8.0f,12.0f,13.0f};
    for (int ti=0; ti<3; ++ti) for (int align=0; align<=2; align+=2) {
        alignas(4) u8 storage[160];
        u8* key=storage+align; u8* p=key;
        const int type=types[ti], stride=hfStride[type];
        for (int axis=0; axis<3; ++axis) {
            hfaPut16(p,3); hfaPut16(p+2,0); hfaPut16(p+4,4); hfaPut16(p+6,8);
            p+=8;
            for (int k=0;k<3;++k,p+=stride) {
                if (type==0) {
                    hfaPutFloat(p,(f32)(axis*11+k*3-17)*0.125f);
                    hfaPutFloat(p+4,(f32)(k*5-axis*3+2)*0.0625f);
                    hfaPutFloat(p+8,(f32)(axis*7-k*2-3)*0.03125f);
                } else {
                    hfaPut16(p,(u16)(s16)(-31001+k*10000+axis*177));
                    if (type==5) {
                        hfaPut16(p+2,(u16)(s16)(30001-k*377-axis*500));
                        hfaPut16(p+4,(u16)(s16)(-19001+k*397+axis*299));
                    } else {p[2]=(u8)(s8)(113-k*31-axis*7);p[3]=(u8)(s8)(-117+k*17+axis*9);}
                }
            }
        }
        for (int fi=0;fi<8;++fi) for (int f=0;f<7;++f) for (int hi=0;hi<3;++hi) {
            HermitePrm prm={frames[f],12.0f,flags[fi],(u8)type,{0,0,0},key};
            u16 a[3]={(u16)hi,(u16)hi,(u16)hi}, b[3]={(u16)hi,(u16)hi,(u16)hi};
            Vec expected={16.25f,-33.0f,45.5f},actual=expected;
            const int rr=hermiteFast(&prm,&expected,a), ar=re4dc_hf_run(&prm,&actual,b);
            if (rr!=ar || __builtin_memcmp(&expected,&actual,12) || __builtin_memcmp(a,b,6)) {
                re4dc_log("HFA_SELFTEST FAIL type=%d align=%d flags=%u frame=%d hist=%d rr=%d ar=%d\n",type,align,flags[fi],f,hi,rr,ar);
                __builtin_trap();
            }
            ++checked;
        }
        for (int which=0;which<4;++which) {
            HermitePrm prm={which==3 ? 9.0f : 1.5f,12.0f,0,(u8)type,{0,0,0},key};
            u16 before[3]={0,0,0};if(which<3)before[which]=3;
            u16 hist[3]={before[0],before[1],before[2]};
            Vec beforeOut={16.25f,-33.0f,45.5f},actual=beforeOut;
            const int ar=re4dc_hf_run(&prm,&actual,hist);
            if(ar!=-1 || __builtin_memcmp(&beforeOut,&actual,12) || __builtin_memcmp(before,hist,6)) {
                re4dc_log("HFA_SELFTEST COLD FAIL type=%d align=%d which=%d ar=%d\n",type,align,which,ar);
                __builtin_trap();
            }
            ++cold;
        }
    }
    re4dc_log("HFA_SELFTEST normal=%u cold_restore=%u mismatch=0\n",checked,cold);
}

#endif
int hermiteSelected(HermitePrm* prm, Vec* out, u16* hist)
{
#if RE4DC_HF_ASM == 2
    static bool selfChecked;
    if (!selfChecked) { hfaSelfTest(); selfChecked=true; }
#endif
    const int type = prm->type;
    if ((type != 0 && type != 5 && type != 6) || ((u32)prm->key & 1))
        return hermiteFast(prm, out, hist);
#if RE4DC_HF_ASM == 2
    const u16 before[3] = {hist[0], hist[1], hist[2]};
    Vec expected;
    const int rr = hermiteFast(prm, &expected, hist);
    const u16 after[3] = {hist[0], hist[1], hist[2]};
    hist[0] = before[0]; hist[1] = before[1]; hist[2] = before[2];
#endif
    int ret = re4dc_hf_run(prm, out, hist);
#if RE4DC_HF_ASM == 2
    if (ret < 0) ++hfaCold; else ++hfaRun;
#endif
    // A cold exit restores the caller's original output and history. The C
    // body owns invalid-history errors and cross-axis stale-pair run-outs.
    if (ret < 0) ret = hermiteFast(prm, out, hist);
#if RE4DC_HF_ASM == 2
    u32 a[3], b[3];
    __builtin_memcpy(a, &expected, 12); __builtin_memcpy(b, out, 12);
    hfaMisOut += (a[0]!=b[0]) + (a[1]!=b[1]) + (a[2]!=b[2]);
    hfaMisHist += (after[0]!=hist[0]) + (after[1]!=hist[1]) + (after[2]!=hist[2]);
    hfaMisRet += rr != ret;
    ++hfaType[type];
    if ((++hfaCalls & 0xfff) == 0)
        re4dc_log("HFA calls=%u run=%u cold=%u t0=%u t5=%u t6=%u mismatch_out=%u hist=%u ret=%u\n",
                  hfaCalls,hfaRun,hfaCold,hfaType[0],hfaType[5],hfaType[6],hfaMisOut,hfaMisHist,hfaMisRet);
    if (hfaMisOut || hfaMisHist || hfaMisRet) __builtin_trap();
#endif
    return ret;
}
#elif !(defined(RE4DC_HF_REG) && RE4DC_HF_REG)
#define hermiteSelected hermiteFast
#endif

#if RE4DC_HERMITE_FAST == 2
extern "C" void re4dc_log(const char* fmt, ...);
u32 hfCalls, hfMisOut, hfMisHist, hfMisRet;
#endif
}   // namespace
int HermiteInterpolation(HermitePrm* prm, Vec* out, u16* hist)
{
#if RE4DC_HERMITE_FAST == 2
    const u16 h0[3] = {hist[0], hist[1], hist[2]};
    Vec ro;
    const int rr = HermiteInterpolation_ref(prm, &ro, hist);
    const u16 rh[3] = {hist[0], hist[1], hist[2]};
    hist[0] = h0[0];
    hist[1] = h0[1];
    hist[2] = h0[2];
    const int fr = hermiteSelected(prm, out, hist);
    u32 a[3], b[3];
    __builtin_memcpy(a, &ro, 12);
    __builtin_memcpy(b, out, 12);
    hfMisOut += (a[0] != b[0]) + (a[1] != b[1]) + (a[2] != b[2]);
    hfMisHist += (rh[0] != hist[0]) + (rh[1] != hist[1]) + (rh[2] != hist[2]);
    hfMisRet += rr != fr;
    if ((++hfCalls & 0xFFF) == 0) {
        re4dc_log("HERMF calls=%u mismatch_out=%u mismatch_hist=%u mismatch_ret=%u\n", hfCalls, hfMisOut, hfMisHist,
                  hfMisRet);
    }
    return fr;
#else
    return hermiteSelected(prm, out, hist);
#endif
}
#endif

// Byte-wise big-endian reads of the key data (the streams are unaligned).
typedef union {
    f32 f;
    struct {
        u8 b0;
        u8 b1;
        u8 b2;
        u8 b3;
    } b;
} FccF32;

typedef union {
    s16 s;
    struct {
        u8 hi;
        u8 lo;
    } b;
} FccS16;

#define FCC_F32(dst, i)      \
    cf.b.b0 = d[(i)];        \
    cf.b.b1 = d[(i) + 1];    \
    cf.b.b2 = d[(i) + 2];    \
    cf.b.b3 = d[(i) + 3];    \
    (dst) = cf.f;
#define FCC_S16(dst, i)      \
    cs.b.hi = d[(i)];        \
    cs.b.lo = d[(i) + 1];    \
    (dst) = (f32) cs.s * 0.0001f;
#define FCC_S8(dst, i) (dst) = (f32) (s8) d[(i)] * 0.0001f;

// Key layout 0: f32 value, f32 in-tangent, f32 out-tangent (12 bytes/key); reads keys i0, i1.
void Fcc_get_data_000(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccF32 cf;

    FCC_F32(v[0], i0 * 12);
    FCC_F32(v[1], i1 * 12);
    FCC_F32(t[0], i0 * 12 + 8);
    FCC_F32(t[1], i1 * 12 + 4);
}

// Key layout 1: f32 value, s16 tangents (8 bytes/key).
void Fcc_get_data_001(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccF32 cf;
    FccS16 cs;

    FCC_F32(v[0], i0 * 8);
    FCC_F32(v[1], i1 * 8);
    FCC_S16(t[0], i0 * 8 + 6);
    FCC_S16(t[1], i1 * 8 + 4);
}

// Key layout 2: f32 value, s8 tangents (6 bytes/key).
void Fcc_get_data_002(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccF32 cf;

    FCC_F32(v[0], i0 * 6);
    FCC_F32(v[1], i1 * 6);
    FCC_S8(t[0], i0 * 6 + 5);
    FCC_S8(t[1], i1 * 6 + 4);
}

// Key layout 4: s16 value, f32 tangents (10 bytes/key).
void Fcc_get_data_010(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccF32 cf;
    FccS16 cs;

    FCC_S16(v[0], i0 * 10);
    FCC_S16(v[1], i1 * 10);
    FCC_F32(t[0], i0 * 10 + 6);
    FCC_F32(t[1], i1 * 10 + 2);
}

// Key layout 5: s16 value, s16 tangents (6 bytes/key). s16 and s8 fields are in 1/10000 units (FCC_S16 / FCC_S8).
void Fcc_get_data_011(u8* d, int i0, int i1, f32* v, f32* t)
{
    static int flag = 0;
    FccS16 cs;

    if (flag) {
        v[0] = (f32) *(s16*) &d[i0 * 6] * 0.0001f;
        v[1] = (f32) *(s16*) &d[i1 * 6] * 0.0001f;
        t[0] = (f32) *(s16*) &d[i0 * 6 + 4] * 0.0001f;
        t[1] = (f32) *(s16*) &d[i1 * 6 + 2] * 0.0001f;
    } else {
        FCC_S16(v[0], i0 * 6);
        FCC_S16(v[1], i1 * 6);
        FCC_S16(t[0], i0 * 6 + 4);
        FCC_S16(t[1], i1 * 6 + 2);
    }
}

// Key layout 6: s16 value, s8 tangents (4 bytes/key).
void Fcc_get_data_012(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccS16 cs;

    FCC_S16(v[0], i0 * 4);
    FCC_S16(v[1], i1 * 4);
    FCC_S8(t[0], i0 * 4 + 3);
    FCC_S8(t[1], i1 * 4 + 2);
}

// Key layout 8: s8 value, f32 tangents (9 bytes/key).
void Fcc_get_data_020(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccF32 cf;

    FCC_S8(v[0], i0 * 9);
    FCC_S8(v[1], i1 * 9);
    FCC_F32(t[0], i0 * 9 + 5);
    FCC_F32(t[1], i1 * 9 + 1);
}

// Key layout 9: s8 value, s16 tangents (5 bytes/key).
void Fcc_get_data_021(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccS16 cs;

    FCC_S8(v[0], i0 * 5);
    FCC_S8(v[1], i1 * 5);
    FCC_S16(t[0], i0 * 5 + 3);
    FCC_S16(t[1], i1 * 5 + 1);
}

// Key layout 10: s8 value, s8 tangents (3 bytes/key).
void Fcc_get_data_022(u8* d, int i0, int i1, f32* v, f32* t)
{
    FCC_S8(v[0], i0 * 3);
    FCC_S8(v[1], i1 * 3);
    FCC_S8(t[0], i0 * 3 + 2);
    FCC_S8(t[1], i1 * 3 + 1);
}

// Key layout 15: f32 value only, no tangents (4 bytes/key; stepped/linear data).
void Fcc_get_data_033(u8* d, int i0, int i1, f32* v, f32* t)
{
    FccF32 cf;

    FCC_F32(v[0], i0 * 4);
    FCC_F32(v[1], i1 * 4);
}

// Unused key layouts.
void dummy(u8* d, int i0, int i1, f32* v, f32* t)
{
}

// Byte size of an axis stream of n keys for key layout `type` (offset to the next axis).
int Fcc_next_axis_addr(int type, int n)
{
    switch (type) {
    case 0:
        return n * 12;
    case 1:
        return n * 8;
    case 2:
        return n * 6;
    case 3:
        return -1;
    case 4:
        return n * 10;
    case 5:
        return n * 6;
    case 6:
        return n * 4;
    case 7:
        return -1;
    case 8:
        return n * 9;
    case 9:
        return n * 5;
    case 10:
        return n * 3;
    case 11:
        return -1;
    case 12:
        return -1;
    case 13:
        return -1;
    case 14:
        return -1;
    case 15:
        return n * 4;
    }
    return -1;
}

// Debug speed display: dead-stripped by the linker, only the strings, constant pools and statics
// remain. The three zeroed 4-byte statics survive as one unnamed 12-byte .sdata object; this stand-in
// keeps the split label as its name (and the section forced) so strip_unused leaves it in place.
static Vec lbl_80314C44 __attribute__((section(".sdata"))) = { 0.0f, 0.0f, 0.0f };

// Debug (dead-stripped): header line of the motion speed display.
// The two label pointers at .rodata+0x218 (relocated words) are a function-local static table
// declared AFTER the first eprintf: its strings and the table are assembled when the declaration
// is reached, i.e. after "MOTION SPEED ---" and before the "%s" of the following call.
void MotionSpeedDispHeader(int x, int y, int who)
{
    eprintf(x, y, 0, 0, "MOTION SPEED ---");
    {
        static const char* const who_str[2] = { "GLOBAL: ", "PLAYER: " };
        eprintf(x, y + 10, 0, 0, "%s", who_str[who]);
    }
}

// Debug (dead-stripped): prints the model's motion frame/speed values.
void MotionSpeedDisp(cModel* m, int x, int y)
{
    MotionWork* w = MOTION(m);

    eprintf(x, y, 0, 0, "%s", (char*) w->pMot);
    lbl_80314C44.x = lbl_80314C44.x * 0.01f + w->Pos_move_old.x * 10.0f * 0.5f;
    eprintf(x, y + 10, 0, 0, "%.2f", (f32) x * lbl_80314C44.x);
    if (lbl_80314C44.y == 0.0f) {
        lbl_80314C44.z = 2.0f;
    }
}
