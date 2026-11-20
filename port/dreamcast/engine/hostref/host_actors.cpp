// hostref (game side, lane eng-host2): the actors the reference hosts besides Leon (PLAYS_RIGHT.md
// "Actors"): Ashley as the partner (enemy id 3: cSubChar in pl_npc.cpp with the pl11 module's cSubAshley)
// and the Ganado (the shared em10.cpp library with the em12 / em15 per-type set files).
//
// What is here:
//   EmReadSearch    read.cpp's enemy-module lookup for the hosted modules: the archive from the data tree
//                   (em/pl11, em/em12, em/em15), the module's REL entry run once (it registers EmInitFunc),
//                   the registered init function remembered per module as setEmModule does
//   the enemy list  etc/emleonNN.esl into pG->Em_list (stage.cpp readEmList, without the old port's PS2 list
//                   rules, which are RE4DC_ knobs)
//   creation        list entries through the original EmSetFromList2; the partner through the original
//                   SubCharInit (pl_sub.cpp), as the room scripts do
//   hits            a weapon hit as pl_wep.cpp registers one (cDmgInfo::set on the actor's hit part)
//   trace           the A line per actor and the generator calls per caller (emMove is wrapped by prep.py)
//   adapters        two asm-label declarations whose argument order differs from the definition: harmless
//                   where int and float arguments travel in separate registers (PowerPC, SH-4), wrong on
//                   the i386 stack (the same trap as atari_init.h, host_em.cpp)
#include "hostref.h"
#include "global.h"
#include "main.h"
#include "em.h"
#include "em_set.h"
#include "player.h"
#include "pl_npc.h"
#include "pl_sub.h"
#include "at_sub.h"

extern void (*EmInitFunc)(cEm* em);   // em.cpp
extern "C" void pl11_prolog();        // the modules' REL entries, linked in under their own names (Makefile)
extern "C" void em12_prolog();
extern "C" void em15_prolog();
extern "C" void em16_prolog();
void SubCharInit(int type, Vec* pos, f32 ang);   // pl_sub.cpp

namespace {
struct HostModule {
    int id;
    const char* file;
    void (*prolog)();
    void* arc;
    void (*init)(cEm*);
};
HostModule g_mods[] = {
    {3, "em/pl11.drs", pl11_prolog, 0, 0},     // Ashley (EmFileTbl[3]: em/pl11 + rel/pl11)
    {0x12, "em/em12.drs", em12_prolog, 0, 0},  // the farm's Ganados
    {0x15, "em/em15.drs", em15_prolog, 0, 0},  // the village square's Ganados
    {0x16, "em/em16.drs", em16_prolog, 0, 0},  // the Ganados of the hill with Ashley (r11d)
};
const char* g_tree;
}

extern "C" void host_actors_tree(const char* tree) { g_tree = tree; }

// read.cpp EmReadSearch for the hosted modules (checkAshleyId: 3 or 5 is 3 with game_costume 0).
extern "C" void* EmReadSearch(u8 id, int, int)
{
    int want = id;
    if ((want == 3 || want == 5) && pG->game_costume == 0) want = 3;
    for (HostModule& m : g_mods) {
        if (m.id != want) continue;
        if (!m.arc) {
            uint32_t bytes = 0;
            m.arc = host_load_data(g_tree, m.file, "enemy", &bytes);
            if (!m.arc) host_fatal(2, "enemy archive %s missing", m.file);
            host_motion_bind(g_tree, m.arc, bytes);   // readEm: re4dc_motion_bind (the clips' separate keys)
            EmInitFunc = 0;
            m.prolog();   // setEmModule: pModule->prolog(), then m->pInitFunc = EmInitFunc
            m.init = EmInitFunc;
        }
        EmInitFunc = m.init;   // SearchEmModule hit: EM_INIT_FUNC = m->pInitFunc
        return m.arc;
    }
    host_stub_hit("EmReadSearch(other enemy)");
    return 0;
}

// stage.cpp readEmList: the list file into pG->Em_list (8 KiB, 256 entries of 0x20 bytes).
extern "C" int host_load_esl(int no)
{
    static const char* const kNames[8] = {"etc/emleon00.esl", "etc/emleon01.esl", "etc/emleon02.esl",
                                          "etc/emleon03.esl", "etc/emleon04.esl", "etc/emleon05.esl",
                                          "etc/emleon06.esl", "etc/emleon07.esl"};
    if (no < 0 || no > 7) return 0;
    uint32_t n = 0;
    void* p = host_load_data(g_tree, kNames[no], "enemy list", &n);
    if (!p) return 0;
    if (n > sizeof pG->Em_list) n = sizeof pG->Em_list;
    __builtin_memset(pG->Em_list, 0, sizeof pG->Em_list);
    __builtin_memcpy(pG->Em_list, p, n);
    pG->em_list_no = (s8) no;
    return 1;
}

// A list entry through the original creator (em_set.cpp EmSetFromList2: the room's checks, EM_SET_WORK,
// the first move); returns the actor or 0.
extern "C" cEm* host_spawn_entry(unsigned entry)
{
    cEm* em = EmSetFromList2((int) entry, 1);
    if (!em || em == errEm) {
        host_log("actor: list entry %02x not created", entry);
        return 0;
    }
    host_log("actor: list entry %02x -> id %02x type %02x at %08x", entry, em->id, em->type, (unsigned) (u32) em);
    return em;
}

// The partner (Ashley, SubCharInit type 1) at a recorded position and yaw.
extern "C" cEm* host_spawn_partner(const float* pos, float ang)
{
    Vec p = {pos[0], pos[1], pos[2]};
    SubCharInit(1, &p, ang);
    if (!pSUB) host_log("actor: the partner was not created");
    else host_log("actor: partner id %02x at %08x", pSUB->id, (unsigned) (u32) pSUB);
    return pSUB;
}

// A partner command as the room scripts give one (pl_sub.cpp SubCharCtrl: 0 follow, 1 wait, ...).
void SubCharCtrl(int mode, int flag);   // pl_sub.cpp
extern "C" void host_sub_ctrl(int mode, int flag)
{
    SubCharCtrl(mode, flag);
    host_log("partner: SubCharCtrl(%d, %d)", mode, flag);
}

// The actor created from list entry `entry` (em_set.cpp GetEmPtrFromList semantics: emset_no).
extern "C" cEm* host_actor_of_entry(unsigned entry)
{
    for (cEm* p = EmMgr.pAlive; p; p = (cEm*) p->pNext)
        if (p != pPL && p->emset_no == entry) return p;
    return 0;
}

// A weapon hit as pl_wep.cpp registers one for each enemy on the line of fire: cDmgInfo::set(0, 10, type,
// shooter position, the part's distance, the part); the part is the actor's own hit part (cEm::hitInfo).
extern "C" int host_hit(unsigned entry, unsigned type)
{
    cEm* em = host_actor_of_entry(entry);
    if (!em) {
        host_log("hit: no actor for list entry %02x", entry);
        return 0;
    }
    YARARE_INFO* part = &em->hitInfo;
    if (!(em->dmg.m_Flag & 1)) em->dmg.set(0, 10, (u8) type, &pPL->pos, part->rad, part);
    host_log("hit: entry %02x id %02x type %u", entry, em->id, type);
    return 1;
}

// ---- generator calls per actor: prep.py wraps em.cpp's emMove with these ----
namespace {
int g_owner_saved;
int actor_index(const cEm* em)
{
    int k = 0;
    for (cEm* p = EmMgr.pAlive; p; p = (cEm*) p->pNext) {
        if (p == pPL) continue;
        if (p == em) return k;
        ++k;
    }
    return -1;
}
}
extern "C" void host_em_move_begin(void* em)
{
    g_owner_saved = host_rnd_owner;
    const int k = actor_index((const cEm*) em);
    host_rnd_owner = k >= 0 && 5 + k < HOST_RNG_OWNERS ? 5 + k : 0;
}
extern "C" void host_em_move_end(void*)
{
    host_rnd_owner = g_owner_saved;
}

// ---- the A lines ----
static u32 fbits(f32 f) { u32 u; __builtin_memcpy(&u, &f, 4); return u; }
namespace {
struct Fnv {
    u32 h = 2166136261u;
    void word(u32 w) { h = (h ^ w) * 16777619u; }
    template<class T> void add(const T& v) { u32 w = 0; __builtin_memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4); word(w); }
};
// The motion as the slot of the actor's archive it came from (Exxx: cEm::subArc), else '?'.
void motion_slot(char* out, const cEm* em)
{
    static const char hex[] = "0123456789ABCDEF";
    const u32 a = (u32) em->Motion.pMot;
    out[0] = '-'; out[1] = 0;
    if (!a) return;
    const PlArc* arc = em->subArc;
    if (arc) {
        const u32 base = (u32) arc;
        // the archive's offset table has no count: scan the slots the per-type set files index (< 0x200)
        for (u32 i = 0; i < 0x200; i++)
            if (arc->ofs[i] && arc->ofs[i] + base == a) {
                out[0] = 'E'; out[1] = hex[(i >> 8) & 15]; out[2] = hex[(i >> 4) & 15]; out[3] = hex[i & 15]; out[4] = 0;
                return;
            }
    }
    out[0] = '?'; out[1] = 0;
}
}

// Every live enemy-list work other than the player, in alive-list order.
extern "C" void host_trace_actors(unsigned t)
{
    unsigned k = 0;
    for (cEm* p = EmMgr.pAlive; p; p = (cEm*) p->pNext) {
        if (p == pPL) continue;
        HostActorRecord r;
        __builtin_memset(&r, 0, sizeof r);
        r.t = t;
        r.k = k;
        r.id = p->id;
        r.entry = p->emset_no;
        r.pos[0] = fbits(p->pos.x); r.pos[1] = fbits(p->pos.y); r.pos[2] = fbits(p->pos.z);
        r.ang[0] = fbits(p->ang.x); r.ang[1] = fbits(p->ang.y); r.ang[2] = fbits(p->ang.z);
        motion_slot(r.mot, p);
        r.frame = fbits(p->Motion.Mot_frame);
        r.mstate = p->Motion.Mot_state;
        r.rno[0] = p->r_no_0; r.rno[1] = p->r_no_1; r.rno[2] = p->r_no_2; r.rno[3] = p->r_no_3;
        r.hp = p->hp;
        r.be = p->be_flag;
        // key state flags: the Ganado work's flags word (em10.h Em10Work.flags at cEm+0x3E0); the partner's
        // subFlags and subFlags2 (cEm+0x400, +0x402)
        if (p == pSUB) r.flags = (u32) p->subFlags | ((u32) p->subFlags2 << 16);
        else __builtin_memcpy(&r.flags, (const u8*) p + 0x3E0, 4);
        Fnv d;   // the logic trace's per-model discrete hash (logic_trace.cpp model_state) plus the life
        d.add(p->be_flag); d.add(p->stat); d.add(p->id); d.add(p->type); d.add(p->Motion.Mot_state); d.add(p->hp);
        r.ps = d.h;
        r.rng_calls = 5 + k < HOST_RNG_OWNERS ? host_rnd_owner_calls[5 + k] : 0;
        host_actor_write(&r);
        ++k;
    }
    host_rng_write(t, host_rnd_owner_calls, 5 + (int) k < HOST_RNG_OWNERS ? 5 + (int) k : HOST_RNG_OWNERS);
}

// Control follow-dist: an engine whose partner keeps k times the original's distance to Leon while she
// follows him (routine 0/1: cSubChar::moveCore -> moveMove): her ground offset from Leon is scaled after the tick.
extern "C" void host_control_follow(float k)
{
    cEm* s = pSUB;
    if (!s || !pPL || s->r_no_0 != 0 || s->r_no_1 != 1) return;
    s->pos.x = pPL->pos.x + (s->pos.x - pPL->pos.x) * k;
    s->pos.z = pPL->pos.z + (s->pos.z - pPL->pos.z) * k;
}

// ---- adapters (argument order) ----
// player.cpp declares cSubChar::registPlAction(Vec*, f32) under its CodeWarrior name with an extra int
// (the original passes `li r5, 0`): (sub, pos, int, ang) on the stack against (this, pos, ang).
void SubCharRegistPlAction(cSubChar* sub, Vec* pos, int, f32 ang) asm("registPlAction__8cSubCharP3Vecf");
void SubCharRegistPlAction(cSubChar* sub, Vec* pos, int, f32 ang)
{
    sub->registPlAction(pos, ang);
}
// em_sub.cpp declares AtSphereCapsuleCk(Vec*, f32, f32, Vec*, Vec*) under the C name; at_sub.cpp defines
// AtSphereCapsuleCk(Vec* c, Vec* p0, f32 r, f32 r2, Vec* p1). The Makefile renames em_sub.o's reference.
extern "C" u32 host_AtSphereCapsuleCkF(Vec* c, f32 r, f32 r2, Vec* p0, Vec* p1)
{
    return AtSphereCapsuleCk(c, p0, r, r2, p1);
}
