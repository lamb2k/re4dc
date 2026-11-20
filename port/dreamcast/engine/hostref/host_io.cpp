// hostref (PC side): command line, fixture file and trace output.
//
// Fixture (text, '#' comments):
//   room 0x101              room archive stN/rNNN.arc
//   pos x y z               start position (pG->sub_pos)    ang a   start yaw in radians (pG->sub_angle)
//   weapon no type          equipped weapon (2 0: the Punisher handgun, the new-game default)
//   seed 0xNNNN             generator seed (RndInit)        ticks N   ticks to run
//   resume x y z ay frame [event]
//                           after construction, continue from a recorded state: position and yaw (floats,
//                           or 0x-prefixed IEEE bit patterns as the logic trace prints them), the idle
//                           footwork restarted at `frame` with no blend; `event`: the state follows an
//                           event's end (be_flag 0x04000000 cleared, as cPlayer::endEvent0 does)
//   pad tick buttons sx sy [subx suby trigL trigR]
//                           pad 0 from that tick on (until the next pad line): GameCube PADStatus bits
//                           (A 0x100, B 0x200, X 0x400, Y 0x800, START 0x1000, Z 0x10, R 0x20, L 0x40,
//                           D-pad 1/2/4/8) and signed stick bytes (forward = +sy)
//
// Trace (text): "# re4ref trace v1", one "H" header line, then one "T" line per tick:
//   T t=<tick> in=<buttons>,<sx>,<sy> p=<x>,<y>,<z> a=<x>,<y>,<z> m=<motion>,<frame>,<state>
//     r=<r_no_0..3> be=<be_flag> ps=<discrete hash> psm=<same, draw marker set>
//     cam=<pos x,y,z>,<at x,y,z>,<fovy> rng=<state>/<calls this tick> stub=<calls>/<hash>/<names>
// Floats are written as their IEEE-754 bit patterns (8 hex digits); the comparison tool decodes them.
#include "hostref.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern FILE* host_log_file;
static FILE* g_out;

static const char* kUsage =
    "usage: re4ref --tree DIR --fixture FILE [--out TRACE] [--log LOG] [--rng-feed LOGIC_TRACE[:offset] [--stop-feed]]\n"
    "              [--control walk-speed[=k] | drop-rng[=tick] | shift-input[=n]\n"
    "                         | drop-rng-actor[=tick] | follow-dist[=k] | late-hit[=n]]\n";

extern "C" int host_parse_args(int argc, char** argv, HostOptions* o)
{
    memset(o, 0, sizeof *o);
    o->k = 1.02f;
    o->shift = 1;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--tree") && i + 1 < argc) o->tree = argv[++i];
        else if (!strcmp(argv[i], "--fixture") && i + 1 < argc) o->fixture = argv[++i];
        else if (!strcmp(argv[i], "--out") && i + 1 < argc) o->out = argv[++i];
        else if (!strcmp(argv[i], "--log") && i + 1 < argc) o->log = argv[++i];
        else if (!strcmp(argv[i], "--control") && i + 1 < argc) {
            const char* c = argv[++i];
            const char* eq = strchr(c, '=');
            if (!strncmp(c, "walk-speed", 10)) { o->control = HOST_CTL_WALK_SPEED; if (eq) o->k = strtof(eq + 1, 0); }
            else if (!strncmp(c, "drop-rng", 8) && (c[8] == 0 || c[8] == '=')) { o->control = HOST_CTL_DROP_RNG; if (eq) o->tick = strtoul(eq + 1, 0, 0); }
            else if (!strncmp(c, "shift-input", 11)) { o->control = HOST_CTL_SHIFT_INPUT; if (eq) o->shift = atoi(eq + 1); }
            else if (!strncmp(c, "drop-rng-actor", 14)) {
                // drop-rng-actor[=tick[,k]]: actor k's (A k=) first generator call at or after tick is dropped
                o->control = HOST_CTL_DROP_RNG_ACTOR;
                o->shift = 0;
                if (eq) {
                    o->tick = strtoul(eq + 1, 0, 0);
                    const char* comma = strchr(eq, ',');
                    if (comma) o->shift = atoi(comma + 1);
                }
            }
            else if (!strncmp(c, "follow-dist", 11)) { o->control = HOST_CTL_FOLLOW_DIST; o->k = 1.1f; if (eq) o->k = strtof(eq + 1, 0); }
            else if (!strncmp(c, "late-hit", 8)) { o->control = HOST_CTL_LATE_HIT; if (eq) o->shift = atoi(eq + 1); }
            else { fprintf(stderr, "re4ref: unknown control %s\n%s", c, kUsage); return 0; }
        } else if (!strcmp(argv[i], "--rng-feed") && i + 1 < argc) {
            // the old trace path, optionally :offset (old tick = reference tick + offset)
            static char path[1024];
            snprintf(path, sizeof path, "%s", argv[++i]);
            char* colon = strrchr(path, ':');
            if (colon && colon != path && colon[1] && strspn(colon + 1, "-0123456789") == strlen(colon + 1)) {
                o->rng_offset = atoi(colon + 1);
                *colon = 0;
            }
            o->rng_feed = path;
        } else if (!strcmp(argv[i], "--stop-feed")) {
            o->stop_feed = 1;
        } else {
            fputs(kUsage, stderr);
            return 0;
        }
    }
    if (!o->tree || !o->fixture) { fputs(kUsage, stderr); return 0; }
    return 1;
}

// A float as written in a fixture: decimal, or 0x + 8 hex digits = its bit pattern.
static float fx_float(const char* t)
{
    if (t[0] == '0' && (t[1] == 'x' || t[1] == 'X') && strlen(t) == 10) {
        uint32_t u = (uint32_t) strtoul(t, 0, 16);
        float f;
        memcpy(&f, &u, 4);
        return f;
    }
    return strtof(t, 0);
}

extern "C" int host_parse_fixture(const char* path, HostFixture* fx)
{
    memset(fx, 0, sizeof *fx);
    fx->room = 0x101;
    fx->weapon_no = 2;
    fx->ticks = 300;
    fx->esl = -1;
    FILE* f = fopen(path, "r");
    if (!f) { fprintf(stderr, "re4ref: cannot open %s\n", path); return 0; }
    char line[512];
    int ok = 1;
    while (fgets(line, sizeof line, f)) {
        char* h = strchr(line, '#');
        if (h) *h = 0;
        char key[32];
        if (sscanf(line, "%31s", key) != 1) continue;
        const char* rest = strstr(line, key) + strlen(key);
        if (!strcmp(key, "room")) fx->room = strtoul(rest, 0, 0);
        else if (!strcmp(key, "pos")) sscanf(rest, "%f %f %f", &fx->pos[0], &fx->pos[1], &fx->pos[2]);
        else if (!strcmp(key, "ang")) sscanf(rest, "%f", &fx->ang);
        else if (!strcmp(key, "weapon")) sscanf(rest, "%d %d", &fx->weapon_no, &fx->weapon_type);
        else if (!strcmp(key, "seed")) fx->seed = strtoul(rest, 0, 0);
        else if (!strcmp(key, "ticks")) fx->ticks = strtoul(rest, 0, 0);
        else if (!strcmp(key, "esl")) fx->esl = (int) strtol(rest, 0, 0);
        else if (!strcmp(key, "god")) fx->god = 1;
        else if (!strcmp(key, "actor")) {
            // actor <entry> [tick [post]]: create enemy-list entry <entry> (EmSetFromList2) before tick's pass
            // (default 1); `post`: after the tick's EmMgr.move (a room task that runs after the characters)
            unsigned e = 0, t = 1;
            char a[32] = "", b[32] = "", c[32] = "";
            int n = sscanf(rest, "%31s %31s %31s", a, b, c);
            if (n >= 1) e = strtoul(a, 0, 0);
            if (n >= 2) t = strtoul(b, 0, 0);
            fx->actors[fx->nactors].post = n >= 3 && !strcmp(c, "post");
            if (n < 1 || fx->nactors >= sizeof fx->actors / sizeof fx->actors[0]) {
                fprintf(stderr, "re4ref: bad actor line: %s\n", line);
                ok = 0;
                break;
            }
            fx->actors[fx->nactors].entry = e;
            fx->actors[fx->nactors].tick = t;
            fx->nactors++;
        } else if (!strcmp(key, "hit")) {
            // hit <tick> <entry> [weapon type]: a weapon hit on the actor of that list entry (pl_wep's dmg.set)
            char a[32] = "", b[32] = "", c[32] = "";
            int n = sscanf(rest, "%31s %31s %31s", a, b, c);
            if (n < 2 || fx->nhits >= sizeof fx->hits / sizeof fx->hits[0]) {
                fprintf(stderr, "re4ref: bad hit line: %s\n", line);
                ok = 0;
                break;
            }
            fx->hits[fx->nhits].tick = strtoul(a, 0, 0);
            fx->hits[fx->nhits].entry = strtoul(b, 0, 0);
            fx->hits[fx->nhits].type = n >= 3 ? strtoul(c, 0, 0) : 1;
            fx->nhits++;
        } else if (!strcmp(key, "subctrl")) {
            // subctrl <tick> <mode> [flag]: a partner command as the room scripts give one (SubCharCtrl)
            int t = 0, m = 0, fl = 0;
            if (sscanf(rest, "%d %d %d", &t, &m, &fl) < 2 || fx->nctrl >= sizeof fx->ctrls / sizeof fx->ctrls[0]) {
                fprintf(stderr, "re4ref: bad subctrl line: %s\n", line);
                ok = 0;
                break;
            }
            fx->ctrls[fx->nctrl].tick = (unsigned) t;
            fx->ctrls[fx->nctrl].mode = m;
            fx->ctrls[fx->nctrl].flag = fl;
            fx->nctrl++;
        } else if (!strcmp(key, "sub")) {
            // sub x y z ay: the partner placed after her creation (an old trace's position), as resume does for Leon
            char a[4][32];
            if (sscanf(rest, "%31s %31s %31s %31s", a[0], a[1], a[2], a[3]) < 4) {
                fprintf(stderr, "re4ref: bad sub line: %s\n", line);
                ok = 0;
                break;
            }
            for (int i = 0; i < 3; i++) fx->sub_pos[i] = fx_float(a[i]);
            fx->sub_ang = fx_float(a[3]);
            fx->nsub = 1;
        }
        else if (!strcmp(key, "resume")) {
            char a[5][32], ev[16] = "";
            if (sscanf(rest, "%31s %31s %31s %31s %31s %15s", a[0], a[1], a[2], a[3], a[4], ev) < 5) {
                fprintf(stderr, "re4ref: bad resume line: %s\n", line);
                ok = 0;
                break;
            }
            fx->has_resume = 1;
            for (int i = 0; i < 3; i++) fx->resume_pos[i] = fx_float(a[i]);
            fx->resume_ang = fx_float(a[3]);
            fx->resume_frame = atoi(a[4]);
            fx->resume_clear_event = !strcmp(ev, "event");
        }
        else if (!strcmp(key, "pad")) {
            char b[32];
            int t, sx = 0, sy = 0, cx = 0, cy = 0, tl = 0, tr = 0;
            int n = sscanf(rest, "%d %31s %d %d %d %d %d %d", &t, b, &sx, &sy, &cx, &cy, &tl, &tr);
            if (n < 4 || fx->npads >= sizeof fx->pads / sizeof fx->pads[0]) {
                fprintf(stderr, "re4ref: bad pad line: %s\n", line);
                ok = 0;
                break;
            }
            HostPad& p = fx->pads[fx->npads++];
            p.tick = (unsigned) t;
            p.button = (uint16_t) strtoul(b, 0, 0);
            p.sx = (int8_t) sx; p.sy = (int8_t) sy; p.cx = (int8_t) cx; p.cy = (int8_t) cy;
            p.tl = (uint8_t) tl; p.tr = (uint8_t) tr;
        } else {
            fprintf(stderr, "re4ref: unknown fixture key %s\n", key);
            ok = 0;
            break;
        }
    }
    fclose(f);
    return ok;
}

extern "C" int host_open_outputs(const HostOptions* o)
{
    g_out = o->out ? fopen(o->out, "w") : stdout;
    host_log_file = o->log ? fopen(o->log, "w") : stderr;
    if (!g_out || !host_log_file) { fprintf(stderr, "re4ref: cannot open the outputs\n"); return 0; }
    return 1;
}

extern "C" void host_trace_header(const HostOptions* o, const HostFixture* f, const char* fp)
{
    static const char* const kCtl[] = {"none", "walk-speed", "drop-rng", "shift-input", "drop-rng-actor",
                                       "follow-dist", "late-hit"};
    // v2 (lane eng-host2) adds the A (actor) and R (generator calls per caller) lines; the T line is v1's.
    fprintf(g_out, "# re4ref trace v2\n");
    fprintf(g_out, "H fixture=%s room=%04x seed=%04x ticks=%u fp=%s control=%s", o->fixture, f->room, f->seed,
            f->ticks, fp, kCtl[o->control]);
    if (o->control == HOST_CTL_WALK_SPEED || o->control == HOST_CTL_FOLLOW_DIST) fprintf(g_out, ",%g", (double) o->k);
    if (o->control == HOST_CTL_DROP_RNG || o->control == HOST_CTL_DROP_RNG_ACTOR) fprintf(g_out, ",%u", o->tick);
    if (o->control == HOST_CTL_DROP_RNG_ACTOR) fprintf(g_out, ",%d", o->shift);
    if (o->control == HOST_CTL_SHIFT_INPUT || o->control == HOST_CTL_LATE_HIT) fprintf(g_out, ",%d", o->shift);
    if (f->esl >= 0) fprintf(g_out, " esl=%d", f->esl);
    for (unsigned i = 0; i < f->nactors; i++) fprintf(g_out, " actor=%02x@%u", f->actors[i].entry, f->actors[i].tick);
    if (o->rng_feed) fprintf(g_out, " rng_feed=%s:%d%s", o->rng_feed, o->rng_offset, o->stop_feed ? " stop_feed" : "");
    fputc('\n', g_out);
}

// A: one hosted actor (an enemy-list work other than the player), after the tick's pass.
//   A t=<tick> k=<alive-list index> id=<enemy id> e=<list entry> p=<x,y,z> a=<x,y,z> m=<motion>,<frame>,<state>
//     r=<r_no_0..3> hp=<life> be=<be_flag> f=<actor flags> ps=<discrete hash> rc=<generator calls it made>
extern "C" void host_actor_write(const HostActorRecord* r)
{
    fprintf(g_out, "A t=%u k=%u id=%02x e=%02x p=%08x,%08x,%08x a=%08x,%08x,%08x m=%s,%08x,%x r=%02x%02x%02x%02x "
                   "hp=%d be=%08x f=%08x ps=%08x rc=%u\n",
            r->t, r->k, r->id, r->entry, r->pos[0], r->pos[1], r->pos[2], r->ang[0], r->ang[1], r->ang[2], r->mot,
            r->frame, r->mstate, r->rno[0], r->rno[1], r->rno[2], r->rno[3], r->hp, r->be, r->flags, r->ps,
            r->rng_calls);
}

// R: generator calls this tick by caller: other, player, camera, objects, spawn, then each actor (k order).
extern "C" void host_rng_write(unsigned t, const unsigned* calls, int n)
{
    fprintf(g_out, "R t=%u other=%u pl=%u cam=%u obj=%u spawn=%u em=", t, calls[0], calls[1], calls[2], calls[3],
            calls[4]);
    for (int i = 5; i < n; i++) fprintf(g_out, i > 5 ? ",%u" : "%u", calls[i]);
    if (n <= 5) fputc('-', g_out);
    fputc('\n', g_out);
}

// The generator state at the start of each tick of an old logic trace (LT t=<tick> n=.. r=<state> sy=.. sp=<Stop_flg>),
// and the Stop_flg word the scenario left there.
extern "C" int host_load_rng_feed(const char* path, unsigned short* states, unsigned* stops, unsigned char* have,
                                  unsigned max)
{
    FILE* f = fopen(path, "r");
    if (!f) { fprintf(stderr, "re4ref: cannot open the rng feed %s\n", path); return 0; }
    char line[1024];
    int n = 0;
    while (fgets(line, sizeof line, f)) {
        unsigned t, nn, r, sy = 0, sp = 0;
        const int got = sscanf(line, "LT t=%u n=%u r=%x sy=%x sp=%x", &t, &nn, &r, &sy, &sp);
        if (got >= 3 && t < max && !have[t]) {
            states[t] = (unsigned short) r;
            stops[t] = got >= 5 ? sp : 0;
            have[t] = got >= 5 ? 3 : 1;   // bit0: the generator, bit1: Stop_flg
            n++;
        }
    }
    fclose(f);
    return n;
}

extern "C" void host_trace_write(const HostTickRecord* r)
{
    fprintf(g_out, "T t=%u in=%04x,%d,%d", r->t, r->button, r->sx, r->sy);
    if (r->has_pl) {
        fprintf(g_out, " p=%08x,%08x,%08x a=%08x,%08x,%08x m=%s,%08x,%x r=%02x%02x%02x%02x be=%08x ps=%08x psm=%08x",
                r->pos[0], r->pos[1], r->pos[2], r->ang[0], r->ang[1], r->ang[2], r->mot, r->frame, r->mstate,
                r->rno[0], r->rno[1], r->rno[2], r->rno[3], r->be, r->ps, r->psm);
    } else {
        fprintf(g_out, " p=- a=- m=- r=- be=- ps=- psm=-");
    }
    fprintf(g_out, " cam=%08x,%08x,%08x,%08x,%08x,%08x,%08x rng=%04x/%u stub=%u/%08x/%s\n", r->cam[0], r->cam[1],
            r->cam[2], r->cam[3], r->cam[4], r->cam[5], r->cam[6], r->rng, r->rng_calls, r->stub_calls,
            r->stub_hash, r->stub_names);
}

extern "C" void host_close_outputs()
{
    if (g_out && g_out != stdout) fclose(g_out);
    if (host_log_file && host_log_file != stderr) fclose(host_log_file);
}
