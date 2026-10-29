#ifndef RE4DC_WATER_LAYER29_PACKAGE_H
#define RE4DC_WATER_LAYER29_PACKAGE_H

// The optional W29 member is part of the already loaded, decoded room archive.
// All offsets are little-endian, relative to this member, and checked against
// both the tagged archive's member span and the DVD-reported payload size.
// Rows use the fixed 32-bit source layouts (56/76 bytes), without pointers.
enum { WATER29_PACKAGE_MAGIC = 0x50393257U, WATER29_PACKAGE_VERSION = 1,
       WATER29_ARCHIVE_OWNER = 0x57323941U };
struct Water29PackageHeader {
    uint32_t magic, version, bytes, room, source_key, result;
    uint32_t main_count, main_offset, main_bytes;
    uint32_t ext_count, ext_offset, ext_bytes, ext_index_base, rows_crc32;
};
static_assert(sizeof(Water29PackageHeader) == 56, "W29 header size");
static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__, "W29 room payload byte order");
static_assert(sizeof(WaterPs2Row) == 56, "W29 main row size");
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
static_assert(sizeof(WaterPs2ExtRow) == 76, "W29 extension row size");
#endif

struct Water29PackageView {
    Water29Definition definition;
    // Archive bytes are only copied with memcpy. No typed row object lives in
    // the DVD buffer, even when the payload happens to be word-aligned.
    const uint8_t* main_rows;
    const uint8_t* ext_rows;
};

static inline uint32_t water29PackageWord(const uint8_t* at)
{
    uint32_t word;
    memcpy(&word, at, sizeof(word));
    return word;
}
static inline uint32_t water29PackageCrc32(const uint8_t* at, uint32_t bytes)
{
    uint32_t crc = ~uint32_t(0);
    for (uint32_t i = 0; i < bytes; ++i) {
        crc ^= at[i];
        for (unsigned bit = 0; bit < 8; ++bit) {
            crc = (crc >> 1) ^ (0xedb88320U & (0U - (crc & 1U)));
        }
    }
    return ~crc;
}

static inline Water29Result water29PackageOpen(const void* archive, uint32_t available,
                                                uint32_t room, uint32_t source_key,
                                                uint32_t incarnation, Water29PackageView* out)
{
    memset(out, 0, sizeof(*out));
    if (!archive || available < 16 || !incarnation) return WATER29_REFUSED;
    const uint8_t* base = (const uint8_t*) archive;
    const uint32_t count = water29PackageWord(base);
    if (!count || count > 256 || count > (available - 16) / 8) return WATER29_REFUSED;
    const uint32_t first = 16 + 8 * count;
    uint32_t start = 0, end = available;
    unsigned found = 0;
    for (uint32_t i = 0; i < count; ++i) {
        const uint32_t off = water29PackageWord(base + 16 + 4 * i);
        const uint8_t* tag = base + 16 + 4 * count + 4 * i;
        // Other archive entries may be absent (offset zero), but every present
        // member must have a bounded, four-byte-aligned start.
        if (off && (off < first || off >= available || (off & 31))) return WATER29_REFUSED;
        if (tag[0] == 'W' && tag[1] == '2' && tag[2] == '9' && tag[3] == 0) {
            if (++found != 1 || !off) return WATER29_REFUSED;
            start = off;
        }
    }
    if (!found) return WATER29_UNBOUND;
    for (uint32_t i = 0; i < count; ++i) {
        const uint32_t off = water29PackageWord(base + 16 + 4 * i);
        if (off == start &&
            !(base[16 + 4 * count + 4 * i] == 'W' &&
              base[17 + 4 * count + 4 * i] == '2' &&
              base[18 + 4 * count + 4 * i] == '9' &&
              base[19 + 4 * count + 4 * i] == 0)) return WATER29_REFUSED;
        if (off > start && off < end) end = off;
    }
    if (end - start < sizeof(Water29PackageHeader)) return WATER29_REFUSED;
    Water29PackageHeader h;
    memcpy(&h, base + start, sizeof(h));
    if (h.magic != WATER29_PACKAGE_MAGIC || h.version != WATER29_PACKAGE_VERSION ||
        h.room != room || h.source_key != source_key || !source_key ||
        h.bytes < sizeof(h) || h.bytes > end - start || end - start - h.bytes >= 32 ||
        h.main_count > WATER29_MAX_ROWS || h.ext_count > WATER29_MAX_ROWS ||
        h.main_count + h.ext_count > WATER29_MAX_ROWS ||
        h.main_bytes != h.main_count * sizeof(WaterPs2Row) ||
        h.main_offset != (h.main_count ? sizeof(h) : 0) ||
        h.ext_index_base > 31 || h.ext_count > 32 - h.ext_index_base ||
        (!h.ext_count && h.ext_index_base)) return WATER29_REFUSED;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    if (h.ext_bytes != h.ext_count * sizeof(WaterPs2ExtRow)) return WATER29_REFUSED;
#else
    if (h.ext_count || h.ext_bytes) return WATER29_REFUSED;
#endif
    for (uint32_t i = h.bytes; i < end - start; ++i) {
        if (base[start + i]) return WATER29_REFUSED;
    }
    if (h.ext_offset != (h.ext_count ? sizeof(h) + h.main_bytes : 0) ||
        h.bytes != sizeof(h) + h.main_bytes + h.ext_bytes ||
        water29PackageCrc32(base + start + sizeof(h), h.bytes - sizeof(h)) != h.rows_crc32 ||
        (h.result == WATER29_NO_WATER ? (h.main_count || h.ext_count) :
         h.result != WATER29_BOUND || (!h.main_count && !h.ext_count))) return WATER29_REFUSED;
    Water29Definition& d = out->definition;
    d.magic = WATER29_MAGIC;
    d.version = WATER29_VERSION;
    d.extent = sizeof(d);
    d.room = h.room;
    d.source_key = h.source_key;
    d.owner = WATER29_ARCHIVE_OWNER;
    d.incarnation = incarnation;
    d.result = h.result;
    d.main_count = h.main_count;
    d.main_bytes = h.main_bytes;
    d.ext_count = h.ext_count;
    d.ext_bytes = h.ext_bytes;
    d.ext_index_base = h.ext_index_base;
    d.main_rows = 0;
    d.ext_rows = 0;
    out->main_rows = h.main_count ? base + start + h.main_offset : 0;
    out->ext_rows = h.ext_count ? base + start + h.ext_offset : 0;
    return (Water29Result) h.result;
}

// Check each serialized row through a real typed local, then copy the fully
// qualified member into the existing Water29 store. The deferred queue uses
// that store's copied records, never a pointer into the room archive.
static inline Water29Result water29PackagePublish(Water29Store* dst,
                                                   const Water29PackageView* member,
                                                   Water29View* published_view)
{
    const Water29Definition& d = member->definition;
    for (uint32_t i = 0; i < d.main_count; ++i) {
        WaterPs2Row row;
        memcpy(&row, member->main_rows + i * sizeof(row), sizeof(row));
        if (row.room != d.room || !water29MainValid(row)) return WATER29_REFUSED;
    }
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    for (uint32_t i = 0; i < d.ext_count; ++i) {
        WaterPs2ExtRow row;
        memcpy(&row, member->ext_rows + i * sizeof(row), sizeof(row));
        if (row.room != d.room || !water29ExtValid(row)) return WATER29_REFUSED;
    }
#endif
    if (d.main_count) memcpy(dst->main_rows, member->main_rows, d.main_bytes);
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    if (d.ext_count) memcpy(dst->ext_rows, member->ext_rows, d.ext_bytes);
#endif
    Water29Definition copied = d;
    copied.main_rows = d.main_count ? dst->main_rows : 0;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    copied.ext_rows = d.ext_count ? dst->ext_rows : 0;
#endif
    const Water29SourceBytes main_source = {copied.main_rows, d.main_bytes, d.owner, d.incarnation};
    const Water29SourceBytes ext_source = {copied.ext_rows, d.ext_bytes, d.owner, d.incarnation};
    return water29Publish(dst, &copied, sizeof(copied), &main_source, &ext_source,
                          d.room, d.source_key, published_view);
}

#endif
