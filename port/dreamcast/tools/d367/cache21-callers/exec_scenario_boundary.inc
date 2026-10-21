// Project only the external scenario services; actual bracket bodies follow.
using u16=std::uint16_t;
struct HostTask { u8 flag{}; } host_task;
struct ScePrim { HostTask* task{&host_task}; } host_prim;
static ScePrim* SceCTask(){return &host_prim;}
struct Damage {u32 bits{};void set(int,u32 value){bits|=value;}void clear(){bits=0;}};
struct HostPlayer {Damage dmg;} host_player,*pPL=&host_player;
struct cSceSys {
    u8 task_kind_back{};unsigned event_start_cnt{},system_bak{},event_no_cut_back{};
    int pLadderTask{};Damage dmg;
    int checkCTaskRange(){return 1;}
} SceSys;
struct SceneManagerBoundary {
    void beginEvent(int){} void endEvent(int){} void beginEvent(){}void endEvent(){}
} EmMgr,ObjMgr,DmgMgr,LightMgr;
struct CockpitBoundary {void lifeMeterDisp(int){}} Cckpt;
struct IdBoundary {void dispSw(int,int){}} IdSys;
static unsigned start_calls,end_calls;
static void EffectEventDelete(){}static void SceKill(int){}static void PlEndCamera(){}
static void KeyStop(u32){}static void SndBlkStop(int){}static void ShadowMemClear(){}
static void SubScreenWait(int){}
struct ScenarioLogger {void err(int,int,const char*,...){std::abort();}} scenario_logger;
// The bracket's only log is the invalid unpaired-End diagnostic. Keep that
// explicit boundary without coupling to the later table fixture's logger.
#define pLog (&scenario_logger)
#include "exec_actual_scenario.inc"
#undef pLog
static void SceEventStart(int mode){++start_calls;actual_SceEventStart(mode);}
static void SceEventEnd(int mode){++end_calls;actual_SceEventEnd(mode);}
