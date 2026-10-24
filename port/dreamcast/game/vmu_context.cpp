// Observes recovered state on the game thread. Does not change simulation or saves.
#include "light.h"
#include "player.h"
#include "pl_npc.h"
#include "global.h"
#include "item.h"
#include "sscrn.h"
#include "room_data.h"
#include "vmu_context.h"

extern "C" void re4dc_vmu_publish(const re4vmu::Snapshot*);
namespace {
unsigned generation=1;
int radio=-1;
void* companion_instance;
void* companion_vtable;
re4vmu::Person companion_kind;
bool had_game;
unsigned last_frame, last_room, last_player;
re4vmu::Snapshot cached;
}
extern "C" void re4dc_vmu_companion(void* instance,int kind) {
    companion_instance=instance;
    companion_vtable=instance?*static_cast<void**>(instance):nullptr;
    companion_kind=kind==2?re4vmu::Ashley:kind==3?re4vmu::Luis:re4vmu::Nobody;
}
extern "C" void re4dc_vmu_invalidate() {
    ++generation;radio=-1;had_game=false;
    cached=re4vmu::Snapshot{};
    re4vmu::Snapshot empty={};empty.generation=generation;re4dc_vmu_publish(&empty);
}
extern "C" void re4dc_vmu_reset(){
    re4dc_vmu_invalidate();companion_instance=nullptr;companion_vtable=nullptr;companion_kind=re4vmu::Nobody;
}
extern "C" void re4dc_vmu_call(int no) {
    // ss_term.cpp partnerType: ops 0..13 Hunnigan; 14..18 Salazar;
    // 19..22 Saddler; 23 the final Hunnigan call (no glasses).
    int next=(no>=0&&no<=13)||no==23?no:-1;
    if(next!=radio)++generation;
    radio=next;
}
extern "C" void re4dc_vmu_snapshot() {
    re4vmu::Snapshot s={};s.generation=generation;
    bool valid=pG&&pG->Rno0==3&&pG->Rno1==0&&pPL&&RoomData.pSave;
    if(!valid){
        if(had_game){++generation;radio=-1;}
        had_game=false;s.generation=generation;re4dc_vmu_publish(&s);return;
    }
    // A restored earlier timeline and character/room switches cancel old visuals.
    if(had_game&&(pG->Frame_cnt<last_frame||pG->room_id!=last_room||pG->pl_type!=last_player)){
        ++generation;radio=-1;
    }
    had_game=true;last_frame=pG->Frame_cnt;last_room=pG->room_id;last_player=pG->pl_type;
    // The sub screen swaps the room heap. Never dereference pPL/pSUB/ItemMgr
    // there: hold the last coherent game snapshot, changing only call lifecycle.
    if(SubScreenWk.type){
        s=cached;s.generation=generation;
        s.call=radio>=0&&SubScreenWk.type==SS_OPEN_TERM&&!SubScreenWk.cancel;
        re4dc_vmu_publish(&s);return;
    }
    s.valid=true;s.generation=generation;
    s.player=pG->pl_type==0?re4vmu::Leon:pG->pl_type==1?re4vmu::Ashley:re4vmu::Nobody;
    s.hp=(s16)pG->pl_life;s.max_hp=(s16)pG->pl_life_max;
    if(s.player!=re4vmu::Nobody)s.condition=(re4vmu::Condition)pPL->getLifeLevel();
    s.call=radio>=0&&SubScreenWk.type==SS_OPEN_TERM&&!SubScreenWk.cancel;
    unsigned weapon=WeaponId2WeaponNo(ItemMgr.m_wep_id);
    s.ammo_kind=re4vmu::Hidden;
    // The portable VMU helper takes the original big-endian routine word.
    // Normalize the native four-byte union under the same audit switch as the HUD.
    if(re4vmu::ammo_visible(pG->pl_type,STAT_BE(pPL->stat),weapon)){
        // Match ItemMgr's explicit debug infinite mode without showing its sentinel 100.
        bool infinite=(s32)pG->Debug_flg[3]>=0&&(pG->Debug_flg[2]&0x00400000);
        s.ammo_kind=infinite?re4vmu::Infinite:re4vmu::Finite;
        s.ammo=ItemMgr.bulletNum();
    }
    if(pSUB&&pSUB==companion_instance&&*reinterpret_cast<void**>(pSUB)==companion_vtable){
        s.companion=companion_kind;
        // Luis has a different layout beyond cModel. Never call Ashley routines on him.
        if(s.companion==re4vmu::Ashley){
            s.companion_condition=SubCharGetCondition();
            // The source clears this per tick and sets it in actual capture handlers
            // (em10 TakeAway, em2b Catch), unlike generic damage/event routine 4.
            s.companion_help=(pG->Status_flg[2]&0x20000000u)!=0 || (s16)pG->ashley_life<=0;
        }
    }
    const u8* record=RoomData.getRoomSavePtr(0x104);
    bool injected=record&&(*reinterpret_cast<const u32*>(record+4)&0x40000000u); // Rsf bit 1
    const u8* suppressant=RoomData.getRoomSavePtr(0x325);
    bool suppressed=suppressant&&(*reinterpret_cast<const u32*>(suppressant+4)&0x80000000u); // Rsf bit 0
    s.infection=re4vmu::infection_stage(injected,pG->Scenario_flg[0],pG->Scenario_flg[1],suppressed);
    cached=s;
    re4dc_vmu_publish(&s);
}
