// PS2_PVS step 2 (lane t2exact, 2026-10-15): the offline visibility caster. For every cell of an X/Z grid over the room,
// eyes are sampled over the cell's camera volume (local ground + eye heights), and from each eye rays go out in K
// directions (a Fibonacci sphere, rotated per eye). Along a ray the nearest occluder triangle that faces the eye (or is
// two-sided) ends it; every instance with a triangle hit before that point (occluder or not) is visible from the cell.
// Ground: from 3 x 3 points of the cell a ray goes down from above the world; its lowest occluder hit is the local
// ground (no hit: that point has no ground, and a cell with no ground point is left without a set).
//
// usage: pvs_cast <work dir> <cell mm> <directions> [verify <cells file> <eyes per cell> <seed>]
//   reads  <work>/tris.bin (pvs_prep.py), writes <work>/cells.bin:
//     u32 nx, nz, ninst; f32 x0, z0, cell; then nx*nz x {f32 ylo, yhi; u8 has; u8 pad[3]; u8 bits[(ninst+7)/8]}
//   verify: random eyes (seeded, not the build grid) inside the camera volume of the cells listed in <cells file>
//     (one "ix iz ylo yhi" per line), each eye's visible set written to <work>/verify.bin
//     (u32 count, count x {u32 cell index; f32 eye[3]; u8 bits[(ninst+7)/8]}).
// Env: PVS_EYE_H (eye heights above local ground, mm, comma list; default 400,1200,2000,2800,3600),
//      PVS_XZ (eye samples per cell axis, default 3), PVS_RAY (ray length mm, default 60000).
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <vector>

struct TriRec { float v[9]; uint32_t inst, flags; };
struct Tri { float a[3], e1[3], e2[3], n[3]; uint32_t inst, flags; };
struct Node { float lo[3], hi[3]; uint32_t left, count; }; // count>0: leaf with tris [left, left+count)

static std::vector<Tri> T;
static std::vector<Node> N;
static std::vector<uint32_t> order;

static void bounds(uint32_t b, uint32_t e, float lo[3], float hi[3], bool centroid) {
    for (int a = 0; a < 3; ++a) { lo[a] = 1e30f; hi[a] = -1e30f; }
    for (uint32_t i = b; i < e; ++i) {
        const Tri& t = T[order[i]];
        for (int a = 0; a < 3; ++a) {
            float p0 = t.a[a], p1 = t.a[a] + t.e1[a], p2 = t.a[a] + t.e2[a];
            if (centroid) { float c = (p0 + p1 + p2) / 3; lo[a] = std::min(lo[a], c); hi[a] = std::max(hi[a], c); }
            else { lo[a] = std::min({lo[a], p0, p1, p2}); hi[a] = std::max({hi[a], p0, p1, p2}); }
        }
    }
}
static uint32_t build(uint32_t b, uint32_t e) {
    Node nd; bounds(b, e, nd.lo, nd.hi, false);
    uint32_t me = N.size(); N.push_back(nd);
    if (e - b <= 4) { N[me].left = b; N[me].count = e - b; return me; }
    float clo[3], chi[3]; bounds(b, e, clo, chi, true);
    int ax = 0; for (int a = 1; a < 3; ++a) if (chi[a] - clo[a] > chi[ax] - clo[ax]) ax = a;
    uint32_t m = (b + e) / 2;
    std::nth_element(order.begin() + b, order.begin() + m, order.begin() + e, [ax](uint32_t x, uint32_t y) {
        const Tri &p = T[x], &q = T[y];
        return 3 * p.a[ax] + p.e1[ax] + p.e2[ax] < 3 * q.a[ax] + q.e1[ax] + q.e2[ax]; });
    uint32_t l = build(b, m); (void)l;
    uint32_t r = build(m, e);
    N[me].left = r; N[me].count = 0; // left child is me+1
    return me;
}
static inline bool slab(const Node& n, const float o[3], const float inv[3], float tmax) {
    float t0 = 0, t1 = tmax;
    for (int a = 0; a < 3; ++a) {
        float ta = (n.lo[a] - o[a]) * inv[a], tb = (n.hi[a] - o[a]) * inv[a];
        if (ta > tb) std::swap(ta, tb);
        t0 = std::max(t0, ta); t1 = std::min(t1, tb);
        if (t0 > t1) return false;
    }
    return true;
}
// Moller-Trumbore; returns t or -1
static inline float hit(const Tri& t, const float o[3], const float d[3]) {
    float p[3] = {d[1] * t.e2[2] - d[2] * t.e2[1], d[2] * t.e2[0] - d[0] * t.e2[2], d[0] * t.e2[1] - d[1] * t.e2[0]};
    float det = t.e1[0] * p[0] + t.e1[1] * p[1] + t.e1[2] * p[2];
    if (std::fabs(det) < 1e-12f) return -1;
    float inv = 1.0f / det;
    float s[3] = {o[0] - t.a[0], o[1] - t.a[1], o[2] - t.a[2]};
    float u = (s[0] * p[0] + s[1] * p[1] + s[2] * p[2]) * inv;
    if (u < -1e-4f || u > 1.0001f) return -1;
    float q[3] = {s[1] * t.e1[2] - s[2] * t.e1[1], s[2] * t.e1[0] - s[0] * t.e1[2], s[0] * t.e1[1] - s[1] * t.e1[0]};
    float v = (d[0] * q[0] + d[1] * q[1] + d[2] * q[2]) * inv;
    if (v < -1e-4f || u + v > 1.0001f) return -1;
    float tt = (t.e2[0] * q[0] + t.e2[1] * q[1] + t.e2[2] * q[2]) * inv;
    return tt > 1.0f ? tt : -1; // 1 mm: not the eye's own surface
}
struct Hit { float t; uint32_t inst, tri; };
// One ray: nearest blocking occluder distance; every hit before it (any triangle) is collected.
static float trace(const float o[3], const float d[3], float tmax, std::vector<Hit>& hits, float tmin = 0) {
    float inv[3]; for (int a = 0; a < 3; ++a) inv[a] = 1.0f / (std::fabs(d[a]) > 1e-12f ? d[a] : (d[a] < 0 ? -1e-12f : 1e-12f));
    uint32_t stack[128]; int sp = 0; stack[sp++] = 0;
    hits.clear();
    while (sp) {
        const Node& n = N[stack[--sp]];
        if (!slab(n, o, inv, tmax)) continue;
        if (n.count) {
            for (uint32_t i = n.left; i < n.left + n.count; ++i) {
                const Tri& t = T[order[i]];
                float th = hit(t, o, d);
                if (th < tmin || th >= tmax) continue;
                hits.push_back({th, t.inst, order[i]});
                if (t.flags & 1) { // occluder: blocks if two-sided or facing the eye
                    float dn = d[0] * t.n[0] + d[1] * t.n[1] + d[2] * t.n[2];
                    if ((t.flags & 2) || dn < 0) tmax = th;
                }
            }
        } else {
            uint32_t self = &n - N.data();
            stack[sp++] = n.left; stack[sp++] = self + 1;
        }
    }
    return tmax;
}
// Lowest occluder hit below (x, ytop, z): -1e30 when none.
static float ground(float x, float z, float ytop) {
    float o[3] = {x, ytop, z}, d[3] = {0, -1, 0};
    std::vector<Hit> hits;
    float inv[3] = {1e12f, -1, 1e12f};
    (void)inv;
    float lowest = 1e30f; bool any = false;
    // all hits: trace with every occluder treated as non-blocking
    uint32_t stack[128]; int sp = 0; stack[sp++] = 0;
    float iv[3] = {1e12f, -1.0f, 1e12f};
    while (sp) {
        const Node& n = N[stack[--sp]];
        if (!slab(n, o, iv, 1e9f)) continue;
        if (n.count) {
            for (uint32_t i = n.left; i < n.left + n.count; ++i) {
                const Tri& t = T[order[i]];
                if (!(t.flags & 5)) continue; // ground: occluders, or any opaque triangle (prep bit 2)
                float th = hit(t, o, d);
                if (th < 0) continue;
                any = true; lowest = std::min(lowest, ytop - th);
            }
        } else { uint32_t self = &n - N.data(); stack[sp++] = n.left; stack[sp++] = self + 1; }
    }
    return any ? lowest : -1e30f;
}

int main(int argc, char** argv) {
    if (argc < 4) { fprintf(stderr, "usage: pvs_cast <work> <cell mm> <directions> [verify <cells> <eyes> <seed>]\n"); return 1; }
    std::string W = argv[1]; const float cell = atof(argv[2]); const int K = atoi(argv[3]);
    const bool verify = argc > 4 && !strcmp(argv[4], "verify");
    std::vector<float> eyeh;
    { const char* e = getenv("PVS_EYE_H"); std::string s = e ? e : "400,1200,2000,2800,3600"; size_t at = 0;
      while (at < s.size()) { size_t c = s.find(',', at); if (c == std::string::npos) c = s.size(); eyeh.push_back(atof(s.substr(at, c - at).c_str())); at = c + 1; } }
    const int XZ = getenv("PVS_XZ") ? atoi(getenv("PVS_XZ")) : 3;
    const float RAY = getenv("PVS_RAY") ? atof(getenv("PVS_RAY")) : 60000.f;
    FILE* f = fopen((W + "/tris.bin").c_str(), "rb"); if (!f) return 2;
    uint32_t n; if (fread(&n, 4, 1, f) != 1) return 2;
    std::vector<TriRec> R(n); if (fread(R.data(), sizeof(TriRec), n, f) != n) return 2; fclose(f);
    uint32_t ninst = 0; float wlo[3] = {1e30f, 1e30f, 1e30f}, whi[3] = {-1e30f, -1e30f, -1e30f};
    T.resize(n);
    for (uint32_t i = 0; i < n; ++i) {
        Tri& t = T[i]; const float* v = R[i].v;
        for (int a = 0; a < 3; ++a) { t.a[a] = v[a]; t.e1[a] = v[3 + a] - v[a]; t.e2[a] = v[6 + a] - v[a];
            wlo[a] = std::min({wlo[a], v[a], v[3 + a], v[6 + a]}); whi[a] = std::max({whi[a], v[a], v[3 + a], v[6 + a]}); }
        t.n[0] = t.e1[1] * t.e2[2] - t.e1[2] * t.e2[1]; t.n[1] = t.e1[2] * t.e2[0] - t.e1[0] * t.e2[2]; t.n[2] = t.e1[0] * t.e2[1] - t.e1[1] * t.e2[0];
        t.inst = R[i].inst; t.flags = R[i].flags; ninst = std::max(ninst, t.inst + 1);
    }
    order.resize(n); for (uint32_t i = 0; i < n; ++i) order[i] = i;
    N.reserve(2 * n / 3 + 16); build(0, n);
    const uint32_t nb = (ninst + 7) / 8;
    const float x0 = std::floor(wlo[0] / cell) * cell, z0 = std::floor(wlo[2] / cell) * cell;
    const uint32_t nx = uint32_t(std::ceil((whi[0] - x0) / cell)), nz = uint32_t(std::ceil((whi[2] - z0) / cell));
    const float ytop = whi[1] + 1000;
    // directions
    std::vector<float> D(3 * K);
    for (int i = 0; i < K; ++i) {
        double y = 1 - 2 * (i + 0.5) / K, r = std::sqrt(std::max(0.0, 1 - y * y)), ph = i * 2.399963229728653;
        D[3 * i] = float(r * std::cos(ph)); D[3 * i + 1] = float(y); D[3 * i + 2] = float(r * std::sin(ph));
    }
    auto cast_eye = [&](const float e[3], uint8_t* bits, unsigned seed) {
        std::vector<Hit> hits; hits.reserve(64);
        // rotate the sphere per eye (about y, and a tilt) so eyes of one cell sample different directions
        const double a1 = (seed * 0.6180339887) * 6.283185307, ca = std::cos(a1), sa = std::sin(a1);
        for (int i = 0; i < K; ++i) {
            float d[3] = {float(ca * D[3 * i] - sa * D[3 * i + 2]), D[3 * i + 1], float(sa * D[3 * i] + ca * D[3 * i + 2])};
            float tm = trace(e, d, RAY, hits);
            for (const Hit& h : hits) if (h.t <= tm) bits[h.inst >> 3] |= uint8_t(1u << (h.inst & 7));
        }
    };
    if (argc > 5 && !strcmp(argv[4], "ceil")) {
        // ceil <cams file> <width> <height>: per logged camera (one line: 12 view floats, 7 projection floats, cull_far),
        // rays through a width x height pixel grid with the game's projection, from the near plane to the cull depth.
        // Writes <work>/ceil.bin: u32 count, ninst; per camera {u8 visible[nb]; u8 frustum[nb]} (frustum: the world box
        // of the instance is not wholly outside a frustum plane or the near / cull depth).
        FILE* cf = fopen(argv[5], "r"); const int Wd = atoi(argv[6]), Ht = atoi(argv[7]);
        std::vector<std::array<float, 20>> cams; std::array<float, 20> c;
        while (true) { int k = 0; for (; k < 20; ++k) if (fscanf(cf, "%f", &c[k]) != 1) break; if (k < 20) break; cams.push_back(c); }
        fclose(cf);
        // instance world boxes from inst.tsv
        std::vector<std::array<float, 6>> box(ninst);
        { FILE* bf = fopen((W + "/inst.tsv").c_str(), "r"); char line[512]; fgets(line, sizeof line, bf);
          while (fgets(line, sizeof line, bf)) { float v[16]; int i = 0; char* q = line; for (; i < 16; ++i) { v[i] = strtof(q, &q); }
            uint32_t id = uint32_t(v[0]); if (id < ninst) for (int a = 0; a < 6; ++a) box[id][a] = v[8 + a]; } fclose(bf); }
        std::vector<uint8_t> out(cams.size() * 2 * nb, 0);
        std::vector<uint32_t> pxc(cams.size() * size_t(ninst), 0); // pixels each instance shows in (ceilpx.bin)
        const size_t tb = (T.size() + 7) / 8; std::vector<uint8_t> tvis(cams.size() * tb, 0); // triangles seen (ceilt.bin)
        std::vector<float> zbuf(cams.size() * size_t(Wd) * Ht, 0); // view depth of the first blocking occluder (ceilz.bin; 0 = none)
        #pragma omp parallel for schedule(dynamic, 1)
        for (long ci = 0; ci < (long)cams.size(); ++ci) {
            const float* v = cams[ci].data(); const float* P = v + 12; const float cfar = v[19];
            const float nearp = P[6] / (P[5] - 1);
            // world-from-view: R^-1 (R rows v[0..2], v[4..6], v[8..10]; t v[3], v[7], v[11])
            const float a = v[0], b = v[1], cc = v[2], d = v[4], f = v[5], g = v[6], k = v[8], l = v[9], m = v[10];
            const float c0 = f * m - g * l, c1 = g * k - d * m, c2 = d * l - f * k, det = a * c0 + b * c1 + cc * c2, id = 1 / det;
            const float I[9] = {c0 * id, (cc * l - b * m) * id, (b * g - cc * f) * id, c1 * id, (a * m - cc * k) * id, (cc * d - a * g) * id,
                                c2 * id, (b * k - a * l) * id, (a * f - b * d) * id};
            float eye[3]; for (int r = 0; r < 3; ++r) eye[r] = -(I[3 * r] * v[3] + I[3 * r + 1] * v[7] + I[3 * r + 2] * v[11]);
            uint8_t* vis = &out[ci * 2 * nb]; uint8_t* fr = vis + nb;
            // frustum test of each instance box (8 corners in view space, clip x/y by the projection, depth by near / cfar)
            for (uint32_t i = 0; i < ninst; ++i) {
                bool outside[6] = {true, true, true, true, true, true};
                for (int q = 0; q < 8; ++q) {
                    const float w[3] = {box[i][(q & 1) ? 3 : 0], box[i][(q & 2) ? 4 : 1], box[i][(q & 4) ? 5 : 2]};
                    const float x = a * w[0] + b * w[1] + cc * w[2] + v[3], y = d * w[0] + f * w[1] + g * w[2] + v[7], z = k * w[0] + l * w[1] + m * w[2] + v[11];
                    const float dep = -z, cx = P[1] * x + P[2] * z, cy = P[3] * y + P[4] * z;
                    if (cx >= -dep) outside[0] = false; if (cx <= dep) outside[1] = false;
                    if (cy >= -dep) outside[2] = false; if (cy <= dep) outside[3] = false;
                    if (dep >= nearp) outside[4] = false; if (dep <= cfar) outside[5] = false;
                }
                bool o = false; for (int q = 0; q < 6; ++q) o = o || outside[q];
                if (!o) fr[i >> 3] |= uint8_t(1u << (i & 7));
            }
            std::vector<Hit> hits; hits.reserve(64);
            for (int py = 0; py < Ht; ++py) for (int px = 0; px < Wd; ++px) {
                const float nx = (px + 0.5f) / Wd * 2 - 1, ny = (py + 0.5f) / Ht * 2 - 1;
                const float dv[3] = {(nx + P[2]) / P[1], (ny + P[4]) / P[3], -1.0f}; // view-space direction at depth 1
                float dw[3]; for (int r = 0; r < 3; ++r) dw[r] = I[3 * r] * dv[0] + I[3 * r + 1] * dv[1] + I[3 * r + 2] * dv[2];
                const float len = std::sqrt(dw[0] * dw[0] + dw[1] * dw[1] + dw[2] * dw[2]);
                for (int r = 0; r < 3; ++r) dw[r] /= len;
                const float tm = trace(eye, dw, cfar * len, hits, nearp * len);
                zbuf[(ci * size_t(Ht) + py) * Wd + px] = tm < cfar * len ? tm / len : 0.0f;
                uint32_t* pc = &pxc[ci * size_t(ninst)]; uint32_t last = ~0u;
                std::sort(hits.begin(), hits.end(), [](const Hit& x, const Hit& y) { return x.inst < y.inst; });
                for (const Hit& h : hits) if (h.t <= tm) tvis[ci * tb + (h.tri >> 3)] |= uint8_t(1u << (h.tri & 7));
                for (const Hit& h : hits) if (h.t <= tm) { vis[h.inst >> 3] |= uint8_t(1u << (h.inst & 7)); if (h.inst != last) { ++pc[h.inst]; last = h.inst; } }
            }
        }
        { FILE* q = fopen((W + "/ceilpx.bin").c_str(), "wb"); fwrite(pxc.data(), 4, pxc.size(), q); fclose(q); }
        { FILE* q = fopen((W + "/ceilt.bin").c_str(), "wb"); fwrite(tvis.data(), 1, tvis.size(), q); fclose(q); }
        { FILE* q = fopen((W + "/ceilz.bin").c_str(), "wb"); fwrite(zbuf.data(), 4, zbuf.size(), q); fclose(q); }
        FILE* o = fopen((W + "/ceil.bin").c_str(), "wb"); uint32_t m32 = cams.size(); fwrite(&m32, 4, 1, o); fwrite(&ninst, 4, 1, o);
        fwrite(out.data(), 1, out.size(), o); fclose(o);
        fprintf(stderr, "ceil: %zu cameras, %dx%d rays each\n", cams.size(), Wd, Ht);
        return 0;
    }
    if (verify) {
        FILE* cf = fopen(argv[5], "r"); const int per = atoi(argv[6]); const unsigned seed = atoi(argv[7]);
        std::vector<std::array<float, 4>> cells; int ix, iz; float ylo, yhi;
        while (fscanf(cf, "%d %d %f %f", &ix, &iz, &ylo, &yhi) == 4) cells.push_back({float(ix), float(iz), ylo, yhi});
        fclose(cf);
        const size_t M = cells.size() * per;
        std::vector<float> eyes(3 * M); std::vector<uint32_t> ci(M); std::vector<uint8_t> out(M * nb, 0);
        std::mt19937 rng(seed); std::uniform_real_distribution<float> U(0, 1);
        for (size_t c = 0; c < cells.size(); ++c) for (int k = 0; k < per; ++k) {
            size_t j = c * per + k; ci[j] = uint32_t(cells[c][1]) * nx + uint32_t(cells[c][0]);
            float x = x0 + (cells[c][0] + U(rng)) * cell, z = z0 + (cells[c][1] + U(rng)) * cell;
            float g = ground(x, z, ytop);
            float lo = g > -1e29f ? g + eyeh.front() : cells[c][2], hi = g > -1e29f ? g + eyeh.back() : cells[c][3];
            eyes[3 * j] = x; eyes[3 * j + 1] = lo + U(rng) * (hi - lo); eyes[3 * j + 2] = z;
        }
        #pragma omp parallel for schedule(dynamic, 1)
        for (long j = 0; j < (long)M; ++j) cast_eye(&eyes[3 * j], &out[j * nb], 1000003u + unsigned(j) * 7919u + seed);
        FILE* o = fopen((W + "/verify.bin").c_str(), "wb"); uint32_t m32 = M; fwrite(&m32, 4, 1, o);
        for (size_t j = 0; j < M; ++j) { fwrite(&ci[j], 4, 1, o); fwrite(&eyes[3 * j], 4, 3, o); fwrite(&out[j * nb], 1, nb, o); }
        fclose(o);
        fprintf(stderr, "verify: %zu eyes, %d directions\n", M, K);
        return 0;
    }
    std::vector<float> ylo(nx * nz, 0), yhi(nx * nz, 0); std::vector<uint8_t> has(nx * nz, 0), bits(size_t(nx) * nz * nb, 0);
    long rays = 0;
    #pragma omp parallel for schedule(dynamic, 1) reduction(+:rays)
    for (long c = 0; c < long(nx) * nz; ++c) {
        const uint32_t ix = c % nx, iz = c / nx;
        if (getenv("PVS_BOX")) { // x0,z0,x1,z1 (mm): only the cells meeting this box (experiments)
            float b[4]; sscanf(getenv("PVS_BOX"), "%f,%f,%f,%f", &b[0], &b[1], &b[2], &b[3]);
            if (x0 + (ix + 1) * cell < b[0] || x0 + ix * cell > b[2] || z0 + (iz + 1) * cell < b[1] || z0 + iz * cell > b[3]) continue;
        }
        std::vector<float> eyes;
        float lo = 1e30f, hi = -1e30f;
        for (int a = 0; a < XZ; ++a) for (int b = 0; b < XZ; ++b) {
            float x = x0 + (ix + (XZ > 1 ? float(a) / (XZ - 1) : 0.5f)) * cell, z = z0 + (iz + (XZ > 1 ? float(b) / (XZ - 1) : 0.5f)) * cell;
            // keep corner eyes 1 mm inside the cell
            x = std::min(std::max(x, x0 + ix * cell + 1), x0 + (ix + 1) * cell - 1);
            z = std::min(std::max(z, z0 + iz * cell + 1), z0 + (iz + 1) * cell - 1);
            float g = ground(x, z, ytop);
            if (g < -1e29f) continue;
            for (float h : eyeh) { eyes.push_back(x); eyes.push_back(g + h); eyes.push_back(z); }
            lo = std::min(lo, g + eyeh.front()); hi = std::max(hi, g + eyeh.back());
        }
        if (eyes.empty()) continue;
        has[c] = 1; ylo[c] = lo; yhi[c] = hi;
        for (size_t e = 0; e < eyes.size() / 3; ++e) { cast_eye(&eyes[3 * e], &bits[size_t(c) * nb], unsigned(c * 131 + e)); rays += K; }
    }
    FILE* o = fopen((W + "/cells.bin").c_str(), "wb");
    fwrite(&nx, 4, 1, o); fwrite(&nz, 4, 1, o); fwrite(&ninst, 4, 1, o); fwrite(&x0, 4, 1, o); fwrite(&z0, 4, 1, o); fwrite(&cell, 4, 1, o);
    uint8_t pad[3] = {0, 0, 0};
    for (size_t c = 0; c < size_t(nx) * nz; ++c) { fwrite(&ylo[c], 4, 1, o); fwrite(&yhi[c], 4, 1, o); fwrite(&has[c], 1, 1, o); fwrite(pad, 1, 3, o); fwrite(&bits[c * nb], 1, nb, o); }
    fclose(o);
    long used = 0; for (auto h : has) used += h;
    fprintf(stderr, "cast: %u x %u cells (%ld with ground), %u instances, %u triangles, %d directions, %ld rays\n", nx, nz, used, ninst, n, K, rays);
    return 0;
}
