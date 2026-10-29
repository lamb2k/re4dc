/* Asset-free KOS executable for the already-consumed EF14 cloth row API.
 * The linked wrapper, scalar body and SH4ZAM inlines are production excerpts.
 * This tests CPU numbers and production cloth clipping, not a PVR raster.
 */
#include <kos.h>
#include <arch/irq.h>
#include <arch/timer.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <re4dc_xm.h>
#include "cloth_strip_geometry11.hpp"
#include "cloth_xm14_offsets.h"

KOS_INIT_FLAGS(INIT_DEFAULT);

extern "C" void fixture_seed_xm(void);
extern "C" void fixture_probe_xm(float out[3]);

namespace {

unsigned checks;
#define CHECK(value) do { ++checks; if (!(value)) { \
    printf("CLOTH_XM14_TARGET FAIL line=%u expr=%s\n", (unsigned)__LINE__, #value); \
    fflush(stdout); \
    return 1; } } while (0)

struct Vec { float x, y, z; };
struct Input { Vec point; uint32_t guard; };
struct Output { Vec point; uint32_t guard[2]; };
static_assert(sizeof(Vec) == 12 && sizeof(Input) == 16 && sizeof(Output) == 20);

/* SH-4 FPSCR RM, DN, PR, SZ and FR are controls. Arithmetic may update the
 * exception cause/flag fields, so a full-word equality assertion is wrong. */
constexpr uint32_t kFpscrControls = 0x003c0003u;
constexpr uint32_t kFpscrPrSz = 0x00180000u;
constexpr uint32_t kFpscrFr = 0x00200000u;
uint32_t fpscr_controls()
{
    uint32_t value;
    __asm__ __volatile__("sts fpscr,%0" : "=r" (value) :: "memory");
    return value & kFpscrControls;
}

double absolute(double value) { return value < 0.0 ? -value : value; }
double oracle(const float (*m)[4], const Vec& p, unsigned row, double* magnitude)
{
    const double terms[4] = {double(m[row][0]) * p.x, double(m[row][1]) * p.y,
                             double(m[row][2]) * p.z, double(m[row][3])};
    *magnitude = absolute(terms[0]) + absolute(terms[1]) +
                 absolute(terms[2]) + absolute(terms[3]);
    return terms[0] + terms[1] + terms[2] + terms[3];
}

int run_points(unsigned count, bool four_only, bool cancellation)
{
    alignas(16) float matrix_storage[16]{};
    float rows[3][4] = {
        {1.5f, 0.25f, -0.5f, 4.0f},
        {-0.5f, 2.0f, 0.125f, -3.0f},
        {0.75f, -1.0f, 1.25f, 2.0f}
    };
    if (cancellation) {
        rows[0][0] = 1024.0f; rows[0][1] = -1024.0f;
        rows[0][2] = 0.25f; rows[0][3] = 0.125f;
    }
    float* matrix_address = matrix_storage + (four_only ? 1 : 0);
    memcpy(matrix_address, rows, sizeof(rows));
    const float (*matrix)[4] = reinterpret_cast<const float (*)[4]>(matrix_address);
    CHECK((uintptr_t(matrix) & 3u) == 0);
    if (four_only) CHECK((uintptr_t(matrix) & 15u) == 4);

    Input input[100]{};
    Output scalar[100]{}, batch[100]{};
    for (unsigned i = 0; i < count; ++i) {
        input[i].point = {float(i) * 0.03125f - 2.0f,
                          float(i * i % 19) * 0.125f - 1.0f,
                          -float(i) * 0.0625f - 3.0f};
        if (cancellation) input[i].point = {1.0f + float(i % 4) * (1.0f / 1024.0f),
                                               1.0f, 0.5f};
        input[i].guard = 0x1234abcdu;
        scalar[i].guard[0] = batch[i].guard[0] = 0x71727374u;
        scalar[i].guard[1] = batch[i].guard[1] = 0x81828384u;
    }
    const uint32_t fpscr_before = fpscr_controls();
    CHECK((fpscr_before & (0x00080000u | 0x00100000u)) == 0);
    CHECK(re4dc_zam_xm_points14_scalar(matrix, input, count * sizeof(Input),
           sizeof(Input), scalar, count * sizeof(Output), sizeof(Output), count) == 1);
    CHECK(fpscr_controls() == fpscr_before);
    CHECK(re4dc_zam_xm_points14(matrix, input, count * sizeof(Input),
           sizeof(Input), batch, count * sizeof(Output), sizeof(Output), count) == 1);
    CHECK(fpscr_controls() == fpscr_before);
    for (unsigned i = 0; i < count; ++i) {
        CHECK(input[i].guard == 0x1234abcdu);
        CHECK(scalar[i].guard[0] == 0x71727374u && scalar[i].guard[1] == 0x81828384u);
        CHECK(batch[i].guard[0] == 0x71727374u && batch[i].guard[1] == 0x81828384u);
        const float sv[3] = {scalar[i].point.x, scalar[i].point.y, scalar[i].point.z};
        const float bv[3] = {batch[i].point.x, batch[i].point.y, batch[i].point.z};
        for (unsigned row = 0; row < 3; ++row) {
            double magnitude;
            const double exact = oracle(matrix, input[i].point, row, &magnitude);
            const double tolerance = 0.00001 + 0.000003 * magnitude;
            CHECK(__builtin_isfinite(sv[row]) && __builtin_isfinite(bv[row]));
            CHECK(absolute(double(sv[row]) - exact) <= tolerance);
            CHECK(absolute(double(bv[row]) - exact) <= tolerance);
            CHECK(absolute(double(sv[row]) - double(bv[row])) <= 2.0 * tolerance);
        }
    }
    if (cancellation) {
        CHECK(absolute(batch[0].point.x - 0.25) < 0.001);
        CHECK(absolute(scalar[0].point.x - 0.25) < 0.001);
    }
    /* A second call must load its matrix afresh after another XMTRX owner. */
    if (count >= 4) {
        fixture_seed_xm();
        Output again[100]{};
        const uint32_t fpscr_interleaved = fpscr_controls();
        CHECK(re4dc_zam_xm_points14(matrix, input, count * sizeof(Input),
               sizeof(Input), again, count * sizeof(Output), sizeof(Output), count) == 1);
        CHECK(fpscr_controls() == fpscr_interleaved);
        for (unsigned i = 0; i < count; ++i)
            CHECK(memcmp(&again[i].point, &batch[i].point, sizeof(Vec)) == 0);
    }
    return 0;
}

int run_near_plane()
{
    alignas(16) const float matrix[3][4] = {
        {1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}
    };
    Vec source[100]{}, scalar[100]{}, batch[100]{};
    const float depths[4] = {-0.5f, -0.99f, -1.01f, -10.0f};
    for (unsigned i = 0; i < 100; ++i) source[i] = {float(i) * 0.01f, 0, depths[i % 4]};
    const uint32_t fpscr_before = fpscr_controls();
    CHECK(re4dc_zam_xm_points14_scalar(matrix, source, sizeof(source), sizeof(Vec),
           scalar, sizeof(scalar), sizeof(Vec), 100) == 1);
    CHECK(re4dc_zam_xm_points14(matrix, source, sizeof(source), sizeof(Vec),
           batch, sizeof(batch), sizeof(Vec), 100) == 1);
    CHECK(fpscr_controls() == fpscr_before);
    unsigned retained = 0;
    for (unsigned i = 0; i < 100; ++i) {
        /* The production geometry near decision is depth >= near_distance;
         * this checks transformed signs/classes, not the packet clipper. */
        const bool old_class = -scalar[i].z >= 1.0f;
        const bool new_class = -batch[i].z >= 1.0f;
        CHECK(old_class == new_class);
        CHECK(old_class == (i % 4 >= 2));
        retained += new_class;
    }
    CHECK(retained == 50);
    return 0;
}

int run_in_place()
{
    alignas(16) const float matrix[3][4] = {
        {1.5f, 0.25f, -0.5f, 4.0f},
        {-0.5f, 2.0f, 0.125f, -3.0f},
        {0.75f, -1.0f, 1.25f, 2.0f}
    };
    Vec points[5] = {{1,2,3}, {4,5,6}, {-2,1,-8}, {0,0,-2}, {8,-3,-10}};
    Vec scalar[5]{};
    CHECK(re4dc_zam_xm_points14_scalar(matrix, points, sizeof(points), sizeof(Vec),
           scalar, sizeof(scalar), sizeof(Vec), 5) == 1);
    CHECK(re4dc_zam_xm_points14(matrix, points, sizeof(points), sizeof(Vec),
           points, sizeof(points), sizeof(Vec), 5) == 1);
    for (unsigned i = 0; i < 5; ++i) {
        CHECK(absolute(points[i].x - scalar[i].x) < 0.0001);
        CHECK(absolute(points[i].y - scalar[i].y) < 0.0001);
        CHECK(absolute(points[i].z - scalar[i].z) < 0.0001);
    }
    return 0;
}

int run_clipped_cells()
{
    alignas(16) const float matrix[3][4] = {
        {1.5f, 0.25f, 0, 0.125f},
        {-0.25f, 1.25f, 0, -0.125f},
        {0, 0, 1, -0.25f}
    };
    unsigned vertices = 0, empty = 0, complete = 0, clipped = 0;
    for (unsigned mask = 0; mask < 16; ++mask) {
        const Vec source[4] = {
            {-0.25f, 0.25f, (mask & 1u) ? -1.75f : -0.25f},
            {-0.25f, -0.25f, (mask & 2u) ? -1.75f : -0.25f},
            {0.25f, 0.25f, (mask & 4u) ? -1.75f : -0.25f},
            {0.25f, -0.25f, (mask & 8u) ? -1.75f : -0.25f}
        };
        Vec scalar[4], batch[4];
        const uint32_t before = fpscr_controls();
        CHECK(re4dc_zam_xm_points14_scalar(matrix, source, sizeof(source), sizeof(Vec),
              scalar, sizeof(scalar), sizeof(Vec), 4) == 1);
        CHECK(re4dc_zam_xm_points14(matrix, source, sizeof(source), sizeof(Vec),
              batch, sizeof(batch), sizeof(Vec), 4) == 1);
        CHECK(fpscr_controls() == before);
        Re4dcEffectQuad reference{}, candidate{};
        const float projection[] = {0, 1, 0, 1, 0, -0.01f, -1.01f};
        const float viewport[] = {0, 0, 640, 480, 0, 1};
        memcpy(reference.projection, projection, sizeof(projection));
        memcpy(reference.viewport, viewport, sizeof(viewport));
        reference.color = 0x91827364u;
        reference.src = 4; reference.dst = 5;
        for (unsigned i = 0; i < 4; ++i) {
            reference.u[i] = i >= 2 ? 1.0f : 0.0f;
            reference.v[i] = i & 1u ? 1.0f : 0.0f;
        }
        candidate = reference;
        memcpy(reference.positions, scalar, sizeof(scalar));
        memcpy(candidate.positions, batch, sizeof(batch));
        struct Guarded { pvr_vertex_t out[12]; uint32_t guard; } old{}, now{};
        old.guard = now.guard = 0x71727374u;
        const unsigned a = re4dc::cloth11::cell(reference, old.out);
        const unsigned b = re4dc::cloth11::cell(candidate, now.out);
        CHECK(a == b && a <= 12 && a % 3 == 0);
        CHECK(old.guard == 0x71727374u && now.guard == 0x71727374u);
        CHECK(fpscr_controls() == before);
        if (!mask) { CHECK(a == 0); ++empty; }
        else if (mask == 15) { CHECK(a == 6); ++complete; }
        else { CHECK(a > 0); ++clipped; }
        for (unsigned i = 0; i < a; ++i) {
            const auto& x = old.out[i]; const auto& y = now.out[i];
            CHECK(x.flags == y.flags && x.argb == y.argb && x.oargb == y.oargb);
            CHECK(__builtin_isfinite(y.x) && __builtin_isfinite(y.y) &&
                  __builtin_isfinite(y.z) && __builtin_isfinite(y.u) && __builtin_isfinite(y.v));
            CHECK(absolute(x.x - y.x) <= 0.001 && absolute(x.y - y.y) <= 0.001);
            CHECK(absolute(x.z - y.z) <= 0.00001 && absolute(x.u - y.u) <= 0.00001 &&
                  absolute(x.v - y.v) <= 0.00001);
        }
        vertices += a;
    }
    printf("CLOTH_XM14_CLIP cases=16 empty=%u complete=%u clipped=%u vertices=%u\n",
           empty, complete, clipped, vertices);
    return 0;
}

int reject(const float (*matrix)[4], const void* source, unsigned source_bytes,
           unsigned source_stride, void* output, unsigned output_bytes,
           unsigned output_stride, unsigned count,
           const void* protected_bytes, unsigned protected_count)
{
    CHECK(protected_count <= 160);
    unsigned char before[160];
    memcpy(before, protected_bytes, protected_count);
    fixture_seed_xm();
    float xm_before[3], xm_after[3];
    fixture_probe_xm(xm_before);
    CHECK(xm_before[0] == 9.0f && xm_before[1] == 17.0f && xm_before[2] == 28.0f);
    const uint32_t fpscr_before = fpscr_controls();
    CHECK(re4dc_zam_xm_points14(matrix, source, source_bytes, source_stride,
          output, output_bytes, output_stride, count) == 0);
    CHECK(fpscr_controls() == fpscr_before);
    fixture_probe_xm(xm_after);
    CHECK(memcmp(xm_after, xm_before, sizeof(xm_after)) == 0);
    CHECK(memcmp(protected_bytes, before, protected_count) == 0);
    CHECK(re4dc_zam_xm_points14_scalar(matrix, source, source_bytes, source_stride,
          output, output_bytes, output_stride, count) == 0);
    CHECK(fpscr_controls() == fpscr_before);
    fixture_probe_xm(xm_after);
    CHECK(memcmp(xm_after, xm_before, sizeof(xm_after)) == 0);
    CHECK(memcmp(protected_bytes, before, protected_count) == 0);
    return 0;
}

int run_rejections()
{
    alignas(16) float matrix[3][4] = {
        {1.5f, 0.25f, -0.5f, 4.0f},
        {-0.5f, 2.0f, 0.125f, -3.0f},
        {0.75f, -1.0f, 1.25f, 2.0f}
    };
    Input source[5]{};
    alignas(16) unsigned char out[128];
    memset(out, 0x5a, sizeof(out));
    CHECK(reject(matrix, source, sizeof(source), sizeof(Input), out, 12, 12, 2,
          out, sizeof(out)) == 0);  // short output span
    CHECK(reject(matrix, source, 11, sizeof(Input), out, sizeof(out), 12, 1,
          out, sizeof(out)) == 0);  // short input span
    CHECK(reject(matrix, source, sizeof(source), 8, out, sizeof(out), 12, 2,
          out, sizeof(out)) == 0);  // stride shorter than Vec
    CHECK(reject(matrix, source, sizeof(source), 13, out, sizeof(out), 12, 2,
          out, sizeof(out)) == 0);  // stride not word aligned
    CHECK(reject(matrix, source, sizeof(source), sizeof(Input), out + 1,
          sizeof(out) - 1, 12, 2, out, sizeof(out)) == 0);
    CHECK(reject(matrix, source, sizeof(source), sizeof(Input), out,
          sizeof(out), 12, 0, out, sizeof(out)) == 0);
    CHECK(reject(matrix, source, sizeof(source), sizeof(Input), out,
          sizeof(out), 12, 101, out, sizeof(out)) == 0);
    CHECK(reject(matrix, out, sizeof(out), 12, out + 4,
          sizeof(out) - 4, 12, 3, out, sizeof(out)) == 0); // shifted overlap
    CHECK(reject(matrix, matrix, sizeof(matrix), 12, out, sizeof(out), 12, 2,
          out, sizeof(out)) == 0); // matrix/source overlap
    CHECK(reject(matrix, source, sizeof(source), sizeof(Input), matrix,
          sizeof(matrix), 12, 2, matrix, sizeof(matrix)) == 0); // matrix/output overlap
    CHECK(reject(reinterpret_cast<const float (*)[4]>(
          reinterpret_cast<const unsigned char*>(matrix) + 1), source,
          sizeof(source), sizeof(Input), out, sizeof(out), 12, 2,
          out, sizeof(out)) == 0);
    CHECK(reject(matrix, reinterpret_cast<const void*>(UINTPTR_MAX - 3u),
          UINT32_MAX, 12, out, sizeof(out), 12, 2, out, sizeof(out)) == 0);
    CHECK(reject(matrix, source, UINT32_MAX, UINT32_MAX - 3u, out, sizeof(out),
          12, 2, out, sizeof(out)) == 0);
    return 0;
}

/* Use a real asynchronous KOS IRQ, without inserting a call into the production
 * row loop. The driver derives exact FTRV offsets from the production object;
 * an IRQ elsewhere in the function is deliberately insufficient evidence.
 * KOS 804b319 entry.s saves both FP banks and FPSCR before invoking this handler.
 * We overwrite XMTRX here and require the interrupted row to survive restoration.
 * This is a timer-IRQ test, not a claim about NMI or arbitrary fault handlers. */
volatile uint32_t irq_count, irq_ftrv_hits, irq_errors;
volatile uint32_t irq_saved_controls, irq_handler_controls;
uint32_t irq_expected_controls;

bool interrupted_ftrv(uintptr_t pc)
{
    const uintptr_t start = reinterpret_cast<uintptr_t>(&re4dc_zam_xm_points14);
    for (unsigned offset : kFixtureFtrvOffsets) {
        /* SPC is the next instruction at a normal IRQ boundary. Accept the
         * FTRV itself or its immediately following instruction, never a broad
         * function range containing preflight or a scalar fallback. */
        if (pc == start + offset || pc == start + offset + 2u) return true;
    }
    return false;
}

void interrupt_xm_owner(irq_t code, irq_context_t* context, void*)
{
    timer_clear(TMU1);
    irq_count = irq_count + 1u;
    if (code != EXC_TMU1_TUNI1 || !context || !irq_inside_int()) {
        irq_errors = irq_errors | 1u;
        return;
    }
    const uint32_t entry = fpscr_controls();
    /* The pinned KOS exception entry normalizes the handler to PR=SZ=FR=0.
     * Do not use FPU instructions under an unexpected handler mode. */
    if (entry & (kFpscrPrSz | kFpscrFr)) {
        irq_errors = irq_errors | 2u;
        return;
    }
    const bool in_ftrv = interrupted_ftrv(context->pc);
    if (in_ftrv) {
        irq_ftrv_hits = irq_ftrv_hits + 1u;
        irq_saved_controls = context->fpscr & kFpscrControls;
        irq_handler_controls = entry;
        if (irq_saved_controls != irq_expected_controls)
            irq_errors = irq_errors | 4u;
    }
    fixture_seed_xm();
    float probe[3];
    fixture_probe_xm(probe);
    if (probe[0] != 9.0f || probe[1] != 17.0f || probe[2] != 28.0f ||
        fpscr_controls() != entry) irq_errors = irq_errors | 8u;
}

int run_interruptions()
{
    alignas(16) const float matrix[3][4] = {
        {1.5f, 0.25f, -0.5f, 4.0f},
        {-0.5f, 2.0f, 0.125f, -3.0f},
        {0.75f, -1.0f, 1.25f, 2.0f}
    };
    Vec source[100], expected[100], actual[100];
    for (unsigned i = 0; i < 100; ++i)
        source[i] = {float(i) * 0.03125f - 2.0f,
                     float(i % 19) * 0.125f - 1.0f,
                     -float(i) * 0.0625f - 3.0f};
    irq_expected_controls = fpscr_controls();
    CHECK((irq_expected_controls & kFpscrPrSz) == 0);
    CHECK(re4dc_zam_xm_points14(matrix, source, sizeof(source), sizeof(Vec),
          expected, sizeof(expected), sizeof(Vec), 100) == 1);
    CHECK(fpscr_controls() == irq_expected_controls);

    /* TMU1 is unused in this standalone fixture. Refuse to take a live timer;
     * retain the existing (normally default) handler and priority on exit. */
    CHECK(!timer_running(TMU1));
    const irq_cb_t previous = irq_get_handler(EXC_TMU1_TUNI1);
    const unsigned previous_priority = irq_get_priority(IRQ_SRC_TMU1);
    CHECK(irq_set_handler(EXC_TMU1_TUNI1, interrupt_xm_owner, nullptr) == 0);
    unsigned rounds = 0, output_errors = 0;
    const unsigned rates[] = {9973u, 17011u, 23003u};
    for (unsigned rate : rates) {
        timer_prime(TMU1, rate, 1);
        timer_clear(TMU1);
        timer_start(TMU1);
        for (unsigned i = 0; i < 4096; ++i) {
            const int result = re4dc_zam_xm_points14(matrix, source, sizeof(source),
                sizeof(Vec), actual, sizeof(actual), sizeof(Vec), 100);
            ++rounds;
            if (result != 1 || memcmp(actual, expected, sizeof(actual)) != 0 ||
                fpscr_controls() != irq_expected_controls) ++output_errors;
            if (irq_errors || output_errors || irq_ftrv_hits >= 4u) break;
        }
        timer_stop(TMU1);
        timer_clear(TMU1);
        if (irq_errors || output_errors || irq_ftrv_hits >= 4u) break;
    }
    /* Cleanup precedes every assertion after installing the timer handler. */
    const irq_mask_t mask = irq_disable();
    timer_stop(TMU1);
    timer_clear(TMU1);
    irq_set_handler(EXC_TMU1_TUNI1, previous.hdl, previous.data);
    irq_set_priority(IRQ_SRC_TMU1, previous_priority);
    irq_restore(mask);
    printf("CLOTH_XM14_IRQ irqs=%u ftrv_hits=%u rounds=%u errors=%u output_errors=%u "
           "saved=%08x handler=%08x entry=%08x exit=%08x\n",
           unsigned(irq_count), unsigned(irq_ftrv_hits), rounds, unsigned(irq_errors),
           output_errors, unsigned(irq_saved_controls), unsigned(irq_handler_controls),
           irq_expected_controls, fpscr_controls());
    CHECK(irq_count > 0u && irq_ftrv_hits >= 4u);
    CHECK(irq_errors == 0u && output_errors == 0u);
    CHECK(fpscr_controls() == irq_expected_controls);
    return 0;
}

} // namespace

int main()
{
    const uint32_t entry = fpscr_controls();
    printf("CLOTH_XM14_FPSCR entry=%08x pr=%u sz=%u fr=%u\n", entry,
           unsigned((entry >> 19) & 1u), unsigned((entry >> 20) & 1u),
           unsigned((entry >> 21) & 1u));
    CHECK((entry & kFpscrPrSz) == 0);
    const unsigned counts[] = {1u, 2u, 3u, 4u, 5u, 99u, 100u};
    for (unsigned count : counts) {
        if (run_points(count, false, false)) return 1;
        if (run_points(count, true, false)) return 1;
    }
    if (run_points(5, true, true) || run_near_plane() ||
        run_in_place() || run_clipped_cells() || run_rejections() || run_interruptions()) return 1;
    CHECK(fpscr_controls() == entry);
    printf("CLOTH_XM14_TARGET PASS checks=%u source=bbfd3254 sh4zam=33fa4850 "
           "fixture=irq1 build=%s\n", checks, kFixtureBuildId);
    fflush(stdout);
    return 0;
}
