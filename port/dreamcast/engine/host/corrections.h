// corrections.h: the corrections and guards the engine builds the original code with (lane eng-fix1, H-026;
// docs/engine/CORRECTIONS_20261121.md). Included by host/e1_prelude.h (every hosted unit of every engine image) and
// force-included by the PC reference (hostref/Makefile, CORRECTIONS=1, the default). Not options: there is no way to
// turn them off in the engine build. CORRECTIONS=0 exists only as the reference's control build (hostref/svc/refctl.sh).
//
// The names are the old port's conditionals in src/ (a later lane writes these corrections into the source and deletes
// the conditionals). Each is tested only by the units named, so one definition for every unit is the release's
// per-unit value. Three corrections are per unit and live in game/hosted_corrections.mk instead: RE4DC_GAME (its
// blocks in game.cpp and r100 reach the old port's platform layer, and engine C++ includes this prelude too) and the
// route conditionals ROUTE_CH22 / ROUTE_CH23 (corrections in pl14 / em35 / em3b, route gating everywhere else).
#ifndef E1_CORRECTIONS_H
#define E1_CORRECTIONS_H

// ---- corrections: the original code made right on this CPU (little-endian SH-4) and compiler (GCC) ----
// em10.cpp EM_RTN / EM_RTN_SET: routine tests and writes on the named bytes r_no_0 / r_no_1, not the GameCube's
// big-endian stat word (needs RE4DC_GAME in em10, per unit).
#define RE4DC_GANADO_ROUTINE_BYTES 1
// em35.cpp: Mendez's routine word, the same byte order (needs RE4DC_GAME in em35).
#define RE4DC_EM35_ROUTINE_BYTES 1
// player.cpp STATDIAG names it; the swap itself is STAT_BE in e1_prelude.h (the reference: re4dc_prelude.h, from its
// own -DRE4DC_STAT_ROUTINE_BYTES, which its STAT_BYTES=0 control build sets to 0: that value is kept).
#ifndef RE4DC_STAT_ROUTINE_BYTES
#define RE4DC_STAT_ROUTINE_BYTES 1
#endif
// pl_sub.cpp SetSubDamage: Ashley's routine-4 handler stored explicitly (the PowerPC r4 register pin of setEmFunc).
#define RE4DC_SUB_EM_FUNC 1
// card.cpp: the save row's key count read at its low byte in this byte order.
#define RE4DC_SAVE_ROW_FIX 1
// ss_pzzl.cpp: the message fields through their members (GCC puts the vtable pointer first; fixed GameCube offsets).
#define RE4DC_SS_MSG_FIELDS 1
// id_sys.cpp: screen ID colours converted to bytes with saturation, as the GameCube's float-to-int conversion does.
#define RE4DC_ID_ALPHA_SAT 1

// ---- guards: tripwires against failures the old port had; counted in host/guard_hooks.cpp (E1 GUARDS), expected 0 ----
// types.h EM_OK / EM_MUST: a spawn that returned 0 is skipped (room code) or retried (bosses, the r11b boat).
#define RE4DC_EM_READ_RETRY 1
// r10c.cpp: a first villager retired by its own first move is treated as missing.
#define RE4DC_R10C_SPAWN_LIVE_GUARD 1
// r117.cpp: a church beam the effect system refused (NULL) does not stall the puzzle.
#define RE4DC_R117_EFFECT_FAILURE_SAFE 1

#endif
