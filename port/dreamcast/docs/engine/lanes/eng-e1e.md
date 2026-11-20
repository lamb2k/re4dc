# Lane eng-e1e: the E1 audit's image-side findings (native services wired, publication out, heap, rumble)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-e1e\HANDBACK.md`. Evidence `E:\RE4DC-Lanes\eng-e1e\ev`,
runs `E:\RE4DC-Lanes\eng-e1e\runs`, scripts `E:\RE4DC-Lanes\eng-e1e\s`. Every run is **Flycast** (std slots), a function
check, engine against engine unless named; **no timing figure is claimed** (plan: no model-only speed round while the
console is unavailable). Item 8 (staging a disc) was dropped by the brief.

## Results by brief item (start addendum order)

| Item | Result |
|---|---|
| 4. Wire the round-4 native services | done in the image: `game/Makefile` links `services/{volumes,collision/col_model,routes,motion/follow,model/model_svc,camera/camera_svc,input/input}` before the hosted objects; `hosted.mk`, `fight.mk`, `boss.mk` no longer link model, motion, cMotBase, atari, atariInfo, at_mod, at_sub, pad, route_ck, view, camera, cam_motion; cam_ctrl / cam_sys / cam_extra keep their decisions with every native-defined symbol weakened (`SPLIT_UNITS`); `eng_pres_u8` exported. `check_link.py` SERVICE functions: default **241 -> 98**, FIGHT=1 **843 -> 677**, BOSS=1 **471 -> 321** (what remains: table below). |
| 2. Heap alias | fixed: heap 0 holds the arena's first 0x1000 bytes, room heap 4 the rest; `MemCreateHeap` refuses an overlapping range; heap-map check after the room load (PASS); `HEAPCK` allocate / free / reuse exercise on heap 4 (PASS); control `HEAPBAD` (the old map): map FAIL, exercise FAIL. |
| 3. Rumble | the native input service draws a random-strength rumble from the presentation generator (`eng_pres_u8`). Controls on the wired image: presentation seed only (`PSEED`) changes no gameplay field (village, hill, fight: hits 5, spawns 4); game seed (`SEED`) changes them; the audit's fault re-introduced (`RUMBLERND`) changes them. |
| 1. Publication out | palette published once a tick in the renderer's skinning layout and read in place; light records kept by a light service and rebuilt only when their inputs change; camera and HUD written in the renderer's form by the steps that produce them. Pictures identical to the image before item 1 (village 17/17, hill 19/19). |
| 5. Timing hygiene | log lines buffered while the ticks run (printed after the loop, dropped lines counted); the Drawing row is the renderer's stamps 5 -> 7 as the model's; route entry points counted in the services row. Not done: the presented-field counter (a console item). |
| 6. Village plays-right | not closed. Final image against the old game: decisions 641/641, angle within 0.241 degree, position 523/641 (worst 5.12) as in E1d. New evidence (engine only): a game-seed-only change moves the yaw 2.52 degrees and the position up to 47 units in the same aiming phase. re4ref with the same actor set and the engine's seed: generator, motion and discrete state 641/641, yaw differs from tick 424 (open). Shot-and-hit outcome: fight image (Ganados, `hit 5`) under the seed controls; `GetWepTargetPos` in the default image is still a stub. |
| 7. Look | listed (below); no fault fixed in this lane. |
| Also: `svc4_units.sh` | exits 2 ("no check made") on a missing, empty or non-re4ref map instead of "0 original functions kept"; controls recorded. |

## Item 4: what the default image still links from original code (98 functions, 22,468 B)

From `ev/link-w4-img.txt` (`check_link.py`), by unit. None of these units had a native version in eng-svc4's round:
- leaf math: `game/math_sub` (21: COSF, SINF, SQRTF, LIMIT_ANGLE, MtxNN*, RotMatrix, TransMatrix, ScaleMatrix,
  SetOrientationZX/ZY, VecAngle, VecElevation, VecLinearCombination, VecRadLimit, de_Boor_Cox, ...), `game/sub2` (13:
  AddSpeed, Front_check x2, GetDistance x2, GetDistance3, GetXZAngleLocal, Muku, Muku2, Muku3, PosToPos, RootSumSquare3,
  RotVector);
- garment pose: `game/pl_cloth` (8: PlClothSet/Move Leon and Girl, girlLapelMove, test*Set*);
- SDK math and allocator: `sdk/mtx` (12), `sdk/vec` (10), `sdk/OSAlloc` (7), `sdk/mtx44` (2), `sdk/mtxvec` (2),
  `sdk/quat` (2); fdlibm (13 functions);
- the laser-sight drawing in `game/objWep` (4), manager templates in `game/pl_npc` (2: cManager<cLight>) and
  `game/pl_sub` (2: cEmMgr::memClear, cManager<cEm>::createBack).
FIGHT=1 and BOSS=1 add the enemy and room-script units (em10, em2b, sce_at, em_sub, r101, r119, em_set, dmg, emtree,
emtorch, sce_com, game, area, em_wrap, em15_set, obj20, libgpu, em_dm_val): the allowed list has no group for enemy
decisions yet, so they count as service (`ev/remaining-w4.md` lists every function).

Stubs added: `cSatMgr::create(Vec*, Vec*, Vec*, int, int, f32)` (fight image only: the scenario's quad collision piece,
no native builder; logged). Native added: `YarareInitCube` (volumes.cpp, the fight's shoot-down item).

## Item 1: conversions removed (counts per picture or per tick; no time figures)

| Conversion (audit section 2) | Before (per picture) | After |
|---|---|---|
| Palette to skinning rows | per visible actor, per used bone: 48-byte copy, 9 multiplies (1/16), column scale (9 mul, 6 add, sqrt); world x pack bind recomputed on a bind mismatch | none in drawing: `skel_publish` writes the final layout once a tick (`SKEL_PAL_DRAW`, image only), for every bone of each table; a bind mismatch is reported as a bake fault (0 of 41 / 37 / 64 / 26 bones in the checked models) |
| Light record (characters but Leon) | 17-word record built from cModel and a scan of the pack's light records, every picture | the light service compares a 14-word input snapshot once a tick and rebuilds on change: hill 728 checks, **25 builds**; TEV scales resolved once a pack; 0 draw misses |
| Leon's light record | a scan of the pack's records every picture | looked up once a pack |
| ActorPose copies for the light rule | 2 x 48 bytes per actor | none (matrices by pointer, `source_lights_w`) |
| Camera stream | 26-word repack + 26-word copy | 18 words written in the renderer's stream right after `CameraMove`, once a tick; constants once at open |
| HUD words | 4-word build + 16-byte copy | 4 words written at the end of the tick |

Checks (Flycast, stills from the frame buffer, `s/stillcmp.py`): before/after item 1, village **0 of 17** and hill
**0 of 19** pictures differ (runs w2-vilst / w3-vilst / w4-vilst, w2-hillst / w3-hillst / w4-hillst). Controls:
`PALCTL` (palette read with the old 12-float stride) 19 of 19 hill pictures differ; `CAMSTALE` (first camera only) 17 of
17 village pictures differ; `LIGHTCTL` (records with a black material) see the hand-back; `LIGHTSTALE` (records never
rebuilt: 1 build instead of 25) changed none of the 19 sampled hill pictures, so the rebuilds are not visible at those
pictures and LIGHTSTALE is not a picture control.

## Items 2 and 3: checks and controls (Flycast)

| Check | Run | Result |
|---|---|---|
| Heap map after the room load | w2-vil, w4-vilst, w4-hillst | `HEAPMAP faults 0: PASS` (heap 0 8cc000a0-8cc010a0, heap 4 8cc010a0-8cec0000) |
| Heap-4 exercise (HEAPCK) | w2-vilhc, w4-vilhc | blocks in heap 4, the freed cell reused, used count restored: PASS; gameplay identical to w2-vil |
| Control HEAPBAD | w2-vilhb, w4-vilhb | map FAIL (heap 0 overlaps heap 4); exercise FAIL (blocks found in heap 0, no reuse, heap 0 count underflows) |
| Presentation seed only | village w2-vilrxp, hill w2-hillrxp, fight f4p | gameplay same (village 641 lines, hill 2187, fight 5411, hits 5 spawns 4); presentation fields differ |
| Game seed only (SEED) | village w2-vilsd, hill w4-hillsd, fight f4s | gameplay differs (village p from 485, hill p from 369; fight: hand-back) |
| Control RUMBLERND | village w2-vilrxr, hill w2-hillrxr, fight f4rxr | gameplay differs (village p from 485, hill p from 277) |
| Rumble vs none | village w2-vilrx, hill w2-hillrx | gameplay same |
| Wiring changes no gameplay | w1/w2 vs eng-e1d m2 (pre-wiring): village LT 641, hill trace 2187, fight 5411 lines | identical |

Reader: `s/outcome.py` (gameplay fields: LT p, a, m, st, mi, k, r, d, ps, pf, c; hill trace v2 T/A/R; fight LT, LL,
LE, GE and the E2 EVENTS totals; LT's pm and FXCALL lines are presentation). It fails on an empty or truncated run.

## Item 5

- `e1_log` buffers while `e1_state[0] == 4` (the tick loop) into 16 KB, printed by `e1_report` (`E1 LOGBUF`): village
  1,543 B, hill 1,598 B, fight 10,822 B, 0 dropped. The PAL and LIGHT checks log through it. DNOWORLD / DNOMARK are
  read at open, no longer in the first picture.
- Rows: Drawing = the renderer's stamps 5 -> 7 in Flycast as in the model (main.cpp no longer overwrites it with the
  whole call); palette, light records and route calls are in the services row in both; camera and HUD writes are in
  the tick.
- Still open: the effect service's `FX_LOG` writes to stderr (fight image, trace lines), and the presented-field
  counter from the hardware (console tooling, lane eng-loop2's area).

## Item 6 (by outcome, existing readers)

| Comparison | Result |
|---|---|
| Final image vs old game (eng-e1 ref-route-4, offset 184; eng-e1d's reader) | mf, ms 641/641; angle 641/641 (worst 0.241 degree); position 523/641, worst 5.12 from tick 523 (`ev/vilold-w4.json`): unchanged from E1d |
| Engine, game seed 0x5A5A vs seed 0 (only the behaviour generator's start differs) | yaw from tick 424 (worst 2.52 degrees), position from 519 (worst 47.2) (`ev/vilseed-w2.json`) |
| Engine, presentation seed only | every field 641/641 (`ev/vilpseed-w2.json`) |
| re4ref plain, e1-route with seed 0 (Leon alone, as the engine) vs engine (`tools/plays_right`) | generator, motion frame and state, discrete hash 641/641; yaw from tick 424 (2.52 degrees), position from 519 (`ev/vilref-w4-vilst.txt`) |

Reading: the old-game position failure is smaller than what the generator's stream alone does to this route in the
engine, and the decisions agree on every tick; the feed closes it (E1d). It is not closed here. The re4ref result is a
new open finding: with the same generator states and the same actor set, the yaw differs in the aiming phase where the
engine agrees with the old game; candidates are the fixture's aim input against the engine route and the stubbed
`GetWepTargetPos`. Not done: a native `GetWepTargetPos` (needs em_sub's line-against-hit-box tests, a native unit
eng-svc4 did not cover).

## Item 7: look (Flycast stills; owner look calls)

| Finding (audit section 7) | Class |
|---|---|
| Ashley's pose at pictures 200 and 320 | behaviour state at the resume (E1d: 49/728 motion frames differ under RESUMEA), not drawing; the wired image's hill pictures are identical to the pre-wiring image's |
| HUD gauges dimmer / missing portrait, ammo digits | renderer HUD widget compositing: fault, not fixed (renderer HUD work) |
| Handgun not drawn | content gap (handgun model not in the pack) |
| Hill barrels missing, ground light pool | bake content (props and the light pool not in the hill pack) |
| Ashley's hair / lash alpha | bake gap (mask runs not baked) |
| Leon's chapter-2 material | owner look call |

## Shared files touched

`render/native_actor.inc` (build_ws reads `ws_rows` / `ws_stride`, defaults unchanged), `render/source_light.inc`
(`source_lights_w`, `model_light_ri`; the ActorPose forms kept), `services/skeleton/skel.cpp` (`SKEL_PAL_DRAW`, image
only), `services/volumes/volumes.cpp` (`YarareInitCube`), `hostref/svc/svc4_units.sh`. No `src/`, `include/`, loader,
consoleloop or disc script edits.
