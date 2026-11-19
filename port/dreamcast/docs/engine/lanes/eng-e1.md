# eng-e1 hand-back (milestone E1 first slice: Leon on the engine), 2026-11-19

Lane `eng-e1` on `lane/eng-e1` from `origin/engine` 4108bf18b. Tiers: **Flycast** = guest timer in the standard harness
Flycast (std slots); no MODELLED and no console number exists. Evidence: `E:\RE4DC-Lanes\eng-e1` (runs, build, s).

## 1. What boots

The E1 image (`port/dreamcast/engine/game`, `make OUT=<dir>` -> `e1.elf`) boots straight into the village square
(r101, by the cross), constructs Leon on the engine's actor table with his original player code, and runs a 640-tick
pad route (walk, walk turning, turn in place, run, run turning, stop, aim, aim turning left and right, lower, walk,
back step) at one logic tick a picture, drawn by the E0 renderer: the village bake, Leon from the actor table, the
HUD. Stills: `runs/e1a-stills-1/pic-*.png` (Flycast).

| Part | Where | What it is |
|---|---|---|
| Hosted behaviour | `game/hosted.mk` HOSTED_SRCS | the 19 player and camera seeds, `rnd.cpp`, and the handgun module the player loads at run time (`wep02.cpp`, `objRuger.cpp`, `objWep.cpp`: the closure missed them, a pointer set by the module prolog). Built from `src/` unchanged, every `RE4DC_` knob off. One endian adapter: `STAT_BE` swaps the routine-word constants as the reference build does (`s/knobdiff.sh`: the only code difference from the reference build's objects besides hooks) |
| Engine core | `core/` | main loop (gameMainLoop's hosted subset in its order, the slow-motion rule), pacer (30 Hz), pad script through the hosted `PadRead`, room-pack loader (pl00 / wep02 DRS bodies, the r101 archive compacted to CAM SAT EAT CNS, the core camera data), per-tick trace with the reference trace's digests (buffered in RAM), RAM map |
| Host adapters | `host/` | behaviour arena with the 13-heap API on the SDK allocator (fixed address), explicit logged stubs, SDK math forwarders, link-time service accounting, prelude |
| Services | `services/` + `game/hosted.mk` SVC_ORIG_SRCS | actor and object tables (`cManager` record forms, Leon and the handgun constructed in place), collision tables, GX projection capture, the E1 actor pass |
| Renderer | `services/render_e1.c`, `services/actor_e1.inc`, `core/draw_e1.c` | `render/render.c` unchanged plus a pass that reads bone matrices in place (cModel::mat and the cParts chain); no shared render file edited |

**Skeleton and collision are a first form.** The motion, parts, IK, shape, cloth, pendulum and collision evaluation are
the original units compiled under the engine's service boundary (`SVC_ORIG_SRCS`, `--gc-sections`): the engine owns
the calls, the records (read in place by the renderer), the memory and the data, but the arithmetic is the original's.
They are the reference a re-laid-out native service must match; the native rewrite is not done (section 8).

## 2. Route result and plays right

Reference: the old game's logic trace on the same pad script (`s/refbuild.sh`: the release recipe as eng-bench's
capture build + `LOGIC_TRACE=1` + `DBG_WARP=1`; fixture `s/fixtures/r101-route.txt`: r101 by the cross, after the
bell (`rsf 0x101 7 10`), `god`, source clock, the nine live Ganados held away by `emaway`). Engine tick k = reference
tick 184 + k. Tool `s/plays_right.py` (position 1 unit, angle 1 degree, Mot_frame and Mot_state exact; reports the
reference's digests pf (model coordinate block), pm (every cParts block), c (camera)).

| Check (641 ticks, Flycast) | Result |
|---|---|
| Mot_frame, Mot_state | exact on 641 / 641 |
| Angle | within 1 degree on 641 / 641 (worst 0.064) |
| Position | within 1 unit on 616 / 641; ticks 0 to 538 all within (bit-identical through 484); 25 ticks 539 to 640 up to 1.353 |
| pf digest (pos, angle, matrices, speed, frame) | bit-identical ticks 0 to 484 |
| pm digest (parts), c (camera) | differ from tick 0 / 222 |
| Control: motion speed 0.97 (`CTRLSPD`) | FAIL (frame at tick 0, position at 49, state at 75, angle at 204) |
| Determinism: three engine runs | identical traces |

**First divergence, understood: the shared generator (SHELL_MAP risk 1).** At tick 485 (the aim is lowered) the angle
moves by 0.064 degrees from the reference. Leon's own code draws the shared generator 6 to 14 times a tick (pendulum
cloth wind, eye wander, camera sway, the aim sway `PlWepLockRand` fRand1_1); in the reference the whole village draws it
about 205 times a tick (`s/rng.py`), so the values Leon's draws get differ. Test: an engine arm that changes only the
generator's start (`SEED`) against the default engine reproduces the pattern (pf diverges at 485, pm from tick 0, the
camera digest), with discrete fields exact. Hosting the effects and AI that draw in between (E2) or a reference that
records the generator at the player's call is what closes it. Generator state per tick is therefore not comparable
to the old game in E1; the engine's own draws are logged per tick.

## 3. Budget rows (Flycast, 600 pictures 41 to 640, NOTRACE run `runs/e1a-17t`)

| Row | Mean | p99 | Worst (picture) | Over row budget | Budget |
|---|---:|---:|---:|---:|---:|
| Behaviour (hosted, outside service entry points) | 0.21 | 3.51 | 6.12 (64) | 6 over 2 | 2 |
| Services (skeleton, collision entry points) | 4.64 | 6.68 | 8.24 (485) | 0 over 9 | 9 |
| Publication | 0.00 | 0.00 | 0.00 | 0 | 0 |
| Drawing (PVR ready to scene finish) | 10.18 | 12.25 | 14.71 (182) | 1 over 14 | 14 |
| System (input, logging, loop) | 0.12 | 4.97 | 5.15 (557) | 11 over 3.5 (the pictures that log an act line) | 3.5 |
| Busy picture | 15.15 | 19.78 | 22.80 (49) | 0 over 33.3 | 33.3 |

Services by entry point (ms a tick, Flycast, `E1 SVC` lines): motion step 2.02, Leon's cloth 1.45, parts world 0.67,
scenery hit check 0.17 (5,216 calls, the camera), scenery check 0.14. Publication is 0 by construction: the renderer
reads the actor table in place; the camera record (104 B) and two light matrices (96 B) are copied inside drawing.

## 4. Main RAM map (Flycast, after the room load; nothing is allocated while ticks run)

| Block | Range | Bytes |
|---|---|---:|
| Program image (incl. the 192 KB trace buffer) | 0x8c010000-0x8c1c1be8 | 1,776,616 |
| Engine room pack (KOS heap: renderer pack and runtime, player archive 837,536, weapon archive 251,648, room sections 337,024) | 0x8c1c1bf0-0x8c9e0717 | 8,514,024 used |
| Free (heap top to the arena) | 0x8c9e1000-0x8cc00000 | 2,224,128 |
| Behaviour arena (fixed; heap 4 over it) | 0x8cc00000-0x8cfc0000 | 3,932,160 |
| - high-water mark (heap 4, 16 allocations, 0 failures) | | **170,336** |
| Kernel stack (high water 9,240) | 0x8cff0000-0x8d000000 | 65,536 |

Overlaps: 0. VRAM: the E0 renderer's map (eng-e0b section 5), unchanged.

## 5. Stubs hit (641 ticks)

`cDmgMgr::hitCheck` 641 (no damage objects), `ChkWindow` 533 (no windows hosted), `GetWepTargetPos` 93 (laser target
while aiming: the laser is not drawn), `SndCall` 56 (footsteps; no sound in E1). No other stub was called.

## 6. Ashley (integrator scope addition), measured, not built

`s/closure_ashley.py` (eng-shell-map's closure with `pl_npc.cpp` and `pl_ashley.cpp` added to the seeds; lab33 call
graph): variant B grows from 22 to 24 files, code 103,856 -> 111,984 B. New interfaces: `RouteCkToPos` (route checks),
`cLight::setParent`, `cLightMgr::createBack` (her light), `cModel::matUpdate`; seven stubs become hosted
(`SubCharGetStatus/Condition`, `cSubChar::control/endDamage/init/registPlAction/setHand`). Room: r118 (after the church,
end of chapter 2, Disc 1, `st1`) is the candidate; not verified. Generic hosting for a controlled Ashley: room set-up by
`pG->pl_type` (the actor-table constructor already switches on it), `ReadPlayerData` for her archive (0x22), her weapon
set (none), the camera and HUD inputs per character, her collision volumes; the castle section itself is Disc 2.

## 7. Staged disc

`E:\RE4DC-Lanes\eng-e1\build\E1-GDEMU-e1a` (KEEP, SHA256SUMS, SHA256SUMS.boot, disc_lint PASS). One boot: the route,
then the report on serial (`LT` trace lines, `ROW` timing lines, `E1 SVC`, `E1 MEM`, stub counts).

## 8. Not done

- Native skeleton and collision services: the first form runs the original evaluation under the engine boundary.
- MODELLED rows (the hwtrace slot exists; no model run). Console: none.
- Generator-exact plays right against the old game (section 2).
- Drawn in E1: no handgun model (not in the pack), no laser, no effects, no foot shadows; lights and HUD layout from the
  pack's first recorded picture; sound none.
- Thread primitives for `TaskScheduler`: the hosted set never sleeps a task (`TaskSleep` is a logged stub, never hit);
  the loop calls the game task's steps directly.
- Ashley hosted (section 6).
