// Engine actor and object tables (lane eng-e1, E1): the managers the hosted behaviour calls, on engine-owned arrays.
//
// The tables are arrays of records in the original layouts (cEm / cPlayer 0xDE0, cObj), allocated from the behaviour
// arena, written in place by the behaviour and read in place by the renderer (services/actor_e1.inc). Construction
// is restricted to what E1 hosts: the player (id 0, Leon) and the handgun object (ObjInitFunc slots the weapon module
// fills). The record bodies (cEm::cEm, status bits, cDmgInfo, cObj::cObj, objMove) are the original ones (em.cpp,
// obj.cpp) so the records start in the reference state.
#include "em.h"
#include "obj.h"
#include "player.h"
#include "pl_npc.h"
#include "global.h"
#include "db_log.h"
#include "e1_engine.h"
#include "route_ck.h"
#include "em_sub.h"
#include "snd.h"
#include <new>

extern "C" void ShapeMove(void* info);
void DrawOba(cModel* m);

cPlayer* pPL;
cSubChar* pSUB;
void (*EmInitFunc)(cEm* em);
void (*PlInitFunc)(cEm* em);
void (*ObjInitFunc[0x40])(cObj*);

// ---- enemy / character table ----
cEmMgr::cEmMgr() : cManager<cEm>(sizeof(cEm), 2)
{
    setName("cEmMgr");
    Guid = 0;
}
void cEmMgr::log(const char* fmt, ...) { (void) fmt; }
// The module characters (ids 1..0x3F: the partners and the enemy modules) take their archive from the engine's room
// pack (core/partner.cpp e1_em_read_search: E1 serves the partner, id 3) and run the init function its module
// registered, as the original's case 1..0xE and default branch do. The tail (serial, list entry 0xFF, be_flag 0x40 |
// 0x02000000, the id, subArc2) is the original's, for the player too (lane eng-e1b; E1's first slice left it out).
void* e1_em_read_search(u8 id);
int cEmMgr::construct(cEm* p, u32 id)
{
    if (id == 0 && pG->pl_type == 0) {
        p = new (p) cPlLeon;
    } else if (id >= 1 && id <= 0x3F) {
        p->subArc = (PlArc*) e1_em_read_search((u8) id);
        if (p->subArc == 0) return 0;
        EmInitFunc(p);
    } else {
        e1_stub_hit("cEmMgr::construct(other)", id);
        return 0;
    }
    if (p->id >= 0x10 && p->id <= 0x20) p->id = 0x10;
    p->serial = Guid;
    Guid++;
    p->emset_no = 0xFF;
    p->be_flag |= 0x40;
    p->id = id;
    p->be_flag |= 0x02000000;
    p->subArc2 = p->subArc;
    return 1;
}
int cEmMgr::arrayAlloc(u32 n)
{
    cManager<cEm>::arrayAlloc(n);
    pPL = 0;
    pSUB = 0;
    return 1;
}
void cEmMgr::destroy(cEm* p)
{
    if ((p->be_flag & 0x201) != 1) {
        return;
    }
    p->push();
    cManager<cEm>::destroy(p);
}
int cEmMgr::isBattle()
{
    // No enemies are hosted in E1: no alive work has status bit 0 (the original walks the alive list).
    int battle = 0;
    for (cEm* p = pAlive; p; p = (cEm*) p->pNext) {
        if (p != (cEm*) pPL && (p->status & 1)) battle = 1;
    }
    return battle;
}
// The characters' tick (lane eng-e1b): em.cpp's cEmMgr::move / emMove with every knob off, on the engine table.
// The player's own move runs later in the tick (core/main.cpp); emMove skips him. e1_em_move_hook counts the
// generator draws and the time of each character's move for the trace and the behaviour row.
void e1_em_move_begin(cEm* em);
void e1_em_move_end(cEm* em);
static void emMove(cEm* em)
{
    if ((em->be_flag & 0x201) != 1) {
        EmMgr.destroy(em);
        return;
    }
    if ((pG->Status_flg[1] & 0x10000000) && !(em->be_flag & 0x800)) return;
    if (em == pPL) return;
    if (em == pSUB && (pG->Stop_flg & 0x1000)) return;
    f32 dz = pPL->pos.z - em->pos.z;
    f32 dx = pPL->pos.x - em->pos.x;
    em->plDist2 = dx * dx + dz * dz;
    em->l_sub = 1e16f;
    e1_em_move_begin(em);
    em->dmg.move();
    em->move();
    if ((em->be_flag & 0x201) != 1) {
        e1_em_move_end(em);
        return;
    }
    em->be_flag &= ~0x20000000;
    ShapeMove(em->pModelInfo);
    if (em->seNo) {
        cModel* parts = em->getPartsPtr(0);
        SndCall(8, em->seNo - 1, &parts->world, em->id, 0, em);
        em->seNo = 0;
    }
    em->updateOldPos();
    EmYarareDisp(em);
    em->invisible_factor2 = 1.0f;
    e1_em_move_end(em);
}
void cEmMgr::move()
{
    dieCheck();
    RouteCk();
    if (!(pG->Stop_flg & 0x20000000)) {
        for (cEm* p = pAlive; p;) {
            cEm* cur = p;
            p = (cEm*) p->pNext;
            emMove(cur);
        }
    } else if (pSUB && !(pG->Stop_flg & 0x1000)) {
        emMove(pSUB);
    }
}
cEmMgr EmMgr;

cEm::cEm() { initWork(); }
void cEm::setStatus(int bit) { status |= 1 << bit; }
void cEm::clearStatus(int bit) { status &= ~(1 << bit); }
int cEm::checkStatus(int bit) { return (status & (1 << bit)) ? 1 : 0; }
int cEm::checkThrow() { return 0; }
void cEm::setItem(u16 item_id, u16 num, u16 item_flg, u16 auto_item_flg, u8 item_eff)
{
    Item_id = item_id;
    Item_num = num;
    Item_flg = item_flg;
    Auto_item_flg = auto_item_flg;
    itemFlag = item_eff;
}
void cEm::setNoItem()
{
    Item_id = 0xFFFF;
    Item_num = 0;
    Item_flg = 0;
    Auto_item_flg = 0;
    itemFlag = 0;
}
void cEm::move() {}
int cEm::initWork()
{
    be_flag = 0x21;
    kindid = 0;
    return 1;
}
cDmgInfo::cDmgInfo() { clear(); }
void cDmgInfo::set(int flag, int timer, u8 kind, Vec* p, f32 r, YARARE_INFO* prt)
{
    m_Flag = flag | 1;
    m_Timer = timer;
    m_Wep = kind;
    m_PosFrom = *p;
    m_Dist = r;
    m_pDamageYarare = prt;
}
void cDmgInfo::set(int flag, int timer)
{
    m_Flag = flag;
    m_Timer = timer;
}
void cDmgInfo::clear()
{
    m_Flag = 0;
    m_Timer = 0;
}
void cDmgInfo::move()
{
    if (m_Timer & 0x80) return;
    if ((m_Timer & 0x7F) == 0) return;
    m_Timer--;
    if (m_Timer == 0) m_Flag = 0;
}

// ---- object table ----
cObjMgr::cObjMgr() : cManager<cObj>(sizeof(cObj), 2)
{
    setName("cObjMgr");
    Guid = 0;
}
void cObjMgr::log(const char* fmt, ...) { (void) fmt; }
int cObjMgr::construct(cObj* p, int id)
{
    if (id > 0x3F || !ObjInitFunc[id]) {
        e1_stub_hit("cObjMgr::construct(unhosted id)", id);
        return 0;
    }
    ObjInitFunc[id](p);
    p->serial = Guid;
    Guid++;
    p->id = id;
    return 1;
}
int cObjMgr::construct(cObj* p, u32 id) { return construct(p, (int) id); }
static void objMove(cObj* p)
{
    if (!(p->be_flag & 0x20)) return;
    if ((pG->Status_flg[1] & 0x10000000) && !(p->be_flag & 0x800)) return;
    p->move();
    ShapeMove(p->pModelInfo);
    p->updateOldPos();
}
void cObjMgr::move()
{
    dieCheck();
    for (cObj* p = pAlive; p;) {
        cObj* n = p;
        p = (cObj*) p->pNext;
        objMove(n);
    }
}
void cObjMgr::destroy(cObj* p)
{
    if ((p->be_flag & 0x201) != 1) return;
    p->push();
    cManager<cObj>::destroy(p);
}
cObj::cObj()
{
    be_flag |= 0x21;
    kindid = 1;
}
cObjMgr ObjMgr;

// ---- the four record tables the headers declare per type (the old port's demand-backed forms): engine form, one
// contiguous array per room, as on the GameCube ----
#define E1_TABLE(T)                                                                                      \
    template<> int cManager<T>::arrayFree()                                                          \
    {                                                                                                \
        if (!pArray) return 0;                                                                       \
        memFree(pArray);                                                                             \
        pArray = 0;                                                                                  \
        return 1;                                                                                    \
    }                                                                                                \
    template<> int cManager<T>::arrayAlloc(u32 n)                                                    \
    {                                                                                                \
        arrayFree();                                                                                 \
        pArray = (T*) memAlloc(size * n);                                                            \
        nArray = n;                                                                                  \
        if (n) memClear(pArray, size * n);                                                           \
        return 1;                                                                                    \
    }                                                                                                \
    template<> T* cManager<T>::workAt(u32 no) { return (T*) ((u8*) pArray + size * no); }            \
    template<> bool cManager<T>::prepareWork(u32 no, u32 count) { return no < nArray && count <= nArray - no; } \
    template<> T* cManager<T>::getPrevWork(T* p)                                                     \
    {                                                                                                \
        p = (T*) ((u8*) p - size);                                                                   \
        if ((u32) p < (u32) pArray || (u32) p >= (u32) pArray + size * (nArray - 1)) return 0;       \
        return p;                                                                                    \
    }
E1_TABLE(cEm)
E1_TABLE(cObj)
E1_TABLE(cParts)
E1_TABLE(cModelInfo)
template<> void cManager<cObj>::destroyNow(cObj* p)
{
    e1_stub_hit("cManager<cObj>::destroyNow", 0);
}
