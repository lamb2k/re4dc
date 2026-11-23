// colb_host.cpp (lane eng-skel2): the room's collision in the baked form (services/collision/col.h) on the PC
// reference. Native builds only (svc.mk: NATIVE_GAME_OBJS). Three uses:
//
//  1. host_room_post (host_glue.cpp host_load_room, every room the native build loads): every file of the room
//     archive's SAT and EAT tables is baked by the engine's own bake (col_bake_into) and written in the baked form into
//     the PC's collision area (0x8F000000; the arena check of col_model.cpp admits it on the PC); the archive's SAT and
//     EAT entries then point there, so the room's pieces are set up from the baked form (col_baked_setup), as on the
//     console. Each file's normal table stays the archive's (its oNorm points back into the archive), so every pointer
//     the behaviour keeps (pFloor_norm, hitCheck's normal) is the reference's and the dumps compare as before.
//     RE4_COLB=0: not done (the pieces baked when they are created, as before lane eng-skel2: the comparison arm).
//  2. RE4_COLB_BAKE=<out dir> (the bake step, svc/colbake.sh): each room of RE4_COLB_ROOMS ("st1/r100 st1/r101 ...")
//     in RE4_TREE is written to <out dir> with its SAT and EAT files in the baked form, the normal table inside each
//     file (the console's form: the original tables are not loaded), every other entry as it was; then the program
//     ends (exit 0). One line a room to stdout (sizes and the FNV-1a hash of each baked file's tables).
//  3. RE4_COLMAP=<out file> (the map entry's check, svc/colmap_check.sh): at each room load, at the points of
//     RE4_COLMAP_POINTS (x y z float bits, one point a line: the fixtures' paths) and a 48 x 48 grid over the room's
//     floor group, src/Sscrn/ss_map.cpp mapPositionCheck's search (its loop, below, as written there) with the original
//     At_poly_line_ck on the unbaked SAT file 0, and col_map_floor on the baked one, with SEck 0 and 1: the polygon, the
//     hit point and the three vertices must be the same to the bit. RE4_COLMAP_CONTROL=1 sets col_map_control.
#include "hostref.h"
#include "atari.h"
#include "at_sub.h"
#include "../../services/collision/col.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

extern int SEck;   // col_model.cpp: at_sub's attribute filter bypass
u32 At_poly_line_ck(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask);

namespace {
constexpr u32 kArea = 0x8F000000u, kAreaBytes = 0x01000000u;   // [0, 6 MB) bake-step archive, [6, 10) bake scratch,
constexpr u32 kArc = 0, kTmp = 0x00600000u, kOut = 0x00A00000u; // [10, 16) the baked files
u8* area()
{
    static u8* a;
    if (!a) {
        void* want = (void*) (uintptr_t) kArea;
        void* r = mmap(want, kAreaBytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
        if (r != want) { fprintf(stderr, "colb: cannot map the collision area\n"); exit(2); }
        a = (u8*) r;
    }
    return a;
}
u32 g_tmp, g_out;
void* tmp_alloc(u32 bytes)
{
    bytes = (bytes + 31u) & ~31u;
    if (kTmp + g_tmp + bytes > kOut) { fprintf(stderr, "colb: bake scratch full\n"); exit(2); }
    void* r = area() + kTmp + g_tmp;
    g_tmp += bytes;
    return r;
}
u32 a32(u32 x) { return (x + 31u) & ~31u; }
u32 fnv(const u8* p, u32 n, u32 h = 2166136261u)
{
    for (u32 i = 0; i < n; i++) h = (h ^ p[i]) * 16777619u;
    return h;
}

// One original file baked into dst (32-aligned); its bytes. inside: the normal table copied into the file (the
// console's form); else oNorm points at the original's table.
u32 bake_file(cSatFile* f, u8* dst, bool inside, u32* hash)
{
    cSat s;   // a piece on the stack, as mapPositionCheck makes one
    Vec zero = {0.0f, 0.0f, 0.0f};
    s.init(f, &zero, &zero);   // operator=, setCoord, blockInit (the block links made pointers, as at create)
    const f32 ctl = col_control_floor;
    col_control_floor = 0.0f;   // the floor control is applied when a piece is set up (col_baked_setup), not baked in
    g_tmp = 0;
    ColPiece* pc = col_bake_into(&s, tmp_alloc);
    col_control_floor = ctl;
    if (!pc) { fprintf(stderr, "colb: bake failed\n"); exit(2); }
    memcpy(dst, f, 0x14);
    ((cSatFile*) dst)->x8 = COL_BAKED_MAGIC;
    ColBakedFile* b = (ColBakedFile*) (dst + 0x14);
    memset(b, 0, sizeof *b);
    u32 off = 0x14 + sizeof(ColBakedFile);
    if (inside) {
        b->oNorm = (s32) off;
        memcpy(dst + off, s.norm_p, 12u * s.normal_num);
        off += 12u * s.normal_num;
    } else {
        b->oNorm = (s32) ((u8*) s.norm_p - dst);
    }
    off = a32(off);
    b->version = COL_BAKED_VERSION;
    b->oPiece = off;
    u8* rec = dst + off;
    memcpy(rec, pc, pc->bytes);
    memset(rec, 0, sizeof(ColPiece));   // the record: set up at room load (col_baked_setup)
    const u8* base = (const u8*) pc;
    b->nNode = pc->nNode;
    b->nLeaf = pc->nLeaf;
    b->nIdx = pc->nIdx;
    b->nMask = pc->nMask;
    b->nPoly = pc->nPoly;
    b->oMinX = (u32) ((const u8*) pc->nodeMinX - base);
    b->oMinZ = (u32) ((const u8*) pc->nodeMinZ - base);
    b->oSzX = (u32) ((const u8*) pc->nodeSizeX - base);
    b->oSzZ = (u32) ((const u8*) pc->nodeSizeZ - base);
    b->oSkip = (u32) ((const u8*) pc->nodeSkip - base);
    b->oLeafN = (u32) ((const u8*) pc->nodeLeaf - base);
    b->oLeaf = (u32) ((const u8*) pc->leaf - base);
    b->oIdx = (u32) ((const u8*) pc->idx - base);
    b->oHot = (u32) ((const u8*) pc->hot - base);
    b->oCold = (u32) ((const u8*) pc->cold - base);
    b->oGrid = (u32) ((const u8*) pc->grid - base);
    b->oMask = (u32) ((const u8*) pc->cmask - base);
    b->bytes = off + pc->bytes;
    if (hash) *hash = fnv(rec + sizeof(ColPiece), pc->bytes - (u32) sizeof(ColPiece), *hash);
    return b->bytes;
}

bool is_table(const u8* e) { return e[0] != 0xFF && (e[0] & 0x80); }
u32 table_count(const u8* e)
{
    u32 first;
    memcpy(&first, e + 4, 4);
    return e[1] ? e[1] : (first - 4) / 4;
}
// One SAT / EAT entry (a table of files, or one file) baked into dst; its bytes
u32 bake_entry(u8* ent, u8* dst, bool inside, u32* hash)
{
    if (!is_table(ent)) return bake_file((cSatFile*) ent, dst, inside, hash);
    const u32 n = table_count(ent);
    u32* ofs = (u32*) (ent + 4);
    u32* nofs = (u32*) (dst + 4);
    memcpy(dst, ent, 4);
    u32 off = a32(4 + 4 * n);
    for (u32 k = 0; k < n; k++) {
        u32 j = 0;
        while (j < k && ofs[j] != ofs[k]) j++;
        if (j < k) { nofs[k] = nofs[j]; continue; }   // a file listed twice: one baked file
        nofs[k] = off;
        off = a32(off + bake_file((cSatFile*) (ent + ofs[k]), dst + off, inside, hash));
    }
    return off;
}

struct Arc {
    u8* d;
    u32 num, *ofs;
    const char* tag(u32 i) const { return (const char*) (d + 0x10 + 4 * num + 4 * i); }
};
Arc arc_of(void* p)
{
    Arc a;
    a.d = (u8*) p;
    memcpy(&a.num, a.d, 4);
    a.ofs = (u32*) (a.d + 0x10);
    return a;
}
bool col_tag(const char* t) { return !memcmp(t, "SAT", 4) || !memcmp(t, "EAT", 4); }

// ---- 1. the native build's room load ----
void room_post(void* arc)
{
    const char* e = getenv("RE4_COLB");
    if (e && !strcmp(e, "0")) return;
    Arc a = arc_of(arc);
    g_out = 0;
    u32 files = 0, bytes = 0;
    for (u32 i = 0; i < a.num; i++) {
        if (!col_tag(a.tag(i))) continue;
        u8* dst = area() + kOut + g_out;
        u32 h = 2166136261u;
        const u32 n = bake_entry(a.d + a.ofs[i], dst, false, &h);
        if (kOut + g_out + n > kAreaBytes) { fprintf(stderr, "colb: area full\n"); exit(2); }
        a.ofs[i] = (u32) (dst - a.d);
        g_out = a32(g_out + n);
        files++;
        bytes += n;
        host_log("colb: %s entry %u baked: %u B at %08x, tables %08x", a.tag(i), i, n, (unsigned) (uintptr_t) dst, h);
    }
    host_log("colb: room archive %08x: %u SAT / EAT entries in the baked form, %u B", (unsigned) (uintptr_t) arc, files, bytes);
}

// ---- 2. the bake step ----
void bake_step(const char* out_dir)
{
    const char* tree = getenv("RE4_TREE");
    const char* rooms = getenv("RE4_COLB_ROOMS");
    if (!tree || !rooms) { fprintf(stderr, "colb: RE4_TREE and RE4_COLB_ROOMS needed\n"); exit(2); }
    char list[4096];
    snprintf(list, sizeof list, "%s", rooms);
    for (char* r = strtok(list, " "); r; r = strtok(0, " ")) {
        char path[1024];
        snprintf(path, sizeof path, "%s/%s.arc", tree, r);
        FILE* f = fopen(path, "rb");
        if (!f) { fprintf(stderr, "colb: %s missing\n", path); exit(2); }
        fseek(f, 0, SEEK_END);
        const u32 size = (u32) ftell(f);
        fseek(f, 0, SEEK_SET);
        if (size > kTmp) { fprintf(stderr, "colb: %s too big\n", path); exit(2); }
        u8* src = area() + kArc;
        if (fread(src, 1, size, f) != size) exit(2);
        fclose(f);
        Arc a = arc_of(src);
        // entries in file order: each one's extent is up to the next distinct offset
        u32 data0 = size;
        for (u32 i = 0; i < a.num; i++)
            if (a.ofs[i] < data0) data0 = a.ofs[i];
        u8* dst = (u8*) malloc(size * 2 + (1u << 20));
        memcpy(dst, src, data0);
        u32* nofs = (u32*) (dst + 0x10);
        u32 at = data0, orig = 0, baked = 0, hashes = 2166136261u;
        u32 done[256];
        for (u32 k = 0; k < a.num; k++) done[k] = 0;
        for (;;) {   // the next entry in file order
            u32 best = 0xFFFFFFFFu, bi = 0;
            for (u32 i = 0; i < a.num; i++)
                if (!done[i] && a.ofs[i] < best) { best = a.ofs[i]; bi = i; }
            if (best == 0xFFFFFFFFu) break;
            u32 end = size;
            for (u32 i = 0; i < a.num; i++)
                if (a.ofs[i] > best && a.ofs[i] < end) end = a.ofs[i];
            at = a32(at);
            u32 n;
            if (col_tag(a.tag(bi))) {
                u32 h = 2166136261u;
                n = bake_entry(src + best, dst + at, true, &h);
                orig += end - best;
                baked += n;
                hashes = fnv((const u8*) &h, 4, hashes);
                printf("COLB %s %s entry %u: %u B -> %u B, tables %08x\n", r, a.tag(bi), bi, end - best, n, h);
            } else {
                n = end - best;
                memcpy(dst + at, src + best, n);
            }
            for (u32 i = 0; i < a.num; i++)   // every entry at this offset (none share one in these archives)
                if (!done[i] && a.ofs[i] == best) { nofs[i] = at; done[i] = 1; }
            at += n;
        }
        char opath[1024];
        snprintf(opath, sizeof opath, "%s/%s.arc", out_dir, r);
        FILE* o = fopen(opath, "wb");
        if (!o || fwrite(dst, 1, at, o) != at) { fprintf(stderr, "colb: cannot write %s\n", opath); exit(2); }
        fclose(o);
        free(dst);
        printf("COLB %s: archive %u B -> %u B (SAT and EAT %u B -> %u B), tables %08x\n", r, size, at, orig, baked, hashes);
    }
    fflush(stdout);
    exit(0);
}

// ---- 3. the map entry's check ----
struct Pt { u32 x, y, z; };
f32 fb(u32 b) { f32 f; memcpy(&f, &b, 4); return f; }
u32 bf(f32 f) { u32 b; memcpy(&b, &f, 4); return b; }
// mapPositionCheck's search (src/Sscrn/ss_map.cpp: `a = pl; b = pl; best = 100000000.0f; idx = -1;` ... the for loop),
// as written there, on a cSat made over the unbaked file
int map_ref(cSat& satB, Vec pl, Vec* hit_out)
{
    Vec a, b, hit, hit2;
    f32 best;
    int idx, i;
    AtPoly* poly;
    a = pl;
    b = pl;
    best = 100000000.0f;
    idx = -1;
    a.y += 100000.0f;
    b.y -= 100000.0f;
    poly = satB.poly_p;
    for (i = 0; i < satB.floor_num + satB.slope_num; i++, poly++) {
        if (At_poly_line_ck((AtPolyData*) &satB, &hit2, poly, &a, &b, 0, 0)) {
            if (hit2.y <= best) {
                idx = i;
                hit = hit2;
                best = hit.y;
            }
        }
    }
    if (idx >= 0) *hit_out = hit;
    return idx;
}
void map_check(void* arc, const u8* baked_sat)
{
    const char* path = getenv("RE4_COLMAP");
    if (!path) return;
    FILE* o = fopen(path, "a");
    if (!o) exit(2);
    const char* c = getenv("RE4_COLMAP_CONTROL");
    col_map_control = c && !strcmp(c, "1");
    Arc a = arc_of(arc);
    u8* ent = 0;
    for (u32 i = 0; i < a.num && !ent; i++)
        if (!memcmp(a.tag(i), "SAT", 4)) ent = a.d + a.ofs[i];
    cSatFile* f = (cSatFile*) (is_table(ent) ? ent + ((u32*) (ent + 4))[0] : ent);
    cSat satB;
    Vec zero = {0.0f, 0.0f, 0.0f};
    satB.init(f, &zero, &zero);
    // the baked table's piece must be set up (it is, when the room's pieces are made; here before them)
    const u8* bf0 = is_table(baked_sat) ? baked_sat + ((const u32*) (baked_sat + 4))[0] : baked_sat;
    cSat satN;
    satN.init((cSatFile*) bf0, &zero, &zero);
    Pt* pts = (Pt*) malloc(sizeof(Pt) * 200000);
    u32 np = 0;
    if (const char* pp = getenv("RE4_COLMAP_POINTS")) {
        FILE* pf = fopen(pp, "r");
        if (pf) {
            while (np < 190000 && fscanf(pf, "%x %x %x", &pts[np].x, &pts[np].y, &pts[np].z) == 3) np++;
            fclose(pf);
        }
    }
    const u32 nfix = np;
    f32 lx = 1e30f, hx = -1e30f, lz = 1e30f, hz = -1e30f, hy = -1e30f;
    for (int i = 0; i < satB.floor_num + satB.slope_num; i++)
        for (int k = 0; k < 3; k++) {
            const Vec& v = satB.vtx[satB.poly_p[i].v[k]];
            if (v.x < lx) lx = v.x;
            if (v.x > hx) hx = v.x;
            if (v.z < lz) lz = v.z;
            if (v.z > hz) hz = v.z;
            if (v.y > hy) hy = v.y;
        }
    for (int gz = 0; gz < 48; gz++)
        for (int gx = 0; gx < 48; gx++) {
            pts[np].x = bf(lx + (hx - lx) * ((f32) gx + 0.5f) / 48.0f);
            pts[np].y = bf(hy);
            pts[np].z = bf(lz + (hz - lz) * ((f32) gz + 0.5f) / 48.0f);
            np++;
        }
    u32 hits = 0, miss = 0, bad = 0;
    const int seck0 = SEck;
    for (int sk = 0; sk < 2; sk++) {
        SEck = sk;
        for (u32 p = 0; p < np; p++) {
            Vec pl = {fb(pts[p].x), fb(pts[p].y), fb(pts[p].z)}, hr = {0, 0, 0};
            const int ir = map_ref(satB, pl, &hr);
            ColMapHit m;
            memset(&m, 0, sizeof m);
            const int okn = col_map_floor(baked_sat, &pl, &m);
            bool same = (ir < 0) == !okn;
            if (same && ir >= 0) {
                const AtPoly& q = satB.poly_p[ir];
                const Vec* v[3] = {&satB.vtx[q.v[0]], &satB.vtx[q.v[1]], &satB.vtx[q.v[2]]};
                same = m.poly == (u32) ir && !memcmp(&m.hit, &hr, 12);
                for (int k = 0; k < 3; k++) same = same && !memcmp(&m.v[k], v[k], 12);
            }
            if (ir >= 0) hits++;
            else miss++;
            if (!same) {
                bad++;
                if (bad <= 20)
                    fprintf(o, "COLMAP MISMATCH seck %d point %08x %08x %08x (%s): ref poly %d hit %08x %08x %08x, entry %d poly %u hit %08x %08x %08x\n",
                            sk, pts[p].x, pts[p].y, pts[p].z, p < nfix ? "path" : "grid", ir, bf(hr.x), bf(hr.y), bf(hr.z), okn,
                            m.poly, bf(m.hit.x), bf(m.hit.y), bf(m.hit.z));
            }
        }
    }
    SEck = seck0;
    fprintf(o, "COLMAP room archive %08x: floor group %d polygons, points %u (path %u, grid %u) x SEck 0 and 1: hits %u misses %u "
               "mismatches %u%s\n", (unsigned) (uintptr_t) arc, satB.floor_num + satB.slope_num, np, nfix, np - nfix, hits, miss, bad,
            col_map_control ? " (control col_map_control)" : "");
    fclose(o);
    free(pts);
}
}   // namespace

extern "C" void host_room_post(void* arc)
{
    if (const char* d = getenv("RE4_COLB_BAKE")) bake_step(d);
    if (getenv("RE4_COLMAP")) {
        // the check needs both forms: the unbaked file stays where it is, the baked table goes to the area
        Arc a = arc_of(arc);
        for (u32 i = 0; i < a.num; i++)
            if (!memcmp(a.tag(i), "SAT", 4)) {
                g_out = 0;
                u8* dst = area() + kOut;
                const u32 n = bake_entry(a.d + a.ofs[i], dst, false, 0);
                map_check(arc, dst);
                (void) n;
                break;
            }
        exit(0);
    }
    room_post(arc);
}
