# eng-draw2 hand-back (2026-11-21)

**Status: finished, unaudited (partly: see "Not done").** Branch `lane/eng-draw2`, head after this note's commit (see the
final message); origin/engine e0a1fd5b7 merged at 398bc3cec; step S1 reverted at 87abe7de7.
Tier of every speed number: **MODELLED (console-build dynarec at 70 MHz, calibrated on the old port)**, slot fly1,
`Sh4Clock = 70`, `Dynarec.Enabled = yes` (each run's `emu.cfg.used`). The model cannot see: the graphics chip (TA intake,
ISP/TSP fill and sort), store-queue submission and the TA FIFO, cache, bus contention, disc timing. Worst pictures may
include the KOS clock's 2.5 ms jump (integrator, eng-skel2): judge on mean and p99.

## How the steps were measured
One calibrated-tier session on fly1 (13:45-15:10), one disc per step run back to back under one lease, each disc with
LEON, HILL, FIGHT (timing), BENCH (DRAWLAB5: c0 c0 c0/D f0 f0 f0/D, STILLS40) and LEONS, HILLS, FIGHTS (stills).
The force-push that would have put step 0 first was refused by the guard, so the discs were built from local test refs
(never pushed) holding the same commits with step 0 first: t-b0 bcb74b954 (base + step 0), t-e1 f47c84210, t-s1
a92a24ff9, t-w1 8f83347ca, t-e2 0d31e25a4 (tree = lane commit e34ee9717). Each step is judged against the run before it.
Evidence: `runs\t-b0 .. t-e2` (serial.txt, drawcost.txt/json, stills, emu.cfg.used/restored), scripts `s\`.
Reader: `tools/engine/drawcost.py`; pixels: `tools/engine/stillsdiff.py` (new; selftest PASS, one pixel apart counted 1).

## Drawing row per step (mean / p99 / worst ms; worst may hold the 2.5 ms clock artefact)
| Disc | LEON | HILL | FIGHT | world corners sent LEON / HILL / FIGHT | triangles to the clipper |
|---|---|---|---|---|---|
| t-b0 base | 27.94 / 34.13 / 35.52 | 37.84 / 41.80 / 44.04 | 26.42 / 34.42 / 36.87 | 7,918 / 10,723 / 7,497 | 367 / 416 / 374 (eng-draw1) |
| t-e1 E1 | 26.68 / 32.46 / 34.72 | 36.68 / 40.78 / 43.37 | 25.02 / 32.83 / 34.93 | same | 132 / 182 / 110 |
| t-s1 S1 (reverted) | 30.78 / 38.03 / 39.83 | 36.67 / 40.77 / 43.36 | 28.93 / 37.58 / 39.28 | 10,901 / 10,723 / 10,216 | 276 / 182 / 260 |
| t-w1 W1 (on S1) | 30.32 / 37.19 / 39.04 | 36.86 / 41.75 / 43.42 | 28.53 / 37.68 / 38.52 | same as S1 | same |
| t-e2 E2 (on W1) | 29.85 / 36.27 / 38.41 | 36.29 / 40.98 / 42.93 | 28.11 / 36.02 / 37.84 | 8,520 / 8,170 / 7,937 | same |

Step deltas (mean): **E1 -1.26 / -1.16 / -1.40** (estimate was -2.1 to -2.3; the census's 235-263 wholly-behind
triangles no longer reach clipped()). **S1 +4.10 / -0.01 / +3.91: slower, reverted** (selection -0.7 ms but the side-plane
groups it kept were staged, copied and clipped: staged vertices 7,929 -> 11,267 on LEON). **W1 -0.46 / +0.19 / -0.40**
(eng-draw1's arm X read -1.3; this one keeps the stage's exact arithmetic: fp-contract off, and on HILL, where a staged
vertex is used 1.09 times, the C walk costs more than the asm stage plus copy). **E2 -0.47 / -0.57 / -0.42** (2,381 /
2,552 / 2,278 world corners a picture not sent: 22 / 24 / 22% of the world corners walked).
Landed head (E1, W1, E2 without S1), estimate from the deltas: LEON about 25.8, HILL about 36.3, FIGHT about 24.2 ms
mean; not run as one disc (owed). The row (14 ms) is far off; the characters are 12 to 24 ms of it.

## Controls
- 2 ms arm D (bench window c0/D, f0/D): t-e1 +1.996 / +1.995, t-s1 +2.004 / +2.008, t-w1 +1.994 / +2.008 ms draw,
  worldOP within 0.02: PASS. t-e2's bench did not run its windows (ROOMTRIP stopped it, below).
- stillsdiff.py `--selftest`: PASS; `pair` exits 1 on any differing pixel or no pairs (it failed on every bench pair).
- DRAWLAB5's D windows also serve as a pixel check: a timing change in the opaque pass must change no pixel (they match
  the base windows on every still except the effect noise below).

## Pixels (differing-pixel counts, E1 stills scenes LEONS / HILLS / FIGHTS against the step before)
- E1 vs base: LEONS 0, HILLS 4 (2 stills, 2 px), FIGHTS 25 (2 stills, worst 12 at picture 600, one colour step, left
  screen edge). The clipper's machine code is byte-identical in the base and E1 images (e1 and fight; `s\cmpclip*.sh`),
  and E1 only skips calls that emitted nothing, so these are not E1's: the same HILLS stills (40, 200) differ by 1 to 3 px
  between t-e1, t-s1 and t-w1 although nothing on the hill changed between them (HILL's counters identical). The
  calibrated tier's E1 stills are not repeatable to the pixel at HILLS 40/200 and FIGHTS 480/600; the integration lane
  found them repeatable on its plain slot (59 of 59). A base re-run on this tier was cancelled (one-disc rule): owed.
- S1 vs E1: LEONS 0, HILLS 3, FIGHTS 0. W1 vs S1: LEONS 0, HILLS 1, FIGHTS 0; **W1 vs base: LEONS 0, HILLS 0, FIGHTS 0**
  (exact stage arithmetic held). E2 vs W1: LEONS 0, HILLS 9 (still 40), FIGHTS 9 (still 480): the same stills as the noise
  above; a wrongly dropped strip would cost whole triangles, not single pixels; not proved (needs the noise floor).
- Bench: not repeatable, see step 0.

## Step 0: why the bench's stills do not repeat
1. **Deterministic: the effect cap's hysteresis.** The first window of a room starts with `fx_drawn_last` (content_fx.inc,
   the effect density cap's "drawn last picture" bonus) empty; later windows start with the previous window's last
   picture's set: picture 1 of the first window differs by 858 px (cross) / 831 px (farm), always in the pyre's fire and
   smoke. Fix is outside this lane's files (request below); compare the same window index across builds.
2. **Random: the smoke and fire sprites** differ between runs of the same disc at a few pictures (593 px at cross 551, 52
   at farm 951, 5 at farm 601...), all in the translucent effect region; not diagnosed. Not threaded rendering (same with
   rend.ThreadedRendering = no, runs r0-std-a / -nothr / -b).
3. A real race fixed (108dec533): KOS starts a render only after the previous picture is flipped and pvr_wait_render_done
   returns at once before it starts; the stills took the frame buffer two fields later and could get the picture before.
   The bench and E1 stills now wait on KOS's flip counter (native_wait_shown). It did not remove 1 and 2.
So: pixel checks of world steps are made on LEONS / HILLS / FIGHTS; the bench's stills can be compared only outside the
effect region and at the same window index.

## Bake step and receipt
None. The facing records are made from the pack's own vertices at room load (native_world_facing): no pack set changes,
no receipt, nothing for eng-int to build. Cost: 4 bytes a strip plus 4 a meshlet group in main memory: the E1 image's
"free to arena" at LEON went 401,408 (eng-draw1's run) -> 270,336 B (t-e2), HILL 483,328. **Pack set for eng-int: none.**

## What changes at the graphics chip (for the deferred console run)
- E1, W1: nothing (same TA words, same count).
- E2: world vertices sent fall by 2,381 / 2,552 / 2,278 a picture (LEON / HILL / FIGHT, of 10,901 / 10,723 / 10,216 on
  the S1 disc), all from strips the chip would have culled: less TA intake, no ISP change.
- Console questions: the TA intake at 8,000 to 10,000 world vertices plus the characters; whether the C walk's store
  pattern (one 32-byte line a corner, no stage) costs more or less than stage + copy on real hardware.

## R3 (eng-load1's request, integrator's assignment) 611b92b2e
native_release (everything a pack holds, resident buffer included), per-pack resident sizing (no longer CROSS/FARM by
name; the bench reserves its two rooms), `e1_draw_close_c` / `e1_draw_reopen_c` in core/draw_e1.c (outside my owned list,
by the assignment). Proof run t-e2 (BENCH, ROOMTRIP): **main memory in use returns exactly (383,420 B after each of three
releases); video memory free returns to 4,913,640 each time, 24 B under the 4,913,664 before the first open** (constant,
not growing: the VRAM allocator's own bookkeeping after its first use); largest free block 4,913,568 at every release,
2,639,648 (village) / 2,167,456 (farm) when open. The check compares with the value before the first open, so it printed
FAIL and stopped the bench (stage 95): the check needs its baseline taken after one warm-up release (not changed: a
change of a check needs your ruling). Control ROOMKEEP (run t-rk): see the final message.

## Files touched outside the owned list
core/draw_e1.c (R3 entries by assignment; step 0's still wait), core/frame.cpp (merge resolution only: both lines kept),
render/native_scene.inc/.h (render/, the pack loader the renderer owns), render/stage_sh4.S (world stage kernel removed;
the actor kernel there untouched), tools/engine/stillsdiff.py (new check).

## Requests for other lanes
- Owner of render/content_fx.inc (eng-look's effects; eng-draw3 includes it): clear `fx_drawn_last` when a window starts
  (as content_actor_frame does at picture 1), so the bench's windows start alike.
- eng-int / integrator: rule on ROOMTRIP's baseline (24 B of VRAM allocator bookkeeping).
- After the clock fix is in engine: the bench's readers to e1_clock (integrator's note), base re-run.

## Not done / not verified
- S1 as briefed (no per-group tests) is a loss on this tier; not landed. A cheaper S1 (float boxes at load) not tried.
- The landed head (without S1) not run as one disc; census (DLV / Z) not re-run, dead shares given by the counters only.
- Calibrated-tier still noise on HILLS / FIGHTS not floored (base re-run cancelled); E2's 9 px not proved to be noise.
- W1 in hand-written SH-4 not done (the C walk measured -0.4 to +0.2 ms).
- Link check after the merge: default PASS (384, SERVICE 0), SENDABLE PASS; FIGHT and BOSS lists are origin's (not printed
  in my summary; eng-draw1 reported them FAIL from origin's service lists). All four images build and link.
