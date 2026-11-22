// hostref (game side): the data the player and camera read, placed where the game's pointers expect it
// (pG->pArc core, pG->pPlayer player, pG->pWep weapon, pG->pRoom room), and the read.cpp entry points
// the player calls (ReadPlayerData, ReadWepData, ReleaseWepData). The files come from a converted
// (little-endian, Dreamcast) data tree; host_data.cpp walks their DVD containers.
#include "hostref.h"
#include "global.h"
#include "main.h"
#include "player.h"

#include "../services/input/vib_table.h"

static const char* g_tree;
void* GetDataExt(void* arc, const char* tag, int no);
extern "C" int host_fixed_release(void* p, uint32_t size);   // host_mem.cpp (lane eng-load1)

// The rumble table (section VIB) in the PC's order (lane eng-e1h; services/input/vib_table.h): the tree carries it
// big-endian, which made the first shot's rumble (objRuger moveFire, VibSetData) read a pattern outside the archive.
// Its length: up to the next section of the archive (DataExtHeader: count, three words, offsets).
static void core_vib_to_host(void* arc)
{
    uint8_t* vib = (uint8_t*) GetDataExt(arc, "VIB", 0);
    if (!vib) return;
    const uint32_t* h = (const uint32_t*) arc;
    const uint32_t at = (uint32_t) (vib - (uint8_t*) arc);
    uint32_t end = 0;
    for (uint32_t i = 0; i < h[0] && i < 4096; i++) {
        const uint32_t o = h[4 + i];
        if (o > at && (!end || o < end)) end = o;
    }
    const int n = vib_table::to_host(vib, end ? end - at : 0x2C0);
    if (n < 0) host_fatal(2, "core archive: the rumble table is not a table");
    if (n > 0) host_log("core archive: rumble table converted to the host order (%d patterns)\n", n);
}

bool host_load_core(const char* tree)
{
    g_tree = tree;
    void* p = host_load_data(tree, "etc/core.das", "core", 0);
    if (!p) return false;
    pG->pArc = (ArcFile*) p;
    core_vib_to_host(p);
    return true;
}

// ReadPlayerData (read.cpp) for Leon, costumes 0..3: FileTbl 6 / 0x5A / 0x5B / 0x79 (the DVD table's
// names with .drs). The player archive has no DLL (dll 0 for type 0).
static const char* const kLeonFiles[4] = {"em/pl00.drs", "em/pl0e.drs", "em/pl0f.drs", "em/pl1c.drs"};
bool host_load_player(const char* tree, int type, int costume)
{
    if (type != 0 || costume < 0 || costume > 3) host_fatal(2, "only Leon (pl_type 0) is hosted");
    void* p = host_load_data(tree, kLeonFiles[costume], "player", 0);
    if (!p) return false;
    pG->pPlayer = (PlArc*) p;
    return true;
}

extern "C" void host_room_post(void* arc) __attribute__((weak));   // lane eng-skel2 (native builds only)
bool host_load_room(const char* tree, unsigned room_id)
{
    static const char hex[] = "0123456789abcdef";
    char name[] = "stN/rNNN.arc";
    name[2] = hex[(room_id >> 8) & 0xF];
    name[5] = hex[(room_id >> 8) & 0xF];
    name[6] = hex[(room_id >> 4) & 0xF];
    name[7] = hex[room_id & 0xF];
    // lane eng-load1: a door's next room returns the last room's archive first when it is the data region's newest
    // block (the first room's lies under the weapon archive and stays)
    static uint32_t room_bytes;
    if (pG->pRoom && room_bytes && host_fixed_release(pG->pRoom, room_bytes))
        host_log("data: room archive %08x returned (%u bytes)", (unsigned) (uintptr_t) pG->pRoom, room_bytes);
    void* p = host_load_data(tree, name, "room", &room_bytes);
    if (!p) return false;
    pG->pRoom = p;
    if (host_room_post) host_room_post(p);   // lane eng-skel2: the native builds' baked collision (svc/colb_host.cpp)
    return true;
}

// ---- the read.cpp entry points the player calls ----
void ReadPlayerData(int type, int costume)
{
    (void) type; (void) costume;
    host_stub_hit("ReadPlayerData");   // the reference loads the player once, before the first tick
}

extern "C" void _prolog();   // wep02.cpp: the handgun module's REL entry (WeaponInitFunc / WeaponMoveFunc)
static int g_wep_loaded = -1;

// ReadWepData (read.cpp) for the handguns of the wep02 module (weapon_no 2 Punisher, 3 Red9: FileTbl 9,
// em/wep02). Other weapons are outside the E1 reference: logged, no data, no module.
extern "C" void ReadWepData(int no, int type)
{
    (void) type;
    if (no != 2 && no != 3) {
        host_stub_hit("ReadWepData(other weapon)");
        return;
    }
    if (g_wep_loaded == 2) return;
    void* p = host_load_data(g_tree, "em/wep02.das", "weapon", 0);
    if (!p) host_fatal(2, "weapon archive em/wep02 missing");
    pG->pWep = p;
    g_wep_loaded = 2;
    _prolog();   // pModule->prolog(): the module is linked into the reference, not relocated
}

extern "C" void ReleaseWepData()
{
    // The weapon archive stays resident (one handgun per run); the module keeps its routines.
}
