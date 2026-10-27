#pragma once

#include <dc/pvr.h>
#include <kos/fs.h>

#include <cstddef>
#include <cstdint>

namespace re4dc::texture {

inline constexpr char kMagic[8] = {'R', 'E', '4', 'D', 'C', 'T', 'X', '\0'};
inline constexpr std::uint32_t kVersion = 2;
inline constexpr std::uint32_t kRgb565 = 0;
inline constexpr std::uint32_t kArgb1555 = 1;
inline constexpr std::uint32_t kArgb4444 = 2;
// Game TREE_IMPOSTOR=1 only: 4bpp palettised full-codebook VQ (impostor
// atlases); its 16 ARGB1555 palette entries follow the VQ data (32 bytes).
inline constexpr std::uint32_t kPal4 = 3;
// TEX_PAL4_ALPHA=1 only: native twiddled PAL4 indices followed by 16
// little-endian ARGB4444 words. Exact colors, including partial alpha.
// TEX_PAL4_MIPMAP=1 additionally admits square PVR-order mip indices.
// The same 16 palette words remain at the payload tail; no VQ expansion.
inline constexpr std::uint32_t kPal4Argb4444 = 4;
// TEX_PAL8_ALPHA=1 only: square twiddled PAL8 indices followed by 256
// ARGB4444 words. TEX_PAL8_MIPMAP additionally admits the PVR mip chain.
// One palette owns an aligned block of sixteen PAL4 banks; exact palettes share.
inline constexpr std::uint32_t kPal8Argb4444 = 5;
#if RE4DC_TEX_PAL4_ALPHA
// Call after PVR initialization, before any palette upload. Configuration is
// immutable; repeated identical calls preserve all live package ownership.
// The native message renderer reserves banks 0..7; other builds reserve none.
bool initialize_palettes(std::uint64_t reserved_banks);
#endif
inline constexpr std::uint32_t kAlpha = 1U << 0U;
inline constexpr std::uint32_t kBinaryAlpha = 1U << 1U;
// Game CAST_MIPMAP=1 only: a full-codebook VQ payload with the PVR mip chain
// (codebook, then the index bytes of every level from 1x1 up), sampled with
// the TCW mipmap bit. Square textures only; other builds reject the flag.
// TEX_TWIDDLED_MIPMAP additionally admits square native 16-bit twiddled
// chains: six prefix bytes, then 1x1 through the unchanged base texels.
inline constexpr std::uint32_t kMipmap = 1U << 2U;
// TEX_PAL32=1 only (colour27, 2026-10-27): a kPal4Argb4444 / kPal8Argb4444 descriptor whose palette tail is 16 / 256
// little-endian ARGB8888 words (64 / 1024 bytes) instead of ARGB4444 words. Palette RAM is ARGB8888 already
// (initialize_palettes), so the PS2 CLUT colours reach the PVR unquantised. Builds without TEX_PAL32 reject the
// descriptor through its payload size.
inline constexpr std::uint32_t kPalette8888 = 1U << 3U;
// Game GANADO_ATLAS_DROP only, never on disc: set at load time on a mipmapped VQ
// descriptor whose top level was left out (Package::drop_top_level). The
// descriptor keeps its logical size (UV scales and size checks are unchanged);
// the texture itself, and so its TSP size, is half that in each direction.
inline constexpr std::uint32_t kTopDrop = 1U << 30U;
// Linear 16-bit payloads use the existing upload-time twiddler. Twiddled and
// full-codebook VQ payloads are copied unchanged and sampled in their native
// format. Indexed formats have the explicit layouts described above; PAL8 is
// opt-in and uncompressed. Partial VQ codebooks are unsupported.
inline constexpr std::uint32_t kPayloadLinear = 0;
inline constexpr std::uint32_t kPayloadTwiddled = 1;
inline constexpr std::uint32_t kPayloadVq = 2;

struct Header {
    char magic[8];
    std::uint32_t version;
    std::uint32_t header_size;
    std::uint32_t texture_stride;
    std::uint32_t texture_count;
    std::uint32_t texture_offset;
    std::uint32_t data_offset;
    std::uint32_t data_size;
    std::uint32_t payload_crc32;
    std::uint32_t source_image_count;
    std::uint32_t flags;
};

struct Texture {
    char material[64];
    std::uint32_t width;
    std::uint32_t height;
    std::uint32_t format;
    std::uint32_t data_offset;
    std::uint32_t data_size;
    std::uint32_t flags;
    std::uint32_t payload;
    std::uint32_t reserved_0;
};

// The sampling flags must match the resident representation. Every room,
// character and source UI/model header uses this shared mapping.
std::uint32_t pvr_format(const Texture& texture);

static_assert(sizeof(Header) == 48);
static_assert(sizeof(Texture) == 96);

// Small descriptor index owned by the source room archive. Its records replace
// only offline-qualified upload-only texels. No source data is decoded or copied.
class SourceIdentityTable {
public:
    bool adopt(const void* archive, std::size_t bytes);
    void clear() { data_ = nullptr; table_ = nullptr; count_ = 0; bytes_ = 0; }
    // 1: identity, 0: ordinary resident pixels, -1: external record with invalid
    // dimensions/palette context. A rejected external record must never be hashed
    // as though its original (discarded) texel range were still present.
    int lookup(const void* pixels, unsigned width, unsigned height, unsigned format,
                unsigned& crc, unsigned& fnv, const void* palette = nullptr,
                unsigned palette_format = 0xffffffffU, unsigned palette_bytes = 0) const;
    unsigned count() const { return count_; }
    // TEX_RESIDENT builds: the native key and source shape of record `index`
    // (room-entry preload by identity; defined only in those builds).
    bool record(unsigned index, unsigned& crc, unsigned& fnv, unsigned& width, unsigned& height, unsigned& format) const;
private:
    const std::uint8_t* data_ = nullptr;
    const std::uint8_t* table_ = nullptr;
    unsigned count_ = 0;
    std::size_t bytes_ = 0;
};

class Package {
public:
    Package() = default;
    Package(const Package&) = delete;
    Package& operator=(const Package&) = delete;
    ~Package();

    bool open(const char* path);
    // Retains only bounded metadata; validates the full file CRC through the
    // shared storage bounce buffer. upload() reads native payloads in chunks.
    // Linear layouts are rejected here; legacy adopt/open remain available.
    bool open_streamed(const char* path);
#if RE4DC_TEX_PACK
    // TEX_PACK (game30.mk): the same package stored at [base, base+size) of a pack file (dc/tex.pak). Opens its own
    // handle, so loads on different threads never share a file position; every read is offset by base.
    bool open_streamed_at(const char* path, std::uint32_t base, std::uint32_t size);
#endif
    bool adopt(const std::uint8_t* data, std::size_t size);
    // Uploads every descriptor's payload into texture memory. Succeeds only
    // by finishing: a package whose earlier attempt stopped part way is
    // refused rather than reported complete, because the allocations it did
    // make are indistinguishable from a whole upload by pointer alone. The
    // caller closes it and loads it again.
    bool upload();
    bool upload_complete() const { return upload_complete_; }
    // The streamed package's own open handle (FILEHND_INVALID when none). The
    // GC-ASSET gate hashes the member through it instead of opening the file
    // again; upload() seeks before every read, so the position is not shared state.
    file_t stream_file() const { return file_; }
    // Test hook: stop the next upload after this many real allocations, zero
    // for never. Bounded and per-package, so the partial-upload path is
    // exercised rather than assumed. close() clears it.
    void inject_upload_failure_after(std::uint32_t uploads) {
        inject_failure_after_ = uploads;
    }
    // After a successful upload the texels are in texture memory and nothing
    // reads them from the CPU again, so the backing store can go. This keeps
    // the header, the descriptors, the material names, the VRAM pointers and
    // the ownership flags, and copies the metadata into its own allocation so
    // the caller is free to reuse or release the bytes it adopted. It is not
    // close(), which would also free the texture memory.
    //
    // False means nothing changed and the payload is still live and valid.
    bool release_payload();
    bool payload_released() const { return payload_released_; }
    // Bytes of adopted storage that release_payload() made reusable, and the
    // metadata copy that replaced them. The difference is the real saving.
    std::size_t released_bytes() const { return released_bytes_; }
    std::size_t metadata_bytes() const { return metadata_bytes_; }
    void close();
#if defined(RE4DC_GANADO_ATLAS_DROP) && RE4DC_GANADO_ATLAS_DROP
    // GANADO_ATLAS_DROP (game30.mk): before upload(), leave out the top level of
    // a single square mipmapped VQ texture. The PVR chain is the codebook, then
    // the index bytes from 1x1 up to the base, so the half-size texture is a
    // prefix of the same payload: data_size shrinks by (w/2)*(h/2) and only the
    // prefix is read and uploaded. False (nothing changed) for any other package.
    bool drop_top_level();
#endif

    const Header& header() const { return *header_; }
    const Texture* textures() const;
    const Texture* find(const char* material) const;
    pvr_ptr_t pvr_texture(std::uint32_t index) const;
    const char* error() const { return error_; }
    std::size_t vram_bytes() const { return vram_bytes_; }
    // Descriptors that reused another descriptor's allocation instead of
    // uploading a second copy of the same payload.
    std::uint32_t shared_textures() const { return shared_textures_; }

private:
    bool range_valid(std::uint32_t offset, std::uint32_t size) const;

    bool validate();
    bool streamed_ = false;
#if RE4DC_TEX_PACK
    bool open_streamed_impl(const char* path, std::uint32_t base, std::uint32_t size);
    std::uint32_t base_ = 0;   // the package's offset in its file (TEX_PACK; 0 for a .re4tex)
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
    const char* win_path_ = nullptr;   // opened through the pack window (no handle of its own)
#endif
#endif

    file_t file_ = FILEHND_INVALID;
    const std::uint8_t* data_ = nullptr;
    std::size_t size_ = 0;
    const Header* header_ = nullptr;
    pvr_ptr_t* pvr_textures_ = nullptr;
    // One flag per descriptor: true when this descriptor allocated the
    // texture memory it points at, false when it borrowed an earlier
    // descriptor's. Only an owner may free.
    bool* owns_texture_ = nullptr;
    // The metadata copy that outlives the adopted bytes, and what the trade
    // cost. Null while the package still points at the caller's storage.
    std::uint8_t* metadata_ = nullptr;
    std::size_t metadata_bytes_ = 0;
    std::size_t released_bytes_ = 0;
    bool payload_released_ = false;
    // Set only when upload() ran to the end of the descriptor array. Distinct
    // from pvr_textures_ != nullptr, which is true from the first allocation.
    bool upload_complete_ = false;
    std::uint32_t inject_failure_after_ = 0;
    std::size_t vram_bytes_ = 0;
    std::uint32_t shared_textures_ = 0;
    const char* error_ = "not opened";
};

#if RE4DC_TEX_PACK
// TEX_PACK (native_ui.cpp texpack::): reads `bytes` at `offset` of `path` through a handle of its own, closed before
// returning, after the IO_SERIAL wait (as Package opens). A sector-aligned read into a 32-byte aligned buffer is a KOS
// CD DMA stream; on a long-lived handle the stream stays open and another thread's read then fails ("Previous DMA
// request is in progress", route pak3). Unaligned reads avoid the stream but cost ~16 ms a sector (route pak5).
// Results: absent (fs_open failed: no such file), short_file (the file ends before offset + bytes: a property of the
// file, not a transient error), io_error (seek or short read inside the file: transient, retry), ok. file_bytes, if
// given, receives the file's length (fs_total) whenever it opened.
enum class RangeRead { ok, absent, io_error, short_file };
RangeRead read_file_range(const char* path, std::uint32_t offset, void* out, std::uint32_t bytes,
                          unsigned long long* file_bytes = nullptr);
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
// TEX_PACK_WINDOW (game30.mk; lane plainread16 2026-10-16; needs DISC_READ_FALLBACK=2): a read-ahead window over the
// pack file. While it is open, Package::open_streamed_at(path, ...) and the package's upload() read the entry from the
// window; a miss refills it with ONE large read starting at the entry (sector aligned). tex.pak is laid out in each
// room's load order (tools/d367/texpak_order.py), so a room's preload reads its pictures in a few large commands
// instead of several per picture. Exact: the same bytes reach the same places. The caller owns the buffer.
//   pack_window_open   path (the pack, e.g. "/cd/dc/tex.pak"), buffer (32-byte aligned), bytes (>= 32 KiB; rounded
//                      down to whole sectors). False (and no window) on a bad buffer or when the pack does not open.
//   pack_window_fill   prefetch: read [offset rounded down to a sector, + window bytes) now, unless already held.
//                      For the door prefetch (lane doorprefetch16): fill with the room's first pack offset while the
//                      door sound plays; the preload then starts on a hit.
//   pack_window_close  closes the handle; the caller frees the buffer after it.
// One window, one thread: open, fill, the loads and close run on the thread that loads textures.
bool pack_window_open(const char* path, void* buffer, std::uint32_t bytes);
bool pack_window_fill(std::uint32_t offset);
void pack_window_close();
bool pack_window_active();
struct PackWindowStats { unsigned fills, hits, misses, kb; };
PackWindowStats pack_window_stats();
#endif
#endif

#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
// GC-ASSET gate (gc-catalog24b): sees the member bytes a streamed package
// already reads, in member order, so the gate can hash the member without a
// second read. bytes(): header / descriptors at open, payload chunks at upload.
// gap(): before each payload read and at the end of upload(), outside any
// read_chunks call; the gate may read [its cursor, upto) through file.
struct UploadObserver {
    void (*bytes)(void* context, const Package* package, std::uint32_t offset, const std::uint8_t* data, std::size_t n);
    void (*gap)(void* context, const Package* package, file_t file, std::uint32_t base, std::uint32_t upto);
    void* context;
};
extern UploadObserver upload_observer;
#endif

} // namespace re4dc::texture
