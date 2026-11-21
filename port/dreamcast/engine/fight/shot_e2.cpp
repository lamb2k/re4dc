// The shot fixture on the engine (lane eng-e1k, H-016.3): the FIGHT=1 image plays a re4ref fixture file instead of the
// village fight's own scenario, so the engine's shot is judged against the PC reference's trace of the same fixture.
//
// What the engine is given: the fixture file itself (boot file /cd/SHOT.TXT, a verbatim copy of
// tools/plays_right/fixtures/shot-ganado.txt), and nothing from the reference's run. It reads the keys re4ref reads
// (hostref/host_io.cpp host_parse_fixture) and plays them the way re4ref's main does (hostref/replay.cpp):
//   room, esl     must be the image's: r101 and the chapter's list 0 (etc/emleon00.esl), else the scene is REFUSED
//   pos, ang      Leon's placement (pG->sub_pos / sub_angle, the route)
//   weapon        must be 2 0 (the image hosts the wep02 handguns), else REFUSED
//   seed          the behaviour generator's seed, set after Leon is created and resumed (as the hill scene)
//   resume        Leon's position and yaw (floats or 0x bit patterns), idle footwork restarted at the frame, no blend
//   ticks         the run's length
//   god           Leon's life refilled at the start of every tick
//   actor e t [post]  list entry e created by the original EmSetFromList2 on tick t, before the tick's pass or (post)
//                 after the enemy table's move
//   pad t b sx sy [cx cy tl tr]  pad 0 from tick t on (GameCube button bits, raw stick units, the analog R trigger)
// Any other key (hit, sub, subctrl, ...) refuses the scene: the engine plays only real inputs, never a planted hit.
// Where the fixture says nothing the engine starts as re4ref does: no room script and no scenario tasks run, the room
// entry spawns nothing, the difficulty points are not set (re4ref does not host game.cpp: pG->point and Game_level
// stay 0), the fight route's warp flags (Item_find_flg) are not set.
//
// Controls (empty boot files next to SHOT.TXT; each makes the engine wrong on purpose, so the judgement must FAIL):
//   SHOTDMG   every life drop of an enemy is 100 more than the game's (the damage amount)
//   SHOTLATE  a weapon hit registered on an enemy is held 30 ticks (one second) before its damage is taken
// The trace is always on in this scene (LT, LE, LL lines; NOTRACE is ignored): it is a function run, never a timing run.
#include "global.h"
#include "player.h"
#include "em.h"
#include "em_set.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#include "shot_e2.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern "C" void* e1_file_load(const char* path, uint32_t* size, uint32_t align);
void RndInit(u16 seed);

E2Shot e2_shot;

static int file_there(const char* p)
{
    file_t f = fs_open(p, O_RDONLY);
    if (f < 0) return 0;
    fs_close(f);
    return 1;
}
// a fixture float: a decimal number or a 0x bit pattern (host_io.cpp fx_float)
static float fx_float(const char* t)
{
    if (t[0] == '0' && (t[1] == 'x' || t[1] == 'X')) {
        const uint32_t b = (uint32_t) strtoul(t, 0, 16);
        float f;
        memcpy(&f, &b, 4);
        return f;
    }
    return strtof(t, 0);
}
static void refuse(const char* why, const char* line)
{
    e2_shot.refused = 1;
    e1_log("E2 SHOT REFUSED: %s: %s\n", why, line);
}

void e2_shot_boot()
{
    uint32_t n = 0;
    if (!file_there("/cd/SHOT.TXT")) return;
    char* text = (char*) e1_file_load("/cd/SHOT.TXT", &n, 32);
    if (!text) { refuse("unreadable", "/cd/SHOT.TXT"); return; }
    E2Shot& s = e2_shot;
    s.active = 1;
    s.room = 0x101;
    s.ticks = 300;
    s.weapon_no = 2;
    s.esl = -1;
    char* end = text + n;
    for (char* l = text; l < end && !s.refused;) {
        char* e = (char*) memchr(l, '\n', end - l);
        if (!e) e = end;
        char line[256];
        unsigned len = (unsigned) (e - l) < sizeof(line) - 1 ? (unsigned) (e - l) : sizeof(line) - 1;
        memcpy(line, l, len);
        line[len] = 0;
        l = e + 1;
        if (char* h = strchr(line, '#')) *h = 0;
        if (char* r = strchr(line, '\r')) *r = 0;
        char key[32];
        if (sscanf(line, "%31s", key) != 1) continue;
        const char* rest = strstr(line, key) + strlen(key);
        if (!strcmp(key, "room")) s.room = strtoul(rest, 0, 0);
        else if (!strcmp(key, "pos")) sscanf(rest, "%f %f %f", &s.pos[0], &s.pos[1], &s.pos[2]);
        else if (!strcmp(key, "ang")) sscanf(rest, "%f", &s.ang);
        else if (!strcmp(key, "weapon")) sscanf(rest, "%d %d", &s.weapon_no, &s.weapon_type);
        else if (!strcmp(key, "seed")) s.seed = strtoul(rest, 0, 0);
        else if (!strcmp(key, "ticks")) s.ticks = strtoul(rest, 0, 0);
        else if (!strcmp(key, "esl")) s.esl = (int) strtol(rest, 0, 0);
        else if (!strcmp(key, "god")) s.god = 1;
        else if (!strcmp(key, "actor")) {
            char a[32] = "", b[32] = "", c[32] = "";
            const int k = sscanf(rest, "%31s %31s %31s", a, b, c);
            if (k < 1 || s.nactors >= E2_SHOT_ACTORS) { refuse("bad actor line", line); break; }
            E2ShotActor& x = s.actors[s.nactors++];
            x.entry = strtoul(a, 0, 0);
            x.tick = k >= 2 ? strtoul(b, 0, 0) : 1;
            x.post = k >= 3 && !strcmp(c, "post");
        } else if (!strcmp(key, "resume")) {
            char a[5][32], ev[16] = "";
            if (sscanf(rest, "%31s %31s %31s %31s %31s %15s", a[0], a[1], a[2], a[3], a[4], ev) < 5) { refuse("bad resume line", line); break; }
            s.has_resume = 1;
            for (int i = 0; i < 3; i++) s.resume_pos[i] = fx_float(a[i]);
            s.resume_ang = fx_float(a[3]);
            s.resume_frame = atoi(a[4]);
            s.resume_event = !strcmp(ev, "event");
        } else if (!strcmp(key, "pad")) {
            char b[32];
            int t = 0, sx = 0, sy = 0, cx = 0, cy = 0, tl = 0, tr = 0;
            const int k = sscanf(rest, "%d %31s %d %d %d %d %d %d", &t, b, &sx, &sy, &cx, &cy, &tl, &tr);
            if (k < 4 || s.npads >= E2_SHOT_PADS) { refuse("bad pad line", line); break; }
            E2ShotPad& p = s.pads[s.npads++];
            p.tick = (unsigned) t;
            p.buttons = (uint16_t) strtoul(b, 0, 0);
            p.sx = (int8_t) sx;
            p.sy = (int8_t) sy;
            p.tr = (uint8_t) tr;
            if (cx || cy || tl) { refuse("the engine's pad path carries no C stick or L trigger", line); break; }
        } else {
            refuse("fixture key not played on the engine", line);
        }
    }
    free(text);
    if (!s.refused && s.room != 0x101) refuse("the image holds room 101 only", "room");
    if (!s.refused && s.esl != 0) refuse("the image holds enemy list 0 only", "esl");
    if (!s.refused && (s.weapon_no != 2 || s.weapon_type != 0)) refuse("the image hosts weapon 2 0 only", "weapon");
    if (!s.refused && (s.ticks == 0 || s.ticks >= E1_TICKS)) refuse("ticks out of range", "ticks");
    s.ctl_dmg = file_there("/cd/SHOTDMG");
    s.ctl_late = file_there("/cd/SHOTLATE");
    e1_log("E2 SHOT: fixture /cd/SHOT.TXT (%lu B): room %03x ticks %u seed %04x esl %d god %d resume %d actors %u pads %u%s%s%s\n",
           (unsigned long) n, s.room, s.ticks, s.seed, s.esl, s.god, s.has_resume, s.nactors, s.npads,
           s.ctl_dmg ? "; CONTROL SHOTDMG: every enemy life drop 100 more" : "",
           s.ctl_late ? "; CONTROL SHOTLATE: weapon hits held 30 ticks" : "", s.refused ? "; REFUSED" : "");
    e1_log("E1 RUN function (traced): not a timing run\n");
}

// After Leon is created and the camera set up (the end of the fight image's room init): the resume, then the seed.
void e2_shot_room_init()
{
    if (!e2_shot.active || e2_shot.refused) return;
    const E2Shot& s = e2_shot;
    cPlayer* p = pPL;
    if (s.has_resume) {
        p->pos.x = s.resume_pos[0];
        p->pos.y = s.resume_pos[1];
        p->pos.z = s.resume_pos[2];
        p->pos_old = p->pos;
        p->ang.y = s.resume_ang;
        p->r_no_0 = 0;
        p->r_no_1 = 0;
        p->r_no_2 = 0;
        p->r_no_3 = 1;
        p->x4FD = 0;
        p->x4FC = (u8) s.resume_frame;
        if (s.resume_event) p->be_flag &= ~0x04000000u;
        p->matUpdate();
    }
    RndInit((u16) s.seed);
}

static void spawn(unsigned tick, int post)
{
    for (unsigned i = 0; i < e2_shot.nactors; i++) {
        const E2ShotActor& a = e2_shot.actors[i];
        if (a.tick != tick || a.post != post) continue;
        cEm* em = EmSetFromList2((int) a.entry, 1);
        if (!em || em == errEm) e1_log("E2 SHOT: list entry %02x not created (tick %u)\n", a.entry, tick);
        else e1_log("E2 SHOT: list entry %02x -> id %02x at %p (tick %u%s)\n", a.entry, em->id, (void*) em, tick, post ? " post" : "");
    }
}

// Before PadRead (re4ref's order): the creations before the tick's pass, god, the pad from the fixture's lines.
void e2_shot_tick_begin(unsigned tick, E1Pad* out)
{
    spawn(tick, 0);
    if (e2_shot.god) pG->pl_life = pG->pl_life_max;
    E1Pad p = {0, 0, 0, 0};
    for (unsigned i = 0; i < e2_shot.npads; i++) {
        const E2ShotPad& x = e2_shot.pads[i];
        if (x.tick <= tick) { p.buttons = x.buttons; p.sx = x.sx; p.sy = x.sy; p.trig_r = x.tr; }
    }
    *out = p;
}

// After the enemy table's move (re4ref: EmMgr.move, EmListWaitDelete, Status_flg[1] bit 29 cleared, then the post
// creations).
void e2_shot_after_em_move(unsigned tick)
{
    pG->Status_flg[1] &= ~0x20000000;
    spawn(tick, 1);
}
