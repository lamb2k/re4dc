# The services row on the calibrated tier: account and first fixes (lane eng-svcspd1, 2026-11-21)

Status: **finished, unaudited.** Every timing here is **MODELLED (console-build dynarec at 70 MHz, calibrated on the old
port)**: slots `fly1` / `fly2`, `Dynarec.Enabled = yes`, `[config] Sh4Clock = 70` (each run's `emu.cfg.used` holds them).
Pictures 41 to 640 of each scene, the image's own `ROW` rows (`svc` and its groups). The row is 9 ms, judged on the worst
picture. What the model cannot see: the graphics chip's fill and sort, store-queue submission, memory bus contention and
cache misses (the dynarec charges about one issue cycle an instruction, `core/hw/sh4/sh4_cycles.cpp`: FDIV, FSQRT and
FTRV latency and operand-cache misses are not charged), real disc timing.

## 1. The account before the fixes

Runs: `base1-d70` (cbececd7c, timing, no arm) for the groups; `prof1-d70` (same commit, lab arm `SVCPROF`) for the
phases. Evidence `E:\RE4DC-Lanes\eng-svcspd1\runs\`, parsers `py\account.py`, `py\compare.py`, `py\worst.py`.

### Groups (ms, mean / worst picture)

| Group | Village (LEON) | Hill (Leon, Ashley) | Fight (Leon, 4 Ganados) | Boss (El Gigante, headless) |
|---|---|---|---|---|
| Services row | 6.94 / 12.80 | 17.83 / 23.18 | 10.61 / 18.95 | 9.76 / 18.23 |
| Motion (MotionMove, MotionSetCore, hokan, IK) | 3.03 / 8.17 | 6.94 / 12.29 | 5.92 / 10.30 | 6.12 / 13.01 |
| Cloth and hair | 2.00 / 4.60 | 7.50 / 10.00 | 0.01 (not linked) | 0.01 (not linked) |
| Parts and palette | 1.23 / 4.29 | 2.32 / 4.81 | 2.24 / 4.83 | 2.02 / 2.65 |
| Collision (and routes, actor volumes) | 0.44 / 0.90 | 0.72 / 1.06 | 2.18 / 6.89 | 1.05 / 1.91 |
| Camera (row less the others) | 0.29 | 0.38 | 0.31 | 0.60 |

The fight has one character with cloth (Leon, costume without jacket chains in this image: cloth is not linked in
FIGHT=1 or BOSS=1); the brief's "five" does not hold for this image.

### Phases (SVCPROF, exclusive, ms a picture, mean; the arm costs about 0.15 to 0.3 ms)

| Phase | Village | Hill | Fight | Boss | Units a tick (hill) |
|---|---:|---:|---:|---:|---|
| cloth kernel | 1.95 | 7.36 | - | - | 5 chains, 122 links, 6,390 link-against-sphere tests (65 hits) |
| world passes (before IK, after IK, after hokan, partsWorldCalc) | 1.77 | 3.45 | 2.61 | 2.56 | 784 bones on the slow path, 41 fast; 3 passes a character |
| blend (matBlend) | 0.24 | 1.31 | 1.26 | 0.97 | 109 bones |
| local matrices (mat_calc) | 0.61 | 1.27 | 0.93 | 1.06 | 271 bones, 6 sinf/cosf each |
| IK (floor queries in it are collision) | 0.36 | 0.78 | 0.46 | 0.57 | 8 chains |
| palette | 0.29 | 0.62 | 0.61 | 0.48 | 264 bones |
| motion keys (sample) | 0.28 | 0.60 | 0.89 | 1.03 | 68 joints, every one decoded from its keys |
| mailbox | 0.24 | 0.41 | 0.61 | 0.52 | 16 entries, 84 + 74 records served |
| collision: line / floor / sphere | 0.38 / 0.11 / 0.11 | 0.61 / 0.30 / 0.14 | 1.36 / 0.47 / 0.39 | 0.43 / 0.29 / 0.28 | 24 lines (494 nodes, 94 triangles), 7 floors, 4 spheres |
| translations, blend table, hokan, the rest | 0.44 | 0.73 | 0.56 | 0.81 | |

### The worst pictures

- Hill 97 (23.5 with the arm): a clip change: a second MotionMove, the hokan and its third world pass, the blend at its
  widest, MotionSetCore (1.6 ms), on top of the cloth's 7.4. Hill 155: the cloth at 9.8 (the skirt's links near the
  legs: more sphere tests reach the full projection).
- Fight 383 and 479: the first world pass at 3.4 ms (2.5 above its mean) together with 3.8 to 4.0 ms of line queries;
  fight 100: 7.3 ms of line queries in one picture.
- Boss 117: motion 13.1 (blend 2.5, hokan 1.3, matcalc 1.6); boss 318 and 167: MotionSetCore 4.8 to 5.0 ms: the clip
  binding's identity hash at a clip's first use in play (27 boss ticks over 0.8 ms).
- Some runs show one picture with 2 to 3 ms more in whichever phase was running (the same code and inputs read 1.06 ms
  of collision in one run and 3.3 in another): an interrupt or a KOS thread inside the timed span. Worst-picture
  figures carry this noise (about +2 ms in the fight).

## 2. Cost per unit against the code

The tier charges about one cycle an issued instruction, so the measured cycles a unit (ms x 70,000 / units) should match
the instructions the disassembly of the image executes for it (`ev\dis\*.s`, from e1.elf of cbececd7c):

| Unit | Measured (70 MHz) | Instructions in the code path | Reading |
|---|---:|---:|---|
| world pass, a bone on the slow path | 292 cycles | about 290: loop body 70, parent_of 25, PSMTXMultVec 62, five skel_xm wrappers 24+25+34+25+23, 3 FDIV | as the code says; seven calls a bone |
| local matrix, a bone | 328 cycles | 6 x newlib sinf / cosf (12 + __kernel 35 to 45, + __ieee754_rem_pio2f 60 to 100 past pi/4) + 50 | as the code says: the trigonometry is 85% |
| sphere test in the cloth's parallel volume test | 81 cycles (kernel time / tests) | about 75 on the rejection path, 9 of them stack spills and reloads | as the code says; most tests reject |
| palette, a bone | 164 cycles | about 130 + two calls | close |
| blend, a bone | 900 cycles | 2 C_QUATMtx, C_QUATSlerp (acosf, sinf), PSMTXQuat, RotMatrix (6 trig), 3 PSVECMag, 3 FDIV: about 1,000 | as the code says |
| line query | 2,490 cycles | 20 nodes, 4 triangles, 3 PSMTXMultVec a piece, a 260-byte memset | set-up dominates small queries |
| clip binding (first use) | 1 to 5 ms | FNV-1a over the clip header and every served joint's key block, 5 instructions a byte over tens of KB | pure waste on the console (no pack, below) |

Nothing costs more than its code; the code does more than it needs to: trigonometry recomputed for bones whose angles
do not change, three world passes where the IK reads a fraction of the first, calls around every XMTRX step, a hash whose
result is never used, sphere tests run through when the sphere is out of reach. On the console FDIV (3 a slow-path
bone), FSQRT and cache misses on the 64-byte bone records add what the model does not charge.

Two findings outside the services' code:
- **The console images link no motion key pack** (`svc_mk_pack` exists only in the PC reference): every pose sample is
  decoded from the clip's keys (binary search and Hermite), `mk_rows 0` in every scene. The bake exists
  (bake/motion_keys.py); loading it is the loader's and the disc's (a request below).
- **No clip is bound at archive load** (skel.cpp's comment says the image does; no caller exists): binding happens at the
  first MotionSetCore in play.

## 3. Fixes (each its own commit; tier as above; ms saved, mean / worst picture)

Checks for every fix: the PC reference's `hostref/svc/svc_controls.sh` (79 rows, every row as it must), the lane's
`services/skeleton/speed_controls.sh` (each fix's control must make the same comparison FAIL; it does), and the engine
against itself: the native build before the fixes (cbececd7c) and after, five fixtures, cloth wind on and off: every
bone, palette and query bit-identical and the traces byte-identical (`ev\pc-self`, `ev\pc-self2c`; script
`s\selfcmp.sh`). The SH-4 build's results follow from the same operations in the same order (fix 4: the same SH4ZAM
instructions inline).

| Fix | Commit | Village | Hill | Fight | Boss | Control (FAILs as it must) |
|---|---|---|---|---|---|---|
| 1. A bone's pose-angle sines and cosines kept while its angles do not change (trig row, 40 B a bone; 89% hits on the hill) | d58cbe51b | 0.26 / 0.65 | 0.69 / 0.97 | 0.36 / 0.68 | 0.41 / 0.82 | trigstale: door103, hill, bell |
| 2. The cloth's parallel sphere test skipped when the sphere is out of reach (r + len + 1 from p1; 33% skipped) | 0ae252a7e | 0.07 / 0.06 | 0.53 / 0.55 | 0.02 / 0.03 | 0.01 / -0.02 | clothbound: hill-ashley |
| 3. MotionMove's first world pass only for the bones the IK reads (48 of 264 a tick on the hill) | 48f4a82e7 | 0.35 / 0.72 | 0.77 / 1.19 | 0.49 / 1.35 | 0.53 / 0.90 | ikclosure: door103, hill, bell |
| 4. The world pass's steps inline on the SH-4 (SH4ZAM's inline forms, parent_of, the C product) | 41b6cdb6e | 0.27 / 0.57 | 0.53 / 0.81 | 0.39 / 0.57 | 0.37 / 0.82 | worldfast: door103, hill, bell |
| 5. No identity hash when a clip is bound without a pack (+ two counters) | d88b20c1b | -0.02 / 0.35 | -0.06 / 0.55 | -0.08 / -2.23 * | 0.01 / 0.36 | mkstale (no pack): door103, hill (hang = FAIL) |
| 2b. The cloth's early out from both ends (65% skipped): taken back | d45d6ef72 | -0.06 / -0.07 | -0.51 / -0.74 | 0.01 / 1.95 * | 0.00 / 0.00 | clothbound |
| 2c. 2b with the second distance only when needed: taken back | ea65a3ae5 | -0.00 / 0.00 | -0.02 / -0.55 (vs 2b) | | | clothbound |
| 2b and 2c taken back: cloth_kernel.c as fix 2 left it | ef52d3edb | | | | | |

\* the fight's worst picture moves by up to 2 ms between runs of the same code (section 1); its means are the reliable
figure. Fix 5's means carry the two new counters (about 0.05 ms); its gain is in the clip-change pictures.
Fix 2b skipped twice as many tests and ran slower (more live values on the path that is not skipped); fix 2c did not
win it back (hill cloth 7.46 ms against fix 2's 6.95); both were taken back (ef52d3edb).

Tried and not landed: **deferring MotionMove's last world pass** to the next entry that reads the table (dropped when
partsWorldCalc follows, as for the player and the partner). Exact on the PC, but the bones it must compute at once (the
mailbox and its ancestors, the history bones, the blend table's bones and everything under their targets, the roots)
are nearly the whole skeleton: the PC census computed about the same bones a tick. The diff is kept in
`ev\fix6-not-landed\fix6.diff`.

## 4. The row after the fixes

Head ef52d3edb (fixes 1 to 5, engine 505c4da2d merged) against engine 505c4da2d itself, same discs and scenes, runs
`eng0-d70` and `finr-d70` (ms, mean / worst picture; the row is 9):

| Scene | Before | After | Saved | Motion | Cloth | Parts | Collision |
|---|---|---|---|---|---|---|---|
| Village | 6.92 / 12.78 | 6.02 / 10.45 | 0.91 / 2.33 | 2.29 / 6.07 | 1.92 / 4.41 | 1.10 / 1.58 | 0.46 / 0.93 |
| Hill | 17.79 / 23.10 | 15.37 / 19.11 | 2.42 / 3.99 | 5.20 / 8.54 | 6.95 / 9.47 | 2.09 / 4.58 | 0.77 / 1.15 |
| Fight | 10.60 / 18.88 | 9.43 / 18.54 | 1.17 / 0.34 * | 4.86 / 8.88 | 0.01 | 2.05 / 5.20 | 2.24 / 9.56 |
| Boss | 9.54 / 17.95 | 8.24 / 15.07 | 1.30 / 2.88 | 4.95 / 10.41 | 0.01 | 1.83 / 4.81 | 1.07 / 1.92 |

\* the fight's worst picture is a collision picture (line queries; plus the run-to-run noise of section 1).
The hill does not reach 9 ms on its worst picture: 19.1 (and 15.4 on the mean).

## 5. What is left, and what a larger redesign would have to change

The hill after the fixes (phases from `finp-d70` / `fin2cp-d70`, with cloth at fix 2's 6.8 ms kernel), ms a picture,
mean: cloth kernel 6.8; world passes 2.1 (after the IK 0.87, partsWorldCalc 0.94, before the IK 0.23, after the hokan
0.09); blend 1.07; local matrices 0.84; IK 0.77; palette 0.62; motion keys 0.60; mailbox 0.42; collision 1.10 (line
0.64, floor 0.31, sphere 0.15); camera 0.37; translations 0.23; blend table 0.20; MotionSetCore and clock 0.21. The
worst picture (19.1) is a clip change (second MotionMove, hokan and its pass, the widest blend) on top of the cloth's
7.4, plus in some runs one 2 to 3 ms interrupt span.

Ten more milliseconds do not come from more of the same; what would have to change:
1. **Cloth (6.8 ms, presentation).** The skirt is 48 links x 4 constraint passes x up to 4 constraints x 11 leg
   spheres. Exact options left are small (the rejection path is 75 instructions with 9 stack spills: a register-tight
   kernel might halve it). The large cut is a cheaper skirt: fewer constraint passes, the 11 spheres as two leg
   capsules, or the skirt stepped every other tick with interpolation. Each changes the look: the owner's call from a
   still pair or a clip. Estimated 4 to 5 ms.
2. **One world pass a character a tick (2.1 ms).** MotionMove's pass after the IK is recomputed by partsWorldCalc in
   the player's and partner's own move. Deferring it (tried) gains nothing because the mailbox and its ancestors
   (what the behaviour reads in between) are most of the skeleton. The redesign is to give the behaviour the bones it
   reads from a smaller set (the head, hands and feet it actually asks for, not their whole ancestry as records) and
   evaluate the rest once, at publish, together with the palette. Estimated 1 to 1.5 ms.
3. **Load the motion key pack on the console** (0.6 ms of key decoding; a request). And bind clips at archive load
   (MotionSetCore's in-play binding is now cheap, but not free).
4. **Approximate maths where only presentation reads it**: FSCA sines for the local matrices and FIPR/FSRRA forms of
   the blend and hokan quaternions would cut 1.5 to 2 ms, but the bones feed hit checks: they are not identical any
   more, so they need the plays-right gate (and an integrator ruling, since they touch gameplay inputs).
5. **Collision repeats**: 8 to 10% of line queries repeat with the same inputs in the same tick (E1 COL2): a per-tick
   memo would save about 0.1 ms on the hill and the fight; the fight's worst pictures are line-query bursts (up to
   7 ms) worth a look by whoever owns the callers (routes, aim, volumes).
6. **The interrupt span** that adds 2 to 3 ms to one picture in some runs: find which KOS thread or handler runs
   inside the tick (it inflates every worst-picture figure on this tier).

## 6. Tools and arms in the repository
- `services/skeleton/svc_prof.h`, host/e1_svc_mem.cpp: lab arm `SVCPROF` (boot file, read before play: phase times
  per tick, `SP` and `SPC` lines after play on the serial line; the selector's report fills up with them, so an arm
  run is a diagnostic run, never a timing run); control `SVCPROFCTL` (200 us waited a tick inside the palette phase).
- Counters (always on): `E1 SKEL2` (trig hits, IK-pass bones, clip bindings), `E1 CLOTH` (volume tests, skips),
  `E1 COL2` (line and sphere queries repeated in a tick with the same inputs: 8 to 10% of line queries).
- `services/skeleton/speed_controls.sh`: the fixes' controls on the PC reference.
- The arm's control, run `finc-d70` against `finp-d70` (hill, e545d0bce): palette phase 0.62 -> 0.82 ms a picture, the
  services row 16.14 -> 16.35, run total +199.6 us a tick: the account reads a known 200 us wait as 200 us.

## 7. Function checks on the SH-4 build (plain Flycast, slots std1 / std2: function only, no speed)
- Disc finf (e545d0bce): LEONT, HILLT, SHOT, LEONS, HILLS, FIGHTS 6 of 6 OK; hill_engine and camengine every row as it
  must; stills 59 pairs against lane eng-e1p's A2, 0 moved (0.5% of pixels over 32, mean 1.0).
- Disc fins (ea65a3ae5): SHOT, SHOTNP, SHOTDMG, SHOTLATE, LEONT, HILLT 6 of 6 OK; shot_engine 4 scenes as they must
  (SHOT: the hit at tick 162, 800 -> 500, as the reference); hill_engine every row as it must.
- The final head ef52d3edb differs from ea65a3ae5 only in cloth_kernel.c, back to fix 2's (bit-identical on the PC).
