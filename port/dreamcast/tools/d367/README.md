# D367 build, stage and capture tooling

The plan and measurements are in `port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md`.

## Current effective recipe (2026-10-03)

- One recipe: `tools/d367/build-r21.sh` (play builds add the overrides in docs/D367_PLAY_BUILD_CHECKLIST.md,
  "Play build rules"; route-build.sh wraps it). Since 8f34aa63 every build writes `$OUT/resolved-knobs.txt`, the
  knobs as make resolved them (defaults, the recipe line, caller overrides, Makefile overrides); route-build.sh
  records its path in programs-route.json. Quote that file, not a make line.
- Known differences from the make line: MODEL_DRAW_PLANS is forced to 1 by the D349_RENDERER_STACK=1 Makefile
  override. MESH_CLIP_LEAN=1 (ce39455f) and CROWD_READOPT=2 CROWD_CULL=1 CROWD_FOGSKIP=1 (7cbea8e7) joined the
  recipe on 2026-10-03 (user decisions); before that the make line never had MESH_CLIP_LEAN.
- 2026-10-05 (perf lanes integration, perf/int-20261005): the recipe's last line adds SKIN_PALETTE_LAZY=1
  ESP_SPRITE_FAST=1 ESP47_SKIP_LEAN=1 MODEL_PREP_KEEP=1 CROWD_READOPT_MEMO=1 ACTOR_BIND_REUSE=1 PS2_WORLD_HDR_CACHE=1
  MESH_CLIP_ACCEPT=1 PS2_PASS_MASK=1 GAME_HF_REG=1 GAME_CLOTH_SPRING=1 GAME_SND_WALL_ALT=1 (render-only or exact; their
  =2 check builds and comments are in game30.mk / effects30.mk / frontend30.mk / crowd.mk) and LINK_ORDER is
  `link-order/r21z-perf-c3-8k.ld`. PS2_FOLIAGE_FAR (changes the look) stays 0. Route doc "2026-10-05: integrated perf
  lanes" has the A/B and the gates.
- The LH / M1 / PERF / LFV blocks below are dated snapshots (2026-09-23/24), kept as evidence. They still list
  `QUALITY=1` (the Standard/Original picker); play builds pass `QUALITY_PICKER=0` (Standard only).
- Profiler areas are not G. hwproject's "game-logic" area (e.g. LH's 12.0 hw ms/tick) books the shared matrix kernels
  as render and undercounts logic. Measured G is a never-draw (`PACE_FORCE=A`) work per tick on a named image, traced
  over all ticks (stride 7 or 1, not 8).

## Canonical recipe (snapshot 2026-09-24; integrated base; every stacked measurement and the m1 disc used this)

```
LH="NO_EH=1 NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN=1 PVR_FAST_WAKE=1 BRIDGE_LEAN=1 PVR_PIPELINE=2 MESH_LOD=1 MESH_LOD_PX=3 NATIVE_FOG=1 COPY_LEAN=1 FRONT_LEAN=1 MESH_DIRECT=1 TA_DIRECT=1 NATIVE_ACTOR_DIRECT=1 UI_VRAM=1 TA_VERTBUF_KB=2048 GAME_FP_CONTRACT=off GAME_CPU=1 GAME_ROT_CACHE=1 GAME_O2=hot GAME_TRIG=1 GAME_PWC_DIAG=1 GAME_ATCHK=1 GAME_MOTION_INDEX=1 GAME_CONCAT_COL=1 GAME_SINCOS=1 GAME_MULTVEC_SCHED=1 GAME_VEC_INLINE=1 GAME_COL_PREFETCH=1 GAME_ATCHK_LIST=1 GAME_ESP_OWNER=1 GAME_SKEL_FTRV=1 GAME_ROTVEC_MEMO=1 AICA_AUDIO=1 RELEASE_FLAGS=1"
M1="ROUTE_MOVIES=1 AICA_STREAMS=1 SUBSCREEN=1 UI_HANDLES=1 TEX_RESIDENT=1 FX_LEAN=1 EM10_SHARED=1 ARENA_FIT=1 GAME_COLD_OS=1 SOUND_REGION_BYTES=0x60000 MOTION_FAST_READ=1 NATIVE_ACTOR_SKIN_LAZY=1 QUALITY=1 VMU_SAVE=1 VMU_DEBUG_SLOT=1 NATIVE_MES=1 SUBSCREEN_OVL=1 SS_POOL_HIGH=1 NATIVE_PKG_HIGH=1"
PERF="FRONT_NATIVE=1 HW_LEAN=1 FOG_FAR=25000 EFFECT_LEAN=1 EFFECT_SPRITES=1 PLAN_ADMIT_LEAN=1 SCENERY_GATE=1 MODEL_SLAB_LATCH=1 NATIVE_ACTOR_LOD=1 NATIVE_ACTOR_PRELIT=1 CROWD_LOD=1 TA_DOUBLEBUF=1 ACTOR_SKIN_FTRV=1"
EXTRA_MAKE="$LH $M1 $PERF OBJDIR=/path/obj-<name>"
# stage: TEXDIRS="$VQ $P/tex" (tex-vq5 + PS2 bark); EFFECT_SPRITES=1 makes stage.sh prepend the
# tex-fx cache itself (tools/d367/tex_fx.sh). User discs add UI_OVERRIDES=/root/re4data/overrides/ui.
```

- `LH`: the game30 logic recipe (12.0 hw ms/tick: hwproject's "game-logic" area, not measured G), plus the bit-exact logic cuts GAME_PWC_DIAG=1 / GAME_ATCHK=1 / GAME_MOTION_INDEX=1 (-2.65 / -3.25 hw ms/tick at 6 / 8 engaged Ganados) and GAME_CONCAT_COL=1 (dbe1abb, a further -1.06 / -1.25; needs GAME_FP_CONTRACT=off). Rejected: GAME_PWC_FAST (+0.45 hw ms), GAME_SCHED=game (no logic gain). Never ship GAME_PWC_DIAG=2 (test-only check build). `M1`: route and memory knobs for the playable disc. `QUALITY=1` is the Standard/Original picker after Start (766332d); Standard is the default. Its text draws through NATIVE_MES=1 (native cMes glyph atlas, 32 KB VRAM). VMU saves (6d5d6a9/cd0343a): `VMU_SAVE=1` saves to the VMU (17 blocks per save, never formats, overwrites in place when full, heap 4 -16 KB) and stores the picker choice as RE4DCCFG; `VMU_DEBUG_SLOT=1` adds the RE4DCDBG debug slot (hold L+START 1 s in play, reload as FILE 20; ~96 KB taken from heap 4 only during the save, refused with a log line if short) that the user asked to keep on the first disc for reloads. `SUBSCREEN_OVL=1` loads the sub-screen code from /cd/dc/sscrn.ovl at each open (heap 4 +112 KB; ~+0.1-0.2 s per open on GD-ROM).
- `PERF` lists landed lane steps: FRONT_NATIVE (c881fba, -4.1 hw ms), the approved 25 m fog far
  plane, the native effect sprites (a0a32aa), and D1 + S1a + the slab latch (27fb5a5; fight p99
  488 -> 172 ms in Flycast, -2.4 hw ms at 25 m), and TA_DOUBLEBUF (b7a7e2d: the TA double-buffered in
  play, a single bank while a sub screen is open; needs `patches/kos-804b319-vbuf-switch.patch` in the
  d367 KOS worktree, which subscreen.mk checks with nm; r100 quiet 73.2 -> 71.3 ms Flycast mean, the
  r101 fight unchanged because it is CPU-bound; the gain grows as CPU per frame falls).
- Add each new lane step here when it lands. Untracked -D knobs don't trigger rebuilds: delete the
  tree ELF, use a fresh OBJDIR per flag set, and record the ELF sha256.
- Frame pacing and the coarse square (f4da5fd; `pace.mk`, `game30.mk`) are not in PERF. Play discs add
  `PACE_CATCHUP=2 PACE_MODE=fast` (PACE_CAP stays 1 by user decision; PACE_CAP=2 measured 2026-10-09 in
  D367_THIRTY_FPS_ROUTE.md; `pacesim.py` replays the pacing rule on hw model drawn / skipped ms). The coarse-square arms add `PACE_CATCHUP=2 PACE_MODE=off
  PACE_TRANS_SKIP=4063 COARSE=1` (every tick drawn; test builds) and, for the gates, `DBG_WARP=1
  LOGIC_TRACE=1 LOGIC_TRACE_MASK_RENDER=1 GAME_DECISION_TRACE=1 ACT_CAP=0` (the r101 square plan,
  `docs/D367_SQUARE_PERF_PLAN.md`).
- R headroom and code placement (801d72d; exact, not in PERF yet: measured on the coarse square only). The
  coarse-square arms add `GAME_OT_MASK=1 GAME_ID_LISTS=1 UI_HEAP_LAZY=30 UI_HEADERS=1 UI_PALETTE_SLOTS=32`
  and `LINK_ORDER=link-order/r101-square-c3-8k.ld` (the hot code placed first in .text from hwproject
  evidence; regenerate it with `tools/d367/ordgen_c3.py --objdir <OBJDIR> -o <file> <never-draw run>
  <drawn run>` after code changes).
- Code placement for r21y (2026-10-04, lane build): `link-order/r21y-house-fight-square-c3-8k.ld`, regenerated
  from the perf-20261004 cost arm (route-build `DBG_WARP=1 PACE_MODE=fast PC_SAMPLER=0 PACE_FORCE=2
  ENC_CENSUS=1`) on the r100-h-quiet, r100-h-fight and perf-r101sq windows:
  `ordgen_c3.py --objdir <cost arm OBJDIR> --exclude '^(re4dc_pace_end|re4dc_vi_retrace_count)$' -o <file>
  <hwmodel runs>` (the exclusion drops the pacing spin, which a PACE_FORCE run books as hw ms). Before each
  release, `tools/d367/ordcheck.py --objdir <OBJDIR> <order.ld> <hwmodel runs>` reports the order's stale rules
  and the share of the runs' hw ms it places; regenerate when it falls well below the placeable share.
- Code placement for the 2026-10-05 recipe (perf lanes integration): `link-order/r21z-perf-c3-8k.ld`, the same method
  on the all-knobs cost arm plus `--skip-weight 1` (adds the skipped ticks' hw ms, from modesplit.sh's proj-skip, as
  weight). Without the skip weight the regenerated order measured +0.2..0.4 hw ms worse than keeping the older r21y
  order; `--max 4096` was worse too. Once the placed share is near the placeable share (~88%), a regenerated order is
  a few-tenths lottery: build each candidate (`LINK_ORDER=<file>` on the route-build line overrides the recipe) and
  keep the one with the lowest hw ms on house + fight + square. ordcheck.py on r21z: 0 stale rules, 88-89% placed.
- The em-em candidate cache (aeefd26; exact, room-independent; not in LH yet: gated on the r101 square): the
  coarse-square arms add `GAME_ATCHK_CACHE=1` (needs GAME_ATCHK_LIST=1, in LH). `GAME_ATCHK_CACHE=2` is its
  check build (every reuse compared with a fresh collection, "ATC" lines).
- The workAt inline (3eaa868; exact, room-independent; not in LH yet): the coarse-square arms add
  `GAME_WORKAT_INLINE=1` (needs OBJECT_DEMAND=1 ENEMY_DEMAND=1).
- The line queries' leaf kernel (cf46edc; exact, room-independent; not in LH yet): the coarse-square arms add
  `GAME_LINE_LEAF=1`; the square's order file (link-order/r101-square-c3-8k.ld) places the kernel
  (platform/lnk_sh4.S) after At_poly_line_ck.
- The line queries' block walk kernel (ba73027; exact, room-independent; not in LH yet): the coarse-square arms
  add `GAME_LINE_WALK=1`; the order file places its kernel (platform/lnw_sh4.S) after the leaf kernel.
- The pieces' transforms in the walk kernel (4e394ea; exact, room-independent; not in LH yet): the coarse-square
  arms add `GAME_LINE_PIECE=1` (needs `GAME_LINE_WALK=1`); the entry lives in platform/lnw_sh4.S, so the
  order file is unchanged.
- The actor vertex kernel (42afaa1, rev 2 7726caa, rev 3 d938501, rev 4 + 5 e4fb8e8; render-only, exact; with
  GAME_FP_CONTRACT=off it needs the GAME_FP_RENDER=fast exemption, the default): `ACTOR_VTX_KERNEL=1` runs the fast actor path's
  position / skin / light passes on platform/avk_sh4.S (with NATIVE_ACTOR_FAST=1; the version C square arms add
  it). `python3 tools/game30/avk/mkavk.py <out.S>` regenerates the kernels from the templates and the fixed
  schedules (sched-*.txt; delete one to reschedule). =2 check builds log "VTXK" lines. Version C discs need
  `EXTRA_TEXDIRS` with the private hair texture dir or COARSE_LEON draws nothing.
- The coarse character adapters (9df764b; default off; render-only; the meshes are private and stay out of Git):
  `COARSE_LEON=1 COARSE_GANADO=1 COARSE_ACTOR_ASSET_DIR=<private bundle dir>` draw Leon and the Ganados from
  the reduced meshes on the coarse path (needs COARSE=1, NATIVE_ACTOR_FAST=1, NATIVE_ACTOR_SKIN_LAZY=1;
  `COARSE_GANADO_LIMIT` caps meshes drawn, presentation only). `COARSE_SKIN_FTRV=1` builds the palette
  matrices with FTRV (coarse_skin_sh4.S; =2 runs the C path too and logs COARSE_SKIN_CHK).
  `ACTOR_SWAP=1` (benchmark, COARSE=0) draws the same meshes through the source renderer; `COARSE_FREEZE_AT=N`
  (diagnostic) stops in frame N's actor pass for matched captures.
- The cast Ganados (08d2216; default off; render-only): `COARSE_GANADO_CAST=1` (needs COARSE_GANADO=1) with
  `COARSE_ACTOR_ASSET_DIR=<private cast bundle>` (ganado_cast_runtime.h, made by the cl lane's private
  tools/cast_bundle.py from the external cast packs) and `EXTRA_TEXDIRS=<bundle>/tex`. =2 logs "GCAST". Use a
  fresh OBJDIR per setting: both sources build coarse_ganado.o.
- The cl lane's R levers (c6edb6f; default off): `COARSE_PREGATE=1` (needs COARSE=1 and COARSE_GANADO_CAST; render only; a
  conservative per-chunk, per-bone bound skips cast Ganado chunks wholly outside a screen edge or far before their
  skin work; =2 is a check build that counts violations, which must be 0) and `CHAR_DATA_BLOCK=1` (needs
  COARSE_LEON=1; link only: the character adapters' data as one 16 KiB-padded block after .data, so game data keeps
  its addresses and cache sets; toggling it does not force a relink: use a fresh OBJDIR and delete the ELF first).
- One submission per actor (e874a66; exact, render-only; default off): `COARSE_ONE_SUBMIT=1` (needs COARSE_LEON=1;
  #error unless ACTOR_DIRECT, SKIN_LAZY, no ACTOR_UV16, no TA_GUARD; refuses COARSE_PREGATE=2). A group's chunks
  share one TA_DIRECT window (Leon 8 -> 3 submissions, a cast Ganado 4 -> 1). =2 is a check build that draws every
  chunk twice and logs "C3CHK" word / header / result mismatches (must be 0): never an image or cost arm. With the
  knob on, the model_parts / direct_parts / handle_hits / frame_pvr_calls counters count windows, not chunks.
- The skeleton kernels (ddea9bf; room-independent; not in LH yet): the coarse-square arms add
  `GAME_PWC_KERNEL=3 GAME_PMC_KERNEL=1 GAME_HERMITE_FAST=1`. PWC_KERNEL needs `GAME_SKEL_FTRV=1` (=1 the
  Ganados' pass, exact; =3 every model's pass, last-bit FP policy, decisions identical); PMC_KERNEL needs
  `GAME_ROT_CACHE=1`. The order file places platform/pwc_sh4.o, pmc_sh4.o and hermiteFast. =2 check builds
  log "PWCK" and "HERMF" lines.
- The skeleton lane's batch 3 (4f81bbd; exact; not in LH yet): the coarse-square arms add `GAME_VEC_NORM_INLINE=1
  GAME_MTXINV_SCHED=1` (both need `GAME_FP_CONTRACT=off`; MTXINV_SCHED also `GAME_SH4_MATH=1`, which GAME_CPU=1
  sets; game30.mk stops the build otherwise).
- The skeleton lane (ee7d080; exact, room-independent; not in LH yet): the coarse-square arms add
  `GAME_LIGHT_LAZY=1 GAME_FP_SCHED=1 GAME_HF_INLINE=1 GAME_HF_PF=1 GAME_PWC_SCHED=1 GAME_PWC_PF=1
  GAME_TRIG_LEAN=1 GAME_ACOS_LEAN=1` (HF_* need GAME_HERMITE_FAST, PWC_SCHED needs GAME_PWC_KERNEL, PWC_PF needs
  PWC_SCHED; TRIG_LEAN acts with GAME_TRIG=1, ACOS_LEAN with GAME_FDLIBM=1). LIGHT_LAZY=2 is its check build.
  `tools/game30/trig_lean_exhaustive.sh` runs TRIG_LEAN's host test over all 2^32 inputs.
- The object scans (0862e7c; exact, room-independent; not in LH yet): the coarse-square arms add `GAME_OB_SCAN=1`
  (its GetEmPtrFromList part needs `GAME_WORKAT_INLINE=1`). =2 check builds log "OBS" lines.
- The object batches 2 and 3 (9f66533, 97874b5; exact; not in LH yet): the coarse-square arms add `GAME_OB_MAT=1 GAME_OB_PATH=1
  GAME_OB_NEAR=1 GAME_OB_DECODE=1`
  (independent of each other and of GAME_OB_SCAN). =2 check builds log "OBM" / "OBP" lines.
- Collision batch 7 (ca229cf; exact; not in LH yet): the coarse-square arms add `GAME_LINE_LEAF2=1 GAME_LINE_WALK_PF=1
  GAME_LINE_TAIL=1 GAME_SCEAT_LIST=1` (LEAF2 / TAIL need GAME_LINE_LEAF=1, WALK_PF needs GAME_LINE_WALK=1); the
  landed order file places the new kernels. =2 check builds log "LK2" / "LWP" / "LTL" / "SAL" lines.
- The coarse world (6f4c91c; render-only; default off): `COARSE_WORLD=15` (bits: 1 house shells, 2 ground, 4 sky,
  8 trees; needs COARSE=1, bit 8 needs TREE_IMPOSTOR=1). It includes the generated private coarse_world.h
  (never committed: copy it into port/dreamcast/game for the build, untracked; the current one is v10,
  coarse_world_v10.h sha256 65f8529ed1ce55d348d50c679cdd696ae7e212298b0c7fb7a50623640e318c85, and nothing in the build checks it) and needs the world textures
  staged with `EXTRA_TEXDIRS`.
- The coarse world's layout-11 runtime rev 2 (e69737e; render-only; default off): `COARSE_WORLD` bits 16 (R1 + R6
  mesh records), 32 (R7 backdrop segments; the sky dome then writes no depth), 64 (R3 world texture preload after the
  character passes, no disc access) and 128 (K0: skip the coarse view's collision piece 0 walk when the world covers
  it; drawing only). It reads a layout-11 coarse_world.h built to the external world agent's renderer contract rev 2
  (re4-assets-private world-agent-20260926 from-main\renderer-contract.md section 11, ref_decoder.py rev 2).
  `COARSE_NO_STD_SCENERY=1` (needs COARSE_WORLD, NATIVE_STATIC=1, NATIVE_MESH=1, NATIVE_PKG_HIGH=1): the coarse room
  never opens the Standard scenery package, +599,424 B of heap 4; test arms only: images the coarse path does not draw
  there (door demo, death, continue) show no packaged scenery.
- The effect pools' scans and moves (1d3dc4d; exact, room-independent; not in LH yet): the coarse-square arms add
  `GAME_FX_SCAN=1 GAME_FX_MOVE=1` (FX_SCAN needs `GAME_ESP_OWNER=1`; its EfmDelete list path needs
  `GAME_ATCHK_LIST=1 GAME_WORKAT_INLINE=1`). Header knobs (include/esp.h): fresh builds only. =2 check builds
  log "FXS", "FXM", "FX48" and "FX15" lines.
- The collision stack (7caa2f7; exact, room-independent; not in LH yet): the coarse-square arms add
  `GAME_SPHERE_WALK=1 GAME_CUBE_MEMO=1 GAME_EM10_IDFIRST=1 GAME_LINE_YROW=1 GAME_ATRECT_FAR=1
  GAME_OBJHIT_LIST=1 GAME_OBJHIT_IDFIRST=1 GAME_EMHIT_LIST=1`. SPHERE_WALK needs `GAME_FP_CONTRACT=off`; the
  order file places its kernel (platform/spw_sh4.o) after cSatBlock::hitCheckSphere. LINE_YROW needs
  `GAME_LINE_PIECE=1`; the lists need `GAME_ATCHK_LIST=1`; OBJHIT_IDFIRST needs OBJHIT_LIST. =2 check builds
  log "SPW", "CBM", "EID", "LYR", "ARF", "OHL", "OID" and "EHL" lines.

## Default recipe (snapshot 2026-09-23; LFV: LF + UI_VRAM + 2 MiB TA buffer + VQ UI/model textures + resident textures)

```
LFV="NO_EH=1 NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN=1 PVR_FAST_WAKE=1 BRIDGE_LEAN=1 PVR_PIPELINE=2 MESH_LOD=1 MESH_LOD_PX=3 NATIVE_FOG=1 UI_VRAM=1 TA_VERTBUF_KB=2048 UI_HANDLES=1 TEX_RESIDENT=1"
P=/root/probe/d367-agents/ps2-blender/stage/ps2trees     # LD packages (private)
VQ=/root/probe/d367-agents/ui-vram/tex-vq5                # VQ texture overlay (private, see below)

# build (private OBJDIR keeps flag changes from reusing the shared obj/)
OWNERS=0x7F STATIC=1 MESH=1 EXTRA_MAKE="$LFV OBJDIR=/path/obj-<name>" \
  bash port/dreamcast/tools/d367/build.sh /path/build-<name>

# stage (MIRROR, FIXTURES_SRC and KEYED are locally extracted private data).
# TEXDIRS order matters: later directories win. The VQ overlay also re-encodes
# the GC bark key f6e54e3e-1ef21097, so the PS2 bark ($P/tex) must come last.
MIRROR=/root/probe/d367-mirror KEYED=/root/probe/d367-native-static/keyed12 \
  MESHDIR=$P/mesh TEXDIRS="$VQ $P/tex" \
  bash port/dreamcast/tools/d367/stage.sh /path/build-<name> /path/disc-<name>
```

Capture with `port/dreamcast/tools/flycast-harness/` (see its README). `stage.sh` records
its inputs in `<disc-dir>/stage-inputs.txt` and warns when a `UI_VRAM=1 TA_VERTBUF_KB=2048`
build is staged without a VQ overlay (the 2.6 MB texture pool then thrashes: 1,884 upload
failures and multi-second frames at r100 in Flycast).

### UI image overrides (UI_OVERRIDES)

`UI_OVERRIDES=/root/re4data/overrides/ui` (private, never in Git) replaces source UI images
with edited PNGs. Name and place each PNG as `extract_ui_images.py` writes it, under the
archive's path: `ss/eng/title_eff0_tpl31_tex00_CMPR_640x360.png` is the title background
(ss/eng/title.dat EFF 0, TPL 31, texture 0, key `c67f5c01-63e0879e`). `tools/ui_overrides.py`
first re-encodes the original through the same path and must reproduce the staged package
(fixtures 16-bit, or the TEXDIRS VQ overlay) byte for byte, then encodes the PNG the same
way under the original key; a size or name mismatch fails. The disc's title.dat is unchanged
(the runtime keys packages by the unmodified source texels). `stage-inputs.txt` and
`<disc>/ui-overrides-report.json` record each override's sha256. Unset: staging is unchanged.

`UI_HANDLES=1 TEX_RESIDENT=1` (texture hitch fix; Flycast r100 camera tour, frames 2400+):
- The hitch was the first-sight texture load: ~0.2 s per package at r100 (~0.3-0.4 s at r101),
  almost all of it the iso9660 lookup. The flat `/cd/dc/tex` directory (~550 packages, 17+
  sectors) overflowed KOS's 16-sector inode cache, so every open re-read the directory from
  the disc. `stage.sh` fans a TEX_RESIDENT build's packages out into `tex/0`..`tex/f` (first hex
  digit); the build opens `/cd/dc/tex/<d>/<crc>-<fnv>.re4tex`.
- `TEX_RESIDENT=1`: the room/enemy/player/weapon identity sets are preloaded at room entry
  (in disc order, leaving 32 of the 192 entries and 256 KiB for first-sight loads), absent
  packages are remembered and never evict a resident texture, eviction is
  least-recently-requested, and the runtime payload CRC is skipped (`stage.sh` verifies every
  package's CRC instead; `TEX_PAYLOAD_CRC=1` keeps the runtime check).
- `UI_HANDLES=1`: one direct-mapped handle per source image descriptor (O(1), no hashing).
- Tour result, LFV + tex-vq3 -> this recipe: median 100 -> 100 ms, p99 870 -> 119 ms, max
  4264 -> 489 ms, frames over 2x the median 289 -> 5, texture loads while moving 756 -> 6.
  The five remaining spikes are not textures (3 are draw-plan installs, `visit_draw_locals` +
  memmove, ~450 ms). The r100 room entry preloads 177 packages in 4.4 s (r101: 188 in 5.0 s).
- Image cost with the knobs on: +41,888 bytes (text +3,360; data +17,920 = the 192 cache
  entries; bss +20,608 = handle table, palette copies, preload list). `TEX_SLOTS=128`
  saves 10,240 bytes. The default build is byte-identical.

Why each part of LFV is needed (Flycast r100, frames 2401-2520, all 116.8 ms/frame):
- `TA_VERTBUF_KB=2048`: r100 sends ~1.41 MB/frame of TA stream (~1031 KB of TA
  parameters), over a 1024 KB bank on hardware (Flycast does not enforce it).
- The 2 MiB banks shrink the PVR texture pool from 4.74 MB to 2.64 MB. `UI_VRAM=1` sizes
  the native texture cache from the actual pool (LRU eviction, fragmentation retry,
  fail-fast, 2 KiB page placement for VQ).
- `tex-vq3` makes the title/menu textures (32 images, 7.24 MB -> 0.97 MB) and large model
  textures (23 images, 2.75 MB -> 0.39 MB) full-codebook VQ. Title peak 1.04 MB, r100 uses
  1.59 MB of 2.58 MB; 0 upload failures, 0 evictions. Worst model PSNR is 26.3 dB (leaf
  litter), which was not visibly different in 2x gameplay crops against LF.

### VQ overlay tex-vq6 (tex-vq5 + r101; the asset pipeline's 00-vq)

r101's room textures were never VQ: tex-vq5 is built from r100 logs only, so r101 streamed 126
textures as 16-bit (4.04 MB against the 2.47-2.55 MB budget). Uploads thrashed and the square
barely moved (warp-vp0-r101: 4,613 failed uploads, 245 ticks in 200 s). tex-vq6 is the same
rule (`--model-min-bytes 16384`) with two r101 square logs added to `ui_logs`
(`warp-vp0-r101`, `warp-sa1-r101`). The source is the route fixtures (`frontier/fixtures/tex`,
a superset of `d354v7-fixtures/tex`).
- 198 images, 18,546,688 -> 2,723,840 bytes.
- The 137 tex-vq5 packages are byte-identical.
- The 61 new r101 images go 4,521,984 -> 690,176 bytes, lowest PSNR 27.6 dB.

The asset pipeline regenerates it as each room's `tex/00-vq` (`sources.toml`: `fixtures`,
`ui_logs`, pinned `vq_overlay`).

r101 bell fight with it: 15 failed uploads, 1,955 ticks in 200 s, Flycast steady 10.1 fps
Standard / 9.4 Original (warp-sa2p-r101, warp-sa2o-r101). Standard vs Original logic trace is
STRICT. Add the logs of later rooms to `ui_logs` the same way when they are brought up.

### Generating the VQ overlay (tex-vq5; tex-vq3 below is the same rule on fewer logs)

tex-vq5 applies the tex-vq3 rule to three more logs (the camera tour and the 4/10-Ganado
crowd) and to the r100 textures the room preload loads, and makes model textures VQ from
16 KiB padded (tex-vq3: 64 KiB), so the r100 room set fits the 2.58 MB pool: 137 images,
14,024,704 -> 2,033,664 bytes, lowest PSNR 26.3 dB (the tex-vq3 leaf litter). Logs are kept
privately in `/root/probe/d367-agents/ui-vram/logs/`:

```
L=/root/probe/d367-agents/ui-vram/logs
python3 port/dreamcast/tools/vq_native_ui.py --textures /root/probe/d354v7-fixtures/tex \
  --log $L/v2-run-output.txt --log $L/v3-run-output.txt --log $L/p2048a-run-output.txt \
  --log $L/la-run-output.txt --log $L/lod2048-run-output.txt --log $L/scen-tour-G25-run-output.txt \
  --log $L/actors30-gcrowd-crowd-run-output.txt --log $L/actors30-gfull-crowd-run-output.txt \
  --log $L/uivram-tour-t1-run-output.txt --log $L/uivram-tour-t3-run-output.txt \
  --model-min-bytes 16384 --output /root/probe/d367-agents/ui-vram/tex-vq5
```

### Generating the VQ overlay (tex-vq3)

The packages are private derived game data: keep them out of Git. Inputs are the
fixtures' native texture packages (`$FIXTURES_SRC/tex`, default
`/root/probe/d354v7-fixtures/tex`) and Flycast run logs that reached r100 gameplay; the
`native UI: load ...` lines name the images the title, menus and r100 load. The measured
`tex-vq3` came from the five logs kept (private) in `/root/probe/d367-agents/ui-vram/logs/`:

```
L=/root/probe/d367-agents/ui-vram/logs
python3 port/dreamcast/tools/vq_native_ui.py --textures /root/probe/d354v7-fixtures/tex \
  --log $L/v2-run-output.txt --log $L/v3-run-output.txt --log $L/p2048a-run-output.txt \
  --log $L/la-run-output.txt --log $L/lod2048-run-output.txt --model-min-bytes 65536 \
  --output /root/probe/d367-agents/ui-vram/tex-vq3 [--previews <png-dir>]
```

Without those logs, pass the `run-output.txt` of any one LFV/LF run that reached r100
instead. The encoder is deterministic: that gives the same 55 packages byte for byte, plus
3 model textures only the LF scenery loads (256x256, 32.9-34.5 dB; 58 images,
10,387,456 -> 1,417,216 bytes). The 58-image set was not captured in Flycast.

UI images (loaded before the first room binds, or indexed C4/C8 sources) of at least 32 KiB
padded and 32 px per side, and model textures of at least 64 KiB padded, are re-encoded
by the pinned KOS `pvrtex` (`/root/work/kos-re4dc-d336/utils/pvrtex/pvrtex`, full
256-entry codebook). The package names (source identities), padded sizes and UV scale are
unchanged. `vq-native-ui-report.json` lists every image with its PSNR; the expected summary
is 55 images, 9,994,240 -> 1,361,920 bytes. The overlay is required only by the 2 MiB TA
recipe; the default-flag build ignores it.

## Effect sprites (`EFFECT_LEAN=1 EFFECT_SPRITES=1`, effects30.mk)

Muzzle flash (weapon owners 0x34-0x4f), the shot's core effects (owner 0) and blood (EM10,
owner 0x10) are drawn as native PVR sprites in OT order (the deferred translucent queue); a
sprite that finds no queue room is dropped, never the frame. Their TPL images have no
packages in the base texture set, so `stage.sh` runs `tex_fx.sh` for any build whose
candidate.txt has `EFFECT_SPRITES=1`: 552 packages from etc/core.das, em/em10.drs and
em/wep00-09.drs (pinned list, `prepare_native_ui.py`, ~10 s once), cached in `FX_CACHE`
(private, default /root/probe/d367-fx-cache, source `RE4DATA`, default /root/re4data) and
staged FIRST in TEXDIRS so the VQ overlay and the PS2 bark still win. No manual step.
r100 fight (a0a32aa): hw 133.3 -> 134.1 ms (+0.8, for effects that were not drawn before),
STRICT; the run log line is `native effect sprites: queued= direct= missing= dropped=`.

## Asset pipeline (assets.sh)

`tools/d367/assets.sh` generates a room's asset set from formulas instead of hand-tuned
arguments, caches every step by content hash, writes a manifest and a review sheet, and
stages the result for `stage.sh`. The design, formulas, override format and plug-in interface
are in `docs/D367_ASSET_PIPELINE.md`. Everything it reads or writes is private: the cache,
manifests and review sheets live under `RE4DC_ASSETS_ROOT` (default
`/root/probe/d367-agents/assets`), and the input paths are listed in
`tools/assetpipe/sources.toml`.

```
tools/d367/assets.sh rooms                       # every stage room on the GC disc image
tools/d367/assets.sh inventory r101              # BIN counts, bounds, instances
tools/d367/assets.sh build r100 [--verify]       # --plan recipe (default today): the accepted packages
ASSETS=$RE4DC_ASSETS_ROOT/out/standard/r100 bash tools/d367/stage.sh <build> <disc>
```

`build r100 --plan recipe` reproduces the LFV r100 inputs byte for byte: the seven LD packages
(`COMMON` `cdeade63...`), the tex-vq5 overlay (137 images) and the PS2 bark. `--verify`
rebuilds every cached step and compares the output hashes. It also writes
`review/standard/r100/index.html`: source vs chosen renders at 3, 8 and 20 m, and predicted
hardware ms per asset. `stage.sh` reads the generated `stage.env` through `ASSETS=`, and
variables set explicitly still win.

## Candidate flag sets (Flycast r100, frames 2401-2520)

| Name | ms/frame | EXTRA_MAKE |
|---|---|---|
| LD | 117 | `NO_EH=1 NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN=1 PVR_FAST_WAKE=1 BRIDGE_LEAN=1 PVR_PIPELINE=1 MESH_LOD=1 MESH_LOD_PX=3 NATIVE_FOG=1` |
| LF | 117 | `NO_EH=1 NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN=1 PVR_FAST_WAKE=1 BRIDGE_LEAN=1 PVR_PIPELINE=2 MESH_LOD=1 MESH_LOD_PX=3 NATIVE_FOG=1`. Async present; `build.sh` selects `/root/work/kos-re4dc-d367` (see `patches/README.md`). Neutral in Flycast; adopted because it stops the CPU waiting on render. |
| LFV (default) | 117 | LF plus `UI_VRAM=1 TA_VERTBUF_KB=2048`, staged with the `tex-vq3` overlay (above). Fits the r100 TA stream on hardware; same Flycast frame time as LF. |

LD packages: the scenery30 LOD packages with the PS2 tree substitution (`MESHDIR`), and
the PS2 bark texture overlay (`TEXDIRS`). The generation steps are documented with the
converter (`tools/convert_room_bins.py --lod ...`).

Add `PC_SAMPLER=1 PC_SAMPLER_BYTES=8192` for the PC-sampling profiler, when that knob is
present in the tree.

## Blender scenery knobs (items 20/21, `game/blender30.mk`)

Both default to 0, and the default image is then byte-identical. Both need `MESH_LOD=1` and
packages annotated by `tools/mesh_annotate.py`. A runtime without the knob ignores the
annotations.

| Knob | Effect | Package input |
|---|---|---|
| `TREE_IMPOSTOR=1` (`TREE_IMPOSTOR_MM=12000`) | Past that view depth, each PS2 tree draws as one camera-facing punch-through quad from a 16-view atlas (4bpp palettised VQ, format kPal4). Quads are batched per atlas into the PT list. | `--impostors` (`tools/tree_impostors.py`) |
| `MESH_TEXTURES=1` | A part with a texture record binds that prepared package instead of its source image. This is how house shells carry their baked GC detail. | `--textures` (`tools/house_shells.py`) |

```
# tree impostors (COMMON): bake, encode, annotate; TEXDIRS += <imp>/tex
blender -b --factory-startup --python tools/blender/bl_impostor_bake.py -- <trees-dc> <bake>
python3 tools/tree_impostors.py <imp> --bake <bake> --trees <trees-dc>
python3 tools/mesh_annotate.py <pkg>/COMMON.re4mesh <out>/COMMON.re4mesh --impostors <imp>/impostors.json
# house shells (FILE_01/17, /18): shell + bake per BIN, package, replace, annotate; TEXDIRS += <sh>/tex
blender -b --factory-startup --python tools/blender/bl_house_shell.py -- FILE_01_17.obj <tpl png dir> <s17> \
  --keep-alpha --cull-hidden --faces 550 --tex-size 512
python3 tools/house_shells.py <sh> <s17> <s18>
python3 tools/convert_room_bins.py <tmp>/FILE_01.re4mesh --owner 1 --bins <R100.FILE_1> <LD lod args> \
  --lod-substitute <dir: the other FILE_01 replacements + <sh>/replace/*.obj>
python3 tools/mesh_annotate.py <tmp>/FILE_01.re4mesh <out>/FILE_01.re4mesh --textures <sh>/textures.json
# honest comparison renders (VQ-decoded texture), 3/8/20 m, 8 azimuths, worst first in metrics.json
blender -b --factory-startup --python tools/blender/bl_house_compare.py -- FILE_01_17.obj <s17>/FILE_01_17.obj \
  <tpl png dir> <sh>/preview/FILE_01_17.png <cmp>
```

`TREE_IMPOSTOR=1` at 12 m, measured on r100 frames 2401-2520 with LF in one Flycast sitting:
frame 116.8 -> 100.1 ms, work 91.3 -> 88.6 ms, TA 1.41 -> 1.28 MB/frame (about 30 quads in 5
batches). The hardware model (`frame_ms.py --impostor`) gives -1.08 ms, or -0.98 ms at 15 m.
VRAM is 84 KB of atlases plus 77 KB of PT bins.

`MESH_TEXTURES=1` with the FILE_01/17 and /18 shells (550 and 800 triangles, 512 VQ each)
gives -0.71 ms/frame in the hardware model (heavy mean 8.62 -> 7.91; per BIN 0.81 -> 0.32 and
0.63 -> 0.40). VRAM is 132 KB. Not measured in Flycast.

## Any room: r101, r103 (W9)

The same package recipe as r100 (instanced meshes, LOD at `MESH_LOD_PX=3`, fog to the
source far plane), read straight from the room SMD. Every render-qualified local BIN is
packaged. r101 and r103 have no common placements, so they have no COMMON package.

```
# packages (private data; st1/<room>.das from the route mirror's iso-src)
python3 tools/convert_room_bins.py <pkg>/MAINSCENARIO.re4mesh --owner 0xff --smd st1/r101.das \
  --lod --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 \
  [--lod-substitute <trees> --lod-bias 0xff:13-16=0.375]
# PS2 trees paired by placement (r101: GC 13-16 <- PS2 81+82, 78, 79, 80; GC bark kept)
python3 tools/ps2_trees.py <trees> --room st1/r101.das --gc-bins 13-16 --ps2-bins 78-82 \
  --ps2-obj <PS2 r101_004.scenario.obj> --dc-uv
# release: the packaged BINs' GX payload leaves the prepared room archive (.dar and .arc)
python3 tools/room_smd.py release <room>.dar <pkg>/MAINSCENARIO.re4mesh.json <released>.dar
python3 tools/room_smd.py release <room>.arc <pkg>/MAINSCENARIO.re4mesh.json <released>.arc
# stage
MESHROOMS="r101=<pkg>" ROOMFILES="st1/r101.dar=<released>.dar st1/r101.arc=<released>.arc" \
  bash port/dreamcast/tools/d367/stage.sh /path/build-<name> /path/disc-<name>
```

`tools/room_smd.py` holds the release contract. A released BIN keeps its header, part
headers (stream size 0), CLR0, and a 2-vertex box, so bounds and the part walk are
unchanged. The runtime matches its parts by index. A released archive needs its package
and `NATIVE_MESH=1`: a released part never falls back to GX. The prepared room's NTR
texture index is rebased. `tests/test_room_smd.py` covers this, plus r101/r103 when
`RE4DC_ROUTE_DAS_DIR` holds the route .das files.

r100 also has five scroll block files (`st1/r100_00..04.dat`, one SMD each) and a room
archive with two SMDs (the room's own and the common one, game.cpp SmdInit). Release them
against both package sets, because either one may be opened at run time (Standard `low/` or
Original). An identity is a converter summary (`.re4mesh.json`) or the R4IM package itself;
a BIN is released only when every identity given covers it the same way (every part, the
part headers in order). The ESQ effect index is rebased like NTR:

```
O=<assets>/out/original/r100/mesh; S=<assets>/out/standard/r100/low; M=<mirror>/st1
for n in 00 01 02 03 04; do
  python3 tools/room_smd.py release $M/r100_$n.dat $O/FILE_$n.re4mesh,$S/FILE_$n.re4mesh <rel>/st1/r100_$n.dat
done
for x in dar arc; do
  python3 tools/room_smd.py release $M/r100.$x $O/MAINSCENARIO.re4mesh,$S/MAINSCENARIO.re4mesh <rel>/st1/r100.$x \
    --common $O/COMMON.re4mesh,$S/COMMON.re4mesh
done
python3 tools/room_smd.py check $M/r100.dar <rel>/st1/r100.dar   # the release contract and nothing else
# stage: ROOMFILES="st1/r100_00.dat=<rel>/st1/r100_00.dat .. st1/r100_04.dat=<rel>/st1/r100_04.dat
#                   st1/r100.dar=<rel>/st1/r100.dar st1/r100.arc=<rel>/st1/r100.arc"
```

All 99 block BINs and all 31 room BINs release. The block pool (block.cpp checkBlockMemory:
the largest sum of file sizes over the BLK sets) drops from 1,126,272 to 39,808 B, and the
resident room archive from 2,615,168 to 1,918,528 B, both in heap 4 (the game reads only the
.dar; the .arc goes along like r101's). `release` writes nothing unless `check` passes on its
output. The released files need the r100 packages on the disc and `NATIVE_MESH=1`, as above.

## Warp rig (`DBG_WARP=1`, test builds only)

Starts a test build next to an event trigger or a door, with the scenario state that event needs,
seconds after boot, instead of a whole title -> intro -> r100 walk.

- **Build:** add `DBG_WARP=1` to the build flags (dbgwarp.mk, dbgwarp_bridge.cpp). With the default
  `DBG_WARP=0` the hooks compile out and the image is byte-identical. Never on a user disc: stage
  `warp.txt` only on test discs.
- **Config:** `/cd/dc/warp.txt` in the staged fixtures (FIXTURES_SRC). Write it from a preset:
  `python3 port/dreamcast/tools/d367/warp.py <preset> [--door] [--dump] -o <fixtures>/warp.txt`
  (`warp.py list` lists them). Lines: `room 0x100`, `pos x y z`, `ang <rad>` or `dir 0x8000`,
  `rsf <room> <bit>...` (room save flags), `scenario <0|1> <hex>`, `find <hex>` (Item_find_flg),
  `unlock <0|1> <hex>`, `inv default`, `act <room frame> <a|b|x|y|start|fwd|back> <hold>`,
  `trg <no> <room frame> [room]` (`--trg NO:FRAME[:ROOM]`), `kill <em id> <room frame> [room]`
  (`--kill ID:FRAME[:ROOM]`), `goto <room frame> x y z [ang]` (up to 4), `dump`. Issue #1 (2026-10-05):
  `act` also takes a raw GameCube button mask (`0x0020` = R, which the rig also gives the analog trigger the aim
  reads; `0x0120` = R + A, fire), and `arm <room frame> <item id>` (up to 8, first room) arms that weapon
  (ItemMgr.debugWeapon) and reloads it as SubScreenExit does when a new weapon is equipped in the inventory
  (SndBlkStop(2), weaponRelease / weaponLoad / weaponInit), logging `warp: arm item 0x2c ... loaded`. `census <room frame>` (up to 6, first room) logs heap 4's occupancy by allocation tag
  and its free cells (`warp: census ...`); PRIM_WATER=1 (test build) logs each room's peak primitive-buffer use
  per frame (`prim water: ...`).
- **What it does:** once the title data is loaded, the title, picker and menus are skipped and
  titleExit takes the debug-start path (config.txt [STAGE]/[ROOM] + START) with the warp room, so
  the room loads through the game's own new-game and room-load code. Quality comes from RE4DCCFG /
  quality.txt. `pos`/`ang` replace the jump point's NextPos/NextY. The flags are set once at the
  first room entry (after gameInit, before the room init reads them). `act` lines press a button or
  push the stick in the first room (door test mode), timed in PADRead calls (one per game frame in
  play; they keep counting inside the sub screen, so Y then B opens and closes the inventory); an event cuts the running action. `dump` logs
  every AEV area of the room (number, type, trigger, centre, door destination). `trg` makes the
  source's developer shortcut `DebugTrg(no)` (sce_com.cpp; the retail stub returns 0) return 1 once,
  at or after that frame of the current room (of `room` only, when given). r101_checkEmNum rings the
  bell on `DebugTrg(0)`, so the square fight reaches event 30 without 15 kills or the 11,700-frame
  timer. The fight before it is the game's own; everything after the bell is the game's own too.
  `kill` shoots the first live enemy with that model id dead through the source's own damage path
  (`cDmgInfo::set`, one hit per frame until its hp is gone), at or after that frame of the current
  room (of `room` only, when given; room frames stop while a movie owns the frame), so its death
  link runs as in play: `kill 0x12 400 0x100` is the s03 Ganado, whose death (r100_Sce_zombi_dead)
  runs the ambush set, s20, the after state and the post-house call. `goto` moves Leon (setPos,
  optional setAng) once at or after that frame of the first room, outside events, to walk him into
  an AEV area without a padscript. Log: `warp: kill 0x12 fired in 100 at room frame N hp=...`,
  `warp: kill 0x12 hp<=0 at room frame N after K hits`, `warp: goto I at room frame N pl=x,y,z`.
- **Log:** `warp:` lines give vblank and guest time for the title skip, each room entry, the
  placement and each action.
- **Stall diagnostics (`STALL_DIAG=1`, test builds only, dbgwarp.mk):** the vblank handler logs
  `vblank N loop=<vsync_cnt>` every 60 vblanks, and when the frame loop has not come round for 180
  vsyncs (then every 600) `stall: frame loop ...` with the interrupted PC/PR, the main thread's saved
  PC/PR/SP and its stack's text addresses (`stall: main stack:`), then the thread dump. Room loads,
  movies' ends and the sub screen hold the loop legitimately, so a report is a lead, not a verdict.
  With `STALL_DIAG=0` (default) vi.cpp is unchanged and the image is byte-identical.
- **Boot fixture:** a blank harness VMU asks to create RE4DCSYS; stage a padscript with
  `0 0008 3 card=8/1 3000` and `+20 0100 3 card=8/1 300` (clock source).
- **Base fixtures:** r101 needs 16 motion keys that `/root/probe/d354v7-fixtures` lacks
  (`RE4DC MISSING: motion key read` at r101 entry); `frontier/fixtures` has them.

| Preset | Room | Flags | Event it reaches |
|---|---|---|---|
| r100-spawn | 0x100 | none | s40 movie and the radio call (r100_StartEvent) |
| r100-post-radio | 0x100 | rsf 13, Scenario[0] 0x10 | play at the gate |
| r100-house-door | 0x100 | rsf 13, Scenario[0] 0x10 | s03 (area 0xA, r100_Sce_look) |
| r100-s20 | 0x100 | r100-house-door + its door act, kill 0x12 at 400 | s03, then s20 + the ambush + the post-house call (OpeSetOpenTerm(1)) |
| r100-s20-route | 0x100 | none; goto area 6 at 400 and area 0xA at 460, kill 0x12 at 700 | s40 + the first call (padscript: A every 90 vbl from vbl 1800), then as r100-s20 from a fresh r100 entry |
| r100-bridge | 0x100 | rsf 13, Scenario[0] 0x10 | s44 (area 0x1B, r100_EventBrige) |
| r100-east-door | 0x100 | rsf 13, Scenario[0] 0x10 | r101 door (AEV area 0, no lock) |
| r101-entry | 0x101 | none | r101 first visit |
| r101-bell-fight | 0x101 | find 0x2000 | r101 square fight |
| r101-bell | 0x101 | find 0x2000, trg 0 at 1200 | the fight, then the bell (event 30, r101s30) |

**A warp start is not STRICT against continued play.** The room is entered fresh with synthesized
flags; the RNG, timers, enemy list state, inventory and play time are those of a new game, not of
a run that played up to that point. Use warps for iteration and bring-up (does the door open, does
the event start, what does the room cost). Logic proofs, STRICT traces and route sign-off still
use normal runs.

**Heap-4-bound events need matched arena fits.** With ARENA_FIT the arena (and so heap 4) is sized
in 4 KiB steps from the image end, and the linker puts `.init` on an 8 KiB boundary after `.text`: a
few bytes of code that push `.text` over that boundary cost 8 KiB of heap 4. Where heap 4 runs out
(the r100 post-house ambush after s20) that changes which enemies, objects and parts get memory, so
compare arms only when their `re4dc_mem: arena fit` lines match (sh-elf-objdump -h: `.init` address;
sh-elf-nm: `_end`). Levers for test arms: STALL_DIAG, ROUTE_MOVIE_DIAG, PC_SAMPLER_BYTES (a .bss ring).

### Late activation: same-binary A/B (`late`, 2026-10-03)

Two arms built separately differ in timing before the window, and the house fixture is timing-sensitive (a 2 ms
delay-only control already FAILs STRICT from tick 777). So a render or schedule switch is compared inside **one ELF**:
the arms share the binary and the prelude, and switch at a fixed tick.

- warp.txt line `late <mask> [tick] [room]` (`warp.py <preset> --late MASK[:TICK[:ROOM]]`; defaults 1400 / 0x100).
  From global tick `tick` (pG->Frame_cnt) while the room is `room`, `RE4DC_WARP_LATE(bits)` (game/platform/include/
  warp_late.h) returns the mask's bits. Keep the line the same length in every arm (`late 0x00 1400 0x100` /
  `late 0x04 1400 0x100`). The first open call logs `warp: late 0xNN open at t=1400 room=100` in every arm.
- Bits (diagnostics, not production options):

  | Bit | Switch | Where |
  |---|---|---|
  | 0x01 | world LOD error 20 px | quality.cpp `re4dc_quality()` lod_px |
  | 0x02 | actor LOD threshold 8 px outside the mid-crowd rule | native_actor_fast.cpp |
  | 0x04 | Fast pacing from the tick; with `PACE_FORCE=A` every eligible image is dropped (no draw: a G diagnostic) | pace.cpp |
  | 0x08 | ACT_CAP only after the tick (ACT_CAP builds; a gameplay change) | act_cap.cpp |
  | 0x10 | Leon keeps the per-part source path (no native plan): the old-path arm of the WP2 Leon pair | coarse_actor_owner_leon.inc |

- DBG_WARP=1 builds only; with DBG_WARP=0 every hook is an `#if` block and the image is byte-identical.
- **H2** (architect review 2026-10-03): the r100 house after the s20 ambush, guarded PS2 worlds, the r21s texture
  pack (fixture `tour/pak-calls-r100-s30-pw.json` with the -uvg worlds and title-c14-pak.pak; provenance in
  architect-review-20261003/scratch-01a1025a/spikes). Cost window 1450:1569, all 120 frames traced:
  `hwproject.sh --count 1450:1569 --trace 1450:1569:1 --drop-traces`; work = total minus the rows `main`,
  `re4dc_pace_end`, `re4dc_vi_retrace_count`. Cost build: `route-build.sh impl-<x> PC_SAMPLER_BYTES=8192
  PACE_MODE=off ACT_CAP=0 ENC_CENSUS=1 ACTOR_CENSUS=1 MESH_CLIP_LEAN=1 PACE_FORCE=A LOGIC_TRACE=0
  GAME_DECISION_TRACE=0`; behaviour build: the same with `LOGIC_TRACE=1 GAME_DECISION_TRACE=1`. (MESH_CLIP_LEAN=1 was
  part of these arms before it joined the play recipe on 2026-10-03, ce39455f.)
- **Last tick:** the hwtrace Flycast exits right after the window's last frame, before the log reader drains it, so
  the trace log ended at 1568. `hwproject.sh --tail 3` keeps the emulator running and stops the reader (the tree's
  read_log.py, `RE4DC_LOG_STOP`) 3 frames later after a final drain; counts and traces are unchanged. A/A on H2
  (2026-10-03, impl-w0t, two runs, `late 0x00`): STRICT 120/120 (1450..1569), 100/100 before (1300..1399), room
  0x100 aligned 1391/1391.

### Cost, heap-4 and class options (W9b)

| Option | Effect |
|---|---|
| `--lod-bias OWNER:BINS=F` | Scales the stored level errors, so coarse levels switch in closer. r101: 0.25 on the heavy terrain/building BINs; r103: 0.375 (0.25 visibly thins its trees). |
| `--lod-floor [OWNER:BINS=]MM` | Level 0 is the source simplified to MM (world, source mm) before clustering. A part is only floored when its area and area-weighted normal stay within 0.2%. Otherwise it keeps the source. `2` removes 14-16% of level-0 triangles. |
| `--lod-share` | R4IM v3. Coarse meshlets index their part's existing vertices through a u16 table instead of storing copies: -133 KB (r101), -176 KB (r103), -176 KB (r100, all seven packages). Level 0 is unchanged. Only a runtime with v3 support adopts it (`room/instanced_mesh.hpp`). Lighting is still one pass per part, over the part's vertex pool. |
| `--class OWNER:BINS=CLASS`, `--class-auto`, `--class-rule CLASS=FULL_M,CULL_M` | Per-mesh scenery class (default, ground, tree, landmark, clutter, structure) and per-room distances, both optional, in the v2/v3 LOD header. A shared runtime distance rule reads them through `mesh_class()` / `class_rule()`. `--class-auto` tags card fields and replaced BINs as tree. Other BINs become ground, clutter or structure by world extent (`auto_class`). Landmarks are only tagged by hand. |

Current r101/r103 recipes (the model's worst view at a 25 m fog far: r101 10.1-12.8 ms, r103 10.9-14.0 ms):

```
# r101 (after the PS2 tree step above)
... --lod-substitute <trees> --lod-bias 0xff:13-17=0.375 --lod-bias 0xff:3,9,12,34,70,64,31,29,38=0.25 \
    --lod-floor 2 --lod-share --class 0xff:13-17=tree --class-auto
# r103
... --lod-bias 0xff:38,59,60,62-67=0.375 --lod-bias 0xff:0,18,61,17,24,28=0.375 \
    --lod-floor 2 --lod-share --class 0xff:38,59,60,62-67=tree --class-auto
```

The runtime keeps a v3 meshlet's gathered corners in a 3 KiB buffer in the package's own heap-4
allocation (not the packet range: with MESH_DIRECT too few slots remain there after the part headers).

## Room discovery (`assets.sh discover <room|route>`)

The first stage of the room pipeline: what a room can load, and whether the build and the prepared
disc provide it, from the source data alone (no emulator, seconds). Run it before building a disc for
a room, and after changing MODULES, the module table or the prepared archives.

```bash
bash port/dreamcast/tools/d367/assets.sh discover route                 # r100 r101 r103
bash port/dreamcast/tools/d367/assets.sh discover r100 --log <evidence>/run-output.txt   # + compare a run
bash port/dreamcast/tools/d367/assets.sh discover r100 --repo <tree> --obj <OBJDIR>      # another tree/build
```

- **Demand:** the room's enemy list (stage.cpp checkEmListNo; stage 1 mirrored so far), each entry
  of the room (alive bit set: spawns at entry; clear: `enabled-later`, e.g. em2a in r100 after s20),
  the room script's `EmSetFromList2` spawns and `EmReadSearch`/`SearchEmModule` loads. Enemy id ->
  read.cpp `EmFileTbl` -> dvd.cpp `FileTbl`: archive (`em/emXX.drs`) and REL module.
- **Checks:** Makefile MODULES, the ENEMY_DEMAND audit list, platform/modules.cpp
  `MODULE(<rel.json module_id>, name)`, missing-symbol stubs naming the module (`--obj`/missing.txt),
  the prepared archive (sources.toml `prepared_mirror`), at most 4 live enemy archives
  (EmReadModule[4]), and heap 4: the prepared header's allocation (u32 at 0x24, as "DVD: Mem Alloc")
  summed over every archive against `[room.X.demand] enemy_heap4_bytes`, a measured value
  (free at an enemy read + the enemy allocations live then). A room without one says so; record it
  from a run log.
- **`--log`:** archives the run loaded that were not predicted (a discovery gap), failed reads, the
  first `alloc[..]:free[..]` shortfall, HALTs, and the linked modules.
- Output: the report, `<assets_root>/discover/<room>.json`; exit 1 when anything is a problem.
- Proof (2026-09-24): on dadfbac (before e6f65cc) it reports em2a missing from MODULES, the audit list and
  the table (the warp-east-1 HALT main_sub.cpp(1440)); on r100 the worst case is 171,328 bytes over the
  measured room, the exact shortfall warp-ea4-after logged at the em23 (crows) read; r101's
  prediction equals what warp-bell1 loaded.
- **Lint** (tools/assetpipe/wiring.py): the known porting traps in each needed module and the room's
  stage module, in the code the Dreamcast build compiles (`#if` evaluated with `__PPC__` undefined):
  `value-init` (`new (em) cEmXX()` zeroes what cEmMgr::construct set), `asm-alias` (an asm-label
  alias of a file-static binds to a missing-symbol stub), `slot-math` (`EmMgr.pArray` / `EmMgr.size *`
  instead of `EmMgr.workAt` + null check), `vptr-offset` (`(u8*)this + 4 + ...`, warning). Errors
  are problems.
- **`--wire`:** writes the missing wiring into `--repo` (default this tree): Makefile MODULES,
  `MODULE(name)` and `MODULE(<rel.json id>, name)` with a room/reason comment, and the ENEMY_DEMAND
  audit list only when the module's lint has no errors. It links the original module's code; game
  logic is never generated. Review the diff and prove the room as usual.
- Proof (round 2): on dadfbac, `discover r100 --wire` writes e6f65cc's Makefile/modules.cpp lines and
  the lint reports the four traps that commit fixed by hand (em2a value-init, slot-math, asm-alias;
  em21 asm-alias); the audit entry waits for them.
- **Heap-4 options** (tools/assetpipe/enemy_heap.py): each live archive's prepared body by tag, and
  the lossless ways to shrink it: `rel-strip` (the REL copy of a linked module; exact),
  `tex-upload` (TPL texels to VRAM), `motion-stream` (FCV keys through motion leases), `effect-compact`
  (unmeasured). Each is `applied`, `qualified` (prepare_enemy_motions.py supports it for that
  archive; its GANADO/SMALL tuples are read from the tool) or `needs-contract`, read against
  sources.toml `enemy_compaction` (the compaction summary). A SHORT room gets a plan: qualified
  options first, then the largest needs-contract ones. r100 (2026-09-24): nothing qualified is left;
  em21 motion-stream (<= 294,240 B) alone covers the 171,328 B crows shortfall; em23 + em2a
  (motion + textures + em2a's 17,152 B REL) is the alternative.
- **Events** (tools/assetpipe/events.py): every `evd/r<room>sNN.evd` the room script names, read from
  the GC ISO: size, asset bytes, actors (kind-3 model sets: em10/em13/em15/em16 Ganados, pl00 Leon,
  pl07 Ashley, obm objects ...). An evd is self-contained (its asset table holds the models,
  textures and motion), so event actors need no enemy REL or archive. The check: a route movie
  (sources.toml `route_movies`; the movie presents the event, the evd is never loaded) or the
  prepared evd with its qualified `.evq` (native_event_file.cpp refuses one without). Names not on
  the disc (r100s01/s02/s42) are listed only. Route (2026-09-24): every r100/r101 event has a movie,
  r101's evds are also qualified, r103 names none.
- **Standard + VRAM** (tools/assetpipe/standard.py): from the room's Standard set index
  (`<assets_root>/out/standard/<room>/low/index.txt`): package bytes vs Original (the native static
  package is heap 4, so the Standard enemy heap-4 room = the measured one minus that delta) and the
  VRAM Standard adds (`tex` records; `drop` textures are not subtracted: an upper bound) against
  `[room.X.standard.budget_context] vram`. Standard assets load only with QUALITY_ASSETS=1, so
  measured budgets so far are Original packages. With `--log`: lowest texture-pool free, peak used,
  rejects, and texture packages the room loads that are not on the disc (`open failed`).
  Route (2026-09-24): Standard r100 -282,560 B of packages, so the crows fit with QUALITY_ASSETS=1
  (111,232 spare; Original stays 171,328 short); r101 -423,328; r103 -406,496. VRAM upper bounds
  leave r101 >= 32,000 and r103 >= 145,536 free. warp-dbp0-fight-orig: lowest free 10,280 and 16
  texture packages missing on that warp disc (a staging gap to trace).
- Not covered yet: other stages' list rules.

## GDEMU image (W10)

`GDI=1 GDI_OUT=/mnt/d/... stage.sh ...` also writes a GDI from the same tree through
`mkgdi.sh`, which also runs on its own with the `mkdisc-hardlink.sh` arguments:

| Track | LBA | Content |
|---|---|---|
| 01 | 0 | MODE1 placeholder ISO, 606 sectors (low-density area) |
| 02 | 756 | Audio, 302 sectors of silence |
| 03 | 45000 | IP.BIN plus the game ISO9660, with absolute extents (`genisoimage -C 0,45000`) |

- 1ST_READ.BIN is unscrambled, as a GD-ROM boot requires.
- IP.BIN fields: device `GD-ROM1/1`, area `JUE`, peripherals `0799810` (VGA, VMU,
  Start/A/B/X/Y/d-pad, analog stick and triggers).
- KOS mounts `/cd` from the low-density TOC. The game links with
  `-Wl,--wrap=cdrom_read_toc` (`game/platform/gdrom_mount.cpp`), which gives fs_iso9660
  the high-density TOC on a GD-ROM, and the boot log shows `gdrom: /cd from
  high-density TOC`. CD-R images are unchanged. Every file the game reads must be in
  track 3.
- `SECTOR=2352` (the default) writes raw MODE1 tracks with EDC/ECC (`mode1raw.c`, built
  with the host cc). `SECTOR=2048` writes `.iso` tracks. Either way the user data is
  2048-byte MODE1.
- To test in Flycast, boot `disc.gdi` (evidence `gdemu-a`; control `gdemu-a-cue`).
- Play discs come as two artifacts (2026-10-03): `<rNN>-title/disc.cue` (one MODE1/2048 track, 2048-byte logical
  sectors; what the launchers boot in Flycast) and `<rNN>-gdemu/disc.gdi` (raw 2352-byte sectors; user data at
  byte 16 of each sector). A Flycast boot of the CUE image does not validate the GDEMU TOC or physical media.

### Disc IO probe and door-load telemetry (`IO_PROBE=1`, default 0)

Diagnostic builds only; the default image does not change.

- `MOTION_FAST_READ=1` (default 0): motion keys are read whole into their aligned
  residency block (98 -> 0.18 ms per key in Flycast).
- `IO_PROBE=1` adds `platform/io_probe.cpp`, which runs timed disc reads at the end of
  OSInit when the fixture `ioprobe.txt` (staged as `/cd/dc/ioprobe.txt`) exists, e.g.
  `seq=8 cold=48 opens=50`. Results go to `ioprobe:` log lines, the `re4dc_ioprobe`
  struct, VMU LCD pages and a PERF_HUD row.
  - The stream phases `idle=N load=N` default to 0 (off): in Flycast they faulted or reset
    the guest in 4 of 6 runs. Pass them only for diagnosis.
- With the room cycle fixture (`roomcycle.txt`, `door 3 300`) each room entry logs one
  `iotime: door` and one `iotime: steady` line: wall time, game frames, source DVD
  blocking and motion-key waits. Read them with
  `tr -d '\0' < run-output.txt | grep -a "iotime: door"`.
- `platform/io_wrap.cpp` links `--wrap=fs_read,fs_open,thd_sleep,genwait_wait` and prints
  `iowrap:` lines with each `iotime` line: blocking time by file path, by caller (return
  address, symbolize with `symbols-demangled.txt`), by KOS wait kind and thread, and per
  thread.
