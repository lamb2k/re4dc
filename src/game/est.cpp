#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
#include "fallback_audit35.h"
#endif
#line 1
// game/est: the effect set ("EST") front end (D:/Bio4/Prog/est.cpp). EstSet(owner, id) is how
// game code starts an effect: it looks the est table up in the loaded effect data
// (EspGetEstAddr) and starts a controller 10 sequence player on it. Also the room "SST" effects
// (per-room effect lists started by area / room key), the effect deletion front ends
// (EffectEspDelete / EffectDeleteAll / EventCutEffDelete ...), the eat (hit) effects
// (EspSetEatEffect) and a few water helpers. EspEvModList maps event model numbers to models.
#include "atari.h"
#include "light.h"
#include "global.h"
#include "esp.h"
#include "espgen.h"
#include "est.h"
#include "math_sub.h"
#include "rnd.h"
#include "player.h"
#include "area.h"
#include "flr_at.h"
#include "at_sub2.h"
#include "snd.h"
#include "db_log.h"

cModel* EspEvModList[0x80];

// Effect set table: starts effect controller 10 on the est data block `head`.
void EstSet(cModel* model, int no, Vec* pos, Vec* rot, EspSeqData* head, int e, int f, u32 g, u32 owner, void* h);

// The common entry: starts est table (owner c, id d) with parts b (-1 = the table's default) on the
// model a (0 = none), at pos/rot (NULL = the table's own), core flags e, kind f, Core_pEm g and an
// optional EspSeqOpt h.
void EstSet(int a, int b, Vec* pos, Vec* rot, int c, int d, int e, int f, u32 g, void* h)
{
    EspSeqData* head = EspGetEstAddr(c, d, 0);

    EstSet((cModel*) a, b, pos, rot, head, e, f, g, c, h);
}

// Starts the sequence `head` on a front-pulled controller 10: stamps the owner info (Core_flg e, plus
// 0x2000 during a movie / bit 0 in the no-suspend mode from Status_flg[2]), the call number, parts,
// offset (pos != NULL sets Flg bit 1 = explicit position) and rotation (head->rot is in degrees),
// and a random seed. Debug_flg[1] 0x01000000 disables all effects.
void EstSet(cModel* model, int no, Vec* pos, Vec* rot, EspSeqData* head, int e, int f, u32 g, u32 owner, void* h)
{
    EspgenWork* w;
    Espgen10Work* p;

    if (pG->Debug_flg[1] & 0x01000000) {
        return;
    }
    if (head == NULL) {
        return;
    }
    if (head->num == 0) {
        pLog->warn(0, 0, "EstSet():EST is enpty.");
        return;
    }
    if (pG->Status_flg[2] & 0x00080000) {
        e |= 0x2000;
    }
    if (pG->Status_flg[2] & 0x02000000) {
        e |= 1;
    }
    if (!PullEspEspgen(&w, e, f, (u8) EspgenGetCallNo(), g, owner, 1)) {
        return;
    }
    EspgenIncCallNo();
    w->id = 0x10;
    p = (Espgen10Work*) w->work;
    p->head = head;
    p->pMod = model;
    if (model != NULL) {
        p->Guid_pMod = model->serial;
    } else {
        p->Guid_pMod = (u32) model;
    }
    p->no = p->Time_cnt = 0;
    if (no == -1) {
        p->Null_parts_no = head->parts;
    } else {
        p->Null_parts_no = no;
    }
    if (pos == NULL) {
        p->Offset = head->pos;
    } else {
        p->Flg |= 2;
        p->Offset = *pos;
    }
    if (rot == NULL) {
        p->Ang = head->rot;
        PSVECScale(&p->Ang, &p->Ang, 3.14f / 180.0f);
    } else {
        p->Ang = *rot;
    }
    p->Rand_seed = Rnd() | (Rnd() << 8) | (Rnd() << 16);
    if (h != NULL) {
        p->p8 = &p->opt;
        p->opt = *(EspSeqOpt*) h;
    } else {
        p->p8 = (EspSeqOpt*) h;
    }
}

// Starts the SST effects of type 1 with key 0xC + area for every effect area the player currently
// stands in (used when a display flag `id` is switched on so its area effects appear at once).
// Sets the room effects whose area the player stands in.
void AreaSstSet(int id)
{
    cEspSystem* sys = g_pEspSys;
    SstAreaEnt* ent;
    Vec pos;
    u32 flag;
    u32 i;
    u32 j;

    if (sys->pSstArea == NULL) {
        return;
    }
    pos = pPL->pos;
    pos.y += 100.0f;
    flag = 0;
    ent = sys->pSstArea->ent;
    for (i = 0; i < sys->pSstArea->num; i++, ent++) {
        if (AreaHitCheck(ent->area, &pos) == 1) {
#if defined(__PPC__)
            flag |= 1 << ent->area_no;
#else
            flag |= NativeSstAreaBit(ent->area_no);
#endif
        }
    }
    for (j = 0; j < 32; j++) {
        if (flag & (1 << j)) {
            SstSet(1, (u16) j, j + 0xC, id, id, 0);
        }
    }
}

// 1 when room effect display flag `id` (0..31, cEspSystem::SstSetFlag) is on.
int GetSstDispFlag(u32 id)
{
    cEspSystem* sys = g_pEspSys;

    if (id > 0x1F) {
        pLog->err(0, 0, "GetSstDispFlag() : id[%02x] invalid .", id);
        return 0;
    }
    if (sys->SstSetFlag & (1 << id)) {
        return 1;
    }
    return 0;
}

// Turns room effect display flag `id` on/off; turning it on from off also starts the matching area
// effects for the player's current areas (AreaSstSet).
void SetSstDispFlag(u32 id, int on)
{
    cEspSystem* sys = g_pEspSys;

    if (id > 0x1F) {
        pLog->err(0, 0, "GetSstDispFlag() : id[%02x] invalid .", id);
        return;
    }
    if (on == 1) {
        if (GetSstDispFlag(id) == 0) {
            sys->SstSetFlag |= on << id;
            AreaSstSet(id);
        } else {
            sys->SstSetFlag |= on << id;
        }
    } else {
        sys->SstSetFlag &= ~(1 << id);
    }
}

// Sets the extra effect-area bits that EffAreaUpdate ORs into the area state every frame.
void SetSstAddAreaFlag(u32 flag)
{
    g_pEspSys->Add_area_bit = flag;
}

// Starts every SST entry of `owner` (0xD2 = none) whose key is in [lo, hi], whose type matches and
// whose display flag is on, as a permanent effect (Core_flg 0x4001, kind no, owner 0xD0). move != 0
// pre-runs the generators 200 frames so steady-state effects (smoke, dust) are already full.
// Starts every effect of owner `owner` whose room key lies in [lo, hi] and whose type is `type`.
void SstSet(u32 owner, int type, int no, int lo, int hi, int move)
{
    cEspSystem* sys = g_pEspSys;
    SstTbl* tbl;
    SstList* list;
    u32* ofs;
    u32 i;

    if (owner > 0xD2) {
        pLog->err(0, 0, "GetSstAddr():Invalid OWNER_ID[%x].", owner);
        return;
    }
    tbl = &sys->sstTbl[owner];
    if (tbl->owner == 0xD2) {
        return;
    }
    list = tbl->list;
    for (i = 0; i < list->num; i++) {
        if (list->ent[i].no < (u16) lo || list->ent[i].no > (u16) hi) {
            continue;
        }
        if (list->ent[i].type != type) {
            continue;
        }
        if (!GetSstDispFlag(list->ent[i].b.id)) {
            continue;
        }
        ofs = tbl->data->ofs;
        ofs += i;
        EstSet(NULL, -1, NULL, NULL, (EspSeqData*) ((u8*) tbl->data + *ofs), 0x4001, (u8) no, 0, 0xD0, NULL);
    }
    if (move) {
        EspGenSetMoveLoop(200);
        EspGenLoopMove();
    }
}

// Deletes sprites by owner info (Core_flg a, kind b, Core_pEm c, attached model).
void EffectEspDelete(int a, int b, u32 c, cModel* model)
{
    EspDelete(a, b, c, model);
}

// Deletes controllers by owner info.
void EffectEspgenDelete(int a, int b, int c)
{
    EspgenDelete(a, b, c);
}

// Deletes effect models by owner info.
void EffectEfmDelete(int a, int b, int c)
{
    EfmDelete(a, b, c);
}

// Removes every sprite, controller and effect model (room change).
void EffectDeleteAll()
{
    pG->Status_flg[1] &= ~0x20;
    EspArrayClear();
    EspgenArrayClear();
    EfmArrayClear();
}

// Removes every non-permanent, non-event effect (event end).
void EffectEventDelete()
{
    EspDeleteEvent();
    EspgenDeleteEvent();
    EfmDeleteEvent();
}

// Releases every live sprite whose owner info matches (a/b/c each skipped when 0) and, when a model is
// given, that is attached to that model instance (pointer and serial).
#if defined(RE4DC_ESP_OWNER) && RE4DC_ESP_OWNER
static void espOwnRecount(cEspSystem* sys)
{
    u32 i;
    for (i = 0; i < 64; i++) {
        re4dc_esp_own[i] = 0;
    }
    for (i = 0; sys->pEspBuf != NULL && i < sys->nEsp; i++) {
        cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);
        if (esp->m_Be_flg & 1) {
            re4dc_esp_own[re4dcEspOwnB(esp->info.Core_pEm)]++;
        }
    }
    re4dc_esp_own_valid = 1;
}
#if RE4DC_ESP_OWNER == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 espOwnCalls, espOwnSkips, espOwnMis, espOwnRecounts;
#endif
#endif
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
// The source loop's test for one slot.
static inline int fxEspDelHit(cEsp* esp, int a, int b, u32 c, cModel* model)
{
    if ((esp->m_Be_flg & 1) == 0) {
        return 0;
    }
    if (a != 0 && esp->info.Core_flg != a) {
        return 0;
    }
    if (b != 0 && esp->info.Core_kind != b) {
        return 0;
    }
    if (c != 0 && esp->info.Core_pEm != c) {
        return 0;
    }
    if (model != NULL) {
        if (esp->m_pMod != model) {
            return 0;
        }
        if (esp->m_Guid_pMod != model->serial) {
            return 0;
        }
    }
    return 1;
}
#if RE4DC_FX_SCAN == 2
// Check build: none of the skipped slots [from, to) may match.
static void fxChkDelSkip(cEspSystem* sys, u32 from, u32 to, int a, int b, u32 c, cModel* model)
{
    for (; from < to && from < sys->nEsp; from++) {
        if (fxEspDelHit((cEsp*) (sys->pEspBuf + from * 0x150), a, b, c, model)) {
            re4dc_fx_chk[FXC_MIS_ESP]++;
        }
    }
}
#endif
// GAME_FX_SCAN: with an owner (c != 0) only the slots in c's owner row can match (esp.h), so while
// the rows are current the source loop steps over the runs outside that row; it returns at once
// when the bucket is empty, as GAME_ESP_OWNER did.
void EspDelete(int a, int b, u32 c, cModel* model)
{
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    u32 fa35_scan = 0;
    bool fa35_stale = false;
#endif
#line 320
    cEspSystem* sys = g_pEspSys;
    const unsigned long* row = NULL;
    unsigned long gen = 0;
    u32 i;

    if (c != 0) {
        const int ok = re4dc_fx_esp_ready();   // counts and rows current
        const u32 B = re4dcEspOwnB(c);
        if (re4dc_esp_own[B] == 0) {
#if RE4DC_FX_SCAN == 2
            fxChkDelSkip(sys, 0, sys->nEsp, a, b, c, model);
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            re4dc::fa35::hit(re4dc::fa35::EspDeleteEmpty, 1);
#endif
#line 332
            return;
        }
        if (ok) {
            row = re4dc_fx_esp_ownmap[B];
            gen = re4dc_fx_esp_gen;
#if RE4DC_FX_SCAN == 2
            re4dc_fx_chk[FXC_ESP_DEL]++;
#endif
        }
    }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    if (!c) re4dc::fa35::hit(re4dc::fa35::EspDeleteOwnerZero, 1);
    else re4dc::fa35::hit(row ? re4dc::fa35::EspDeleteMapped : re4dc::fa35::EspDeleteMiss);
#endif
#line 342
    for (i = 0; i < sys->nEsp; i++) {
        cEsp* esp;
        if (row != NULL && re4dc_fx_esp_gen == gen) {
            unsigned long m = row[i >> 5] >> (i & 31);
            if (m == 0) {
#if RE4DC_FX_SCAN == 2
                fxChkDelSkip(sys, i, (i | 31) + 1, a, b, c, model);
#endif
                i |= 31;
                continue;
            }
            m = re4dcFxCtz(m);
#if RE4DC_FX_SCAN == 2
            fxChkDelSkip(sys, i, i + m, a, b, c, model);
#endif
            i += m;
        }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        if (!row || re4dc_fx_esp_gen != gen) {
            ++fa35_scan;
            if (row) fa35_stale = true;
        }
#endif
#line 359
        esp = (cEsp*) (sys->pEspBuf + i * 0x150);
        if (fxEspDelHit(esp, a, b, c, model)) {
            PushEsp(esp);
        }
    }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::EspDeleteScan, fa35_scan);
    if (fa35_stale) re4dc::fa35::hit(re4dc::fa35::EspDeleteStale, 1);
#endif
#line 364
#if RE4DC_FX_SCAN == 2
    if (row != NULL && re4dc_fx_esp_gen != gen) {
        re4dc_fx_chk[FXC_FALLBACK]++;
    }
#endif
}
#else
void EspDelete(int a, int b, u32 c, cModel* model)
{
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    u32 fa35_scan = 0;
    re4dc::fa35::hit(re4dc::fa35::EspDeleteOff, 1);
    if (!c) re4dc::fa35::hit(re4dc::fa35::EspDeleteOwnerZero, 1);
#endif
#line 373
    cEspSystem* sys = g_pEspSys;
    u32 i;

#if defined(RE4DC_ESP_OWNER) && RE4DC_ESP_OWNER
    if (c != 0) {
        if (!re4dc_esp_own_valid) {
            espOwnRecount(sys);
#if RE4DC_ESP_OWNER == 2
            espOwnRecounts++;
#endif
        }
#if RE4DC_ESP_OWNER == 2
        if (++espOwnCalls % 1024 == 0) {
            re4dc_log("ESPOWN calls=%u skips=%u mismatch=%u recounts=%u\n", espOwnCalls, espOwnSkips, espOwnMis,
                      espOwnRecounts);
        }
#endif
        if (re4dc_esp_own[re4dcEspOwnB(c)] == 0) {
#if RE4DC_ESP_OWNER == 2
            espOwnSkips++;
            for (i = 0; i < sys->nEsp; i++) {
#line 394
                cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);
                if ((esp->m_Be_flg & 1) && esp->info.Core_pEm == c) {
                    espOwnMis++;
                }
            }
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            re4dc::fa35::hit(re4dc::fa35::EspDeleteEmpty, 1);
#endif
#line 400
            return;
        }
    }
#endif
    for (i = 0; i < sys->nEsp; i++) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        ++fa35_scan;
#endif
#line 405
        cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);

        if ((esp->m_Be_flg & 1) == 0) {
            continue;
        }
        if (a != 0 && esp->info.Core_flg != a) {
            continue;
        }
        if (b != 0 && esp->info.Core_kind != b) {
            continue;
        }
        if (c != 0 && esp->info.Core_pEm != c) {
            continue;
        }
        if (model != NULL) {
            if (esp->m_pMod != model) {
                continue;
            }
            if (esp->m_Guid_pMod != model->serial) {
                continue;
            }
        }
        PushEsp(esp);
    }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::EspDeleteScan, fa35_scan);
#endif
#line 429
}
#endif

// Releases every live sprite that is neither permanent (Core_flg bit 0) nor event-owned (bit 0x800).
void EspDeleteEvent()
{
    cEspSystem* sys = g_pEspSys;
    u32 i;

    for (i = 0; i < sys->nEsp; i++) {
        cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);

        if (esp->m_Be_flg & 1) {
            int ev = !(esp->info.Core_flg & 1);

            if (ev && !(esp->info.Core_flg & 0x800)) {
                PushEsp(esp);
            }
        }
    }
}

// Water explosion splash: est 1/0x2F in the lake rooms (r10a/b, r11a/b), else the generic 0/0x15.
void EspSetWaterBomb(Vec* pos)
{
    if (pG->room_id == 0x10A || pG->room_id == 0x10B || pG->room_id == 0x11A || pG->room_id == 0x11B) {
        EstSet(0, -1, pos, NULL, 1, 0x2F, 0, 0, 0, NULL);
    } else {
        EstSet(0, -1, pos, NULL, 0, 0x15, 0, 0, 0, NULL);
    }
}

// Bullet-hits-water splash: est 1/0x20 in the lake rooms, else 0/0x14; none in stage 3-11 / 2-24.
void EspSetWaterHitmark(Vec* pos)
{
    if ((pG->room_id32 & 0xFFFF0000) == 0x03110000 || (pG->room_id32 & 0xFFFF0000) == 0x02240000) {
        return;
    }
    if (pG->room_id == 0x10A || pG->room_id == 0x10B || pG->room_id == 0x11A || pG->room_id == 0x11B) {
        EstSet(0, -1, pos, NULL, 1, 0x20, 0, 0, 0, NULL);
    } else {
        EstSet(0, -1, pos, NULL, 0, 0x14, 0, 0, 0, NULL);
    }
}

// Never called: the eat effect messages by type.
static inline void EspEatEffectMessage(int type)
{
    switch (type) {
    case 0:
        pLog->err(0, 0, "ESP: EAT no set(type=0)");
        break;
    case 1:
        pLog->err(0, 0, "ESP: EAT no set(type=1)");
        break;
    case 2:
        pLog->err(0, 0, "ESP: EAT no set(type=2)");
        break;
    case 3:
        pLog->err(0, 0, "ESP: EAT no set(type=3)");
        break;
    }
}

// 1 when the hit point lies on a near-horizontal floor whose FlrAt entry is marked as a puddle (x45).
int EspChkInPuddle(Vec* pos, Vec* nrm)
{
    if (nrm->y > 0.9f) {
        FlrAt* at = FlrAtCheck(0, pos, 1);

        if (at != NULL && at->x45 == 1) {
            return 1;
        }
    }
    return 0;
}

// Spawns the hit effect for an eat (environment collision) attribute: `type` is the EAT type (0 dirt
// / puddle, 1 spark pair, 2 and 4..7 per-weapon effects from the AtEffInfo table, 3 unused), `nrm`
// the surface normal (rotation for the decal, flipped for flag-bit-0 infos), `wep` the weapon id.
// Hit effect for the eat (effect collision) attribute type.
void EspSetEatEffect(Vec* pos, Vec* nrm, int type, int wep)
{
    AtEffInfo* info = EatMgr.getEffInfo(type);
    Vec rot;
    u32 eff1;
    u32 eff2;
    f32 len;

    if (info != NULL && (info->flag & 1)) {
        rot.x = atan2f(SQRTF(nrm->x * nrm->x + nrm->z * nrm->z), nrm->y);
        rot.y = atan2f(nrm->x, nrm->z);
        rot.z = 0.0f;
    } else {
        len = SQRTF(nrm->x * nrm->x + nrm->z * nrm->z);
        rot.x = -atan2f(nrm->y, len);
        rot.y = atan2f(nrm->x, nrm->z);
        rot.z = 0.0f;
    }
    switch (type) {
    case 0:
        if (EspChkInPuddle(pos, nrm) == 1) {
            EstSet(0, -1, pos, NULL, 0, 0x11, 0, 0, type, (void*) type);
            SndCall(2, 0xC, pos, 0, 0, NULL);
        } else {
            EstSet(0, -1, pos, &rot, 0, 0x1F, 0, 0, type, (void*) type);
            if (pG->Debug_flg[3] & 0x4000) {
                EstSet(0, -1, pos, &rot, 0, 0x87, 0, 0, type, (void*) type);
            }
        }
        break;
    case 1:
        EstSet(0, -1, pos, &rot, 0, 0x1F, 0, 0, 0, NULL);
        EstSet(0, -1, pos, &rot, 0, 0x20, 0, 0, 0, NULL);
        break;
    case 2:
        if (info == NULL || eff1 == 0xD2) {
            pLog->err(0, 0, "NOT REGIST EAT EFF INFO %d", type);
            break;
        }
        info->getWepEff(wep, &eff1, &eff2);
        if (eff1 != 0xD2 && eff2 != 1) {
            EstSet(0, -1, pos, &rot, eff1, (u8) eff2, 0, 0, 0, NULL);
        }
        SndCall(2, 0xB, pos, 0, 0, NULL);
        break;
    case 3:
        pLog->err(0, 0, "ESP: EAT no set(type=EAT_ET_PAD)");
        break;
    case 4:
    case 5:
    case 6:
    case 7:
        if (info == NULL || eff1 == 0xD2) {
            pLog->err(0, 0, "NOT REGIST EAT EFF INFO %d", type);
            break;
        }
        info->getWepEff(wep, &eff1, &eff2);
        if (eff1 != 0xD2 && eff2 != 1) {
            EstSet(0, -1, pos, &rot, eff1, (u8) eff2, 0, 0, 0, NULL);
        }
        if (info != NULL && (info->flag & 1)) {
            SndCall(2, 0xB, pos, 0, 0, NULL);
        }
        break;
    }
}

// Event script: starts est `no` (decimal digits -> BCD id) of `owner` as an event-cut effect
// (Core_flg 0x1001), if the table exists.
void EventCutEstSet(int owner, u32 no)
{
    u8 id = (no / 10) * 16 + no % 10;

    if (EspGetEstAddr(owner, id, 1) != NULL) {
        EstSet(0, -1, NULL, NULL, owner, id, 0x1001, 0, 0, NULL);
    }
}

// Deletes the effects started by the current event cut (Core_flg 0x3001).
void EventCutEffDelete()
{
    EffectEspDelete(0x3001, 0, 0, NULL);
    EffectEspgenDelete(0x3001, 0, 0);
    EffectEfmDelete(0x3001, 0, 0);
}

// Deletes the cut effects and the whole-event effects (Core_flg 0x2001).
void EventAllEffDelete()
{
    EventCutEffDelete();
    EffectEspDelete(0x2001, 0, 0, NULL);
    EffectEspgenDelete(0x2001, 0, 0);
    EffectEfmDelete(0x2001, 0, 0);
}

// 1 when water effects are on (Status_flg[1] 0x400) and the point is not in a flagged effect area.
int ChkWaterEffectEnable(Vec* pos)
{
    if (pG->Status_flg[1] & 0x400) {
        if (EffAreaCheckInRoom(pos) == 0) {
            return 1;
        }
    }
    return 0;
}

// Ganado falling into water: est 1/0x32 when the room has it, else the generic 0x10/0x8D; the
// position pointer doubles as the owner key.
void EstSetEm10WaterFall(Vec* pos)
{
    EspSeqData* head = EspGetEstAddr(1, 0x32, 1);

    if (head != NULL) {
        EstSet((int) pos, -1, NULL, NULL, 1, 0x32, 0, 0, (u32) pos, NULL);
    } else {
        EstSet((int) pos, -1, NULL, NULL, 0x10, 0x8D, 0, 0, (u32) pos, NULL);
    }
}

asm(".section .rodata; .balign 8");
