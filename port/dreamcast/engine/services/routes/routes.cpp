// routes.cpp: the native route service (lane eng-svc4; routes.h, docs/engine/SERVICES.md section 25).
//
// What it owns (the original unit route_ck.cpp, every function it links):
//   - the room's way-point graph, read in place from the RTP sub-file at pG->Rtp: the points, each point's links and
//     the next-hop table (row = where you are, column = where you go, -1 = unreachable);
//   - the nearest reachable point of a position (the ten nearest by squared distance, then the first with a clear line
//     from 500 above the position) and its per-tick cache in the actor (RckStat bit 0, RckNear; RouteCk clears it);
//   - the next position toward an actor or a position (RouteCkToEm, RouteCkToPos: the target itself when the line is
//     clear and there is floor half way, else the next way point; the partner's follow and the enemies' chase), the
//     escape point (RouteCkEscEm), the step between two positions (RouteCkPosToPos) and the path lengths;
//   - the line test against the scenery under all of them (the native collision query, cSatMgr::hitCheck).
// Debug displays (Draw_rtp, Draw_eminfo, the route lines of debug mode 8) draw nothing: the engine's renderer has no
// debug lines; they are counted.
//
// Arithmetic: the original's, operation for operation (single precision, contraction off), so the PC reference
// compares bit for bit. The graph is the room file's: the service reads it in place and keeps no copy.
#include "route_ck.h"
#include "em.h"
#include "player.h"
#include "atari.h"
#include "global.h"
#include "math_sub.h"
#include "routes.h"

extern "C" {
RouteCounters route_cnt;
int route_control;
}

namespace {

constexpr int kNearMax = 10;        // the nearest-point search sorts this many candidates
constexpr f32 kEye = 500.0f;        // line tests start this far above the feet
constexpr f32 kArrive = 62500.0f;   // within 250 units (squared, XZ) of a way point it counts as reached
constexpr int kNoPoint = -1;

inline RtpData* graph() { return (RtpData*) pG->Rtp; }
inline const RtpPoint* points(const RtpData* r) { return (const RtpPoint*) (r->pointOfs + (u32) r); }
inline const RtpLink* links(const RtpData* r) { return (const RtpLink*) (r->linkOfs + (u32) r); }
inline const s8* hops(const RtpData* r) { return (const s8*) (r->nextOfs + (u32) r); }

// The next hop from point `at` toward point `to` (-1: unreachable). The routehop control skips the way points between:
// every reachable destination is its own next hop.
inline int hop(const RtpData* r, int at, int to)
{
    const int h = hops(r)[r->nPoint * at + to];
    return route_control == 2 && h != -1 ? to : h;
}

// The scenery between two points (non-zero: blocked). attr: the caller's body flags (route lines also hit 0x4000);
// flag bit 1 also stops at 8, without bit 2 also at 0x40000.
int line_blocked(const Vec* from, const Vec* to, int attr, int flag)
{
    route_cnt.lines++;
    Vec a = *from;
    Vec b = *to;
    if (pG->debug_mode == 8) route_cnt.debug_draws++;
    int mask = (flag & 2) ? 0x383078 : 0x383070;
    if (!(flag & 4)) mask |= 0x40000;
    return SatMgr.hitCheck(&a, &b, NULL, NULL, attr | 0x4000, mask);
}

// The nearest way point of `pos`: mode != 0 the nearest; else the nearest of the ten nearest with a clear line from
// kEye above `pos`. -1 when none.
s8 near_point(const Vec* pos, int mode, int mask)
{
    route_cnt.near_calls++;
    const RtpData* r = graph();
    if (r == NULL || r->nPoint == 0) {
        route_cnt.near_none++;
        return kNoPoint;
    }
    const int n = r->nPoint;
    const int m = n < kNearMax ? n : kNearMax;
    f32 dist[kNearMax];
    int idx[kNearMax];
    for (int i = 0; i < m; i++) {
        dist[i] = 1.0e16f;
        idx[i] = kNoPoint;
    }
    // insertion into a sorted list of m: a point goes in front of every candidate it does not exceed
    const RtpPoint* pt = points(r);
    for (int i = 0; i < n; i++, pt++) {
        const f32 d = (pos->x - pt->pos.x) * (pos->x - pt->pos.x) + (pos->y - pt->pos.y) * (pos->y - pt->pos.y) +
                      (pos->z - pt->pos.z) * (pos->z - pt->pos.z);
        if (d > dist[m - 1]) continue;
        int k = m - 1;
        for (; k > 0 && !(d > dist[k - 1]); k--) {
            dist[k] = dist[k - 1];
            idx[k] = idx[k - 1];
        }
        dist[k] = d;
        idx[k] = i;
    }
    if (mode != 0) return (s8) idx[0];
    const RtpPoint* pts = points(r);
    Vec eye = *pos;
    eye.y += kEye;
    int skip = route_control == 1 ? 1 : 0;   // routenear: the first reachable candidate passed over
    int first = kNoPoint;
    for (int i = 0; i < m; i++) {
        route_cnt.near_lines++;
        if (line_blocked(&eye,&pts[idx[i]].pos, mask, 0) == 0) {
            if (skip-- > 0) {
                first = idx[i];
                continue;
            }
            return (s8) idx[i];
        }
    }
    if (first != kNoPoint) return (s8) first;
    route_cnt.near_none++;
    return kNoPoint;
}

// The actor's nearest way point, searched once per tick (RckStat bit 0 keeps RckNear until RouteCk clears it).
int near_cached(cEm* em, int mode, int mask)
{
    if (em->RckStat & 1) {
        route_cnt.near_cached++;
        return em->RckNear;
    }
    em->RckStat |= 1;
    return near_point(&em->pos, mode, mask);
}

// A clear line from `a` to `b` with floor under its middle (within 2000 below).
bool direct_ok(Vec* a, Vec* b, int mask, int flag)
{
    if (line_blocked(a, b, mask, flag) != 0) return false;
    Vec c;
    PosToPos(a, b, &c, 0.5f);
    return SatMgr.getFloor(&c, 600.0f, 100000.0f, NULL, 0) > c.y - 2000.0f;
}

// One step of `em` toward `target` (an actor's position when `tem` is that actor, else a position): the target itself
// (returns 1) or the next way point (returns 0). `dist`: the height difference on a direct move, else the largest
// height difference from the eye to any way point left on the path.
int step(cEm* em, const Vec* target, cEm* tem, Vec* out, int flag, f32* dist)
{
    route_cnt.steps++;
    Vec a = em->pos;
    a.y += kEye;
    Vec b = *target;
    b.y += kEye;
    int mask = em->atari.m_flag;
    if (em->id == 3) flag |= 4;   // the partner's lines pass 0x40000 surfaces
    auto direct = [&]() {
        route_cnt.steps_direct++;
        *out = *target;
        if (dist != NULL) *dist = fabsf(a.y - b.y);
        return 1;
    };
    if (!(flag & 1)) {
        if (graph() == NULL) return direct();
        if (direct_ok(&a, &b, mask, flag)) return direct();
    }
    em->RckMy = em->RckNear = near_cached(em, 0, mask);
    if (tem != NULL) em->RckTo = tem->RckNear = near_cached(tem, 0, mask);
    else em->RckTo = near_point(&b, 0, mask);
    const int p = em->RckMy;
    if (p == kNoPoint) return direct();
    const int t = em->RckTo;
    if (t == kNoPoint) return direct();
    const RtpData* r = graph();
    int next = hop(r, p, t);
    if (next == kNoPoint) return direct();
    if ((flag & 1) && next == t && fabsf(a.y - b.y) < 2000.0f) {
        if (graph() == NULL || line_blocked(&a, &b, mask, flag) == 0) return direct();
    }
    mask |= 0x80;
    const RtpPoint* pts = points(r);
    const RtpPoint* at = &pts[em->RckMy];
    const f32 d2 = (em->pos.x - at->pos.x) * (em->pos.x - at->pos.x) + (em->pos.z - at->pos.z) * (em->pos.z - at->pos.z);
    if (d2 < kArrive || (next != em->RckMy && line_blocked(&a, &pts[next].pos, mask, flag) == 0)) em->RckMy = next;
    *out = pts[em->RckMy].pos;
    if (dist != NULL) {
        route_cnt.dists++;
        f32 dmax = fabsf(a.y - b.y);
        next = em->RckMy;
        while ((next = hop(r, next, em->RckTo)) != kNoPoint) {
            const f32 d = fabsf(a.y - pts[next].pos.y);
            if (d > dmax) dmax = d;
            if (next == em->RckTo) break;
        }
        *dist = dmax;
    }
    return 0;
}

}   // namespace

// ==== entry points (route_ck.h) ====

// Once per tick before the actors move: every live enemy's and the player's nearest-point cache is cleared.
void RouteCk()
{
    for (u32 i = 0; i < EmMgr.nArray; i++) {
        cEm* em = (cEm*) EmMgr.workAt(i);
        if (em != NULL && (em->be_flag & 0x201) == 1) em->RckStat = 0;
    }
    pPL->RckStat = 0;
}

int RouteCkToEm(cEm* em, cEm* target, Vec* out, int flag) { return step(em, &target->pos, target, out, flag, NULL); }

int RouteCkToPos(cEm* em, Vec* target, Vec* out, int flag, f32* dist) { return step(em, target, NULL, out, flag, dist); }

// The escape point for `em` fleeing `from`: the neighbour of its nearest way point that lies most directly away from
// `from` (within 1000 in height); without a way point, the position mirrored through `em`.
void RouteCkEscEm(cEm* em, cEm* from, Vec* out)
{
    const int mask = em->atari.m_flag;
    PSVECSubtract(&em->pos, &from->pos, out);
    PSVECAdd(out, &em->pos, out);
    em->RckNear = near_cached(em, 0, mask);
    if (em->RckNear == kNoPoint) return;
    const RtpData* r = graph();
    const RtpPoint* pts = points(r);
    const RtpPoint* pt = &pts[em->RckNear];
    *out = pt->pos;
    if (pt->nLine == 0) return;
    const f32 ang = GetXZAngle(&em->pos, (Vec*) &from->pos);
    f32 best = 0.0f;
    const RtpLink* lk = &links(r)[pt->offLine];
    for (u32 i = 0; i < pt->nLine; i++) {
        const RtpPoint* np = &pts[lk[i].point];
        const f32 m = fabsf(Muku(&em->pos, (Vec*) &np->pos, ang, PI));
        if (m < best) continue;
        if (fabsf(np->pos.y - em->pos.y) > 1000.0f) continue;
        best = m;
        *out = np->pos;
    }
}

// The step between two positions without an actor (scenario and camera use): `to` itself (1) when the line is clear
// or nothing is routed, else the next way point (0).
int RouteCkPosToPos(Vec* from, Vec* to, Vec* out)
{
    route_cnt.steps++;
    Vec a = *from;
    Vec b = *to;
    a.y += kEye;
    b.y += kEye;
    if (graph() == NULL || direct_ok(&a, &b, 0, 0)) {
        route_cnt.steps_direct++;
        *out = *to;
        return 1;
    }
    const int p = near_point(&a, 0, 0);
    const int t = p == kNoPoint ? kNoPoint : near_point(&b, 0, 0);
    const int next = t == kNoPoint ? kNoPoint : hop(graph(), p, t);
    if (next == kNoPoint) {
        route_cnt.steps_direct++;
        *out = *to;
        return 1;
    }
    const RtpPoint* pts = points(graph());
    const f32 d2 = (a.x - pts[p].pos.x) * (a.x - pts[p].pos.x) + (a.z - pts[p].pos.z) * (a.z - pts[p].pos.z);
    if (d2 < kArrive || line_blocked(&a, &pts[next].pos, 0, 0) == 0) *out = pts[next].pos;
    else *out = pts[p].pos;
    return 0;
}

// 1 when the nearest way points of the two positions are connected.
int RouteCkConnectPosCk(Vec* pPos1, Vec* pPos2)
{
    const int p = near_point(pPos1, 0, 0);
    if (p == kNoPoint) return 0;
    const int t = near_point(pPos2, 0, 0);
    if (t == kNoPoint) return 0;
    return hop(graph(), p, t) != kNoPoint;
}

// The walking distance between two positions: the path length between their nearest way points, or the straight XZ
// distance when the line is clear (from the feet: the original tests the unraised positions here) or nothing is routed.
f32 RouteCkPosToPosDis(Vec* from, Vec* to)
{
    route_cnt.dists++;
    Vec a = *from;
    Vec b = *to;
    a.y += kEye;
    b.y += kEye;
    if (graph() != NULL) {
        bool direct = false;
        if (line_blocked(from, to, 0, 0) == 0) {
            Vec c;
            PosToPos(&a, &b, &c, 0.5f);
            direct = SatMgr.getFloor(&c, 600.0f, 100000.0f, NULL, 0) > c.y - 2000.0f;
        }
        if (!direct) {
            const int p = near_point(from, 0, 0);
            const int t = p == kNoPoint ? kNoPoint : near_point(to, 0, 0);
            if (t != kNoPoint) return RouteCkGetDist(p, t);
        }
    }
    return SQRTF((from->x - to->x) * (from->x - to->x) + (from->z - to->z) * (from->z - to->z));
}

void RouteCkGetPoint(int no, Vec* out)
{
    const RtpData* r = graph();
    if (r != NULL) {
        *out = points(r)[no].pos;
    } else {
        out->x = out->y = out->z = 0.0f;
    }
}

int RouteCkGetPointNumber()
{
    const RtpData* r = graph();
    return r != NULL ? r->nPoint : -1;
}

// The path length from point n0 to n1 along the next hops; where the path breaks, the straight distance from the
// point reached so far to n1 (the length walked until then is dropped, as the original does).
f32 RouteCkGetDist(int n0, int n1)
{
    f32 d = 0.0f;
    if (n0 == n1) return d;
    const RtpData* r = graph();
    const RtpPoint* pts = points(r);
    Vec v;
    do {
        const int next = hop(r, n0, n1);
        if (next == kNoPoint) {
            PSVECSubtract((Vec*) &pts[n0].pos, (Vec*) &pts[n1].pos, &v);
            return PSVECMag(&v);
        }
        PSVECSubtract((Vec*) &pts[n0].pos, (Vec*) &pts[next].pos, &v);
        d += PSVECMag(&v);
        n0 = next;
    } while (n0 != n1);
    return d;
}

int RouteCkGetNearPoint(Vec* pos) { return near_point(pos, 0, 0); }

int getNearInfo(cEm* em, int mode, int mask) { return near_cached(em, mode, mask); }

s8 getNearPoint(Vec* pos, int mode, int mask) { return near_point(pos, mode, mask); }

// Debug displays of the way points and the placements: counted, not drawn.
void Draw_rtp()
{
    if (graph() != NULL && graph()->nPoint != 0) route_cnt.debug_draws++;
}

void Draw_eminfo()
{
    if (pG->pEmi != NULL) route_cnt.debug_draws++;
}
