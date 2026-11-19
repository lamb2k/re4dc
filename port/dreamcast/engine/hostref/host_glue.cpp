// hostref (game side): the data the player and camera read, placed where the game's pointers expect it
// (pG->pArc core, pG->pPlayer player, pG->pWep weapon, pG->pRoom room), and the read.cpp entry points
// the player calls (ReadPlayerData, ReadWepData, ReleaseWepData). The files come from a converted
// (little-endian, Dreamcast) data tree; host_data.cpp walks their DVD containers.
#include "hostref.h"
#include "global.h"
#include "main.h"
#include "player.h"

static const char* g_tree;

bool host_load_core(const char* tree)
{
    g_tree = tree;
    void* p = host_load_data(tree, "etc/core.das", "core", 0);
    if (!p) return false;
    pG->pArc = (ArcFile*) p;
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

bool host_load_room(const char* tree, unsigned room_id)
{
    static const char hex[] = "0123456789abcdef";
    char name[] = "stN/rNNN.arc";
    name[2] = hex[(room_id >> 8) & 0xF];
    name[5] = hex[(room_id >> 8) & 0xF];
    name[6] = hex[(room_id >> 4) & 0xF];
    name[7] = hex[room_id & 0xF];
    void* p = host_load_data(tree, name, "room", 0);
    if (!p) return false;
    pG->pRoom = p;
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
