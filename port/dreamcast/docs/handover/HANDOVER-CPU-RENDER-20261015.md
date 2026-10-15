# Handover: RE4 Dreamcast CPU/rendering optimization + PS2 Chapter 1 POC (2026-10-15, ~19:30)

Labels used throughout: **CONSOLE** = measured on the user's NTSC Dreamcast (GDEMU, benchmark discs). **FLYCAST** =
emulator measurement or count. **MODELLED** = SH-4 hw-model (hwproject) estimate. **EST** = estimate from code/counts.

## 1. Code references

Repository: `https://github.com/lamb2k/re4dc` (origin). Local clone (WSL Ubuntu-24.04): `/root/work/re4-dreamcast`.
Public branch `dreamcast-port` 5d44dc0d. Remote `bruce` = Bruceleeto/re4dc (never push there).
All branches below were pushed to origin on 2026-10-15 19:20.

| Branch | Tip | Worktree | What |
|---|---|---|---|
| **t15/int** | c5ef4ade | /root/probe/lanes-20261015/t15int | **Best starting commit.** Test 15 integration: test 14 fixes + GC_CENSUS_TRIM, PS2 cast ch1-1..2-1, KOS_SBRK_LAST_PAGE, GANADO_LOD g70, HUD fix, SH4ZAM via kos-ports v0.9.1, hw-model refit tools. Recipe: `port/dreamcast/tools/d367/test15/t15-build.sh` |
| lane/actorplan | a4d28b22 (WIP) | /root/probe/lanes-20261015/actorplan | Character draw plan / one-pass kernel: pricing tools + doc only, no source change. Base t15/int cb4e24c6 |
| lane/worldvert | 713f9319 (WIP) | /root/probe/lanes-20261015/worldvert (+ worldvert-work) | World vertex ladder converter + WORLD_VERT knob. **Base is the test 13 lineage** (b933f62a, on lane/worldlod 6f3defad, on 1c79d543): rebase or merge onto t15/int |
| lane/sh4zam-adopt-kp | 4d783211 | /root/probe/lanes-20261015/sh4zam/adopt (local branch name lane/sh4zam-adopt) | SH4ZAM knobs (all closed or default off), memcpy lint, upstream notes. Base t14/rc e2048df6 + kos-ports switch |
| lane/storemiss | 8aa745ab | /root/probe/lanes-20261015/storemiss/tree | hw-model refit (`hwsim --console-fit` = data fill +6, I fill +5, store miss 0); rank/refit/reprice tools. Merged into t15/int |
| lane/t2exact | 37bb9b8a | /root/probe/lanes-20261015/t2exact/tree | SG_SELECT_LEAN (closed), HOT_COLD_SPLIT/PS2_PVS (off), strip-group pricing per room, back-face ceiling (cone.py) |
| lane/logicwaste | befad291 | /root/probe/lanes-20261015/logicwaste/tree | LOGIC_WASTE_MASK 0x02 (exact, keep), LOGIC_APPROX_MASK 0x01 jacket cloth half rate (approx, look review pending) |
| lane/leonlod | 4988dacb | /root/probe/lanes-20261015/leonlod | LEON_LOD (stays 0), GANADO_LOD (g70 = level 2, in t15) |
| lane/poc101 | 39136d68 | /root/probe/lanes-20261015/poc101 | POC101 stacked-lever bench disc (runtime rows). Its DETAIL row did NOT load LOD packages: ignore it |
| t14/bench | f6515b50 | /root/probe/lanes-20261015/t14rc/bench | Benchmark disc program (bench.cpp, Part 1/2 scenes, sweeps) on the test 14 candidate |
| t14/rc | 2830c60c | /root/probe/lanes-20261015/t14rc/tree | Test 14 candidate (KOS_DMA_DONE_FIX). **Blocked: r118 fault** (see 4) |
| lane/flycast-console | 75091290 | - | Harness: fp_run.py RE4DC_EMU=console, gdemu_gate.sh |

Local-only, not in the GitHub repo: the console-like Flycast fork at `C:\Game Dev\Emulators\flycast-console`
(branch console-like 41905914, no remote). Bundle: `patches\flycast-console-41905914.bundle` (163 MB, `git clone` it);
patch: `patches\0001-flycast-console-*.patch`. Exe: `C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe`.
Use it for crash repro only, never for timing.

Dependent changes elsewhere:
- kos-ports at `/root/work/kos-ports` f4faacc4, SH4ZAM 33fa4850 installed. Pins are in `toolchain.lock`; install with `port/dreamcast/tools/install-sh4zam.sh`. Never vendor SH4ZAM.
- The patched KOS d367 is required: build-r21.sh defaults to it; d336 lacks the vbuf-switch patch.
- The KOS DMA fix patch is `kos-804b319-cdrom-dma-done.patch` (KOS_DISC_FIX=1, forced by DISC_COMPAT=1).

## 2. Current progress

Target plan (adopted by the user): `CPU-SAVINGS-PLAN-20261015.md`. Keep the fast vertex maths and rebuild the feed path
as prepared Dreamcast data plus a small runtime loop. Order:
1. Village world L2.
2. Character draw plan.
3. Fused character vertex kernel.
4. Scenery batching in spatial cells.

Provisional target: 74 -> 55-62 ms per drawn tick at the r101 cross.

| Item | State | Numbers |
|---|---|---|
| Step 2: character draw plan (ACTOR_PLAN) | **Proposed and priced only. Not built.** | t15 base arm ap0rW: 61.85 ms/frame MODELLED (bench r101-t12 frames 500:799). Leon + Ganados owned path 10.04 ms (vertex 4.58, pose 0.70, **setup 4.77**). Objects path 2.30 (setup 1.63). Ceiling -2.9..-3.4 ms corr, realistic -1.5..-2.5 MODELLED. Items listed so far sum to only 1.5-1.7 ms (under the 2 ms build gate); asset-load preparation is what clears 2 ms |
| Existing exact knobs ACTOR_PROOF_LEAN / ACTOR_MATERIAL_RECORD / ACTOR_BIND_REUSE | **Known anomaly.** The image is byte-identical with them on (arm ap1rW), so the saving is 0.00 | -D flags reach the coarse_actor.cpp compile (build.log line 924), but coarse_actor.o is unchanged: investigate the `#if` chain around coarse_actor_transaction.inc and coarse_ganado.o with -E |
| Step 3: one-pass character vertex kernel (ACTOR_ONEPASS) | **Proposed only.** | Ceiling -1.0..-1.3 ms MODELLED (lower with GANADO_LOD=2). The emit pass (Part::whole) copies by index, so it can't fuse without duplicating vertices. XMTRX holds the skin matrix. s8 normals alone are worth 0.14 |
| Step 1: village world L2 (WORLD_VERT=1, WORLD_VERT_LEVEL) | **Built (WIP). L2-fixed data made; not priced, no gates.** The user's verdict is "Village L2 salvaged" (L3 dropped) | FLYCAST world vertices per frame: mean of 8 cameras L0 18.6k -> L2-fixed 13.5k (-28%); cross 17.7k -> 12.6k. The sliver fix (screen-error bound + thin-part guard) cost ~4 points of reduction. L2-fixed sheet `C:\Game Dev\Emulators\worldvert-20261015\WORLDVERT-R101-L2FIX.png` is NOT yet reviewed or shown to the user. _end +0x180 with the knob on |
| Step 4: scenery batching | Only a proxy arm (wv2 = L2-fixed in 256-vertex meshlets: 804 vs 1,335 meshlets, pixel-identical, but 15.5k vs 12.6k vertices sent to the TA). Net ms not priced. Spatial-cell merging not started | - |
| SH4ZAM | Render-only FTRV/FSCA arm adopted for test 14 (GAME_SH4ZAM_RENDER_ONLY). Every other SH4ZAM arm is closed or off | Skinning on SH4ZAM: +3.79 ms (+4.74 corr) MODELLED, so our asm stays. shz_memcpy ~2x newlib instructions (31-byte byte-loop prelude): +0.15. GAME_SHZ_MEMSET: -0.65/-0.55, likely layout luck (the function ties newlib). GAME_SHZ_MEM global wrap: off by default, **open hang bug** (house run stuck in texture/movie loading with memcpy on; the main-RAM-only guard 3870142e is unproven) |
| GANADO_LOD g70 | In the t15 recipe | -0.55 cross / -0.12 house MODELLED (refit) |
| LOGIC_WASTE 0x02 | Exact; being merged into t15 | -0.23 cross MODELLED |

## 3. Evidence

All in `C:\Game Dev\Emulators\` unless a path is given. Copies of the key docs are on the pushed branch
`handover/chatgpt-20261015` under `port/dreamcast/docs/handover/`.

- **CPU accounting (the answer):** `CPU-ANSWER-20261015.md`.
  - The vertex kernels run at 35-38 cycles a vertex. The cost is fixed fees: ~616 world meshlets x ~3.4k cycles, and ~75 character part draws x ~30k cycles through 4-5 layers.
  - Drawing is ~55 of 99 ms per picture (CONSOLE total; split MODELLED). Logic is ~33 ms and is real simulation.
- **Plan:** `CPU-SAVINGS-PLAN-20261015.md`.
- **Backlog:** `PERF-BACKLOG-CH1-2-20261015.md` (+ .csv; the evening status section is at the end), `PERF-BACKLOG-PER-ROOM-20261015.md`, `WORLD-BUDGET-BY-ROOM-20261015.md`, `RE4DC-PERF-ALT-VIEWS-20261015.md`, `RE4DC-HW-ONLY-COSTS-20261015.md`.
- **hw-model calibration:** `HWMODEL-CALIBRATION-20261015.md`.
  - Calibration trace: `D:\Flycast-Evidence\re4-dreamcast\hwcal-20261015\hw-cross` (bench 76f40d95, r101 cross, 40 ticks).
  - Current console fit: data fill +6, I fill +5, store miss 0. Render still under-priced x1.07-1.19.
- **RAM budget:** `RAM-BUDGET-20261015.md` (KOS is the binding pool; test 15 measured squeeze headroom ~11 KB on every segment).
- **CONSOLE benchmark results:** memory note `C:\Users\lambd\.claude\projects\C--Game-Dev-Emulators\memory\re4-dreamcast-console-benchmark-20261015.md`.

  | Scene / sweep | CONSOLE result |
  |---|---|
  | Cross | 99.8 ms/picture: LOGIC 33.1, ACTOR PREP 2.8, ACTOR DRAW 28.4, WORLD 19.1, OTHER 15.8 |
  | House | 77.4 ms/picture |
  | Del Lago | 60.6 ms/picture |
  | Farm | 142 ms/picture |
  | Cross frozen sweep | 72.0 ms with 41k vertices. No world: 49.0. World cut to 18.8 m: -3.9 ms. World cut to 12.5 m: -7.9 ms. No effects: -1.2 |
  | Per-scene memory waits | D-stall ~30%, I-stall ~20% |
  | Bench A (ACTOR_MOVCA) | 0 change |
  | Bench B (MEM_MOVCA) | +0.5 ms |
- **Benchmark discs:** `RE4DC-Benchmark-Part1-b7aba292`, `-Part2-b7aba292` (build 76f40d95 + bench), `RE4DC-Bench-POC101-39136d68`, and the LinkOrder D3/D3-CTL/D3-FIX discs. SD install script (user-run): `re4-batch-sd-linkordd3-20261015\update_sd_linkordd3.py` (slots 158-162).
- **Lane evidence:** `C:\Flycast-Evidence\re4-dreamcast\{actorplan,worldvert,sh4zam-skin,storemiss,t2exact,logicwaste,leonlod,t15int,discread,rambudget}-20261015\`.
- **Lane docs:** in each branch, `port/dreamcast/docs/lanes/{actorplan,worldvert,sh4zam-adopt,sh4zam-upstream,t2exact,hwmodel-miss,leonlod}.md`.
- **Build commands:**
  - Test 15 recipe: `bash port/dreamcast/tools/d367/test15/t15-build.sh`. The data set T15_DATA is in `tools/d367/test11/t11-fix.py`.
  - Public kit: `build-public.sh` (needs `install-sh4zam.sh`).
  - Lane arms: actorplan `build.sh`, `hw.sh`, `cg.sh`, `owned.py` (lane doc); worldvert `/root/probe/lanes-20261015/worldvert-work/{build.sh,hw.sh}`.
  - Testing skill: `C:\Users\lambd\.claude\skills\re4-dreamcast-testing\SKILL.md` (warps, staging, STRICT, identity, align, kos_squeeze.sh, trace_lock.sh 4 slots).
- **Chapter 1 assets and tooling inventory:** `C:\Game Dev\Emulators\HANDOVER-CH1-ASSETS-20261015.md`.
  - **In progress when this was sent.** A read-only agent is filling in: rooms/characters with conversion coverage; private assets, manifests and hashes; Blender; PS2 tools; toolchain; remaining GC dependencies; reusable renderer work.
- **Private game data:** `C:\Game Dev\Emulators\re4-assets-private\`. This is copyrighted; local paths only, never upload it.
  - World ladder data: `worldvert-20261015\r101-v2` (wv1 = L2-fixed, wv2 = 256-vertex meshlets), built from `crowd12-bake-20261015\r101-t13`.

## 4. Immediate state
- **Running jobs: none in the handed-over lanes.** actorplan, worldvert and sh4zam are stopped, with clean trees and everything committed.
- **Still running, owned by me and not overlapping:**
  - the r118 crash hunt for test 14 (branch lane/r118fault, to be created);
  - test 15 integration (t15/int: merging LOGIC_WASTE 0x02 and the prune-tool branch, and making a jacket-cloth motion still pair).

  Coordinate before rebasing t15/int.
- **Known failures:**
  - **Test 14 candidate faults entering r118** on the cap-6 decisions fixture mx-r118, 3/3 runs (FAULT in the vblank handler with a garbage handler node). It doesn't fault without KOS_DMA_DONE_FIX; t15/int carries the same fix. A layout- or timing-dependent memory corruption is suspected. Evidence: `C:\Flycast-Evidence\re4-dreamcast\t14rel-20261015\rmx-r118*`.
  - The GAME_SHZ_MEM memcpy hang is open.
  - The three actor knobs compile to nothing.
  - The actorplan `hw.sh` stops with "rc: unbound variable" after the projection.
  - hwsim_cg (call tree) is nominal-only, with no console fit.
- **Incomplete:** the worldvert L2-fixed sheet review; wv1/wv0 pricing (commands in worldvert.md: `bash /root/probe/lanes-20261015/worldvert-work/hw.sh wv1 wvF-cross cross`, etc.); the gates for WORLD_VERT; and the `re4dc_world_vert_level_set` in-place switch, which has never been exercised.
- **Next experiments I was about to run:**
  1. actorplan: find why the three knobs compile out (-E on coarse_actor.cpp), re-price ap1rW, then ACTOR_PLAN item 1 (remove the double preflight, ~0.25 ms nominal).
  2. worldvert: price L2-fixed against L0 at the cross and the house, calibrated to CONSOLE -7.9 ms; then wv2 on top; then the gates; then POC102.

## 5. Critical constraints
- **Gameplay:** collision, scripts and sequencing stay GameCube logic. Logic changes must be decisions-identical (STRICT fight/bell/door103 MUST-IDENTICAL). Approximations are allowed as default-off runtime switches with a gameplay-equivalence gate (same kills, triggers, doors, waves, room clears, cutscenes). Visible changes need still pairs, and the user judges the look.
- **Look decisions:**
  - Leon stays the full PS2 model, jacket on (LEON_LOD=0; never remove the jacket).
  - Ganados use g70 in gameplay, full models in cutscenes.
  - Village world uses L2.
  - The effects lane is on hold (effects cost ≤1.2 ms CPU on CONSOLE).
- **Enemy cap:** max 6 Ganados alive. Hold new spawns and park (never delete) the farthest off-screen ones; PS2 per-chapter spawn logic.
- **Memory:**
  - Main RAM 16 MB is tight. The KOS pool is the binding resource.
  - KOS squeeze gate: 48 KiB through fight/call/door103/leave100/leave103 must pass, 10 runs. Report the _end delta and the heap-4 delta.
  - The r100 s30 cliff movie is already short of heap 4 (known issue).
  - VRAM 8 MB: keep room textures resident, with no disc reads in play. Size buffers to need and keep a VRAM map.
- **Validation for each change:**
  - knob-off identity (`objcopy -R .stack` image hash);
  - STRICT/decisions;
  - TEX_CHECK + LEON-GC 0;
  - align logger 0;
  - KOS squeeze;
  - GDEMU race gate (console-like Flycast, RE4DC_GD_PROFILE=gdemu, 10 seeds, 0 bad reads) for release candidates.

  Each Flycast check is 1 minute or less, warped to the event and run in parallel. Measure each saving incrementally on top of the previous stack. Label MODELLED vs CONSOLE. Cache, layout, GPU and disc levers count only from CONSOLE A/B.
- **Ownership/lifetime:**
  - Agents commit locally; the coordinator lands and pushes.
  - Never vendor kos-ports libraries.
  - Private assets never go in git.
  - Stay on C:.
  - Delete your own rebuildable outputs after the gates; raw traces are deleted after 24 h unless they're in keep.txt.
- **Ruled out (don't redo):**
  - **Write-miss levers** (MOVCA, SQ, store-miss PREF): CONSOLE Bench A = 0, Bench B = +0.5; the refit puts store misses at 0-5 cycles.
  - **Back-face culling before the transform:** the 61% of corners that feed only back faces share corners inside meshlets; the best grouping nets ~0 at the cross.
  - **SH4ZAM:** skinning (+3.8 ms), logic arm (<0.4), memcpy (slower).
  - **Small levers:** SG_SELECT_LEAN (-0.18 real, fails squeeze); UI_OT_CACHE (-0.13); far-Ganado half rate D1 (~0); FX half rate (dropped).
  - **The logic-waste census items** except 0x02 and the cloth.
  - **Never measured:** LINK_ORDER (I-cache, ~20% of CPU) has never been measured on CONSOLE. The D3-FIX vs D3-CTL A/B discs are ready (SD slots 159-160) and waiting for the user's run. It fails the squeeze at leave100/103 without KOS_SBRK_LAST_PAGE.
