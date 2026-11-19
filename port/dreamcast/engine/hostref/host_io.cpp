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
    "usage: re4ref --tree DIR --fixture FILE [--out TRACE] [--log LOG]\n"
    "              [--control walk-speed[=k] | drop-rng[=tick] | shift-input[=n]]\n";

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
            else if (!strncmp(c, "drop-rng", 8)) { o->control = HOST_CTL_DROP_RNG; if (eq) o->tick = strtoul(eq + 1, 0, 0); }
            else if (!strncmp(c, "shift-input", 11)) { o->control = HOST_CTL_SHIFT_INPUT; if (eq) o->shift = atoi(eq + 1); }
            else { fprintf(stderr, "re4ref: unknown control %s\n%s", c, kUsage); return 0; }
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
    static const char* const kCtl[] = {"none", "walk-speed", "drop-rng", "shift-input"};
    fprintf(g_out, "# re4ref trace v1\n");
    fprintf(g_out, "H fixture=%s room=%04x seed=%04x ticks=%u fp=%s control=%s", o->fixture, f->room, f->seed,
            f->ticks, fp, kCtl[o->control]);
    if (o->control == HOST_CTL_WALK_SPEED) fprintf(g_out, ",%g", (double) o->k);
    if (o->control == HOST_CTL_DROP_RNG) fprintf(g_out, ",%u", o->tick);
    if (o->control == HOST_CTL_SHIFT_INPUT) fprintf(g_out, ",%d", o->shift);
    fputc('\n', g_out);
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
