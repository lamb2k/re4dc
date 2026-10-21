// game/at_sub.cpp: the collision primitives under atari.cpp / at_mod.cpp: plane / triangle vs
// line and swept sphere (At_poly_*), point / rect / box / sphere / capsule overlap tests, the
// polygon attribute word and its effect type, plus debug drawing of capsules and boxes.

#include "atari.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "at_sub.h"
#include "math_sub.h"
#include "dbmodule.h"
#include "eprintf.h"
#include "db_log.h"

Vec BoxTmp[16];

#define SQ_DIST(a, b) \
    (((a)->x - (b)->x) * ((a)->x - (b)->x) + ((a)->y - (b)->y) * ((a)->y - (b)->y) + ((a)->z - (b)->z) * ((a)->z - (b)->z))

// Segment point1 -> point2 against the plane through `a` with normal `n`: 1 and the crossing
// point in *out when the ends lie on opposite sides; else *out = point2 and 0.
int At_surface_line_ck(Vec* out, Vec* a, Vec* n, Vec* point1, Vec* point2)
{
    f32 d0;
    f32 d1;

    d0 = At_surface_point_rel(a, n, point1);
    d1 = At_surface_point_rel(a, n, point2);
    if (d0 * d1 < 0.0f) {
        f32 a0 = fabsf(d0);
        f32 a1 = fabsf(d1);
        InterVectorXYZ(out, point1, point2, a1 / (a0 + a1));
        return 1;
    }
    if (out) {
        *out = *point2;
    }
    return 0;
}

// 1 when the point `p` (assumed on the triangle's plane) lies inside triangle `poly`.
int At_poly_point_rel(Vec* poly, Vec* nrm, Vec* p)
{
    int next[3] = { 1, 2, 0 };
    Vec c;
    Vec b;
    Vec a;
    u32 i;

    for (i = 0; i < 3; i++) {
        PSVECSubtract(&poly[next[i]], &poly[i], &a);
        PSVECSubtract(p, &poly[i], &b);
        PSVECCrossProduct(&a, &b, &c);
        if (PSVECDotProduct(&c, nrm) < 0.0f) {
            return 0;
        }
    }
    return 1;
}

// 1 when the sphere (p, r) touches the axis-aligned box given by its min / max corners.
int At_box_sphere_ck(Vec* box, Vec* p, f32 r)
{
    static int ptbl[6][3] = {
        { 0, 2, 1 }, { 4, 5, 6 }, { 2, 6, 3 }, { 0, 1, 4 }, { 1, 3, 5 }, { 2, 0, 6 },
    };
    Vec tri[3];
    Vec n;
    f32 d;
    int i;

    for (i = 0; i < 6; i++) {
        tri[0] = box[ptbl[i][0]];
        tri[1] = box[ptbl[i][1]];
        tri[2] = box[ptbl[i][2]];
        Get_normal(tri, &n);
        d = PSVECDotProduct(&n, p) - PSVECDotProduct(&n, &tri[0]);
        if (d > r) {
            return 0;
        }
    }
    return 1;
}

// Unit normal of triangle `tri` (cross of its two edges).
void Get_normal(Vec* tri, Vec* out)
{
    Vec a;
    Vec b;

    PSVECSubtract(&tri[2], &tri[0], &a);
    PSVECSubtract(&tri[1], &tri[0], &b);
    PSVECCrossProduct(&a, &b, out);
    PSVECNormalize(out, out);
}

// Dead-stripped by the original linker (only its constant pool survives in .rodata).
static f32 At_half(f32 v)
{
    return v * 0.5f;
}

// Capsule (p0 - p1, radius r) vs axis box: samples spheres along the segment every 2r; 1 on
// any overlap.
u32 AtBoxCapsuleCk3(Vec* box, Vec* p0, f32 r, Vec* p1)
{
    Vec dir;
    Vec p;
    f32 len;
    u32 n;

    if (At_box_sphere_ck(box, p0, r)) {
        return 1;
    }
    if (At_box_sphere_ck(box, p1, r)) {
        return 1;
    }
    PSVECSubtract(p0, p1, &dir);
    len = RootSumSquare3(&dir);
    n = (u32) (len / (r + r)) + 2;
    len = len / (f32) n;
    if (len < 0.01f) {
        return 0;
    }
#line 301 "D:/Bio4/Prog/at_sub.cpp"
    VECNormalize(&dir, &dir);
    PSVECScale(&dir, &dir, len);
    p = *p1;
    n--;
    while (n-- != 0) {
        PSVECAdd(&p, &dir, &p);
        if (At_box_sphere_ck(box, &p, r)) {
            return 1;
        }
    }
    return 0;
}

// Capsule (p0 - p1, radius r) vs sphere (c, r2): sampled spheres along the segment; 1 on overlap.
u32 AtSphereCapsuleCk(Vec* c, Vec* p0, f32 r, f32 r2, Vec* p1)
{
    Vec dir;
    Vec p;
    f32 rr;
    f32 len;
    f32 d;   // the two end-point distances through one twice-set local: not tied to the dz chain
    u32 n;

    rr = (r + r2) * (r + r2);
    d = SQ_DIST(c, p0);
    if (d < rr) {
        return 1;
    }
    d = SQ_DIST(c, p1);
    if (d < rr) {
        return 1;
    }
    PSVECSubtract(p0, p1, &dir);
    len = RootSumSquare3(&dir);
    n = (u32) (len / (r2 + r2)) + 2;
    len = len / (f32) n;
    if (len < 0.01f) {
        return 0;
    }
#line 366 "D:/Bio4/Prog/at_sub.cpp"
    VECNormalize(&dir, &dir);
    PSVECScale(&dir, &dir, len);
    if (r2 < 0.01f) {
        n = 2;
    }
    p = *p1;
    n--;
    while (n-- != 0) {
        PSVECAdd(&p, &dir, &p);
        if (SQ_DIST(c, &p) < rr) {
            return 1;
        }
    }
    return 0;
}

// Debug draw of a capsule: spheres at both ends and 4 side lines.
void AtCapsuleDisp(Vec* pPosTop, Vec* pPosBot, f32 r, u32 color)
{
    Vec dir;
    Vec p;
    f32 len;
    u32 n;

    Draw_sphere(pPosTop, r, color, 1, 1);
    Draw_sphere(pPosBot, r, color, 1, 1);
    PSVECSubtract(pPosTop, pPosBot, &dir);
    len = RootSumSquare3(&dir);
    n = (u32) (len / (r + r)) + 2;
    len = len / (f32) n;
    if (len < 0.01f) {
        return;
    }
#line 418 "D:/Bio4/Prog/at_sub.cpp"
    VECNormalize(&dir, &dir);
    PSVECScale(&dir, &dir, len);
    p = *pPosBot;
    n--;
    while (n-- != 0) {
        PSVECAdd(&p, &dir, &p);
        Draw_sphere(&p, r, color, 1, 1);
    }
}

// Debug draw of a box of half sizes sx / sy / sz at `pos` in matrix `m` (12 edges).
void AtCubeDisp(Mtx m, f32 sx, f32 sy, f32 sz, Vec* pos, u32 color)
{
    Mtx mat;
    Vec c;
    Vec v[8];

    PSMTXMultVec(m, pos, &c);
    PSMTXCopy(m, mat);
    TransMatrix(mat, &c);
    color >>= 8;
    v[0].x = -sx;
    v[0].y = 0.0f;
    v[0].z = sz;
    v[1].x = sx;
    v[1].y = 0.0f;
    v[1].z = sz;
    v[2].x = sx;
    v[2].y = sy;
    v[2].z = sz;
    v[3].x = -sx;
    v[3].y = sy;
    v[3].z = sz;
    v[4].x = -sx;
    v[4].y = 0.0f;
    v[4].z = -sz;
    v[5].x = sx;
    v[5].y = 0.0f;
    v[5].z = -sz;
    v[6].x = sx;
    v[6].y = sy;
    v[6].z = -sz;
    v[7].x = -sx;
    v[7].y = sy;
    v[7].z = -sz;
    RE4DC_XM_LOAD(mat);
    RE4DC_XM_POINT(mat, &v[0], &v[0]);
    RE4DC_XM_POINT(mat, &v[1], &v[1]);
    RE4DC_XM_POINT(mat, &v[2], &v[2]);
    RE4DC_XM_POINT(mat, &v[3], &v[3]);
    RE4DC_XM_POINT(mat, &v[4], &v[4]);
    RE4DC_XM_POINT(mat, &v[5], &v[5]);
    RE4DC_XM_POINT(mat, &v[6], &v[6]);
    RE4DC_XM_POINT(mat, &v[7], &v[7]);
    Draw_line3d(&v[0], &v[1], color, 0);
    Draw_line3d(&v[1], &v[2], color, 0);
    Draw_line3d(&v[2], &v[3], color, 0);
    Draw_line3d(&v[3], &v[0], color, 0);
    Draw_line3d(&v[4], &v[5], color, 0);
    Draw_line3d(&v[5], &v[6], color, 0);
    Draw_line3d(&v[6], &v[7], color, 0);
    Draw_line3d(&v[7], &v[4], color, 0);
    Draw_line3d(&v[0], &v[4], color, 0);
    Draw_line3d(&v[1], &v[5], color, 0);
    Draw_line3d(&v[2], &v[6], color, 0);
    Draw_line3d(&v[3], &v[7], color, 0);
}

// Segment vert0 -> vert1 against one collision triangle: plane crossing, the three edge-side
// tests, then the attribute filter (flag bits 0x400..0x8000 skip polygon classes 0x40 / 0x400 /
// 0x4000 / 0x8000 / 0x400000 / 0x800000, `mask` bits skip directly). Returns the polygon's
// attribute word (never 0 on a hit) and the hit point in *out; 0 when missed.
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
// GAME_DECISION_TRACE (test builds): every scenery line test result, in call order (logic_trace.cpp).
extern "C" unsigned re4dc_dt_note(unsigned kind, unsigned a, unsigned b);
static u32 At_poly_line_ck_dt(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask);
u32 At_poly_line_ck(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask)
{
    return re4dc_dt_note(1, flag, At_poly_line_ck_dt(pd, out, poly, vert0, vert1, flag, mask));
}
#define At_poly_line_ck At_poly_line_ck_dt
#endif
u32 At_poly_line_ck(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask)
{
    Vec d0;
    Vec d1;
    Vec c;
    Vec a;
    Vec b;
    Vec* vtx = pd->vtx;
    Vec* v0 = &vtx[poly->v[0]];
    Vec* v1;
    Vec* v2;
    Vec* nrm = &pd->nrm[poly->n];
    f32 dp0;
    f32 dp1;
    f32 t;
    f32 s0;
    f32 s1;
    u32 attr;

    d0.x = vert0->x - v0->x;
    d0.y = vert0->y - v0->y;
    d0.z = vert0->z - v0->z;
    d1.x = vert1->x - v0->x;
    d1.y = vert1->y - v0->y;
    d1.z = vert1->z - v0->z;
    dp0 = d0.x * nrm->x + d0.y * nrm->y;
    dp0 += d0.z * nrm->z;
    dp1 = d1.x * nrm->x + d1.y * nrm->y;
    dp1 += d1.z * nrm->z;
    if (dp0 * dp1 > 0.0f) {
        return 0;
    }
    v1 = &vtx[poly->v[1]];
    PSVECSubtract(vert1, vert0, &a);
    PSVECSubtract(vert0, v0, &b);
    PSVECCrossProduct(&pd->edge[poly->e[0]], &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) {
        return 0;
    }
    v2 = &vtx[poly->v[2]];
    PSVECSubtract(vert0, v1, &b);
    PSVECCrossProduct(&pd->edge[poly->e[1]], &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) {
        return 0;
    }
    PSVECSubtract(vert0, v2, &b);
    PSVECCrossProduct(&pd->edge[poly->e[2]], &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) {
        return 0;
    }
    t = -dp0 / PSVECDotProduct(&a, nrm);
    if (t >= 1.0f || t < 0.0f) {
        return 0;
    }
    s0 = PSVECDotProduct(nrm, vert0) - PSVECDotProduct(nrm, v0);
    s1 = PSVECDotProduct(nrm, vert1) - PSVECDotProduct(nrm, v0);
    if (s0 * s1 < 0.0f) {
        f32 a0 = fabsf(s0);
        f32 a1 = fabsf(s1);
        InterVectorXYZ(out, vert0, vert1, a1 / (a0 + a1));
    } else if (out) {
        *out = *vert1;
    }
    attr = Get_poly_attr(poly);
    if (SEck == 0) {
        if ((flag & 0x1000) && (attr & 0x400000)) {
            return 0;
        }
        if ((flag & 0x2000) && (attr & 0x4000)) {
            return 0;
        }
        if ((flag & 0x4000) && (attr & 0x40)) {
            return 0;
        }
        if ((attr & 0x400) && !(flag & 0x8000)) {
            return 0;
        }
        if ((flag & 0x800) && (attr & 0x8000)) {
            return 0;
        }
        if ((flag & 0x8000) && (attr & 0x800000)) {
            return 0;
        }
    } else {
        if ((flag & 0x400) && (attr & 0x4000)) {
            return 0;
        }
        if ((flag & 0x800) && (attr & 0x400000)) {
            return 0;
        }
    }
    if (mask & attr) {
        return 0;
    }
    return attr | 0x01000000;
}
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
#undef At_poly_line_ck
#endif

#if defined(RE4DC_LINE_TAIL) && RE4DC_LINE_TAIL
// GAME_LINE_TAIL (game30.mk; G, collision traversal; exact): At_poly_line_ck from its t test on, for a
// polygon that passed its plane test and three edge tests (the survivors of platform/lnk_sh4.S /
// lnk2_sh4.S, which run those tests with the same float operations). dp0 and a are recomputed with
// At_poly_line_ck's expressions (contract off), the rest is its code; the call is noted in the decision
// trace as At_poly_line_ck's is. =2 (check build): At_poly_line_ck's body also runs; the results and hit
// points are compared ("LTL" lines).
static u32 lineTail(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask)
{
    Vec d0;
    Vec a;
    Vec* v0 = &pd->vtx[poly->v[0]];
    Vec* nrm = &pd->nrm[poly->n];
    f32 dp0;
    f32 t;
    f32 s0;
    f32 s1;
    u32 attr;

    d0.x = vert0->x - v0->x;
    d0.y = vert0->y - v0->y;
    d0.z = vert0->z - v0->z;
    dp0 = d0.x * nrm->x + d0.y * nrm->y;
    dp0 += d0.z * nrm->z;
    PSVECSubtract(vert1, vert0, &a);
    t = -dp0 / PSVECDotProduct(&a, nrm);
    if (t >= 1.0f || t < 0.0f) {
        return 0;
    }
    s0 = PSVECDotProduct(nrm, vert0) - PSVECDotProduct(nrm, v0);
    s1 = PSVECDotProduct(nrm, vert1) - PSVECDotProduct(nrm, v0);
    if (s0 * s1 < 0.0f) {
        f32 a0 = fabsf(s0);
        f32 a1 = fabsf(s1);
        InterVectorXYZ(out, vert0, vert1, a1 / (a0 + a1));
    } else if (out) {
        *out = *vert1;
    }
    attr = Get_poly_attr(poly);
    if (SEck == 0) {
        if ((flag & 0x1000) && (attr & 0x400000)) {
            return 0;
        }
        if ((flag & 0x2000) && (attr & 0x4000)) {
            return 0;
        }
        if ((flag & 0x4000) && (attr & 0x40)) {
            return 0;
        }
        if ((attr & 0x400) && !(flag & 0x8000)) {
            return 0;
        }
        if ((flag & 0x800) && (attr & 0x8000)) {
            return 0;
        }
        if ((flag & 0x8000) && (attr & 0x800000)) {
            return 0;
        }
    } else {
        if ((flag & 0x400) && (attr & 0x4000)) {
            return 0;
        }
        if ((flag & 0x800) && (attr & 0x400000)) {
            return 0;
        }
    }
    if (mask & attr) {
        return 0;
    }
    return attr | 0x01000000;
}
#if RE4DC_LINE_TAIL == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 ltlCalls, ltlHits, ltlMis;
#endif
extern "C" u32 At_poly_line_tail(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask)
{
#if RE4DC_LINE_TAIL == 2
    Vec ro = *out;
    Vec to = *out;
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    const u32 rr = At_poly_line_ck_dt(pd, &ro, poly, vert0, vert1, flag, mask);
#else
    const u32 rr = At_poly_line_ck(pd, &ro, poly, vert0, vert1, flag, mask);
#endif
    const u32 r = lineTail(pd, &to, poly, vert0, vert1, flag, mask);
    if (r != rr || __builtin_memcmp(&ro, &to, sizeof(Vec)) != 0) {
        ++ltlMis;
    }
    ltlHits += r != 0;
    *out = to;
    if (++ltlCalls % 1024 == 0) {
        re4dc_log("LTL calls=%u hits=%u mismatch=%u\n", ltlCalls, ltlHits, ltlMis);
    }
#else
    const u32 r = lineTail(pd, out, poly, vert0, vert1, flag, mask);
#endif
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    return re4dc_dt_note(1, flag, r);
#else
    return r;
#endif
}
#endif

// Dead-stripped by the original linker (only its constant pool survives in .rodata).
static f32 At_line_rate(f32 a, f32 b)
{
    if (a == 0.0f) {
        return 1.0f;
    }
    return b / a;
}

// Gathers the triangle's vertices / normal / attribute and runs At_poly_sphere_ck2.
u32 At_poly_sphere_ck(AtPolyData* pd, AtPoly* poly, Vec* oldPos, Vec* pos, f32 r, u32 flag, u32 mask)
{
    Vec tri[3];
    Vec n;
    u32 attr;

    tri[0].x = pd->vtx[poly->v[0]].x;
    tri[0].y = pd->vtx[poly->v[0]].y;
    tri[0].z = pd->vtx[poly->v[0]].z;
    tri[1].x = pd->vtx[poly->v[1]].x;
    tri[1].y = pd->vtx[poly->v[1]].y;
    tri[1].z = pd->vtx[poly->v[1]].z;
    tri[2].x = pd->vtx[poly->v[2]].x;
    tri[2].y = pd->vtx[poly->v[2]].y;
    tri[2].z = pd->vtx[poly->v[2]].z;
    n.x = pd->nrm[poly->n].x;
    n.y = pd->nrm[poly->n].y;
    n.z = pd->nrm[poly->n].z;
    attr = Get_poly_attr(poly);
    return At_poly_sphere_ck2(tri, &n, attr, oldPos, pos, r, flag, mask);
}

// Swept sphere (oldPos -> pos, radius r) against a front-facing triangle: a sphere ending
// within r of the plane over the face is pushed out along the normal, a rim contact along the
// nearest edge; *pos is adjusted in place. Same attribute filter as the line test. Returns the
// attribute word (0 = no contact).
u32 At_poly_sphere_ck2(Vec* tri, Vec* n, u32 attr, Vec* oldPos, Vec* pos, f32 r, u32 flag, u32 mask)
{
    Vec hp;
    Vec nn;
    f32 d;
    u32 hit;
    u32 i;

    if (PSVECDotProduct(n, oldPos) - PSVECDotProduct(n, tri) < 0.0f) {
        return 0;
    }
    d = PSVECDotProduct(n, pos) - PSVECDotProduct(n, tri);
    {
        // `hit = 99` after the fabsf (a volatile asm, so the `li` cannot move above it); the
        // rim-hit `hit = 1` of the else arm jumps into the surface-hit arm's copy (`goto hit1`),
        // the original's cross-jump survivor.
        f32 ad = fabsf(d);
        hit = 99;
        if (ad > r) {
            Vec hp2;

            if (At_surface_line_ck(&hp, tri, n, oldPos, pos)) {
                hit = 0;
                nn = *n;
                hp2 = hp;
                if (At_poly_point_rel(tri, &nn, &hp2)) {
                hit1:
                    hit = 1;
                }
            } else {
                hit = 0;
            }
        } else {
            Vec v;
            Vec hp2;

            PSVECScale(n, &hp, d);
            PSVECSubtract(pos, &hp, &hp);
            nn = *n;
            hp2 = hp;
            if (At_poly_point_rel(tri, &nn, &hp2) == 0) {
                if (flag & 0x20) {
                    hit = 0;
                } else {
                    for (i = 0; i < 3; i++) {
                        f32 len;
                        f32 dot;
                        if (attr & (1 << (i + 29))) {
                            continue;
                        }
                        PSVECSubtract(&tri[(i + 1) % 3], &tri[i], &v);
                        PSVECSubtract(pos, &tri[i], &nn);
                        len = PSVECSquareMag(&v);
                        dot = PSVECDotProduct(&nn, &v);
                        if (dot < 0.01f) {
                            continue;
                        }
                        if (len < dot) {
                            continue;
                        }
                        PSVECScale(&v, &hp, dot / len);
                        PSVECAdd(&hp, &tri[i], &hp);
                        if (PSVECSquareDistance(pos, &hp) < r * r) {
                            hit = 2;
                            break;
                        }
                    }
                    if (i == 3) {
                        hit = 0;
                    }
                }
            } else {
                goto hit1;
            }
        }
    }
    if (hit != 0) {
        if (SEck == 0) {
            if ((flag & 0x1000) && (attr & 0x400000)) {
                hit = 0;
            } else if ((flag & 0x2000) && (attr & 0x4000)) {
                hit = 0;
            } else if ((flag & 0x4000) && (attr & 0x40)) {
                hit = 0;
            } else if ((attr & 0x400) && !(flag & 0x8000)) {
                hit = 0;
            } else if ((flag & 0x8000) && (attr & 0x800000)) {
                hit = 0;
            } else if ((flag & 0x800) && (attr & 0x8000)) {
                hit = 0;
            }
        } else {
            if ((flag & 0x400) && (attr & 0x4000)) {
                hit = 0;
            } else if ((flag & 0x800) && (attr & 0x400000)) {
                hit = 0;
            }
        }
        if (mask & attr) {
            hit = 0;
        }
    }
    switch (hit) {
    case 0:
        break;
    case 1:
        PSVECScale(n, &nn, r);
        PSVECAdd(&hp, &nn, pos);
        break;
    case 2:
        PSVECSubtract(pos, &hp, &nn);
        if (PSVECDotProduct(&nn, n) > 0.0f) {
            PSVECNormalize(&nn, &nn);
            PSVECScale(&nn, &nn, r * 0.99f);
            PSVECAdd(&hp, &nn, pos);
        }
        break;
    default:
        eprintf(80, 160, 0, 0, "HIT ERROR %d", hit);
        break;
    }
    return hit;
}

// Dead-stripped by the original linker (only its constant pool survives in .rodata).
static f32 At_zero_one(f64 a)
{
    if (a != 0.0) {
        return 1.0f;
    }
    return (f32) a;
}

// The 24-bit attribute word of a polygon (attrHi << 16 | attrLo).
u32 Get_poly_attr(AtPoly* poly)
{
    return (poly->attrHi << 16) | poly->attrLo;
}

// 1 when `p` is inside the XZ quadrilateral rect[0..3] (edge cross products from corners 0 and 2).
int At_rect_point_ck(Vec* rect, Vec* p)
{
    f32 x0 = rect[0].x;
    f32 z0 = rect[0].z;
    f32 px = p->x;
    f32 pz = p->z;
    f32 x1 = rect[1].x;
    f32 z1 = rect[1].z;
    f32 x3 = rect[3].x;
    f32 z3 = rect[3].z;
    f32 dx;
    f32 dz;
    f32 ex1;
    f32 ez1;
    f32 ex3;
    f32 ez3;

    dx = px - x0;
    dz = pz - z0;
    ex1 = x1 - x0;
    ez1 = z1 - z0;
    ex3 = x3 - x0;
    ez3 = z3 - z0;
    if (ex1 * dz > ez1 * dx || ex3 * dz < ez3 * dx) {
        return 0;
    }
    x0 = rect[2].x;
    z0 = rect[2].z;
    dx = px - x0;
    dz = pz - z0;
    ex1 = x1 - x0;
    ez1 = z1 - z0;
    ex3 = x3 - x0;
    ez3 = z3 - z0;
    if (ex1 * dz < ez1 * dx || ex3 * dz > ez3 * dx) {
        return 0;
    }
    return 1;
}

// 1 when two XZ quads overlap: a corner of either inside the other, or ra's centre inside rb.
int At_rect_rect_ck(Vec* ra, Vec* rb)
{
    Vec c;
    int i;

    for (i = 0; i < 4; i++) {
        if (At_rect_point_ck(ra, &rb[i])) {
            return 1;
        }
    }
    for (i = 0; i < 4; i++) {
        if (At_rect_point_ck(rb, &ra[i])) {
            return 1;
        }
    }
    c.x = 0.0f;
    c.y = 0.0f;
    c.z = 0.0f;
    for (i = 0; i < 4; i++) {
        PSVECAdd(&c, ra, &c);
    }
    PSVECScale(&c, &c, 0.25f);
    if (At_rect_point_ck(rb, &c)) {
        return 1;
    }
    return 0;
}

// Quadrant of a relative angle: 0 front (|ang| <= 45 degrees), 1 left, 3 right, 2 behind.
int Get_ang_dir(f32 ang)
{
    if (ang > 2.3561945f || ang < -2.3561945f) {
        return 2;
    }
    if (ang > 0.78539819f) {
        return 1;
    }
    if (ang > 0.78539819f) {
        return 1;
    } else {
        int dir = 0;
        if (ang < -0.78539819f) {
            dir = 3;
        }
        return dir;
    }
}

// Dead-stripped by the original linker (only its rectangle template and constant survive).
static int At_rect_default_ck(Vec* p)
{
    Vec rect[4] = {
        { 0.0f, 0.0f, 5000.0f }, { 5000.0f, 0.0f, 0.0f }, { 0.0f, 0.0f, -5000.0f }, { -5000.0f, 0.0f, 0.0f },
    };
    if (p->y > 300.0f) {
        return 0;
    }
    return At_rect_point_ck(rect, p);
}

// Linear blend: out = a * t + b * (1 - t).
void InterVectorXYZ(Vec* out, Vec* a, Vec* b, f32 t)
{
    Vec tmp;
    f32 s = 1.0f - t;

    PSVECScale(a, &tmp, t);
    PSVECScale(b, out, s);
    PSVECAdd(out, &tmp, out);
}

// Surface effect type 0..7 of an attribute word from its bits 0x800000 (1), 0x8000 (2) and
// 0x80 (4): indexes the room's AtEffInfo table.
int EatGetEffectType(u32 attr)
{
    int type = 0;

    if (attr & 0x800000) {
        type = 1;
    }
    if (attr & 0x8000) {
        type += 2;
    }
    if (attr & 0x80) {
        type += 4;
    }
    return type;
}

// Signed distance of `p` from the plane through `a` with unit normal `n`.
f32 At_surface_point_rel(Vec* a, Vec* n, Vec* p)
{
    return PSVECDotProduct(n, p) - PSVECDotProduct(n, a);
}
