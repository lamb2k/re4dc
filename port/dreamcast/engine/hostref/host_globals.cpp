// hostref: the main-loop globals the player and camera read (main.cpp and the managers' instances).
// Managers the E1 closure does not host (action button, damage, items, objects, lights, HUD, messages,
// debug camera, log) exist as zeroed instances of their real layout; their methods are logging stubs
// (host_stubs.cpp). No constructor of theirs runs: their code is not part of the reference.
#include "hostref.h"
#include "global.h"
#include "main.h"
#include "main_sub.h"
#include "joy.h"
#include "act_btn.h"
#include "dmg.h"
#include "item.h"
#include "obj.h"
#include "light.h"
#include "db_cam.h"
#include "cockpit.h"
#include "mes.h"
#include "id_sys.h"
#include "db_log.h"

// main.cpp
const Vec vecZero = {0.0f, 0.0f, 0.0f};
GlobalWork Global;
SystemSaveWork SystemSave;
JOY Joy[4];
KeyWork Key;
ScreenInfo Screen;
GlobalWork* pG = &Global;
SystemWork* pSys = (SystemWork*) &SystemSave;
f32 ZNEAR;
f32 ZFAR;
f32 ORTHO_T;
f32 ORTHO_B;
f32 ORTHO_L;
f32 ORTHO_R;

// game.cpp collision-profile counters (atari.cpp increments them)
u32 g_at2_cnt[20];
u32 g_at2_cyc[20];
u32 g_at2_total;
u32 g_at2_total_cyc;

// filter0a.cpp (drawing flags the camera sets)
u8 use_filter0a;
u8 filter0a_mask_flag;
u8 filter0a_mask_id;
u8 filter0a_mask_alpha;

// Stand-ins: the real layout, zero-filled, no constructor.
#define HOST_STANDIN(Type, name) \
    alignas(32) unsigned char host_standin_##name[sizeof(Type)] asm(#name)
HOST_STANDIN(cActionButton, ActBtn);
HOST_STANDIN(cDmgMgr, DmgMgr);
HOST_STANDIN(cItemMgr, ItemMgr);
HOST_STANDIN(cLightMgr, LightMgr);
HOST_STANDIN(debugCamera, CamDbg);
HOST_STANDIN(Cockpit, Cckpt);
HOST_STANDIN(MessageControl, cMes);
HOST_STANDIN(IDSystem, IdSys);

alignas(32) static unsigned char host_log_obj[sizeof(cLog)];
cLogPtr pLog = {(cLog*) host_log_obj};
