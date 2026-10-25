// ACTOR_GANADO_PS2_STUMP (default off): the exact PS2 conversions of the infos em10 swaps in during play that the
// five-appearance Ganado cast has no row for: em10HeadSet's lost-head stump (mot[3]: BIN 475 / 447 / 479 / 483 / 460
// for appearances 0..4) and em10HandSet's hand poses 449 / 450 / 454 / 455 (lane stump17, 10-17; Codex 10-13 did
// appearance 2's stump only). Nine geometries, loaded from dc/native/ganado/ganado_var.re4gv (coarse_actor_owner_ganado.inc).
#pragma once
#ifndef RE4DC_ACTOR_GANADO_PS2_STUMP
#define RE4DC_ACTOR_GANADO_PS2_STUMP 0
#endif
// Immutable chunk IDs the stumps take after the fixed table (one per cast appearance).
#ifndef RE4DC_ACTOR_GANADO_PS2_GRIP
#define RE4DC_ACTOR_GANADO_PS2_GRIP 0
#endif
// ACTOR_GANADO_PS2_GRIP (lane purge-cast24 10-24): + the grip hands 451 / 456 (ps2_ganado_stump.py --grip): 11 geometries.
#define RE4DC_GANADO_STUMP_IDS ((9u+2u*RE4DC_ACTOR_GANADO_PS2_GRIP)*RE4DC_ACTOR_GANADO_PS2_STUMP)
// The grip knob's code sits in these macros (used on existing lines of coarse_actor_material.inc and
// coarse_actor_owner_ganado.inc, so a knob-off build is byte-identical):
//  RE4DC_GRIP_VARIANT_RUN(run): a grip hand planned from the variant package draws the appearance atlas (material 0),
//    not the source hand material;
//  RE4DC_GRIP_ORIGINAL_SKIP(role, bin): the grip hands 451 / 456 are package variants (the PS2 meshes), not the GC
//    extra chunks.
#if RE4DC_ACTOR_GANADO_PS2_GRIP
#define RE4DC_GRIP_VARIANT_RUN(run) ((run).immutable_asset_id>=kRe4dcGanadoStumpAsset && \
    (run).immutable_asset_id<kRe4dcGanadoStumpAsset+RE4DC_GANADO_STUMP_IDS)
#define RE4DC_GRIP_ORIGINAL_SKIP(role, bin) \
    if(((role)==2 || (role)==3) && bound && ganado_var::find(bound->appearance,(role),(bin))>=0)return nullptr;
#else
#define RE4DC_GRIP_VARIANT_RUN(run) false
#define RE4DC_GRIP_ORIGINAL_SKIP(role, bin)
#endif
#if RE4DC_ACTOR_GANADO_PS2_STUMP
// Fixed chunks 1..46 precede optional far chunks 47..66. The variants take the next nine IDs (package geometry k:
// kRe4dcGanadoStumpAsset + k; k = appearance for the five stumps); the registry and player costume/hand IDs follow.
#if RE4DC_CROWD_FAR
constexpr unsigned kRe4dcGanadoStumpAsset=67u;
#else
constexpr unsigned kRe4dcGanadoStumpAsset=47u;
#endif
#endif
