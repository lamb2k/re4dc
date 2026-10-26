// Synthetic Build17 gate. The policy, native adapter, wrappers and first Snd
// read come from production source; the fake supplies only devices and data.
// Fake-clock deadlines are not Dreamcast throughput or cycle measurements.
#include "disc_pio_fallback.h"
#include "disc_stream_table_check.h"
#include <algorithm>
#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <deque>
#include <functional>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using re4dc::disc_pio::Command;
using re4dc::disc_pio::Request;
using re4dc::disc_pio::Result;
using re4dc::disc_pio::State;
using re4dc::disc_pio::read;
using re4dc::disc_pio::stream_table_valid;

namespace test {
unsigned assertions = 0, passed = 0, failed = 0;
void require(bool value, const char* expression, int line) {
    ++assertions;
    if (!value) throw std::runtime_error(std::string(expression) + " at line " + std::to_string(line));
}
#define REQUIRE(x) test::require(bool(x), #x, __LINE__)
void run(const char* group, const std::string& name, const std::function<void()>& body) {
    try {
        body();
        ++passed;
        std::printf("CASE\t%s\t%s\tPASS\n", group, name.c_str());
    } catch (const std::exception& error) {
        ++failed;
        std::printf("CASE\t%s\t%s\tFAIL\t%s\n", group, name.c_str(), error.what());
    }
}
void word(unsigned char* data, size_t offset, uint32_t value) {
    std::memcpy(data + offset, &value, sizeof(value));
}
constexpr size_t file_length = 5000;
constexpr uint32_t file_sector = 200;
std::vector<unsigned char> table_image() {
    std::vector<unsigned char> bytes(6144, 0x69);
    word(bytes.data(), 0, 8);
    word(bytes.data(), 4, 4200);  // header in a cached partial final sector
    for (size_t offset : {size_t(8), size_t(4200)}) {
        word(bytes.data(), offset, 1);
        word(bytes.data(), offset + 4, 12);
        word(bytes.data(), offset + 8, 136);
    }
    return bytes;
}
unsigned char sector_byte(uint32_t sector, size_t offset) {
    return static_cast<unsigned char>((sector * 37u + offset * 17u + offset / 23u) & 255u);
}
void fill(const Request& r, const std::vector<unsigned char>& file = {}) {
    auto* out = static_cast<unsigned char*>(r.buffer);
    for (size_t i = 0; i < r.count * 2048; ++i) {
        uint32_t sector = r.sector + static_cast<uint32_t>(i / 2048);
        const size_t position = size_t(sector - file_sector) * 2048 + i % 2048;
        out[i] = sector >= file_sector && position < file.size() ? file[position] : sector_byte(sector, i % 2048);
    }
}
void check_data(const Request& r, const std::vector<unsigned char>& file = {}) {
    std::vector<unsigned char> expected(r.count * 2048);
    fill({expected.data(), r.sector, r.count}, file);
    REQUIRE(std::memcmp(r.buffer, expected.data(), expected.size()) == 0);
}
enum class Fault { none, drop, io, no_disc, changed, missing, corrupt, streaming, not_found };
struct Plan {
    Fault fault = Fault::none;
    unsigned complete_ms = 20;
    unsigned data_ms = 20;
    size_t corrupt_offset = 0;
    unsigned idle_ms = 0;  // zero uses data_ms; nonzero separates idle and landing
};
struct Seen { Request request; bool dma; };
struct Switch { Result reason; bool session; unsigned failures; };
struct FakeDriver {
    uint64_t clock = 0, begun = 0;
    bool owned = false, acquire_ok = true, enabled = true, busy = false, landed_data = false;
    bool aborted = false, abort_hangs = false, stop_on_disable = true, reset_stuck = false;
    bool init_fails = false, init_hangs = false, mode_fails = false, init_active = false;
    bool active = false, cancelled = false, late_cancelled = false;
    unsigned acquisitions = 0, releases = 0, disables = 0, enables = 0, aborts = 0;
    unsigned resets = 0, modes = 0, clears = 0, prepares = 0, submitted = 0;
    unsigned submit_refusals = 0, sector_size = 2048, late_events = 0, delivered_late = 0;
    int handle = 0;
    Plan current;
    Request request{};
    std::deque<Plan> plans;
    std::vector<Seen> seen;
    std::vector<Switch> switches;
    std::vector<std::string> trace;
    std::vector<unsigned char> file;
    uint64_t late_at = 0;

    uint64_t now() const { return clock; }
    bool acquire() {
        ++acquisitions;
        REQUIRE(!owned);
        if (!acquire_ok) return false;
        owned = true;
        trace.push_back("acquire");
        return true;
    }
    void release() {
        REQUIRE(owned);
        ++releases;
        owned = false;
        trace.push_back("release");
    }
    void service() {
        if (late_at && clock >= late_at) {
            ++late_events;
            // A disabled and retired command cannot own a destination. The
            // late interrupt itself must not create a new completion token.
            if (!late_cancelled) ++delivered_late;
            late_at = 0;
        }
        if (!active || aborted || init_active || cancelled) return;
        if (current.fault != Fault::drop && current.fault != Fault::streaming &&
            clock - begun >= current.data_ms) {
            if (current.fault == Fault::none || current.fault == Fault::corrupt) {
                if (!landed_data) {
                    fill(request, file);
                    if (current.fault == Fault::corrupt)
                        word(static_cast<unsigned char*>(request.buffer), current.corrupt_offset, 0xfffffffcu);
                    landed_data = true;
                }
            }
            busy = false;
        }
    }
    void pause(uint64_t, unsigned, bool) { REQUIRE(owned); clock += 10; service(); }
    void prepare(const Request& r, bool) {
        REQUIRE(owned && !busy);
        REQUIRE(sector_size == 2048);
        REQUIRE(enabled);
        ++prepares;
        trace.push_back("prepare");
        std::memset(r.buffer, 0xed, r.count * 2048);
        landed_data = false;
    }
    int submit(const Request& r, bool dma) {
        REQUIRE(owned && !busy);
        if (submit_refusals) { --submit_refusals; return 0; }
        current = plans.empty() ? Plan{} : plans.front();
        if (!plans.empty()) plans.pop_front();
        seen.push_back({r, dma});
        request = r;
        begun = clock;
        busy = dma;
        aborted = cancelled = init_active = false;
        active = true;
        ++submitted;
        trace.push_back(dma ? "dma" : "pio");
        return ++handle;
    }
    Command check(int h) {
        REQUIRE(owned && h == handle);
        service();
        if (init_active) return init_hangs ? Command::pending : init_fails ? Command::failed : Command::done;
        if (aborted) return abort_hangs ? Command::pending : Command::done;
        if (clock - begun < current.complete_ms) return Command::pending;
        switch (current.fault) {
            case Fault::drop: case Fault::streaming: return Command::pending;
            case Fault::io: return Command::failed;
            case Fault::no_disc: return Command::no_disc;
            case Fault::changed: return Command::disc_changed;
            default: return Command::done;
        }
    }
    bool engine_busy() { REQUIRE(owned); service(); return busy; }
    bool landed(const Request&) { REQUIRE(owned && !busy); service(); return landed_data; }
    void disable_dma() {
        REQUIRE(owned);
        ++disables;
        enabled = false;
        trace.push_back("disable");
        if (stop_on_disable) busy = false;
    }
    void enable_dma() { REQUIRE(owned && !busy); ++enables; enabled = true; trace.push_back("enable"); }
    void abort(int h) {
        REQUIRE(owned && !enabled && h == handle);
        ++aborts;
        aborted = cancelled = late_cancelled = true;
        late_at = clock + 40;
        trace.push_back("abort");
    }
    void reset() {
        REQUIRE(owned && !enabled);
        ++resets;
        busy = reset_stuck;
        cancelled = true;
        sector_size = 2352;
        trace.push_back("reset");
    }
    int submit_init() {
        REQUIRE(owned && !busy && !enabled);
        init_active = true;
        trace.push_back("init");
        return ++handle;
    }
    bool sector_mode_2048() {
        REQUIRE(owned && !busy && !enabled && init_active);
        ++modes;
        trace.push_back("mode2048");
        if (!mode_fails) sector_size = 2048;
        return !mode_fails;
    }
    void clear_events() { REQUIRE(owned && !busy); ++clears; trace.push_back("clear"); }
    void switched(Result r, bool session, unsigned failures) {
        REQUIRE(owned && !busy);
        switches.push_back({r, session, failures});
    }
    void balanced() const { REQUIRE(!owned && acquisitions == releases); }
};

void portable_cases() {
    run("controller", "normal_dma_has_one_owner_and_no_switch", [] {
        alignas(32) unsigned char buffer[4096];
        FakeDriver d; State s;
        Request r{buffer, 91, 2};
        REQUIRE(read(d, s, r, true) == Result::ok);
        check_data(r); d.balanced();
        REQUIRE(d.seen.size() == 1 && d.seen[0].dma && d.switches.empty());
        REQUIRE(d.disables == 0 && d.clears == 1 && s.failures == 0);
    });
    for (Fault fault : {Fault::drop, Fault::io, Fault::missing}) {
        run("controller", "same_sectors_retry_fault_" + std::to_string(int(fault)), [fault] {
            alignas(32) unsigned char buffer[6144];
            FakeDriver d; State s; d.plans = {{fault}, {}};
            Request r{buffer, 0x123456, 3};
            REQUIRE(read(d, s, r, true) == Result::ok);
            REQUIRE(d.seen.size() == 2 && d.seen[0].dma && !d.seen[1].dma);
            for (const Seen& seen : d.seen)
                REQUIRE(seen.request.buffer == r.buffer && seen.request.sector == r.sector && seen.request.count == r.count);
            REQUIRE(d.switches.size() == 1 && d.switches[0].failures == 1 && !d.switches[0].session);
            REQUIRE(d.disables == 1 && d.aborts == 1 && d.enables == 1);
            REQUIRE(d.clock < 7000 && s.failures == 1 && !s.session_pio);
            check_data(r); d.balanced();
        });
    }
    run("controller", "command_done_waits_for_dma_engine_and_buffer", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; d.plans = {{Fault::none, 10, 180}};
        REQUIRE(read(d, s, {buffer, 8, 1}, true) == Result::ok);
        REQUIRE(d.clock >= 180 && d.switches.empty() && !d.busy);
        d.balanced();
    });
    run("controller", "late_old_completion_cannot_write_into_reused_buffer", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; d.plans = {{Fault::drop}, {Fault::none, 120, 120}};
        Request r{buffer, 12, 1};
        REQUIRE(read(d, s, r, true) == Result::ok);
        REQUIRE(d.late_events == 1 && d.delivered_late == 0);
        check_data(r); d.balanced();
    });
    run("controller", "two_dma_failures_latch_and_pio_does_not_clear", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; d.plans = {{Fault::drop}, {}, {Fault::io}, {}, {}};
        for (unsigned i = 0; i < 3; ++i) REQUIRE(read(d, s, {buffer, 10 + i, 1}, true) == Result::ok);
        REQUIRE(d.seen.size() == 5 && !d.seen.back().dma);
        REQUIRE(s.session_pio && s.failures == 2 && d.switches.size() == 2);
        REQUIRE(!d.switches[0].session && d.switches[1].session);
        d.balanced();
    });
    run("controller", "successful_dma_breaks_consecutive_streak", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; d.plans = {{Fault::drop}, {}, {}, {Fault::drop}, {}};
        for (unsigned i = 0; i < 3; ++i) REQUIRE(read(d, s, {buffer, 10 + i, 1}, true) == Result::ok);
        REQUIRE(!s.session_pio && s.failures == 1 && d.switches.size() == 2);
        d.balanced();
    });
    for (Fault fault : {Fault::no_disc, Fault::changed}) {
        run("controller", "media_change_is_not_dma_failure_" + std::to_string(int(fault)), [fault] {
            alignas(32) unsigned char buffer[2048];
            FakeDriver d; State s; d.plans = {{fault}};
            REQUIRE(read(d, s, {buffer, 2, 1}, true) == (fault == Fault::no_disc ? Result::no_disc : Result::disc_changed));
            REQUIRE(d.seen.size() == 1 && d.switches.empty() && s.failures == 0 && !d.busy);
            d.balanced();
        });
    }
    run("controller", "pio_failure_is_bounded_and_not_retried_recursively", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; d.plans = {{Fault::drop}, {Fault::drop}};
        REQUIRE(read(d, s, {buffer, 5, 1}, true) == Result::timeout);
        REQUIRE(d.seen.size() == 2 && d.aborts == 2 && s.failures == 1 && d.clock < 13000);
        d.balanced();
    });
    run("controller", "explicit_pio_and_two_byte_alignment_do_not_count", [] {
        alignas(32) unsigned char buffer[2080];
        FakeDriver d; State s; s.failures = 1;
        REQUIRE(read(d, s, {buffer, 5, 1}, false) == Result::ok);
        REQUIRE(read(d, s, {buffer + 2, 5, 1}, true) == Result::ok);
        REQUIRE(!d.seen[0].dma && !d.seen[1].dma && s.failures == 1);
        d.balanced();
    });
    run("controller", "submission_refusal_has_deadline_and_same_sector_pio", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; d.submit_refusals = 21;
        REQUIRE(read(d, s, {buffer, 99, 1}, true) == Result::ok);
        REQUIRE(d.clock >= 200 && d.clock < 1000 && d.seen.size() == 1 && !d.seen[0].dma);
        REQUIRE(d.aborts == 0 && s.failures == 1);
        d.balanced();
    });
    for (unsigned recovery = 0; recovery < 2; ++recovery) {
        run("controller", "reset_restores_2048_before_retry_" + std::to_string(recovery), [recovery] {
            alignas(32) unsigned char buffer[2048];
            FakeDriver d; State s; d.plans = {{Fault::drop}, {}};
            d.abort_hangs = recovery == 0;
            d.stop_on_disable = recovery == 0;
            REQUIRE(read(d, s, {buffer, 23, 1}, true) == Result::ok);
            REQUIRE(d.resets == 1 && d.modes == 1 && d.sector_size == 2048);
            const auto mode = std::find(d.trace.begin(), d.trace.end(), "mode2048");
            const auto pio = std::find(d.trace.begin(), d.trace.end(), "pio");
            REQUIRE(mode < pio && d.clock < 10000);
            d.balanced();
        });
    }
    for (unsigned failure = 0; failure < 4; ++failure) {
        run("controller", "unsafe_retirement_poison_blocks_reuse_" + std::to_string(failure), [failure] {
            alignas(32) unsigned char buffer[2048];
            FakeDriver d; State s; d.plans = {{Fault::drop}};
            d.abort_hangs = true;
            d.reset_stuck = failure == 0;
            d.init_fails = failure == 1;
            d.init_hangs = failure == 2;
            d.mode_fails = failure == 3;
            REQUIRE(read(d, s, {buffer, 4, 1}, true) == Result::unsafe);
            REQUIRE(s.poisoned && d.seen.size() == 1 && d.enables == 0);
            const unsigned before = d.prepares;
            REQUIRE(read(d, s, {buffer, 8, 1}, true) == Result::unsafe);
            REQUIRE(d.prepares == before && d.clock < 15000);
            d.balanced();
        });
    }
    run("controller", "invalid_requests_do_not_acquire_or_touch_buffers", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s;
        const std::array<Request, 5> invalid = {{{nullptr, 1, 1}, {buffer + 1, 1, 1},
            {buffer, 1, 0}, {buffer, 1, size_t(UINT32_MAX / 2048u) + 1}, {buffer, UINT32_MAX, 2}}};
        for (const Request& r : invalid) REQUIRE(read(d, s, r, true) == Result::invalid);
        REQUIRE(d.acquisitions == 0 && d.prepares == 0);
    });
    run("controller", "ownership_timeout_never_submits", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; d.acquire_ok = false;
        REQUIRE(read(d, s, {buffer, 3, 1}, true) == Result::lock_timeout);
        REQUIRE(d.prepares == 0 && d.releases == 0 && !d.owned);
    });
    run("semantic", "two_corrupt_dma_windows_latch_session_pio", [] {
        alignas(32) unsigned char buffer[6144];
        FakeDriver d; State s; d.file = table_image();
        d.plans = {{Fault::corrupt}, {}, {Fault::corrupt}, {}, {}};
        for (unsigned attempt = 0; attempt < 2; ++attempt) {
            s.validation_begin();
            REQUIRE(read(d, s, {buffer, file_sector, 3}, true) == Result::ok);
            REQUIRE(!stream_table_valid(buffer, file_length, 2));
            REQUIRE(s.validation_reject());
            REQUIRE(!s.validation_reject());
            REQUIRE(read(d, s, {buffer, file_sector, 3}, true) == Result::ok);
            REQUIRE(stream_table_valid(buffer, file_length, 2));
            s.validation_end();
            REQUIRE(s.failures == attempt + 1);
        }
        REQUIRE(s.session_pio && !s.retry_pio);
        s.validation_begin();
        REQUIRE(read(d, s, {buffer, file_sector, 3}, true) == Result::ok);
        REQUIRE(!d.seen.back().dma && !s.validation_reject());
        s.validation_end();
        REQUIRE(s.failures == 2);
        d.balanced();
    });
    run("semantic", "accepted_window_clears_only_at_end", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s; s.failures = 1;
        s.validation_begin();
        REQUIRE(read(d, s, {buffer, 3, 1}, true) == Result::ok);
        REQUIRE(s.failures == 1);
        s.validation_end();
        REQUIRE(s.failures == 0 && !s.session_pio);
        d.balanced();
    });
    run("semantic", "transport_fault_and_bad_pio_are_not_counted_twice", [] {
        alignas(32) unsigned char buffer[6144];
        FakeDriver d; State s; d.file = table_image(); d.plans = {{Fault::drop}, {Fault::corrupt}, {}};
        s.validation_begin();
        REQUIRE(read(d, s, {buffer, file_sector, 3}, true) == Result::ok);
        REQUIRE(!stream_table_valid(buffer, file_length, 2));
        REQUIRE(s.failures == 1 && s.validation_reject() && s.failures == 1);
        // The fallback mode is held across arbitrary reads until this window ends.
        REQUIRE(read(d, s, {buffer, 90, 1}, true) == Result::ok && !d.seen.back().dma);
        REQUIRE(!s.validation_reject() && s.failures == 1);
        s.validation_end();
        REQUIRE(!s.retry_pio && s.failures == 1);
        d.balanced();
    });
    run("semantic", "explicit_pio_semantic_failure_has_no_dma_streak", [] {
        alignas(32) unsigned char buffer[2048];
        FakeDriver d; State s;
        s.validation_begin();
        REQUIRE(read(d, s, {buffer, 7, 1}, false) == Result::ok);
        REQUIRE(s.validation_reject() && s.failures == 0);
        s.validation_end();
        d.balanced();
    });
}

void validator_cases() {
    run("validator", "valid_two_block_file", [] {
        auto bytes = table_image();
        REQUIRE(stream_table_valid(bytes.data(), file_length, 2));
    });
    for (int length = -1; length < 12; ++length) {
        run("validator", "short_length_" + std::to_string(length), [length] {
            std::vector<unsigned char> bytes(static_cast<size_t>(std::max(length, 1)), 0);
            REQUIRE(!stream_table_valid(bytes.data(), length, 2));
        });
    }
    run("validator", "null_and_zero_alignment", [] {
        auto bytes = table_image();
        REQUIRE(!stream_table_valid(nullptr, file_length, 2));
        REQUIRE(!stream_table_valid(bytes.data(), file_length, 0));
    });
    const std::vector<std::pair<size_t, uint32_t>> invalid = {
        {0, 0xfffffffcu}, {4, 0xfffffffcu}, {0, 9}, {0, file_length - 8},
        {8, 0x10001}, {12, 13}, {12, 0xfffffffcu}, {16, 137}, {16, 0xfffffffeu},
        {12, file_length - 8}, {16, file_length - 8}, {4200 + 4, file_length - 4200},
        {4200 + 8, file_length - 4200}
    };
    for (size_t i = 0; i < invalid.size(); ++i) {
        run("validator", "unsafe_header_" + std::to_string(i), [&, i] {
            auto bytes = table_image();
            word(bytes.data(), invalid[i].first, invalid[i].second);
            REQUIRE(!stream_table_valid(bytes.data(), file_length, 2));
        });
    }
    run("validator", "unaligned_host_buffer_uses_memcpy_reads", [] {
        const auto bytes = table_image();
        std::vector<unsigned char> shifted(bytes.size() + 1);
        std::copy(bytes.begin(), bytes.end(), shifted.begin() + 1);
        REQUIRE(stream_table_valid(shifted.data() + 1, file_length, 2));
    });
}
}  // namespace test

#ifndef RE4DC_TEST_PORTABLE_ONLY
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

// Only the imported API's types/constants are stubbed. Values and layouts below
// follow pinned KOS dc/syscalls.h at 804b3195ebd1a06a27cc2b3a5eacf7a2429040a3.
struct cd_read_params_t { uint32_t start_sec; size_t num_sec; void* buffer; uint32_t is_test; };
struct cd_cmd_chk_status_t { int32_t err1, err2; size_t size; int ata; };
struct cd_check_drive_status_t { int status, disc_type; };
struct cd_sec_mode_params_t { uint32_t rw; int sector_part, track_type, sector_size; };
enum { CD_CMD_PIOREAD = 16, CD_CMD_DMAREAD = 17, CD_CMD_INIT = 24,
       CD_CMD_FAILED = -1, CD_CMD_NOT_FOUND = 0, CD_CMD_PROCESSING = 1,
       CD_CMD_COMPLETED = 2, CD_CMD_STREAMING = 3, CD_CMD_BUSY = 4,
       CD_CDROM_XA = 0x20, CDROM_READ_DATA_AREA = 0x2000,
       ERR_OK = 0, ERR_NO_DISC = 1, ERR_DISC_CHG = 2, ERR_SYS = 3,
       ERR_NO_ACTIVE = 5, ERR_TIMEOUT = 6 };
#define ASIC_ACK_A 0xa05f6900u
#define ASIC_ACK_C 0xa05f6908u
#define ASIC_EVT_GD_DMA 0x000eu
#define ASIC_EVT_GD_DMA_OVERRUN 0x020du
#define ASIC_EVT_GD_DMA_ILLADDR 0x020cu
#define RE4DC_DISC_POLL_SPIN_MS 2
#define RE4DC_DISC_LAND_SPIN_MS 20
#define RE4DC_DISC_PIO_FALLBACK 1
#define RE4DC_DISC_READ_FALLBACK 2
#define RE4DC_DISC_FAIL_TEST 0
#define RE4DC_DISC_READ_VERIFY 0
#define RE4DC_DISC_READ_METER 0
#define RE4DC_FB_V1 0
#define RE4DC_DVD_READ_SAFE 0
#define RE4DC_DVD_STUCK_TEST 0

namespace native_fake {
constexpr uintptr_t physical = 0x0c100000u, cached = 0x8c100000u, uncached = 0xac100000u;
constexpr size_t mapping_size = 65536;
volatile uint32_t& reg(uintptr_t address) { return *reinterpret_cast<volatile uint32_t*>(address); }
struct Maps {
    std::vector<std::pair<void*, size_t>> maps;
    Maps() {
        const int fd = static_cast<int>(syscall(SYS_memfd_create, "re4dc-build17-fake-ram", 0));
        REQUIRE(fd >= 0);
        REQUIRE(ftruncate(fd, mapping_size) == 0);
        for (uintptr_t base : {physical, cached, uncached}) {
            void* p = mmap(reinterpret_cast<void*>(base), mapping_size, PROT_READ | PROT_WRITE,
                           MAP_SHARED | MAP_FIXED_NOREPLACE, fd, 0);
            REQUIRE(p == reinterpret_cast<void*>(base));
            maps.push_back({p, mapping_size});
        }
        close(fd);
        void* p = mmap(reinterpret_cast<void*>(0xa05f6000u), 8192, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
        REQUIRE(p == reinterpret_cast<void*>(0xa05f6000u));
        maps.push_back({p, 8192});
    }
    ~Maps() { for (const auto& mapping : maps) munmap(mapping.first, mapping.second); }
};
struct Fatal : std::runtime_error { using std::runtime_error::runtime_error; };
struct Machine {
    enum class Phase { command, engine, marker };
    struct Pause { uint64_t when; bool slept; Phase phase; };
    uint64_t clock = 0, start = 0;
    bool owned = false, lock_ok = true, aborted = false, init_active = false;
    bool abort_hangs = false, reset_stuck = false, init_fail = false, mode_fail = false;
    bool data_written = false, active = false, cache_valid = false, intervening_read = false, iso_owned = false;
    unsigned acquires = 0, releases = 0, aborts = 0, resets = 0, inits = 0, modes = 0;
    unsigned invalidations = 0, purges = 0, iso_invalidations = 0, dvd_reads = 0, sound_disabled = 0;
    unsigned pass_subticks = 0, pass_divisor = 1;
    int irq_mask = 0, handle = 0, disc_type = CD_CDROM_XA, sector_size = 2048;
    cd_sec_mode_params_t mode{};
    test::Plan plan;
    Request request{};
    bool dma = false;
    std::deque<test::Plan> plans;
    std::vector<test::Seen> seen;
    std::vector<std::string> logs;
    std::vector<Pause> pauses;
    std::vector<unsigned char> file;
    Machine() {
        reg(0xa05f7414u) = 1; reg(0xa05f7418u) = 0;
        reg(ASIC_ACK_A) = reg(ASIC_ACK_C) = 0;
        std::memset(reinterpret_cast<void*>(physical), 0, mapping_size);
    }
    void service() {
        if (!active || aborted || init_active) return;
        if (plan.fault == test::Fault::drop || plan.fault == test::Fault::streaming) return;
        if (clock - start >= (plan.idle_ms ? plan.idle_ms : plan.data_ms))
            reg(0xa05f7418u) = 0;
        if (clock - start >= plan.data_ms) {
            if ((plan.fault == test::Fault::none || plan.fault == test::Fault::corrupt) && !data_written) {
                test::fill(request, file);
                if (plan.fault == test::Fault::corrupt)
                    test::word(static_cast<unsigned char*>(request.buffer), plan.corrupt_offset, 0xfffffffcu);
                data_written = true;
            }
        }
    }
    void pause_record(bool slept) {
        const Phase phase = clock - start < plan.complete_ms || aborted || init_active ? Phase::command :
                            (reg(0xa05f7418u) & 1u) ? Phase::engine : Phase::marker;
        pauses.push_back({clock, slept, phase});
    }
    void balanced() const { REQUIRE(!owned && acquires == releases && !irq_mask); }
};
Machine* machine;
int semaphore;
}
auto& _g1_ata_sem = native_fake::semaphore;
uint64_t timer_ms_gettime64() { return native_fake::machine->clock; }
int sem_wait_timed(int*, unsigned timeout) {
    auto& m = *native_fake::machine; REQUIRE(timeout == 30000 && !m.owned && !m.irq_mask);
    ++m.acquires;
    if (!m.lock_ok) return -1;
    m.owned = true; return 0;
}
void sem_signal(int*) { auto& m = *native_fake::machine; REQUIRE(m.owned); m.owned = false; ++m.releases; }
void thd_pass() {
    auto& m = *native_fake::machine;
    REQUIRE(!m.irq_mask);
    m.pause_record(false);
    if (++m.pass_subticks >= m.pass_divisor) { m.pass_subticks = 0; ++m.clock; }
    m.service();
}
void thd_sleep(unsigned ms) {
    auto& m = *native_fake::machine;
    REQUIRE(!m.irq_mask);
    m.pause_record(true);
    m.clock += ms;
    m.service();
}
int irq_disable() { auto& m = *native_fake::machine; int old = m.irq_mask; m.irq_mask = 1; return old; }
void irq_restore(int old) { native_fake::machine->irq_mask = old; }
void dcache_inval_range(uintptr_t address, size_t bytes) {
    auto& m = *native_fake::machine;
    REQUIRE(m.owned && address >= native_fake::cached && address + bytes <= native_fake::cached + native_fake::mapping_size);
    ++m.invalidations;
}
void dcache_purge_range(uintptr_t address, size_t bytes) {
    auto& m = *native_fake::machine;
    REQUIRE(m.owned && bytes == 32 && address >= native_fake::cached && address + bytes <= native_fake::cached + native_fake::mapping_size);
    ++m.purges;
}
int syscall_gdrom_send_command(int command, void* params) {
    auto& m = *native_fake::machine;
    REQUIRE(m.owned && !(native_fake::reg(0xa05f7418u) & 1u));
    if (command == CD_CMD_INIT) {
        REQUIRE(!params && native_fake::reg(0xa05f7414u) == 0);
        m.init_active = true; ++m.inits; return ++m.handle;
    }
    REQUIRE(command == CD_CMD_DMAREAD || command == CD_CMD_PIOREAD);
    REQUIRE(m.sector_size == 2048 && native_fake::reg(0xa05f7414u) == 1);
    const auto& p = *static_cast<cd_read_params_t*>(params);
    REQUIRE(p.is_test == 0);
    m.plan = m.plans.empty() ? test::Plan{} : m.plans.front();
    if (!m.plans.empty()) m.plans.pop_front();
    m.request = {p.buffer, p.start_sec, p.num_sec};
    m.dma = command == CD_CMD_DMAREAD;
    m.seen.push_back({m.request, m.dma});
    m.start = m.clock; m.active = true; m.aborted = m.init_active = m.data_written = false;
    native_fake::reg(0xa05f7418u) = m.dma ? 1 : 0;
    return ++m.handle;
}
void syscall_gdrom_exec_server() { native_fake::machine->service(); }
int syscall_gdrom_check_command(int handle, cd_cmd_chk_status_t* status) {
    auto& m = *native_fake::machine; REQUIRE(m.owned && handle == m.handle);
    if (m.init_active) return m.init_fail ? CD_CMD_FAILED : CD_CMD_COMPLETED;
    if (m.aborted) return m.abort_hangs ? CD_CMD_PROCESSING : CD_CMD_COMPLETED;
    if (m.clock - m.start < m.plan.complete_ms) return CD_CMD_PROCESSING;
    switch (m.plan.fault) {
        case test::Fault::drop: return CD_CMD_PROCESSING;
        case test::Fault::streaming: return CD_CMD_STREAMING;
        case test::Fault::io: return CD_CMD_FAILED;
        case test::Fault::no_disc: status->err1 = 2; return CD_CMD_FAILED;
        case test::Fault::changed: status->err1 = 6; return CD_CMD_FAILED;
        case test::Fault::not_found: return CD_CMD_NOT_FOUND;
        default: return CD_CMD_COMPLETED;
    }
}
int syscall_gdrom_abort_command(int handle) {
    auto& m = *native_fake::machine;
    REQUIRE(m.owned && handle == m.handle && native_fake::reg(0xa05f7414u) == 0);
    m.aborted = true; ++m.aborts;
    if (!m.reset_stuck) native_fake::reg(0xa05f7418u) = 0;
    return 0;
}
void syscall_gdrom_reset() {
    auto& m = *native_fake::machine;
    REQUIRE(m.owned && native_fake::reg(0xa05f7414u) == 0);
    ++m.resets; m.sector_size = 2352;
    native_fake::reg(0xa05f7418u) = m.reset_stuck ? 1 : 0;
}
void syscall_gdrom_init() { REQUIRE(native_fake::machine->owned); }
int syscall_gdrom_check_drive(cd_check_drive_status_t* status) {
    REQUIRE(native_fake::machine->owned); status->disc_type = native_fake::machine->disc_type; return 0;
}
int syscall_gdrom_sector_mode(cd_sec_mode_params_t* mode) {
    auto& m = *native_fake::machine;
    REQUIRE(m.owned && m.init_active && native_fake::reg(0xa05f7414u) == 0);
    m.mode = *mode; ++m.modes;
    if (m.mode_fail) return -1;
    m.sector_size = mode->sector_size; return 0;
}
void re4dc_log(const char* format, ...) {
    char buffer[512]; va_list args; va_start(args, format); std::vsnprintf(buffer, sizeof(buffer), format, args); va_end(args);
    native_fake::machine->logs.emplace_back(buffer);
}
void re4dc_disc_note(int, const char*, ...) {}
[[noreturn]] void fatal(const char* message) { throw native_fake::Fatal(message); }
namespace v2 {
// Generated by the runner from dvd_read_safe.cpp, not a copied test marker.
#include "disc_pio_test_helpers.inc"
#include "disc_pio_native.inc"
int read(void*, uint32_t, size_t, bool) { throw std::runtime_error("legacy v2 read reached"); }
int stream_refused() { throw std::runtime_error("legacy stream path reached"); }
}
int __real_cdrom_read_sectors_ex(void*, uint32_t, size_t, bool) { throw std::runtime_error("KOS read bypass reached"); }
int __real_cdrom_stream_start(int, int, bool) { throw std::runtime_error("KOS stream start reached"); }
int __real_cdrom_stream_request(void*, size_t, bool) { throw std::runtime_error("KOS stream request reached"); }
int __real_cdrom_stream_stop(bool) { throw std::runtime_error("KOS stream stop reached"); }
int s_sector, s_cnt;
bool s_dma;
size_t s_consumed;
extern "C" int __wrap_cdrom_read_sectors_ex(void*, uint32_t, size_t, bool);
namespace iso_fake {
int iso_mutex, dcache;
struct IsoLock {
    explicit IsoLock(int* mutex) {
        auto& m = *native_fake::machine;
        REQUIRE(mutex == &iso_mutex && !m.owned && !m.iso_owned);
        m.iso_owned = true;
    }
    ~IsoLock() { native_fake::machine->iso_owned = false; }
};
#define mutex_lock_scoped(mutex) IsoLock scoped_iso_lock(mutex)
void bclear_cache(int cache) {
    auto& m = *native_fake::machine;
    REQUIRE(cache == dcache && m.iso_owned && !m.owned);
    m.cache_valid = false; ++m.iso_invalidations;
}
// The added KOS helper itself comes from the patch; the surrounding ISO cache
// and mutex are fakes, not a claim to execute the complete KOS filesystem.
#include "disc_pio_test_iso.inc"
#undef mutex_lock_scoped
}
extern "C" void re4dc_iso_retry_invalidate() {
    auto& m = *native_fake::machine;
    REQUIRE(!m.owned);  // ISO->G1 order must not be inverted by the retry hook.
    iso_fake::re4dc_iso_retry_invalidate();
    REQUIRE(!m.iso_owned);
    if (m.intervening_read)
        REQUIRE(__wrap_cdrom_read_sectors_ex(reinterpret_cast<void*>(native_fake::cached + 16384), 9, 1, true) == ERR_OK);
}
// Actual sector/stream wrappers and validation entrypoints, extracted unchanged.
#include "disc_pio_test_wrappers.inc"

using u8 = unsigned char;
using u32 = uint32_t;
struct SND_RIT { uint16_t values[8]; };
struct SndStrFile {};
struct { SndStrFile* str_file[2]{}; } SndMem;
void Snd_str_blk_init(int, void*) { ++native_fake::machine->sound_disabled; }
constexpr u32 SND_DATA_TOP = native_fake::cached;
#define ALIGN32(x) (((x) + 31u) & ~31u)
#define SND_FILE "synthetic-imported-snd.cpp"
int DvdRead(int id, void* destination, int, int, int, int, const char*, int) {
    auto& m = *native_fake::machine; REQUIRE(id == 0);
    ++m.dvd_reads;
    REQUIRE(__wrap_cdrom_read_sectors_ex(destination, test::file_sector, 2, true) == ERR_OK);
    void* tail = reinterpret_cast<void*>(native_fake::cached + 32768);
    if (!m.cache_valid) {
        REQUIRE(__wrap_cdrom_read_sectors_ex(tail, test::file_sector + 2, 1, true) == ERR_OK);
        m.cache_valid = true;
    }
    std::memcpy(static_cast<unsigned char*>(destination) + 4096, tail, test::file_length - 4096);
    return m.dvd_reads;
}
struct DvdType { int ReadCheck(int, int* length, int, int) { *length = test::file_length; return 1; } } Dvd;
int run_sound_first_read() {
    int len = 0, r = 0, i = 0, str_flag = 0;
    u32 adr = 0;
    // Actual SndInit first-file validation and retry region, extracted unchanged.
#include "disc_pio_test_snd.inc"
str_done:
    (void) adr; (void) i;
    return str_flag;
}

namespace test {
template<class F> void machine_case(const char* name, F body) {
    run("native", name, [&] {
        native_fake::Machine machine;
        native_fake::machine = &machine;
        v2::pio_state = State{};
        body(machine);
    });
}
void native_cases() {
    using namespace native_fake;
    auto* buffer = reinterpret_cast<unsigned char*>(cached);
    machine_case("adapter_dma_physical_address_marker_cache_and_ack", [buffer](Machine& m) {
        REQUIRE(__wrap_cdrom_read_sectors_ex(buffer, 7, 2, true) == ERR_OK);
        REQUIRE(m.seen.size() == 1 && m.seen[0].dma && uintptr_t(m.seen[0].request.buffer) == physical);
        REQUIRE(m.invalidations == 1 && m.purges >= 1 && m.logs.empty());
        REQUIRE(reg(ASIC_ACK_A) == (1u << 14) && reg(ASIC_ACK_C) == ((1u << 13) | (1u << 12)));
        check_data({buffer, 7, 2}); m.balanced();
    });
    machine_case("adapter_drop_completion_retries_identical_sector_geometry", [buffer](Machine& m) {
        m.plans = {{Fault::drop}, {}};
        REQUIRE(__wrap_cdrom_read_sectors_ex(buffer, 101, 3, true) == ERR_OK);
        REQUIRE(m.seen.size() == 2 && m.seen[0].dma && !m.seen[1].dma);
        REQUIRE(m.seen[0].request.sector == 101 && m.seen[1].request.sector == 101);
        REQUIRE(m.seen[0].request.count == 3 && m.seen[1].request.count == 3);
        REQUIRE(uintptr_t(m.seen[0].request.buffer) == physical && m.seen[1].request.buffer == buffer);
        REQUIRE(m.logs.size() == 1 && m.logs[0].find("DMA timeout") != std::string::npos);
        REQUIRE(m.aborts == 1 && m.clock < 7000 && v2::pio_state.failures == 1);
        check_data({buffer, 101, 3}); m.balanced();
    });
    machine_case("adapter_never_treats_streaming_as_completion", [buffer](Machine& m) {
        m.plans = {{Fault::streaming}, {}};
        REQUIRE(v2::pio_read(buffer, 1, 1, true) == ERR_OK);
        REQUIRE(m.logs.size() == 1 && m.logs[0].find("DMA timeout") != std::string::npos);
        REQUIRE(m.clock >= re4dc::disc_pio::timeout_ms(1)); m.balanced();
    });
    machine_case("adapter_not_found_still_requires_landed_data", [buffer](Machine& m) {
        m.plans = {{Fault::not_found}, {}};
        REQUIRE(v2::pio_read(buffer, 1, 1, true) == ERR_OK);
        REQUIRE(m.seen.size() == 2 && m.logs[0].find("DMA data check") != std::string::npos);
        m.balanced();
    });
    machine_case("adapter_done_status_does_not_release_live_dma", [buffer](Machine& m) {
        m.plans = {{Fault::none, 1, 150}};
        REQUIRE(v2::pio_read(buffer, 12, 1, true) == ERR_OK);
        REQUIRE(m.clock >= 150 && m.logs.empty() && reg(0xa05f7418u) == 0);
        m.balanced();
    });
    machine_case("adapter_command_and_landing_use_distinct_spin_budgets", [buffer](Machine& m) {
        // Fake clock only: 64 initial yields take four synthetic milliseconds.
        // Command done at 10, engine idle at 22, bytes present at 45. This makes
        // both the engine and marker paths outlast the command spin budget.
        m.pass_divisor = 16;
        m.plans = {{Fault::none, 10, 45, 0, 22}};
        REQUIRE(__wrap_cdrom_read_sectors_ex(buffer, 13, 1, true) == ERR_OK);
        unsigned command_sleeps = 0, engine_yields = 0, engine_sleeps = 0, marker_yields = 0, marker_sleeps = 0;
        uint64_t first_command_sleep = UINT64_MAX, first_marker_sleep = UINT64_MAX;
        for (const auto& pause : m.pauses) {
            if (pause.phase == Machine::Phase::command && pause.slept) {
                ++command_sleeps;
                first_command_sleep = std::min(first_command_sleep, pause.when);
            } else if (pause.phase == Machine::Phase::engine) {
                if (pause.slept) ++engine_sleeps; else ++engine_yields;
            } else if (pause.phase == Machine::Phase::marker) {
                if (pause.slept) {
                    ++marker_sleeps;
                    first_marker_sleep = std::min(first_marker_sleep, pause.when);
                } else ++marker_yields;
            }
        }
        REQUIRE(command_sleeps > 0 && first_command_sleep >= RE4DC_DISC_POLL_SPIN_MS);
        REQUIRE(first_command_sleep < RE4DC_DISC_LAND_SPIN_MS);
        REQUIRE(engine_yields > 64 && engine_sleeps == 0);
        REQUIRE(marker_yields > 64 && marker_sleeps > 0);
        REQUIRE(first_marker_sleep >= 22 + RE4DC_DISC_LAND_SPIN_MS);
        REQUIRE(m.logs.empty() && m.seen.size() == 1);
        check_data({buffer, 13, 1}); m.balanced();
    });
    machine_case("adapter_session_switch_logs_once_per_failure", [buffer](Machine& m) {
        m.plans = {{Fault::drop}, {}, {Fault::missing}, {}, {}};
        for (unsigned i = 0; i < 3; ++i) REQUIRE(v2::pio_read(buffer, 31 + i, 1, true) == ERR_OK);
        REQUIRE(v2::pio_state.session_pio && m.logs.size() == 2 && m.seen.size() == 5);
        REQUIRE(m.logs[0].find("same sectors") != std::string::npos && m.logs[1].find("session") != std::string::npos);
        REQUIRE(!m.seen.back().dma); m.balanced();
    });
    for (int type : {int(CD_CDROM_XA), 0x10}) {
        const std::string name = "adapter_reset_sector_mode_type_" + std::to_string(type);
        machine_case(name.c_str(), [buffer, type](Machine& m) {
            m.plans = {{Fault::drop}, {}}; m.abort_hangs = true; m.disc_type = type;
            REQUIRE(v2::pio_read(buffer, 2, 1, true) == ERR_OK);
            REQUIRE(m.resets == 1 && m.inits == 1 && m.modes == 1 && m.sector_size == 2048);
            REQUIRE(m.mode.rw == 0 && m.mode.sector_part == CDROM_READ_DATA_AREA);
            REQUIRE(m.mode.track_type == (type == CD_CDROM_XA ? 2048 : 1024));
            m.balanced();
        });
    }
    for (unsigned why = 0; why < 3; ++why) {
        const std::string name = "adapter_unsafe_retirement_is_fatal_" + std::to_string(why);
        machine_case(name.c_str(), [buffer, why](Machine& m) {
            m.plans = {{Fault::drop}}; m.abort_hangs = true;
            m.reset_stuck = why == 0; m.init_fail = why == 1; m.mode_fail = why == 2;
            bool fatal_seen = false;
            try { (void) v2::pio_read(buffer, 17, 1, true); } catch (const Fatal&) { fatal_seen = true; }
            REQUIRE(fatal_seen && v2::pio_state.poisoned && m.seen.size() == 1);
            REQUIRE(reg(0xa05f7414u) == 0);
            fatal_seen = false;
            try { (void) v2::pio_read(buffer, 18, 1, true); } catch (const Fatal&) { fatal_seen = true; }
            REQUIRE(fatal_seen && m.seen.size() == 1); m.balanced();
        });
    }
    machine_case("adapter_two_byte_aligned_buffer_uses_pio", [buffer](Machine& m) {
        REQUIRE(v2::pio_read(buffer + 2, 3, 1, true) == ERR_OK);
        REQUIRE(m.seen.size() == 1 && !m.seen[0].dma && m.invalidations == 0 && m.purges == 0);
        check_data({buffer + 2, 3, 1}); m.balanced();
    });
    machine_case("adapter_lock_timeout_is_fatal_without_submission", [buffer](Machine& m) {
        m.lock_ok = false;
        bool fatal_seen = false;
        try { (void) v2::pio_read(buffer, 8, 1, true); } catch (const Fatal&) { fatal_seen = true; }
        REQUIRE(fatal_seen && m.seen.empty() && m.releases == 0 && !m.owned);
    });
    machine_case("actual_wrappers_refuse_every_stream_entrypoint", [buffer](Machine& m) {
        REQUIRE(__wrap_cdrom_stream_start(3, 2, true) == ERR_SYS);
        REQUIRE(__wrap_cdrom_stream_request(buffer, 4096, true) == ERR_SYS);
        REQUIRE(__wrap_cdrom_stream_request(buffer, 32, false) == ERR_SYS);
        REQUIRE(__wrap_cdrom_stream_stop(true) == ERR_NO_ACTIVE);
        REQUIRE(m.seen.empty() && m.acquires == 0 && m.logs.empty());
    });
    for (bool intervening : {false, true}) {
        const std::string name = intervening ? "actual_snd_retry_survives_intervening_read" : "actual_snd_retry_discards_corrupt_cached_tail";
        machine_case(name.c_str(), [buffer, intervening](Machine& m) {
            m.file = table_image(); m.intervening_read = intervening;
            m.plans = {{}, {Fault::corrupt, 20, 20, 104}, {}, {}, {}};
            REQUIRE(run_sound_first_read() == 1);
            REQUIRE(m.dvd_reads == 2 && m.iso_invalidations == 1 && m.sound_disabled == 0);
            REQUIRE(stream_table_valid(buffer, file_length, 2));
            REQUIRE(m.seen.size() == (intervening ? 5u : 4u));
            REQUIRE(m.seen[0].dma && m.seen[1].dma);
            for (size_t i = 2; i < m.seen.size(); ++i) REQUIRE(!m.seen[i].dma);
            REQUIRE(m.seen[0].request.sector == m.seen[m.seen.size() - 2].request.sector);
            REQUIRE(m.seen[1].request.sector == m.seen.back().request.sector);
            REQUIRE(!v2::pio_state.validating && !v2::pio_state.retry_pio && v2::pio_state.failures == 1);
            unsigned switches = 0;
            for (const auto& log : m.logs) if (log.find("DMA->PIO") != std::string::npos) ++switches;
            REQUIRE(switches == 1); m.balanced();
        });
    }
    machine_case("actual_snd_failed_pio_retry_disables_streamed_sound", [](Machine& m) {
        m.file = table_image();
        m.plans = {{}, {Fault::corrupt, 20, 20, 104}, {}, {Fault::corrupt, 20, 20, 104}};
        REQUIRE(run_sound_first_read() == 0);
        REQUIRE(m.dvd_reads == 2 && m.sound_disabled == 2 && m.iso_invalidations == 1);
        REQUIRE(!v2::pio_state.validating && !v2::pio_state.retry_pio && v2::pio_state.failures == 1);
        m.balanced();
    });
    machine_case("actual_snd_valid_first_read_has_no_retry_or_switch", [](Machine& m) {
        m.file = table_image(); v2::pio_state.failures = 1;
        REQUIRE(run_sound_first_read() == 1);
        REQUIRE(m.dvd_reads == 1 && m.iso_invalidations == 0 && m.logs.empty());
        REQUIRE(v2::pio_state.failures == 0 && !v2::pio_state.validating); m.balanced();
    });
}
}  // namespace test
#endif

int main() {
    test::portable_cases();
    test::validator_cases();
#ifndef RE4DC_TEST_PORTABLE_ONLY
    try {
        native_fake::Maps mappings;
        test::native_cases();
    } catch (const std::exception& error) {
        ++test::failed;
        std::printf("CASE\tnative\tfake_address_mapping\tFAIL\t%s\n", error.what());
    }
#endif
    std::printf("TOTAL\tpassed=%u\tfailed=%u\tassertions=%u\n", test::passed, test::failed, test::assertions);
    return test::failed ? 1 : 0;
}
