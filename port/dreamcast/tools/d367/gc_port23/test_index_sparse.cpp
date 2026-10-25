// gc-catalog24b: the sparse resident catalog index must give the same verdict as
// the old exact lookup for every catalog row, plus absent identities, including
// rows whose 16-byte prefixes tie across block boundaries and 64-row blocks.
// Optional argv[1]: a real gc-assets.idx (every row is checked).
#include "../../../game/platform/include/gc_asset_gate.h"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
extern "C" void re4dc_log(const char*, ...) {}
using namespace re4dc_gcasset;
namespace {
std::vector<unsigned char> blob;
unsigned reads;
unsigned read_at(void*, unsigned offset, void* out, unsigned bytes) {
    ++reads;
    if (offset > blob.size() || bytes > blob.size() - offset) return 0;
    std::memcpy(out, blob.data() + offset, bytes); return bytes;
}
struct Row { unsigned char raw[112]; };
std::vector<Row> make_rows(unsigned n, unsigned seed) {
    std::vector<Row> rows;
    for (unsigned i = 0; i < n; ++i) {
        Row r{}; seed = seed * 1103515245u + 12345u;
        const char* kind = (i % 5 == 0) ? "model" : (i % 7 == 0) ? "font-glyph" : "texture";
        char id[48];
        if (i % 3 == 0) std::snprintf(id, sizeof id, "tie%04u", i % 37);           // shared ids: digests decide
        else std::snprintf(id, sizeof id, "%08x-%08x", seed, seed ^ 0x5a5a5a5au);
        std::strcpy(reinterpret_cast<char*>(r.raw), kind);
        std::strcpy(reinterpret_cast<char*>(r.raw + 16), id);
        for (unsigned b = 0; b < 32; ++b) r.raw[64 + b] = static_cast<unsigned char>((seed >> (b % 24)) + i * 7 + b);
        r.raw[96] = i % 4;
        rows.push_back(r);
    }
    std::sort(rows.begin(), rows.end(), [](const Row& a, const Row& b) { return std::memcmp(a.raw, b.raw, 96) < 0; });
    rows.erase(std::unique(rows.begin(), rows.end(), [](const Row& a, const Row& b) { return !std::memcmp(a.raw, b.raw, 96); }), rows.end());
    return rows;
}
void make_blob(const std::vector<Row>& rows) {
    blob.assign(128, 0);
    std::memcpy(blob.data(), "GCIDX001", 8);
    const unsigned head[4] = {1, unsigned(rows.size()), 112, 128};
    std::memcpy(blob.data() + 8, head, 16);
    for (const auto& r : rows) blob.insert(blob.end(), r.raw, r.raw + 112);
}
bool use_stream;
bool stream_odd(void*, void (*sink)(void*, const unsigned char*, unsigned), void* ctx) {
    for (std::size_t at = 0; at < blob.size(); at += 1000) sink(ctx, blob.data() + at, unsigned(std::min<std::size_t>(1000, blob.size() - at)));
    return true;
}
bool install() {
    const Digest pin = fingerprint(blob.data(), unsigned(blob.size()));
    return use_stream ? install_index_stream(stream_odd, nullptr, read_at, nullptr, unsigned(blob.size()), pin)
                      : install_index(read_at, nullptr, unsigned(blob.size()), pin);
}
void check_one(const char* label);
void check_all(const char* label) {
    use_stream = false; check_one(label);
    use_stream = true; check_one(label);
}
void check_one(const char* label) {
    assert(install());
    const unsigned n = (unsigned(blob.size()) - 128) / 112;
    unsigned binds = 0; reads = 0;
    for (unsigned i = 0; i < n; ++i) {
        const unsigned char* r = blob.data() + 128 + i * 112;
        Digest d; std::memcpy(d.bytes, r + 64, 32);
        const CheckedAsset a = bind_checked(reinterpret_cast<const char*>(r), reinterpret_cast<const char*>(r + 16), d);
        assert(a.value && (a.value & 16383u) == i);   // old exact lookup: row i
        ++binds;
    }
    const unsigned per_bind = reads / binds;
    // absent identities: changed digest byte (sorts next to the row) and unknown id; 8 per install (quarantine size)
    unsigned absent = 0;
    for (unsigned i = 0; i < n; i += 97) {
        if (absent && !(absent % 8)) assert(install());
        const unsigned char* r = blob.data() + 128 + i * 112;
        Digest d; std::memcpy(d.bytes, r + 64, 32); d.bytes[31] ^= 1;
        const CheckedAsset a = bind_checked(reinterpret_cast<const char*>(r), reinterpret_cast<const char*>(r + 16), d);
        bool row_match = false;   // the mutated digest might equal another real row
        for (unsigned j = 0; j < n; ++j) if (!std::memcmp(blob.data() + 128 + j * 112, r, 64) && !std::memcmp(blob.data() + 128 + j * 112 + 64, d.bytes, 32)) row_match = true;
        assert(a.value && ((a.value & 16383u) >= n) != row_match);
        ++absent;
    }
    std::printf("%s [%s install]: rows=%u binds=%u reads/bind=%u absent=%u PASS\n", label, use_stream ? "stream" : "read", n, binds, per_bind, absent);
}
}
int main(int argc, char** argv) {
    make_blob(make_rows(7901, 1)); check_all("synthetic-7901");
    make_blob(make_rows(16320, 2)); check_all("synthetic-16320 (64-row blocks)");
    make_blob(make_rows(1, 3)); check_all("synthetic-1");
    make_blob(make_rows(33, 4)); check_all("synthetic-33");
    // tamper: same verdicts as before (pin mismatch / disorder refused)
    { auto rows = make_rows(100, 5); make_blob(rows);
      const Digest pin = fingerprint(blob.data(), unsigned(blob.size()));
      blob[128 + 5 * 112 + 70] ^= 1;
      assert(!install_index(read_at, nullptr, unsigned(blob.size()), pin));
      std::swap_ranges(blob.begin() + 128, blob.begin() + 240, blob.begin() + 240);
      assert(!install_index(read_at, nullptr, unsigned(blob.size()), fingerprint(blob.data(), unsigned(blob.size())))); }
    if (argc > 1) {
        FILE* f = std::fopen(argv[1], "rb"); assert(f);
        blob.clear(); unsigned char buf[4096]; size_t got;
        while ((got = std::fread(buf, 1, sizeof buf, f)) > 0) blob.insert(blob.end(), buf, buf + got);
        std::fclose(f); check_all(argv[1]);
    }
    std::printf("sparse index verdicts equal the exact lookup\n");
    return 0;
}
