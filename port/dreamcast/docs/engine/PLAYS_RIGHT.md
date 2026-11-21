# Plays right: the reference build of Leon and the comparison tool (lane eng-host, 2026-11-19)

The "Plays right" gate (ENGINE_PLAN.md section 8) compares the engine with the original code on the same
inputs. This is the original side: Leon's own player and camera code, built for the PC, replaying a pad
recording and writing one trace line per tick, and the tool that compares two traces.

- **Reference:** `port/dreamcast/engine/hostref/` builds `re4ref`.
- **Comparison:** `port/dreamcast/tools/plays_right/plays_right.py`, tolerances in `tolerances.json`,
  controls in `controls.sh`, fixtures in `fixtures/`.
- **Result:** on the old game's door103 fixture (village square, the walk to the farm door) the reference
  agrees with the old game's own logic trace for 323 ticks, 272 of them bit for bit (section 7).

## 1. Build

```
cd port/dreamcast/engine/hostref
make -j4          # build/hostref/plain/re4ref: the reference
make -j4 fma      # build/hostref/fma/re4ref: the same with fused multiply-add (a measurement, section 5)
```

- **Target:** i386 code (`-m32`), run on x86-64 Linux. The game's structures, its data files and its
  `u32` pointer casts are 32-bit; `-malign-double` keeps 64-bit members 8-aligned as on the SH-4.
- **Floats:** SSE single precision, flush-to-zero and denormals-are-zero (the SH-4 runs with FPSCR.DN set),
  no fused multiply-add in the reference.
- **Knobs:** no `RE4DC_` knob is defined. `RE4DC_GAME` only selects the non-PowerPC source paths.
- **Needs:** gcc/g++ with the 32-bit C library (`gcc -m32` links). No 32-bit libstdc++: `host_rt.cpp`
  carries the few C++ runtime pieces.
- **Sources are not edited.** `prep.py` writes host copies in three cases: empty `asm("" : "+f"(x))`
  scheduling barriers get the SSE register class (no code either way); `rnd.cpp` gets a call counter and a
  state reader; `em.cpp`, `obj.cpp` and `read.cpp` are cut to the functions the player uses (verbatim).

## 2. What the reference is made of

| Part | Files | Where it comes from |
|---|---|---|
| The E1 closure (SHELL_MAP.md section 5, variant B) | 19 player and camera files and `rnd.cpp` | original, compiled as they are |
| Skeleton and pose, collision, math, pad, room counts | `model motion cMotBase ik math_sub sub2 atari at_mod at_sub at_sub2 atariInfo shape pl_cloth cons pad foot_shadow_tbl` | original |
| The held weapon (Punisher, the default handgun) | `wep02.cpp`, `objRuger.cpp`, `objMauser.cpp`, `objWep.cpp` | original: the weapon module fills Leon's footwork motions, so he cannot stand or walk without it |
| Character and object managers | `em.cpp`, `obj.cpp` (cut) | original pieces; `construct` builds Leon and the weapon object only (`host_em.cpp`) |
| Matrix, vector and libm | `src/lib` mtx, vec, quat, fdlibm | original SDK C code and the game's own fdlibm |
| Memory | `host_mem.cpp`, `host_memapi.cpp` | a 16 MiB arena at the Dreamcast's address, 0x8C000000; one deterministic heap |
| Work pools | `host_mgr.cpp` | the GameCube's dense layout (the Dreamcast port's demand pages are a port feature) |
| Data | `host_data.cpp`, `host_glue.cpp` | the converted Dreamcast data tree: `etc/core.das`, `em/pl00.drs`, `em/wep02.drs`, `stN/rNNN.arc` |
| Everything else E1 does not host | `host_stubs.cpp` | logging stubs: HUD, sound, effects, lights, drawing, debug, rumble, and other behaviour (enemies, items, scenario, partner, windows, racks) |

Every one of the 281 rows of the E1 interface (`closure-iface-B.tsv`: 175 engine entry points, 72
behaviour stubs, the old port's hooks and unnamed symbols) is accounted for in `hostref/closure-map.tsv`:
107 original code, 11 original SDK or libm, 33 host adapters, 60 logging stubs, 1 no-op, 69 not linked (no
caller in the hosted code). Skeleton and pose: 36 of 36 original. Collision: 18 of 21 original, 3 not linked.

One i386 trap, found and fixed: `include/atari_init.h` declares `cAtariInfo::init` with its seven float
arguments first. On the PowerPC and the SH-4 integer and float arguments travel in separate registers,
so the order does not matter; on the i386 everything is on the stack. `host_em.cpp` gives that name a
body that passes the arguments on in `init`'s order. Without it Leon's collision sphere was 800 units wide.

## 3. Replay

```
re4ref --tree <converted data tree> --fixture <fixture.txt> [--out trace.txt] [--log run.log]
       [--control walk-speed[=k] | drop-rng[=tick] | shift-input[=n]]
```

The data tree is private game data (the Dreamcast build's little-endian tree, for example a release tree's
`st1/`, `em/`, `etc/` folders). It is never committed; only the fixture and the trace are text of ours.

**Fixture** (text, `#` comments):

| Line | Meaning |
|---|---|
| `room 0x101` | the room archive `st1/r101.arc` |
| `pos x y z`, `ang a` | where Leon is placed (the game's `sub_pos`, `sub_angle`) |
| `weapon 2 0` | the equipped weapon (only the wep02 handguns are hosted) |
| `seed 0x0d37` | the generator seed |
| `resume x y z ay frame [event]` | continue from a recorded tick: position and yaw (floats, or `0x` bit patterns as the logic trace prints them), idle footwork restarted at `frame` with no blend; `event`: the tick follows an event's end |
| `ticks N` | ticks to run |
| `pad tick buttons sx sy [subx suby trigL trigR]` | pad 0 from that tick on: GameCube button bits (A 0x100, B 0x200, X 0x400, Y 0x800, START 0x1000, Z 0x10, R 0x20, L 0x40, D-pad 1/2/4/8) and signed sticks, forward = +sy |

**A tick** is one pass of the game's frame loop: `PadRead` (the original, fed by the fixture through
`PADRead`), `Frame_cnt++`, then the hosted part of `gameMainLoop` in its order: `UpdateNearClipDist`,
`pPL->move()` under the game's own condition, `ObjMgr.move()` (the held weapon), `CameraMove()`.
Set-up follows `gameRoomInit`: managers sized by the room's own counts, room collision (SAT and EAT),
the player created by `EmMgr.create(0, 0)` (constructor and `startUp`), then the camera.

## 4. Trace format

One line per tick (wrapped here):

```
# re4ref trace v1
H fixture=... room=0101 seed=0d37 ticks=348 fp=plain control=none
T t=284 in=0000,0,80 p=4719cbc0,4541d68a,c6d04ff7 a=00000000,3fd1a36e,00000000 m=W11,00000000,0
  r=00010100 be=03002077 ps=9270cb96 psm=aa70cb96
  cam=471505ee,4596ae5f,c6cbd564,471f5b20,458c8e25,c6d11dc4,42480000 rng=8074/0
  stub=24/8bd36d90/eprintf+cDmgMgr::hitCheck+ChkWindow+cLightInfo::updateMatrix+PenClothMove3+...
```

| Field | Content |
|---|---|
| `t` | tick (0: the state after construction or resume) |
| `in` | pad 0 this tick: buttons, stick x, stick y |
| `p`, `a` | Leon's position and angles (x, y, z) |
| `m` | motion: the archive slot it came from (`Pxx` player archive, `Wxx` weapon archive), frame, state |
| `r` | routine bytes `r_no_0..3` |
| `be` | `be_flag` |
| `ps`, `psm` | the logic trace's discrete hash (be_flag, stat, id, type, Mot_state); `psm` with the draw pass's marker 0x08000000 set |
| `cam` | camera eye x, y, z, target x, y, z, field of view |
| `rng` | generator state / calls to it this tick |
| `stub` | stub calls this tick / FNV of their names in call order / the distinct names |

Floats are IEEE-754 bit patterns (8 hex digits). The old game's logic trace (`LOGIC_TRACE=1`, `LT t=` lines)
records p, a, the motion frame and state, the discrete hash and the generator, so those fields compare
directly; it records the camera only as a hash.

## 5. Tolerances and why

| Field | Tolerance | Why |
|---|---|---|
| Position | 1 unit (1 mm) per axis | The largest difference from the old game over 323 ticks is 0.0115 units, and it is the resume's own start-up (the height alone, ticks 1 to 51). From tick 52 on, 272 ticks are bit-identical, walk and wall slide included. 1 unit is 87 times the largest difference seen and a 1.5% error in the walk's 68 units a tick fails it on the first tick |
| Angles | 1 degree | Bit-identical on every tick (yaw, pitch, roll) |
| Camera eye and target | 1 unit; field of view 0.1 degree | Same rule as the position; the old trace has the camera only as a hash, so this is for engine against reference |
| Motion id, frame, state | exact | Discrete: a frame off is a tick off |
| Routine, discrete hash | exact | Discrete game state: any difference is a behaviour change |
| Generator state | exact | Risk 1 of SHELL_MAP.md: an extra or missing draw changes every later enemy decision |

**x86 against SH-4 floats, measured (Flycast tier).** On this fixture the x86 reference and the old game's
SH-4 code, as Flycast ran it, produce identical bits on every tick once the resume's start-up has passed.
The fused variant (`make fma`, a*b+c with one rounding) matches worse: 68 bit-identical ticks, 50 float
steps at most. So the reference stays unfused. Not measured: the console's own FPU where the SH-4 code
uses `fmac` (Flycast's rounding of it is what this run saw); the logic trace's room digest (`LD` lines)
is the existing console check for that. The tolerances above are wider than anything measured; they are set by what a player
can notice, and every one is shown to fail on a control (section 6).

## 6. Controls (each must fail the check)

`RE4_TREE=<tree> controls.sh [out dir]` runs door103-walk twice and once under each control, and compares
each with the first run:

| Check | Must | Result | First divergence |
|---|---|---|---|
| determinism (a second run) | PASS | PASS, bit for bit on all 349 ticks | none |
| walk-speed=1.02 (2% more ground per walking tick) | FAIL | FAIL | tick 285, position: 39440.13 against 39441.49 (1.37 units) |
| drop-rng=1 (one generator call dropped) | FAIL | FAIL | tick 5, generator: d769 against 6ed3 |
| shift-input=1 (every pad change a tick later) | FAIL | FAIL | tick 283, routine: 00010000 against 00000101 |

Against the old game's trace the walk-speed and shift-input controls fail at the same ticks (position,
discrete hash).

## 7. Agreement with the old game

- **Fixture:** the old port's door103 gate fixture (lab32 kit `fixtures/door103.txt`): the village square
  after the bell, Leon at the door to the farm. Old trace: the Flycast logic-trace run of 2026-11-03
  (`E:\RE4DC-Lanes\cachefoot\gates\st-door103-a\run-output.txt`, sha256 976ac22d...).
- **What the old run does:** Leon is placed at t=183; the radio call starts at once and ends at t=739;
  idle (the footwork loops every 90 ticks); A at 871 and 991; the stick forward at 1111 for 25 ticks;
  A at 1151 opens the door; the room changes at 1176. Pad timing is read off the run's own log
  (`warp: act` lines between `LT` records).
- **The reference** (`fixtures/door103-walk.txt`) resumes at t=829 (a loop restart, so no blend from the
  call's pose) and replays the same pads. Reference tick n is old tick 828 + n.
- **Window: t=829 to 1151, 323 ticks, every compared field within tolerance.** Discrete hash, motion frame
  and state, angles: exact on every tick. Position: 272 ticks bit-identical; ticks 1 to 51 differ in height
  only, at most 0.0115 units. The walk (1112 to 1135, 68 units a tick) and its slide along the door frame
  (1131 on) are bit-identical.
- **First divergence: t=1152, motion frame (old 14, reference 15).** Cause: A at 1151 opens the door; the
  door and the room change are scenario code the reference does not host, so the old game stops the player
  and the reference keeps idling. Position follows at 1161.
- **Not compared against the old game:** the generator (the old run has 26 enemies and the room's effects
  drawing from it every tick; the reference has only Leon, so it differs from the first tick by design)
  and the camera (the old trace has it only as a hash).
- **From the warp start** (t=183) the placement is bit-identical in position and angle; the old run's
  radio call then puts Leon in its event routine in the same tick, which the reference does not host.

Commands (old trace and data tree are private):

```
re4ref --tree $TREE --fixture fixtures/door103-walk.txt --out door103.trace
plays_right.py door103.trace <old run-output.txt> --offset 828 --window 1:323 \
    --tolerances tolerances.json --fields p,a,mf,ms,ps
```

## 8. Limits

- One fixture with walking. Running, turning, aiming and shooting have no old-game trace to agree with
  yet: their next fixtures need a logic-trace run with those inputs.
- The camera is in the trace but has no old-game agreement (hash only in the old trace).
- Not hosted: scenario, doors, events, enemies, items, effects, sound, HUD, partner. Their entry points
  log; a fixture that needs them diverges where it first calls one (the `stub` field names it).
- Heap pressure is not modelled (one heap); the frame loop's `GetSystemVcnt` is fixed at 2.
- A resume restarts the idle loop without its key history: allow a start-up window (here 51 ticks of
  height differences) or resume at a loop restart.
- The reference is a PC build only; the engine's own PC-against-SH-4 check is the Determinism gate.

## Actors: Ashley and the Ganado (lane eng-host2, 2026-11-19)

The reference also hosts Ashley as the partner and the Ganado, so E1 (Ashley) and E2 (Ganados) have their
plays-right reference. Every agreement number here is PC (reference) against Flycast (old game).

### What is hosted

| Actor | Original files compiled as they are | Comes in by |
|---|---|---|
| Ashley (enemy id 3) | `pl_npc.cpp` (cSubChar: follow, wait, hide, carried, damage), `pl11.cpp` (the pl11 module's cSubAshley) | `SubCharInit(1, pos, yaw)` (pl_sub.cpp), as the room scripts create her; `SubCharCtrl` for their commands |
| Ganado (em10 library) | `em10.cpp`; the per-type set files `em12_set` (farm), `em15_set` (village square), `em16_set` (r11d hill); `em_set.cpp` (enemy list), `em_sub.cpp` (helpers), `dmg.cpp` (damage records), `em_dm_val.cpp` (damage values) | `EmSetFromList2(entry)` on the room's enemy list (`etc/emleonNN.esl`) |
| Services they reach | `route_ck.cpp` (route points: `pG->Rtp` from the room's RTP), `area.cpp` | original, as under Leon |

- **Closures** (eng-shell-map method, variant B, on top of E1; `E:\RE4DC-Lanes\eng-host2\s\closure2.py`):
  - Ashley adds 2 files, 37,418 B of SH-4 code, 38 interface symbols.
  - The Ganado adds 9 files (em10 pulls in the old port's `scheduler.cpp`), 292,562 B of code, 191
    interface symbols.
  - None of those symbols is a row of `closure-map.tsv`. Every row, and what re4ref does with it:
    `hostref/closure-map-actors.tsv` (223 rows: original code 42, SDK or libm 6, host adapters 3, stubs 129, not linked 43).
  - The lab33 image holds neither pl11 nor the cSubChar routines only pl11 reaches (`--gc-sections`), so
    Ashley's graph comes from the SH-4 objects (`objgraph.py`). Control: dropping pl11 and em15_set from
    the seeds shrinks both closures.
- **Module entries** (`_prolog`) are linked under their own names (`-D_prolog=em15_prolog`, Makefile).
  `EmReadSearch` (host_actors.cpp) loads the archive, runs the entry once and keeps the init function it
  registered, as `setEmModule` does.
- **Prepared archives:** the Dreamcast tree's enemy archives (em/emNN, em/pl11) keep most FCV clips' keys
  in `dc/mot/<crc>-<fnv>.fcv` (their MTC table). The reference loads those files with the old port's
  identity checks and gives motion.cpp the key table, as `native_motion.cpp` does (host_data.cpp).
- **Argument-order adapters** (the atari_init.h trap again): `registPlAction__8cSubCharP3Vecf` (player.cpp
  passes an extra int before the float) and em_sub.cpp's `AtSphereCapsuleCk` (floats declared first; the
  Makefile renames em_sub.o's reference to the adapter with `objcopy --redefine-sym`).
- **Stubs:** `host_actor_stubs.cpp` is generated by `gen_stubs.py` from the link's undefined references.
  Each logs the call and returns zero of the declared return type, taken from the headers with `decltype`
  (so a float comes back in the x87 register). They cover effects, sound, lights, HUD, room controllers
  (`Ctrl11/12`), the Ganado's held objects (`SetWeapon`, `SetObj12`), doors, windows, ladders and items.

### Trace v2

`# re4ref trace v2`: the T line is v1's, so old traces still compare. After it, per tick:

```
A t=60 k=3 id=15 e=14 p=c62ec55e,bb7c0000,c44f4eb4 a=00000000,403bb23a,00000000 m=E02C,00000000,0 r=02010100
  hp=440 be=02002077 f=00000109 ps=0df9fc41 rc=4
R t=60 other=0 pl=0 cam=0 obj=0 spawn=0 em=0,0,0,4
```

| Field | Content |
|---|---|
| `A` | one line per live enemy-list work other than Leon, in alive-list order (`k`) |
| `id`, `e` | enemy id; the enemy-list entry it came from (`ff`: not from the list, Ashley) |
| `p`, `a`, `m`, `r` | position, angles, motion (`Exxx`: slot of the actor's own archive), frame, state; routine bytes |
| `hp`, `be`, `f` | life, `be_flag`, key flags (Ganado: the work's flags word at +0x3E0; Ashley: subFlags and subFlags2) |
| `ps` | discrete hash: be_flag, stat, id, type, Mot_state, life |
| `rc` | generator calls this actor made this tick (its `emMove`, wrapped by prep.py) |
| `R` | generator calls this tick by caller: other, player, camera, objects, creation, each actor |

### Agreement with the old game

- **What the old traces have:** enemies appear only in the decision-trace runs' LP lines: id and position
  of every live enemy every 4th tick, in alive-list order. No recorded run has their angles, motion,
  routine or life (logic_trace.cpp's `LE` lines were never switched on in a kept run).
- **So the agreement is on position, every 4th tick.** `plays_right.py --actor` matches the actor by id and
  rank in the alive list.

| Actor, fixture | Old run | Window, within tolerance | First divergence and cause |
|---|---|---|---|
| Ganado 0x14 (walks), `bell-ganado` | cachefoot `st-bell-l` (bell gate, village square) | t=185 to 317: 33 samples; 13 bit-identical (t=187 to 235), then 1 to 72 float steps, 0.002 units at most | t=319, position 43 units. The room's event starts at t=318 (`sky event: state=3`, Stop_flg 0x80400100) and freezes the old Ganados; scenario and event code are not hosted |
| Ganado 0x1f (roof) | same | t=185 to 349: 41 samples, 33 bit-identical | t=351, after the same event |
| Ganados 0x1e, 0x1c | same | the whole run (75 samples): 0.004 and 0.37 units. 0x1c sits 0.37 off its spawn in the old run (a push the reference does not host) | none |
| Leon, same fixture | same | 133 ticks: angles and frames exact, position 0.027 units | none in the window |
| Ashley, `hill-ashley` | logicbudget `dt-lbt0-dec-bk11d` (r11d, the hill path) | t=185 to 289: 26 samples within 0.018 units, her idle sway in phase | t=291, 3.2 units. She starts walking at about t=288, inside the room's opening event (Stop_flg 0x80400100, t=185 to 370); the old trace has no routine to tell which scripted command moved her |

How the Ganado window is reached (`bell-ganado.txt`):
- Leon is resumed as the old trace has him at t=184.
- The four Ganados the old run created (entries 0x14, 0x1c, 0x1e, 0x1f, after the characters' move of the
  pass that ends at t=185) are created the same way.
- `--rng-feed <old trace>:183` starts each tick's generator where the old run's did. **Without the feed
  the walking Ganado diverges at t=191** (1.6 units): the old run's other actors and effects draw from the
  same generator (risk 1 of SHELL_MAP.md), so the engine must keep every draw in order.
- `--stop-feed` (Stop_flg from the old trace as well) does not move the t=319 divergence: the freeze is
  in Status_flg, which the old trace records only as a hash.

```
re4ref --tree $TREE --fixture fixtures/bell-ganado.txt --rng-feed <st-bell-l run-output.txt>:183 --out bell.trace
plays_right.py bell.trace <st-bell-l run-output.txt> --offset 184 --tolerances tolerances.json --actor e=14
re4ref --tree $TREE --fixture fixtures/hill-ashley.txt --rng-feed <dt-lbt0-dec-bk11d.txt>:183 --out hill.trace
plays_right.py hill.trace <dt-lbt0-dec-bk11d.txt> --offset 184 --tolerances tolerances.json --actor id=03
```

**The fixtures that would record the missing fields** (emulator runs, outside this PC-only lane):
- **Ashley:** r11d with the bk-r11d warp minus its `kill` lines; `LOGIC_TRACE=1` with the decision trace
  and `RE4DC_LOGIC_TRACE_EM_FROM=371`, `EM_TO=1100` (after the opening event: the LE and LF lines give her
  id, routine word, motion state and frame, life, position and yaw every tick); a pad script that waits to
  t=400, walks forward 60 ticks, stands 60, walks 60. Ashley then follows Leon with no event running.
- **Ganado:** the same EM window on the bell gate (`EM_FROM=185`, `EM_TO=330`) gives its routine and life.

### Controls (`controls.sh`, all as they must)

| Check | Must | Result | First divergence |
|---|---|---|---|
| determinism-ganado (bell-ganado twice, Ganado 0x14) | PASS | PASS | none |
| drop-rng-ganado (that Ganado's first generator call from tick 1 dropped) | FAIL | FAIL | tick 7, generator 74b3 against cd59 |
| determinism-hit (bell-ganado-hit twice) | PASS | PASS | none |
| late-hit (the handgun hit on 0x14 one tick later) | FAIL | FAIL | tick 60, position 10.5 units (the flinch starts a tick later) |
| determinism-ashley (square-follow twice, Ashley) | PASS | PASS | none |
| follow-dist (Ashley 10% further from Leon while she follows) | FAIL | FAIL | tick 51, position |

- Leon's four controls are unchanged (same ticks as section 6).
- The hit (`hit <tick> <entry> <weapon>`) is registered as pl_wep.cpp does for an enemy on the line of
  fire. The handgun takes 360 of the Ganado's 800 life (em_dm_val.cpp).
- `square-follow` gives Ashley `SubCharCtrl(1, 1)`: control(2) clears her wait bit (pl_sub's comment
  "0 follow, 1 wait" has them the other way round). She follows Leon across the square at about 930 units.

### Limits

- Against the old game: positions only, every 4th tick. Angles, motion, routine and life compare only
  reference against reference until the LE fixtures above are recorded.
- The old runs' Ganados hold weapons and carts (`SetWeapon`, `SetObj12`), push objects and run room events;
  the reference stubs those. Ladders (`SceAtCheckLadder`) and doors answer "none".
- Ashley carried and released (em10 takes her, `cSubChar::moveBull`) is in the closure and the build, but
  no fixture exercises it: no old trace records it.
- One heap; `GetSystemVcnt` fixed at 2. The old port's alive cap (4) is replaced by the fixture creating
  the entries the old run created.


## Outcome reader (lane eng-svc5, 2026-11-20)

The gate's reader: `tools/plays_right/outcome.py` judges two runs of the same inputs by **outcome**, and **fails closed**.
`plays_right.py` stays the per-tick diagnostic (now strict by default as well, below). Status: finished, unaudited.

```
outcome.py A.trace B.trace --tolerances tolerances.json [--offset N] [--expect-ticks LO:HI] [--actors e=14,id=03#0]
           [--pos all|final] [--log a|b|ab] [--json out.json]
```

| Outcome | How it is judged |
|---|---|
| Route | Leon's position at the last tick, within `pos` (1 unit) per axis |
| Position | Leon's and every actor's position within `pos` on every compared tick (`--pos all`, the default), or at the last tick each has in both runs (`--pos final`) |
| Kills | which actors' life reaches 0 from above 0, and when (within `event_ticks`) |
| Damage | every drop of an actor's life (and Leon's, when both runs record it): the amounts exact and in order, the ticks within `event_ticks` |
| Triggers | actor spawns (first tick in the alive list) and removals; the event word (Stop_flg) changes in order, where both runs record it |
| Clears | the room clear: the first tick every list enemy that appeared is dead or gone |

`event_ticks` (tolerances.json, new): 3 ticks (0.1 s at 30 ticks a second), accepted by the integrator (HANDOVERS.md H-014.5). Every native
pair on the PC is 0 ticks apart.

**Fails closed.** Each of these is a failure whatever the values: a missing or unreadable file (`missing-file`); no
trace record (`no-records`); a record tag the reader does not know, or a line that is not a record in a trace file
(`unknown-line`; serial logs are read with `--log`, which skips and counts non-record lines); a record without a field
the outcome needs (`malformed`); a NaN or infinity in a position or angle (`non-finite`); two records of one tick or of
one actor in one tick (`duplicate`); ticks missing from the expected set, which is `--expect-ticks` or the H line's
`ticks=` (a logic trace without `--expect-ticks` fails: its length is not known) (`short-run`); ticks outside it
(`extra-tick`); an actor named by `--actors` absent, or an actor of one run never in the other (`missing-actor`).

**Formats.** re4ref traces (`# re4ref trace v1/v2`: H, T, A, R lines; the engine's hill trace writes the same) and
logic-trace records (LT, LE, LF, LL, GE and the other L* records of `logic_trace.cpp` and the engine's fight trace).
Actors are matched by enemy-list entry (`e=`), or by id and order of first appearance when they have none (Ashley).
Old-game logs with enemies only every 4th tick (LP lines) cannot pass: they are `plays_right.py --lenient` material.

**Controls** (`outcome_controls.py <out dir> [--engine-log serial.txt:LO:HI]`; 30 rows, all as they must,
`E:\RE4DC-Lanes\eng-svc5\ev\outcome_controls.md`):

| Row | Must | Input |
|---|---|---|
| determinism (door103-walk, bell-ganado-kill, bell-ganado-clear, hill-ashley) | PASS | the reference twice |
| missing-file, no-records | FAIL | B absent; B empty |
| unknown-line (record, text) | FAIL | a `Q t=20` record; a serial line in a trace file |
| malformed | FAIL | one A line without `hp=` |
| non-finite | FAIL | one actor position a NaN |
| duplicate | FAIL | one T line twice |
| short-run (cut, gap) | FAIL | B cut after tick 300 of 520; B without tick 100's T line |
| extra-tick | FAIL | one tick after the last |
| missing-actor (gone, required) | FAIL | B without 0x1e; `--actors e=55` |
| route, position | FAIL | door103-walk with the walk 2% longer (re4ref `--control walk-speed=1.02`): 8.5 units at the end |
| kill | FAIL | bell-ganado-kill without its third hit |
| damage | FAIL | the second hit by weapon 0x14 (another amount) |
| damage-time | FAIL | every hit 30 ticks later (`--control late-hit=30`) |
| trigger-spawn, trigger-gone | FAIL | 0x1f created at tick 20; 0x1f's records removed from tick 400 |
| clear | FAIL | bell-ganado-clear without the hits on 0x1c |
| logic form | PASS | bell-ganado-clear as LT/LL/LE records with serial lines between, against itself (`--log ab`) |
| logic form without --log / without --expect-ticks | FAIL | the same files |
| trigger-event | FAIL | the event word changed from tick 200 |
| engine log against itself | PASS | eng-e2's Flycast fight log (f16t-1, 901 ticks, 4 Ganados) |
| engine log, Leon hit once more | FAIL | one more life drop on Leon |

**New fixtures:** `bell-ganado-kill` (three handgun hits kill Ganado 0x14 at tick 140) and `bell-ganado-clear` (all four
Ganados die; the room clears at tick 160). Reference-only (the old run has no shots).

**Strict `plays_right.py`.** Default strict structure (eng-svc4's draft, checked): a missing tick (a tick with A or R
lines but no T line counts), a missing field, a non-finite value, a duplicate tick, or a tick or field count different
from the expected set (`--expect-ticks`, `--expect-count`) fails with verdict STRUCTURE. `--lenient` is the old reader,
for sparse old-game logs. `controls.sh` adds one control per structure fault (18 rows, all as they must,
`E:\RE4DC-Lanes\eng-svc5\ev\pr_controls.md`). Its `drop-rng` control moved to bell-ganado: on door103-walk Leon's walk no
longer draws from the behaviour generator (his eye wander is presentation since eng-e1d), so it dropped nothing and
**passed**, a stale control found by re-running it.


## Shots, the magazine and controls that fail closed (lane eng-e1h, 2026-11-20)

**The reference fires.** Its item stub answered 0 rounds, so A while aiming took the empty-gun branch and no shot ever
fired (lane eng-e1g's finding). `hostref/host_stubs.cpp` now holds the armed handgun's magazine with item.cpp's rules
for a type-1 weapon: the new game's 10 rounds loaded, none carried; trigger spends a round (0 when empty), reload and
reloadable move carried rounds in. The default image's `host/e1_stubs.cpp` follows the same rules (the fight image's
magazine refills at 3 left, so the two agree for its first 7 shots). The first shot's rumble no longer crashes the
reference: the core archive's rumble table is converted to the PC's byte order at load (SERVICES.md section 43).
aimchk no longer replaces the magazine or skips a rumble pattern; it logs every shot line (`shots.txt`:
GetWepTargetList2's line, scenery hit, enemies crossed, each enemy's distance from the line).

**Fixture `shot-ganado`** (fixtures/shot-ganado.txt): bell-ganado with Leon resumed facing yaw -1.54, aiming from tick
150 and pressing A at 160 (and 180). The shot at 161 crosses Ganado 0x14 at about 2,430 units: its life drops 800 to
500 at tick 162; the second shot misses. outcome.py: the reference twice PASS; the native build against the reference
PASS (321 ticks, 4 actors, positions 0 apart, damage e=14 once); **control** without the press at 160: FAIL, damage
(and positions from tick 162). Evidence: `E:\RE4DC-Lanes\eng-e1h\ev\shot\shot-pc.txt`.

**Controls that fail closed.** svc_controls.sh exited 0 with an empty table when the odump build was missing (its runs
exit inside the table's pipeline), and controls.sh exited 0 whatever its rows said (the status was set in the
pipeline's subshell). Now:

| Script | Exits 2 (incomplete) when | Planned rows | Control (each exits 2) |
|---|---|---|---|
| hostref/svc/svc_controls.sh | odump or native build, a fixture or the tree missing; a run fails; a row has no comparison report; fewer rows than planned | 5 a fixture + 47 | `RE4_HOSTREF_BUILD=<empty folder>`; a fixture that does not exist |
| tools/plays_right/controls.sh | the reference binary, a fixture or the tree missing; a run fails; a comparison exits other than 0 / 1 or writes no report; fewer rows | 18 | the reference binary absent |
| tools/plays_right/outcome_controls.py | the binary, the tree, a fixture or the engine log missing; a run fails or writes no trace; fewer rows | 28 (30 with --engine-log) | `--bin` absent |
| hostref/svc/svc5_units.sh | no map, no binary beside the map, a unit whose object the map does not name | - | a map copied without its binary; a unit that does not exist |

A WRONG row still exits 1. Full runs on the lane's final reference: svc_controls 77 rows, controls.sh 18,
outcome_controls 28, all as they must (`E:\RE4DC-Lanes\eng-e1h\ev\ctl2\`).

## The reader's last false passes, and the shot on the engine against the reference (lane eng-e1k, 2026-11-21)

Status: finished, unaudited. PC numbers are re4ref (hostref); engine numbers are **Flycast** (function checks).

**outcome.py, four false passes closed (H-016.5).** Each new control row below passed under the reader before this lane
(`E:\RE4DC-Lanes\eng-e1k\ev\item1\old-reader.txt`) and now fails as it must:

| Gap | Rule now | Control (outcome_controls.py) |
|---|---|---|
| An interior actor sample deleted from a surviving, stationary actor passed (positions were compared only where both runs had a record) | every actor has a record on every tick from its first to its last (`missing-sample`); a park and re-queue is not hosted yet, so a gap always fails | 0x1e's A line of tick 250 removed: FAIL [missing-sample] |
| Every R line removed skipped the R check (it ran only when some R line was there) | a re4ref trace whose H line declares a room needs an R line on every T tick (`short-run`) | B without any R line: FAIL [short-run] |
| A present but unrecorded position (`pos=~`) was read as "no value" and skipped | a position or angle field that is present but holds the sentinel (`-`, `~`, empty) is `malformed` | one LE line with `pos=~`: FAIL [malformed] |
| Yaw was checked for finiteness only | Leon's and every actor's yaw within `ang_deg` (1 degree, the fixtures' value; wrapped) on the position's ticks (`yaw`); a yaw one run records and the other does not fails; the engine's LE `ay=` is read | 0x1e, and Leon, turned 2 degrees from tick 300: FAIL [yaw]; turned 0.5 degrees: PASS; LE lines without `ay=`: FAIL [yaw] |

outcome_controls.py: 35 rows (37 with `--engine-log`), all as they must (`ev\ctl\outcome_controls.md`). No existing fixture
needed a fix: the village engine run against the PC reference (eng-e1g `f1`), and shot-ganado, door103-walk, hill-ashley,
hill-follow and bell-ganado-hit native against reference all still PASS (`ev\item1\existing.txt`). The village no-clamp
run (eng-e1g `vnc`, Flycast) now fails first on yaw at tick 424 (2.52 degrees), before position at 519 (`ev\item1\vnc.txt`).

**The shot's target list is native (H-016.3).** `GetWepTargetList2` (the handgun's shot, pl_wep.cpp PlWepHitCheck2) is
`services/aim/aim.cpp` in every image: the scenery through the native collision service, the enemies on the actor table
with the original's rules (hit-only kinds, the line's ground frame, the nearest box each enemy's segment enters, nearest
first, a full list keeps the nearest, flag 0x4000 on listed boxes). The default image's stub is gone: with no enemy on
the line the list is empty by computation (the report's `E1 AIM LIST` line counts shots, scenery hits and listed
enemies). FIGHT=1 and BOSS=1 weaken em_sub's body (FIGHT 109 to 108 service functions, BOSS 58 to 57).
PC check (hostref aimchk, both lists on every shot; `hostref/svc/aim_check.sh`): shot-ganado 2 of 2 shots and
aimfire-ganado 10 of 10 the same (count, enemy, box, attribute; box distance within 0.004 unit); the control
`RE4_AIM_CONTROL=grow` (boxes 25% larger) FAILs the list (box distance 32.8 units apart) (`ev\ctl\aim_check.out`).
The PC controls after this lane's reference change: svc_controls.sh 77 rows, controls.sh 18, outcome_controls.py 37,
all as they must (`ev\ctl\`).

**The shot fixture on the engine.** The FIGHT=1 image plays a re4ref fixture file when the boot file `SHOT.TXT` is on the
disc (`engine/fight/shot_e2.cpp`). What the engine is given: the fixture file, verbatim
(`tools/plays_right/fixtures/shot-ganado.txt`), and nothing from the reference's run. It plays the keys re4ref reads in
re4ref's order: room and enemy list (must be the image's: r101, list 0), Leon's placement, weapon (must be 2 0), the seed
(set after Leon is created and resumed), the resume, `god`, the four list entries created by the original EmSetFromList2
after the enemy table's move of tick 1 (`post`), and the pad lines as they are. Any other key (`hit`, `sub`, ...) refuses
the scene (`E2 SHOT REFUSED`): no planted hit. Where the fixture says nothing the engine starts where re4ref does: no
room script or scenario task, no room-entry spawn, no difficulty points (re4ref does not host game.cpp), no warp flags.
The scene is always traced and says "not a timing run".

**One reference fix.** The first run differed from tick 135: the reference's Ganado drew its voice timer from the
behaviour generator, the engine's from the presentation generator (the owner's split, game/fight.mk `PRESENT_em10`).
The reference now splits em10's presentation callers the same way (`hostref/Makefile PRESENT_EM10`); the engine was not
changed.

**Result** (`tools/plays_right/shot_engine.py`; Flycast test disc s1 of commit 1543e4780, judged against the reference
of 313d1cd71; evidence `E:\RE4DC-Lanes\eng-e1k\ev\shot-s1\shot_engine.md`):

| Actor | Reference (re4ref) life drops | Engine (Flycast) life drops |
|---|---|---|
| Ganado 0x14 | tick 162, 800 to 500 | tick 162, 800 to 500 |
| 0x1c, 0x1e, 0x1f | none | none |

321 ticks, 4 actors: route 0, position max 0 units, yaw max 0 degrees, no kill, no clear; the bit patterns agree on every
compared field. Controls, each an engine scene of its own on the same disc, judged against the same reference:

| Scene | Must | Got |
|---|---|---|
| SHOT | PASS | PASS |
| SHOTNP (the fixture without the press at 160) | FAIL [damage] | FAIL: A amounts [300], B [] |
| SHOTDMG (boot file: 100 more life taken at each hit) | FAIL [damage] | FAIL: A amounts [300], B [400] |
| SHOTLATE (boot file: each registered hit held 30 ticks) | FAIL [damage] | FAIL: A at 162, B at 192 |

Run: `build_console_disc.sh --scenes SHOT,SHOTNP,SHOTDMG,SHOTLATE`, the disc in Flycast, then
`RE4_TREE=<tree> shot_engine.py <serial.txt> <out>` (it runs the reference itself).
