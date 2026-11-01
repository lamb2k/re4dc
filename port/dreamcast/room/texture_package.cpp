#include "texture_package.hpp"
#include "room_storage.hpp"

#include <dc/pvr/pvr_mem.h>
#include <dc/pvr/pvr_txr.h>
#include <fcntl.h>

#include <cstring>
#include <cstdlib>

// Game PVR_PIPELINE=1 lets the PVR render the previous scene while the CPU
// continues; its frame owner waits for that render before VRAM is freed or
// overwritten. Other builds (room tool, default game) compile nothing here.
#ifndef RE4DC_PVR_PIPELINE
#define RE4DC_PVR_PIPELINE 0
#endif
#if RE4DC_PVR_PIPELINE
extern "C" void re4dc_pvr_vram_fence();
#endif
// Game TREE_IMPOSTOR=1: kPal4 (palettised VQ impostor atlases).
#ifndef RE4DC_TREE_IMPOSTOR
#define RE4DC_TREE_IMPOSTOR 0
#endif

#ifndef RE4DC_TEX_PAL4_ALPHA
#define RE4DC_TEX_PAL4_ALPHA 0
#endif

#ifndef RE4DC_TEX_PAL4_MIPMAP
#define RE4DC_TEX_PAL4_MIPMAP 0
#endif
#if RE4DC_TEX_PAL4_MIPMAP && (!RE4DC_TEX_PAL4_ALPHA || !RE4DC_CAST_MIPMAP)
#error TEX_PAL4_MIPMAP requires TEX_PAL4_ALPHA and CAST_MIPMAP
#endif

#ifndef RE4DC_TEX_PAL8_ALPHA
#define RE4DC_TEX_PAL8_ALPHA 0
#endif
#ifndef RE4DC_TEX_PAL8_MIPMAP
#define RE4DC_TEX_PAL8_MIPMAP 0
#endif
#if RE4DC_TEX_PAL8_ALPHA && !RE4DC_TEX_PAL4_ALPHA
#error TEX_PAL8_ALPHA requires TEX_PAL4_ALPHA
#endif
#if RE4DC_TEX_PAL8_MIPMAP && (!RE4DC_TEX_PAL8_ALPHA || !RE4DC_CAST_MIPMAP)
#error TEX_PAL8_MIPMAP requires TEX_PAL8_ALPHA and CAST_MIPMAP
#endif

#ifndef RE4DC_TEX_TWIDDLED_MIPMAP
#define RE4DC_TEX_TWIDDLED_MIPMAP 0
#endif
#if RE4DC_TEX_TWIDDLED_MIPMAP && !RE4DC_CAST_MIPMAP
#error TEX_TWIDDLED_MIPMAP requires CAST_MIPMAP
#endif

namespace re4dc::texture {
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
UploadObserver upload_observer{};
#endif
namespace {
#if defined(RE4DC_TEX_META_EVICT) && RE4DC_TEX_META_EVICT
// TEX_META_EVICT=1 (lane vram12 D5): a streamed package takes one KOS allocation instead of three. Its texture
// pointer table and ownership flags follow the descriptor prefix in the metadata block (a one-texture package: 160 B
// of KOS heap instead of 184 B, dlmalloc's 16-byte minimum chunk per table), so the KOS heap that
// ARENA_FIT_KOS_BYTES leaves holds ~15% more resident packages. close() frees the tables only when they are not
// that tail.
constexpr unsigned kTableCopies=RE4DC_UI_VRAM?2U:1U;
std::size_t meta_tail_offset(std::size_t metadata_bytes){return (metadata_bytes+3U)&~std::size_t(3);}
std::size_t meta_tail_bytes(std::uint32_t count){return kTableCopies*count*sizeof(pvr_ptr_t)+count*sizeof(bool);}
#endif
inline void vram_fence() {
#if RE4DC_PVR_PIPELINE
    re4dc_pvr_vram_fence();
#endif
}

std::uint32_t crc_update(std::uint32_t crc, const std::uint8_t* data, std::size_t size) {
    for(std::size_t i = 0; i < size; ++i) {
        crc ^= data[i];
        for(unsigned bit = 0; bit < 8; ++bit) {
            const std::uint32_t mask = 0U - (crc & 1U);
            crc = (crc >> 1U) ^ (0xedb88320U & mask);
        }
    }
    return crc;
}
std::uint32_t crc32(const std::uint8_t* data, std::size_t size) {
    return ~crc_update(0xffffffffU,data,size);
}

// Store queues copy complete 32-byte units. Full-codebook 8x8 VQ has
// a 16-byte tail; pad only the transfer, within PVR allocator alignment.
void upload_native(const std::uint8_t* src, void* destination, std::size_t bytes) {
    const std::size_t bulk=bytes&~std::size_t(31);
    if(bulk) pvr_txr_load(src,destination,bulk);
    if(bytes!=bulk) {
        alignas(32) std::uint8_t tail[32]{};
        std::memcpy(tail,src+bulk,bytes-bulk);
        pvr_txr_load(tail,static_cast<std::uint8_t*>(destination)+bulk,32);
    }
}

#ifndef RE4DC_UI_VRAM
#define RE4DC_UI_VRAM 0
#endif
#if RE4DC_UI_VRAM
// Game UI_VRAM=1. PVR texture RAM is paged in 2 KiB units (Sega hardware
// notes): a full VQ codebook (exactly 2 KiB) is placed on a page boundary and
// a texture of at most one page never straddles two. The allocator only
// guarantees 32 bytes, so re-place such a texture inside a block padded by one
// page less 32 bytes; if that block is unavailable keep the plain one (layout,
// not correctness). pvr_textures_ then holds count sampled pointers followed
// by count allocation bases (what pvr_mem_free() must receive); the class
// layout is unchanged, so translation units built without the knob agree.
#if defined(RE4DC_VRAM_PAGES_VQ_ONLY) && RE4DC_VRAM_PAGES_VQ_ONLY
extern "C" pvr_ptr_t re4dc_vram_pages_malloc_any(std::size_t size);   // platform/vram_pages.cpp
#endif
pvr_ptr_t allocate_texture(std::size_t bytes, bool vq, pvr_ptr_t& base) {
    constexpr std::uintptr_t kPage = 2048;
#if defined(RE4DC_VRAM_PAGES_VQ_ONLY) && RE4DC_VRAM_PAGES_VQ_ONLY
    // VRAM_PAGES_VQ_ONLY: a non-VQ texture of more than a page has no page rule (`placed` below), so the page
    // allocator places it anywhere instead of on the next page (a PAL4 package's 32-byte palette tail cost 2,016 B).
    base = !vq && bytes > kPage ? re4dc_vram_pages_malloc_any(bytes) : pvr_mem_malloc(bytes);
#else
    base = pvr_mem_malloc(bytes);
#endif
    if(base == nullptr) return nullptr;
    const std::uintptr_t start = reinterpret_cast<std::uintptr_t>(base);
    const bool placed = vq ? (start & (kPage - 1U)) == 0 :
        bytes > kPage || (start & (kPage - 1U)) + bytes <= kPage;
    if(placed) return base;
    pvr_mem_free(base);
    base = pvr_mem_malloc(bytes + kPage - 32U);
    if(base == nullptr) {
        base = pvr_mem_malloc(bytes);
        return base;
    }
    return reinterpret_cast<pvr_ptr_t>(
        (reinterpret_cast<std::uintptr_t>(base) + kPage - 1U) & ~(kPage - 1U));
}
#endif
} // namespace

namespace {
unsigned word(const std::uint8_t* p) { unsigned v; std::memcpy(&v,p,4); return v; }
unsigned half(const std::uint8_t* p) { std::uint16_t v; std::memcpy(&v,p,2); return v; }
}

bool SourceIdentityTable::adopt(const void* archive, std::size_t bytes) {
    clear();
    if(!archive || bytes < 16) return false;
    auto* data = static_cast<const std::uint8_t*>(archive);
    const unsigned slots=word(data);
    if(slots > (bytes-16)/8) return false;
    const std::uint8_t* native=nullptr;
    std::size_t native_bytes=0;
    for(unsigned i=0;i<slots;++i) {
        if(std::memcmp(data+16+4*slots+4*i,"NTR",4)) continue;
        const unsigned off=word(data+16+4*i);
        if(native || off>bytes || bytes-off<32) return false;
        native=data+off;native_bytes=bytes-off;
    }
    if(!native) return true; // original qualified archive stays selectable
    if(std::memcmp(native,"R4NTBL\0",8) || word(native+8)!=1 || word(native+16)!=12 ||
       word(native+28)!=bytes || word(native+24)<=bytes) return false;
    const unsigned count=word(native+12);
    if(!count || count>(native_bytes-32)/12 || count>1024 ||
       crc32(native+32,count*12)!=word(native+20)) return false;
    for(unsigned i=0;i<count;++i) {
        const auto* entry=native+32+i*12;
        const unsigned record=word(entry),header=word(entry+4),tpl=word(entry+8);
        if(record>bytes-32 || header>bytes-36 || tpl>bytes-12 ||
           (record&31) || (header&3) || (tpl&3)) return false;
        const auto* p=data+record;const auto* h=data+header;
        const unsigned w=word(p+16),ht=word(p+20),fmt=word(p+24);
        const bool indexed=!std::memcmp(p,"R4PREF\0",8);
        if(indexed) {
            if(record>bytes-64 || (fmt!=8 && fmt!=9) || word(p+32)>2 ||
               !word(p+36) || (word(p+36)&1) || word(p+36)>(fmt==8?32U:512U) ||
               word(p+28)<64 || word(p+48) || word(p+52) || word(p+56) || word(p+60))return false;
        }
        if((!indexed && (std::memcmp(p,"R4NREF\0",8) || (fmt>6 && fmt!=14))) || !w || !ht || w>1024 || ht>1024 ||
           // minLOD 0 only: the native package is the base level. A max LOD
           // is a whole externalized chain (--compact-room-mips); the Dreamcast
           // renderer samples the base level and never reads source texels.
           h[33] || (h[34] && indexed) || h[35] ||
           w!=half(h+2) || ht!=half(h) || fmt!=word(h+4) ||
           std::uint64_t(tpl)+word(h+8)!=record) return false;
    }
    data_=data;bytes_=bytes;table_=native+32;count_=count;
    return true;
}

#ifndef RE4DC_TEX_RESIDENT
#define RE4DC_TEX_RESIDENT 0
#endif
#ifndef RE4DC_TEX_PAYLOAD_CRC
#define RE4DC_TEX_PAYLOAD_CRC 0
#endif
#if RE4DC_TEX_RESIDENT
bool SourceIdentityTable::record(unsigned index,unsigned& crc,unsigned& fnv,unsigned& width,unsigned& height,unsigned& format) const {
    if(!data_ || index>=count_) return false;
    const auto start=word(table_+12*index);
    if(std::uint64_t(start)+32>bytes_) return false;
    const auto* p=data_+start;
    crc=word(p+8);fnv=word(p+12);width=word(p+16);height=word(p+20);format=word(p+24);
    return true;
}
#endif
int SourceIdentityTable::lookup(const void* pixels,unsigned width,unsigned height,unsigned format,
                                  unsigned& crc,unsigned& fnv,const void* palette,unsigned palette_format,unsigned palette_bytes) const {
    const auto address=reinterpret_cast<std::uintptr_t>(pixels);
    const auto base=reinterpret_cast<std::uintptr_t>(data_);
    if(!data_ || address<base || address-base>=bytes_) return false;
    const auto offset=address-base;
    for(unsigned i=0;i<count_;++i) {
        const auto start=word(table_+12*i);
#if defined(RE4DC_TEX_IDENT_LEAN) && RE4DC_TEX_IDENT_LEAN
        // TEX_IDENT_LEAN (crowd.mk): the bounds first; the tag only for an entry within 64 bytes.
        if(offset<start || offset-start>=64U) continue;
        const bool indexed=!std::memcmp(data_+start,"R4PREF\0",8);
        if(!indexed && offset-start>=32U) continue;
#else
        const bool indexed=!std::memcmp(data_+start,"R4PREF\0",8);
        if(offset<start || offset-start>=(indexed?64U:32U)) continue;
#endif
        if(offset!=start) return -1;
        const auto* p=data_+offset;
        if(word(p+16)!=width || word(p+20)!=height || word(p+24)!=format) return -1;
        if(indexed) {
            if(!palette || palette_format!=word(p+32) || palette_bytes!=word(p+36))return -1;
            auto* bytes=static_cast<const std::uint8_t*>(palette);unsigned fingerprint=2166136261U;
            for(unsigned j=0;j<palette_bytes;++j)fingerprint=(fingerprint^bytes[j])*16777619U;
            if(fingerprint!=word(p+44) || crc32(bytes,palette_bytes)!=word(p+40))return -1;
        } else if(palette || palette_bytes)return -1;
        crc=word(p+8);fnv=word(p+12);return true;
    }
    return false;
}

Package::~Package() {
    close();
}

bool Package::range_valid(std::uint32_t offset, std::uint32_t size) const {
    return offset >= sizeof(Header) &&
           static_cast<std::uint64_t>(offset) + size <= size_;
}

#if RE4DC_IO_SERIAL
extern "C" void re4dc_io_serial_wait(void);   // platform/dvd.cpp (IO_SERIAL)
#define RE4DC_IO_SERIAL_WAIT() re4dc_io_serial_wait()
#else
#define RE4DC_IO_SERIAL_WAIT() ((void)0)
#endif

bool Package::open(const char* path) {
    close();
    RE4DC_IO_SERIAL_WAIT();
    file_ = fs_open(path, O_RDONLY);
    if(file_ == FILEHND_INVALID) {
        error_ = "open failed";
        return false;
    }
    const ssize_t total = fs_total(file_);
    if(total < static_cast<ssize_t>(sizeof(Header))) {
        error_ = "file is smaller than the header";
        close();
        return false;
    }
    size_ = static_cast<std::size_t>(total);
    data_ = static_cast<const std::uint8_t*>(fs_mmap(file_));
    if(data_ == nullptr) {
        error_ = "filesystem does not support mapping";
        close();
        return false;
    }
    return validate();
}

#if RE4DC_TEX_PACK
RangeRead read_file_range(const char* path, std::uint32_t offset, void* out, std::uint32_t bytes,
                          unsigned long long* file_bytes) {
    RE4DC_IO_SERIAL_WAIT();
    const file_t f=fs_open(path,O_RDONLY);
    if(f==FILEHND_INVALID) return RangeRead::absent;
    const ssize_t total=fs_total(f);
    if(file_bytes) *file_bytes=total<0?0ULL:static_cast<unsigned long long>(total);
    if(total>=0 && static_cast<unsigned long long>(offset)+bytes>static_cast<unsigned long long>(total)) {
        fs_close(f);
        return RangeRead::short_file;   // a truncated file stays truncated: not worth a retry
    }
    const bool ok=total>=0 && fs_seek(f,static_cast<off_t>(offset),SEEK_SET)==static_cast<off_t>(offset) &&
                  fs_read(f,out,bytes)==static_cast<ssize_t>(bytes);
    fs_close(f);
    return ok?RangeRead::ok:RangeRead::io_error;
}
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
// TEX_PACK_WINDOW (texture_package.hpp): one read-ahead window over the pack.
namespace {
struct PackWindow {
    file_t f=FILEHND_INVALID;
    const char* path=nullptr;
    std::uint8_t* buf=nullptr;
    std::uint32_t cap=0,off=0,len=0,total=0;
    std::uint32_t want_end=0;   // end of the package being read (set at its open)
    std::uint32_t next=0;       // where the next package starts if the pass reads the pack in order
    PackWindowStats st{};
} g_win;
// [o, o+n) of the pack into the window, one read from the sector holding o (whole sectors into an aligned buffer: one
// GD command under DISC_READ_FALLBACK=2). A full window only when the pass is reading the pack in order (this read starts
// where the previous package ended, or a prefetch); otherwise just the rest of the current package, so a picture that
// sits elsewhere in the pack (loaded first by an earlier room) does not pull in a window of unneeded neighbours.
bool win_load(std::uint32_t o_req, bool full=false) {
    const std::uint32_t o=o_req&~2047U;
    if(o>=g_win.total) return false;
    std::uint32_t n=g_win.total-o<g_win.cap?g_win.total-o:g_win.cap;
    if(!full && o_req!=g_win.next) {
        std::uint32_t need=(g_win.want_end>o_req?g_win.want_end:o_req+1)-o;
        need=(need+2047U)&~2047U;
        if(need<n) n=need;
    }
    RE4DC_IO_SERIAL_WAIT();
    g_win.len=0;
    if(fs_seek(g_win.f,static_cast<off_t>(o),SEEK_SET)!=static_cast<off_t>(o)) return false;
    std::uint32_t done=0;
    while(done<n) {
        const ssize_t got=fs_read(g_win.f,g_win.buf+done,n-done);
        if(got<=0 || static_cast<std::uint32_t>(got)>n-done) return false;
        done+=static_cast<std::uint32_t>(got);
    }
    g_win.off=o;g_win.len=n;++g_win.st.fills;g_win.st.kb+=n/1024;
    return true;
}
// Copies [o, o+n) of the pack, refilling the window as it goes.
bool win_copy(std::uint32_t o, void* dst, std::uint32_t n) {
    auto* out=static_cast<std::uint8_t*>(dst);
    bool first=true;
    while(n) {
        if(!(o>=g_win.off && o<g_win.off+g_win.len)) {
            if(first) ++g_win.st.misses;
            if(!win_load(o)) return false;
        } else if(first) ++g_win.st.hits;
        first=false;
        const std::uint32_t a=g_win.off+g_win.len-o, k=n<a?n:a;
        std::memcpy(out,g_win.buf+(o-g_win.off),k);
        out+=k;o+=k;n-=k;
    }
    return true;
}
}  // namespace
bool pack_window_open(const char* path, void* buffer, std::uint32_t bytes) {
    pack_window_close();
    if(!path || !buffer || (reinterpret_cast<std::uintptr_t>(buffer)&31U) || bytes<32U*1024U) return false;
    RE4DC_IO_SERIAL_WAIT();
    const file_t f=fs_open(path,O_RDONLY);
    if(f==FILEHND_INVALID) return false;
    const ssize_t total=fs_total(f);
    if(total<=0) { fs_close(f); return false; }
    g_win.f=f;g_win.path=path;g_win.buf=static_cast<std::uint8_t*>(buffer);g_win.cap=bytes&~2047U;
    g_win.off=g_win.len=0;g_win.want_end=g_win.next=0;g_win.total=static_cast<std::uint32_t>(total);
    return true;
}
bool pack_window_fill(std::uint32_t offset) {
    if(g_win.f==FILEHND_INVALID) return false;
    if(offset>=g_win.off && offset<g_win.off+g_win.len) return true;
    return win_load(offset,true);
}
void pack_window_close() {
    if(g_win.f!=FILEHND_INVALID) fs_close(g_win.f);
    g_win.f=FILEHND_INVALID;g_win.path=nullptr;g_win.buf=nullptr;g_win.cap=g_win.off=g_win.len=g_win.total=0;
}
bool pack_window_active() { return g_win.f!=FILEHND_INVALID; }
PackWindowStats pack_window_stats() { return g_win.st; }
#endif
bool Package::open_streamed(const char* path) { return open_streamed_impl(path,0,0); }
bool Package::open_streamed_at(const char* path, std::uint32_t base, std::uint32_t size) {
    return size ? open_streamed_impl(path,base,size) : (close(),error_="empty pack entry",false);
}
bool Package::open_streamed_impl(const char* path, std::uint32_t base, std::uint32_t size) {
    close();
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
    // A pack entry while the window is open: no handle of its own, every read goes through the window.
    if(size && g_win.f!=FILEHND_INVALID && !std::strcmp(path,g_win.path)) {
        if(std::uint64_t(base)+size>g_win.total) { error_="pack entry outside the pack"; return false; }
        base_=base;win_path_=g_win.path;g_win.want_end=base+size;
    } else
#endif
    {
    RE4DC_IO_SERIAL_WAIT();
    file_ = fs_open(path,O_RDONLY);
    if(file_ == FILEHND_INVALID) { error_="open failed"; return false; }
    base_=base;
    }
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
    if(size && file_!=FILEHND_INVALID){
#else
    if(size){
#endif
        const ssize_t whole=fs_total(file_);
        if(whole<0 || std::uint64_t(base)+size>std::uint64_t(whole) ||
           fs_seek(file_,static_cast<off_t>(base),SEEK_SET)!=static_cast<off_t>(base)) {
            error_="pack entry outside the pack";close();return false;
        }
    }
    const ssize_t total=size?static_cast<ssize_t>(size):fs_total(file_);
#else
bool Package::open_streamed(const char* path) {
    close();
    RE4DC_IO_SERIAL_WAIT();
    file_ = fs_open(path,O_RDONLY);
    if(file_ == FILEHND_INVALID) { error_="open failed"; return false; }
    const ssize_t total=fs_total(file_);
#endif
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
#define RE4DC_PKG_READ(dst,n,o) (win_path_?win_copy(base_+(o),(dst),(n)):storage::read_exact(file_,(dst),(n)))
#else
#define RE4DC_PKG_READ(dst,n,o) storage::read_exact(file_,(dst),(n))
#endif
    Header h{};
    if(total < static_cast<ssize_t>(sizeof(h)) || !RE4DC_PKG_READ(&h,sizeof(h),0)) {
        error_="streamed header read failed";close();return false;
    }
    // Bound metadata before trusting offsets/counts. Prepared native packages
    // place the descriptor table directly after the header; no texel overlap.
    const std::uint64_t prefix=std::uint64_t(h.texture_offset)+std::uint64_t(h.texture_count)*sizeof(Texture);
    if(std::memcmp(h.magic,kMagic,8) || h.version!=kVersion || h.header_size!=sizeof(h) ||
       h.texture_stride!=sizeof(Texture) || h.texture_offset!=sizeof(h) ||
       !h.texture_count || prefix>64*1024 || prefix>std::uint64_t(total) || h.data_offset<prefix) {
        error_="invalid streamed metadata layout";close();return false;
    }
    size_=static_cast<std::size_t>(total);
    metadata_bytes_=static_cast<std::size_t>(prefix);
#if defined(RE4DC_TEX_META_EVICT) && RE4DC_TEX_META_EVICT
    metadata_=static_cast<std::uint8_t*>(std::malloc(meta_tail_offset(metadata_bytes_)+meta_tail_bytes(h.texture_count)));
#else
    metadata_=static_cast<std::uint8_t*>(std::malloc(metadata_bytes_));
#endif
    if(!metadata_) { error_="streamed metadata allocation failed";close();return false; }
    std::memcpy(metadata_,&h,sizeof(h));
    if(!RE4DC_PKG_READ(metadata_+sizeof(h),metadata_bytes_-sizeof(h),sizeof(h))) {
        error_="streamed descriptor read failed";close();return false;
    }
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    // The exact bytes read from the member: header + descriptors, before any
    // in-RAM descriptor edit (GANADO_ATLAS_DROP).
    if(upload_observer.bytes)upload_observer.bytes(upload_observer.context,this,0,metadata_,metadata_bytes_);
#endif
    data_=metadata_;streamed_=true;
    if(!validate()) return false;
    for(unsigned i=0;i<header_->texture_count;++i) {
        if(textures()[i].payload==kPayloadLinear) {
            error_="streamed upload requires native texture layout";close();return false;
        }
    }
#if RE4DC_TEX_RESIDENT && !RE4DC_TEX_PAYLOAD_CRC
    // TEX_RESIDENT: no payload CRC pass on the render thread (it read the whole
    // file a second time through a bit-serial CRC: tens of ms per texture). The
    // payload CRC is verified when the disc is staged (tools/d367/stage.sh);
    // the header and every descriptor were validated above. TEX_PAYLOAD_CRC=1
    // restores the runtime check for debugging.
    error_=nullptr;return true;
#endif
    // Validate once before any VRAM allocation or publishing this package.
    std::uint32_t crc=0xffffffffU;
#if RE4DC_TEX_PACK
    if(fs_seek(file_,static_cast<off_t>(base_+sizeof(Header)),SEEK_SET)!=static_cast<off_t>(base_+sizeof(Header)) ||
#else
    if(fs_seek(file_,sizeof(Header),SEEK_SET)!=sizeof(Header) ||
#endif
       !storage::read_chunks(file_,size_-sizeof(Header),[](const std::uint8_t* p,std::size_t n,void* ctx) {
           auto& c=*static_cast<std::uint32_t*>(ctx);c=crc_update(c,p,n);return true;
       },&crc) || ~crc!=header_->payload_crc32) {
        error_="streamed payload read or CRC mismatch";close();return false;
    }
    error_=nullptr;return true;
}

// R4 5A. The same package, parsed out of memory the caller owns rather than a
// mapping into .rodata, so a room can be read into its arena and released by
// resetting it. The bytes are not copied and are not freed here: the arena owns
// them, and close() only drops this object's view of them.
bool Package::adopt(const std::uint8_t* data, std::size_t size) {
    close();
    if(data == nullptr || size < sizeof(Header)) {
        error_ = "adopted buffer is smaller than the header";
        return false;
    }
    data_ = data;
    size_ = size;
    return validate();
}

// The body of open() as it stood, unchanged, so both paths accept and
// reject exactly the same packages.
bool Package::validate() {
    header_ = reinterpret_cast<const Header*>(data_);
    if(std::memcmp(header_->magic, kMagic, sizeof(kMagic)) != 0 ||
       header_->version != kVersion || header_->header_size != sizeof(Header)) {
        error_ = "magic, version, or header size mismatch";
        close();
        return false;
    }
    const std::uint64_t descriptor_bytes =
        static_cast<std::uint64_t>(header_->texture_count) * header_->texture_stride;
    if(header_->texture_stride != sizeof(Texture) ||
       descriptor_bytes > 0xffffffffU ||
       !range_valid(header_->texture_offset,
                    static_cast<std::uint32_t>(descriptor_bytes)) ||
       !range_valid(header_->data_offset, header_->data_size)) {
        error_ = "texture package range or stride mismatch";
        close();
        return false;
    }
    if(!streamed_ && crc32(data_ + header_->header_size, size_ - header_->header_size) !=
       header_->payload_crc32) {
        error_ = "payload CRC mismatch";
        close();
        return false;
    }
    for(std::uint32_t index = 0; index < header_->texture_count; ++index) {
        const Texture& texture = textures()[index];
        const bool dimensions = texture.width >= 8 && texture.width <= 1024 &&
            texture.height >= 8 && texture.height <= 1024 &&
            (texture.width & (texture.width - 1U)) == 0 &&
            (texture.height & (texture.height - 1U)) == 0;
        // Full 256-entry VQ codebook, no mipmaps or small-codebook pointer bias.
        // Unknown layouts must not fall through as a raw 16-bit upload.
        const std::uint64_t pixels = std::uint64_t(texture.width) * texture.height;
#if RE4DC_CAST_MIPMAP
        // CAST_MIPMAP: a square full-codebook VQ payload may carry the PVR mip
        // chain (kMipmap): one index byte for 1x1, then one per 2x2 block of
        // every level up to the base. vq_indices replaces pixels / 4 below.
        const bool mip = (texture.flags & kMipmap) != 0;
        std::uint64_t vq_indices = pixels / 4U;
        if(mip) {
#if RE4DC_TEX_TWIDDLED_MIPMAP || RE4DC_TEX_PAL8_MIPMAP
            const bool native_mip =
#if RE4DC_TEX_TWIDDLED_MIPMAP
                (texture.format <= kArgb4444 && texture.payload == kPayloadTwiddled)
#else
                false
#endif
#if RE4DC_TEX_PAL4_MIPMAP
                || (texture.format == kPal4Argb4444 && texture.payload == kPayloadTwiddled)
#endif
#if RE4DC_TEX_PAL8_MIPMAP
                || (texture.format == kPal8Argb4444 && texture.payload == kPayloadTwiddled)
#endif
                ;
            if(!dimensions || texture.width != texture.height ||
               (!native_mip && (texture.payload != kPayloadVq || texture.format > kArgb4444))) {
                error_ = "unsupported square native mip layout";
#elif RE4DC_TEX_PAL4_MIPMAP
            const bool pal4_mip = texture.format == kPal4Argb4444 &&
                texture.payload == kPayloadTwiddled;
            if(!dimensions || texture.width != texture.height ||
               (!pal4_mip && (texture.payload != kPayloadVq || texture.format > kArgb4444))) {
                error_ = "unsupported square native mip layout";
#else
            if(texture.payload != kPayloadVq || texture.width != texture.height || texture.format > kArgb4444) {
                error_ = "mipmapped texture must be square 16-bit VQ";
#endif
                close();
                return false;
            }
            vq_indices = 1U;
            for(std::uint32_t s = 2U; s <= texture.width; s <<= 1U) vq_indices += std::uint64_t(s / 2U) * (s / 2U);
        }
#define RE4DC_VQ_INDICES vq_indices
#else
#define RE4DC_VQ_INDICES (pixels / 4U)
#endif
#if RE4DC_TEX_TWIDDLED_MIPMAP
        // Native 16-bit twiddled mips: three padding texels, then 1x1
        // through the original base plane. No upload-time re-twiddling.
        const std::uint64_t raw_bytes = ((texture.flags & kMipmap) &&
            texture.payload == kPayloadTwiddled && texture.format <= kArgb4444)
            ? (pixels * 4U / 3U + 3U) * 2U : pixels * 2U;
#define RE4DC_RAW_BYTES raw_bytes
#else
#define RE4DC_RAW_BYTES (pixels * 2U)
#endif
#if RE4DC_TEX_PAL4_ALPHA
#if RE4DC_TEX_PAL4_MIPMAP
        const bool pal4_alpha = texture.format == kPal4Argb4444 &&
            texture.payload == kPayloadTwiddled;
        // KOS pvrtex: ceil-chain pixels = floor(base*4/3)+3; PAL4 packs
        // two indices per byte. Three prefix nibbles precede the 1x1 texel.
        // The shared ARGB4444 palette remains the final 32 payload bytes.
        const std::uint64_t pal4_bytes = (texture.flags & kMipmap)
            ? (pixels * 4U / 3U + 3U) / 2U + 32U : pixels / 2U + 32U;
#else
        const bool pal4_alpha = texture.format == kPal4Argb4444 &&
            texture.payload == kPayloadTwiddled && !(texture.flags & kMipmap);
#endif
        const bool pal4_vq = RE4DC_TREE_IMPOSTOR && texture.format == kPal4 &&
            texture.payload == kPayloadVq && !(texture.flags & kMipmap);
#if RE4DC_TEX_PAL8_ALPHA
        const bool pal8_alpha = texture.format == kPal8Argb4444 &&
            texture.payload == kPayloadTwiddled && texture.width == texture.height &&
            !(texture.flags & kTopDrop) &&
            (!(texture.flags & kMipmap) || RE4DC_TEX_PAL8_MIPMAP);
        const std::uint64_t pal8_bytes = ((texture.flags & kMipmap)
            ? pixels * 4U / 3U + 3U : pixels) + 512U;
#endif
#if RE4DC_TEX_PAL4_MIPMAP
        const std::uint64_t expected =
#if RE4DC_TEX_PAL8_ALPHA
            pal8_alpha ? pal8_bytes :
#endif
            pal4_alpha ? pal4_bytes :
#else
        const std::uint64_t expected =
#if RE4DC_TEX_PAL8_ALPHA
            pal8_alpha ? pal8_bytes :
#endif
            pal4_alpha ? pixels / 2U + 32U :
#endif
            pal4_vq ? 2048U + pixels / 16U + 32U :
            texture.payload == kPayloadVq ? 2048U + RE4DC_VQ_INDICES : RE4DC_RAW_BYTES;
#if RE4DC_TEX_PAL32
        // TEX_PAL32: an ARGB8888 palette tail doubles the palette bytes (16 -> 32 / 256 -> 512 extra).
        const std::uint64_t pal32_extra = (texture.flags & kPalette8888) && (pal4_alpha || pal8_alpha)
            ? (pal8_alpha ? 512U : 32U) : 0U;
#define RE4DC_PAL32_EXTRA + pal32_extra
#else
#define RE4DC_PAL32_EXTRA
#endif
        if(!dimensions || texture.payload > kPayloadVq || texture.reserved_0 != 0 ||
           texture.data_size != expected RE4DC_PAL32_EXTRA ||
            (texture.format > kArgb4444 && !pal4_alpha && !pal4_vq
#if RE4DC_TEX_PAL8_ALPHA
             && !pal8_alpha
#endif
            ) ||
#elif RE4DC_TREE_IMPOSTOR
        // kPal4: 256 8-byte codebook entries of 4x4 texels, one index byte
        // per 4x4 block, then the 16-entry palette.
        const bool pal4 = texture.format == kPal4 && texture.payload == kPayloadVq;
        const std::uint64_t expected = pal4 ? 2048U + pixels / 16U + 32U :
            texture.payload == kPayloadVq ? 2048U + RE4DC_VQ_INDICES : RE4DC_RAW_BYTES;
        if(!dimensions || texture.payload > kPayloadVq || texture.reserved_0 != 0 ||
           texture.data_size != expected || (texture.format > kArgb4444 && !pal4) ||
#else
        const std::uint64_t expected = texture.payload == kPayloadVq
            ? 2048U + RE4DC_VQ_INDICES : RE4DC_RAW_BYTES;
        if(!dimensions || texture.payload > kPayloadVq || texture.reserved_0 != 0 ||
           texture.data_size != expected || texture.format > kArgb4444 ||
#endif
           texture.data_offset < header_->data_offset ||
           std::uint64_t(texture.data_offset) + texture.data_size >
               std::uint64_t(header_->data_offset) + header_->data_size ||
           !range_valid(texture.data_offset, texture.data_size)) {
            error_ = "invalid texture dimensions, format, layout or payload size";
            close();
            return false;
        }
#undef RE4DC_VQ_INDICES
#undef RE4DC_RAW_BYTES
#undef RE4DC_PAL32_EXTRA
    }
    error_ = nullptr;
    return true;
}

#if RE4DC_TEX_PAL4_ALPHA
namespace {
bool palettes_initialized;
std::uint64_t palette_reserved, palette_banks;
// Test 12 (fx lane, tools/d367/test12fx/fx_pal4_pack.py): a bank is shared by every uploaded PAL4 texture whose 16
// palette words are identical (an effect flipbook's frames carry their group's palette), counted per bank; the bank
// is freed with its last texture. Banks outside palette_reserved only.
std::uint8_t palette_refs[64];
#if RE4DC_TEX_PAL32
// TEX_PAL32: room for an ARGB8888 palette as pairs of 16-bit words (low half first).
constexpr unsigned kPalWordScale = 2U;
#else
constexpr unsigned kPalWordScale = 1U;
#endif
std::uint16_t palette_words[64][16 * kPalWordScale];
#if RE4DC_TEX_PAL8_ALPHA
std::uint32_t palette8_refs[4];
std::uint16_t palette8_words[4][256 * kPalWordScale];
std::uint8_t palette4_formats[64];
#if RE4DC_TEX_PAL32
std::uint8_t palette8_kinds[4];   // 1: ARGB8888 tail (TEX_PAL32); never shared with a 4444 palette
#endif
#endif
bool uses_palette(const Texture& texture) {
    return texture.format == kPal4Argb4444 ||
#if RE4DC_TEX_PAL8_ALPHA
        texture.format == kPal8Argb4444 ||
#endif
        (RE4DC_TREE_IMPOSTOR && texture.format == kPal4);
}
// Check the whole transaction before allocating VRAM or writing palette RAM.
// Aliased descriptors deliberately own separate banks, as in the legacy path.
bool palettes_available(const Package& package) {
    unsigned needed = 0, available = 0;
    for(std::uint32_t i = 0; i < package.header().texture_count; ++i)
        if(uses_palette(package.textures()[i])) ++needed;
    if(!needed) return true;
    if(!palettes_initialized) return false;
#if RE4DC_TEX_PAL8_ALPHA
    // Streamed metadata does not retain palette tails. Check the exact whole
    // transaction after the normal payload upload, before any palette write or
    // ownership change; this avoids an extra disc read solely for preflight.
    // A refused upload still owns its VRAM until close(), as other failures do.
    (void)available;
    return true;
#else
    for(unsigned bank = 0; bank < 64U; ++bank)
        if(!(palette_banks & (std::uint64_t(1) << bank))) ++available;
    return needed <= available;
#endif
}
std::uint32_t palette_argb8888(std::uint16_t value, bool alpha4) {
    if(alpha4) return ((value >> 12U) * 17U << 24U) |
        (((value >> 8U) & 15U) * 17U << 16U) |
        (((value >> 4U) & 15U) * 17U << 8U) | ((value & 15U) * 17U);
    const unsigned r = (value >> 10U) & 31U;
    const unsigned g = (value >> 5U) & 31U, b = value & 31U;
    return (value & 0x8000U ? 0xff000000U : 0U) |
        (((r << 3U) | (r >> 2U)) << 16U) |
        (((g << 3U) | (g >> 2U)) << 8U) | (b << 3U) | (b >> 2U);
}
#if RE4DC_TEX_PAL8_ALPHA
// A bounded stack plan points either at immutable live palette words or at
// already-uploaded, fenced VRAM. No extra IO or per-texture allocation. Plan the
// complete transaction first; exhaustion cannot overwrite a live palette bank.
struct PalettePlan {
    std::uint64_t occupied;
    std::uint8_t refs4[64], formats4[64];
    std::uint32_t refs8[4];
    const volatile std::uint16_t* words4[64];
    const volatile std::uint16_t* words8[4];
#if RE4DC_TEX_PAL32
    std::uint8_t kinds8[4];
#endif
};
std::uint64_t palette8_mask(unsigned block) {
    return std::uint64_t(0xffffU) << (block * 16U);
}
bool equal_palette(const volatile std::uint16_t* a,
                   const volatile std::uint16_t* b, unsigned count) {
    for(unsigned k = 0; k < count; ++k) if(a[k] != b[k]) return false;
    return true;
}
bool plan_palettes(Package& package, bool commit) {
    PalettePlan plan{};
    plan.occupied = palette_banks;
    std::memcpy(plan.refs4, palette_refs, sizeof(plan.refs4));
    std::memcpy(plan.formats4, palette4_formats, sizeof(plan.formats4));
    std::memcpy(plan.refs8, palette8_refs, sizeof(plan.refs8));
    for(unsigned b = 0; b < 64U; ++b) plan.words4[b] = palette_words[b];
    for(unsigned b = 0; b < 4U; ++b) plan.words8[b] = palette8_words[b];
#if RE4DC_TEX_PAL32
    std::memcpy(plan.kinds8, palette8_kinds, sizeof(plan.kinds8));
#endif
    for(std::uint32_t i = 0; i < package.header().texture_count; ++i) {
        auto& texture = const_cast<Texture&>(package.textures()[i]);
        if(!uses_palette(texture)) continue;
        const bool pal8 = texture.format == kPal8Argb4444;
        const unsigned count = pal8 ? 256U : 16U;
#if RE4DC_TEX_PAL32
        const bool p32 = (texture.flags & kPalette8888) != 0U;   // ARGB8888 tail: count pairs of 16-bit words
        const unsigned count16 = p32 ? count * 2U : count;
#define RE4DC_PAL_WORDS count16
#else
#define RE4DC_PAL_WORDS count
#endif
        const auto* words = reinterpret_cast<const volatile std::uint16_t*>(
            static_cast<const std::uint8_t*>(package.pvr_texture(i)) +
            texture.data_size - RE4DC_PAL_WORDS * 2U);
        unsigned bank = 64U;
        bool fresh = false;
        if(pal8) {
            unsigned block = 4U;
            for(unsigned b = 0; b < 4U; ++b)
                if(plan.refs8[b] && plan.refs8[b] != 0xffffffffU &&
#if RE4DC_TEX_PAL32
                   plan.kinds8[b] == std::uint8_t(p32) &&
#endif
#if RE4DC_TEX_PAL32
                   equal_palette(plan.words8[b], words, count16)) { block = b; break; }
#else
                   equal_palette(plan.words8[b], words, 256U)) { block = b; break; }
#endif
            if(block == 4U) {
                for(unsigned b = 0; b < 4U; ++b)
                    if(!(plan.occupied & palette8_mask(b))) { block = b; break; }
                if(block == 4U) return false;
                plan.occupied |= palette8_mask(block);
                plan.words8[block] = words;
#if RE4DC_TEX_PAL32
                plan.kinds8[block] = std::uint8_t(p32);
#endif
                fresh = true;
            }
            ++plan.refs8[block];
            bank = block * 16U;
            if(commit && fresh)
#if RE4DC_TEX_PAL32
                for(unsigned k = 0; k < count16; ++k) palette8_words[block][k] = words[k];
#else
                for(unsigned k = 0; k < 256U; ++k) palette8_words[block][k] = words[k];
#endif
        } else {
            // Legacy ARGB1555 impostors retain separate banks. ARGB4444 shares
            // only with the same palette interpretation, never a PAL8 sub-bank.
            if(texture.format == kPal4Argb4444)
                for(unsigned b = 0; b < 64U; ++b)
                    if(plan.refs4[b] && plan.refs4[b] < 255U &&
#if RE4DC_TEX_PAL32
                       plan.formats4[b] == (texture.format | (p32 ? 0x80U : 0U)) &&
                       equal_palette(plan.words4[b], words, count16)) { bank = b; break; }
#else
                       plan.formats4[b] == texture.format &&
                       equal_palette(plan.words4[b], words, 16U)) { bank = b; break; }
#endif
            if(bank == 64U) {
                for(unsigned b = 0; b < 64U; ++b)
                    if(!(plan.occupied & (std::uint64_t(1) << b))) { bank = b; break; }
                if(bank == 64U) return false;
                plan.occupied |= std::uint64_t(1) << bank;
                plan.words4[bank] = words;
#if RE4DC_TEX_PAL32
                plan.formats4[bank] = static_cast<std::uint8_t>(texture.format | (p32 ? 0x80U : 0U));
#else
                plan.formats4[bank] = static_cast<std::uint8_t>(texture.format);
#endif
                fresh = true;
            }
            ++plan.refs4[bank];
            if(commit && fresh)
#if RE4DC_TEX_PAL32
                for(unsigned k = 0; k < count16; ++k) palette_words[bank][k] = words[k];
#else
                for(unsigned k = 0; k < 16U; ++k) palette_words[bank][k] = words[k];
#endif
        }
        if(commit) {
            texture.reserved_0 = bank + 1U;
            if(fresh)
                for(unsigned k = 0; k < count; ++k)
#if RE4DC_TEX_PAL32
                    pvr_set_pal_entry(bank * 16U + k, p32
                        ? std::uint32_t(words[2U * k]) | std::uint32_t(words[2U * k + 1U]) << 16U
                        : palette_argb8888(words[k], texture.format != kPal4));
#else
                    pvr_set_pal_entry(bank * 16U + k,
                        palette_argb8888(words[k], texture.format != kPal4));
#endif
        }
    }
#undef RE4DC_PAL_WORDS
    if(commit) {
        palette_banks = plan.occupied;
        std::memcpy(palette_refs, plan.refs4, sizeof(palette_refs));
        std::memcpy(palette4_formats, plan.formats4, sizeof(palette4_formats));
        std::memcpy(palette8_refs, plan.refs8, sizeof(palette8_refs));
#if RE4DC_TEX_PAL32
        std::memcpy(palette8_kinds, plan.kinds8, sizeof(palette8_kinds));
#endif
    }
    return true;
}
bool bind_palettes(Package& package) {
    return plan_palettes(package, false) && plan_palettes(package, true);
}
void release_palettes(const Package& package) {
    for(std::uint32_t i = 0; i < package.header().texture_count; ++i) {
        auto& texture = const_cast<Texture&>(package.textures()[i]);
        if(!uses_palette(texture) || !texture.reserved_0) continue;
        const unsigned bank = texture.reserved_0 - 1U;
        if(texture.format == kPal8Argb4444) {
            const unsigned block = bank / 16U;
            if(--palette8_refs[block] == 0U) palette_banks &= ~palette8_mask(block);
        } else if(--palette_refs[bank] == 0U) {
            palette_banks &= ~(std::uint64_t(1) << bank);
            palette4_formats[bank] = 0;
        }
        texture.reserved_0 = 0;
    }
}
#else
bool bind_palettes(Package& package) {
    // upload() fenced before any writes; repeat capacity validation before
    // committing so exhaustion never leaves a partial bank reservation.
    if(!palettes_available(package)) return false;
    for(std::uint32_t i = 0; i < package.header().texture_count; ++i) {
        auto& texture = const_cast<Texture&>(package.textures()[i]);
        if(!uses_palette(texture)) continue;
        const auto* entries = reinterpret_cast<const volatile std::uint16_t*>(
            static_cast<const std::uint8_t*>(package.pvr_texture(i)) + texture.data_size - 32U);
        std::uint16_t words[16];
        for(unsigned k = 0; k < 16U; ++k) words[k] = entries[k];
        unsigned bank = 64U;
        for(unsigned b = 0; b < 64U && texture.format == kPal4Argb4444; ++b)
            if(palette_refs[b] && palette_refs[b] < 255U && !std::memcmp(palette_words[b], words, sizeof(words))) {
                bank = b;
                break;
            }
        if(bank < 64U) {   // shared: the bank already holds these 16 words
            ++palette_refs[bank];
            texture.reserved_0 = bank + 1U;
            continue;
        }
        bank = 0;
        while(palette_banks & (std::uint64_t(1) << bank)) ++bank;
        palette_banks |= std::uint64_t(1) << bank;
        palette_refs[bank] = 1;
        std::memcpy(palette_words[bank], words, sizeof(words));
        texture.reserved_0 = bank + 1U;
        for(unsigned k = 0; k < 16U; ++k)
            pvr_set_pal_entry(bank * 16U + k,
                palette_argb8888(words[k], texture.format == kPal4Argb4444));
    }
    return true;
}
void release_palettes(const Package& package) {
    for(std::uint32_t i = 0; i < package.header().texture_count; ++i) {
        auto& texture = const_cast<Texture&>(package.textures()[i]);
        if(!uses_palette(texture) || !texture.reserved_0) continue;
        const unsigned bank = texture.reserved_0 - 1U;
        if(palette_refs[bank] > 1U) {
            --palette_refs[bank];
        } else {
            palette_refs[bank] = 0;
            palette_banks &= ~(std::uint64_t(1) << bank);
        }
        texture.reserved_0 = 0;
    }
}
#endif
} // namespace
bool initialize_palettes(std::uint64_t reserved_banks) {
    if(palettes_initialized) return reserved_banks == palette_reserved;
    palette_reserved = palette_banks = reserved_banks;
    pvr_set_pal_format(PVR_PAL_ARGB8888);
    palettes_initialized = true;
    return true;
}
#elif RE4DC_TREE_IMPOSTOR
namespace {
// Game TREE_IMPOSTOR=1: each uploaded kPal4 texture owns one of the 64
// 16-entry banks of PVR palette RAM (ARGB1555, the only palette user), and
// Texture::reserved_0 holds bank + 1 while it does (0 in the file). The
// upload copied the palette into VRAM behind the VQ data; it is read from
// there, so the upload path itself is unchanged.
std::uint64_t palette_banks;
bool bind_palettes(Package& package) {
    for(std::uint32_t index = 0; index < package.header().texture_count; ++index) {
        auto& texture = const_cast<Texture&>(package.textures()[index]);
        if(texture.format != kPal4 || texture.reserved_0 != 0) continue;
        unsigned bank = 0;
        while(bank < 64U && ((palette_banks >> bank) & 1U)) ++bank;
        if(bank == 64U) return false;
        palette_banks |= std::uint64_t(1) << bank;
        texture.reserved_0 = bank + 1U;
        const auto* entries = reinterpret_cast<const volatile std::uint16_t*>(
            static_cast<const std::uint8_t*>(package.pvr_texture(index)) + texture.data_size - 32U);
        pvr_set_pal_format(PVR_PAL_ARGB1555);
        for(unsigned k = 0; k < 16U; ++k) pvr_set_pal_entry(bank * 16U + k, entries[k]);
    }
    return true;
}
void release_palettes(const Package& package) {
    for(std::uint32_t index = 0; index < package.header().texture_count; ++index) {
        auto& texture = const_cast<Texture&>(package.textures()[index]);
        if(texture.format != kPal4 || texture.reserved_0 == 0) continue;
        palette_banks &= ~(std::uint64_t(1) << (texture.reserved_0 - 1U));
        texture.reserved_0 = 0;
    }
}
} // namespace
#endif

std::uint32_t pvr_format(const Texture& texture) {
#if RE4DC_TEX_PAL8_ALPHA
    if(texture.format == kPal8Argb4444)
        return PVR_TXRFMT_PAL8BPP | PVR_TXRFMT_8BPP_PAL((texture.reserved_0 - 1U) / 16U) |
            PVR_TXRFMT_TWIDDLED
#if RE4DC_TEX_PAL8_MIPMAP
            | ((texture.flags & kMipmap) ? 0x80000000U : 0U)
#endif
            ;
#endif
#if RE4DC_TEX_PAL4_ALPHA
    if(texture.format == kPal4Argb4444)
        return PVR_TXRFMT_PAL4BPP | PVR_TXRFMT_4BPP_PAL(texture.reserved_0 - 1U) | PVR_TXRFMT_TWIDDLED
#if RE4DC_TEX_PAL4_MIPMAP
            | ((texture.flags & kMipmap) ? 0x80000000U : 0U)
#endif
            ;
#endif
#if RE4DC_TREE_IMPOSTOR
    if(texture.format == kPal4) // reserved_0: palette bank + 1 (bind_palettes)
        return PVR_TXRFMT_PAL4BPP | PVR_TXRFMT_4BPP_PAL(texture.reserved_0 - 1U) | PVR_TXRFMT_VQ_ENABLE;
#endif
    const std::uint32_t formats[] = {
        PVR_TXRFMT_RGB565, PVR_TXRFMT_ARGB1555, PVR_TXRFMT_ARGB4444
    };
    return formats[texture.format] |
        (texture.payload == kPayloadVq ? PVR_TXRFMT_VQ_ENABLE : 0U)
#if RE4DC_CAST_MIPMAP
        // TCW bit 31 (mip mapped); pvr_poly_compile ORs the format word into
        // mode3, and pvr_poly_cxt_txr already sets the D adjust to 1.0.
        | ((texture.flags & kMipmap) ? 0x80000000U : 0U)
#endif
        ;
}

bool Package::upload() {
    if(header_ == nullptr) {
        error_ = "package is not open";
        return false;
    }
    if(upload_complete_) {
        return true;
    }
    if(pvr_textures_ != nullptr) {
        // A previous attempt allocated but did not finish. Retrying in place
        // would have to know which descriptors already moved their texels,
        // which nothing records, so the only honest answer is to refuse.
        error_ = "previous upload did not complete; close and load again";
        return false;
    }
#if RE4DC_TEX_PAL4_ALPHA
    if(!palettes_available(*this)) {
        error_ = "PVR palette manager uninitialized or banks exhausted";
        return false;
    }
#endif
    vram_fence();
#if defined(RE4DC_TEX_META_EVICT) && RE4DC_TEX_META_EVICT
    if(streamed_ && metadata_ != nullptr) {   // the tables in the metadata block's tail (open_streamed_impl)
        pvr_textures_ = reinterpret_cast<pvr_ptr_t*>(metadata_ + meta_tail_offset(metadata_bytes_));
        owns_texture_ = reinterpret_cast<bool*>(pvr_textures_ + kTableCopies * header_->texture_count);
        std::memset(pvr_textures_, 0, meta_tail_bytes(header_->texture_count));
    } else {
        pvr_textures_ = static_cast<pvr_ptr_t*>(std::calloc(kTableCopies * header_->texture_count, sizeof(pvr_ptr_t)));
        if(pvr_textures_ == nullptr) {
            error_ = "texture pointer allocation failed";
            return false;
        }
        owns_texture_ = static_cast<bool*>(std::calloc(header_->texture_count, sizeof(bool)));
        if(owns_texture_ == nullptr) {
            error_ = "texture ownership allocation failed";
            return false;
        }
    }
#elif RE4DC_UI_VRAM
    pvr_textures_ = static_cast<pvr_ptr_t*>(std::calloc(2U * header_->texture_count, sizeof(pvr_ptr_t)));
#else
    pvr_textures_ = static_cast<pvr_ptr_t*>(std::calloc(header_->texture_count, sizeof(pvr_ptr_t)));
#endif
#if !(defined(RE4DC_TEX_META_EVICT) && RE4DC_TEX_META_EVICT)
    if(pvr_textures_ == nullptr) {
        error_ = "texture pointer allocation failed";
        return false;
    }
    owns_texture_ = static_cast<bool*>(std::calloc(header_->texture_count, sizeof(bool)));
    if(owns_texture_ == nullptr) {
        error_ = "texture ownership allocation failed";
        return false;
    }
#endif
    std::uint32_t uploaded = 0;
    for(std::uint32_t index = 0; index < header_->texture_count; ++index) {
        const Texture& texture = textures()[index];

        // R4e: several materials routinely bind the same payload. The
        // converter already stores it once, so two descriptors carry the same
        // data_offset, and the payload at a given offset is by construction
        // the same bytes. Upload it once and let the later descriptors point
        // at the same texture memory.
        bool shared = false;
        for(std::uint32_t earlier = 0; earlier < index; ++earlier) {
            const Texture& candidate = textures()[earlier];
            if(candidate.data_offset == texture.data_offset &&
               candidate.data_size == texture.data_size) {
                pvr_textures_[index] = pvr_textures_[earlier];
                shared = true;
                ++shared_textures_;
                break;
            }
        }
        if(shared) {
            continue;
        }

#if RE4DC_UI_VRAM
        pvr_textures_[index] = allocate_texture(texture.data_size,
            texture.payload == kPayloadVq, pvr_textures_[header_->texture_count + index]);
#else
        pvr_textures_[index] = pvr_mem_malloc(texture.data_size);
#endif
        if(pvr_textures_[index] == nullptr) {
            error_ = "PVR texture allocation failed";
            return false;
        }
        owns_texture_[index] = true;
        if(inject_failure_after_ != 0U && uploaded >= inject_failure_after_) {
            error_ = "injected mid-upload failure";
            return false;
        }
        ++uploaded;
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
        if(streamed_ && win_path_) {
            // Through the window (opened while it was open). It may have closed since (a load deferred to a later
            // frame): then this package takes a handle of its own, as without the window.
            if(g_win.f==FILEHND_INVALID || std::strcmp(win_path_,g_win.path)) {
                RE4DC_IO_SERIAL_WAIT();
                file_=fs_open(win_path_,O_RDONLY);win_path_=nullptr;
                if(file_==FILEHND_INVALID) { error_="streamed texture upload read failed";return false; }
            } else {
                auto* target=static_cast<std::uint8_t*>(pvr_textures_[index]);
                std::uint32_t o=base_+texture.data_offset,n=texture.data_size;
                bool first=true;
                while(n) {
                    if(!(o>=g_win.off && o<g_win.off+g_win.len)) {
                        if(first) ++g_win.st.misses;
                        if(!win_load(o)) { error_="streamed texture upload read failed";return false; }
                    } else if(first) ++g_win.st.hits;
                    first=false;
                    // Pieces stay whole 32-byte units (store-queue uploads; upload_native pads a ragged tail with
                    // zeros), except the payload's own end: a window end inside a unit reloads from that sector.
                    const std::uint32_t a=g_win.off+g_win.len-o;
                    std::uint32_t k=n<=a?n:(a&~31U);
                    if(!k) {
                        if(!win_load(o)) { error_="streamed texture upload read failed";return false; }
                        continue;
                    }
                    upload_native(g_win.buf+(o-g_win.off),target,k);
                    target+=k;o+=k;n-=k;
                }
                vram_bytes_ += texture.data_size;
                g_win.next=static_cast<std::uint32_t>((base_+size_+2047U)&~std::size_t(2047));   // packages start on sectors
                continue;
            }
        }
#endif
        if(streamed_) {
            auto* target=static_cast<std::uint8_t*>(pvr_textures_[index]);
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
            // Gate: the payload chunks are reported with their member offset;
            // gap() first lets the gate cover bytes no upload reads (padding).
            if(upload_observer.gap)upload_observer.gap(upload_observer.context,this,file_,
#if RE4DC_TEX_PACK
                base_,
#else
                0U,
#endif
                texture.data_offset);
            struct Sink { std::uint8_t* dst; std::uint32_t offset; const Package* package; } sink{target,texture.data_offset,this};
#endif
#if RE4DC_TEX_PACK
            if(fs_seek(file_,static_cast<off_t>(base_+texture.data_offset),SEEK_SET)!=static_cast<off_t>(base_+texture.data_offset) ||
#else
            if(fs_seek(file_,texture.data_offset,SEEK_SET)!=static_cast<off_t>(texture.data_offset) ||
#endif
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
               !storage::read_chunks(file_,texture.data_size,[](const std::uint8_t* src,std::size_t n,void* ctx) {
                   auto& s=*static_cast<Sink*>(ctx);
                   upload_native(src,s.dst,n);s.dst+=n;
                   if(upload_observer.bytes)upload_observer.bytes(upload_observer.context,s.package,s.offset,src,n);
                   s.offset+=static_cast<std::uint32_t>(n);return true;
               },&sink)) {
#else
               !storage::read_chunks(file_,texture.data_size,[](const std::uint8_t* src,std::size_t n,void* ctx) {
                   auto*& dst=*static_cast<std::uint8_t**>(ctx);
                   upload_native(src,dst,n);dst+=n;return true;
               },&target)) {
#endif
                error_="streamed texture upload read failed";return false;
            }
        } else if(texture.payload == kPayloadLinear) {
            // Legacy layout: the PVR cannot consume it, so it is reordered
            // here during upload.
            pvr_txr_load_ex(data_ + texture.data_offset, pvr_textures_[index],
                            texture.width, texture.height, PVR_TXRLOAD_16BPP);
        } else {
            // Already in the layout the PVR expects; copy it straight in.
            upload_native(data_ + texture.data_offset, pvr_textures_[index],
                          texture.data_size);
        }
        vram_bytes_ += texture.data_size;
    }
#if RE4DC_TREE_IMPOSTOR || RE4DC_TEX_PAL4_ALPHA
    if(!bind_palettes(*this)) {
        error_ = "PVR palette banks exhausted";
        return false;
    }
#endif
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    // The member tail no payload read covered (the gate reads it, then finishes).
    if(streamed_ && upload_observer.gap)upload_observer.gap(upload_observer.context,this,file_,
#if RE4DC_TEX_PACK
        base_,
#else
        0U,
#endif
        static_cast<std::uint32_t>(size_));
#endif
    upload_complete_ = true;
    error_ = nullptr;
    return true;
}

// Copies the header and the descriptor array out of the adopted bytes and
// points the package at the copy. Everything the runtime asks a texture package
// for after upload -- header(), textures(), find(), pvr_texture() -- reads only
// that prefix, so the texels behind it are free.
//
// Refuses, changing nothing, if the package has not uploaded, if any payload
// would fall inside the prefix (so dropping the rest could not be safe), or if
// the copy cannot be allocated.
bool Package::release_payload() {
    if(payload_released_) {
        return true;
    }
    if(header_ == nullptr || !upload_complete_) {
        error_ = "payload release before a completed upload";
        return false;
    }
    if(streamed_) {
        // No whole-file CPU payload was allocated: do not count it as freed.
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
        // A live pack window owns the handle. This package has none to close (any texture format; was TEX_PAL8_ALPHA only).
        if(file_ != FILEHND_INVALID)
#endif
        fs_close(file_);file_=FILEHND_INVALID;
        size_=metadata_bytes_;payload_released_=true;return true;
    }
    const std::uint64_t descriptor_end =
        static_cast<std::uint64_t>(header_->texture_offset) +
        static_cast<std::uint64_t>(header_->texture_count) *
            header_->texture_stride;
    if(descriptor_end > size_) {
        error_ = "descriptor range outside the package";
        return false;
    }
    const std::size_t prefix = static_cast<std::size_t>(descriptor_end);
    // Every payload must lie beyond the prefix, or the prefix is not a
    // self-contained metadata block and nothing may be dropped.
    for(std::uint32_t index = 0; index < header_->texture_count; ++index) {
        if(textures()[index].data_offset < prefix) {
            error_ = "payload overlaps the metadata prefix";
            return false;
        }
    }
    std::uint8_t* copy = static_cast<std::uint8_t*>(std::malloc(prefix));
    if(copy == nullptr) {
        error_ = "metadata copy allocation failed";
        return false;
    }
    std::memcpy(copy, data_, prefix);
    metadata_ = copy;
    metadata_bytes_ = prefix;
    released_bytes_ = size_;
    payload_released_ = true;
    data_ = copy;
    size_ = prefix;
    header_ = reinterpret_cast<const Header*>(copy);
    // The mapping, if there was one, backed the bytes just copied away.
    if(file_ != FILEHND_INVALID) {
        fs_close(file_);
        file_ = FILEHND_INVALID;
    }
    return true;
}

#if defined(RE4DC_GANADO_ATLAS_DROP) && RE4DC_GANADO_ATLAS_DROP
bool Package::drop_top_level() {
    if(header_ == nullptr || !streamed_ || upload_complete_ || pvr_textures_ != nullptr ||
       header_->texture_count != 1 || data_ != metadata_ || metadata_ == nullptr)
        return false;
    Texture& texture = const_cast<Texture&>(textures()[0]);
    if(!(texture.flags & kMipmap) || (texture.flags & kTopDrop) || texture.payload != kPayloadVq ||
       texture.width != texture.height || texture.width < 16U)
        return false;
    const std::uint32_t top = (texture.width / 2U) * (texture.height / 2U);
    if(texture.data_size <= 2048U + top || header_->data_size < top)
        return false;
    texture.data_size -= top;
    texture.flags |= kTopDrop;
    const_cast<Header*>(header_)->data_size -= top;
    return true;
}
#endif

void Package::close() {
#if RE4DC_TREE_IMPOSTOR && !RE4DC_TEX_PAL4_ALPHA
    // Before the fence: the next kPal4 upload fences before it rewrites a bank.
    if(header_ != nullptr) release_palettes(*this);
#endif
    if(pvr_textures_ != nullptr) {
        vram_fence();
#if RE4DC_TEX_PAL4_ALPHA
        // Only a completed upload owns banks. Malformed descriptors and
        // failed uploads cannot release another package's reservation.
        if(header_ != nullptr && upload_complete_) release_palettes(*this);
#endif
        if(header_ != nullptr) {
            for(std::uint32_t index = 0; index < header_->texture_count; ++index) {
                // Borrowed pointers are aliases of an owner's allocation;
                // freeing one would be a double free.
                const bool owned =
                    owns_texture_ != nullptr && owns_texture_[index];
#if RE4DC_UI_VRAM
                if(owned && pvr_textures_[header_->texture_count + index] != nullptr) {
                    pvr_mem_free(pvr_textures_[header_->texture_count + index]);
                }
#else
                if(owned && pvr_textures_[index] != nullptr) {
                    pvr_mem_free(pvr_textures_[index]);
                }
#endif
            }
        }
#if defined(RE4DC_TEX_META_EVICT) && RE4DC_TEX_META_EVICT
        // owns_texture_ is set only after pvr_textures_: with no table there is no flag array either
        if(!(streamed_ && metadata_ != nullptr &&
             reinterpret_cast<std::uint8_t*>(pvr_textures_) == metadata_ + meta_tail_offset(metadata_bytes_))) {
            std::free(pvr_textures_);
            std::free(owns_texture_);
        }
    }
#else
        std::free(pvr_textures_);
    }
    std::free(owns_texture_);
#endif
    owns_texture_ = nullptr;
    pvr_textures_ = nullptr;
    vram_bytes_ = 0;
    shared_textures_ = 0;
    if(file_ != FILEHND_INVALID) {
        fs_close(file_);
    }
    file_ = FILEHND_INVALID;
    std::free(metadata_);
    metadata_ = nullptr;
    metadata_bytes_ = 0;
    released_bytes_ = 0;
    payload_released_ = false;
    streamed_ = false;
#if RE4DC_TEX_PACK
    base_ = 0;
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
    win_path_ = nullptr;
#endif
#endif
    upload_complete_ = false;
    inject_failure_after_ = 0;
    data_ = nullptr;
    size_ = 0;
    header_ = nullptr;
}

const Texture* Package::textures() const {
    return reinterpret_cast<const Texture*>(data_ + header_->texture_offset);
}

const Texture* Package::find(const char* material) const {
    for(std::uint32_t index = 0; index < header_->texture_count; ++index) {
        if(std::strncmp(textures()[index].material, material,
                        sizeof(textures()[index].material)) == 0) {
            return &textures()[index];
        }
    }
    return nullptr;
}

pvr_ptr_t Package::pvr_texture(std::uint32_t index) const {
    if(pvr_textures_ == nullptr || index >= header_->texture_count) {
        return nullptr;
    }
    return pvr_textures_[index];
}

} // namespace re4dc::texture
