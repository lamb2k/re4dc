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
