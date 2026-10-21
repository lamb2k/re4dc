// game/espgen10: effect controller 10, the sequence player (D:/Bio4/Prog/espgen10.cpp). Plays an
// effect sequence (EspSeqData: records sorted by Set_time) record by record: at each frame every
// record whose Set_time equals the frame counter is spawned, either as an esp (Kind 0) or as a
// nested controller (Kind 1). EstSet (est.cpp) creates these controllers. Also holds the shared
// controller allocation helpers EspgenDataSet / SetEspCore / PullEspEspgen.
#include "atari.h"
#include "light.h"
#include "esp.h"
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "native_effect_source.h"
#endif
#include "espgen.h"
#include "math_sub.h"
#include "db_log.h"

extern "C" {
void espgen10_Update(EspgenWork* w);
void espgen10_Move00(EspgenWork* w);
void espgen10_Move01(EspgenWork* w);
}

// Spawns record `no` of the sequence: Kind 0 -> one esp via EspSeqSet (pos is passed only when
// flag != 0), Kind 1 -> a controller via EspgenSeqSet. In event mode (Core_flg 0x1000) the parent
// model comes from EspEvModList[Parent_no]. Returns 0 when the spawn failed (pool full / bad kind).
int EspgenDataSet(EspSeqData* head, int no, EspInfo* info, u32* seed, cModel* model, u16 parts, Mtx* mtx, Vec* pos,
                  Vec* rot, EspSeqOpt* p8, int flag)
{
    // COMPILER-DIFF #13 block: the original never allocates `list` (REG_EQUIV symbol_ref) and
    // reload materialises `lis r9; addi r11` before the compare. Here `list` is a 2-set variable
    // (the rec offset, then the table address): no REG_EQUIV, global gives it r11, the high is
    // a plain local-alloc qty (r9) since the addi's destination is not a hard register.
    u32 list;
    EspGenWork* rec;
    int ret = 1;

    list = no * sizeof(EspGenWork) + 0x30;
#if defined(RE4DC_GAME) && !defined(__PPC__)
    EspGenWork scratch;
    EspGenWork* reference = re4dc_effect_ref(head, no);
    rec = re4dc_effect_read(reference, scratch);
#else
    rec = (EspGenWork*) ((u32) head + list);
#endif
    if (info->Core_flg & 0x1000) {
        u32 no = rec->Parent_no;
        list = (u32) EspEvModList;
        if (no > 0x7F) {
            model = NULL;
        } else {
            model = *(cModel**) (list + (no << 2));
        }
    }

    switch (rec->Kind) {
    case 0: {
        cEsp* esp;
        if (flag == 0) {
            pos = NULL;
        }
#if defined(RE4DC_GAME) && !defined(__PPC__)
        rec = reference; // EspSeqSet expands locally; never let a retained pointer refer to scratch.
#endif
        if (EspSeqSet(rec, info, seed, model, mtx, 0, 0.0f, &esp, p8, pos) == 0) {
            ret = 0;
        }
        break;
    }
    case 1:
        if (EspgenSeqSet(head, no, info, model, parts, mtx, pos, rot, p8, flag) == 0) {
            ret = 0;
        }
        break;
    default:
        pLog->err(0, 0, "ESP_CTRL : KIND[%d] is invalid.", rec->Kind);
        ret = 0;
        break;
    }
    return ret;
}
// Fills the controller's EspInfo owner block: Core_flg = a, Call_no = b, Core_kind = c, Core_pEm = d,
// owner = e (the ids EfmDelete / EspDelete use to find effects by owner).
void SetEspCore(EspgenWork* w, int a, u32 b, u8 c, u32 d, int e)
{
    w->info.Core_flg = a;
    w->info.Core_kind = c;
    w->info.Call_no = b;
    w->info.Core_pEm = d;
    w->info.owner = e;
}

// Takes a free controller from the pool (front == 1: from the front, drawn first) and stamps the
// owner info on it. Returns 0 when the pool is empty.
int PullEspEspgen(EspgenWork** out, int a, int c, u32 b, u32 d, int e, int front)
{
    int ret;

    if (front == 1) {
        ret = PullEspgenFront(out);
    } else {
        ret = PullEspgen(out);
    }
    if (ret) {
        SetEspCore(*out, a, b, c, d, e);
    }
    return ret;
}

// One sequence frame: kills the controller when the model died or was reused; rebuilds Mat from the
// parts (or Offset/Ang for 0xFE) unless Flg bit 0 says it is fixed; then spawns every record whose
// Set_time == Time_cnt (records must be sorted, otherwise "no SORT" error) and ends the controller
// after the last record.
void espgen10_Update(EspgenWork* w)
{
    Espgen10Work* p = (Espgen10Work*) w->work;
    EspSeqData* head = p->head;
#if defined(RE4DC_GAME) && !defined(__PPC__)
#if !defined(RE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST) || !RE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST
    EspGenWork scratch;
    EspGenWork* rec = re4dc_effect_read(re4dc_effect_ref(head, p->no), scratch);
#endif
#else
    EspGenWork* rec = &head->rec[p->no];
#endif
    cModel* model = p->pMod;

    if (model != NULL) {
        if ((model->be_flag & 0x201) != 1 || model->serial != p->Guid_pMod) {
            PushEspgen(w);
            return;
        }
    }
    if ((p->Null_parts_no >= 0xF8 && p->Null_parts_no <= 0xFD) || p->Null_parts_no == 0xFF) {
        pLog->err(0, 0, "ESP_CTRL10 : PARTS_NO[%x] invalid.", p->Null_parts_no);
        PushEspgen(w);
        return;
    }
    if (p->Null_parts_no == 0xFE) {
        PSMTXIdentity(p->Mat);
        RotMatrix(p->Mat, &p->Ang);
        p->Mat[0][3] = p->Offset.x;
        p->Mat[1][3] = p->Offset.y;
        p->Mat[2][3] = p->Offset.z;
    } else {
        if (p->pMod == NULL) {
            pLog->err(0, 0, "ESP_CTRL10 : PARTS_NO is set but No Parent.");
            PushEspgen(w);
            return;
        }
        if (!(p->Flg & 1)) {
            cModel* part;
            Vec ofs;
            Vec r;

            if (p->Null_parts_no >= model->nParts) {
                pLog->err(0, 0, "ESP_CTRL10 : PARTS_NO[%d] is invalid(MAX:%d).", p->Null_parts_no, model->nParts);
                PushEspgen(w);
                return;
            }
            part = model->getPartsPtr(p->Null_parts_no);
            PSMTXIdentity(p->Mat);
            PSVECAdd(&p->Ang, &model->ang, &r);
            RotMatrix(p->Mat, &r);
            PSMTXMultVecSR(p->Mat, &p->Offset, &ofs);
            p->Mat[0][3] = part->mat[0][3] + ofs.x;
            p->Mat[1][3] = part->mat[1][3] + ofs.y;
            p->Mat[2][3] = part->mat[2][3] + ofs.z;
            if (!(head->flags & 1)) {
                p->Flg |= 1;
            }
        }
    }
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST) && RE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST
    // Original validation can discard this controller without reading its
    // borrowed record. Keep that ordering before the Dreamcast decoder.
    EspGenWork scratch;
    EspGenWork* rec = re4dc_effect_read(re4dc_effect_ref(head, p->no), scratch);
#endif
    if (rec->Set_time < p->Time_cnt) {
        pLog->err(0, 0, "ESP_ESTSET : DATA[%d] is no SORT.", p->no);
        PushEspgen(w);
        return;
    }
    while (rec->Set_time == p->Time_cnt) {
        int flag = 0;
        if (p->Flg & 2) {
            flag = 1;
        }
        if (!EspgenDataSet(head, p->no, &w->info, &p->Rand_seed, p->pMod, p->Null_parts_no, &p->Mat, &p->Offset, &p->Ang, p->p8,
                           flag)) {
            return;
        }
        p->no++;
#if !defined(RE4DC_GAME) || defined(__PPC__)
        rec++;
#endif
        if (p->no >= head->num) {
            PushEspgen(w);
            break;
        }
#if defined(RE4DC_GAME) && !defined(__PPC__)
        rec = re4dc_effect_read(re4dc_effect_ref(head, p->no), scratch);
#endif
    }
    p->Time_cnt++;
}

// Step 0 of Espgen10MoveTbl: first frame, then step 1.
void espgen10_Move00(EspgenWork* w)
{
    espgen10_Update(w);
    w->step = 1;
}

// Step 1 of Espgen10MoveTbl: steady state.
void espgen10_Move01(EspgenWork* w)
{
    espgen10_Update(w);
}

// EspgenMoveTbl entry for controller type 0x10: dispatches on w->step.
void Espgen10_Move(EspgenWork* w)
{
    static void (*Espgen10MoveTbl[])(EspgenWork*) = {espgen10_Move00, espgen10_Move01};

    Espgen10MoveTbl[w->step](w);
}
