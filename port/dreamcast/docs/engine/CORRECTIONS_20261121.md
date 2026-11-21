# Corrections, game settings and guards carried into the engine (lane eng-fix1, 2026-11-21)

Status: **finished, unaudited.** Part 1 (reading and PC reference runs) and part 2 (wiring, integrator rulings H-026 and
the owner's three decisions of 2026-11-21). Tiers: the PC reference (host replay, exact traces) and plain Flycast
function runs (slot std1: not a timing tier). No console.

- Old port: the Test 27.2 release, source `6e86de745` (`src/`, `include/` identical to `origin/t15/int`), recipe
  `tools/d367/build-r21.sh` plus `tools/d367/test27.2/release-knobs.txt` (Disc 1) and `release-knobs-disc2.txt` (Disc 2).
- Engine: `origin/engine` 505c4da2d merged (lane eng-e2a merged: link-check baselines FIGHT 73, BOSS 26).
- The old port's `RE4DC_` names are called "the old port's conditionals" here; they are carried as one of three kinds:
  - **corrections:** the original code made right on this CPU (little-endian SH-4) and compiler (GCC). Built in,
    unconditional, in `engine/host/corrections.h` (included by the hosted prelude `engine/host/e1_prelude.h`) and, for
    the three that must be per unit, `engine/game/hosted_corrections.mk`.
  - **game settings:** the owner's product choices, in `engine/game/game_settings.mk`, each with who decided and when.
  - **guards:** tripwires against failures the old port had; counted in `engine/host/guard_hooks.cpp` and printed as
    `E1 GUARDS ...` in every E1-family scene summary; the selector fails a timing scene where a count is not 0.

## 1. For the integrator and the owner

Departures from the GameCube version, chosen by the owner (game settings):
1. At most 4 Ganados alive at once, Novistadors in the same 4 (owner 2026-10-15, 2026-10-17 "lets do cap 4 for the
   zombies", 2026-10-18).
2. The PS2 version's enemy spawns per chapter (owner 2026-10-15 "i want the ps2 logic holistically for enemy spawns").
3. No ambient farm animals in stage 1 (owner 2026-10-17 "Get rid of them asap").
4. Quick weapon select, X + D-pad (owner 2026-11-21 "i want to keep quiock weapon switch"). Not in the GameCube game.
   ON, but its code (`src/game/sscrn.cpp` re4dc_qw_frame / qwTask, the weapon list, the X + D-pad chord of the old pad
   layer) is in nothing the engine hosts yet: a counted stub shows it in every scene summary
   (`E1 STUBCOUNT quick weapon select ON (owner), not hosted ... calls=1`). Request below.

Open (not set): `LIGHT_CUT_HOLD` (r11f barn light cut) and `SS_MENU_ANIM_RT` (inventory menu flash per elapsed tick);
section 6.

What changed in play, measured on the PC reference: the Ganados' routine bytes. With the corrections, a hit Ganado's
neighbours react as the released game's do (bell-ganado-hit: Ganado 0x1e leaves its Find reaction at tick 61, routine
1/0x0D to 1/0x10; shot-ganado: Ganado 0x1f at tick 163, 1/0x15 to 1/0x10). Kills, damage amounts and ticks, and the
room clear are unchanged on every fixture; positions and angles of the Ganados after a hit are not (section 5).

Plain facts for the owner:
- The released Test 27.2 Disc 2 program compiles a second copy of `src/em10/em10.cpp` for module em1f without the
  Ganado routine-byte correction: the old port's `port/dreamcast/game/Makefile:68` sets `RE4DC_GANADO_ROUTINE_BYTES=1`
  for `$(OBJDIR)/mod/em10g/shared/src/em10/em10.o` only; `mod/em1f/src/em10/em10.o` is built without it (read from the
  release build's preprocessed units). The release line was not touched.
- Every E1-family image links with the corrections, guards and settings; link-check SERVICE counts unchanged (section 7).

## 2. How the list was made

1. `make -n` of the release build (both disc programs) in a detached worktree of `6e86de745`, then each `src/` compile
   line run as `-E -dM` with the generated headers: the value of every old-port conditional in every release unit.
2. The same for the engine images (default, FIGHT, BOSS, SENDABLE) and the PC reference.
3. A conditional belongs to a unit when its name is in the unit's source or a `src/` / `include/` header the unit read.
4. Each release-on conditional ruled by reading its sites (scripts and outputs: section 10).

## 3. The three kinds: every item of the former class (a)

### Corrections (in `engine/host/corrections.h` unless "per unit")

| Correction | What in the original depends on the GameCube's byte order or compiler | For the later source pass |
|---|---|---|
| `GANADO_ROUTINE_BYTES` | `src/em10/em10.cpp:550-559` (EM_RTN) and `:596-606` (EM_RTN_SET) compare and write the big-endian status word `stat & 0xFFFF0000 == r0<<24 \| r1<<16`; on the little-endian SH-4 the upper half is r_no_3 / r_no_2 | clean: resolve to the named-byte branch; keep the `__PPC__` test (both branches matter only if a PowerPC build is kept) |
| `EM35_ROUTINE_BYTES` | `src/em35/em35.cpp:1779`: the same big-endian routine word for Mendez (0x010D000n) | clean, as above |
| `STAT_ROUTINE_BYTES` | the `STAT_BE()` constants of the routine word (7 sites: player, pl_class, pl_sub, pl_wep); the swap is `engine/host/e1_prelude.h:20`; the only `src/` test is the STATDIAG log, `src/game/player.cpp:1616` | needs care: `STAT_BE` is a macro both builds use (identity on PowerPC); the pass would write the constants in this byte order and drop the macro |
| `SUB_EM_FUNC` | `src/game/pl_sub.cpp:373`: `setEmFunc` reads `mot` from PowerPC register r4 (a register pin); GCC drops the pin, `subFunc` was an uninitialised local | clean (the else is "nothing": the store is added) |
| `SAVE_ROW_FIX` | `src/game/card.cpp:3692`: the key count's low byte read as byte 3 (big-endian) | clean |
| `SS_MSG_FIELDS` | `src/Sscrn/ss_pzzl.cpp:201`: message fields at the GameCube's fixed offsets 0xFC / 0x1D1; GCC places the vtable pointer first | clean |
| `ID_ALPHA_SAT` | `src/game/id_sys.cpp:1136`: `(u8)` of a float above 255 (undefined in C): the GameCube's conversion saturates, GCC's wraps (title logo 314 became 58) | clean |
| `GAME` (per unit) | the non-PowerPC paths. In hosted units: `src/game/cam_ctrl.cpp:1173/1185` (roomInit: placement fill before Check), `:1292` (Move), `:2377` (endPushObject), `:2406` (EndLookDownEm), `:2436` (endScope), `:2494` (LowerBinocular), `:2541` (setMotionBaseMatPtr): GCC compiles cCamera's destructor to a bare memset, so a destroyed extra kept a 0x09090909 vtable and the next delete faulted; `src/pl11/pl11.cpp:22`, `src/em15/em15_set.cpp:47` and every enemy module's Init: `new (em) T()` value-initialises (zeroes the archive cEmMgr::construct set), CodeWarrior did not | needs care: the same conditional also gates old-port hooks (`game.cpp` native_ui.h, `r100.cpp` event-file glue), so a pass must split it |
| `ROUTE_CH22` (per unit: pl14) | `include/pl14.h:43,210`, `include/obj13.h:13`: Luis's asm-label calls name nothing off the GameCube; forwarded to cEm members | needs care: the same name is route gating in `stage.cpp`, `snd.cpp`, `trans.cpp` and the 2-2 rooms |
| `ROUTE_CH23` (per unit: em35, em3b) | `src/em35/em35.cpp:238`, `src/em3b/em3b.cpp:109`: placement construction keeps the module archive (value-initialisation) | needs care: route gating elsewhere |

Why three are per unit: `GAME` reaches the old port's platform layer in `game/game.cpp` and `st1/r100.cpp`, and the
prelude is also force-included by engine C++ and the native services, where `RE4DC_GAME` names reference-only hooks
(`services/model/model_svc.cpp:45`). `ROUTE_CH22` / `ROUTE_CH23` are corrections only in pl14 / em35 / em3b.
`model.h` includes the old port's `actor_lifetime.h` under `RE4DC_GAME`: the engine's is empty
(`engine/host/oldport/actor_lifetime.h`; its declarations serve the old drawing path, off).

### Game settings (`engine/game/game_settings.mk`)

| Setting | Units | Decided |
|---|---|---|
| `ALIVE_CAP`=4, `ALIVE_CAP_N`=4, `ALIVE_CAP_PARK`, `ALIVE_CAP_R101`, `ALIVE_CAP_ON`, `R101_ALIVE_CAP`=4, `R101_CAP_N`=4, `R101_CAP_WAVES` | em_set, sce_com, sce_sys, em_wrap, the room units, r101 | owner 2026-10-15 / 10-17 / 10-18 (cap 4) |
| `ROUTE_CH21_FULL` | em_set, r10c | the r10c ambush goes through the cap (lane ch2rooms20 under the cap rule); its held sends are null-checked by design |
| `PS2_ENEMY_RULES`, `PS2_ENEMY_ROOMS`=0x3ff, `PS2_CH2_ENEMY` (only where its list data exists) | stage, r100 r101 r104 r107 r108 r10f r111 r113 r118 r11a-r11f r200 | owner 2026-10-15 (PS2 spawns per chapter); 0x3ff the release's value (integrator H-026) |
| `ANIMALS_OFF` | em_set | owner 2026-10-17 |
| `QUICK_WEAPON` | sscrn (not hosted) | owner 2026-11-21 |
| castle (later, commented): `ALIVE_CAP_NOVIS`, `_DEFER_FLAGS`, `_DEFER_GOTO_R207`, `_R202_GATE`, `PS2_CH3_ENEMY`, `PS2_CH4_ENEMY`, `PS2_ENEMY_CASTLE`=0xe7 | em_set, stage, em_wrap, st2 rooms | owner 2026-10-18 (Novistadors in the cap), chapters 3-4 PS2 spawns |
| open: `LIGHT_CUT_HOLD`, `SS_MENU_ANIM_RT` | cam_ctrl, ss_pzzl | section 6 |

### Guards (in `engine/host/corrections.h`, counted in `engine/host/guard_hooks.cpp`)

| Guard | The old port's failure it was written for | What in the engine would have to be wrong for it to fire | Counted |
|---|---|---|---|
| `EM_READ_RETRY`, EM_MUST (bosses, the r11b boat) | issue #52: an enemy module read failed on GDEMU (no free DVD queue slot, GD read error) and the spawn returned 0 | the engine refused the spawn: an unhosted kind or module, a missing archive, a full enemy table | yes: `re4dc_em_sleep`, `E1 GUARDS em_must_retry N` |
| `EM_READ_RETRY`, EM_OK (room code skips a 0 spawn) | the same | the same; and by design a spawn the cap holds returns 0 in r10c (`ROUTE_CH21_FULL`) | no: `include/types.h` macro, no hook |
| `R10C_SPAWN_LIVE_GUARD` | issue #52 follow-up: a Ganado's model init failed in heap 4 and retired it in its first move | a Ganado whose model or pool record the engine refused | no: a test in `r10c.cpp`, no hook (r10c not hosted) |
| `R117_EFFECT_FAILURE_SAFE` | the effect pool refused the church beam (LightSet stored NULL) | the effect service refused an allocation | no: a test in `r117.cpp`, no hook (r117 not hosted) |

Every former class (a) item fits one kind. `EM_READ_RETRY` is one conditional with three parts: two guards (above) and
the loader's read retry in `read.cpp` (a service's job: not hosted).

What these change in chapter 1 if they were left out (part 1's order of risk, now all built in): the Ganado routine bytes
(every Ganado room, from the first hit in the village square), the camera's corrections (any event camera cut), the
enemy modules' construction (the r100 dog and traps, the r108 Ganados, the merchant, the r10b fish and Del Lago, the
boat), the cap and the PS2 spawn rules (every Ganado room). The route events' PS2 movies (`ROUTE_MOVIES`) belong to the
movie service, not to this set.

## 4. The camera control's corrections under `GAME`: which land in hosted code

Lane eng-e1j made the camera's evaluation native; in `cam_ctrl.cpp` only `HermiteExport`, `debugDrawRail` and `calcAddr`
are weakened to the service (the image's `n/svc4_syms.txt`). Read from the maps of the default, FIGHT and BOSS images
(`evidence/part2/link/new-*.e1.map.gz`):

| Function (`src/game/cam_ctrl.cpp`) | Correction | In the images |
|---|---|---|
| `CameraControl::roomInit` (`:1173`, `:1185`) | the placement storage filled before `Check()`, not after (a look-at or motion extra built in it was overwritten) | hosted and linked (0x254 bytes, all three images) |
| `CameraControl::Move` (`:1292`) | case 5: the destroyed motion extra forgotten | hosted and linked (0x2fc, was 0x2f8) |
| `CameraControl::endPushObject` (`:2377`) | the destroyed extra forgotten | hosted and linked (0x70) |
| `CameraControl::endScope` (`:2436`) | the same | hosted and linked (0xa4, was 0x9c) |
| `CameraControl::LowerBinocular` (`:2494`) | the same | hosted and linked (0x98, was 0x90) |
| `CameraControl::EndLookDownEm` (`:2406`) | the same | compiled, not linked (no caller in these images): moot today |
| `CameraControl::setMotionBaseMatPtr` (`:2541`) | an event teardown after the motion retired returns | compiled, not linked: moot today |
| (`:2357`) | the comment that explains them | - |

Five of the corrections land in hosted, linked code; two are in functions no image reaches yet; none is in the native
camera service.

## 5. What changes on the PC reference

The reference is now built with the corrections, guards and settings (`hostref/Makefile` `CORRECTIONS ?= 1`:
`corrections.h` force-included, `HOSTREF_SETTINGS` from `game_settings.mk`). `CORRECTIONS=0` builds the old reference;
it exists only as `svc/refctl.sh`'s control build. The variant check refuses an existing `build/hostref` folder made
before this change (its variant name now ends `-corrections1`): delete it once (`make clean`) and rebuild.

Every fixture of `tools/plays_right/fixtures` and `hostref/svc/aim_fixtures`, the old reference (A) against the new (B),
`outcome.py` with the agreed tolerances (`evidence/part2/cmp-corr.md`):

| Fixture | outcome.py | First difference | Cause |
|---|---|---|---|
| bell-ganado-hit (and its aimchk run) | FAIL: position, yaw; kills, damage, clear equal | t=61: Ganado 0x1e routine 1/0x0D to 1/0x10 (old stays), one more behaviour draw; first position over tolerance t=165, e=14, 4.4 units | the Ganado routine-byte correction (bisected in part 1: it alone reproduces every difference) |
| bell-ganado-kill | FAIL as above | t=61; t=63 e=1e 15.5 units | same |
| bell-ganado-clear | FAIL as above; clear at t=160 in both | t=61; t=141 e=14 61.7 units | same |
| shot-ganado (and its aimchk run) | FAIL: position, yaw; route 0.57 units | t=163: Ganado 0x1f routine 1/0x15 to 1/0x10, Leon's camera eye moves the same tick; t=245 e=14 4.5 units | same |
| bell-ganado, door103-walk, e1-route, hill-ashley, hill-follow, hill-follow-g, square-follow, aim-ganado, aimfire-ganado | PASS | identical, bit for bit | - |

The shot itself does not move: on both references Ganado 0x14 goes from 800 to 500 life at the same tick (trace tick
162; the fixture presses at 160 and 161). Quick weapon select changes nothing in the reference: no reference unit names
it, and the reference built with and without it has identical code in all 98 objects (compared without debug info,
which holds the build folder's path).

`refctl.sh` has five new rows (17 rows in all, every one as it must):

| Row | Must | Got |
|---|---|---|
| bell-ganado-hit: the fixed reference against itself (outcome) | PASS | PASS: 201 ticks, 4 actors, position and yaw max 0 |
| corrections off (`CORRECTIONS=0`), bell-ganado-hit: Ganado 1e's routine bytes first differ at tick 61 | PASS | PASS: fixed 01100000, old 010d0000 |
| corrections off, bell-ganado-hit: outcome against the fixed reference | FAIL | FAIL: first position t=165 e=14 4.382 units |
| corrections off, shot-ganado: Ganado 1f's routine bytes first differ at tick 163 | PASS | PASS: fixed 01100000, old 01150001 |
| corrections off, shot-ganado: outcome against the fixed reference | FAIL | FAIL: first position t=245 e=14 4.516 units |

(shot-ganado's own determinism row is the em10 block's first row.)

## 6. Open, and what settles each

| Conditional | What settles it |
|---|---|
| `LIGHT_CUT_HOLD` (+ `_ROOMS` 0x11f), `cam_ctrl` | Whether the r11f barn's outdoor light cut on the front loft is the GameCube's own look: a still pair at r11f phase 2 front loft, engine renderer against a GameCube capture. |
| `SS_MENU_ANIM_RT`, `ss_pzzl` | Whether the engine's sub screen can draw below 30 Hz on console. |

## 7. Engine images: build and link check

All four images link with the corrections, guards and settings (objects compiled from the commit's tree; `check_link.py`
on each map; `evidence/part2/link/`):

| Image | Original functions kept (allowed) before, after | SERVICE before (origin/engine 505c4da2d) | SERVICE after |
|---|---|---|---|
| default | 384 (107,044 B), 384 (107,008 B) | 0 | 0 |
| FIGHT=1 | 796 (354,712 B), 801 (355,544 B) | 73 (28,500 B) | 73 (28,500 B) |
| BOSS=1 | 473 (150,368 B), 479 (151,368 B) | 26 (5,936 B) | 26 (5,936 B) |
| SENDABLE=1 | 384 (107,044 B), 384 (107,008 B) | 0 | 0 |

Lane eng-e2a is merged: the baselines are 73 and 26, and they are not raised (before the merge, against 18e3a6f35: 114 and
57, also unchanged). The added allowed functions are original code the corrections make reachable in already-allowed
units. Maps and lists: `evidence/part2/link-merged/` (and `link/` for the pre-merge check).

## 8. Suites, and the engine on Flycast against the new reference

Suites on the new reference (`build/hostref`, CORRECTIONS=1), after merging origin/engine 505c4da2d: `svc_controls.sh`
79 rows, `camcheck.sh` 21, `refctl.sh` 17 (12 + the five above), `tools/plays_right/controls.sh` 18,
`outcome_controls.py` 35, `aim_check.sh` (5 fixtures x 3 arms), `e2check.sh` 14 (lane eng-e2a's): every row as it must,
exit 0 (`evidence/part2/suites-new2/`; the same suites before the merge: `suites-new/`). The fixture comparison old
against new reference is the same after the merge (`cmp-corr2.md`). `camengine.sh` not run (section 11).

One Flycast test disc, run twice: from the commit e591c471a (before merging origin/engine, `runs/d1/`) and from the
merged head 9e7e3d61d (`runs/d2/`), plain slot std1 by lease (`Dynarec.Enabled` and `Sh4Clock` not set in the slot's
emu.cfg, the defaults; a function check, never a timing): LEON, HILL, FIGHT, SHOT, SHOTNP, SHOTDMG, SHOTLATE, HILLT.
**8 of 8 scenes OK** under the selector on both. The judgements below are the same on both runs (figures from d2). Every scene's summary has
`E1 GUARDS em_must_retry 0; uncounted em_ok_skip r10c_spawn_live r117_beam_null` and the quick weapon select stub
(`calls=1`).

| Judge (against the NEW reference) | Row | Must | Got |
|---|---|---|---|
| `shot_engine.py` | SHOT | PASS | PASS: 321 ticks, 4 actors, position and yaw max 0 |
| | SHOTNP (no press) | FAIL | FAIL [damage]: tick 162 e=14, reference 300, engine none |
| | SHOTDMG (wrong damage) | FAIL | FAIL [damage]: tick 162 e=14, 300 against 400 |
| | SHOTLATE (hits 30 ticks late) | FAIL | FAIL [damage]: tick 162 against 192 |
| `hill_engine.py` | Leon, engine against the reference | PASS | PASS: 729 ticks, no divergence |
| | Ashley, engine against the reference | PASS | PASS: 729 ticks, no divergence |
| | control: the reference with the presentation split off | FAIL | FAIL: first divergence tick 367 |

Both sides moved together: the same engine run judged against the **old** reference (CORRECTIONS=0) fails SHOT at
exactly the reference's own difference (`[position] tick 245 e=14 4.516 units`, `runs/d2/shot_engine_oldref.txt`, and d1 the same). The
shot's hit, damage and tick did not move on either side (Ganado 0x14, 800 to 500 at trace tick 162).

Guard control (`runs/g2/`, commit e591c471a: the hooks and the selector rule are unchanged by the merge): the BOSS scene (timing, headless) with El Gigante's enemy-list entry 0x28 given an unhosted
kind (0x2C for 0x2B, a copy of EMLIST.BIN in RAM, staged through `BOSS_EMLIST`): r119's EM_MUST spawn is refused, the
guard retries as the release does (23 retries in 900 ticks), the summary reads `E1 GUARDS em_must_retry 23`, and the
selector fails the scene: **`BOSS FAILED ... why: guard taken: em_must_retry 23`**. A first attempt that dropped the
archive (`runs/g1/`) is not a clean control: the image refuses to start without it ("E1 load: missing /cd/EM2B.ARC").

## 9. Requests for other lanes

- The lane that hosts items and the sub screen: quick weapon select needs `src/game/sscrn.cpp` (re4dc_qw_frame, qwTask:
  the case equip path, the weapon list) hosted, and the X + D-pad chord in the engine's input path (the old port's
  `platform/pad.cpp:527` posted the slot in `re4dc_qw_slot`). Until then `engine/host/guard_hooks.cpp` counts it as a
  stub in every scene summary.
- Lanes that keep a `build/hostref` folder: delete it once (the reference's variant name now ends `-corrections1`).
- The lane that will write the corrections into the source and delete the old port's conditionals: section 3 says per
  correction whether it is a clean candidate; `GAME`, `ROUTE_CH22`, `ROUTE_CH23` and `STAT_ROUTINE_BYTES` need care.
- Release line (not this lane): em1f's copy of em10.cpp without the Ganado routine-byte correction (section 1).
- eng-load1 / eng-snd1: the "belongs to an engine service" rows of the table below.
- eng-snd1: re-check its run c1mute in slot std1 of 11:39-11:42 (this lane's runner removed the slot's disc links while
  that run held them; hand-back, "Incident").

## 10. Evidence and how to repeat it

Scripts: `E:\RE4DC-Lanes\eng-fix1\s\` (part 1: `dry.sh`, `dryloop.sh`, `rel_macros.py`, `analyze.py`, `groups.py`,
`classes.py`, `gen_doc.py`, `gen_fix.py`, `bv.sh`, `fxrun.sh`, `fxcmp.py`, `suites.sh`, `ecc.py`; part 2: `p12.sh` to
`p26.sh`, `cdisc.sh`). Outputs: `E:\RE4DC-Lanes\eng-fix1\evidence\` and `evidence\part2\` (link-check lists and maps per
image before and after, the suites' result tables on the new reference, the fixture comparison), runs in
`E:\RE4DC-Lanes\eng-fix1\runs\` (serial logs, judge outputs).

## 11. Not done, not verified

- Nothing ran on a console; the Flycast runs are function runs in a plain slot (no timing claim).
- `camengine.sh` was not run (it needs LEONT and HILLT on one disc; the disc held eight scenes).
- The uncounted guards (EM_OK skip, r10c, r117) print "uncounted"; r10c and r117 are not hosted yet.
- No other E1 scene than BOSS exercises a counted guard path; FIGHT, LEON, HILL report 0 because nothing refuses.
- The table's "belongs to an engine service" and "not needed" rows outside the hosted units were ruled by unit and
  makefile comment, not site by site.

## 12. The full table

Columns: units (the `src/` and `include/` files that name the conditional); release value in the Disc 1 / Disc 2
program; where the release sets it (old makefile line); engine images E (default) F (FIGHT) B (BOSS) S (SENDABLE) and the
reference **before** this lane's part 2 (the values part 1 read; after part 2 the corrections, guards and settings are
on as section 3 says).

### Corrections: the original code made right on this CPU and compiler (built in, unconditional) (10)

| Conditional | Units | What it changes | Release D1 / D2 | Release set at | Engine before (E F B S) | Reference before | Owner / scope |
|---|---|---|---|---|---|---|---|
| `EM35_ROUTINE_BYTES` | em35/em35.cpp | Mendez routine bytes (#55): the catch hit stored the GC word 0x010D000n, routine 1 step 0xD does not exist, Mendez froze; the bear-hug callbacks released Leon at once | 1 / 1 | Makefile:80 | not built | not built | em35 (needs RE4DC_GAME) |
| `GAME` | include/TexRender.h include/cManager.h include/model.h include/obj13.h +120 | Selects the non-PowerPC source paths. In the hosted units it carries GCC/ABI correctness fixes with no option of their own: cam_ctrl (8 blocks: placement fill before Check(), destroyed camera extras forgotten: SH-4 address error 0xE0), every enemy module Init (placement new without value-init: keeps the archive cEmMgr::construct set; pl11, em15_set and about 40 more), em10 / em35 / em3b / r117 fix blocks (need it besides their option). Also gates old-port hooks (game.cpp native_ui, r100 event glue) | 1 / 1 | Makefile:2472 Makefile:2491 | E:undef F:undef B:undef S:undef | 1 | per unit; not game.cpp, r100 (old-port hooks) |
| `GANADO_ROUTINE_BYTES` | em10/em10.cpp | Ganado routine tests and writes (32 EM_RTN, 14 EM_RTN_SET in em10.cpp) use the named bytes r_no_0/1 instead of the GameCube big-endian word: without it every test reads r_no_3/2 and every write sets routine 0/0 (grab, catch, find-shout staggering) | 1 / 1/undef | Makefile:68 | F:undef | undef | em10 (needs RE4DC_GAME) |
| `ID_ALPHA_SAT` | game/id_sys.cpp | Screen ID colours convert to bytes with saturation as on the GameCube (#66 bug 6: title logo and fades wrapped) | 1 / 1 | effects30.mk:382 | not built | not built | id_sys (screen IDs) |
| `ROUTE_CH22` | include/obj13.h include/pl14.h game/snd.cpp game/stage.cpp +5 | In pl14.h / obj13.h: Luis's and the ladder's asm-label calls forwarded to cEm members off the GameCube (ABI); elsewhere chapter 2-2 adapters and gating | 1/undef / 1/undef | Makefile:697 Makefile:698 | F:undef | not built | pl14, obj13.h users only (rest: route gating, b) |
| `ROUTE_CH23` | em35/em35.cpp em3b/em3b.cpp game/snd.cpp game/stage.cpp +4 | In em35 / em3b: placement construct keeps the archive cEmMgr::construct set (value-init fix, needs RE4DC_GAME); elsewhere chapter 2-3 module linking, BGM substitution and disc gating | 1 / 1 | Makefile:766 Makefile:769 | not built | not built | em35, em3b only (rest: route gating, b) |
| `SAVE_ROW_FIX` | game/card.cpp | Save screen's written row reads the key count's low byte in Dreamcast order (#66 bug 4): new count and time shown at once | 1 / 1 | vmusave.mk:31 | not built | not built | card.cpp (saves) |
| `SS_MSG_FIELDS` | Sscrn/ss_pzzl.cpp | Inventory reads the message completion/answer through typed fields: GCC puts the vtable pointer first, the GameCube offsets 0xFC / 0x1D1 read the wrong bytes | 1 / 1 | subscreen.mk:60 | not built | not built | ss_pzzl (inventory) |
| `STAT_ROUTINE_BYTES` | game/player.cpp | Every other cModel::stat GameCube word (STAT_BE: player, partner, HUD, dog, El Gigante, Luis, boat, bell, gatling, bosses) byte-swapped; the only src site is the STATDIAG log in player.cpp | 1 / 1 | Makefile:2482 | E:undef F:undef B:undef S:undef | 1 | engine: e1_prelude.h STAT_BE always swaps |
| `SUB_EM_FUNC` | game/pl_sub.cpp | SetSubDamage stores Ashley's routine-4 handler explicitly: the PowerPC r4 pin is gone off PowerPC, so the handler was an uninitialised local (reboot when the r200 truck hits Ashley; any SetSubDamage on her) | 1 / 1 | Makefile:734 | E:undef F:undef B:undef S:undef | undef | pl_sub |

### Game settings: the owner's product choices (game/game_settings.mk) (21)

| Conditional | Units | What it changes | Release D1 / D2 | Release set at | Engine before (E F B S) | Reference before | Owner / scope |
|---|---|---|---|---|---|---|---|
| `ALIVE_CAP` | game/em_set.cpp game/sce_com.cpp game/sce_sys.cpp | Owner rule: at most 4 Ganados (and Novistadors) alive; extra sends held, not dropped | 4 / 4 | Makefile:500 | F:4 B:undef | undef | em_set, sce_com, sce_sys |
| `ALIVE_CAP_DEFER_FLAGS` | game/em_set.cpp st/em_wrap.cpp | setFlag commands on a held handle are kept and applied after its first AI init | undef / 1 | Makefile:431 Makefile:432 | F:undef B:undef | undef | em_set, em_wrap (Disc 2) |
| `ALIVE_CAP_DEFER_GOTO_R207` | game/em_set.cpp st/em_wrap.cpp st2/r207.cpp | r207 queued movement of held sends | undef / 1 | Makefile:451 Makefile:452 | F:undef B:undef | undef | em_set, em_wrap, r207 (Disc 2) |
| `ALIVE_CAP_N` | game/em_set.cpp | The cap value (4) | 4 / 4 | Makefile:501 | F:4 B:undef | undef | em_set |
| `ALIVE_CAP_NOVIS` | game/em_set.cpp st2/r205.cpp st2/r213.cpp st2/r21d.cpp | Novistadors share the cap of 4 with Ganados (owner 10-18) | undef / 1 | Makefile:503 | F:undef B:undef | undef | em_set, r205 r213 r21d (Disc 2) |
| `ALIVE_CAP_ON` | include/em_far_delete.h include/em_wrap.h st/em_wrap.cpp st2/r204.cpp +3 | Room code sees held handles (isActive / getPtr skip a held send; far delete counts held Ganados as the PS2 does) | 1 / 1/undef | Makefile:510 | F:1/undef | not built | em_wrap, em_far_delete.h, st2/st3 rooms |
| `ALIVE_CAP_PARK` | game/em_set.cpp | Over the cap anyway: the farthest off-screen unhurt Ganado is parked (destroyed and re-queued, still counted) | 1 / 1 | Makefile:506 | F:1 B:undef | undef | em_set |
| `ALIVE_CAP_R101` | game/em_set.cpp | The generic hold stands aside in r101, whose own R101_ALIVE_CAP runs | 1 / 1 | Makefile:500 | F:1 B:undef | undef | em_set |
| `ALIVE_CAP_R202_GATE` | game/em_set.cpp | r202 at cap 4: operator 2E (the rock for the camera event) admitted before operator 21 | undef / 1 | Makefile:485 | F:undef B:undef | undef | em_set (Disc 2) |
| `ANIMALS_OFF` | game/em_set.cpp | Stage 1 ambient cows, chickens and the set-0 farm dog not spawned; scripted dogs stay (release rule with PS2_ENEMY_RULES) | 1 / 1 | Makefile:367 | F:1 B:undef | undef | em_set |
| `PS2_CH2_ENEMY` | game/stage.cpp | Chapter 2 PS2 spawn lists and room code as one unit, cap on top | 1 / 1 | Makefile:283 | not built | not built | stage (needs the PS2 list data: engine data provider) |
| `PS2_CH3_ENEMY` | game/em_set.cpp game/stage.cpp | Chapter 3 PS2 spawn lists and room code, cap on top (hold only in castle rooms) | undef / 1 | Makefile:308 Makefile:309 | F:undef B:undef | undef | stage, em_set (Disc 2; needs PS2 list data) |
| `PS2_CH4_ENEMY` | game/em_set.cpp game/stage.cpp | Chapter 4 PS2 spawn lists and room code, cap on top | undef / 1 | Makefile:337 Makefile:338 | F:undef B:undef | undef | stage, em_set (Disc 2; needs PS2 list data) |
| `PS2_ENEMY_CASTLE` | st2/r208.cpp st2/r20b.cpp st2/r216.cpp st2/r223.cpp +2 | Castle room-code PS2 spawn differences (bit per room) | undef / 0xe7 | Makefile:539 | not built | not built | r208 r20b r216 r223 r226 r227 (Disc 2) |
| `PS2_ENEMY_ROOMS` | game/stage.cpp st1/r100.cpp st1/r101.cpp st1/r104.cpp +6 | Per-room bits of the PS2 enemy-spawn room code (r100/r104 list rows, r101 square trio from PS2 area 15, r118 0x7D, r11a held rows, r11c cabin, r11d sisters) | 0x3ff / 0x3ff | Makefile:398 Makefile:399 | F:0x33f | not built | stage, r100 r101 r104 r108 r118 r11a r11b ... |
| `PS2_ENEMY_RULES` | include/obj13.h game/stage.cpp st1/r101.cpp st1/r107.cpp +7 | PS2 USA enemy rules of the chapter 1 rooms: list start-alive bits (stage.cpp), r101 reset waves below 5 alive and two held villagers, r107 holds (CHANGES GAMEPLAY by design) | 1 / 1 | Makefile:309 Makefile:338 | F:1 | not built | stage, r101 r107 r10f r111 r113 r11c ..., obj13.h |
| `QUICK_WEAPON` | game/sscrn.cpp | X + D-pad picks a weapon by kind (2023 remake style) through the case equip path | 1 / 1 | quickweapon.mk:16 quickweapon.mk:17 | not built | not built | owner 2026-11-21 "i want to keep quiock weapon switch" (not in the GameCube game; sscrn.cpp not hosted yet) |
| `R101_ALIVE_CAP` | st1/r101.cpp | r101's own cap of 4: start-list extras held, room sends queued, released one at a time | 4 / 4 | Makefile:552 | F:4 | not built | r101 (in FIGHT=1) |
| `R101_CAP_N` | st1/r101.cpp | The r101 cap value (4) | 4 / 4 | Makefile:552 | F:4 | not built | r101 (in FIGHT=1) |
| `R101_CAP_WAVES` | st1/r101.cpp | The two reset waves go through the cap too | 1 / 1 | Makefile:584 | F:1 | not built | r101 (in FIGHT=1) |
| `ROUTE_CH21_FULL` | game/em_set.cpp st1/r10c.cpp | r10c's seven-Ganado ambush goes through the cap (held sends null-checked); also opens the 2-1 path on the old disc | 1 / 1 | Makefile:609 | F:undef B:undef | undef | em_set, r10c |

### Guards: tripwires against failures the old port had (counted, expected 0) (3)

| Conditional | Units | What it changes | Release D1 / D2 | Release set at | Engine before (E F B S) | Reference before | Owner / scope |
|---|---|---|---|---|---|---|---|
| `EM_READ_RETRY` | include/types.h game/em_set.cpp game/read.cpp st1/r10c.cpp | Room code skips the part of a spawn that returned 0 (EM_OK) and retries progress-critical ones (EM_MUST: bosses, the r11b boat) instead of dereferencing 0; read.cpp retry is the loader (c, eng-load1) | 1 / 1 | game30.mk:3734 | E:undef F:undef B:undef S:undef | undef | types.h (EM_OK / EM_MUST in r100 r10b r119 r11b r11c r204 r22c), em_set, read.cpp, r10c |
| `R10C_SPAWN_LIVE_GUARD` | st1/r10c.cpp | r10c's first-villager event treats a spawned-then-retired Ganado as missing instead of driving it | 1 / 1 | game30.mk:3748 | not built | not built | r10c |
| `R117_EFFECT_FAILURE_SAFE` | st1/r117.cpp | The church beam: a refused LightSet (NULL) no longer leaves the puzzle waiting forever | 1 / 1 | esppool.mk:52 | not built | not built | r117 (needs RE4DC_GAME) |

### Open: not set, waiting on a decision (3)

| Conditional | Units | What it changes | Release D1 / D2 | Release set at | Engine before (E F B S) | Reference before | Owner / scope |
|---|---|---|---|---|---|---|---|
| `LIGHT_CUT_HOLD` | game/cam_ctrl.cpp | Leaving every camera area of r11f keeps the last area's light cut, not cut 0 (the outdoor cut lit the barn in Mendez phase 2); render only | 1 / 1 | mendezfx.mk:36 | E:undef F:undef B:undef S:undef | undef | cam_ctrl (hosted); settle: still pair at r11f front loft, engine renderer vs GameCube capture |
| `LIGHT_CUT_HOLD_ROOMS` | game/cam_ctrl.cpp | Rooms list (0x11f) | 0x11f / 0x11f | mendezfx.mk:36 | E:undef F:undef B:undef S:undef | undef | with LIGHT_CUT_HOLD |
| `SS_MENU_ANIM_RT` | Sscrn/ss_pzzl.cpp | Inventory command-menu flash steps per elapsed tick, not per drawn frame | 1 / 1 | subscreen.mk:154 | not built | not built | settle: does the engine run the sub screen below 30 Hz on console |

### Belongs to an engine service (the service must do the same; not built from these conditionals) (42)

| Conditional | Units | What it changes | Release D1 / D2 | Release set at | Engine before (E F B S) | Reference before | Owner / scope |
|---|---|---|---|---|---|---|---|
| `CLOTH_LIGHT_ABI_FIX` | game/cloth.cpp | SH-4 caller passes the Vec address commonClothLightSet expects (cloth drawing) | 1 / 1 | game30.mk:4184 | not built | not built | cloth service (native, eng-e1d) |
| `CRASH_SCREEN` | game/scheduler.cpp | Fault / HALT / 30 s stall draws a report into the frame buffer | 1 / 1 | Makefile:1776 | not built | not built | platform (crash screen) |
| `CRASH_TASK_DETAIL` | game/scheduler.cpp | Crash screen shows the waited-on task thread | 1 / 1 | Makefile:1776 | not built | not built | platform (crash screen) |
| `DISC_READ_FALLBACK` | game/snd.cpp | Stream reads checked; on failure the session latches onto plain bounded sector reads (#28) | 3 / 3 | Makefile:2099 Makefile:2102 | not built | not built | disc service (eng-load1) |
| `DISC_SET` | game/dvd.cpp game/game.cpp | Three-disc release: the disc is chosen by chapters finished; wrong disc holds on "insert disc N" | 1 / 1 | Makefile:1299 Makefile:1300 | F:undef B:undef | not built | disc service (eng-load1) |
| `DVD_BUFF_BYTES` | game/dvd.cpp | Read staging buffer size (the GameCube fixed 128 KB area) | 64*1024 / 64*1024 | Makefile:3095 Makefile:3096 | not built | not built | disc service (eng-load1) |
| `EFFECT_ADMISSION_GUARD` | game/eff_sys.cpp | Effect admission failure path guarded (eff_sys) | 1 / 1 | Makefile:1136 | not built | not built | effects service |
| `EFFECT_CONTROLLER_VALIDATE_FIRST` | game/espgen10.cpp | Effect controller inputs validated before native record reads | 1 / 1 | game30.mk:4174 | not built | not built | effects service |
| `EM27_SLOT_FIX` | em27/em27.cpp | em27 fish scans slots through workAt: a raw slot of the sparse backing read 0xFF filler as a NaN position (r10b dock); harmless on a full array | 1 / 1 | Makefile:588 | not built | not built | model / pool service (svc4) |
| `EM_ADMISSION_DISP_FIX` | game/read.cpp | readEm with no free module slot restores the caller display flags | 1 / 1 | Makefile:103 | not built | undef | loader (eng-load1) |
| `ESP_POOL_RECYCLE` | game/esp.cpp | Full effect pool retires a low-priority effect instead of failing | 1 / 1 | esppool.mk:49 | not built | not built | effects service |
| `EVD_ADMISSION_TXN` | game/event.cpp | Event data admission is transactional (rollback on a failed bin) | 1 / 1 | Makefile:1002 | not built | not built | loader (eng-load1) |
| `EVD_DEBUG_READ_CLEANUP` | game/event.cpp | Event admission failure frees a fresh debug-file allocation | 1 / 1 | Makefile:1042 | not built | not built | loader (eng-load1) |
| `EVD_EXEC_FAILURE_CLEANUP` | game/event.cpp | Event em0 read/start failure returns failure and releases only its own input | 1 / 1 | Makefile:1055 | not built | not built | loader (eng-load1) |
| `EVD_MODULE_VALIDATE_FIRST` | game/event.cpp | Event module exchange validated before its effects are released | 1 / 1 | Makefile:1097 | not built | not built | loader (eng-load1) |
| `EVD_MOVIE_NO_READ` | st1/r100.cpp st1/r101.cpp | With a route event's PS2 movie on the disc, r100 / r101 no longer preload its GC evd (GC asset purge) | 1 / 1 | Makefile:93 | F:undef | not built | movie player / loader (eng-load1) |
| `EVD_READ_ADMISSION_PREFLIGHT` | game/event.cpp | Impossible event table admission refused before taking a descriptor | 1 / 1 | Makefile:1088 | not built | not built | loader (eng-load1) |
| `EVD_READ_RELEASE_REFS` | game/event.cpp | EvtFree drops one registration of a multiply referenced read row | 1 / 1 | Makefile:1078 | not built | not built | loader (eng-load1) |
| `EVD_START_CLEANUP` | game/event.cpp | Failed event init abandoned locally; effect-model view published after validation | 1 / 1 | Makefile:1015 | not built | not built | loader (eng-load1) |
| `EVD_START_ROLLBACK` | game/event.cpp | Failed event start undoes its new admission | 1 / 1 | Makefile:1030 | not built | not built | loader (eng-load1) |
| `EVENT_FILES` | game/datactrl.cpp | Immutable event file backing (datactrl) | 1 / 1 | Makefile:2499 | not built | not built | loader (eng-load1) |
| `LOAD_INDICATOR` | game/game.cpp game/main.cpp game/read.cpp | The PS2 "Loading..." indicator during room loads | 1 / 1 | game30.mk:665 | F:undef B:undef | undef | loader UI (eng-load1) |
| `PAD_PROMPTS` | Sscrn/ss_file.cpp | Dreamcast button prompts in the manual / file screens | 1 / 1 | game30.mk:1160 game30.mk:1161 | not built | not built | input service |
| `PAD_PROMPT_MANUAL_ART` | Sscrn/ss_file.cpp game/main_sub.cpp | Dreamcast manual page art for the prompts | 1 / 1 | game30.mk:1163 game30.mk:1164 | not built | not built | input service |
| `PS2_AREA_HIDE` | st1/r107.cpp | r107 per-area scenery hiding of the PS2 room code (render only, read only) | 1 / 1 | game30.mk:3392 game30.mk:3393 | not built | not built | world bake / renderer |
| `PS2_ETS_LIGHT` | game/EtcModel.cpp game/light.cpp | Room lights of dropped etc parents follow the PS2 | 1 / 1 | game30.mk:4210 | not built | not built | room bake / renderer |
| `PS2_ETS_MATCH` | game/EtcModel.cpp | Etc-list entries the PS2 room data dropped are skipped (render + room objects) | 2 / 2 | game30.mk:4196 | not built | not built | room bake |
| `PS2_FIRE_SST` | game/EtcModel.cpp game/eff_sys.cpp | PS2 torch fire sets for dropped etc torches | 1 / 1 | game30.mk:4218 | not built | not built | effects service |
| `RADIO_SUB_RT` | Sscrn/ss_term.cpp | Codec subtitles follow the voice stream's clock, not drawn frames | 1 / 1 | subscreen.mk:172 subscreen.mk:178 | not built | not built | sound (eng-snd1) + codec screen |
| `RELEASE_FLAGS` | game/debug.cpp | The debug-disc boot turns its on-screen debug displays off | 1 / 1 | frontend30.mk:77 | not built | not built | boot config |
| `RESET_HEAP_FIX` | game/read.cpp | Soft reset (#26): no free into destroyed heaps; module archives in a destroyed heap forgotten | 1 / 1 | game30.mk:3726 | not built | undef | memory / loader (eng-load1) |
| `RESET_MEM_FIX` | game/main.cpp | Soft reset puts port state back to fresh-boot values | 1 / 1 | game30.mk:3774 | not built | not built | memory / loader (eng-load1) |
| `RESET_RETIRE_BEFORE_HEAPS` | game/main.cpp | Native reset borrowers retired before their source heaps die | 1 / 1 | game30.mk:37 | not built | not built | memory / loader (eng-load1) |
| `ROUTE_MOVIES` | game/game.cpp st1/r100.cpp st1/r101.cpp st1/r102.cpp +31 | PS2 movies present the route events (r100 s03 s20 s30 s40 s41 s43 s44, r101 s00 s21 s30, r102 s00, r104 r105 r106 r10b ...); off: the GameCube real-time events with their GC evd files (GC-ASSET rule) | 1/undef / 1/undef | Makefile:2435 | F:undef B:undef | not built | movie player (no lane yet) + hosted room call sites |
| `ROUTE_MOVIES_CH3` | st2/r201.cpp st2/r203.cpp st2/r204.cpp st2/r206.cpp +2 | Chapter 3 castle events as PS2 movies | undef / 1 | Makefile:2309 | not built | not built | movie player (Disc 2 rooms) |
| `ROUTE_MOVIES_CH4` | st2/r212.cpp st2/r214.cpp st2/r215.cpp st2/r227.cpp +1 | Chapter 4 castle events as PS2 movies | - / 1 | Makefile:2323 | not built | not built | movie player (Disc 2 rooms) |
| `SND_WALL_ALT` | game/snd.cpp | Positional SE wall test (sndSurroundCalc) through an alternative line query; audio only | 1 / 1 | game30.mk:2507 | not built | not built | sound (eng-snd1) |
| `SS_ACTOR_LIFETIME` | Sscrn/ss_pzzl.cpp game/cockpit.cpp game/pl_npc.cpp | Actor inputs preserved while the inventory backing owns their memory (pl_npc, cockpit, ss_pzzl) | 1 / 1 | subscreen.mk:72 | E:undef S:undef | undef | sub screen backing (no lane yet) |
| `SUBSCREEN` | game/cDataSwap.cpp game/sscrn.cpp | Dreamcast storage for the ARAM-swapped sub screen area | 1 / 1 | subscreen.mk:226 | not built | not built | sub screen backing (no lane yet) |
| `TITLE_START_OK` | game/title.cpp | Title menu takes START as well as A (#66: Dreamcast players pressed START twice) | 1 / 1 | effects30.mk:415 | not built | not built | input service |
| `VMU_CONTEXT` | Sscrn/ss_term.cpp game/main.cpp game/pl_sub.cpp game/sscrn.cpp +2 | VMU screen shows context (partner, codec) - hooks in pl_sub, pl11, pl14, ss_term, sscrn | 1 / 1 | vmu_context.mk:8 | E:undef F:undef B:undef S:undef | undef | VMU service (no lane yet) |
| `VMU_DIALOG` | game/card.cpp | Dreamcast VMU save dialogs (card.cpp) | 1 / 1 | demo_candidate.mk:50 demo_candidate.mk:51 | not built | not built | saves service (no lane yet) |

### Not needed: the old drawing path, its memory limits, its speed work and approximations (200)

| Conditional | Units | Release D1 / D2 | Engine before (E F B S) | Reference before | Why not needed | What it changes |
|---|---|---|---|---|---|---|
| `ACTOR_PL08_PACK` | game/main.cpp game/read.cpp | 1 / 1 | not built | undef | old drawing data | Leon pl08 immutable chunks read from a pack into one heap-4 cell |
| `ACTOR_TRANSACTION` | include/model.h game/main_mem.cpp game/model.cpp +1 | 1 / 1 | E:undef F:undef B:undef S:undef | 0 | old drawing path | Actor drawing transactions (model.h) |
| `ACT_CAP_TABLE` | game/em.cpp | 1 / 1 | not built | undef | old activation cap (r101 only, 5 active a tick) | Per-room activation cap from act_cap.cpp: r101 runs at most 5 Ganados a tick (parks the rest); inert under the alive cap of 4 |
| `ATCHK` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `ATCHK_CACHE` | include/atariInfo.h game/at_mod.cpp game/cam_ctrl.cpp +1 | 1 / 1 | E:undef F:undef B:undef S:undef | undef | speed (collision service) | Collision candidate cache; wraps AtariInfo fields (AT_FLAG16 / AT_RADIUS) |
| `ATCHK_LIST` | include/cManager.h game/at_mod.cpp game/esp_efm.cpp +1 | 1 / 1 | E:undef F:undef B:undef S:undef | undef | speed (collision service) | Alive lists kept as arrays (cManager.h generation bump) |
| `ATLIST_512` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `ATLIST_OVERFLOW` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `ATRECT_FAR` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `BODY_CORPSE` | game/em.cpp | 1 / 1 | not built | undef | approximation | Settled corpses skip their frame step |
| `BODY_CORPSE_TICKS` | game/em.cpp | 90 / 90 | not built | undef | approximation | BODY_CORPSE settle time |
| `BODY_ROUTE` | em10/em10.cpp | 1 / 1/undef | F:undef | undef | approximation | Far Ganados refresh route queries every 16th tick instead of 8th |
| `BODY_ROUTE_FAR` | em10/em10.cpp | 12000 / 12000/undef | F:undef | undef | approximation | BODY_ROUTE distance |
| `CBM_BITS` | game/at_mod.cpp | 4 / 4 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `CHAPTER_END_HOLD` | game/sce_com.cpp | 1 / 1 | F:undef | not built | old native world | Chapter-end save keeps the native world room (#66 blue screen) |
| `CLOTH_NATIVE` | include/cloth.h game/cloth.cpp game/trans.cpp | 1/undef / 1/undef | F:undef B:undef | not built | old drawing / effects path (engine renderer, effects service) |  |
| `CLOTH_SPRING` | include/cloth.h game/cloth.cpp | 1/undef / 1/undef | F:undef B:undef | not built | old drawing / effects path (engine renderer, effects service) |  |
| `COARSE` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `COARSE_FX_SPRITES` | game/esp.cpp game/esp_sub.cpp game/trans.cpp | 2 / 2 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `COARSE_SCENERY_FALLBACK` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `COARSE_SOURCE_ACTORS` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `COARSE_SOURCE_OBJECTS` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `COL_PREFETCH` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `COPY_LEAN` | game/eprintf.cpp game/main_mem.cpp | 1 / 1 | not built | not built | speed | Allocation tag string without vfprintf |
| `CROWD_INVIS_SKIP` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) | re4dc_actor_crowd_note (and the =2 peek): a skipped source-path Ganado keeps its CROWD_LOD crowd entry; |
| `CUBE_MEMO` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `D349_RENDERER_STACK` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `DOOR_FREEZE` | game/filter09.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `DVD_BORROW` | game/dvd.cpp game/game.cpp | 1 / 1 | F:undef B:undef | not built | old heap 4 | Load-time staging buffer borrowed from heap 4 |
| `DVD_BORROW_BYTES` | game/dvd.cpp | 128*1024U / 128*1024U | not built | not built | old heap 4 (DVD_BORROW size) | Borrowed staging size |
| `DVD_BORROW_SPARE` | game/dvd.cpp | 512*1024U / 512*1024U | not built | not built | old heap 4 (DVD_BORROW margin) | Free heap kept while borrowing |
| `EFFECT_FADE_CLAMP` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_HAZE_LEAN` | game/esp_sub.cpp | 3 / 3 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_LEAN` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_MASK12` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_PS2_HAZE` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_PS2_STREAK` | game/esp_sub.cpp | 2 / 2 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_PS2_TOGGLE` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) | re4dc_look_set sets each preset's effect look (re4dc_ps2fx_set): native_static.o needs the toggle define too. |
| `EFFECT_ROOM` | game/esp_sub.cpp | 7 / 7 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_SPRITES` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_TORCH` | game/esp0e.cpp game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFFECT_UV12` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EFM_PS2_CUT` | game/eff_sys.cpp game/trans.cpp | 1 / 2 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EM10_IDFIRST` | em10/em10.cpp | 1 / 1 | F:undef | undef | speed, exact | em10 nearby-damage scan tests the id range first |
| `EMHIT_LIST` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `ESP1B_GRID03` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP47_SKIP_LEAN` | game/esp47.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP_CUT_EARLY` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP_ESSENTIAL_EARLY` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP_OWNER` | include/esp.h game/esp.cpp game/est.cpp | 1 / 1 | E:undef F:undef B:undef S:undef | undef | effects speed | Effect owner index |
| `ESP_POOL_ROOM_CAP` | game/esp.cpp | undef / 320 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP_POOL_ROOM_CAP_LIST` | game/esp.cpp | undef / 0x202 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP_SETUP_LEAN` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP_SPRITE_FAST` | game/esp.cpp game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ESP_TYPE_CAP` | game/esp.cpp | 16 / 16 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `EVENT_MANAGER_STORAGE_FLAGS` | include/cManager.h game/event.cpp | 1 / 1 | E:undef F:undef B:undef S:undef | undef | old demand-backed pools | Event manager flag bytes read only from allocated pool storage (cManager.h) |
| `FAR_SHELL` | game/main_mem.cpp | 1 / 1 | not built | not built | old drawing path | Far shell beyond the view-distance cut |
| `FLASHLIGHT_POOL` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FLASHLIGHT_POOL_DIST` | game/trans.cpp | 3500 / 3500 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FLASHLIGHT_POOL_GAIN` | game/trans.cpp | 150 / 150 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FLASHLIGHT_POOL_SIZE` | game/trans.cpp | 1800 / 1800 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FRONT_LEAN` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FRONT_NATIVE` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_ESP_WORDS` | include/esp.h game/esp.cpp | 32 / 32 | E:undef F:undef B:undef S:undef | undef | effects speed | Effect bitmap words |
| `FX_ESSENTIAL_BOOT` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_HAZE_ROOM_INDEX` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_INSIGNIA_KEEP` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_LEAN` | game/foot_shadow.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_MIST_PS2` | game/esp48.cpp game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_MOVE` | include/esp.h game/esp15.cpp game/esp48.cpp +1 | 1 / 1 | E:undef F:undef B:undef S:undef | undef | effects speed | Effect move fast path |
| `FX_POP_RATE` | game/esp_sub.cpp | 2 / 2 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_SCAN` | include/esp.h game/esp.cpp game/esp_efm.cpp +2 | 1 / 1 | E:undef F:undef B:undef S:undef | undef | effects speed | Effect slot scan by bitmap |
| `FX_STRIP21` | game/esp.cpp game/esp01.cpp game/esp02.cpp +1 | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `FX_TRIM` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `GC_CENSUS_TRIM` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `HAZE_SPRITE_CUT` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `HERMITE_FAST` | game/motion.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `HF_INLINE` | game/motion.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `HF_PF` | game/motion.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `HF_REG` | game/motion.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `HW_FOG_HAZE` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `ID_LISTS` | game/id_sys.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LAKE_NIGHT_FX` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LAKE_RIPPLES` | game/espgen45.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LEON_CLOTH_DRAWN` | game/pendulum.cpp game/pl_cloth.cpp | 1 / 1 | not built | undef | approximation (cloth service) | Leon's cloth simulated only while drawn |
| `LEON_FACE_LAZY` | game/mirror.cpp game/shadow.cpp game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LEON_HAND_PACK` | game/read.cpp | 1 / 1 | not built | undef | old drawing data | Leon's PS2 hand poses from a pack |
| `LEON_NO_GC_FRONT` | game/trans.cpp | 2 / 2 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LIGHT_LAZY` | game/light.cpp game/lightInfo.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LIGHT_SET_REUSE` | game/light.cpp | 2 / 2 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LINE_LEAF` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `LINE_LEAF2` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `LINE_PIECE` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `LINE_TAIL` | game/at_sub.cpp game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `LINE_WALK` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `LINE_WALK_PF` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `LINE_YROW` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `LOGIC_APPROX_MASK` | game/atari.cpp | 0x01 / 0x01 | not built | undef | approximation (collision service) | Approximate collision memos (NOT exact) |
| `LOGIC_LOD_EM` | game/em.cpp | 2 / 2 | not built | undef | approximation | Far / off-screen Ganados run their frame step every 2nd tick (release plays approximately) |
| `LOGIC_LOD_FAR` | game/em.cpp | 12000 / 12000 | not built | undef | approximation | LOGIC_LOD_EM far distance |
| `LOGIC_LOD_NEAR` | game/em.cpp | 5000 / 5000 | not built | undef | approximation | LOGIC_LOD_EM near distance |
| `LOGIC_WASTE` | game/atari.cpp game/atariInfo.cpp game/cam_ctrl.cpp +4 | 1 / 1 | E:undef F:undef B:undef S:undef | undef | speed, exact memos | Logic-waste census memos (collision, camera obstruction, cloth) |
| `LOGIC_WASTE_MASK` | game/atari.cpp | 0x02 / 0x02 | not built | undef | speed | LOGIC_WASTE data word |
| `LOOK_TOGGLE` | game/filter00.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `LQ_MEMO` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `MOTION_CAPACITY` | game/main_mem.cpp lib/OSAlloc.c | 1 / 1 | not built | not built | old heap 4 | Reclaimable motion overflow |
| `MOVIE_WORLD_ARENA` | game/main_mem.cpp | 1 / 1 | not built | not built | old memory map | r11f movies borrow the retained world cell |
| `NATIVE_ACTOR_SKIN` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `NATIVE_ACTOR_SKIN_LAZY` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `NATIVE_DRAW_OUTCOMES` | game/cloth.cpp game/esp_sub.cpp game/espgen45.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `NATIVE_LASER` | game/esp.cpp game/esp19.cpp game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `NATIVE_MES` | game/mes.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `NATIVE_MODEL_REGISTRY` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) | The entry gate: trans.cpp's re4dc_actor_transaction_candidate (platform/include/source_actor_owner_hooks.inc) also nominates registry ids, so their OT... |
| `NATIVE_STATIC` | game/scroll.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `NMR_NO_GC_FRONT` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `OBJHIT_IDFIRST` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `OBJHIT_LIST` | game/at_mod.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `OB_MAT` | game/id_sys.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `OB_NEAR` | game/route_ck.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `OB_PATH` | game/id_sys.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `OB_SCAN` | game/dmg.cpp game/em_set.cpp game/id_sys.cpp | 1 / 1 | F:undef B:undef | undef | speed, exact | Live-enemy scans walk the alive list |
| `OT_MASK` | include/trans_ot.h game/trans_ot.cpp | 1 / 1 | E:undef F:undef B:undef S:undef | undef | old drawing path | Used-OT bitmask |
| `PACE_CATCHUP` | game/main.cpp game/main_sub.cpp game/trans.cpp | 2 / 2 | not built | not built | old frame pacing | Render skip with catch-up (dropped images run logic only) |
| `PACE_TRANS_SKIP` | game/esp.cpp game/espgen.cpp game/main.cpp +1 | 4063 / 4063 | not built | not built | old frame pacing | Presentation stages a dropped image skips |
| `PARTS_LINKED_FLAG` | game/model.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `PAUSE_NATIVE_PRESENTATION` | game/game.cpp | 1 / 1 | F:undef B:undef | not built | old renderer | OPTIONS over a live room keeps the native view |
| `PEN_CLOTH_LOD` | game/pendulum.cpp | 2 / 2 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PEN_CLOTH_LOD_FAR` | game/pendulum.cpp | 15000 / 15000 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PMC_KERNEL` | game/math_sub.cpp game/model.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `POST_F00` | game/filter00.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PRIMITIVE_BUFFERS` | game/game.cpp game/trans.cpp | 1 / 1 | F:undef B:undef | not built | old drawing path | Primitive buffer count |
| `PRIM_BUF_KB` | Sscrn/ss_item_draw.cpp game/game.cpp | 432/undef / 432/undef | F:undef B:undef | not built | old drawing path | Primitive buffer size cap |
| `PRIM_CAP_R107` | game/game.cpp | 327680 / 327680 | F:undef B:undef | not built | old heap 4 | r107 primitive buffer cap |
| `PRIM_CAP_R10B` | game/game.cpp | 327680 / 327680 | F:undef B:undef | not built | old heap 4 | r10b primitive buffer cap |
| `PRIM_CAP_R226` | game/game.cpp | undef / 327680 | F:undef B:undef | not built | old heap 4 | r226 primitive buffer cap |
| `PROP_GATE` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2FX_DRAW` | game/esp_sub.cpp | / RE4DC_EFFECT_PS2_STR / / RE4DC_EFFECT_PS2_STR | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_FIRE_HALO_CUT` | game/eff_sys.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_FX_ADDITIONS` | game/esp_sub.cpp game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_FX_POPULATION` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_FX_ROOMS` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_FX_ROOMS_EXT` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_FX_STAGE1` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_WORLD_DYNAMIC` | game/scroll.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_WORLD_PARTS` | game/scroll.cpp game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_WORLD_ROOT_POSE` | game/scroll.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `PS2_WORLD_SOURCE_OWNER` | game/main_mem.cpp game/scroll.cpp game/trans.cpp | 1 / 1 | not built | not built | old memory map (heap 4, arenas) |  |
| `PWC_DIAG` | game/model.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `PWC_KERNEL` | game/model.cpp | 3 / 3 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `QUALITY` | game/title.cpp | 1 / 1 | not built | not built | old renderer | Graphics quality picker at the first title menu |
| `R117_FX_FALLBACK` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `R117_FX_QUALIFIED_FALLBACK` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `RAIN_DC` | game/filter06.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `RAIN_DC_N` | game/filter06.cpp | 320 / 320 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `RAIN_PS2` | game/filter06.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `RENDER_OPTION` | game/option.cpp | 1 / 1 | not built | not built | old renderer | Quality / Standard / Fast resolution option rows |
| `ROOM_INDEX` | game/roomdata.cpp | 1 / 1 | not built | not built | speed, exact | Room record index memo (roomdata) |
| `ROTVEC_MEMO` | game/sub2.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `ROT_CACHE` | game/math_sub.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `ROUTE_CH13` | game/sce_at.cpp game/snd.cpp st1/r102.cpp +1 | 1/undef / 1/undef | F:undef | not built | route gating of the old discs | Chapter 1-3 modules, r102 s00 movie, BGM0-for-BGM1 substitution, "Coming Soon" door check |
| `ROUTE_CH21` | game/snd.cpp st1/r117.cpp st1/r119.cpp +1 | 1 / 1 | B:undef | not built | route gating of the old discs | Chapter 2-1 modules, overlays, movies and BGM substitution |
| `ROUTE_CH31` | game/snd.cpp | undef / 1 | not built | not built | route gating of the old discs | Chapter 3-1 modules and BGM substitution |
| `ROUTE_CH32` | game/snd.cpp | undef / 1 | not built | not built | route gating of the old discs | Chapter 3-2..3-4 modules and BGM substitution |
| `ROUTE_OVL` | game/game.cpp | 1 / 1 | F:undef B:undef | not built | old image layout | Boat and Del Lago as room overlays |
| `ROUTE_SOON_RETURN` | game/sce_at.cpp | 1 / 1 | F:undef | not built | route gating of the old discs | "Coming Soon" door cancels like a locked door |
| `RVM_BITS` | game/sub2.cpp | 8 / 8 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `SCEAT_LIST` | game/sce_at.cpp | 1 / 1 | F:undef | not built | speed, exact | Trigger-area walks skip filtered records |
| `SCENERY_GATE` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `SH4ZAM_RENDER` | include/dolphin/mtx.h include/vec.h | 1 / 1 | E:undef F:undef B:undef S:undef | undef | old drawing path | Render-only matrix call sites through SH4ZAM (RENDER_MTX*) |
| `SINCOS` | game/math_sub.cpp lib/mtx.c | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `SK1_ASM` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `SKEL_FTRV` | em10/em10.cpp game/model.cpp | 1 / 1 | F:undef | undef | speed (skeleton service) | Skeleton matrices with ftrv |
| `SKIN_PALETTE_LAZY` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `SPHERE_WALK` | game/atari.cpp | 1 / 1 | not built | undef | original service the engine replaces natively (speed / memory option) |  |
| `SS11_PRELOAD` | game/main_mem.cpp | 1 / 1 | not built | not built | old VRAM path | Room textures re-preloaded after the chapter screens |
| `SS_POOL_HIGH` | game/eff_sys.cpp game/esp.cpp game/espgen.cpp +1 | 1 / 1 | F:undef B:undef | not built | old heap 4 | Effect / light / primitive pools placed above the sub screen window |
| `SS_POOL_TOP` | game/main_mem.cpp | 1 / 1 | not built | not built | old heap 4 | SS_POOL_HIGH pools at the top of the highest free cell |
| `STATIC_OBJ_BAKE` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `TRANS_SS_GUARD` | game/trans.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `TRAP_FX` | game/esp_sub.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `UI_DRAW_LEAN` | game/mes.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `VEC_INLINE` | include/vec.h | 1 / 1 | E:undef F:undef B:undef S:undef | undef | speed | Small vector functions inline (vec.h) |
| `VEC_NORM_INLINE` | include/vec.h lib/mtx.c | 1/undef / 1/undef | E:undef F:undef B:undef S:undef | undef | speed | Vector normalise inline |
| `WATER42_GRID_SKIP` | game/Espgen42.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WATER45_GRID_SKIP` | game/Espgen42.cpp game/espgen45.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WATER45_LEAN` | game/espgen45.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) | r10b: espgen45 (the lake height field) keeps hA/hB/pos but skips its GX-only normal/bump/display-list buffers (1.36 MB of heap 4; |
| `WATER45_NATIVE` | game/esp_sub.cpp game/espgen.cpp game/espgen45.cpp +1 | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WATER_PS2` | game/Espgen42.cpp game/espgen.cpp game/espgen45.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WATER_PS2_EXT` | game/espgen45.cpp game/water_layer29.h game/water_layer29_package.h +1 | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WATER_PS2_EXT_ROOMS` | game/espgen45.cpp | 7 / 7 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WATER_PS2_FLIP` | game/espgen45.cpp | 8 / 8 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WATER_PS2_ROOMS` | game/espgen45.cpp | 0x3f / 0x3f | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WEAPON_HEAP4` | game/game.cpp game/pl_wep.cpp game/read.cpp +1 | 1 / 1 | E:undef F:undef B:undef S:undef | undef | old heap 4 | Weapon bodies in heap 4 |
| `WEAPON_HEAP4_TOP` | game/read.cpp | 1 / 1 | not built | undef | old heap 4 | Weapon body at the top of the highest free heap-4 cell |
| `WEAPON_HEAP4_WALK_GUARD` | game/read.cpp | 1 / 1 | not built | undef | old heap 4 | Heap-4 walk guard for weapon placement |
| `WEAPON_WEP04_OVL` | game/game.cpp game/read.cpp | 1 / 1 | F:undef B:undef | undef | old image layout | Blacktail as an overlay |
| `WORKAT_INLINE` | include/cManager.h game/em_set.cpp game/esp_efm.cpp | 1 / 1 | E:undef F:undef B:undef S:undef | undef | speed (old demand-backed pools) | Manager lookup inline |
| `WORLD_ROOM_MODULES` | game/quake.cpp | undef / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |
| `WORLD_STAGE_MODULES` | game/EtcModel.cpp | 1 / 1 | not built | not built | old drawing / effects path (engine renderer, effects service) | Existing export alias needed by r200, without enabling the unrelated world-test module set. |
| `WPAL_FAST` | game/trans.cpp | 3 / 3 | not built | not built | old drawing / effects path (engine renderer, effects service) |  |

### Not conditionals: hook macros, header guards, constants (the same text in every build, or answered by the image) (58)

| Macro | Kind | Units | Value in release | Engine (E F B S) | Reference |
|---|---|---|---|---|---|
| `ALIVE_BUMP` | hook | include/cManager.h game/at_mod.cpp | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `ATARI_TOUCH` | hook | include/atariInfo.h include/wep_mod.h em2b/em2b.cpp +10 | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `AT_FLAG16` | constant | include/atariInfo.h em39/em39.cpp | AtFlag16 / AtFlag16 | E:u16 F:u16 B:u16 S:u16 | u16 |
| `AT_RADIUS` | constant | include/atariInfo.h | AtRadius / AtRadius | E:f32 F:f32 B:f32 S:f32 | f32 |
| `BUS_CLOCK` | value | game/debug.cpp game/dvd.cpp game/main_sub.cpp | 162000000u / 162000000u | not built | not built |
| `C20_PREF_OBJ` | hook (old platform) | game/trans.cpp | <fn> / <fn> | not built | not built |
| `CHAPTER_HOLD` | hook | game/sce_com.cpp | <fn> / <fn> | F:<fn> | not built |
| `CLOTH_POOL_RETIRE11` | hook | game/esp.cpp | <fn> / <fn> | not built | not built |
| `CLOTH_SLOT_RETIRE11` | hook | game/esp.cpp | <fn> / <fn> | not built | not built |
| `CODEC_CANCEL` | hook | include/snd.h Sscrn/ss_term.cpp | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `CODEC_READY` | hook | include/snd.h Sscrn/ss_term.cpp | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `CODEC_REQUEST` | hook | include/snd.h Sscrn/ss_term.cpp | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `DOORPH` | hook (old platform) | game/game.cpp game/sce_at.cpp game/stage.cpp | <fn> / <fn> | F:<fn> B:<fn> | not built |
| `DOORSPIN` | hook (old platform) | game/main.cpp | <fn> / <fn> | not built | not built |
| `DT_SND` | constant | game/snd.cpp | def / def | not built | not built |
| `EFM_CLASS_BUMP` | hook | include/cManager.h | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `EVENT_FILE_FLAG` | value | game/datactrl.cpp game/event.cpp | 4 / 4 | not built | not built |
| `EVENT_IS_ALIVE` | hook | include/cManager.h game/event.cpp | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `GCA_BANK_BEGIN` | hook | game/dvd.cpp | <fn> / <fn> | not built | not built |
| `GCA_BANK_END` | hook | game/dvd.cpp | <fn> / <fn> | not built | not built |
| `GCA_BANK_PIECE` | hook | game/dvd.cpp | <fn> / <fn> | not built | not built |
| `GXF_GET_PROJECTION` | hook (old platform) | game/cloth.cpp game/esp_sub.cpp game/trans.cpp | re4dc_gxf_get_projecti / re4dc_gxf_get_projecti | not built | not built |
| `GXF_GET_VIEWPORT` | hook (old platform) | game/cloth.cpp game/esp_sub.cpp game/trans.cpp | re4dc_gxf_get_viewport / re4dc_gxf_get_viewport | not built | not built |
| `GXF_SET_PROJECTION` | hook (old platform) | game/camera.cpp | re4dc_gxf_set_projecti / re4dc_gxf_set_projecti | not built | GXSetProjection |
| `HALT_STORE` | hook | include/dbg_tool.h include/flag_rsf.h include/types.h +24 | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `HZ` | hook | game/esp_sub.cpp | <fn> / <fn> | not built | not built |
| `LC_PALETTE` | constant | game/trans.cpp | ((u32) re4dc_locked_ca / ((u32) re4dc_locked_ca | not built | not built |
| `LOGIC_TRACE` | option | game/main.cpp game/rnd.cpp | 1/undef / 1/undef | E:1 F:1 B:1 S:1 | undef |
| `MANAGER_FLAG_LOAD` | hook | include/cManager.h | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `MANAGER_FLAG_SET` | hook | include/cManager.h | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `MANAGER_FLAG_STORE` | hook | include/cManager.h | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `MANAGER_IS_ALIVE` | hook | include/cManager.h | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `MODEL_DIAG` | hook (old platform) | game/trans.cpp | <fn> / <fn> | not built | not built |
| `OWN_ALL` | constant | include/main_mem.h | 31u / 31u | E:31u F:31u B:31u S:31u | 31u |
| `OWN_EG` | constant | include/main_mem.h game/game.cpp | 16u / 16u | E:16u F:16u B:16u S:16u | 16u |
| `OWN_EM` | constant | include/main_mem.h game/game.cpp | 2u / 2u | E:2u F:2u B:2u S:2u | 2u |
| `OWN_EP` | constant | include/main_mem.h game/game.cpp | 8u / 8u | E:8u F:8u B:8u S:8u | 8u |
| `OWN_OB` | constant | include/main_mem.h game/game.cpp | 4u / 4u | E:4u F:4u B:4u S:4u | 4u |
| `OWN_PL` | constant | include/main_mem.h game/game.cpp | 1u / 1u | E:1u F:1u B:1u S:1u | 1u |
| `PFIRE_OWNER` | constant | game/eff_sys.cpp | 0x68 / 0x68 | not built | not built |
| `PS2_ENEMY_LIST` | hook | game/stage.cpp | <fn> / <fn> | not built | not built |
| `PS2_FX_POPULATION_H` | guard | game/ps2_fx_population.h | def / def | not built | not built |
| `PS2_ROOMS_LIST` | option | game/stage.cpp | RE4DC_PS2_ENEMY_ROOMS / RE4DC_PS2_ENEMY_ROOMS | not built | not built |
| `RENDER_MTXConcat` | hook (old platform) | include/dolphin/mtx.h include/vec.h game/esp_sub.cpp +1 | re4dc_zam_MTXConcat / re4dc_zam_MTXConcat | E:PSMTXConcat F:PSMTXConcat B:PSMTXConcat S:PSMTXConcat | PSMTXConcat |
| `RENDER_MTXInverse` | hook (old platform) | include/dolphin/mtx.h include/vec.h game/esp_sub.cpp +1 | re4dc_zam_MTXInverse / re4dc_zam_MTXInverse | E:PSMTXInverse F:PSMTXInverse B:PSMTXInverse S:PSMTXInverse | PSMTXInverse |
| `RENDER_MTXMultVec` | hook (old platform) | include/dolphin/mtx.h include/vec.h game/esp_sub.cpp | re4dc_zam_MTXMultVec / re4dc_zam_MTXMultVec | E:PSMTXMultVec F:PSMTXMultVec B:PSMTXMultVec S:PSMTXMultVec | PSMTXMultVec |
| `RENDER_MTXRotRad` | hook (old platform) | include/dolphin/mtx.h include/vec.h game/esp_sub.cpp | re4dc_zam_MTXRotRad / re4dc_zam_MTXRotRad | E:PSMTXRotRad F:PSMTXRotRad B:PSMTXRotRad S:PSMTXRotRad | PSMTXRotRad |
| `SKIN_PALETTE` | constant | game/trans.cpp | (g_skin_palette ? g_sk / (g_skin_palette ? g_sk | not built | not built |
| `SND_PAD_READ` | hook (old platform) | game/dvd.cpp | <fn> / <fn> | not built | not built |
| `SS_HOOK_PRESENT` | constant | game/trans.cpp | 1 / 1 | not built | not built |
| `SUBSCREEN_ACTOR_H` | guard | include/re4dc_subscreen_actor.h | def / def | not built | not built |
| `TAIL_VB` | hook (old platform) | game/main.cpp | <fn> / <fn> | not built | not built |
| `TRACE_OWNER_PUBLISH` | hook | include/main_mem.h game/game.cpp | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `TRACE_OWNER_RELEASE` | hook | include/main_mem.h game/game.cpp game/stage.cpp | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `WORLD_HEAP_CHANGED` | hook | game/main_mem.cpp | <fn> / <fn> | not built | not built |
| `XM_DIR` | hook | include/re4dc_xm.h game/cam_extra.cpp game/esp01.cpp +5 | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `XM_LOAD` | hook | include/re4dc_xm.h game/area.cpp game/at_mod.cpp +29 | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |
| `XM_POINT` | hook | include/re4dc_xm.h game/area.cpp game/at_mod.cpp +26 | <fn> / <fn> | E:<fn> F:<fn> B:<fn> S:<fn> | <fn> |

### Off in the release, or in no unit the release builds (157): no ruling needed

Each name: the units that test it. Engine or reference ON is marked; none of these is ON in the release.

`ACTOR_EARLY_COARSE` game/trans.cpp; `ACTOR_PRESENTATION32` game/trans.cpp; `ACTOR_SKIN_RESERVE` game/trans.cpp; `ACTOR_SWAP` game/trans.cpp; `ACTOR_TEX_PREP` game/trans.cpp; `ACTOR_TEX_PREP_DRAW` game/trans.cpp; `ACT_CAP` game/em.cpp; `ALIVE_CAP_LOG` game/em_set.cpp; `ANIM_SAMPLE_LEAN` game/motion.cpp; `ATCHK_DISTINCT29` include/atariInfo.h game/at_mod.cpp; `BENCH_CENSUS` game/esp.cpp; `BODY_GRID` em10/em10.cpp; `BODY_IK` em10/em10.cpp; `BODY_IK_FAR` em10/em10.cpp; `BODY_IK_NEAR` em10/em10.cpp; `BODY_LOG` game/em.cpp; `CABIN_SOURCE` game/datactrl.cpp game/dvd.cpp +6; `CLOTH_MATERIAL11` game/cloth.cpp game/esp.cpp +1; `CLOTH_PUBLICATION11` game/cloth.cpp; `CLOTH_SHEET11` game/cloth.cpp; `CLOTH_TILES11` game/cloth.cpp; `CLOTH_XM_BATCH14` include/re4dc_xm.h game/cloth.cpp; `CODEC_READY_FIXTURE` include/snd.h; `DBG_WARP` game/sce_com.cpp game/title.cpp +1; `DEAD_STACK_POISON` game/scheduler.cpp; `DEATH_TRACE` game/em_sub.cpp game/game.cpp +1; `DECISION_TRACE` game/at_mod.cpp game/at_sub.cpp +4; `DISC_PIO_FALLBACK` game/snd.cpp; `DIST_POSE_LOD` game/em.cpp game/motion.cpp; `DIST_POSE_LOD_FAR` game/em.cpp; `DRAW_FALLBACK_AUDIT` game/esp_sub.cpp game/main.cpp; `DRAW_SETUP_AUDIT` game/main.cpp game/trans.cpp; `EFFECT_BIND_DIAG` game/read.cpp; `EFFECT_HAZE_LEAN_TOGGLE` game/esp_sub.cpp; `EFFECT_OWNERS_ALL` game/esp_sub.cpp; `EFM_CLASS_IDENTITY` include/cManager.h game/esp_efm.cpp; `ELIG_TOOL12` game/esp_sub.cpp; `EL_CENSUS` game/atari.cpp game/em.cpp +2; `EM35_DIAG` em35/em35.cpp; `EM_READ_FAIL_INJECT` game/read.cpp; `EM_READ_FAIL_INJECT_ROOM` game/read.cpp; `ENCV` game/trans.cpp; `ENC_SKIP_GANADO` game/trans.cpp; `ENGINE_PREVIEW` em10/em10.cpp game/ik.cpp; `ENGINE_VIS_LOG` em10/em10.cpp; `ESP_CENSUS` game/esp.cpp game/esp_sub.cpp; `ESP_HIT_THIN` game/esp.cpp game/esp1a.cpp; `ESP_LOD` game/esp.cpp; `ESP_LOD_FAR` game/esp.cpp; `ESP_POOL_CAP` game/esp.cpp; `ESP_POOL_DIAG` game/esp.cpp; `ESP_POOL_ROOM_LIST` game/esp.cpp; `ESP_POOL_ROOM_MIN` game/esp.cpp; `ESP_SPIKE_LOG` game/game.cpp; `EVD_ARAM_ALLOC_RETRY` game/event.cpp; `EVD_FORWARD_RECEIPT` game/event.cpp; `EVENT_SWAP_RELOAD` game/datactrl.cpp game/dvd.cpp +1; `FALLBACK_AUDIT29` game/atari.cpp game/cloth.cpp +5; `FALLBACK_AUDIT35` game/at_mod.cpp game/cloth.cpp +4; `FRONTEND_TPL_OWNER34_H` game/frontend_tpl_owner34.h; `FRONT_TEXOBJ` game/trans.cpp; `FRONT_TPL_OWNER` game/frontend_tpl_owner34.h game/game.cpp +5; `FSCA_SINCOS` game/math_sub.cpp; `FSCA_TINY_BITS` game/math_sub.cpp; `FSCA_XMAX_BITS` game/math_sub.cpp; `FX_CORE_TEX_PREP` game/esp0a.cpp game/esp0e.cpp +1; `FX_EARLY_CUT` game/esp_sub.cpp; `FX_LEVEL` game/esp_sub.cpp; `FX_LEVEL_TOGGLE` game/esp_sub.cpp; `FX_TRIM_LOG` game/esp_sub.cpp; `GCOBJ_SKIP` game/trans.cpp; `GC_ASSET_GATE` Sscrn/ss_term.cpp game/block.cpp +4; `GUARD_FAIL_INJECT` game/eff_sys.cpp game/event.cpp; `GUARD_FAIL_INJECT_EVT` game/event.cpp; `GUARD_FAIL_INJECT_MASK` game/eff_sys.cpp game/event.cpp; `GUARD_FAIL_INJECT_ROOM` game/eff_sys.cpp game/event.cpp; `HEAP4_WATER` game/main_mem.cpp; `HEAP_CENSUS` game/main_mem.cpp; `HEAP_REPLACE_LOG` game/main_mem.cpp; `HF_ASM` game/motion.cpp; `IO_PROBE` game/dvd.cpp; `ISSUE52_ACTOR_DIAG` game/em.cpp game/em_set.cpp +2; `ITEMS_CENSUS` game/eff_sys.cpp game/item_model.cpp; `LAKE_FIX_TOGGLE` game/esp_sub.cpp game/filter06.cpp; `LIGHT_CUT_LOG` game/cam_ctrl.cpp game/light.cpp; `LINE_RESUME` game/atari.cpp; `LINE_RESUME29_H` game/line_resume29.h; `LOGIC_TRACE_OWNERSHIP` include/main_mem.h; `M1_LOGIC_CAPTURE` game/esp.cpp game/main.cpp +1; `MCHECK_LEONGC` game/trans.cpp; `MIST_CUT` game/esp_sub.cpp; `MODEL_WALK_CHECK` game/main.cpp game/scheduler.cpp +1; `MOVIE_CANCEL_CLIP` st1/r11f.cpp; `MOVIE_EOF` game/game.cpp st1/r11f.cpp; `MOVIE_SKIP` game/game.cpp st1/r10b.cpp +1; `MOVIE_UNHANDLED` st1/r100.cpp st1/r101.cpp +9; `OSFREE_CHECK` game/main_mem.cpp lib/OSAlloc.c; `OTHER_PROFILE` game/main.cpp game/trans.cpp; `OTHER_UNIT` game/main.cpp game/trans.cpp; `OT_PROF` game/trans_ot.cpp; `OT_WALK_CHECK` game/shape.cpp game/trans.cpp +1; `PACE_CHECK` game/trans.cpp; `PARTS_PTR_MEMO` game/model.cpp; `PEN_CLOTH_CENSUS` game/pendulum.cpp; `PRIM_CAP_R202` game/game.cpp; `PRIM_CAP_R320` game/game.cpp; `PRIM_MIN_ST3` game/game.cpp; `PRIM_WATER` game/trans.cpp; `PS2_ENEMY_ST3` st3/r301.cpp st3/r30f.cpp +2; `PS2_FX_COMMON_HAZE` game/esp_sub.cpp game/trans.cpp; `PS2_FX_COMMON_HAZE_RECIPES_H` game/ps2_fx_common_haze_recipes.h; `PS2_FX_GEN` game/esp_sub.cpp; `PS2_WORLD_R11F_OWNER` game/main_mem.cpp game/scroll.cpp +2; `PS2_WORLD_TRANSITION_OWNER` game/scroll.cpp game/trans.cpp +1; `PVR_RTT` game/TexRender.cpp game/esp_sub.cpp; `QA_START_KIT` game/item.cpp; `QUICK_WEAPON_POC_KIT` game/item.cpp; `QW_METER` game/sscrn.cpp; `R100_DEFER_EVENTS` st1/r100.cpp; `R101_CAP_LOG` st1/r101.cpp; `RADIO_SUB_LOG` Sscrn/ss_term.cpp; `RAIN_DIAG_HOST_TEST` game/filter06.cpp; `RAIN_PS2_SHEET_REF` game/esp.cpp game/esp08.cpp +1; `RAIN_R10C_DC` game/filter06.cpp; `RAIN_R10C_DIAG` game/espgen44.cpp game/filter06.cpp; `ROUTE_CH3` game/em_set.cpp st3/r300.cpp +9; `SH4ZAM_LOGIC` include/re4dc_xm.h; `SH4_APPROX_RENDER` include/dolphin/mtx.h include/vec.h; `SHORE_FX_LEVEL` game/esp_sub.cpp; `SKIN_ADMISSION32` game/trans.cpp; `SKIN_CENSUS` game/trans.cpp; `SKIN_RECIPE32` game/trans.cpp; `SKIN_SH4ZAM` game/trans.cpp; `SPLINE_BLOCK03` game/esp_sub.cpp; `SS_CLOSE_HOLD` game/sscrn.cpp; `STAT_DIAG` em21/em21.cpp game/player.cpp; `STRIP21_RETURN` game/esp_sub.cpp; `TA_BIN_DIAG` game/esp_sub.cpp game/ps2_fx_common_haze.inc; `TICK_LOG` game/debug.cpp game/main.cpp; `TITLE_ID_DIAG` game/title.cpp; `TRACE_ALLOC` game/main_mem.cpp; `TRANSITION_GATE_DIAG` game/trans.cpp; `TRIG_FSCA_ROT` game/math_sub.cpp; `TRUCK_DIAG` em3b/em3b.cpp; `WARP_AFTER_RESET` game/main.cpp; `WARP_GOD_HOOK` game/em_sub.cpp game/pl_dmg.cpp +1; `WATER_LAYER29` game/espgen45.cpp game/read.cpp; `WATER_LAYER29_H` game/water_layer29.h; `WATER_LAYER29_PACKAGE_H` game/water_layer29_package.h; `WEAPON_ARCHIVE_REUSE` game/read.cpp; `WEAPON_HEAP4_FAILTEST` game/read.cpp; `WEP27_H` include/re4dc_wep27.h; `WEP_MODULES_27` game/item.cpp game/pl_wep.cpp +3; `WEP_TARGET_GUARD` game/emmine.cpp game/obj1b.cpp; `WORLD_CENSUS24` game/main.cpp; `WORLD_VALID_MEMO31` game/main_mem.cpp; `XM_ON` include/re4dc_xm.h; 
