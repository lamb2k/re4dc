// dmg_vol.cpp (lane eng-e2a, 2026-11-21): the damage volumes, native. Fire, blasts, traps and the Ganados' own attack
// zones register a volume (a vertical cylinder, or a quad on the ground) with a kind and a lifetime; characters and
// objects ask each tick whether a point stands in one. The behaviour keeps registering them (dmg.cpp's cDmgMgr::set and
// cDmg::beginEvent stay hosted: what is registered, and that an event clears it, are its decisions); the table, its
// records, its tick and the point tests are the engine's (docs/engine/lanes/eng-e2a.md, item 2).
//
// - The table is the engine's record pool (pool.h, as the character, light and object tables: ENG_POOL), 20 records of
//   0x118 bytes made at room load (the fight image's managers, fight/fight_e2.cpp, as game.cpp sizes it). A record is
//   built in place as a cylinder (id 0) or a quad (id 1).
// - The tick (cDmgMgr::move): each live record's lifetime counted down, a record at 0 released; released records are
//   freed in the same tick (the original freed them over the next two passes of its sweep; a slot is reused from the
//   tick after either way, except the table's last two slots, which the original held one tick longer).
// - A point test returns the kind of the first live record (in table order) that holds the point: a cylinder by its
//   height band (centre +- half height) and its radius on the ground; a quad by the ground quad alone (the original
//   never reads its height), through the math service's quad test (HitCheckPoint4). The record's centre (the cylinder's,
//   or the quad's mean corner) is handed back.
#include "types.h"
#include "global.h"
#include "dmg.h"
#include "pool.h"
#include "math_sub.h"
#include <string.h>

extern "C" {
struct DmgCounters { u32 sets_seen, tests, hits, ticks, expired, freed, logs, debug_draws; };
DmgCounters dmg_cnt;
// Control (PC check only, svc/e2_dump.cpp RE4_SVC_CONTROL "dmgwide"): every cylinder 10% wider. The check must fail.
int dmg_control;
}

namespace eng_pool {
template <> struct traits<cDmg> {
    template <class... A> static void log(cManager<cDmg>*, const char*, A...) { dmg_cnt.logs++; }
    static void clear(cManager<cDmg>* m, cDmg* p) { memset((void*) p, 0, m->size); }
    static void dtor(cDmg* p) { p->~cDmg(); }
};
}   // namespace eng_pool
ENG_POOL(cDmg)
template <> void cManager<cDmg>::log(const char*, ...) { dmg_cnt.logs++; }

cDmgMgr::cDmgMgr() : cManager<cDmg>(0x118, 2)
{
    setName("cDmgMgr");
}

// A record built in place: id 1 a quad, any other id a cylinder; in use, its id kept.
int cDmgMgr::construct(cDmg* p, u32 id)
{
    if (id == 1) new (p) cDmgP4;
    else new (p) cDmgCyl;
    p->be_flag = 1;
    p->m_Id = id;
    return 1;
}

namespace {
// free every record the table has released (marked 0x200 / 0x600 by destroy): its destructor, then the slot
void sweep(cDmgMgr* m)
{
    for (u32 i = 0; i < m->nArray; i++) {
        cDmg* p = m->workAt(i);
        if (!(p->be_flag & 0x600)) continue;
        p->~cDmg();
        p->be_flag = 0;
        dmg_cnt.freed++;
    }
}
}   // namespace

void cDmgMgr::move()
{
    dmg_cnt.ticks++;
    sweep(this);
    for (u32 i = 0; i < nArray; i++) {
        cDmg* p = workAt(i);
        if ((p->be_flag & 0x201) != 1) continue;
        if (--p->m_Time == 0) {
            destroy(p);
            dmg_cnt.expired++;
        }
    }
    sweep(this);
}

int cDmgMgr::hitCheck(Vec* pos, Vec* out)
{
    dmg_cnt.tests++;
    for (u32 i = 0; i < nArray; i++) {
        cDmg* p = workAt(i);
        if ((p->be_flag & 0x201) != 1) continue;
        if (const int k = p->hitCheck(pos, out)) {
            dmg_cnt.hits++;
            return k;
        }
    }
    return 0;
}

int cDmgCyl::hitCheck(Vec* p, Vec* out)
{
    if (pG->Debug_flg[2] & 0x10000000) dmg_cnt.debug_draws++;   // the volume's debug drawing: not drawn
    const f32 dy = p->y - m_Pos.y, dx = p->x - m_Pos.x, dz = p->z - m_Pos.z;
    const f32 r = dmg_control == 1 ? m_Radius * 1.1f : m_Radius;
    if (dy > m_Height || dy < -m_Height || dx * dx + dz * dz > r * r) return 0;
    if (out) *out = m_Pos;
    return kind;
}

int cDmgP4::hitCheck(Vec* p, Vec* out)
{
    if (!HitCheckPoint4(p, m_Pos)) return 0;
    if (out) {
        out->x = (m_Pos[0].x + m_Pos[1].x + m_Pos[2].x + m_Pos[3].x) * 0.25f;
        out->y = (m_Pos[0].y + m_Pos[1].y + m_Pos[2].y + m_Pos[3].y) * 0.25f;
        out->z = (m_Pos[0].z + m_Pos[1].z + m_Pos[2].z + m_Pos[3].z) * 0.25f;
    }
    return kind;
}

cDmgMgr DmgMgr;
