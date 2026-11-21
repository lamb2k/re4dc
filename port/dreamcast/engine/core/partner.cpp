// E1 partner hosting and the hill scene (lane eng-e1b, E1 second slice).
//
// Ashley's original partner code (pl_npc.cpp cSubChar, the pl11 module's cSubAshley; game/hosted.mk PARTNER_SRCS)
// runs on the engine next to Leon. What the engine owns here:
// - The partner's archive (e1_em_read_search, read.cpp EmReadSearch's job): em/pl11.drs, its main-RAM parts placed in
//   the engine room pack at room load. The Dreamcast tree keeps 61 of its motion clips' keys apart, in
//   dc/mot/<crc32>-<fnv1a>.fcv (the archive's MTC table, R4MOTBL); the engine loads every listed clip at room load,
//   checks its size and header against the archive's proxy, and points the archive's offset word at the full clip,
//   so the original motion code reads the keys in place (no lease, no disc read and no lookup per tick).
// - The module entry (pl11 _prolog, linked as pl11_prolog) that registers the partner's init function.
// - The hill scene (boot option HILL): r11d, the re4ref fixture tools/plays_right/fixtures/hill-follow.txt. Leon is
//   resumed as the old game had him at t=372 (idle footwork restarted at frame 9 on tick 1), Ashley is created by the
//   original SubCharInit at her recorded position and yaw and told to follow (SubCharCtrl(1, 1) at tick 1).
// - The characters' tick (EmMgr.move, services/managers.cpp) before the player's, in gameMainLoop's order.
// - Comparison inputs (boot options): FEED (the old run's generator state at the start of every tick, FEED.BIN, as
//   re4ref --rng-feed), CTRLFOL (the control: Ashley 10% further from Leon while she follows; must fail).
// - The re4ref trace v2 lines (T, A, R), with the generator draws counted per caller.
#include "global.h"
#include "e1_clock.h"   // lane eng-clock1: the engine's clock (TMU2 counts at the reload's rate)
#include "player.h"
#include "em.h"
#include "pl_npc.h"
#include "pl_sub.h"
#include "camera.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#include <string.h>

E1Pad e1_pad_now;
int e1_scene;

#ifdef E2_BOSS
// The boss image (lane eng-boss, BOSS=1) hosts neither the partner nor the hill scene: the scene hooks do nothing.
void e1_partner_boot() {}
void e1_partner_room_init() {}
void e1_partner_tick_begin(unsigned) {}
void e1_partner_chars_move(E1Timing&) {}
void e1_partner_tick_end(unsigned) {}
void e1_trace_v2(unsigned) {}
void e1_rng_owner(int) {}
#else
extern void (*EmInitFunc)(cEm* em);
extern "C" void pl11_prolog();
void RndInit(u16 seed);
extern "C" unsigned short re4dc_rnd_state(void);

// ---- the partner's archive ----
struct HostModule {
    int id;
    const char* file;
    void (*prolog)();
    uint8_t* arc;
    uint32_t bytes, keys, clips;
    void (*init)(cEm*);
};
static HostModule mods[] = {{3, "/cd/em/pl11.drs", pl11_prolog, 0, 0, 0, 0, 0}};
uint32_t e1_partner_bytes[2];   // archive main-RAM parts, motion keys

static uint32_t rd32(const uint8_t* p) { uint32_t v; memcpy(&v, p, 4); return v; }

// Size of the main-RAM parts (type 0) of a DVD container, nested containers (type 4) one level deep, and placing
// them one after the other, 32-aligned (dvd.cpp cDvdQueue::readMain as re4ref's host_data.cpp walks it).
static uint32_t container_walk(file_t f, uint32_t base, int depth, uint8_t* dst, uint32_t at)
{
    uint32_t rec[8 * 32];
    if (fs_seek(f, base + 0x20, SEEK_SET) < 0 || fs_read(f, rec, sizeof(rec)) <= 0) return at;
    for (unsigned i = 0; i < 32; i++) {
        const uint32_t* e = rec + 8 * i;
        if (e[0] == 0xFFFFFFFFu) break;
        if (e[0] == 0 && e[2] == 0) {
            if (dst) {
                fs_seek(f, base + e[3], SEEK_SET);
                fs_read(f, dst + at, e[1]);
            }
            at += (e[1] + 31u) & ~31u;
        } else if (e[0] == 4 && depth == 0) {
            at = container_walk(f, base + e[3], 1, dst, at);
        }
    }
    return at;
}

static uint32_t prefix_bytes(const uint8_t* p) { const uint32_t n = p[2]; return ((3 + 3 * n + 3) & ~3u) + 4 + 4 * n; }

// The archive's MTC table: every listed clip's full file loaded, checked and linked in place of its proxy.
static void bind_motion_keys(HostModule& m)
{
    const uint32_t n = rd32(m.arc);
    for (uint32_t i = 0; i < n; i++) {
        if (memcmp(m.arc + 16 + 4 * n + 4 * i, "MTC", 3)) continue;
        const uint8_t* mtc = m.arc + rd32(m.arc + 16 + 4 * i);
        if (memcmp(mtc, "R4MOTBL", 7)) { e1_log("E1 partner: MTC without R4MOTBL\n"); return; }
        const uint32_t count = rd32(mtc + 12);
        for (uint32_t j = 0; j < count; j++) {
            const uint8_t* e = mtc + 32 + 20 * j;
            const uint32_t ofs = rd32(e), size = rd32(e + 4);
            char path[64];
            snprintf(path, sizeof(path), "/cd/dc/mot/%08lx-%08lx.fcv", (unsigned long) rd32(e + 8), (unsigned long) rd32(e + 12));
            uint32_t got = 0;
            uint8_t* clip = (uint8_t*) e1_file_load(path, &got, 32);
            if (!clip || got != size || memcmp(clip, m.arc + ofs, prefix_bytes(m.arc + ofs))) {
                e1_log("E1 partner: motion keys %s missing or not this archive's (%lu B, want %lu)\n", path,
                       (unsigned long) got, (unsigned long) size);
                continue;
            }
            unsigned linked = 0;
            for (uint32_t w = 0; w < n; w++) {
                uint8_t* word = m.arc + 16 + 4 * w;
                if (rd32(word) != ofs) continue;
                const uint32_t rel = (uint32_t) (uintptr_t) clip - (uint32_t) (uintptr_t) m.arc;
                memcpy(word, &rel, 4);
                linked++;
            }
            if (!linked) e1_log("E1 partner: clip %lx not in the offset table\n", (unsigned long) ofs);
            m.keys += size;
            m.clips++;
        }
    }
}

void* e1_em_read_search(u8 id)
{
    int want = id;
    if ((want == 3 || want == 5) && pG->game_costume == 0) want = 3;
    for (HostModule& m : mods) {
        if (m.id != want) continue;
        if (!m.arc) {
            file_t f = fs_open(m.file, O_RDONLY);
            if (f < 0) { e1_log("E1 partner: missing %s\n", m.file); return 0; }
            m.bytes = container_walk(f, 0, 0, 0, 0);
            m.arc = (uint8_t*) memalign(32, m.bytes);
            if (m.arc) container_walk(f, 0, 0, m.arc, 0);
            fs_close(f);
            if (!m.arc) return 0;
            bind_motion_keys(m);
            e1_partner_bytes[0] = m.bytes;
            e1_partner_bytes[1] = m.keys;
            e1_log("E1 partner: %s %lu B at %p, %lu motion clips' keys %lu B linked\n", m.file, (unsigned long) m.bytes,
                   m.arc, (unsigned long) m.clips, (unsigned long) m.keys);
            EmInitFunc = 0;
            m.prolog();   // setEmModule: the module's REL entry registers its init function
            m.init = EmInitFunc;
        }
        EmInitFunc = m.init;
        return m.arc;
    }
    e1_stub_hit("EmReadSearch(unhosted character)", id);
    return 0;
}

// ---- generator draws per caller ----
// The draws are counted from the generator's state (rnd.cpp's step, replayed here without drawing), so the calls
// inside rnd.cpp (fRand*) count as well.
static unsigned rng_calls[5 + 8], rng_owner;
static unsigned short rng_mark;
static unsigned rng_steps(unsigned short from, unsigned short to)
{
    unsigned short r = from;
    for (unsigned n = 0; n < 4096; n++) {
        if (r == to) return n;
        unsigned nn = ((unsigned char) ((r >> 1) + (r >> 8)) << 8) | (unsigned char) (r >> 1);
        unsigned m = nn & 0xFFFF;
        if (m == r) m = (nn + 0x101) & 0xFFFF;
        r = (unsigned short) m;
    }
    return 4096;
}
void e1_rng_owner(int owner)
{
    const unsigned short now = re4dc_rnd_state();
    rng_calls[rng_owner] += rng_steps(rng_mark, now);
    rng_mark = now;
    rng_owner = (unsigned) owner < 13 ? (unsigned) owner : 0;
}
static int actor_index(const cEm* em)
{
    int k = 0;
    for (cEm* p = EmMgr.pAlive; p; p = (cEm*) p->pNext) {
        if (p == pPL) continue;
        if (p == em) return k;
        ++k;
    }
    return -1;
}
static uint64_t chars_t0, chars_us;
static int chars_saved;
void e1_em_move_begin(cEm* em)
{
    chars_saved = (int) rng_owner;
    const int k = actor_index(em);
    e1_rng_owner(k >= 0 && k < 8 ? 5 + k : 0);
    chars_t0 = e1_clock_us();
}
void e1_em_move_end(cEm*)
{
    chars_us += e1_clock_us() - chars_t0;
    e1_rng_owner(chars_saved);
}

// ---- scene options ----
static unsigned short* feed;
static unsigned feed_n;
static int follow_control;
// Diagnostic arm RESUMEA (the cause of the first divergence against the old game): Ashley's idle state that the old
// run's trace does not record and a resume cannot know, taken from what the old run did next: her idle timer (m_Timer:
// it expires at t=421, a look-around, r_no_2 0x1E), her idle frame (58 at t=372) and r_no_3 0.
static int resume_hidden;
#include <dc/maple.h>
#include <dc/maple/controller.h>
// Scene choice at boot (lane eng-e1d: one disc, both scenes): the root file HILL, or the A or Start button held on the
// first controller while the program starts, selects the hill path; otherwise the village route.
static int boot_button_hill()
{
    maple_device_t* dev = maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
    if (!dev) return 0;
    cont_state_t* st = (cont_state_t*) maple_dev_status(dev);
    return st && (st->buttons & (CONT_A | CONT_START));
}
void e1_partner_boot()
{
    file_t f = fs_open("/cd/HILL", O_RDONLY);
    const int file = f >= 0, button = boot_button_hill();
    if (file) fs_close(f);
    if (file || button) {
        e1_scene = E1_SCENE_HILL;
        e1_log("E1 scene: hill path (r11d), Leon and Ashley (%s)\n", file ? "root file HILL" : "button held at boot");
    } else {
        e1_log("E1 scene: village route (hold A or Start at boot for the hill path)\n");
    }
    // FEED, both scenes (lane eng-e1d: the village route too, to show which fields depend only on the generator state
    // the old game's other draws leave at the start of a tick)
    uint32_t n = 0;
    f = fs_open("/cd/FEED.BIN", O_RDONLY);
    if (f >= 0) {
        fs_close(f);
        feed = (unsigned short*) e1_file_load("/cd/FEED.BIN", &n, 32);
        feed_n = feed ? n / 2 : 0;
        e1_log("E1 FEED: the old run's generator state at the start of %u ticks\n", feed_n);
    }
    if (e1_scene != E1_SCENE_HILL) return;
    f = fs_open("/cd/CTRLFOL", O_RDONLY);
    if (f >= 0) { fs_close(f); follow_control = 1; e1_log("E1 CONTROL: Ashley follows 10%% further from Leon\n"); }
    f = fs_open("/cd/RESUMEA", O_RDONLY);
    if (f >= 0) { fs_close(f); resume_hidden = 1; e1_log("E1 RESUMEA: Ashley's hidden idle state from the old run\n"); }
}

// After the player and the camera (gameRoomInit order), as re4ref's main does for the fixture: the resume, then the
// partner created by the room script's call.
void e1_partner_room_init()
{
    if (e1_scene != E1_SCENE_HILL) return;
    // lane eng-e1d: the behaviour generator starts where the old run's was at the resume (the fixture's seed 0x0d37,
    // hill-follow.txt; re4ref applies it the same way), so the engine compares with re4ref without a per-tick feed
    // lane eng-e1e: the SEED boot option (the game-seed control) applies here too, 0x5A5A in place of the fixture's
    RndInit(e1_game_seed_option ? 0x5A5A : 0x0d37);
    static const uint32_t resume_pos[3] = {0x469df1b2u, 0xc3841c09u, 0x465a0443u}, resume_yaw = 0xbfe89375u;
    static const uint32_t sub_pos[3] = {0x469ae1f8u, 0xc4064a5au, 0x4658bef3u}, sub_yaw = 0x3fa98f4au;
    cPlayer* p = pPL;
    memcpy(&p->pos.x, &resume_pos[0], 4);
    memcpy(&p->pos.y, &resume_pos[1], 4);
    memcpy(&p->pos.z, &resume_pos[2], 4);
    p->pos_old = p->pos;
    memcpy(&p->ang.y, &resume_yaw, 4);
    p->r_no_0 = 0;
    p->r_no_1 = 0;
    p->r_no_2 = 0;
    p->r_no_3 = 1;
    p->x4FD = 0;
    p->x4FC = 9;
    p->matUpdate();
    Vec sp;
    float sa;
    memcpy(&sp.x, &sub_pos[0], 4);
    memcpy(&sp.y, &sub_pos[1], 4);
    memcpy(&sp.z, &sub_pos[2], 4);
    memcpy(&sa, &sub_yaw, 4);
    e1_rng_owner(4);
    SubCharInit(1, &sp, sa);
    e1_rng_owner(0);
    e1_log("E1 partner: %s id %d at %p, %d %d %d\n", pSUB ? "created" : "NOT created", pSUB ? pSUB->id : -1, (void*) pSUB,
           pSUB ? (int) pSUB->pos.x : 0, pSUB ? (int) pSUB->pos.y : 0, pSUB ? (int) pSUB->pos.z : 0);
    memset(rng_calls, 0, sizeof(rng_calls));
    rng_mark = re4dc_rnd_state();
}

void e1_partner_tick_begin(unsigned tick)
{
    memset(rng_calls, 0, sizeof(rng_calls));
    rng_owner = 0;
    if (feed && tick < feed_n) RndInit(feed[tick]);
    rng_mark = re4dc_rnd_state();
    if (e1_scene != E1_SCENE_HILL) return;
    if (tick == 1) {
        e1_rng_owner(4);
        SubCharCtrl(1, 1);   // follow (control(2) clears her wait bit), as the room script leaves her
        e1_rng_owner(0);
        if (resume_hidden && pSUB) {
            pSUB->m_Timer = 48;
            pSUB->Motion.Mot_frame = 58.0f;
            pSUB->r_no_3 = 0;
        }
    }
    pG->pl_life = pG->pl_life_max;   // the fixture's `god`
}

void e1_partner_chars_move(E1Timing& tm)
{
    chars_us = 0;
    EmMgr.move();
    pG->Status_flg[1] &= ~0x20000000;
    tm.chars_us = (uint32_t) chars_us;
}

// Control (the plays-right check must fail): Ashley keeps 1.1 times the original's distance to Leon while she
// follows him (routine 0 / 1, cSubChar::moveMove), as re4ref --control follow-dist does.
void e1_partner_tick_end(unsigned)
{
    e1_rng_owner(0);
    cEm* s = pSUB;
    if (!follow_control || !s || !pPL || s->r_no_0 != 0 || s->r_no_1 != 1) return;
    s->pos.x = pPL->pos.x + (s->pos.x - pPL->pos.x) * 1.1f;
    s->pos.z = pPL->pos.z + (s->pos.z - pPL->pos.z) * 1.1f;
}

// ---- re4ref trace v2 (tools/plays_right: T, A and R lines) ----
static uint32_t fb(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
struct Fnv {
    uint32_t h = 2166136261u;
    void word(uint32_t w) { h = (h ^ w) * 16777619u; }
    template <class T> void add(const T& v) { uint32_t w = 0; memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4); word(w); }
};
static void put_slot(char* out, char kind, unsigned v, int digits)
{
    static const char hex[] = "0123456789ABCDEF";
    out[0] = kind;
    for (int i = 0; i < digits; i++) out[1 + i] = hex[(v >> (4 * (digits - 1 - i))) & 15];
    out[1 + digits] = 0;
}
static void player_slot(char* out, const void* mot)
{
    const uint32_t a = (uint32_t) (uintptr_t) mot;
    strcpy(out, "-");
    if (!mot) return;
    if (pG->pPlayer) {
        const uint32_t base = (uint32_t) (uintptr_t) pG->pPlayer;
        for (int i = 0; i < 0x100; i++)
            if (pG->pPlayer->ofs[i] && pG->pPlayer->ofs[i] + base == a) { put_slot(out, 'P', i, 2); return; }
    }
    if (pG->pWep) {
        const PlArc* w = (const PlArc*) pG->pWep;
        const uint32_t base = (uint32_t) (uintptr_t) w;
        for (int i = 0; i < 0x80; i++)
            if (w->ofs[i] && w->ofs[i] + base == a) { put_slot(out, 'W', i, 2); return; }
    }
    strcpy(out, "?");
}
static void actor_slot(char* out, const cEm* em)
{
    const uint32_t a = (uint32_t) (uintptr_t) em->Motion.pMot;
    strcpy(out, "-");
    if (!a) return;
    if (const PlArc* arc = em->subArc) {
        const uint32_t base = (uint32_t) (uintptr_t) arc;
        for (uint32_t i = 0; i < 0x200; i++)
            if (arc->ofs[i] && arc->ofs[i] + base == a) { put_slot(out, 'E', i, 3); return; }
    }
    strcpy(out, "?");
}
void e1_trace_v2(unsigned t)
{
    char line[400];
    unsigned total = 0;
    for (unsigned c : rng_calls) total += c;
    if (t == 0) {
        int n = snprintf(line, sizeof(line), "# re4ref trace v2\nH fixture=engine-e1b-hill room=%04x seed=0d37 ticks=%u fp=sh4 control=%s%s\n",
                         e1_route().room, e1_route().ticks, follow_control ? "follow-dist,1.1" : "none", feed ? " rng_feed=FEED.BIN" : "");
        e1_trace_put(line, n);
    }
    cPlayer* p = pPL;
    Fnv d, dm;
    d.add(p->be_flag); d.add(p->stat); d.add(p->id); d.add(p->type); d.add(p->Motion.Mot_state);
    const uint32_t bm = p->be_flag | 0x08000000u;
    dm.add(bm); dm.add(p->stat); dm.add(p->id); dm.add(p->type); dm.add(p->Motion.Mot_state);
    char mot[8];
    player_slot(mot, p->Motion.pMot);
    const CameraParam& c = pG->Cam.param;
    int n = snprintf(line, sizeof(line),
                     "T t=%u in=%04x,%d,%d p=%08lx,%08lx,%08lx a=%08lx,%08lx,%08lx m=%s,%08lx,%x r=%02x%02x%02x%02x be=%08lx ps=%08lx psm=%08lx "
                     "cam=%08lx,%08lx,%08lx,%08lx,%08lx,%08lx,%08lx rng=%04x/%u stub=0/00000000/-\n",
                     t, e1_pad_now.buttons, e1_pad_now.sx, e1_pad_now.sy, (unsigned long) fb(p->pos.x), (unsigned long) fb(p->pos.y),
                     (unsigned long) fb(p->pos.z), (unsigned long) fb(p->ang.x), (unsigned long) fb(p->ang.y), (unsigned long) fb(p->ang.z),
                     mot, (unsigned long) fb(p->Motion.Mot_frame), (unsigned) p->Motion.Mot_state, p->r_no_0, p->r_no_1, p->r_no_2,
                     p->r_no_3, (unsigned long) p->be_flag, (unsigned long) d.h, (unsigned long) dm.h, (unsigned long) fb(c.pos.x),
                     (unsigned long) fb(c.pos.y), (unsigned long) fb(c.pos.z), (unsigned long) fb(c.at.x), (unsigned long) fb(c.at.y),
                     (unsigned long) fb(c.at.z), (unsigned long) fb(c.fovy), re4dc_rnd_state(), total);
    e1_trace_put(line, n);
    unsigned k = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == pPL) continue;
        Fnv h;
        h.add(e->be_flag); h.add(e->stat); h.add(e->id); h.add(e->type); h.add(e->Motion.Mot_state); h.add(e->hp);
        uint32_t flags = 0;
        if (e == pSUB) flags = (uint32_t) e->subFlags | ((uint32_t) e->subFlags2 << 16);
        else memcpy(&flags, (const uint8_t*) e + 0x3E0, 4);
        actor_slot(mot, e);
        n = snprintf(line, sizeof(line),
                     "A t=%u k=%u id=%02x e=%02x p=%08lx,%08lx,%08lx a=%08lx,%08lx,%08lx m=%s,%08lx,%x r=%02x%02x%02x%02x hp=%d be=%08lx "
                     "f=%08lx ps=%08lx rc=%u\n",
                     t, k, e->id, e->emset_no, (unsigned long) fb(e->pos.x), (unsigned long) fb(e->pos.y), (unsigned long) fb(e->pos.z),
                     (unsigned long) fb(e->ang.x), (unsigned long) fb(e->ang.y), (unsigned long) fb(e->ang.z), mot,
                     (unsigned long) fb(e->Motion.Mot_frame), (unsigned) e->Motion.Mot_state, e->r_no_0, e->r_no_1, e->r_no_2,
                     e->r_no_3, (int) e->hp, (unsigned long) e->be_flag, (unsigned long) flags, (unsigned long) h.h,
                     k < 8 ? rng_calls[5 + k] : 0u);
        e1_trace_put(line, n);
        ++k;
    }
    n = snprintf(line, sizeof(line), "R t=%u other=%u pl=%u cam=%u obj=%u spawn=%u em=", t, rng_calls[0], rng_calls[1], rng_calls[2],
                 rng_calls[3], rng_calls[4]);
    for (unsigned i = 0; i < k && i < 8; i++) n += snprintf(line + n, sizeof(line) - n, i ? ",%u" : "%u", rng_calls[5 + i]);
    if (!k) n += snprintf(line + n, sizeof(line) - n, "-");
    n += snprintf(line + n, sizeof(line) - n, "\n");
    e1_trace_put(line, n);
}
#endif   // E2_BOSS
