// Host test of the TEX_PACK index (game/platform/include/texpack_index.inc compiled unchanged) with a mock disc
// reader: absent / read error / invalid media / retry policy. Run by tests/test_texpack_index.py.
// Architect review 2026-10-03 (P1, P2): one transient header read failure latched the pack off for the session;
// the index CRC, count bound, extents and key order were not checked.
// Review 2026-10-04: the init retries ran back to back (one lookup burst spent them all), nothing re-armed them
// before the first room, a truncated pack read as a transient error forever, and a bad lookup sector was re-read
// (and logged) on every use: retries are now spaced in UI frames (find()'s `now`).
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
using mutex_t = int;
#define MUTEX_INITIALIZER 0
static int locks = 0;
void mutex_lock(mutex_t*) { ++locks; }
void mutex_unlock(mutex_t*) { --locks; }
static char last_log[512];
static unsigned logs = 0;
void re4dc_log(const char* f, ...) {
    va_list a; va_start(a, f); std::vsnprintf(last_log, sizeof(last_log), f, a); va_end(a); ++logs;
}
struct Key { unsigned crc, fnv; bool operator==(const Key& b) const { return crc == b.crc && fnv == b.fnv; } };

static std::vector<unsigned char> disk;
static bool present = true;
static unsigned reads = 0, fail_reads = 0, fail_at = ~0U;  // fail the next fail_reads reads (at fail_at, or any)
static unsigned now = 1000;                                   // the UI frame passed to find()
namespace re4dc::texture {
enum class RangeRead { ok, absent, io_error, short_file };
RangeRead read_file_range(const char*, std::uint32_t off, void* dst, std::uint32_t n, unsigned long long* total) {
    if (!present) return RangeRead::absent;
    if (total) *total = disk.size();
    ++reads;
    if (std::uint64_t(off) + n > disk.size()) return RangeRead::short_file;   // as texture_package.cpp: size, not I/O
    if (fail_reads && (fail_at == ~0U || fail_at == off)) { --fail_reads; return RangeRead::io_error; }
    std::memcpy(dst, disk.data() + off, n);
    return RangeRead::ok;
}
}  // namespace re4dc::texture
namespace {
#if RE4DC_TEX_PAYLOAD_RETRY
#include "texpack_payload_retry.inc"
#endif
#include "texpack_index.inc"
}

static void put(unsigned at, unsigned v) { for (unsigned i = 0; i < 4; ++i) disk.at(at + i) = (unsigned char)(v >> (8 * i)); }
static unsigned get(unsigned at) { return disk[at] | disk[at + 1] << 8 | disk[at + 2] << 16 | unsigned(disk[at + 3]) << 24; }
static unsigned crc_of(unsigned at, unsigned n) {
    unsigned c = 0xffffffffU;
    for (unsigned i = 0; i < n; ++i) { c ^= disk[at + i]; for (int b = 0; b < 8; ++b) c = (c >> 1) ^ (0xedb88320U & (0U - (c & 1U))); }
    return ~c;
}
static unsigned nsec(unsigned n) { return (n * 16 + 2047) / 2048; }
// A pack of n entries: key i = {i+1, 0x100+i}, each a 100-byte package at its own 2048-byte block.
static void make(unsigned n) {
    const unsigned data = 2048 + 2048 * nsec(n);
    disk.assign(data + 2048 * n, 0);
    std::memcpy(disk.data(), "RE4PAK1", 8);
    put(8, 1); put(12, n); put(16, 2048); put(20, data);
    for (unsigned i = 0; i < n; ++i) {
        const unsigned e = 2048 + 16 * i;
        put(e, i + 1); put(e + 4, 0x100 + i); put(e + 8, data + 2048 * i); put(e + 12, 100);
    }
    put(24, crc_of(2048, 2048 * nsec(n)));
}
static void recrc() { put(24, crc_of(2048, 2048 * nsec(get(12) > 8192 ? 1 : get(12)))); }
static void reset() {
    texpack::state = texpack::kUntried; texpack::cached = ~0U;
    texpack::count = texpack::data_offset = texpack::sectors = texpack::hits = texpack::misses = texpack::errors = 0;
    texpack::attempts = texpack::streak = texpack::room_gen = texpack::attempt_gen = texpack::retry_at = 0;
    texpack::bad_sector = ~0U; texpack::bad_until = 0; texpack::pack_bytes = 0;
    std::memset(texpack::first, 0, sizeof(texpack::first));
    present = true; reads = fail_reads = 0; fail_at = ~0U; now = 1000;
}
static texpack::Result find(unsigned crc, unsigned fnv, unsigned* off = nullptr) {
    unsigned o = 0, s = 0;
    const texpack::Result r = texpack::find({crc, fnv}, o, s, now);
    if (off) *off = o;
    assert(locks == 0);
    return r;
}
#define CHECK(c) do { if (!(c)) { std::printf("FAIL line %d: %s (log: %s)\n", __LINE__, #c, last_log); return 1; } } while (0)

int main() {
    unsigned off = 0;
    // healthy pack, 300 entries (3 index sectors)
    reset(); make(300);
    CHECK(find(1, 0x100, &off) == texpack::kFound && off == get(2048 + 8));
    CHECK(find(300, 0x100 + 299, &off) == texpack::kFound && off == get(2048 + 16 * 299 + 8));
    CHECK(find(150, 0x100 + 149, &off) == texpack::kFound);
    CHECK(find(7, 0x999) == texpack::kNotInPack && find(0, 0) == texpack::kNotInPack && find(9999, 1) == texpack::kNotInPack);
    CHECK(texpack::state == texpack::kReady && texpack::count == 300 && texpack::sectors == 3);
    std::printf("HEALTHY: 300 entries, 3 sectors, hits=%u misses=%u\n", texpack::hits, texpack::misses);

    // P1: one transient header read failure; the next use retries and the pack works (was latched off for good)
    reset(); make(300); fail_reads = 1; fail_at = 0;
    CHECK(find(1, 0x100) == texpack::kError);
    CHECK(texpack::state == texpack::kRetry && !texpack::settled());
    now += texpack::kRetryFrames;
    CHECK(find(1, 0x100) == texpack::kFound && texpack::state == texpack::kReady && texpack::settled());
    CHECK(locks == 0);
    std::printf("TRANSIENT_HEADER_READ: first=error, %u frames later found, reads=%u\n", texpack::kRetryFrames, reads);

    // a transient index-sector failure during init: nothing published, then a full init
    reset(); make(300); fail_reads = 1; fail_at = 2048 * 2;
    CHECK(find(150, 0x100 + 149) == texpack::kError && texpack::state == texpack::kRetry && texpack::count == 0);
    now += texpack::kRetryFrames;
    CHECK(find(150, 0x100 + 149) == texpack::kFound);
    std::printf("TRANSIENT_INDEX_READ: error, then found\n");

    // spaced retry: a burst of lookups in one frame spends one attempt; kRetryNow attempts kRetryFrames apart,
    // then one every kRetrySlowFrames; between attempts no I/O
    reset(); make(300); fail_reads = 5;
    for (int i = 0; i < 50; ++i) CHECK(find(1 + i, 0x100 + i) == texpack::kError);   // a preload burst
    CHECK(reads == 1 && texpack::attempts == 1);
    now += texpack::kRetryFrames - 1;
    CHECK(find(1, 0x100) == texpack::kError && reads == 1);       // not yet
    now += 1;
    CHECK(find(1, 0x100) == texpack::kError && reads == 2);       // attempt 2
    now += texpack::kRetryFrames;
    CHECK(find(1, 0x100) == texpack::kError && reads == 3);       // attempt 3: now the slow cadence
    now += texpack::kRetryFrames;
    CHECK(find(1, 0x100) == texpack::kError && reads == 3);
    now += texpack::kRetrySlowFrames - texpack::kRetryFrames;
    CHECK(find(1, 0x100) == texpack::kError && reads == 4);       // attempt 4, kRetrySlowFrames after attempt 3
    texpack::room_loaded();
    CHECK(find(1, 0x100) == texpack::kError && reads == 5);       // a room load: attempt 5 at once
    CHECK(find(1, 0x100) == texpack::kError && reads == 5);
    now += texpack::kRetryFrames;                                 // ... and the fast spacing again
    CHECK(find(1, 0x100) == texpack::kFound && texpack::state == texpack::kReady);
    std::printf("SPACED_RETRY: one attempt per burst, %u frames apart, then every %u frames; a room load retries at once\n",
                texpack::kRetryFrames, texpack::kRetrySlowFrames);

    // the UI frame counter wrapping between two attempts
    reset(); make(300); fail_reads = 1; now = 0xfffffff0U;
    CHECK(find(1, 0x100) == texpack::kError);
    now += texpack::kRetryFrames - 1;                             // wrapped, one frame early
    CHECK(find(1, 0x100) == texpack::kError && reads == 1);
    now += 1;
    CHECK(find(1, 0x100) == texpack::kFound);
    std::printf("FRAME_WRAP: spacing holds across the counter wrap\n");

    // the first room after boot: nothing calls room_loaded(), yet the slow cadence still recovers the pack
    reset(); make(300); fail_reads = 3;
    for (int i = 0; i < 3; ++i) { CHECK(find(1, 0x100) == texpack::kError); now += texpack::kRetryFrames; }
    CHECK(reads == 3 && find(1, 0x100) == texpack::kError && reads == 3);
    now += texpack::kRetrySlowFrames;
    CHECK(find(1, 0x100) == texpack::kFound);
    std::printf("FIRST_ROOM: recovered without a room load\n");

    // the slow cadence logs every 16th failure, not each one: attempts 1-3, 16 and 32 of 40
    reset(); make(300); fail_reads = 40; logs = 0;
    for (int i = 0; i < 40; ++i) { CHECK(find(1, 0x100) == texpack::kError); now += texpack::kRetrySlowFrames; }
    CHECK(texpack::attempts == 40 && reads == 40 && logs == texpack::kRetryNow + 2);
    std::printf("RETRY_LOG: %u lines for 40 failed attempts\n", logs);

    // a lookup's sector read failing after init: an error for this use (the key is not missing); that sector is not
    // re-read (or logged) before kRetryFrames, other sectors still are; then found
    reset(); make(300);
    CHECK(find(1, 0x100) == texpack::kFound);
    fail_reads = 1;
    CHECK(find(150, 0x100 + 149) == texpack::kError);
    const unsigned rl = reads, ll = logs;
    for (int i = 0; i < 20; ++i) CHECK(find(150, 0x100 + 149) == texpack::kError);
    CHECK(reads == rl && logs == ll);
    CHECK(find(1, 0x100) == texpack::kFound && reads == rl + 1);   // sector 0 is fine
    now += texpack::kRetryFrames;
    CHECK(find(150, 0x100 + 149) == texpack::kFound);
    std::printf("LOOKUP_SECTOR_READ: error, no re-read for %u frames, then found\n", texpack::kRetryFrames);

    // absent: per-file path, never retried
    reset(); make(300); present = false;
    CHECK(find(1, 0x100) == texpack::kNotInPack && texpack::state == texpack::kAbsent && texpack::settled());
    present = true;
    CHECK(find(1, 0x100) == texpack::kNotInPack && reads == 0);
    std::printf("ABSENT: per-file\n");

    // a truncated pack (shorter than its 2048-byte header, or empty) is invalid media, not a transient read error
    reset(); disk.assign(100, 0x55);
    CHECK(find(1, 0x100) == texpack::kNotInPack && texpack::state == texpack::kInvalid);
    CHECK(std::strstr(last_log, "shorter than its header") && texpack::settled());
    CHECK(find(7, 0x999) == texpack::kNotInPack && reads == 1);   // per-file loads, no more pack reads
    reset(); disk.clear();
    CHECK(find(1, 0x100) == texpack::kNotInPack && texpack::state == texpack::kInvalid);
    std::printf("SHORT_FILE: 100-byte and empty packs rejected as invalid\n");

    // P2: corrupt index entry (key A pointing at B's package): the index CRC rejects the pack
    reset(); make(300); put(2048 + 8, get(2048 + 16 + 8));
    CHECK(find(1, 0x100) == texpack::kNotInPack && texpack::state == texpack::kInvalid);
    CHECK(std::strstr(last_log, "INVALID: index crc"));
    std::printf("CORRUPT_INDEX: rejected by the index CRC\n");

    // P2: count*16 wrap (0x10000000) and other header fields
    reset(); make(300); put(12, 0x10000000);
    CHECK(find(1, 0x100) == texpack::kNotInPack && texpack::state == texpack::kInvalid && std::strstr(last_log, "count"));
    reset(); make(300); put(12, 0);
    CHECK(find(1, 0x100) == texpack::kNotInPack && texpack::state == texpack::kInvalid);
    reset(); make(300); put(12, 8193);
    CHECK(find(1, 0x100) == texpack::kNotInPack && texpack::state == texpack::kInvalid);
    reset(); make(300); put(16, 4096);
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "index offset"));
    reset(); make(300); put(20, get(20) + 16);
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "data offset"));
    reset(); make(300); put(20, 2048);   // inside the index
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "data offset"));
    std::printf("HEADER_FIELDS: count 0x10000000 / 0 / 8193, index offset, data offset rejected\n");

    // key order, duplicate keys and extents (CRC recomputed so only the checked property is wrong)
    reset(); make(300); put(2048 + 16 * 5, 3); recrc();
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "key order"));
    reset(); make(300); put(2048 + 16 * 5, get(2048 + 16 * 4)); put(2048 + 16 * 5 + 4, get(2048 + 16 * 4 + 4)); recrc();
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "key order"));
    reset(); make(300); put(2048 + 16 * 128, 127); recrc();   // across a sector boundary
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "key order"));
    reset(); make(300); put(2048 + 16 * 7 + 8, get(2048 + 16 * 7 + 8) + 4); recrc();
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "entry extent"));
    reset(); make(300); put(2048 + 16 * 299 + 12, 4096); recrc();   // past the end of the file
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "entry extent"));
    reset(); make(300); put(2048 + 16 * 9 + 12, 0); recrc();
    CHECK(find(1, 0x100) == texpack::kNotInPack && std::strstr(last_log, "entry extent"));
    std::printf("INDEX_ENTRIES: order, duplicates, alignment, extents, empty rejected\n");

    // the largest pack the runtime takes: 8192 entries, 64 sectors
    reset(); make(8192);
    CHECK(find(8192, 0x100 + 8191) == texpack::kFound && texpack::sectors == 64);
    std::printf("MAX_COUNT: 8192 entries found\n");
#if RE4DC_TEX_PAYLOAD_RETRY
    unsigned ordinal=~0U,size=0;
    CHECK(texpack::find({8192,0x100+8191},off,size,now,&ordinal)==texpack::kFound&&ordinal==8191);
    texpack_payload_retry::failed(ordinal,now);CHECK(texpack_payload_retry::blocked(8191,now));
    texpack::room_loaded();CHECK(!texpack_payload_retry::blocked(8191,now));
    texpack_payload_retry::failed(0,now);CHECK(texpack_payload_retry::blocked(0,now));
    reset();make(300);CHECK(find(1,0x100)==texpack::kFound);
    CHECK(!texpack_payload_retry::blocked(0,now));
    // The validated sorted index gives every admitted member one unique ordinal.
    for(unsigned i=0;i<300;++i){ordinal=~0U;CHECK(texpack::find({i+1,0x100+i},off,size,now,&ordinal)==texpack::kFound&&ordinal==i);}
    // Same first key with a changed later member: do not publish a false ordinal.
    reset();make(300);CHECK(find(1,0x100)==texpack::kFound);
    put(2048+16*7+4,0x98765432); // no change to the first key in this sector
    texpack::cached=~0U;ordinal=~0U;
    CHECK(texpack::find({8,0x98765432},off,size,now,&ordinal)==texpack::kError&&ordinal==~0U);
    CHECK(texpack::cached==~0U);
    make(300);now+=texpack::kRetryFrames;
    CHECK(texpack::find({8,0x107},off,size,now,&ordinal)==texpack::kFound&&ordinal==7);
    std::printf("PAYLOAD_INDEX_ORDINAL_AND_RESET PASS\n");
#endif
    std::printf("TEXPACK_INDEX_HOST_TEST PASS\n");
    return 0;
}
