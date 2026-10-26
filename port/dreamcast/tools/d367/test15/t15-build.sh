#!/bin/bash
# t15-build.sh <arm>...: test 15 build arms (t15/int, 2026-10-15; scope C:\Game Dev\Emulators\TEST15-SCOPE.md) = the test 14
#   recipe (test14/t14-build.sh arm rP, final candidate source ba856017, image eb2bc4e4) + the test 15 knobs ($T15). Every
#   test 15 knob is default 0 in the Makefiles: with T15="" (arm kP) the play image must be byte-identical to test 14's
#   (objcopy -R .stack image eb2bc4e4).
# Arms: rP release play, rW warp, mW warp + MCHECK_LEONGC=1 TEX_CHECK=2 + the CAST-GC census, rT trace, kP knob-off play (= test 14 recipe,
#       identity vs eb2bc4e4), kW / kT knob-off warp / trace (the STRICT reference for rT).
# Env: T (tree, default /root/probe/lanes-20261015/t15int), K (logs, default /root/probe/lanes-20261015/t15k), LP (label
#      prefix, default t15i), T15 (test 15 knobs, default T15REC), XON (extra knobs, test only), PAD_T / PAD_K.
# Data set: T15_DATA in test11/t11-fix.py (= T14_DATA + cast15).
# --- the test 14 recipe (copied from test14/t14-build.sh at b1518aa4; keep in step) ---
set -u
K=${K:-/root/probe/lanes-20261015/t15k}
T=${T:-/root/probe/lanes-20261015/t15int}
export SOURCE_DATE_EPOCH=1760000000
F="PACE_DEBUG=1 ROUTE_CH13=1 ROUTE_CH21=1 SBB_STUB=1 PVR_READY_STRICT=1 ACT_CAP=0 PS2_INTERIOR_ACTORS=2 GAME_ATLIST_OVERFLOW=1 GAME_ATLIST_512=1 LEON_NATIVE_PIPE=0 LEON_FACE_LAZY=0 NATIVE_LASER=1 ACTOR_GANADO_SOURCE_LIGHT=0 PRIM_CAP_R10B=327680"
LOOK="EFFECT_PS2_TOGGLE=1 LOOK_TOGGLE=1 FILTER00_DC=1 CHARBAKE_TOGGLE=1 CHARBAKE_HAIR=0"
PS2="PS2_LEON=1 PS2_LEON_DIR=/root/re4data/private/ps2leon-rig-20261026 ACTOR_PL08_PACK=1 PS2_GANADO=1 PS2_GANADO_DIR=/root/probe/lanes-20261010/ps2cast-all-assets/pg5 PS2_GANADO_F=1 PS2_GIGANTE=1 PS2_DELLAGO=1 PS2_VERTEX_ALPHA=1"
P2="MOVIE_DISC_QUIET=1 EFFECT_HAZE_LEAN=3 EFFECT_HAZE_LEAN_TOGGLE=0 RENDER_OPTION=1 PS2_GANADO_LIT=1 CAST_MIPMAP=1 PS2_CROW=1 PS2_ANIMALS=1 PS2_WOLF=1 HEAP4_PARTS_RESERVE=1 DVD_READ_SAFE=1 LAKE_RIPPLES=1 VGA_SOFT=1 LETTERBOX_CLIP=1 PS2_PT_CUTOUT=1 PACE_VMU=1 PACE_VMU_GPU=1 UI_FRAG_RESERVE=1"
T9K="DOOR_FREEZE=1 LOAD_INDICATOR=1 VMU_CONTEXT=1 OPTION_ROW_STYLE=1 PT_BLEND_FIX=1 MODEL_STREAM_FIX=1 SS_MENU_ANIM_RT=1 PS2_ENEMY_RULES=1 ACT_CAP_TABLE=1 RENDER_QUALITY_ONLY=1 RESET_HEAP_FIX=1"
HANDS="LEON_HAND_POSES=1 LEON_HAND_PACK=1 LEON_SKIN_SLOTS=1"
T11REC="PS2_R100_SMX=1 PS2_R100_TR4=1 LAKE_ZBIAS=1.001 WORLD_HOLE_FIX=1 SPEED_VMU_OFF=2 TEX_REF_SELFKEY=1 MOVIE_HEAP_PREFLIGHT=1 PS2_FX_ROOMS=1 PS2_FX_STAGE1=1 PS2_FX_POPULATION=1 PS2_FX_ADDITIONS=1 PS2_FX_ROOMS_EXT=1 EFFECT_TORCH=1 RAIN_PS2=1 ACTOR_PROBE_LIGHT=1 LEON_SOURCE_LIGHT=1 LEON_LIGHT_HEADROOM=1 PS2_ENEMY_ROOMS=0x3f MV_SHADOWS=1"
T12REC="UI_SOURCE_LRU=1 HW_FOG_HAZE=1 FX_SPRITE_TRIM=2 TEX_PAL4_ALPHA=1 FX_PS2_PACK=1 FX_FLIPBOOK=2 R101_ALIVE_CAP=6 TEX_WRAP_SAFE=1 PS2_CAST_MERCHANT=1 ACTOR_GANADO_APP0_GRIP=1 RENDER_FSAA=1 GC_STUB_SKIP=1 OWNER_SETUP_LEAN=1 TEX_IDENT_LEAN=1 PS2_WORLD_LEAN=23 PS2_STRIP_GROUPS=1 PS2_ROOM_PIN=1 LEON_LIGHT_FILL=45 VRAM_ROOM_LOG=1 EFM_PS2_CUT=1 STATIC_OBJ_BATCH=2 TEX_META_EVICT=1 PRELOAD_LARGE_FIRST=1 ROOM_RESIDENT=1 SS_FREEZE_RESERVE=1 DCINV_PURGE=1 MAPLE_RECV_PURGE=1 ARENA_FIT_KOS_BYTES=196608"
T122="RETIRE_KOS_FLOOR=65536"
# Test 13 knobs (TEST13-SCOPE.md items 1..6; item 7 is a tool):
#   6 ROOM_CHANGE_EVICT=60 (T13_6; lane t13-rce bdb2b431; render only, needs TEX_KEEP=1: LRU order across a room change,
#     the old room's leftovers not drawn in its last 60 frames are evicted at the next room's first preload pass)
#   1 STATIC_OBJ_BAKE=1 + PS2_PLACE_GATE=1 (lane crowd12-t13 ce0b7a82; render only; data bake13), and
#     STATIC_OBJ_BATCH_WORDCMP=1 (the same branch's 5149da0a word compare for STATIC_OBJ_BATCH, which was not behind a knob
#     and changed the 12.2 image; the RC put it behind this knob so that kP stays identical; exact, render only)
#   3 PS2_ASHLEY=2 PS2_ASHLEY_ROOMS=1 (lane ps2cast3 d940cbc0; render only; data ashley13; user choice B: PS2 model, rest face)
#   4 PS2_CH1_ENEMY=1 (lane alivecap-1015 659f2280; GAMEPLAY by design: PS2 chapter 1 enemy rules + ALIVE_CAP=6 +
#     ALIVE_CAP_PARK + R101_CAP_WAVES; gated by the decisions check of ALIVECAP-20261015.md, not by STRICT)
#   5 GAME_LQ_MEMO=1 (exact, logic; STRICT), LEON_FACE_LAZY=1 (exact, render), PS2_AREA_HIDE=1 (r107, render only)
#     (the GC render census removals of item 5 were never built: no knob)
#   2 objs13 is data only (objs13d)
#   8 UI_FRAG_WINDOW=3 (user pull-in 10-15 under release rule 1; t11 lane vr knob + the RC's =3, render only): an upload of
#     128 KiB or more refused for fragmentation releases one idle window of the size instead of LRU evictions; fixes the
#     r105 chapter 1-2 results picture (eaf5d457 495x150, "no contiguous block", 120-frame latch) that objs13's r105
#     layout exposed. =1 (all sizes) dropped r100 s20 effect sprites (H2 guard_p 0 -> 11/15); =3 proof 10-15: r105 0
#     no-contiguous, loaded once; H2 r100 guard_p 0 (arms t13w0rW / t13w3rW / t13y1rW). =2 stays out (test 11 crash).
T13R="STATIC_OBJ_BAKE=1 PS2_PLACE_GATE=1 STATIC_OBJ_BATCH_WORDCMP=1 PS2_ASHLEY=2 PS2_ASHLEY_ROOMS=1 GAME_LQ_MEMO=1 LEON_FACE_LAZY=1 PS2_AREA_HIDE=1 UI_FRAG_WINDOW=3"
T13G="PS2_CH1_ENEMY=1"
T13_6=${T13_6-ROOM_CHANGE_EVICT=60}
T13REC="$T13R $T13G $T13_6"
T13=${T13-$T13REC}
# Test 14 knobs (TEST14-SCOPE.md rows; all render, I/O or exact: STRICT rT vs kT, identity kP vs test 13):
#   1  (knobs out, see below) SS_HOLD_RESTORE=1 CORE_PIN=1 + data res14 (lane t14-r101res; VRAM rule: r101 resident list complete, the sub screen
#      hold restores the evicted room keys at the close, the HUD core set is never evicted)
#   17 MOTION_COLD_POOL=262144 + data res14r3 (lane t14-r103res c9dc83ed: cold motion keys in heap 4 instead of slab
#      eviction; the r103 resident list)
#   15 G1_DIAG_INLINE=1 G1_FP_UNSIGNED=1 G1_PRESORT_LAZY=1 (lane g1parts 7979c550; exact; PRESORT_LAZY needs
#      PVR_READY_STRICT=1, which F sets)
#   -  ACTOR_NO_CLEAR=1 (lane memlay d270ca82; render only; T14_NC, in only if its gates pass on the merge). Row 14
#      MEMSET_LEAN stays 0 (ACTOR_NO_CLEAR covers its clear).
#   11/12 subset: DISC_COMPAT=1 DISC_READ_FALLBACK=0 (lane discread 2cfb535d; forces KOS_DISC_FIX=1: the KOS GD-DMA
#      completion fix + fs_iso9660 mutex; the timing-neutral subset, STRICT in Flycast). Product number unchanged (T0000).
#   18 GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1 (lane sh4zam-direct e4e3336c; render only, not bit-exact: STRICT logic, the
#      look accepted by the user 10-15)
#   Row 1's knobs are OUT after the RC gates on the intermediate candidate (bb2c4c51, 10-15): CORE_PIN=1 kept the 4 HUD
#   keys pinned through r105's chapter 1-2 results screen, which then found no contiguous 512 KiB block for its 631x169
#   picture (texchk FAIL, crash suite ch12) and refused 63-102 effect sprites (guard_p; test 13: 8). SS_HOLD_RESTORE=1
#   alone matched test 13 there (8) but restores nothing without CORE_PIN (lane note: the HUD is hidden before the
#   post-bell call); without both r105 refuses 0. Row 1's data (the r101 list in res14r3) stays: r101 bell 0 uploads
#   after the preload (test 13: 4).
T14_1=${T14_1-}
T14_18="GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1"
T14_17="MOTION_COLD_POOL=262144"
# RC fix 10-15 (coordinator option b): ROOM_REENTRY_EVICT=1, the r101 death / Continue re-entry fragmentation (crash death)
T14_RE=${T14_RE-ROOM_REENTRY_EVICT=1}
T14_15="G1_DIAG_INLINE=1 G1_FP_UNSIGNED=1 G1_PRESORT_LAZY=1"
T14_NC=${T14_NC-ACTOR_NO_CLEAR=1}
# T14_DISC="" (env): the variant without the disc items (KOS_DISC_FIX=0), ready in case the console verdict on
# KOS_DISC_FIX goes against it (LinkOrder2 console halt 10-15, "invalid prepared enemy motion archive", under analysis).
# Test 15 disc reads (user decision 10-16, "option A"; lane plainread16): stream (fast) reads as before, and on the first
# stream or sector read that fails, times out or does not land, an automatic switch to plain bounded sector reads for
# the rest of the session (DISC_READ_FALLBACK=3; DMA, DMA after a bounded drive re-init, then PIO). DISC_LAND_SPIN_MS=20
# only acts after the switch (yield while a plain read's DMA lands; size-scaled bound). The fast path is STRICT against
# test 14's T14_DISC="DISC_COMPAT=1 DISC_READ_FALLBACK=0". Plain reads from the start: T14_DISC="DISC_COMPAT=1
# DISC_LAND_SPIN_MS=20 STORAGE_BOUNCE_ALIGNED=1 TEX_PACK_WINDOW=128" plus data texord16 (lane plainread16 52868e97).
T14_DISC=${T14_DISC-DISC_COMPAT=1 DISC_READ_FALLBACK=3 DISC_LAND_SPIN_MS=20}
T14REC="$T14_1 $T14_17 $T14_15 $T14_NC $T14_DISC $T14_18 $T14_RE MEMSET_LEAN=0"
T14=${T14-$T14REC}
# Test 15 knobs (TEST15-SCOPE.md rows and merge log). Merged with default 0; in T15REC only once their lane reports gates passed.
#   2  GC_CENSUS_TRIM=1 (lane t2exact 4633156c, A2b; exact: GX state getters inline, coarse hook lookups by range)
#   7  PS2_CAST_CH1=1 PS2_CAST_BOAT=1 ACTOR_PALETTE_BANK=40 NATIVE_MODEL_REGISTRY_POOL=1 (lane ps2cast14 b00f9a43; render
#      only; data cast15; r117 PS2 zealot pool chosen by the user 10-15)
#   R  KOS_SBRK_LAST_PAGE=1 (lane ramreclaim 464aada4; exact, +4,096 B usable KOS; gates: identity, squeeze 10/10, STRICT
#      fight/bell/door103, align 0; RAM-BUDGET-20261015.md). ARENA_FIT_KOS_BYTES stays 196608 (the +16 KiB waits on the
#      heap-4 reclaims: it costs the r100 s30 movie heap 4). KOS_CENSUS=2 merged as a diagnostic (default 0).
#   Merged, default 0, NOT in T15REC yet (waiting on their lanes' gates / decisions):
#     -  SG_SELECT_LEAN (lane t2exact 866edc60); HOT_COLD_SPLIT (B5, d11ac47e: layout, off unless console A/B); PS2_PVS
#     4  GANADO_LOD=2 (lane leonlod e9fb332f + fa799f12 cutscene full models; needs PS2_GANADO=1). LEON_LOD stays 0
#        (user 10-15 evening: Leon keeps the default full model)
#     10 LOGIC_WASTE / LOGIC_APPROX_MASK (lane logicwaste 1d2e2f38)
#     -  SUB_EM_FUNC, MOVIE_POLL_SETTLE (lane ch22-1014 9b401bc0 / 4835a107; stability fixes, on after their STRICT gates)
#   Dropped: UI_OT_CACHE (reverted 35be27e8). Not merged: LINK_ORDER (console crash under investigation), worldlod,
#   SKIN_SH4ZAM (lane sh4zam, no commit yet).
T15_2="GC_CENSUS_TRIM=1"
T15_7="PS2_CAST_CH1=1 PS2_CAST_BOAT=1 ACTOR_PALETTE_BANK=40 NATIVE_MODEL_REGISTRY_POOL=1"
T15_R="KOS_SBRK_LAST_PAGE=1"
#   4  GANADO_LOD=1 GANADO_LOD_LEVEL=2 (g70; lane leonlod fa799f12, lean gates 4988dacb; render only; cutscenes switch to
#      level 0 by themselves). LEON_LOD stays 0. Needs PS2_GANADO=1 and the package on the disc: data set glod
#      (dc/native/ganado/ganado_lod.re4gl, sha256 46566154; in T15_DATA). Check the candidate's boot log for
#      "GANADOLOD level=2 name=g70" in r101 and "level=0" at the r101s30 event. _end +928 B.
T15_4="GANADO_LOD=1 GANADO_LOD_LEVEL=2 GANADO_LOD_PACK=/root/probe/lanes-20261015/t15k/data/glod/ganado_lod.re4gl"
#   F  SUB_EM_FUNC=1 MOVIE_POLL_SETTLE=1 (lane ch22-1014 9b401bc0 / 4835a107, cherry-picked fc30290b / 9a0b9ea7; fix-only):
#      STRICT vs kT stop 2000 on h2 fight / r101 bell / door103 (t15srT, evidence t15int-20261015 st{A,B,C}); s40 movie
#      1175/1175 both arms.
T15_F="SUB_EM_FUNC=1 MOVIE_POLL_SETTLE=1"
#   H  HUD fix (t15/hud, CORE_PIN=2 + SS_HOLD_RESTORE=1 + data res16): merged default 0, gated (door103 vram PASS, r105 =
#      control, STRICT door103). ON (coordinator 10-15): T15_H, data res16 in T15_DATA.
T15_H="SS_HOLD_RESTORE=1 CORE_PIN=2"
#   10 LOGIC_WASTE=1 LOGIC_WASTE_MASK=0x02 (lane logicwaste befad291, keepers aaa020b3: Ps2fxClass verdict cache; exact, STRICT
#      fight/bell/H2/door103; -0.23 ms cross MODELLED; _end +1,824 B). LOGIC_APPROX_MASK (Leon cloth 30 Hz) stays 0 until the
#      user OKs its motion still pair.
T15_10="LOGIC_WASTE=1 LOGIC_WASTE_MASK=0x02"
#   O  OVL_ID_GUARD=1 (daac0cf2; robustness: a route overlay from another build stops cleanly at its load). STRICT h2/bell/door103
#      vs kT stop 2000 (t15orT); deliberate mismatch stops cleanly (og3-r118-mm).
T15_O="OVL_ID_GUARD=1"
#   L  PS2_CAST_MERCHANT_LIT=1 (ps2cast ca6257d2; user 10-16 "Lit for merchant"; render only; bit 32 of RE4DC_NMR_SOURCE_LIGHT;
#      needs PS2_CAST_MERCHANT=1, in T12REC). No extra data files.
T15_L="PS2_CAST_MERCHANT_LIT=1"
# lane audio16 (eaf9c6d0, 10-16): ch1 sounds; MUST ship with data snd16 (45-entry aica_str.dat; with 32 every stream goes silent)
T15_S="AICA_STR_ENT_MAX=48"
# lane s30movie16 (50a4b793, ChatGPT design bce6fd98 + a9533269): r100 s30 cliff movie plays (retained-world loan, 13-slot ledger)
T15_M="MOVIE_WORLD_ARENA=1 MOVIE_WORLD_ARENA_S30=1"
# lane doorpause16 (cfa76c2e, 10-16): skip reading the zero padding after converted sound banks (-0.8 s per door at 2 MB/s, exact)
T15_D="SND_PAD_SKIP=1"
# lane ganlit16 (de25aabe, user 10-16 "Option a for lighting"): villagers take their colour from the room's lights through
#   the per-actor probe, still flat (one colour per part). ACTOR_PROBE_LIGHT 1 -> 2 for the whole recipe (overrides T11REC's =1:
#   the last assignment on the make line wins); Leon is drawn exactly as with =1 (probe_eligible only adds Ganados).
#   NEAREST=0 = no per-vertex Ganado light (option (a), -0.08 ms cross MODELLED). Render only. No data.
T15_G="ACTOR_PROBE_LIGHT=2 GANADO_LIT=1 GANADO_LIT_NEAREST=0"
#   V  VIEW_DIST_OPTION=1 (lane viewdist16; render only, user-approved player option, user 10-16 "the distance reduction can
#      go in on its own"): Options row "View distance" Full / Near / Short (25 / 18.75 / 12.5 m, the benchmark sweep rows;
#      console -3.9 / -7.9 ms CPU at the cross), fog to 100 % at the cut, this boot only; no fog inside houses (indoor
#      effect areas), r10b / r11a / r11b never cut (kViewRoomMin). Gates in C:/Flycast-Evidence/re4-dreamcast/viewdist-20261016.
#      T15_V="" builds the control without it.
#      Test 19 on (lane bootdef19, user 10-19 "a middle ground for draw distance"): VIEW_DIST_BOOT=1, every boot starts
#      at Near (18.75 m); the lakes stay uncut (kViewRoomMin), so LAKE_FAR's 45 m lake view is unchanged.
#      Test 19 on (lane qws19, user 10-19 "I also want to integrate the weapon switch"): QUICK_WEAPON=1, hold X + D-pad to
#      equip a weapon by kind (quickweapon.mk). Logic only when the chord is pressed; QUICK_WEAPON_POC_KIT never goes here.
#      Also ACTOR_PLAN=1 (lane actorplan19, character setup memoised, render only, approved for Test 19).
#      Test 19 on (lane manual19, issue #44): MANUAL_PACK_PROBE=1, the manual page checks look in dc/tex.pak first, so the
#      Dreamcast controller pages show instead of the GameCube ones (render only).
#      Test 19 on (lane scenery19, P2 stage 1): SCENERY_CHUNK=1, the PS2 world pass selects then emits (exact, render only).
#      Test 19 on (lane scenery19): SG_SELECT_LEAN=1 with SCENERY_CHUNK=1 (exact; STRICT bell/door103, KOS, stills x4;
#      r101 scenery 11.09 -> 10.76 ms MODELLED).
#      Test 19 on (lane chardraw19, P2): CHAR_CHUNK=1, every skinned model on the new draw path (exact: the
#      CHAR_CHUNK=2 word compare had 0 mismatches for Leon, Ganado, corpse, Ashley, Luis, merchant, riders and
#      three bosses; KOS 48 KiB 10/10, fight headroom 6,104 B).
#      Test 19 on (user pull-in 10-19, lane engine19): ENEMY_VIS_CULL=1, the wall check (a villager fully hidden
#      behind a wall is not drawn; logic, sound and collision unchanged).
#      Test 20 line (10-20): CHAR_CHUNK off (measured slower, as in 19.1); SCENERY_DEDUP off (measured slower) + SCENERY_UNIT_CONCAT=1 +
#      SCENERY_SCREEN_MEMO=1 (measured, exact) + SCENERY_FAR_LOD=4 (approximation, look ~1% distant pixels, -0.7 ms).
#      Test 20 (10-20, lane logic-lod): LOGIC_LOD_EM=2 LOGIC_APPROX_MASK=0x01, far/off-screen Ganados + animals at half rate,
#      Leon jacket cloth half rate (gameplay gate: kills, doors, cutscenes, cap identical; farm fight -4.9 ms MODELLED).
#      Test 20 (10-20, lane logic-lod): ESP_TYPE_CAP=16 (at most 16 drawn effects per id from enemies/animals/objects;
#      farm fight -3.2 ms) + ESP_CUT_EARLY=1 (exact, never-drawn mist/haze skip the transform).
#      Test 21 (10-20, lane pace20, user "yes please"): PACE_STEADY=1 adds STEADY to Options > Frame pacing; the
#      default stays Fast (players opt in). Knob-off identity fd597042; farm Fast vs Steady same kills.
#      Test 21 (10-20, Codex boss21 + lane motion21): MOTION_PRESSURE_BACKING=1 MOTION_RESERVE_PACK=1 pack motion
#      clips into the reserved slabs (Codex r100 ambush: 703 loads/682 evictions -> 21..24 loads, 0 evictions).
T15_V=${T15_V-VIEW_DIST_OPTION=1 VIEW_DIST_BOOT=1 QUICK_WEAPON=1 ACTOR_PLAN=1 MANUAL_PACK_PROBE=1 SCENERY_CHUNK=1 SG_SELECT_LEAN=1 ENEMY_VIS_CULL=1 SCENERY_UNIT_CONCAT=1 SCENERY_SCREEN_MEMO=1 SCENERY_FAR_LOD=4 LOGIC_LOD_EM=2 LOGIC_APPROX_MASK=0x01 ESP_TYPE_CAP=16 ESP_CUT_EARLY=1 BODY_CORPSE=1 BODY_ROUTE=1 RIGID_CHUNK=1 CHUNK_SUBMIT=1 PACE_STEADY=1 MOTION_PRESSURE_BACKING=1 MOTION_RESERVE_PACK=1}
# lane resident16 (10-16): the room preload runs again when SS heap 11 closes (chapter title / results / save screens), so
#   r105 after the chapter 1-2 save screen loads its set back in one pass instead of 81 disc reads in play. Render only.
T15_P="SS11_PRELOAD=1"
#   W  WATER_PS2=1 (lane water16; render only, user 10-16 "ok option a for water"): chapter 1 room water drawn as the PS2
#      does (stacked scrolling / animated planes, KI #26 / #19) in r107 r108 r10a r11a r10b r11b (WATER_PS2_ROOMS default 0x3f; r10b / r11b
#      added 10-16 by lane water16b after the vq16w VQ set). Data: vq16w + water16i in T15_DATA (water pictures preloaded).
#      Gates in C:/Flycast-Evidence/re4-dreamcast/water-20261016. T15_W="" builds the control without it.
T15_W=${T15_W-WATER_PS2=1}
#   WV (removed 10-16, user: "use the previously optimized r101; we will come back to improving the world; we need to
#      use Blender and more sophistication"): WORLD_VERT is off, r101 draws the test 14 world (bake13, T15_DATA without
#      wt16r101). The reduced sets lost structure (tools/d367/worldtest16/lostpart: test 15 world32 1657 flagged pieces,
#      C16 1511). Any reduced world comes back only through the lost-part gate (WORLD-NEXT.md).
#   T  FOLIAGE_TRIM=1 FOLIAGE_OPTION=1 (lane mist16; user 10-16 "I approve near", "ship with full near and off then log the
#      issue"; render only): the chapter 1 outdoor brush / leaf cards in the punch-through list to 12 m (Near, the boot
#      default), Options row "Foliage" Full / Near / Off, this boot only. Off leaves out the listed card keys only (85128754).
#      Gates in C:\Flycast-Evidence\re4-dreamcast\mist-20261016. T15_T="" builds the control without it.
#      Test 19 on (lane bootdef19, user 10-19 "default foliage to off"): FOLIAGE_TRIM=2, every boot starts at Off; the
#      Options row still offers Full and Near.
T15_T=${T15_T-FOLIAGE_TRIM=2 FOLIAGE_OPTION=1}
#   FS FAR_SHELL=1 (lane farshell16; render only, needs T15_V; user 10-16 "short + far shell looks good", "short shell + half
#      vertices"): at Short (12.5 m) the PS2 world's opaque pass stops at the cut and the room's far shell
#      (dc/native/rXXX/far-shell.fsh, data fsh in T15_DATA: r100 r101, ~3,000 triangles each) is drawn beyond it with
#      Full's fog, PT / TR world passes and actors (docs/lanes/farshell16.md). Near and rooms without a shell file keep
#      the plain cut. T15_FS="" builds the control without it. Residency (lane farshell17, test 17; test 16 shipped
#      without it): the shell is in heap 4 only at Short, lent to every route movie, and given back when heap 4 runs
#      short (docs/lanes/farshell17.md).
T15_FS=${T15_FS-FAR_SHELL=1}
#   RS RADIO_SUB_RT=1 (lane radiosub16; test 16 scope, after the t15/rc freeze; test 14 console report "the radio call
#      subtitles are very slow"): the codec call's subtitle pages follow the voice's clock (KOS timer from the moment the
#      AICA stream starts sounding, GameCube 30 Hz ticks) instead of drawn call frames. UI only (the game is stopped under
#      the sub screen). T15_RS="" builds the control. Gates in C:/Flycast-Evidence/re4-dreamcast/radiosub-20261016.
T15_RS=${T15_RS-RADIO_SUB_RT=1}
#   HZ HAZE_SPRITE_CUT=1 (lane nohaze16, test 15.1; user 10-16 "i don't think we need those sprites at all", "let's make off
#      really mean off"; render only): no haze / mist sprite is drawn in any room at any Foliage setting (the camera haze
#      around Leon, the Esp48 mist sheets, the r118 / r11c PS2 haze additions); the distant haze stays as the fog table.
#      Ships with the Foliage Off fix (85128754). T15_HZ="" builds the control without it. Docs: docs/MIST_CUT.md.
T15_HZ=${T15_HZ-HAZE_SPRITE_CUT=1}
#   PB PRIM_BUF_KB=432 (lane cast16, test 17; size only, every room): the room primitive buffer asks at most 432 KB of
#      heap 4 (GC room values up to 655,360 B in r11f). Worst chapter 1-2 per-frame peak 294,752 B (r11c siege, PRIM_WATER:
#      r11f 273,312, r11e 284,448, r101 bell 268,768, r100 235,808) x 1.5; overflow 0 in all. r11f then keeps 182,432 B
#      of heap 4 free with the full PS2 Ashley + g70 Mendez (was: Ashley failed Mendez's parts). T15_PB="" builds the control.
T15_PB=${T15_PB-PRIM_BUF_KB=432}
#   SO STAGE_OVL=1 SS_POOL_TOP=1 (lane ch3found16, test 17; heap only): stage modules load as overlays in heap 3 beside
#      the room REL, and the sub screen high pools go to the top of heap 4. Restores the 4 spawns h2 lost at tick 658 on
#      the ch2 recipe (GC and test 16 spawn them all). T15_SO="" builds the control. Docs: CH3-FOUNDATIONS-20261016.md.
T15_SO=${T15_SO-STAGE_OVL=1 SS_POOL_TOP=1}
#   AC ANIMALS_OFF=1 + cap 4 (test 16.1 hotfix and test 17, user 10-17: "Get rid of them asap" (the ambient farm animals: cows,
#      chickens, the r103 farm dog; no eggs from chickens) and "lets do cap 4 for the zombies": at most 4 Ganados alive
#      at once in every room, more arrive as they die; the documented cap exceptions stay). CHANGES GAMEPLAY by design,
#      gated by gameplay equivalence (doors, kills, waves, triggers, room clears), not STRICT. ALIVE_CAP=4 replaces
#      PS2_CH1_ENEMY's default 6 and R101_ALIVE_CAP must equal it. T15_AC="" builds test 16 (cap 6, animals).
#      ANIMALSOFF-20261017.md.
T15_AC=${T15_AC-ANIMALS_OFF=1 ALIVE_CAP=4 R101_ALIVE_CAP=4}
# T15_VP (lane vram101, test 17, 10-17): VRAM_PAGES_VQ_ONLY=1, only VQ textures start on a 2 KiB page (render only;
#      r101 preload 22 evictions -> 0, largest free block 10 KB -> 58 KB). Data T17V_DATA. T15_VP="" builds without it.
T15_VP=${T15_VP-VRAM_PAGES_VQ_ONLY=1}
# T15_DY (lane cast16, test 17, coordinator 10-17): NATIVE_MODEL_REGISTRY_DYING=1, a dying Ganado-class enemy keeps its PS2 /
#      registry model through the death fade (G1 ticket: source FIFO position, TR list, source alpha) instead of the
#      GameCube model (r101 near-kill rig: 14 GC fade frames -> 0, 14 native fades). Render only: STRICT h2 / bell60 /
#      door103 / r101 near-kill vs knobs off, KOS squeeze 10/10, s30 heap_before 1,065,248 (-4,096 B). T15_DY="" builds
#      without it. Release check: a near-fade still pair (TEST17-SCOPE.md).
T15_DY=${T15_DY-NATIVE_MODEL_REGISTRY_DYING=1}
# T15_TP (lane cast16, test 17): TEX_PKG_SKIP=1, the room preload skips the GameCube TPLs that a room package's role rows
#      replace with their own atlas (a source draw still loads one on first sight). VRAM only: r11f free / largest
#      382,080 / 331,776 -> 543,872 / 497,664 (47 skips), r101 near-kill 137,376 / 18,432 -> 155,808 / 36,864, r103 no-op;
#      CAST-GC / TEXCHK / LEON-GC unchanged. T15_TP="" builds without it.
T15_TP=${T15_TP-TEX_PKG_SKIP=1}
# T15_GD (lane gatlas17, test 17, 10-17; user: "We can lower ganado texture detail if that will make the room work"):
#      GANADO_ATLAS_DROP=3, in r101 only the PS2 cast's em15-00 and em15-03 512x512 Ganado atlases load without their
#      top mip level (256x256 with mips, 2 x 65,536 B of VRAM). The smallest cut that keeps all of r101's preload picks
#      resident (pass 4 full=0: 20 more pictures, 65f9e9a9 among them), 0 loads in play at the cap-4 cross fight and
#      the bell gate, and the largest free block >= 20 KB (38,912). Render only. GATLAS17-20261017.md. T15_GD="" builds
#      without it.
T15_GD=${T15_GD-GANADO_ATLAS_DROP=3}
# T15_ST (lane stump17, test 17, coordinator 10-17: no GameCube fallback): ACTOR_GANADO_PS2_STUMP=1, every cast
#      appearance's lost-head stump (BIN 475 / 447 / 479 / 483 / 460) and the hand poses 449 / 450 / 454 / 455 draw PS2 from
#      the disc package dc/native/ganado/ganado_var.re4gv (data set stump17, read into a heap-4 room cell when a room first
#      draws one, freed at room leave, lent to route movies). CAST-GC head-shot rigs r101 / r103 / r200 0 GC; s30 340/340,
#      heap_before -4,096 B (one ARENA_FIT step); KOS 48 KiB 10/10. docs/lanes/stump17.md. T15_ST="" builds without it.
STUMP17D=${STUMP17D:-/root/re4data/private/stump17-20261017}
T15_ST=${T15_ST-ACTOR_GANADO_PS2_STUMP=1 ACTOR_GANADO_PS2_STUMP_DIR=$STUMP17D}
# T15_PG (lane farmprop17, test 17, coordinator 10-17: on game-wide): PROP_GATE=1, a lazily skinned room object (cObj)
#      wholly beyond the native actor fog gate's cull depth skips its part walk instead of preparing each part's skinned
#      frame only to cull it (trans.cpp propGate; r103 farm props ~3 ms/picture Flycast). Render only, exact (=2 check:
#      every part of a gated model is culled by the fog gate). T15_PG="" builds without it.
T15_PG=${T15_PG-PROP_GATE=1}
# T15_FN (lane lake17, test 17, 10-17; tester "foliage Near and Off look the same"): FOLIAGE_NEAR_FIX=1, Near (the approved
#      boot default) draws the cut-out cards of translucent-only placements again: the pass-1 placement scan skipped them,
#      so they were drawn in neither pass. Render only; needs T15_T. Evidence C:/Flycast-Evidence/re4-dreamcast/lake17-20261017
#      (stills/fr100-sheet.png). T15_FN="" builds without it.
T15_FN=${T15_FN-FOLIAGE_NEAR_FIX=1}
# T15_LF (lane lake17, test 16.4 release values, user 10-17): LAKE_FAR=45000 LAKE_FAR_SHORE=45000, the lake (r10b boat,
#      r11a / r11b shore day and night) draws to 45 m instead of the 25 m cap (PS2 world, coarse view, fog; fog ramp the
#      last 20 %). Render only; modelled ~+3.8 hw ms at the boat, accepted. T15_LF="" builds without it.
T15_LF=${T15_LF-LAKE_FAR=45000 LAKE_FAR_SHORE=45000}
# T15_AS (lane ashley17, test 17, 10-18; rule 7 no GameCube character fallback): PS2_ASHLEY_ROOMS=2, Ashley's partner
#      package shares a 32-entry registry texture table with the room package (r11c: Luis 11 + Ashley 6 refused her at
#      16, so she drew the GameCube model). Placed last: it overrides T13R's PS2_ASHLEY_ROOMS=1. Data: ch2 adds her
#      partner packages for r10f / r11d / r11e / r200. Render only; STRICT r11c / r11e / r200; release image _end
#      unchanged (s30 340/340 heap_before 187,840 both; KOS squeeze 48 KiB PASS). ASHLEY17-20261017.md.
#      T15_AS="" builds without it.
T15_AS=${T15_AS-PS2_ASHLEY_ROOMS=2}
# T15_LN (lane lakefx165, test 16.5, issue #30): LAKE_NIGHT_FX=1 = the night lake's torch flames (r11a / r11b owner 0x68
#      sprites drawn natively, not only their glow). Render only. T15_LN="" builds without it.
T15_LN=${T15_LN-LAKE_NIGHT_FX=1}
# T15_TR (lane trans17, test 16.5 / 17, user 10-18 "With trans17"): TRANS_POLICY=3 = FLAT (1: uniform 14/15 alpha parts
#      and fully opaque translucent-pass textures draw opaque) + CARD (2: CARD_NEAR parts draw punch-through). SOFTA, FAR
#      and DROP stay off. Reads data set trans17 (dc/native/rXXX/ps2-world.r4tc + dc/native/trclass.idx); a room not in
#      the index draws as today. Render only. docs/lanes/trans17.md. T15_TR="" builds without it.
T15_TR=${T15_TR-TRANS_POLICY=3}
# T15_RD (lane rain17, 2026-10-18; user 10-18 "320 Dreamcast way"): RAIN_DC=1 RAIN_DC_N=320 = the night lake's
#      Dreamcast rain, 320 screen-space streaks (an approximation of the PS2 Esp08 rain sheet; render only, private RNG;
#      needs RAIN_PS2=1's hook, which stays on in T11REC). With RAIN_DC on the old RAIN_PS2 lines stop. RAIN_PS2_SHEET_REF
#      is a reference arm and never in a recipe. T15_RD="" builds without it.
T15_RD=${T15_RD-RAIN_DC=1 RAIN_DC_N=320}
T15REC="$T15_2 $T15_7 $T15_R $T15_4 $T15_F $T15_H $T15_10 $T15_O $T15_L $T15_S $T15_M $T15_D $T15_G $T15_V $T15_P $T15_W $T15_T $T15_FS $T15_RS $T15_HZ $T15_PB $T15_SO $T15_AC $T15_VP $T15_DY $T15_TP $T15_GD $T15_ST $T15_PG $T15_FN $T15_LF $T15_AS $T15_LN${T15_TR:+ $T15_TR}${T15_RD:+ $T15_RD}"
T15=${T15-$T15REC}
ON="$T9K PVR_LATCH=2 PVR_RECOVER=1 TA_HEADROOM=1 CRASH_TASK_DETAIL=1 $PS2 $P2 $HANDS"
BASE="$ON $T11REC $T12REC $T122"
# CAST-GC (lane castgc17, user 10-17 "why do we keep falling back to gamecube models"): the check arm also carries the
# native census (NATIVE_MODEL_REGISTRY_CENSUS, report every 150 UI frames) that tools/d367/cast_gc.py judges: any
# character / enemy drawn through the GameCube path fails unless tools/d367/castgc/allow.tsv lists it.
MC="MCHECK_LEONGC=1 TEX_CHECK=2 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150"
TR="DBG_WARP=1 PC_SAMPLER=1 LOGIC_TRACE=1 GAME_DECISION_TRACE=1 PACE_MODE=off TRACE_SS_MASK=1 TRACE_ALLOC=1 CODEC_READY_FIXTURE=1"
WP="DBG_WARP=1 PC_SAMPLER=1"
PL="DBG_WARP=0 PC_SAMPLER=0"
b() { lab=$1; tree=$2; shift 2; t0=$(date +%s); echo "== $lab $(date +%T) tree=$tree $*" >> $K/logs-build.txt
  (cd $tree && TREE=$tree bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh $lab $F $LOOK "$@" >> $K/logs-build.txt 2>&1)
  rc=$?; O=/root/probe/lanes/route/out-$lab
  end=$(/opt/toolchains/dc/sh-elf/bin/sh-elf-nm $O/re4dc-game.elf 2>/dev/null | awk '$3=="_end"{print $1}')
  echo "rc=$rc $lab $(cut -c1-16 $O/elf.sha256 2>/dev/null) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt 2>/dev/null) end=$end $(cd $tree && git rev-parse --short=8 HEAD) $*" | sed 's/PS2_LEON_DIR=[^ ]* //;s/PS2_GANADO_DIR=[^ ]* //' | tee -a $K/logs-build.txt | cut -c1-400
  echo "$end" > $O/end.txt; }
L=${LP:-t15i}
mkdir -p $K
for x in "$@"; do case $x in
  rP)  b ${L}rP  $T $BASE $T13 $T14 $T15 IMAGE_PAD_BYTES=0 $PL ;;
  rW)  b ${L}rW  $T $BASE $T13 $T14 $T15 IMAGE_PAD_BYTES=0 $WP ${XON:-} ;;
  mW)  b ${L}mW  $T $BASE $T13 $T14 $T15 IMAGE_PAD_BYTES=0 $WP $MC ${XON:-} ;;
  rT)  b ${L}rT  $T $BASE $T13 $T14 $T15 IMAGE_PAD_BYTES=${PAD_T:-0} $TR ${XON:-} ;;
  kP)  b ${L}kP  $T $BASE $T13 $T14 IMAGE_PAD_BYTES=0 $PL ;;
  kW)  b ${L}kW  $T $BASE $T13 $T14 IMAGE_PAD_BYTES=0 $WP ${XON:-} ;;
  kT)  b ${L}kT  $T $BASE $T13 $T14 IMAGE_PAD_BYTES=${PAD_K:-0} $TR ${XON:-} ;;
  *) echo "arm? $x" ;;
esac; done
