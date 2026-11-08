// D367 VMU saves (VMU_SAVE=1, vmusave.mk; empty in the default image): the VMU file layer under
// the virtual memory card (platform/card.cpp). KOS vmufs low-level calls over caller buffers
// (pinned KOS, no vmufs_write: its OVERWRITE deletes before writing). No allocation here.
//
// Write order (design-vmu 5.3), A/B when the free blocks hold the new copy:
//   1. new data blocks into free blocks (FAT changes stay in RAM)   pull: nothing lost
//   2. FAT                                                          pull: leaked blocks, old save intact
//   3. dir block with the new entry = commit                        pull: two copies, newest seq wins
//   4. old entry: dir block, then FAT
// When the VMU is too full for both copies (user decision 2026-09-23), the old copy is released
// in RAM first and the new one written into the freed blocks: FAT, then dir. A pull then risks
// only that one save (a bad CRC -> the game's "damaged file" path); no other file's blocks move.
#if RE4DC_VMU_SAVE
#include <kos.h>
#include <dc/vmufs.h>
#include <dc/maple.h>
#include <dc/maple/vmu.h>
#include <string.h>

#include "vmu_store.h"
#include "re4dc_platform.h"

extern "C" uint16_t net_crc16ccitt(const uint8_t* data, int size, uint16_t start);

// VMU_SAFE_IO=1 (issue #66 bug 5): KOS vmu_block_write / vmu_block_read over the wrapped symbols (vmufs.c calls them too).
// KOS waits 100 ms for each maple answer. If that runs out the frame is still on the maple queue, but the next
// maple_frame_init clears frame->queued, so maple_queue_frame inserts it a second time: the frame then links to itself and
// maple_queue_flush spins forever in the vblank interrupt. The whole console stops, the crash watchdog included, in the
// middle of a VMU write; a torn FAT or directory block can then read back as corrupt. Here a late answer takes the frame
// off the queue before it is reused, every wait is bounded, and a block that cannot be written is an error the game shows.
// VMU_IO_FAULT=N (test discs only): before the Nth block write since boot, maple sends are held off for 700 ms.
#if (defined(RE4DC_VMU_SAFE_IO) && RE4DC_VMU_SAFE_IO) || (defined(RE4DC_VMU_IO_FAULT) && RE4DC_VMU_IO_FAULT)
#include <kos/genwait.h>
#include <arch/irq.h>
#include <arch/timer.h>
extern "C" {
int __wrap_vmu_block_write(maple_device_t* dev, uint16_t blocknum, const uint8_t* buffer);
int __real_vmu_block_write(maple_device_t* dev, uint16_t blocknum, const uint8_t* buffer);
int __wrap_vmu_block_read(maple_device_t* dev, uint16_t blocknum, uint8_t* buffer);
}
namespace {
#if RE4DC_VMU_IO_FAULT
unsigned s_writes;
void* fault_end(void*)
{
    thd_sleep(700);
    maple_state.dma_in_progress = 0;
    return nullptr;
}
void fault_maybe(unsigned blk)
{
    if (++s_writes != RE4DC_VMU_IO_FAULT) return;
    while (maple_state.dma_in_progress) thd_pass();
    maple_state.dma_in_progress = 1;
    thd_create(1, fault_end, nullptr);
    re4dc_log("card-vmu: fault test: maple sends held 700 ms at write %u block %u\n", s_writes, blk);
}
#endif
#if RE4DC_VMU_SAFE_IO
constexpr unsigned kAnswerMs = 500, kFrameMs = 2000, kDmaEndMs = 1000;
volatile int s_answered;
unsigned s_late;
uint64_t now_ms() { return timer_ms_gettime64(); }
void answered_cb(maple_state_t*, maple_frame_t* f)
{
    s_answered = 1;
    genwait_wake_all(f);
}
bool frame_take(maple_frame_t* f)
{
    const uint64_t t0 = now_ms();
    while (maple_frame_trylock(f) < 0) {
        if (now_ms() - t0 > kFrameMs) return false;
        thd_sleep(2);
    }
    return true;
}
void frame_release(maple_frame_t* f) { f->state = MAPLE_FRAME_VACANT; }
// Off the queue, and no DMA still landing in its buffer, before anyone reuses the frame.
void frame_abandon(maple_frame_t* f, const char* what, unsigned blk)
{
    ++s_late;
    maple_queue_remove(f);
    const uint64_t t0 = now_ms();
    while (maple_state.dma_in_progress && now_ms() - t0 < kDmaEndMs) thd_sleep(2);
    frame_release(f);
    re4dc_log("card-vmu: %s block %u got no answer in %u ms (late %u)\n", what, blk, kAnswerMs, s_late);
}
bool send_and_wait(maple_frame_t* f)
{
    const uint64_t t0 = now_ms();
    const int o = irq_disable();
    s_answered = 0;
    f->callback = answered_cb;
    maple_queue_frame(f);
    while (!s_answered && now_ms() - t0 < kAnswerMs) genwait_wait(f, "vmu_safe_io", 20);
    const bool got = s_answered;
    irq_restore(o);
    return got;
}
int write_once(maple_device_t* dev, uint16_t blk, const uint8_t* in)
{
    maple_frame_t* f = &dev->frame;
    if (!frame_take(f)) return MAPLE_ETIMEOUT;
    int rv = MAPLE_EOK;
    for (int phase = 0; phase < 5; ++phase) {
        f->state = MAPLE_FRAME_UNSENT;
        maple_frame_init(f);
        f->send_buf[0] = MAPLE_FUNC_MEMCARD;
        f->send_buf[1] = ((blk & 0xFF) << 24) | ((blk >> 8) << 16) | (phase << 8);
        if (phase < 4) {
            memcpy(f->send_buf + 2, in + 128 * phase, 128);
            f->cmd = MAPLE_COMMAND_BWRITE;
            f->length = 2 + 128 / 4;
        } else {
            f->cmd = MAPLE_COMMAND_BSYNC;
            f->length = 2;
        }
        f->dst_port = dev->port;
        f->dst_unit = dev->unit;
        if (!send_and_wait(f)) {
            frame_abandon(f, "write", blk);
            return MAPLE_ETIMEOUT;
        }
        if (phase < 4 && ((maple_response_t*) f->recv_buf)->response != MAPLE_RESPONSE_OK) rv = MAPLE_EFAIL;
    }
    frame_release(f);
    return rv;
}
#endif
}  // namespace
int __wrap_vmu_block_write(maple_device_t* dev, uint16_t blocknum, const uint8_t* buffer)
{
#if RE4DC_VMU_IO_FAULT
    fault_maybe(blocknum);
#endif
#if RE4DC_VMU_SAFE_IO
    int rv = MAPLE_EFAIL;
    for (int i = 0; i < 4; ++i) {
        rv = write_once(dev, blocknum, buffer);
        if (rv == MAPLE_EOK) return rv;
        thd_sleep(100);
    }
    re4dc_log("card-vmu: write block %u failed rc=%d\n", (unsigned) blocknum, rv);
    return rv;
#else
    return __real_vmu_block_write(dev, blocknum, buffer);
#endif
}
#if RE4DC_VMU_SAFE_IO
int __wrap_vmu_block_read(maple_device_t* dev, uint16_t blocknum, uint8_t* buffer)
{
    maple_frame_t* f = &dev->frame;
    if (!frame_take(f)) return MAPLE_ETIMEOUT;
    const uint32_t id = ((blocknum & 0xFF) << 24) | ((blocknum >> 8) << 16);
    f->state = MAPLE_FRAME_UNSENT;
    maple_frame_init(f);
    f->send_buf[0] = MAPLE_FUNC_MEMCARD;
    f->send_buf[1] = id;
    f->cmd = MAPLE_COMMAND_BREAD;
    f->length = 2;
    f->dst_port = dev->port;
    f->dst_unit = dev->unit;
    if (!send_and_wait(f)) {
        frame_abandon(f, "read", blocknum);
        return MAPLE_ETIMEOUT;
    }
    const maple_response_t* r = (const maple_response_t*) f->recv_buf;
    const uint32_t* d = (const uint32_t*) r->data;
    int rv = MAPLE_EFAIL;
    if (r->response == MAPLE_RESPONSE_DATATRF && d[0] == MAPLE_FUNC_MEMCARD && d[1] == id) {
        memcpy(buffer, d + 2, 512);
        rv = MAPLE_EOK;
    }
    frame_release(f);
    return rv;
}
#endif
#endif

namespace {
maple_device_t* dev_of(const VmuStore* s) { return static_cast<maple_device_t*>(s->dev); }
vmu_root_t* root_of(const VmuStore* s) { return reinterpret_cast<vmu_root_t*>(s->root); }
vmu_dir_t* dir_of(const VmuStore* s) { return reinterpret_cast<vmu_dir_t*>(s->dir); }
unsigned dir_count(const VmuStore* s) { return root_of(s)->dir_size * 16U; }

bool is_memcard(maple_device_t* d) { return d && d->valid && (d->info.functions & MAPLE_FUNC_MEMCARD); }

// dir entries hold names without a terminator; vmufs_dir_find compares 12 bytes with strncmp.
void set_name(vmu_dir_t* e, const char* name)
{
    memset(e->filename, 0, sizeof(e->filename));
    for (unsigned i = 0; i < sizeof(e->filename) && name[i]; ++i) e->filename[i] = name[i];
}

struct Lock {
    Lock() { vmufs_mutex_lock(); }
    ~Lock() { vmufs_mutex_unlock(); }
};

// The native and host writers share one fixed, endian-independent icon asset.
void build_icon(unsigned char* hdr_pal, unsigned char* px)
{
    static const unsigned char icon[] = {
#include "vmu_save_icon.inc"
    };
    static_assert(sizeof(icon) == 32 + 512, "VMU icon must contain one palette and frame");
    memcpy(hdr_pal, icon, 32);
    memcpy(px, icon + 32, 512);
}
}  // namespace

extern "C" {

int vmus_pick(VmuStore* s)
{
    maple_device_t* d = maple_enum_dev(0, 1);  // A1
    if (!is_memcard(d)) {
        d = nullptr;
        for (int p = 0; p < 4 && !d; ++p)
            for (int u = 1; u < 3 && !d; ++u) {
                maple_device_t* c = maple_enum_dev(p, u);
                if (is_memcard(c)) d = c;
            }
    }
    s->dev = d;
    s->mounted = 0;
    if (!d) return VMUS_NOCARD;
    s->port = d->port;
    s->unit = d->unit;
    return VMUS_OK;
}

int vmus_present(const VmuStore* s)
{
    if (!s->dev) return 0;
    maple_device_t* d = maple_enum_dev(s->port, s->unit);
    return d == s->dev && is_memcard(d);
}

int vmus_mount(VmuStore* s, void* root512, void* fat512, void* dir6656)
{
    s->root = static_cast<unsigned char*>(root512);
    s->fat = static_cast<uint16_t*>(fat512);
    s->dir = static_cast<unsigned char*>(dir6656);
    s->mounted = 0;
    if (!vmus_present(s)) return VMUS_NOCARD;
    Lock lock;
    if (vmufs_root_read(dev_of(s), root_of(s)) < 0) return vmus_present(s) ? VMUS_IOERROR : VMUS_NOCARD;
    const vmu_root_t* r = root_of(s);
    for (int i = 0; i < 16; ++i)
        if (r->magic[i] != 0x55) {
            s->mounted = -1;
            return VMUS_NOFS;
        }
    if (r->fat_size != 1 || r->dir_size == 0 || r->dir_size > 13 || r->blk_cnt == 0 || r->blk_cnt > 241 ||
        r->fat_loc >= 256 || r->dir_loc >= 256) {
        s->mounted = -1;
        return VMUS_NOFS;
    }
    if (vmufs_fat_read(dev_of(s), root_of(s), s->fat) < 0 || vmufs_dir_read(dev_of(s), root_of(s), dir_of(s)) < 0)
        return vmus_present(s) ? VMUS_IOERROR : VMUS_NOCARD;
    for (unsigned i = 0; i < dir_count(s); ++i) dir_of(s)[i].dirty = 0;
    s->mounted = 1;
    return VMUS_OK;
}

int vmus_find(const VmuStore* s, const char* name)
{
    if (s->mounted != 1) return -1;
    char n[12];
    memset(n, 0, sizeof(n));
    for (unsigned i = 0; i < sizeof(n) && name[i]; ++i) n[i] = name[i];
    for (unsigned i = 0; i < dir_count(s); ++i) {
        const vmu_dir_t* e = &dir_of(s)[i];
        if (e->filetype && memcmp(e->filename, n, sizeof(n)) == 0) return (int) i;
    }
    return -1;
}

unsigned vmus_file_blocks(const VmuStore* s, int idx) { return idx < 0 ? 0 : dir_of(s)[idx].filesize; }
unsigned vmus_free_blocks(const VmuStore* s) { return s->mounted == 1 ? (unsigned) vmufs_fat_free(root_of(s), s->fat) : 0; }
unsigned vmus_free_dirents(const VmuStore* s) { return s->mounted == 1 ? (unsigned) vmufs_dir_free(root_of(s), dir_of(s)) : 0; }

int vmus_read(VmuStore* s, int idx, void* buf, unsigned cap, unsigned blocks)
{
    if (s->mounted != 1 || idx < 0) return VMUS_NOFILE;
    const vmu_dir_t* e = &dir_of(s)[idx];
    unsigned n = e->filesize;
    if (blocks && blocks < n) n = blocks;
    if (n * 512 > cap) return VMUS_FULL;
    Lock lock;
    unsigned blk = e->firstblk;
    unsigned char* out = static_cast<unsigned char*>(buf);
    for (unsigned i = 0; i < n; ++i) {
        if (blk >= root_of(s)->blk_cnt) return VMUS_IOERROR;  // chain ends early / corrupt FAT
        if (vmu_block_read(dev_of(s), (uint16_t) blk, out + i * 512) != MAPLE_EOK)
            return vmus_present(s) ? VMUS_IOERROR : VMUS_NOCARD;
        blk = s->fat[blk];
    }
    return VMUS_OK;
}

int vmus_delete(VmuStore* s, const char* name)
{
    const int idx = vmus_find(s, name);
    if (idx < 0) return VMUS_NOFILE;
    Lock lock;
    if (vmufs_file_delete(root_of(s), s->fat, dir_of(s), dir_of(s)[idx].filename) < 0) return VMUS_IOERROR;
    if (vmufs_dir_write(dev_of(s), root_of(s), dir_of(s)) < 0 || vmufs_fat_write(dev_of(s), root_of(s), s->fat) < 0)
        return vmus_present(s) ? VMUS_IOERROR : VMUS_NOCARD;
    return VMUS_OK;
}

int vmus_write(VmuStore* s, const char* name, const void* data, unsigned blocks, const char* old, int* inplace)
{
    *inplace = 0;
    if (s->mounted != 1) return VMUS_NOCARD;
    const int oidx = old ? vmus_find(s, old) : -1;
    const unsigned free_now = vmus_free_blocks(s);
    const unsigned old_blocks = vmus_file_blocks(s, oidx);
    if (vmus_find(s, name) >= 0) return VMUS_IOERROR;           // caller clears stale copies first
    if (free_now < blocks && free_now + old_blocks < blocks) return VMUS_FULL;
    if (vmus_free_dirents(s) == 0 && oidx < 0) return VMUS_FULL;
    Lock lock;
    const bool ab = free_now >= blocks && vmus_free_dirents(s) > 0;
    if (!ab) {
        // In place: release the old copy in RAM; its blocks take the new data.
        *inplace = 1;
        if (vmufs_file_delete(root_of(s), s->fat, dir_of(s), dir_of(s)[oidx].filename) < 0) return VMUS_IOERROR;
    }
    vmu_dir_t e;
    memset(&e, 0, sizeof(e));
    e.filetype = 0x33;
    set_name(&e, name);
    vmufs_dir_fill_time(&e);
    e.hdroff = 0;
    const int rv = vmufs_file_write(dev_of(s), root_of(s), s->fat, dir_of(s), &e,
                                    const_cast<void*>(data), (int) blocks);  // step 1 (+ dir entry in RAM)
    if (rv < 0) {
        // Nothing on the card references the new blocks: reload FAT/dir to drop the RAM changes.
        vmufs_fat_read(dev_of(s), root_of(s), s->fat);
        vmufs_dir_read(dev_of(s), root_of(s), dir_of(s));
        return rv == -2 ? VMUS_FULL : (vmus_present(s) ? VMUS_IOERROR : VMUS_NOCARD);
    }
    if (vmufs_fat_write(dev_of(s), root_of(s), s->fat) < 0) goto io;          // step 2
    if (vmufs_dir_write(dev_of(s), root_of(s), dir_of(s)) < 0) goto io;       // step 3: commit
    if (ab && oidx >= 0) {                                                      // step 4
        if (vmufs_file_delete(root_of(s), s->fat, dir_of(s), dir_of(s)[oidx].filename) < 0) goto io;
        if (vmufs_dir_write(dev_of(s), root_of(s), dir_of(s)) < 0) goto io;
        if (vmufs_fat_write(dev_of(s), root_of(s), s->fat) < 0) goto io;
    }
    return VMUS_OK;
io:
    s->mounted = 0;  // RAM copies may no longer match the card: the next screen remounts
    return vmus_present(s) ? VMUS_IOERROR : VMUS_NOCARD;
}

int vmus_rewrite(VmuStore* s, int idx, const void* data, unsigned blocks)
{
    if (s->mounted != 1 || idx < 0 || dir_of(s)[idx].filesize != blocks) return VMUS_IOERROR;
    Lock lock;
    unsigned blk = dir_of(s)[idx].firstblk;
    const unsigned char* in = static_cast<const unsigned char*>(data);
    for (unsigned i = 0; i < blocks; ++i) {
        if (blk >= root_of(s)->blk_cnt) return VMUS_IOERROR;
        if (vmu_block_write(dev_of(s), (uint16_t) blk, in + i * 512) != MAPLE_EOK)
            return vmus_present(s) ? VMUS_IOERROR : VMUS_NOCARD;
        blk = s->fat[blk];
    }
    return VMUS_OK;
}

unsigned vmus_package(unsigned char* out, const char* desc_long, unsigned payload_len)
{
    static const char kShort[] = "RESIDENT EVIL 4";
    memset(out, 0, 128);
    memset(out, ' ', 48);
    memcpy(out, kShort, sizeof(kShort) - 1);
    for (unsigned i = 0; i < 32 && desc_long[i]; ++i) out[16 + i] = (unsigned char) desc_long[i];
    memcpy(out + 48, "RE4DC", 5);
    out[64] = 1;  // icon_cnt; anim speed, eyecatch 0
    out[72] = (unsigned char) payload_len;
    out[73] = (unsigned char) (payload_len >> 8);
    out[74] = (unsigned char) (payload_len >> 16);
    out[75] = (unsigned char) (payload_len >> 24);
    build_icon(out + 96, out + 128);
    const unsigned total = 128 + 512 + payload_len;
    const uint16_t crc = net_crc16ccitt(out, (int) total, 0);
    out[70] = (unsigned char) crc;
    out[71] = (unsigned char) (crc >> 8);
    const unsigned size = (total + 511) & ~511U;
    memset(out + total, 0, size - total);
    return size;
}

}  // extern "C"
#endif  // RE4DC_VMU_SAVE
