# eng-e1b hand-back (E1 second slice: Ashley on the engine, and the full-field fixtures), 2026-11-19

Lane `eng-e1b` on `lane/eng-e1b` from `origin/engine` aa960fc8c. Tiers: **Flycast** = the old game or the engine in
the standard harness Flycast (std slots); **PC** = re4ref; **MODELLED** = nominal 200 MHz SH-4 hwsim over a Flycast
hwtrace (fly slot); no console number. Evidence: `E:\RE4DC-Lanes\eng-e1b` (`runs`, `ev`, `build`, `s`).

## 1. The two full-field fixtures (old game, Flycast)

Reference build: eng-e1's (release recipe + `LOGIC_TRACE=1` + `DBG_WARP=1`) plus `LOGIC_TRACE_EM_FROM=185`,
`LOGIC_TRACE_EM_TO=1100` (one image covers both windows; elf sha256 33ef1bdc8...; `s/refbuild.sh`, `refdisc.sh`,
`refbase\`). The LE / LF lines give every alive enemy-list work every tick: id, type, be_flag, routine word, motion
state and frame, life, position, yaw. No log overruns.

| Fixture | Warp (`tools/plays_right/fixtures/`) | Run | What it records |
|---|---|---|---|
| Ashley at the r11d hill path | `fx-hill-warp.txt`: logicbudget bk-r11d without its `kill` / `killrep` (and census) lines, `act_clock source`, Leon walks t=400-459 and t=520-579 | `runs\fx-hill-1` (LT 0..1110, LE 185..1100) | the opening event t=185-370; then Ashley follows Leon twice; the hill's four Ganados stay 26 m away |
| Ganado at the bell gate | `fx-bell-warp.txt`: cachefoot st-bell-l's warp (r101-bell-trg) | `runs\fx-bell-1` (LT 0..420, LE 185..480) | four Ganados (id 0x15) from t=185; the room event freezes them at t=318 |

The recordings (5.0 and 1.9 MB of old-game log) stay in `E:\RE4DC-Lanes\eng-e1b\fixtures` with their sha256; the
warps, and the re4ref fixtures built on them (`hill-follow.txt`, `hill-follow-g.txt`), are in git.
`plays_right.py` now reads LE / LF lines as a full-field old trace (`--actor`: id and rank; fields p, a (yaw), mf,
ms, r, hp, be, aps; the old trace has no motion slot, flags word or per-actor generator calls). Its controls table is
unchanged (`ev\controls\controls.md`: every line as it must).

## 2. re4ref against the fixtures, every field (PC against Flycast)

Tolerances as agreed (`tolerances.json`): position 1 unit, angles 1 degree, the rest exact. `n/N` = ticks within.
Table: `ev\table.txt`, JSON per line in `ev\table\`.

| Actor, fixture | p | a | mf | ms | r | hp | be | aps | First divergence and cause |
|---|---|---|---|---|---|---|---|---|---|
| Ganado 0x14 (walks), bell, t=185-317 | 133/133 (0.002) | 133/133 | 133/133 | 133/133 | 133/133 | 133/133 | 133/133 | 133/133 | none in the window; t=318 the room event freezes the old Ganados (not hosted) |
| Ganado 0x1e, same | 133/133 (0) | all | all | all | all | all | all | all | none |
| Ganado 0x1c, same | 133/133 (0.37) | all | 0/133 | all | all | all | 122/133 | 122/133 | t=185: its idle frame is 13 ahead in the old run (its start frame came from the shared generator, drawn after other actors); be bit at t=196 |
| Ganado 0x1f (roof), same | 60/133 | all | 1/133 | 132/133 | all | all | all | 132/133 | t=186, 15 units: the old run's roof Ganado is pushed (not hosted) |
| Leon, bell, same window | 133/133 (0.027) | all | all | all | (ps) all | | | | none |
| Leon, hill, t=373-1100 (`hill-follow`, generator fed) | 53/728 | 728/728 | 728/728 | 728/728 | (ps) 728/728 | | | | t=426, 1.26 units: Ashley (below) turns differently and pushes him |
| Ashley, hill, same | 53/728 (to t=425) | 607/728 | 517/728 | 725/728 | 603/728 | 728/728 | 728/728 | 601/728 | t=373 frame 58 apart (resume: her idle restarts at 0); t=426 position: her idle timer, drawn from the generator before the resume point, runs out at t=421 in the old run (a look-around), not in the reference |

The hill window starts at a resume (t=372, after the opening event, which neither re4ref nor the engine hosts).
The idle timer is not in any trace; the RESUMEA arm in section 4 shows it is the cause.

## 3. Ashley on the engine (hill scene, r11d)

Room: **r11d**, the hill path with Ashley (chapter 2, Disc 1), the room the fixture uses. One image, two scenes: the
village route (Leon alone, the default, unchanged) and the hill scene (boot option `HILL`).

| Part | Where | What |
|---|---|---|
| Hosted partner code | `game/hosted.mk` PARTNER_SRCS | `pl_npc.cpp` (cSubChar: follow, wait, hide, carried, damage; 34,484 B linked) and `pl11.cpp` (cSubAshley, the module of enemy id 3; 1,060 B; its REL entry linked as `pl11_prolog`), from `src/` unchanged, every knob off. `route_ck.cpp` (5,796 B) joins the services (first form). Image text +52,532 B over E1 |
| Her archive | `core/partner.cpp` `e1_em_read_search` | `em/pl11.drs` main-RAM parts (411,744 B) in the room pack; the 61 clips its MTC table keeps apart (`dc/mot/*.fcv`, 430,112 B) loaded at room entry, checked (size, header) and linked in place of their proxies: the original motion code reads the keys in place, no lease or lookup per tick, no disc read in play |
| Creation and commands | `core/partner.cpp` | the original `SubCharInit(1, pos, yaw)` (EmMgr.createBack(3) -> engine construct -> the module's init) and `SubCharCtrl(1, 1)` (follow), as the room script does |
| Characters' tick | `services/managers.cpp` | em.cpp's `cEmMgr::move` / `emMove` (knobs off) on the engine table, before the player's move (gameMainLoop order); the construct tail is the original's (serial, list entry, be_flag 0x40 / 0x02000000, subArc2), now for Leon too |
| Drawing | `core/draw_e1.c` | **placeholder**: no engine pack holds Ashley's mesh, so the renderer marks each of her bones with a flat square read in place from the actor table (her parts chain, the world matrices the skeleton service wrote); nothing converted per tick. r11d has no world bake: the hill scene draws Leon (pack), Ashley's marks, the HUD and the village sky and fog |
| Route | `core/route.cpp` | re4ref's pads (`hill-follow.txt`): stick forward ticks 28-87 and 148-207 |
| Trace | `core/partner.cpp` | re4ref trace v2 lines (T, A, R) with the generator draws counted per caller (from the generator's state, so draws inside rnd.cpp count) |

The new interfaces, each one now engine code or a stub:

| Interface | Now | Calls (729 ticks) |
|---|---|---|
| `RouteCkToPos` | engine service, first form: `route_ck.cpp` under the service boundary, on the room's RTP section (now kept in the room pack; `pG->Rtp`) | every follow step |
| `cModel::matUpdate` | skeleton service (`model.cpp`, already in the first form), counted in the services row | 733 |
| `cLightMgr::createBack(int, int, int, int)` | engine stub: one engine light record, logged | 1 |
| `cLight::setParent(cModel*)` | engine stub: keeps the parent, logged; E1 draws with the room's baked light set | 1 |
| also reached: `DoorOpenCk`, `SubOpenDoorSet`, `SceAtCheckLadder`, `SubLadderClimbCk`, `SubLadderClimbCk2` | logged stubs answering "none" (no door or ladder is hosted; none near her in r11d) | 729 each but `SubOpenDoorSet` 0 |

## 4. Plays right: the engine's per-actor trace (Flycast) against re4ref (PC) and the old game (Flycast)

Engine runs: the E1 image, hill scene, the standard Flycast; the trace is re4ref's format, so `plays_right.py
--actor id=03` and the T line compare directly. FEED = the old run's generator state at the start of every tick
(as re4ref `--rng-feed`). Every engine-vs-re4ref line uses the same fixture (`hill-follow.txt`), FEED on both sides
unless stated.

| Comparison | Ashley: p a mid mf ms r hp be f aps | Leon: p a mid mf ms r ps | First divergence and cause |
|---|---|---|---|
| engine vs re4ref, FEED | **729/729 on every field, bit-identical** | **729/729, bit-identical** | none. Not compared equal: `rc` and `rng`: the engine hosts the pendulum cloth wind draws (Leon 6, Ashley 9 a tick) that re4ref stubs (`PenClothMove`, `PenClothMove3`) |
| engine vs re4ref, no feed | 361/729 (routine) | 729/729 | tick 361 (old t=733), Ashley's routine: her idle timer is a generator draw, and the engine's generator differs from re4ref's by those cloth draws. Leon draws nothing his own fields depend on in this route |
| engine vs old fixture, FEED | as re4ref vs old (section 2): position to tick 53 (t=425), hp and be all 728 | position bit-identical ticks 1-50, within to tick 53; a, mf, ms, ps 728/728 | t=426: Ashley's idle timer (below) |
| engine vs old, FEED + RESUMEA | **p 728/728 (0.0117 units), a 728/728 (0.0001 deg), r 728/728, hp, be 728/728**; mf 679/728 (her idle frame for the first 49 ticks), ms 727/728 | **728/728 on every field, bit-identical** | none in position or routine over the 728 ticks (t=373-1100, both follows) |
| determinism: the RESUMEA run twice; the drawn b2 image against the headless b0 image | identical traces | identical | - |

**Cause of the first divergence against the old game, tested:** RESUMEA (a diagnostic boot option of the engine)
gives Ashley, at the resume, the idle state that the old run's trace does not record but its next ticks reveal: the
idle timer (its look-around at t=421 means 48 ticks were left at t=372), her idle frame and `r_no_3` 0. With it, Leon
is bit-identical to the old game for all 728 ticks and Ashley stays within 0.0117 units with her routine exact on
every tick. So the divergence is the resume (state the fixture cannot carry), not the hosting.

**Control (must fail):** CTRLFOL, Ashley 10% further from Leon while she follows (as re4ref `--control
follow-dist=1.1`): FAIL against the engine's own run at tick 78 (t=450, 95.4 units: her first follow), FAIL against
the old fixture at tick 78; re4ref's own control fails at tick 79.

## 5. Budget rows, hill scene (Leon and Ashley), 600 pictures (41 to 640)

Image b2 (commit below), boot options `HILL NOTRACE` (no generator feed, no diagnostic arm: the scene as the engine
runs it). Behaviour = the tick outside the service entry points; services = time inside the skeleton, cloth and
collision entry points (link-time wraps; now also Ashley's `PlClothMoveGirl` and the pendulum cloth); publication = 0
by construction; drawing = graphics chip ready to scene finish; system = input and the trace (pacer wait excluded).

| Row (budget) | Flycast mean | p99 | worst (picture) | over row | MODELLED mean | worst | over row |
|---|---:|---:|---:|---:|---:|---:|---:|
| Behaviour (2) | 0.22 | 0.25 | 6.18 (45) | 1 / 600 | 0.19 | 0.21 | 0 / 60 |
| Services (9) | 11.86 | 14.52 | 15.46 (102) | **600 / 600** | 17.5 | 19.3 | **60 / 60** |
| Publication (0) | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Drawing (14) | 7.34 | 8.63 | 9.12 (581) | 0 / 600 | 9.62 | 11.17 (80) | 0 / 60 |
| System (3.5) | 0.03 | 0.03 | 2.08 (161) | 0 / 600 | 0.04 | 0.05 | 0 / 60 |
| **Busy picture (33.3)** | **19.46** | 23.35 | 26.74 (45) | 0 / 600 | **27.39** | 30.69 (100) | 0 / 60 |

- MODELLED = nominal 200 MHz SH-4 hwsim over a Flycast hwtrace (fly1, interpreter): every 10th picture of the same
  600 traced (60 pictures); the instruction count over all 600 (7.84 M a picture) is within 1.2% of the traced 60
  (7.75 M). Phases come from store stamps (`m1_timing`, core/e1_core.h `e1_stamp`, the bench's observer); the
  behaviour / services split of the tick phases comes from the function table by object file (services 16.30 ms,
  behaviour 0.18 ms, unattributed leaf math 1.25 ms split pro rata). `ev\model-hill-rows.json`, `-phases.csv`.
- Per character (Flycast mean a tick, services included): Ashley 7.54, Leon 4.16, objects 0.09, camera 0.29.
  MODELLED: Ashley 10.84, Leon 6.28, objects and camera 0.60.
- Services by entry point (Flycast, ms a tick): motion step 4.81 (two characters), Ashley's cloth
  (`PlClothMoveGirl`) 3.55, Leon's cloth 1.43, parts world 1.26, scenery hit check 0.38 (camera and partner),
  scenery check 0.24. **The services row is over its 9 ms on every picture in both tiers; Ashley's cloth and the
  motion step are the first form's original arithmetic** (the native skeleton and cloth are lane eng-svc's).
- The busy picture fits 33.3 ms on every picture in both tiers, but the MODELLED 27.4 mean is not under half the
  budget: per the plan it does not count until a console run.
- Drawing has no world in this scene (no r11d bake): it is Leon, Ashley's marks, the sky and the HUD.

**Behaviour arena high-water mark: 300,736 B** (heap 4, 17 allocations, 0 failures, 0 frees) of 3,932,160; Leon
alone (village route) is 170,336. Ashley adds 130,400 B.

## 6. Main RAM map, hill scene (Flycast, after the room load; nothing allocated while ticks run)

| Block | Range | Bytes |
|---|---|---:|
| Program image (incl. the 192 KB trace buffer, the 19 KB model stamps) | 0x8c010000-0x8c1e9aa8 | 1,940,136 |
| Renderer pack and runtime (opened first in this scene) | 0x8c1e9ab0-0x8c9b2900 | 8,160,022 |
| Room data: r11d sections 199,520 (of a 1,219,488 B archive, read section by section), player 837,536, weapon 251,648, Ashley's archive 411,744, her 61 motion-key clips 430,112, managers 25,472 | 0x8c9b2900-0x8cbc08c0 | 2,133,504 |
| Free (heap top to the arena) | 0x8cbc1000-0x8cc00000 | 258,048 |
| Behaviour arena (fixed; heap 4) | 0x8cc00000-0x8cfc0000 | 3,932,160 (high water 300,736) |
| Kernel stack (high water 8,800) | 0x8cff0000-0x8d000000 | 65,536 |

Overlaps 0. Main RAM is tight in this scene: the village pack (8.2 MB, world included) is loaded only for Leon's mesh
and the HUD. A character-only pack would free most of it.

## 7. What a controlled Ashley needs (her castle section, Disc 2; not built)

Not built. What the engine has to provide, from the code the player paths take when `pG->pl_type == 1`:

| Need | Where in the original | Engine today |
|---|---|---|
| Her player class | `cEmMgr::construct` id 0, `pl_type` 1 -> `new cPlAshley` (`pl_ashley.cpp`, 318 lines: model set, room-dependent motion table `pl01weaponSet`, hands, bust bounce); cloth through `PlClothMoveGirl` | construct switches on `pl_type` but builds Leon only; `pl_ashley.cpp` not in the hosted set. Her cloth service is hosted (the partner uses it) |
| Her player archive | `ReadPlayerData(1, costume)`: file 0x22 `em/pl01` (costume 1: 0xBE), no weapon module (`dll` 0) | the engine loader serves type 0 only (`em/pl00`). `em/pl01.drs` (1.53 MB) keeps its motion keys in the archive (no MTC table), so it loads like Leon's |
| Character switch | `PlSelect(1)` (life maxima, pesetas and weapon data swapped, `pl_flag` bit 0), `PlSetCostume`, `PlayerInit` / `PlayerLifeReset` (life 600) | hosted (`pl_sub.cpp`, `player.cpp`); needs the room set-up to call them in gameRoomInit's order |
| No weapon | `pl_wep` paths skip for type 1; `ReadWepData` not called | `ReadWepData` answers only the handgun; nothing to add |
| Camera and HUD per character | `cam_ctrl.cpp` attribute switch on `pl_type`; `player.cpp` damage frames per type; HUD life gauge without ammo | camera code hosted; the HUD is the pack's recorded widget layout (Leon's): her gauge is a renderer task |
| Her actions in the castle | crouch and hide, ladders, doors, levers and cranks, push blocks (`ActBtn`, `SceAt*`, door and ladder checks), being carried by the armour knights | all stubs ("none"); scenario, doors, ladders and enemies are E3 / E4 work |
| Her collision volumes | set by `cPlAshley` / `cPlayer::init` from her archive | collision service hosted; volumes come with the class |
| Her mesh | the same body data the partner draws | no engine pack holds Ashley yet (placeholder marks only); a bake of her body and levels is needed for both roles |
| Rooms | the castle section (Disc 2: r2xx) | no engine room pack beyond the village; Disc 2 data and the disc layout are E4 |

## 8. Staged disc

`E:\RE4DC-Lanes\eng-e1b\build\E1B-GDEMU-hill` (KEEP, SHA256SUMS, SHA256SUMS.boot, disc_lint standard PASS). Boot
options on the disc: `HILL FEED RESUMEA` (the plays-right run: the old run's generator states and Ashley's resume
state, so the console trace compares with the old fixture and re4ref). Booted in Flycast (`runs\staged-hill-1`): the
trace is byte-identical to the headless engine's. One boot: 728 ticks, then the report on serial (T / A / R trace
lines, ROW timing, E1 SVC, E1 MEM, E1 ARENA, stub counts). The trace buffer (192 KB) fills three times in this scene:
those three pictures print mid-run (system row; Flycast worst 16.5 s). The timing rows above come from the NOTRACE
image (`build\e1-b2-hilltime.iso`).

| File | sha256 |
|---|---|
| disc.gdi | 025516557d49e1835e7eb8571e09244b64db190cf3981ead555c54b1924ca19f |
| track01.bin | 65be0804ac1f9522453c4a467640748d11e590699696cdfafc381375e62cab9f |
| track02.raw | 15453e38e9c8e03d6e7854c2414f93e944b6059b4933847ebf735834407cec48 |
| track03.bin | aca895ed3c3d3e4a4e53ab72f3006814d506ee0599bb29e7846157a47da8cb94 |
| 1ST_READ.BIN | e9f4b1c758c55afc6e947fbc7503cb201a0b5b032bd09a458358ec3b270750a1 |

## 9. Changes outside the partner, found on the way

- The E1 image did not link on `engine` since eng-look's merge (`m1_content`, `m1_content_counts`): defined in
  `core/draw_e1.c` at step 0 with the glow on (the bench's defaults).
- With eng-look's renderer the E1 image refuses the E0 pack (content-variant table): the discs now carry eng-look's
  `lkg` pack (`s/mkiso.sh`, `s/stage.sh`). The village route with it draws as before (`runs\b1-vilst-1`).
- The original construct tail (serial, list entry, be_flag 0x40 | 0x02000000, subArc2) now runs for Leon too. The
  village route's plays-right result is unchanged (eng-e1's check against `ref-route-4`: the same 25 position ticks
  over, worst 1.353, pf equal to tick 485).
- An empty punch-through list (no world) made the graphics chip time out (100 ms) every picture and left it black:
  one off-screen triangle keeps the list non-empty.

## 10. Not done

- Ashley's mesh: no engine pack holds her body; she is drawn as bone marks (placeholder). A bake of her body (and
  levels) is needed, for the partner and for a controlled Ashley.
- r11d's world: no engine bake; the hill scene shows the village sky and fog only.
- Native skeleton, cloth and collision services (the first form runs the original arithmetic; services row over
  budget, section 5). Ashley's cloth is the largest single entry.
- The opening event of r11d (t=185-370), the Ganados of the hill (`hill-follow-g` runs them in re4ref only), Ashley
  carried, hidden or hurt: not hosted on the engine; no fixture for carried or hidden yet.
- The generator against the old game: the engine is compared with the old run's generator fed per tick (FEED); without
  it the engine's own draws (pendulum cloth wind, which re4ref stubs) change Ashley's idle timer from tick 361.
- The old-game fixture starts at a resume: Ashley's hidden idle state needs the RESUMEA arm to match the old run
  (section 4); re4ref has no fixture key for it.
- MODELLED over 60 sampled pictures of the 600, not all 600. No console run.
- Controlled Ashley (section 7): listed, not built.
