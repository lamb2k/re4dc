/* occl_rank.c (lane engine19, offline, host only): the OCCL candidate list of each camera cell, chosen by use.
 *
 * For a camera cell (eye at its centre, EYE_UP over its lowest floor) every occluder whose front holds the eye is
 * scored by the target boxes (a Ganado-sized box on each 1 m floor cell in range) it shadows wholly, through BOTH slab
 * faces, as the runtime test does (platform/room_occl.c). Up to K occluders are then picked greedily by the targets
 * they add. Ranking only: the runtime test decides from the real eye, so a poor pick costs culls, never correctness.
 *
 * input "OCRI": u32 nocc, ncell, ntgt, K, threads; f32 range;
 *        nocc x {f32 c[4][3], f32 half, s32 side}; ncell x {f32 eye[3], u32 valid}; ntgt x {f32 lo[3], hi[3]}
 * output: ncell x K u16 (0xFFFF = none), best first.
 * build: cc -O2 -pthread -o occl_rank occl_rank.c -lm
 */
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { float c[4][3], half; int32_t side; float n[3], d; } Occ;
typedef struct { float eye[3]; uint32_t valid; } Cell;
typedef struct { float lo[3], hi[3]; } Tgt;
static Occ* O; static Cell* C; static Tgt* T;
static uint32_t NO, NC, NT, K, NTH; static float RANGE;
static uint16_t* OUT;
static uint32_t next_cell; static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;

static void sub(const float* a, const float* b, float* r) { r[0] = a[0] - b[0]; r[1] = a[1] - b[1]; r[2] = a[2] - b[2]; }
static float dot(const float* a, const float* b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
static void cross(const float* a, const float* b, float* r)
{
    r[0] = a[1] * b[2] - a[2] * b[1]; r[1] = a[2] * b[0] - a[0] * b[2]; r[2] = a[0] * b[1] - a[1] * b[0];
}

/* shadow wedge planes of one face (quad offset by s * half along n) from eye e: m[4][3], inward */
static void wedge(const Occ* o, const float* e, float s, float m[4][3])
{
    float q[4][3], ctr[3] = {0, 0, 0};
    for (int i = 0; i < 4; i++) {
        for (int k = 0; k < 3; k++) q[i][k] = o->c[i][k] + o->n[k] * s * o->half;
        for (int k = 0; k < 3; k++) ctr[k] += q[i][k] * 0.25f;
    }
    float ce[3]; sub(ctr, e, ce);
    for (int i = 0; i < 4; i++) {
        float a[3], b[3]; sub(q[i], e, a); sub(q[(i + 1) & 3], e, b);
        cross(a, b, m[i]);
        if (dot(m[i], ce) < 0) for (int k = 0; k < 3; k++) m[i][k] = -m[i][k];
    }
}

static int shadowed(const Occ* o, const float* e, const float mf[4][3], const float mb[4][3], const Tgt* t)
{
    float p[3];
    for (int b = 0; b < 8; b++) {
        p[0] = (b & 1) ? t->hi[0] : t->lo[0]; p[1] = (b & 2) ? t->hi[1] : t->lo[1]; p[2] = (b & 4) ? t->hi[2] : t->lo[2];
        if (dot(o->n, p) - o->d > -o->half - 1.0f) return 0;
        float pe[3]; sub(p, e, pe);
        for (int i = 0; i < 4; i++) if (dot(mf[i], pe) < 0 || dot(mb[i], pe) < 0) return 0;
    }
    return 1;
}

static void* worker(void* arg)
{
    (void) arg;
    uint32_t words = (NT + 63) / 64;
    uint64_t* bits = malloc(sizeof(uint64_t) * words * (size_t) (NO ? NO : 1));
    uint64_t* have = malloc(sizeof(uint64_t) * words);
    uint32_t* cnt = malloc(sizeof(uint32_t) * (NO ? NO : 1));
    uint32_t* tin = malloc(sizeof(uint32_t) * (NT ? NT : 1));
    for (;;) {
        pthread_mutex_lock(&mu); uint32_t c = next_cell++; pthread_mutex_unlock(&mu);
        if (c >= NC) break;
        uint16_t* out = OUT + (size_t) c * K;
        for (uint32_t i = 0; i < K; i++) out[i] = 0xFFFF;
        if (!C[c].valid) continue;
        const float* e = C[c].eye;
        uint32_t ntin = 0;
        for (uint32_t t = 0; t < NT; t++) {
            float m[3]; for (int k = 0; k < 3; k++) m[k] = 0.5f * (T[t].lo[k] + T[t].hi[k]) - e[k];
            if (dot(m, m) <= RANGE * RANGE) tin[ntin++] = t;
        }
        memset(bits, 0, sizeof(uint64_t) * words * NO);
        for (uint32_t o = 0; o < NO; o++) {
            cnt[o] = 0;
            const Occ* q = &O[o];
            if (dot(q->n, e) - q->d < q->half + 50.0f) continue;
            float far2 = 0;
            for (int i = 0; i < 4; i++) { float v[3]; sub(q->c[i], e, v); float l = dot(v, v); if (l > far2) far2 = l; }
            if (far2 > RANGE * RANGE) continue;
            float mf[4][3], mb[4][3];
            wedge(q, e, 1.0f, mf); wedge(q, e, -1.0f, mb);
            uint64_t* b = bits + (size_t) o * words;
            for (uint32_t j = 0; j < ntin; j++) {
                uint32_t t = tin[j];
                if (shadowed(q, e, (const float (*)[3]) mf, (const float (*)[3]) mb, &T[t])) { b[t >> 6] |= 1ull << (t & 63); cnt[o]++; }
            }
        }
        memset(have, 0, sizeof(uint64_t) * words);
        for (uint32_t k = 0; k < K; k++) {
            uint32_t best = 0xFFFFFFFF, bestn = 0;
            for (uint32_t o = 0; o < NO; o++) {
                if (cnt[o] <= bestn) continue;
                uint64_t* b = bits + (size_t) o * words; uint32_t n = 0;
                for (uint32_t w = 0; w < words; w++) n += __builtin_popcountll(b[w] & ~have[w]);
                if (n > bestn) { bestn = n; best = o; }
            }
            if (best == 0xFFFFFFFF) break;
            out[k] = (uint16_t) best;
            uint64_t* b = bits + (size_t) best * words;
            for (uint32_t w = 0; w < words; w++) have[w] |= b[w];
            cnt[best] = 0;
        }
    }
    free(bits); free(have); free(cnt); free(tin);
    return 0;
}

int main(int argc, char** argv)
{
    if (argc != 3) { fprintf(stderr, "usage: occl_rank <in> <out>\n"); return 2; }
    FILE* f = fopen(argv[1], "rb"); if (!f) return 1;
    char mg[4]; uint32_t u[5];
    if (fread(mg, 1, 4, f) != 4 || memcmp(mg, "OCRI", 4) || fread(u, 4, 5, f) != 5 || fread(&RANGE, 4, 1, f) != 1) return 1;
    NO = u[0]; NC = u[1]; NT = u[2]; K = u[3]; NTH = u[4] ? u[4] : 1; if (NTH > 64) NTH = 64;
    O = calloc(NO ? NO : 1, sizeof(Occ)); C = calloc(NC ? NC : 1, sizeof(Cell)); T = calloc(NT ? NT : 1, sizeof(Tgt));
    for (uint32_t i = 0; i < NO; i++) {
        if (fread(O[i].c, 4, 12, f) != 12 || fread(&O[i].half, 4, 1, f) != 1 || fread(&O[i].side, 4, 1, f) != 1) return 1;
        float a[3], b[3], n[3]; sub(O[i].c[1], O[i].c[0], a); sub(O[i].c[3], O[i].c[0], b); cross(a, b, n);
        float l = sqrtf(dot(n, n)) * (float) O[i].side;
        for (int k = 0; k < 3; k++) O[i].n[k] = n[k] / l;
        O[i].d = dot(O[i].n, O[i].c[0]);
    }
    for (uint32_t i = 0; i < NC; i++) if (fread(C[i].eye, 4, 3, f) != 3 || fread(&C[i].valid, 4, 1, f) != 1) return 1;
    for (uint32_t i = 0; i < NT; i++) if (fread(T[i].lo, 4, 3, f) != 3 || fread(T[i].hi, 4, 3, f) != 3) return 1;
    fclose(f);
    OUT = malloc(sizeof(uint16_t) * (size_t) NC * K);
    pthread_t th[64];
    for (uint32_t i = 0; i < NTH; i++) pthread_create(&th[i], 0, worker, 0);
    for (uint32_t i = 0; i < NTH; i++) pthread_join(th[i], 0);
    FILE* o = fopen(argv[2], "wb"); fwrite(OUT, 2, (size_t) NC * K, o); fclose(o);
    return 0;
}
