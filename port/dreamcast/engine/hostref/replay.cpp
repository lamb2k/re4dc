// hostref replay (game side): Leon's original player and camera code on the PC, driven by a recorded pad
// stream (fixture format and trace format: host_io.cpp; usage: re4ref with no arguments).
//
// One tick is one pass of the game's frame loop (main.cpp): PadRead, Frame_cnt++, then the part of
// gameMainLoop (game.cpp) that the E1 closure hosts, in its order: UpdateNearClipDist, the player's move
// (pPL->move, under the game's own condition), the object manager's move (the held weapon), CameraMove.
// Scenario, enemies, effects, lights, damage and the HUD are not hosted (their entry points are stubs).
// The trace line for tick t is written after that pass: the state the old game's logic trace (LT t=)
// records at the top of the next iteration (before that iteration's render; see PLAYS_RIGHT.md).
#include "hostref.h"
#include "global.h"
#include "main.h"
#include "main_sub.h"
#include "joy.h"
#include "pad.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "player.h"
#include "atari.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "view.h"
#include "cons.h"
#include "rnd.h"

void* GetDataExt(void* arc, const char* tag, int no);
extern "C" void PlayerInit();   // player.cpp (C linkage)
struct ConsRoom;
int ConsInitRoom(ConsRoom* p);   // cons.cpp
bool host_load_core(const char* tree);
bool host_load_player(const char* tree, int type, int costume);
bool host_load_room(const char* tree, unsigned room_id);

static HostFixture g_fx;
static HostOptions g_opt;
static PADStatus g_pad;

// Pad 0 for tick t (piecewise constant), with the shift-input control applied.
static PADStatus pad_for(unsigned t)
{
    PADStatus s;
    __builtin_memset(&s, 0, sizeof s);
    const int shift = g_opt.control == HOST_CTL_SHIFT_INPUT ? g_opt.shift : 0;
    for (unsigned i = 0; i < g_fx.npads; i++) {
        const HostPad& p = g_fx.pads[i];
        if ((long) p.tick + shift <= (long) t) {
            s.button = p.button;
            s.stickX = p.sx; s.stickY = p.sy;
            s.substickX = p.cx; s.substickY = p.cy;
            s.triggerLeft = p.tl; s.triggerRight = p.tr;
        }
    }
    return s;
}

// ---- the SDK pad interface pad.cpp reads (PADRead fills four channels; only 0 is connected) ----
void PADInit() {}
int PADReset(u32) { return 1; }
void PADSetAnalogMode(u32) {}
u32 PADRead(PADStatus* status)
{
    for (int i = 0; i < 4; i++) {
        __builtin_memset(&status[i], 0, sizeof(PADStatus));
        status[i].err = -1;   // PAD_ERR_NO_CONTROLLER
    }
    status[0] = g_pad;
    status[0].err = 0;
    return 0;
}
extern "C" int GetSystemVcnt() { return 2; }   // 30 pictures a second: two fields per tick

// UpdateNearClipDist (main_sub.cpp): the near clip is 100 unless a water / filter copy asked for another.
void UpdateNearClipDist()
{
    GlobalWork* g = pG;
    if (!(g->Status_flg[1] & 0x1000)) {
        ZNEAR = 100.0f;
    }
    g->Status_flg[1] &= ~0x1000;
}

// ---- the parts of gameRoomInit (game.cpp) that set up what the player and camera read ----
static bool room_init(const char* tree)
{
    if (!host_load_core(tree) || !host_load_player(tree, 0, 0) || !host_load_room(tree, g_fx.room)) return false;
    ConsInitRoom((ConsRoom*) GetDataExt(pG->pRoom, "CNS", 0));
    ModInfoMgr.roomInit();
    ModInfoMgr.arrayAlloc(ConsGetRoomValue(7));
    PartsMgr.roomInit();
    PartsMgr.arrayAlloc(ConsGetRoomValue(6));
    EmMgr.roomInit();
    EmMgr.arrayAlloc(ConsGetRoomValue(0));
    ObjMgr.roomInit();
    ObjMgr.arrayAlloc(ConsGetRoomValue(1));
    {
        Vec pos = {0.0f, 0.0f, 0.0f};
        Vec rot = {0.0f, 0.0f, 0.0f};
        void* p = GetDataExt(pG->pRoom, "SAT", 0);
        SatMgr.roomInit();
        SatMgr.arrayAlloc(ConsGetRoomValue(10));
        SatMgr.create(p, 0, &pos, &rot, 0);
        p = GetDataExt(pG->pRoom, "EAT", 0);
        EatMgr.roomInit();
        EatMgr.arrayAlloc(ConsGetRoomValue(11));
        EatMgr.create(p, 0, &pos, &rot, 0);
        SatMgr.seCk = 0;
        EatMgr.seCk = 1;
        EatMgr.initEffInfo();
    }
    // The player: EmMgr.create(0, 0) (game.cpp, after the collision and event set-up, before the camera).
    pG->sub_pos.x = g_fx.pos[0];
    pG->sub_pos.y = g_fx.pos[1];
    pG->sub_pos.z = g_fx.pos[2];
    pG->sub_angle = g_fx.ang;
    host_stub_tick_reset();
    if (!EmMgr.create(0, 0) || !pPL) host_fatal(3, "the player was not created");
    CameraRoomInit();
    void* cam = GetDataExt(pG->pRoom, "CAM", 0);
    if (cam) CamCtrl.RoomDataRead((CameraDataHeader*) cam);
    else pG->pCamRoom = cam;
    CamCtrl.CoreDataRead((CameraDataHeader*) (pG->pArc->ofs_30 + (u32) pG->pArc));
    CamCtrl.roomInit();
    View.roomInit();
    return true;
}

// ---- trace ----
static u32 fbits(f32 f) { u32 u; __builtin_memcpy(&u, &f, 4); return u; }

static void put_hex(char* out, char kind, unsigned v)
{
    static const char hex[] = "0123456789ABCDEF";
    out[0] = kind; out[1] = hex[(v >> 4) & 15]; out[2] = hex[v & 15]; out[3] = 0;
}

// The current motion as the archive slot it came from: Pxx (player archive), Wxx (weapon archive).
static void motion_id(char* out, const void* mot)
{
    const u32 a = (u32) mot;
    out[0] = '-'; out[1] = 0;
    if (!mot) return;
    if (pG->pPlayer) {
        const u32 base = (u32) pG->pPlayer;
        for (int i = 0; i < 0x100; i++)
            if (pG->pPlayer->ofs[i] && pG->pPlayer->ofs[i] + base == a) { put_hex(out, 'P', i); return; }
    }
    if (pG->pWep) {
        const PlArc* w = (const PlArc*) pG->pWep;
        const u32 base = (u32) w;
        for (int i = 0; i < 0x80; i++)
            if (w->ofs[i] && w->ofs[i] + base == a) { put_hex(out, 'W', i); return; }
    }
    out[0] = '?'; out[1] = 0;
}

struct Fnv {
    u32 h = 2166136261u;
    void word(u32 w) { h = (h ^ w) * 16777619u; }
    template<class T> void add(const T& v) { u32 w = 0; __builtin_memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4); word(w); }
};

static void trace_tick(unsigned t, const PADStatus& in)
{
    HostTickRecord r;
    __builtin_memset(&r, 0, sizeof r);
    r.t = t;
    r.button = in.button;
    r.sx = in.stickX;
    r.sy = in.stickY;
    cPlayer* p = pPL;
    if (p) {
        r.has_pl = 1;
        r.pos[0] = fbits(p->pos.x); r.pos[1] = fbits(p->pos.y); r.pos[2] = fbits(p->pos.z);
        r.ang[0] = fbits(p->ang.x); r.ang[1] = fbits(p->ang.y); r.ang[2] = fbits(p->ang.z);
        motion_id(r.mot, p->Motion.pMot);
        r.frame = fbits(p->Motion.Mot_frame);
        r.mstate = p->Motion.Mot_state;
        r.rno[0] = p->r_no_0; r.rno[1] = p->r_no_1; r.rno[2] = p->r_no_2; r.rno[3] = p->r_no_3;
        r.be = p->be_flag;
        // ps: the logic trace's discrete hash (logic_trace.cpp model_state): be_flag, stat, id, type,
        // Mot_state. psm: the same with be_flag 0x08000000 set (the draw pass's marker, left by the
        // old game's render between logic and the next record).
        Fnv d, dm;
        d.add(p->be_flag); d.add(p->stat); d.add(p->id); d.add(p->type); d.add(p->Motion.Mot_state);
        const u32 bm = p->be_flag | 0x08000000u;
        dm.add(bm); dm.add(p->stat); dm.add(p->id); dm.add(p->type); dm.add(p->Motion.Mot_state);
        r.ps = d.h;
        r.psm = dm.h;
    }
    const CameraParam& c = pG->Cam.param;
    r.cam[0] = fbits(c.pos.x); r.cam[1] = fbits(c.pos.y); r.cam[2] = fbits(c.pos.z);
    r.cam[3] = fbits(c.at.x); r.cam[4] = fbits(c.at.y); r.cam[5] = fbits(c.at.z);
    r.cam[6] = fbits(c.fovy);
    r.rng = host_rnd_state();
    r.rng_calls = host_rnd_calls;
    r.stub_calls = host_stub_calls();
    r.stub_hash = host_stub_hash();
    r.stub_names = host_stub_names();
    host_trace_write(&r);
}

int main(int argc, char** argv)
{
    if (!host_parse_args(argc, argv, &g_opt)) return 1;
    if (!host_parse_fixture(g_opt.fixture, &g_fx)) return 1;
    if (!host_open_outputs(&g_opt)) return 1;

    host_fp_init();
    host_arena_init();
    // Boot state the frame loop relies on (main.cpp systemScreenInit / systemWorkInit / systemStartInit,
    // game.cpp gameInit: the fields the player and camera read). debug_mode 0: release play (the
    // Dreamcast build clears the debug start main.cpp's systemWorkInit sets).
    ZNEAR = 100.0f;
    ZFAR = 1000000.0f;
    ORTHO_T = 240.0f;
    ORTHO_B = -240.0f;
    ORTHO_L = -320.0f;
    ORTHO_R = 320.0f;
    Screen.x = 0.0f;
    Screen.y = 0.0f;
    Screen.width = 512.0f;    // the Dreamcast log: "width = 512", "height = 448"
    Screen.height = 448.0f;
    pSys->brightness = 0x40;
    pSys->language = 1;
    pSys->region = 1;
    pG->language = 1;
    pG->debug_mode = 0;
    pG->game_mode = 5;
    pSys->key_type = 0;
    pG->mot_speed = 1.0f;
    pG->pl_type = 0;
    pG->pl_costume = 0;
    pG->room_id = (u16) g_fx.room;
    pG->stage_no = (u8) (g_fx.room >> 8);
    pG->room_no = (u8) g_fx.room;
    pG->Rno0 = 3;
    RndInit((u16) g_fx.seed);
    PlayerInit();   // player.cpp: weapon 2 / type 0, life, pl_flag
    pG->weapon_no = (u8) g_fx.weapon_no;
    pG->weapon_type = (u8) g_fx.weapon_type;
    CameraGameInit();
    View.gameInit(&pG->Cam);
    PadInit();
    if (!room_init(g_opt.tree)) return 2;

    if (g_fx.has_resume) {
        // Continue from a recorded state: position and yaw as recorded; the footwork routine (0/0) is
        // re-entered with its own "resume" path (pl_R1_Footwork: r_no_3 bit0 -> motionSet with hokan
        // x4FD and frame x4FC), so the next move() restarts the idle at that frame without a blend.
        cPlayer* p = pPL;
        p->pos.x = g_fx.resume_pos[0];
        p->pos.y = g_fx.resume_pos[1];
        p->pos.z = g_fx.resume_pos[2];
        p->pos_old = p->pos;
        p->ang.y = g_fx.resume_ang;
        p->r_no_0 = 0;
        p->r_no_1 = 0;
        p->r_no_2 = 0;
        p->r_no_3 = 1;
        p->x4FD = 0;
        p->x4FC = (u8) g_fx.resume_frame;
        if (g_fx.resume_clear_event) p->be_flag &= ~0x04000000u;
        p->matUpdate();
    }
    host_trace_header(&g_opt, &g_fx, HOST_FP_NAME);
    PADStatus none;
    __builtin_memset(&none, 0, sizeof none);
    trace_tick(0, none);   // t=0: the state after construction (startUp ran one move)

    bool rng_dropped = false;
    for (unsigned t = 1; t <= g_fx.ticks; t++) {
        host_stub_tick_reset();
        g_pad = pad_for(t);
        const Vec before = pPL->pos;
        const u16 rng0 = host_rnd_state();
        PadRead();
        pG->Frame_cnt++;
        // gameMainLoop (game.cpp), the hosted part, in its order
        UpdateNearClipDist();
        if (!(pG->Stop_flg & 0x10000000) && (pPL->be_flag & 0x20) &&
            (!(pG->Status_flg[1] & 0x10000000) || (pPL->be_flag & 0x800))) {
            pPL->move();
        }
        if (!(pG->Stop_flg & 0x4000000)) ObjMgr.move();
        CameraMove();
        // controls (each must make the comparison fail; PLAYS_RIGHT.md)
        if (g_opt.control == HOST_CTL_WALK_SPEED && pPL->r_no_0 == 0 && pPL->r_no_1 == 1) {
            // an engine whose walk covers k times the ground per tick
            pPL->pos.x = before.x + (pPL->pos.x - before.x) * g_opt.k;
            pPL->pos.z = before.z + (pPL->pos.z - before.z) * g_opt.k;
        }
        if (g_opt.control == HOST_CTL_DROP_RNG && !rng_dropped && t >= g_opt.tick && host_rnd_calls > 0) {
            // an engine that skips one generator call: the tick ends one draw short
            const unsigned n = host_rnd_calls;
            RndInit(rng0);
            for (unsigned i = 0; i + 1 < n; i++) Rnd();
            host_rnd_calls = n - 1;
            rng_dropped = true;
        }
        trace_tick(t, g_pad);
    }
    if (g_opt.control == HOST_CTL_DROP_RNG && !rng_dropped)
        host_log("control drop-rng: no generator call at or after tick %u (nothing dropped)", g_opt.tick);
    host_close_outputs();
    return 0;
}
