#ifndef RE4DC_SUBSCREEN_ACTOR_H
#define RE4DC_SUBSCREEN_ACTOR_H
#include "types.h"

// Actor-derived inputs only. Health, inventory, ammo and Status_flg stay live.
struct Re4dcSsActorView {
    u32 player_stat;
    u32 partner_stat;
    u8 partner_present;
    u8 partner_is_ashley;
    u8 partner_wait;
    u8 partner_move;
    u8 partner_routine0;
    u8 partner_routine1;
};

extern "C" {
int re4dc_ss_actor_view(Re4dcSsActorView* out);
int re4dc_ss_actor_has_partner();
int re4dc_ss_actor_is_ashley();
u32 re4dc_ss_actor_player_stat();
// Called only after original ItemMgr.use succeeded. Target0=player,1=partner.
void re4dc_ss_actor_reset(unsigned target);
}
#endif
