// aimprop.cpp (lane eng-e2g): the property check of the shot's per-box test. The native answer (services/aim/aim.cpp
// aim_part_entry: hit_shape.h's capsule_in / cube_in) against the original's (src/game/em_sub.cpp emLineCapsuleCrossCk and
// emLineCubeCrossCk, with sub2.cpp's LineSphereCrossCk: the plain build's own objects) on generated cases, seeded and
// repeatable:
//   - single boxes: a part frame (a random turn, a scale 0.6 .. 1.6, now and then uneven or mirrored) and one hit box
//     (a capsule along y, x or z, or the flag-8 box), crossed by a segment built in one of these ways:
//       random     aimed near the box from 300 .. 20000 units, ending before, inside or past it;
//       steep      along the capsule's axis within 20 degrees (either way): the case knock-ganado's head capsule met;
//       graze      passing an end sphere at 98 .. 102 % of the radius;
//       spanend    aimed at the axis's ends (within 5 % of the radius along it), up to the radius across;
//       inside     starting inside the capsule or box;
//       vertical   a capsule whose axis is within 0.02 rad of straight up or down (the game's 0.01 rad rule);
//       mirrored   a box or capsule on a mirrored part frame;
//   - groups: 2 .. 6 boxes about one centre and one segment through them: the box each rule chooses (the nearest hit
//     point, the later of equals, as em_sub.cpp emLineAtCk).
// Verdict: PASS when every case agrees on hit or miss, every group on the box, and every distance from the segment's
// start to the hit point within 1 unit (the shot list's bound, aim_check.sh). The first 40 differing cases go to
// aimprop-diff.txt. Control: RE4_AIM_CONTROL=truegeom (aim.cpp's true-geometry boxes, its body before eng-e2g) must FAIL.
//
//   aimprop <out dir> [seed] [single cases] [groups]        (defaults 20261121, 40000, 10000)
#include "hostref.h"
#include "em.h"
#include "em_sub.h"
#include "db_log.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

extern "C" {
f32 aim_part_entry(const Mtx mat, const YARARE_INFO* p, const Vec* pa, const Vec* pb);
extern int aim_control;
}

// what the original objects need of the game: the log (VECNormalize's message on a zero vector)
cLogPtr pLog;
void cLog::err(int, int, const char*, ...) {}

namespace {
u32 g_rng;
u32 rnd()   // xorshift32
{
    g_rng ^= g_rng << 13;
    g_rng ^= g_rng >> 17;
    g_rng ^= g_rng << 5;
    return g_rng;
}
f32 uni(f32 lo, f32 hi) { return lo + (hi - lo) * (f32) ((rnd() >> 8) * (1.0 / 16777216.0)); }
Vec vec(f32 x, f32 y, f32 z) { Vec v = {x, y, z}; return v; }
Vec add(Vec a, Vec b) { return vec(a.x + b.x, a.y + b.y, a.z + b.z); }
Vec sub(Vec a, Vec b) { return vec(a.x - b.x, a.y - b.y, a.z - b.z); }
Vec mul(Vec a, f32 s) { return vec(a.x * s, a.y * s, a.z * s); }
f32 dot(Vec a, Vec b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
Vec cross(Vec a, Vec b) { return vec(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
f32 len(Vec a) { return sqrtf(dot(a, a)); }
Vec unit(Vec a) { const f32 l = len(a); return l > 0.0f ? mul(a, 1.0f / l) : vec(0, 1, 0); }
Vec rand_dir()
{
    for (;;) {
        const Vec v = vec(uni(-1, 1), uni(-1, 1), uni(-1, 1));
        const f32 l = len(v);
        if (l > 0.05f && l <= 1.0f) return mul(v, 1.0f / l);
    }
}
Vec perp(Vec d)   // a unit vector across d, at a random angle about it
{
    const Vec r = rand_dir();
    return unit(sub(r, mul(d, dot(r, d))));
}
// rotation about a unit axis by an angle into rows of m (3x3 part)
void rot(Mtx m, Vec ax, f32 ang)
{
    const f32 c = cosf(ang), s = sinf(ang), t = 1.0f - c, x = ax.x, y = ax.y, z = ax.z;
    m[0][0] = t * x * x + c;     m[0][1] = t * x * y - s * z; m[0][2] = t * x * z + s * y;
    m[1][0] = t * x * y + s * z; m[1][1] = t * y * y + c;     m[1][2] = t * y * z - s * x;
    m[2][0] = t * x * z - s * y; m[2][1] = t * y * z + s * x; m[2][2] = t * z * z + c;
}
Vec mpoint(const Mtx m, Vec p)
{
    return vec(m[0][0] * p.x + m[0][1] * p.y + m[0][2] * p.z + m[0][3], m[1][0] * p.x + m[1][1] * p.y + m[1][2] * p.z + m[1][3],
               m[2][0] * p.x + m[2][1] * p.y + m[2][2] * p.z + m[2][3]);
}

enum Kind { RANDOM, STEEP, GRAZE, SPANEND, INSIDE, VERTICAL, MIRRORED, NKIND };
const char* kname[NKIND] = {"random", "steep", "graze", "spanend", "inside", "vertical", "mirrored"};

struct Case {
    Mtx m;
    YARARE_INFO box;
    Vec top, bot;   // the capsule's ends in the world (the original's construction)
    f32 r;          // its radius
};

// a part frame: a random turn (or a near-vertical one), a scale, now and then uneven or mirrored; at `at`
void make_frame(Mtx m, Kind k, Vec at)
{
    if (k == VERTICAL) {
        // the capsule's axis (the frame's y for flags 1) within 0.02 rad of up, or of down
        const Vec h = unit(vec(uni(-1, 1), 0.0f, uni(-1, 1)));
        rot(m, h, uni(0.0f, 0.02f) + (rnd() & 1 ? 3.14159265f - 0.02f : 0.0f));
    } else {
        rot(m, rand_dir(), uni(0.0f, 6.2831853f));
    }
    f32 s[3];
    s[0] = s[1] = s[2] = uni(0.6f, 1.6f);
    if (rnd() % 10 == 0) { s[1] *= uni(0.7f, 1.4f); s[2] *= uni(0.7f, 1.4f); }
    if (k == MIRRORED) s[rnd() % 3] *= -1.0f;
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) m[i][j] *= s[j];
    m[0][3] = at.x, m[1][3] = at.y, m[2][3] = at.z;
}

void make_box(Case& c, Kind k, bool cube)
{
    memset(&c.box, 0, sizeof c.box);
    c.box.ofs = vec(uni(-200, 200), uni(-200, 200), uni(-200, 200));
    c.box.width = uni(30, 300);
    // a zero height now and then (a sphere; a flat box), but never for a box a segment must start inside: a flat box has
    // no inside, and a start on its plane is decided by rounding in either form (26 such cases in the first run)
    c.box.height = rnd() % 20 == 0 && !(cube && k == INSIDE) ? 0.0f : uni(1, 500);
    if (cube) {
        c.box.flags = 9;
        c.box.depth = uni(30, 300);
    } else {
        const u32 ax = k == VERTICAL ? 0 : rnd() % 3;
        c.box.flags = ax == 0 ? 1 : ax == 1 ? 3 : 5;
    }
    Vec top = c.box.ofs, bot = c.box.ofs;
    if (c.box.flags & 6) { if (c.box.flags & 2) top.x += c.box.height; else top.z += c.box.height; }
    else top.y += c.box.height;
    PSMTXMultVec(c.m, &top, &c.top);
    PSMTXMultVec(c.m, &bot, &c.bot);
    Vec s = {0.0f, 0.0f, c.box.width};
    PSMTXMultVecSR(c.m, &s, &s);
    c.r = PSVECMag(&s);
}

// the segment a -> b for a case of kind k
void make_line(const Case& c, Kind k, Vec* a, Vec* b)
{
    const bool cube = c.box.flags & 8;
    const Vec mid = cube ? mpoint(c.m, add(c.box.ofs, vec(0, c.box.height * 0.5f, 0))) : mul(add(c.top, c.bot), 0.5f);
    const Vec ax = sub(c.top, c.bot);
    const f32 axl = len(ax);
    const f32 size = cube ? len(sub(mpoint(c.m, c.box.ofs), mpoint(c.m, add(c.box.ofs, vec(c.box.width, c.box.height, c.box.depth)))))
                          : c.r + axl * 0.5f;
    Vec target = add(mid, mul(rand_dir(), uni(0, 1.5f) * size)), dir = rand_dir();
    switch (k) {
    case STEEP:
        if (!cube && axl > 0.0f) {
            const Vec u = mul(ax, (rnd() & 1 ? 1.0f : -1.0f) / axl);
            dir = unit(add(u, mul(perp(u), tanf(uni(0.0f, 0.349f)))));
            target = add(add(c.bot, mul(ax, uni(-0.2f, 1.2f))), mul(perp(u), uni(0, 1.2f) * c.r));
        }
        break;
    case GRAZE: {
        const Vec e = cube ? mid : (rnd() & 1 ? c.top : c.bot);
        target = add(e, mul(perp(dir), (cube ? size * 0.5f : c.r) * uni(0.98f, 1.02f)));
        break;
    }
    case SPANEND:
        if (!cube && axl > 0.0f) {
            const Vec u = mul(ax, 1.0f / axl);
            target = add(add(rnd() & 1 ? c.top : c.bot, mul(u, uni(-0.05f, 0.05f) * c.r)), mul(perp(u), uni(0, 1.0f) * c.r));
        }
        break;
    case INSIDE: {
        Vec in;
        if (cube) in = mpoint(c.m, add(c.box.ofs, vec(uni(-0.9f, 0.9f) * c.box.width, uni(0.05f, 0.95f) * c.box.height,
                                                     uni(-0.9f, 0.9f) * c.box.depth)));
        else in = add(add(c.bot, mul(ax, uni(0, 1))), mul(perp(axl > 0.0f ? unit(ax) : vec(0, 1, 0)), uni(0, 0.9f) * c.r));
        *a = in;
        *b = add(in, mul(rand_dir(), uni(300, 20000)));
        return;
    }
    default:
        break;
    }
    const f32 L = uni(300, 20000);
    *a = sub(target, mul(dir, L));
    *b = add(*a, mul(dir, L * uni(0.2f, 3.0f)));
}

// one box's two answers: hit or not, and the distance from a to the hit point
struct Ans { int hit; f32 dist; };
Ans original(const Case& c, Vec a, Vec b)
{
    Vec hit = {0, 0, 0}, top = c.top, bot = c.bot, ofs = c.box.ofs;
    int r;
    if (c.box.flags & 8) r = emLineCubeCrossCk(&a, &b, (f32(*)[4]) c.m, c.box.width, c.box.height, c.box.depth, &ofs, &hit);
    else r = emLineCapsuleCrossCk(&a, &b, &top, &bot, c.r, &hit);
    Ans o = {r, r ? len(sub(hit, a)) : 0.0f};
    return o;
}
Ans native(const Case& c, Vec a, Vec b)
{
    const f32 t = aim_part_entry(c.m, &c.box, &a, &b);
    Ans o = {t >= 0.0f, 0.0f};
    if (o.hit) o.dist = len(mul(sub(b, a), t));
    return o;
}

struct Tally { unsigned cases, same, hitmiss, over; float maxd; } T[NKIND + 2];
FILE* g_diff;
unsigned g_ndiff;
void diff_line(const char* what, unsigned n, const Case& c, Vec a, Vec b, Ans o, Ans w)
{
    if (!g_diff || g_ndiff++ >= 40) return;
    fprintf(g_diff, "%s %u flags %x w %.6g h %.6g d %.6g r %.6g top %.6g %.6g %.6g bot %.6g %.6g %.6g a %.6g %.6g %.6g b %.6g %.6g %.6g"
                    " original %d %.4f native %d %.4f\n", what, n, c.box.flags, c.box.width, c.box.height, c.box.depth, c.r,
            c.top.x, c.top.y, c.top.z, c.bot.x, c.bot.y, c.bot.z, a.x, a.y, a.z, b.x, b.y, b.z, o.hit, o.dist, w.hit, w.dist);
}
}   // namespace

int main(int argc, char** argv)
{
    if (argc < 2) { fprintf(stderr, "aimprop <out dir> [seed] [cases] [groups]\n"); return 2; }
    const u32 seed = argc > 2 ? (u32) strtoul(argv[2], 0, 0) : 20261121u;
    const unsigned ncase = argc > 3 ? (unsigned) atoi(argv[3]) : 40000u, ngroup = argc > 4 ? (unsigned) atoi(argv[4]) : 10000u;
    const char* ctl = getenv("RE4_AIM_CONTROL");
    if (ctl && !strcmp(ctl, "truegeom")) aim_control = 2;
    g_rng = seed ? seed : 1;
    char path[512];
    snprintf(path, sizeof path, "%s/aimprop-diff.txt", argv[1]);
    g_diff = fopen(path, "w");
    for (unsigned n = 0; n < ncase; n++) {
        const Kind k = (Kind) (n % NKIND);
        Case c;
        make_frame(c.m, k, vec(uni(-20000, 20000), uni(-2000, 4000), uni(-20000, 20000)));
        make_box(c, k, k != VERTICAL && k != STEEP && k != SPANEND && rnd() % 4 == 0);
        Vec a, b;
        make_line(c, k, &a, &b);
        const Ans o = original(c, a, b), w = native(c, a, b);
        Tally& t = T[k];
        t.cases++;
        const bool hm = o.hit != w.hit;
        const float d = o.hit && w.hit ? fabsf(o.dist - w.dist) : 0.0f;
        if (d > t.maxd) t.maxd = d;
        t.hitmiss += hm;
        t.over += d > 1.0f;
        if (!hm && d <= 1.0f) t.same++;
        else diff_line(kname[k], n, c, a, b, o, w);
    }
    // groups: the box each rule chooses
    Tally& g = T[NKIND];
    for (unsigned n = 0; n < ngroup; n++) {
        const int K = 2 + (int) (rnd() % 5);
        const Vec centre = vec(uni(-20000, 20000), uni(-2000, 4000), uni(-20000, 20000));
        Case c[6];
        for (int i = 0; i < K; i++) {
            const Kind k = (Kind) (rnd() % 3 == 0 ? VERTICAL : RANDOM);
            make_frame(c[i].m, k, add(centre, vec(uni(-300, 300), uni(-300, 300), uni(-300, 300))));
            make_box(c[i], k, rnd() % 5 == 0);
        }
        const Vec dir = rand_dir(), target = add(centre, mul(rand_dir(), uni(0, 400)));
        const f32 L = uni(300, 20000);
        const Vec a = sub(target, mul(dir, L)), b = add(a, mul(dir, L * uni(0.5f, 3.0f)));
        int bo = -1, bw = -1;
        f32 best_o = 1e16f, best_w = 1e16f, dmax = 0.0f;
        bool hm = false;
        for (int i = 0; i < K; i++) {
            const Ans o = original(c[i], a, b), w = native(c[i], a, b);
            hm |= o.hit != w.hit;
            if (o.hit && w.hit && fabsf(o.dist - w.dist) > dmax) dmax = fabsf(o.dist - w.dist);
            if (o.hit && !(o.dist * o.dist > best_o)) { best_o = o.dist * o.dist; bo = i; }
            if (w.hit && !(w.dist * w.dist > best_w)) { best_w = w.dist * w.dist; bw = i; }
        }
        g.cases++;
        if (dmax > g.maxd) g.maxd = dmax;
        g.hitmiss += hm;
        g.over += dmax > 1.0f;
        if (bo != bw) {
            T[NKIND + 1].cases++;   // box differs
            if (g_diff && g_ndiff++ < 40) fprintf(g_diff, "group %u boxes %d chosen original %d native %d\n", n, K, bo, bw);
        }
        if (!hm && dmax <= 1.0f && bo == bw) g.same++;
    }
    unsigned bad = 0;
    snprintf(path, sizeof path, "%s/aimprop.txt", argv[1]);
    FILE* f = fopen(path, "w");
    for (int k = 0; k <= NKIND; k++) {
        const Tally& t = T[k];
        bad += t.cases - t.same;
        char line[256];
        snprintf(line, sizeof line, "%-9s cases %u same %u hit-or-miss differs %u distance over 1 unit %u max distance %.4f%s\n",
                 k < NKIND ? kname[k] : "groups", t.cases, t.same, t.hitmiss, t.over, (double) t.maxd,
                 k == NKIND ? "" : "");
        fputs(line, stdout);
        if (f) fputs(line, f);
    }
    char line[256];
    snprintf(line, sizeof line, "aimprop seed %u cases %u groups %u box differs %u control %s: %s\n", seed, ncase, ngroup,
             T[NKIND + 1].cases, ctl ? ctl : "none", bad ? "FAIL" : "PASS");
    fputs(line, stdout);
    if (f) { fputs(line, f); fclose(f); }
    if (g_diff) fclose(g_diff);
    return bad ? 1 : 0;
}
