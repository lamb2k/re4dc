// E1 room-pack loading (lane eng-e1): the behaviour data the hosted code reads in place, served by the engine.
//
// - Player archive (ReadPlayerData): the body of em/pl00.drs (the little-endian disc tree's DRS container, record type
//   0) at pG->pPlayer; PL_ARC_PTR(arc, n) = arc + word n of the body, as on the GameCube.
// - Weapon archive (ReadWepData): the body of em/wep02.drs at pG->pWep; the module's prolog is the hosted
//   src/wep02/wep02.cpp _prolog (the engine links the module's code; its REL in the archive is not used).
// - Room archive: st1/r101.arc compacted at load to the sections the E1 hosted code and services read (CAM, SAT,
//   EAT, CNS), keeping the tagged-archive layout GetDataExt walks.
// - Core archive (pG->pArc): only the camera core data (core.das CAM, ofs_30) and the vibration table (ofs_1C), in a
//   synthetic ArcFile whose offsets point at them.
// All of it lives in the engine's room-pack region (KOS heap, loaded before the first tick; no disc reads in play).
#include "global.h"
#include "player.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#include <string.h>

uint8_t* e1_pl_arc;
uint8_t* e1_wep_arc;
uint8_t* e1_room_arc;
uint8_t* e1_core_arc;
uint32_t e1_resident_bytes[4];   // player, weapon, room, core

extern "C" void* e1_file_load(const char* path, uint32_t* size, uint32_t align)
{
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) {
        e1_log("E1 load: missing %s\n", path);
        return NULL;
    }
    uint32_t n = fs_total(f);
    uint8_t* p = (uint8_t*) memalign(align ? align : 32, n + 32);
    if (!p || fs_read(f, p, n) != (ssize_t) n) {
        e1_log("E1 load: read failed %s\n", path);
        fs_close(f);
        free(p);
        return NULL;
    }
    fs_close(f);
    if (size) *size = n;
    return p;
}

// The type-0 record (the body) of a DRS container, copied into its own resident block.
static uint8_t* drs_body(const char* path, uint32_t* bytes)
{
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) {
        e1_log("E1 load: missing %s\n", path);
        return NULL;
    }
    uint32_t rec[64];
    fs_read(f, rec, sizeof(rec));
    uint32_t size = 0, off = 0;
    for (unsigned i = 8; i + 8 <= 64; i += 8) {   // records start at 0x20, 32 bytes each
        if (rec[i] == 0xFFFFFFFFu) break;
        if (rec[i] == 0) { size = rec[i + 1]; off = rec[i + 3]; break; }
    }
    uint8_t* p = size ? (uint8_t*) memalign(32, size) : NULL;
    if (!p || fs_seek(f, off, SEEK_SET) < 0 || fs_read(f, p, size) != (ssize_t) size) {
        e1_log("E1 load: bad DRS %s\n", path);
        fs_close(f);
        free(p);
        return NULL;
    }
    fs_close(f);
    *bytes = size;
    return p;
}

// GetDataExt (read.cpp): the no-th sub-file with a three-letter tag in a tagged archive.
void* GetDataExt(void* arc, const char* tag, int no)
{
    if (!arc || !tag) return NULL;
    uint32_t num = *(uint32_t*) arc;
    const uint8_t* tags = (const uint8_t*) arc + 0x10 + 4 * num;
    int cnt = 0;
    for (uint32_t i = 0; i < num; i++) {
        const uint8_t* t = tags + 4 * i;
        if (t[0] == tag[0] && t[1] == tag[1] && t[2] == tag[2]) {
            if (cnt == no) return (uint8_t*) arc + ((uint32_t*) ((uint8_t*) arc + 0x10))[i];
            cnt++;
        }
    }
    return NULL;
}

// A tagged archive reduced to the listed tags (same header, offsets and tag tables; sections copied in order), read
// section by section from the file (lane eng-e1b: no whole-archive staging copy in the room pack; r11d's archive is
// 1.2 MB, of which the hosted code reads 0.2 MB).
static uint8_t* compact_arc_file(file_t f, const char* const* keep, unsigned nkeep, uint32_t* out_size)
{
    const uint32_t size = fs_total(f);
    uint8_t hdr[0x10 + 8 * 64];
    if (fs_read(f, hdr, sizeof(hdr)) < 0x10) return NULL;
    uint32_t num = *(const uint32_t*) hdr;
    if (num > 64) return NULL;
    const uint32_t* offs = (const uint32_t*) (hdr + 0x10);
    const uint8_t* tags = hdr + 0x10 + 4 * num;
    uint32_t head = (0x10 + 8 * num + 31) & ~31u, total = head;
    uint32_t len[64] = {0};
    int take[64] = {0};
    for (uint32_t i = 0; i < num; i++) {
        uint32_t end = size;
        for (uint32_t j = 0; j < num; j++) if (offs[j] > offs[i] && offs[j] < end) end = offs[j];
        len[i] = end - offs[i];
        for (unsigned k = 0; k < nkeep; k++) if (!memcmp(tags + 4 * i, keep[k], 3)) take[i] = 1;
        if (take[i]) total += (len[i] + 31) & ~31u;
    }
    uint8_t* d = (uint8_t*) memalign(32, total);
    if (!d) return NULL;
    memset(d, 0, head);
    memcpy(d, hdr, 0x10);
    memcpy(d + 0x10 + 4 * num, tags, 4 * num);
    uint32_t at = head;
    for (uint32_t i = 0; i < num; i++) {
        uint32_t* o = (uint32_t*) (d + 0x10) + i;
        if (!take[i]) {
            *o = 0;
            ((uint8_t*) (d + 0x10 + 4 * num))[4 * i] = 0;   // tag removed: GetDataExt does not find it
            continue;
        }
        fs_seek(f, offs[i], SEEK_SET);
        fs_read(f, d + at, len[i]);
        *o = at;
        at += (len[i] + 31) & ~31u;
    }
    *out_size = total;
    return d;
}

void e1_load_room(unsigned room)
{
    char path[48];
    snprintf(path, sizeof(path), "/cd/st%u/r%03x.arc", room >> 8, room);
#ifdef E2_BOSS
    uint32_t size = 0;
    uint8_t* raw = (uint8_t*) e1_file_load(path, &size, 32);
    if (!raw) return;
    // eng-boss: the arena script and the boss read the whole room archive (numbered sections, RTP route data)
    e1_room_arc = raw;
    e1_resident_bytes[2] = size;
    pG->pRoom = e1_room_arc;
    pG->Rtp = GetDataExt(pG->pRoom, "RTP", 0);
    pG->RoomMes = GetDataExt(pG->pRoom, "MDT", 0);   // read.cpp ReadAreaData: the room data pointers
    pG->pOsd = GetDataExt(pG->pRoom, "OSD", 0);
    pG->pEmi = GetDataExt(pG->pRoom, "EMI", 0);
    e1_log("E1 load: %s %lu B whole (E2 boss), RTP %p\n", path, (unsigned long) size, pG->Rtp);
    {   // the whole core archive (the oba collision object's dummy model is in it)
        uint32_t cb = 0;
        uint8_t* core = drs_body("/cd/etc/core.das", &cb);
        if (!core) return;
        e1_core_arc = core;
        e1_resident_bytes[3] = cb;
        pG->pArc = (ArcFile*) core;
        e1_log("E1 load: core archive %lu B whole (E2 boss)\n", (unsigned long) cb);
        return;
    }
#else
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) { e1_log("E1 load: missing %s\n", path); return; }
    const uint32_t size = fs_total(f);
    // RTP: the room's route points (route_ck.cpp, the partner's follow; lane eng-e1b)
    static const char* const keep[] = {"CAM", "SAT", "EAT", "CNS", "RTP"};
    e1_room_arc = compact_arc_file(f, keep, 5, &e1_resident_bytes[2]);
    fs_close(f);
#endif
    pG->pRoom = e1_room_arc;
    e1_log("E1 load: %s %lu -> %lu B (CAM SAT EAT CNS RTP)\n", path, (unsigned long) size, (unsigned long) e1_resident_bytes[2]);
    // core archive: the camera core data and the vibration table
    uint32_t cb = 0;
    uint8_t* core = drs_body("/cd/etc/core.das", &cb);
    if (!core) return;
    void* cam = GetDataExt(core, "CAM", 0);
    void* vib = GetDataExt(core, "VIB", 0);
    const uint32_t cam_bytes = 0x20, vib_bytes = 0x2C0;
    e1_core_arc = (uint8_t*) memalign(32, 0x100 + cam_bytes + vib_bytes);
    memset(e1_core_arc, 0, 0x100);
    memcpy(e1_core_arc + 0x100, cam, cam_bytes);
    memcpy(e1_core_arc + 0x100 + cam_bytes, vib, vib_bytes);
    ArcFile* a = (ArcFile*) e1_core_arc;
    a->ofs_30 = 0x100;
    a->ofs_1C = 0x100 + cam_bytes;
    e1_resident_bytes[3] = 0x100 + cam_bytes + vib_bytes;
    free(core);
    pG->pArc = a;
}

// read.cpp ReadPlayerData, engine form: pl_flag bit 0 asks for the archive; Leon (type 0, costume 0) = em/pl00.drs.
void ReadPlayerData(int type, int costume)
{
    if (!(pG->pl_flag & 1)) return;
    pG->pl_flag &= ~1;
#ifdef E2_BOSS
    if (type != 0 || costume > 1) {   // eng-boss: costume 1 (chapter 2, file 0x5A) = em/pl08
#else
    if (type != 0 || costume != 0) {
#endif
        e1_stub_hit("ReadPlayerData(other character)", type << 8 | costume);
        return;
    }
    if (!e1_pl_arc) e1_pl_arc = drs_body(costume ? "/cd/em/pl08.drs" : "/cd/em/pl00.drs", &e1_resident_bytes[0]);
    pG->pPlayer = (PlArc*) e1_pl_arc;
    e1_log("E1 load: player archive %lu B at %p\n", (unsigned long) e1_resident_bytes[0], e1_pl_arc);
}

extern "C" void _prolog();   // src/wep02/wep02.cpp (hosted)
static int wep_loaded = -1;
// read.cpp ReadWepData, engine form: Leon's handgun (weapon 2 / 3 -> wep_data_leon[2,3] -> em/wep02, module wep02).
extern "C" void ReadWepData(int no, int type)
{
    if (no != 2 && no != 3) {
        e1_stub_hit("ReadWepData(unhosted weapon)", no << 8 | type);
        return;
    }
    if (wep_loaded == 2) {
        pG->pWep = e1_wep_arc;
        return;
    }
    e1_wep_arc = drs_body("/cd/em/wep02.drs", &e1_resident_bytes[1]);
    pG->pWep = e1_wep_arc;
    _prolog();
    wep_loaded = 2;
    e1_log("E1 load: weapon archive %lu B at %p (module wep02 prolog)\n", (unsigned long) e1_resident_bytes[1], e1_wep_arc);
}
extern "C" void ReleaseWepData() {}
