#include "room_storage.hpp"

#include <kos.h>

#include <cstring>
#if defined(__sh__)
#include <kos/mutex.h>
#else
#include <mutex>
#endif

namespace re4dc::storage {
namespace {

// Bounded so a single read never monopolises the frame. DCA3 uses 64 KiB on the
// same hardware and services audio between chunks; that pacing belongs to the
// asynchronous work, but the bound is worth keeping from the start.
constexpr std::size_t kReadChunkBytes = 64U * 1024U;
#ifndef RE4DC_STORAGE_BOUNCE_BYTES
#define RE4DC_STORAGE_BOUNCE_BYTES 65536
#endif
constexpr std::size_t kBounceBytes=RE4DC_STORAGE_BOUNCE_BYTES;
static_assert(kBounceBytes>=2048 && kBounceBytes<=kReadChunkBytes && kBounceBytes%2048==0);

// A CD sector. Requests stay a whole number of these while there is more than
// one left, so the ragged end of a file is always its own request.
constexpr std::size_t kSectorBytes = 2048U;

// Deliberately not 32-byte aligned: that is what steers KOS away from its
// streaming path. Holds at most one bounded chunk or one small package.
alignas(32) std::uint8_t g_small_file_bounce[kBounceBytes + 32U];
bool bounce_busy = false;
// Reserve before fs_open: that call may yield too. All users share this
// existing bounce buffer; a competing reader gets the explicit retry result.
#if defined(__sh__)
mutex_t reader_mutex = MUTEX_INITIALIZER;
struct ReaderGuard {
    bool acquired = mutex_trylock(&reader_mutex)==0;
    ~ReaderGuard() { if(acquired) mutex_unlock(&reader_mutex); }
};
#else
std::mutex reader_mutex;
struct ReaderGuard {
    bool acquired = reader_mutex.try_lock();
    ~ReaderGuard() { if(acquired) reader_mutex.unlock(); }
};
#endif
#if defined(RE4DC_STORAGE_BOUNCE_ALIGNED) && RE4DC_STORAGE_BOUNCE_ALIGNED
// STORAGE_BOUNCE_ALIGNED (Makefile; only with DISC_READ_FALLBACK=2, where KOS cdrom streams are refused anyway):
// 32-byte aligned, so fs_iso9660 reads each chunk's whole sectors with ONE multi-sector GD command instead of one
// command per 2048-byte sector through its sector cache (a 16 KiB chunk: 1 command, not 8). Same bytes.
std::uint8_t* small_file_buffer() { return g_small_file_bounce; }
#else
std::uint8_t* small_file_buffer() { return g_small_file_bounce + 16U; }
#endif

std::size_t align_up(std::size_t value) {
    return (value + (kArenaAlignment - 1U)) & ~(kArenaAlignment - 1U);
}

} // namespace

void Arena::init(std::uint8_t* base, std::size_t capacity) {
    base_ = base;
    capacity_ = capacity;
    used_ = 0;
    high_water_ = 0;
    resets_ = 0;
}

std::uint8_t* Arena::allocate(std::size_t bytes) {
    if(base_ == nullptr || bytes == 0) {
        return nullptr;
    }
    const std::size_t padded = align_up(bytes);
    if(padded < bytes || padded > capacity_ - used_) {
        return nullptr;
    }
    std::uint8_t* result = base_ + used_;
    used_ += padded;
    if(used_ > high_water_) {
        high_water_ = used_;
    }
    return result;
}

void Arena::reset() {
    used_ = 0;
    ++resets_;
}

void Arena::rewind(std::size_t mark) {
    if(mark <= used_) {
        used_ = mark;
    }
}

bool read_chunks(file_t file, std::size_t bytes, ChunkConsumer consume, void* context) {
    ReaderGuard guard;
    if(!guard.acquired || bounce_busy || !consume) return false;
    bounce_busy = true;
    bool ok = true;
    while(bytes && ok) {
        const std::size_t chunk = bytes < kBounceBytes ? bytes : kBounceBytes;
        std::size_t done = 0;
        while(done < chunk) {
            const ssize_t got = fs_read(file, small_file_buffer() + done, chunk - done);
            if(got <= 0 || static_cast<std::size_t>(got) > chunk-done) { ok=false; break; }
            done += static_cast<std::size_t>(got);
        }
        if(ok) ok = consume(small_file_buffer(), chunk, context);
        bytes -= chunk;
    }
    bounce_busy = false;
    return ok;
}

bool read_aligned_chunk(file_t file, void* destination, std::size_t bytes) {
    if(!destination || (reinterpret_cast<std::uintptr_t>(destination)&31U) ||
       !bytes || (bytes&31U) || bytes>kReadChunkBytes) return false;
    ReaderGuard guard;
    if(!guard.acquired || bounce_busy) return false;
    auto* out=static_cast<std::uint8_t*>(destination);
    std::size_t done=0;
    while(done<bytes) {
        const ssize_t got=fs_read(file,out+done,bytes-done);
        if(got<=0 || static_cast<std::size_t>(got)>bytes-done || (got&31)) return false;
        done+=static_cast<std::size_t>(got);
    }
    return true;
}

bool read_exact(file_t file, void* destination, std::size_t bytes) {
    auto* out = static_cast<std::uint8_t*>(destination);
    return read_chunks(file, bytes, [](const std::uint8_t* p, std::size_t n, void* ctx) {
        auto*& target = *static_cast<std::uint8_t**>(ctx);
        std::memcpy(target,p,n); target+=n; return true;
    }, &out);
}

ReadResult read_file(Arena& arena, const char* path) {
    ReadResult result{};
    ReaderGuard guard;
    if(!guard.acquired || bounce_busy) { result.error="storage reader re-entry"; return result; }
    const std::size_t mark = arena.mark();
    const std::uint32_t started = timer_us_gettime64() & 0xffffffffU;

    file_t handle = fs_open(path, O_RDONLY);
    if(handle == FILEHND_INVALID) {
        result.error = "open failed";
        return result;
    }
    const ssize_t total = fs_total(handle);
    if(total <= 0) {
        fs_close(handle);
        result.error = "empty or unsized file";
        return result;
    }
    const std::size_t size = static_cast<std::size_t>(total);
    std::uint8_t* buffer = arena.allocate(size);
    if(buffer == nullptr) {
        fs_close(handle);
        result.error = "room arena exhausted";
        return result;
    }

    // See small_file_buffer(): a package this small is read through the block
    // cache and copied, because the streaming path does not return for it.
    const bool via_bounce = size < kReadChunkBytes;
    if(via_bounce) bounce_busy = true;

    std::size_t done = 0;
    while(done < size) {
        const std::size_t remaining = size - done;
        std::size_t want =
            remaining < kReadChunkBytes ? remaining : kReadChunkBytes;
        if(want > kSectorBytes && (want % kSectorBytes) != 0) {
            want -= want % kSectorBytes;
        }
        // Keep the original <64 KiB non-streaming policy. A smaller shared
        // bounce is copied incrementally into the same final owning allocation.
        // Large-file direct reads retain the existing 64 KiB policy.
        if(via_bounce && want>kBounceBytes)want=kBounceBytes;
        const ssize_t got = fs_read(handle,via_bounce?small_file_buffer():buffer+done,want);
        if(got < 0 || static_cast<std::size_t>(got)>want) {
            if(via_bounce) bounce_busy = false;
            fs_close(handle);
            arena.rewind(mark);
            result.error = "read error";
            return result;
        }
        if(got == 0) {
            if(via_bounce) bounce_busy = false;
            // End of file before the declared length: a truncated package must
            // never reach a parser.
            fs_close(handle);
            arena.rewind(mark);
            result.error = "unexpected end of file";
            return result;
        }
        if(via_bounce)std::memcpy(buffer+done,small_file_buffer(),static_cast<std::size_t>(got));
        done += static_cast<std::size_t>(got);
    }
    fs_close(handle);
    if(via_bounce) {
        bounce_busy = false;
    }

    result.data = buffer;
    result.size = size;
    result.read_us = (timer_us_gettime64() & 0xffffffffU) - started;
    return result;
}

} // namespace re4dc::storage
