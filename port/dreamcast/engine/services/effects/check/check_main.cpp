// Effect equivalence check (lane eng-e2): the original effect code against the native effect service, per tick, on the
// effect calls of an engine fight run.
//
//   fxcheck <data tree> <engine serial> [--ticks N] [--control drop=<k>|gravity=<x>] [--out table.txt]
//
// Inputs: the engine run's report (FX source lines: which archive and offset each registered EffData block came from;
// FXCALL lines: tick, owner, est id, parts, position, angle and the sequence seed of every EstSet). Both sides load the
// same EffData blocks from the disc tree and start the same sequences with the same seeds on the same ticks; a call
// that followed a model part is started at its recorded world position on both sides (no models here). Then each tick
// both sides run their effect frame (sequence players, then sprites) and the live sprites are compared, matched by
// spawn order: count, position (1/100 unit), size, alpha, life and animation pattern.
#include "global.h"
#include "model.h"
#include "esp.h"
#include "espgen.h"
#include "fx.h"
#include "check.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned fx_host_tick;
extern unsigned fx_check_drop;
extern float fx_check_gravity;
static unsigned cur_seed;
static unsigned seed_source() { return cur_seed; }

struct Buf { unsigned char* p; unsigned n; const unsigned char* data() const { return p; } unsigned size() const { return n; } };
static Buf read_file(const char* tree, const char* name)
{
    char path[512];
    snprintf(path, sizeof path, "%s/%s", tree, name);
    FILE* f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "missing %s\n", path); exit(2); }
    fseek(f, 0, SEEK_END); Buf d; d.n = ftell(f); fseek(f, 0, SEEK_SET);
    d.p = (unsigned char*) malloc(d.n + 64);
    if (fread(d.p, 1, d.n, f) != d.n) exit(2);
    fclose(f);
    return d;
}
static double fab(double x) { return x < 0 ? -x : x; }
static double fmx(double a, double b) { return a > b ? a : b; }
static unsigned rd32(const unsigned char* p) { unsigned v; memcpy(&v, p, 4); return v; }
// the DRS body: the first main-RAM record (as the engine loader's drs_body)
static unsigned char* drs_body(const Buf& d, unsigned* bytes)
{
    for (unsigned i = 8; i + 8 <= 64; i += 8) {
        const unsigned* rec = (const unsigned*) d.data();
        if (rec[i] == 0xFFFFFFFFu) break;
        if (rec[i] == 0) {
            *bytes = rec[i + 1];
            unsigned char* p = (unsigned char*) aligned_alloc(32, (*bytes + 31) & ~31u);
            memcpy(p, d.data() + rec[i + 3], *bytes);
            return p;
        }
    }
    return 0;
}
// every main-RAM part of a container, nested containers one level deep, 32-aligned (the engine's module loader)
static unsigned walk(const Buf& d, unsigned base, int depth, unsigned char* dst, unsigned at)
{
    for (unsigned i = 0; i < 32; i++) {
        const unsigned char* e = d.data() + base + 0x20 + 32 * i;
        if (rd32(e) == 0xFFFFFFFFu) break;
        if (rd32(e) == 0 && rd32(e + 8) == 0) {
            if (dst) memcpy(dst + at, d.data() + base + rd32(e + 12), rd32(e + 4));
            at += (rd32(e + 4) + 31u) & ~31u;
        } else if (rd32(e) == 4 && depth == 0) {
            at = walk(d, base + rd32(e + 12), 1, dst, at);
        }
    }
    return at;
}
struct Arc { const char* name; unsigned char* base; unsigned bytes; };

struct Call { unsigned tick, owner, id, parts, model, pos, seed; float x, y, z, rx, ry, rz; };
struct Live { unsigned uid; float x, y, z, size, a; unsigned life, ptn; };

int main(int argc, char** argv)
{
    if (argc < 3) { fprintf(stderr, "usage: fxcheck <tree> <engine serial> [--ticks N] [--control drop=k|gravity=x]\n"); return 2; }
    const char* tree = argv[1];
    unsigned ticks = 900;
    const char* control = "none";
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "--ticks")) ticks = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--control")) {
            control = argv[++i];
            if (!strncmp(control, "drop=", 5)) fx_check_drop = atoi(control + 5);
            if (!strncmp(control, "gravity=", 8)) fx_check_gravity = atof(control + 8);
        }
    }
    // archives, as the engine loaded them
    Arc arcs[5];
    unsigned narcs = 0;
    {
        Buf core = read_file(tree, "etc/core.das"); unsigned n = 0; unsigned char* b = drs_body(core, &n); arcs[narcs++] = {"etc/core.das", b, n};
        Buf room = read_file(tree, "st1/r101.arc"); unsigned char* r = (unsigned char*) aligned_alloc(32, (room.size() + 31) & ~31u);
        memcpy(r, room.data(), room.size()); arcs[narcs++] = {"st1/r101.arc", r, room.size()};
        Buf wep = read_file(tree, "em/wep02.drs"); b = drs_body(wep, &n); arcs[narcs++] = {"em/wep02.drs", b, n};
        Buf pl = read_file(tree, "em/pl00.drs"); b = drs_body(pl, &n); arcs[narcs++] = {"em/pl00.drs", b, n};
        Buf em = read_file(tree, "em/em15.drs"); n = walk(em, 0, 0, 0, 0); b = (unsigned char*) aligned_alloc(32, (n + 31) & ~31u);
        walk(em, 0, 0, b, 0); arcs[narcs++] = {"em/em15.drs", b, n};
    }
    orig_init();
    fx_room_init();
    fx_check_seed = seed_source;
    for (unsigned k = 0; k < narcs; k++) { fx_bind_archive(arcs[k].base, arcs[k].bytes); orig_bind_archive(arcs[k].base, arcs[k].bytes); }
    // the run's data loads and calls
    static Call calls[4096];
    unsigned ncalls = 0;
    unsigned loads = 0;
    FILE* f = fopen(argv[2], "rb");
    if (!f) return 2;
    char line[512];
    while (fgets(line, sizeof line, f)) {
        unsigned owner, off;
        char name[64];
        if (sscanf(line, "FX source: owner %x %63s +%x", &owner, name, &off) == 3) {
            for (unsigned k = 0; k < narcs; k++)
                if (!strcmp(arcs[k].name, name)) {
                    const Arc& a = arcs[k];
                    orig_data_load(a.base + off, owner);
                    native_EspDataLoad((u32) (uintptr_t) (a.base + off), owner, 0);
                    loads++;
                }
            continue;
        }
        Call c;
        int ax, ay, az, rx, ry, rz;
        if (sscanf(line, "FXCALL t=%u owner=%x id=%x parts=%x model=%u pos=%u seed=%x at=%d,%d,%d rot=%d,%d,%d", &c.tick, &c.owner,
                   &c.id, &c.parts, &c.model, &c.pos, &c.seed, &ax, &ay, &az, &rx, &ry, &rz) == 13) {
            c.x = ax; c.y = ay; c.z = az; c.rx = rx / 1000.0f; c.ry = ry / 1000.0f; c.rz = rz / 1000.0f;
            if (c.owner != 0xFFFF && ncalls < 4096) calls[ncalls++] = c;
        }
    }
    fclose(f);
    printf("fxcheck: %u data loads, %u calls (by owner and id), control %s\n", loads, ncalls, control);
    // per tick
    unsigned first_bad = ~0u, compared = 0, ticks_equal = 0, bit_equal = 0, max_live = 0;
    double worst = 0;
    unsigned next = 0;
    for (unsigned t = 0; t <= ticks; t++) {
        fx_host_tick = t;
        for (; next < ncalls && calls[next].tick == t; next++) {
            const Call& c = calls[next];
            Vec pos = {c.x, c.y, c.z}, rot = {c.rx, c.ry, c.rz};
            const int parts = c.model ? 0xFE : (int) c.parts;   // no models in the check: a model call at its position
            cur_seed = c.seed;
            orig_est_start(c.owner, c.id, parts, &pos, &rot, c.seed);
            native_EstSet(0, parts, &pos, &rot, c.owner, c.id, 0, 0, 0, 0);
        }
        orig_tick();
        fx_move();
        static Live o[ORIG_POOL], n[1024];
        unsigned no = 0, nn = 0;
        for (unsigned i = 0; i < ORIG_POOL; i++) {
            cEsp* e = orig_slot(i);
            if (!(e->m_Be_flg & 1)) continue;
            o[no++] = {orig_uid[i], e->m_Pos.x, e->m_Pos.y, e->m_Pos.z, e->m_Size_mul, e->m_Col_a, e->m_Life_time, e->m_Ptn_no};
        }
        for (unsigned i = 0; i < fx_sprites.n; i++)
            n[nn++] = {fx_sprites.uid[i], fx_sprites.px[i], fx_sprites.py[i], fx_sprites.pz[i], fx_sprites.smul[i], fx_sprites.ca[i],
                       fx_sprites.life[i], fx_sprites.ptn[i]};
        for (unsigned i = 1; i < no; i++) for (unsigned j = i; j > 0 && o[j - 1].uid > o[j].uid; j--) { Live x = o[j]; o[j] = o[j - 1]; o[j - 1] = x; }
        for (unsigned i = 1; i < nn; i++) for (unsigned j = i; j > 0 && n[j - 1].uid > n[j].uid; j--) { Live x = n[j]; n[j] = n[j - 1]; n[j - 1] = x; }
        if (no > max_live) max_live = no;
        bool ok = no == nn, bits = ok;
        for (unsigned i = 0; ok && i < no; i++) {
            const Live &a = o[i], &b = n[i];
            const double d = fmx(fab(a.x - b.x), fmx(fab(a.y - b.y), fab(a.z - b.z)));
            if (d > worst) worst = d;
            if (a.uid != b.uid || d > 0.01 || fab(a.size - b.size) > 1e-5 || fab(a.a - b.a) > 1e-3 || a.life != b.life || a.ptn != b.ptn) ok = false;
            if (memcmp(&a.x, &b.x, 12) || a.size != b.size || a.a != b.a) bits = false;
        }
        compared++;
        if (ok) ticks_equal++; else if (first_bad == ~0u) {
            first_bad = t;
            printf("first difference at tick %u: live %u original / %u native", t, no, nn);
            if (no && nn) printf("; first sprite uid %u pos %.3f,%.3f,%.3f / uid %u pos %.3f,%.3f,%.3f", o[0].uid, o[0].x,
                                                 o[0].y, o[0].z, n[0].uid, n[0].x, n[0].y, n[0].z);
            printf("\n");
        }
        if (bits) bit_equal++;
    }
    printf("ticks %u: equal %u, bit-identical %u, worst position difference %.6f, most live %u, sprites spawned native %u, "
           "original efm %u nested %u log %u, native kind1 %u efm %u\n", compared, ticks_equal, bit_equal, worst, max_live,
           (unsigned) fx_stats.spawned, orig_efm, orig_kind1, orig_log_count, (unsigned) fx_stats.kind1, (unsigned) fx_stats.efm);
    printf("EQUIVALENCE %s\n", first_bad == ~0u ? "PASS" : "FAIL");
    return first_bad == ~0u ? 0 : 1;
}
