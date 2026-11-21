# Where the drawing time goes, and what to build instead (lane eng-draw1, 2026-11-21)

Status: finished, unaudited. Tier of every number unless marked: **MODELLED (console-build dynarec at 70 MHz, calibrated
on the old port)**, flycast-console slots fly1 / fly2, `Dynarec.Enabled = yes`, `[config] Sh4Clock = 70`. "estimate"
marks a number computed from code counts and measured unit costs, not run.

## 0. The answer

Ordered as the integrator asked (F-Zero engine line's order): what is spent per draw, the invisible work, how primitives
are walked, then fewer or cheaper primitives. Picture-changing options are kept apart.

1. **What is spent.** Drawing is two things of about equal size: the world (selection 3.7 ms on a moving picture, then
   0.94 us a world corner and 7.5 us a triangle given to the clipper) and the characters (1.5 to 1.8 us a corner,
   all-in: skinning, weight sets, lighting, emission). HUD, sky, effects and list switches are under 1.5 ms together.
   Per unit the cost is instruction count, because that is all this tier charges (section 1).
2. **Invisible work is a fifth to a quarter of the drawing row** (census, section 4b): **43 to 47% of the world's
   corners a picture belong to strips no triangle of which is ever seen** (every triangle back-facing under the
   headers' own culling, or wholly off the screen), and 45 to 53% of the staged world vertices serve only those; **56 to
   71% of the triangles given to the clipper lie wholly behind the near plane** and produce nothing. At the measured unit
   costs that is about 5.1 ms (LEON), 6.6 (HILL), 5.1 (FIGHT) of CPU time, plus 0.4 to 1.3 ms of characters' positions
   and normals skinned and lit for strips the outcode test then drops. Characters are drawn with culling off in every
   header: 57 to 58% of their on-screen triangles are back faces the chip draws and hides (0.2 to 0.4 screens of area);
   culling them is a look choice (double-sided parts), not an exact cull.
3. **The near plane fix added 3.7 to 5.6 ms** (LEON 4.1, HILL 5.6, FIGHT 3.7, measured): 370 to 420 triangles a
   picture reach the clipper, of which only 69 to 94 cross the plane.
4. **Walking order:** the world stages each vertex, then copies each corner from the stage; a staged vertex is copied
   about once, so the copy is overhead. Walking the strips without a stage measured -1.3 to -1.4 ms in C (E1 scenes)
   and is about -3 to -4 ms in a hand-scheduled loop (estimate). Unrolling the copy instead (arm V) made it worse
   (+0.1 to +0.3 ms): strips average 4.7 corners, so per-strip overhead dominates.
5. **Pixel-identical path (estimate):** LEON 11.0 mean / 14.9 worst, FIGHT 10.2 / 15.6, HILL 14.4 / 17.8 against the
   14 ms row (section 7; estimate). **It does not reach the row at the worst pictures, and HILL misses even its mean.** What
   closes the gap changes the picture and is the owner's look choice: world distance levels (W2: -0.75 to -3.1 ms
   measured, with its differing-pixel count), character distance levels in the E1 images, culling the characters' back
   faces, a light cap. W2, W3 and character levels carry exact differing-pixel counts on the bench (section 6b: W2 761 to
   18,387 pixels a still); back-face culling, the light cap and every E1 pair are still owed one.

## 1. What this tier charges (read from the emulator's source)

flycast-console f06da2d8 (the slots run 8fb534cc, the commit before it, which only adds cache counters):
`core/hw/sh4/dyna/decoder.cpp` dec_DecodeBlock and `core/hw/sh4/sh4_cycles.cpp` countCycles.

- With the dynarec on, every compiled block carries a fixed charge decided when it is compiled: per instruction the
  opcode table's issue cycles (almost all 1), or 0 when it pairs with the one before (different units, neither CO, not
  both the same non-MT unit), plus 2 cycles for each of the first three memory instructions of the block. The block's
  sum is scaled by 200 / Sh4Clock (2.857 at 70) and rounded. The TMU, which `timer_us_gettime64` reads, advances by
  these charges.
- A block ends after a branch and its delay slot and after every conditional branch (taken or not); `fschg` does not end
  one.
- **Not charged at all:** cache misses, store-queue bursts to the graphics chip and the TA's FIFO, FPU result latency
  (ftrv, fsrra issue in one), memory bus contention, the graphics chip's own time (TA, ISP/TSP fill and sort), disc time.
- So on this tier a path costs (its charged issue cycles) / 70 MHz. What makes it faster: fewer instructions, more LS
  instructions next to EX/FE/MT ones, fewer conditional branches inside loops (each one restarts the memory charge).
  What does not show: cache layout, prefetch, store-queue burst sizes, operand-cache RAM. **Options of that kind are
  console work and are listed as such; this tier cannot rank them.**
- `tools/engine/fccycles.py` applies that rule to a code path of an ELF (selftest: four hand-charged blocks, PASS). Its
  charge agrees with the measurement within 10% on the world's stage loop and over-charges by 20 to 50% on loops full of
  conditional branches (skin kernel 0.72 counted against 0.59 measured, lighting 1.74 against 1.04 to 1.16): measured
  unit costs are used for the account, the tool for comparing a loop with its replacement.
- Calibration note: the old port's console time is about 2.86 times its charge (fitted at 70.9 to 75.7 MHz). The
  engine's scheduled kernels would run on a console at about their real scheduled cycles: `re4dc_avk_pos_skin_u16` is
  37.5 real cycles a vertex (its scheduler) and is charged 41 to 50 here, that is 0.59 us against about 0.19 us real
  (estimate). For such code the tier is pessimistic by 2.5 to 3.8 times; for code bound by store-queue submission it may
  be optimistic. The row is still judged on this tier (Amendments D).

## 2. How each number was obtained

- Image: branch `lane/eng-draw1` at 25c0d69a2 (discs d1 base and bench lab, d2 set A, d3 set B), a11dc7fe5 (d4
  options), 2b80ade89 (d5 census) and 91a0f6d7c (d6 census with the characters' sides, look pairs), built by
  `tools/engine/build_console_disc.sh --ref HEAD` with boot files by `--put`. Runs `E:\RE4DC-Lanes\eng-draw1\runs\d1..d6`,
  each with its `serial.txt`, `emu.cfg.used` and `drawcost.json`. Timing runs d1 to d4: Sh4Clock 70, Dynarec yes. Census
  and look runs d5, d6: dynarec without a clock line (function runs; no time from them is used).
- Pictures 41 to 640 of each E1-family scene (the selector's window): LEON (village route), HILL (Leon and Ashley),
  FIGHT (four Ganados at the cross); bench windows of 600 pictures (CROSS, FARM hay-fork view).
- **Phases** (`render/draw_cost.inc`): one clock read at each pass boundary the renderer already has (visibility, end of
  selection, sky, each world pass in and out, HUD in and out). The spans between consecutive stamps are the phases; the
  drawing row (ROW draw) minus their sum is the remainder (list and scene finish): 0.05 ms in every scene. "actors" is the
  span between the opaque world pass and the punch-through one: the characters (Leon, Ashley, Ganados) and one list
  switch.
- **Counters**: register sums added to a global once a strip, part or call (never once a vertex).
- **Lab arms** (run-time, read before play from boot files DLA / DLB / DLC or bench schedule tokens; `render/draw_cost.h`):
  repeat one phase (its second run adds its own cost once more) or change the near plane. In the E1 images they are
  interleaved over the pictures (every 6th, 5th or 4th picture); each arm picture is compared with the mean of its nearest
  base pictures before and after (`tools/engine/drawcost.py`). While a set is on, the world's selection runs every
  picture, base pictures included. Bench arms are whole windows against the room's two base windows (spread 0.00 ms).
- **Controls**: arm D puts 2 ms of busy waiting inside the opaque world pass and must read 2.0 ms (within 0.1) in the
  drawing row and in the worldOP span: LEON +1.95 / +1.94, HILL +1.97 / +2.00, FIGHT +1.98 / +2.03, bench CROSS +1.99 /
  +2.01: PASS. The reader on eng-cmp1's d70 serial (an image without these lines) FAILS each drawn E1 scene (exit 1).
- **Instrumentation cost**: LEON 27.48 / 35.02 ms (mean / worst) against eng-cmp1's 27.01 / 34.94 on the same tier and
  scene, HILL 37.35 / 43.72 against 36.84 / 42.74, FIGHT 26.01 / 36.14 against 25.58 / 35.82: about +0.45 ms mean.
- **Per-picture regression** (600 pictures, `s\regress.py`): world spans against world corners and clipped triangles.

## 3. The account (MODELLED, ms a picture: mean / p99 / worst over pictures 41-640)

| Phase | LEON (village route) | HILL (Leon and Ashley) | FIGHT (four Ganados) | Bench CROSS (mean) | Bench FARM (mean) |
|---|---|---|---|---:|---:|
| **Drawing row** | **27.48 / 33.47 / 35.02** | **37.35 / 41.28 / 43.72** | **26.01 / 33.81 / 36.14** | 27.70 | 32.30 |
| Visibility and selection | 3.83 / 5.00 / 7.57 | 0.53 / 1.52 / 3.97 | 3.71 / 4.89 / 5.96 | 1.51 | 0.56 |
| World, three lists | 10.63 / 15.60 / 17.15 | 11.57 / 12.62 / 13.91 | 10.21 / 15.60 / 17.78 | 10.40 | 14.11 |
| - stage (transform, 1/w, UV) | 4.61 | 5.14 | 4.26 | 4.44 | 6.21 |
| - copy to the store queue, and the clipper | 5.44 | 6.03 | 5.12 | 5.39 | 7.40 |
| - headers, placements, per piece | 0.58 | 0.40 | 0.84 | 0.57 | 0.50 |
| Characters (opaque) | 11.95 / 12.16 / 14.62 | 24.09 / 26.33 / 28.71 | 10.99 / 15.22 / 17.66 | 13.54 | 15.11 |
| - weight sets (blend, project, per-set light terms) | 1.60 | 3.55 | 1.44 | 1.62 | 1.86 |
| - normals lit | 4.31 | 7.06 | 3.52 | 4.32 | 4.79 |
| - corners emitted (opaque part) | 3.72 | 8.49 | 3.01 | 4.20 | 4.24 |
| - positions skinned (0.59 us each, bench) | 2.11 | 4.01 | 1.84 | 2.18 | 2.19 |
| - frame setup, part tests, light pick, rest | 0.21 | 0.98 | 1.18 | 1.22 (with shadows) | 2.03 (with shadows) |
| Translucent extras (hair emission 0.50, laser, effects) | 0.52 | 0.51 | 0.55 | 1.30 | 1.43 |
| HUD | 0.45 | 0.55 | 0.45 | 0.44 | 0.44 |
| Sky, list switches, finish | 0.12 | 0.12 | 0.12 | 0.10 | 0.10 |

Work units (mean / worst a picture):

| Units | LEON | HILL | FIGHT | CROSS | FARM |
|---|---|---|---|---:|---:|
| World pieces drawn / placements / material headers | 216 / 66 / 46 | 198 / 76 / 23 | 203 / 58 / 45 | 218 / 69 / 47 | 217 / 59 / 27 |
| World vertices staged | 7,929 / 13,104 | 9,867 / 11,155 | 7,597 / 12,882 | 7,593 | 12,071 |
| World strips / corners copied (corners per strip) | 1,684 / 7,918 (4.7) | 2,148 / 10,723 (5.0) | 1,611 / 7,498 (4.7) | 1,655 / 7,435 | 2,771 / 12,115 |
| World strips clipped / triangles to the clipper / corners out | 119 / 367 / 433 (worst 560) | 99 / 416 / 595 | 129 / 374 / 368 | 124 / 400 / 406 | 213 / 546 / 450 |
| Meshlets tested in selection | 359 (worst 531) | 89 (277) | 340 (520) | 143 | 103 |
| Character passes / parts drawn / weight sets | 1 / 8 / 183 | 2 / 15 / 431 | 5 / 7 / 181 | 1 / 13 / 191 | 1 / 14 / 194 |
| Positions skinned / normals lit / lights per normal | 3,572 / 3,709 / 3.0 | 6,781 / 6,765 / 2.4 (up to 4) | 3,108 / 3,264 / 2.9 | 3,688 / 3,776 / 3.0 | 3,695 / 3,778 / 4.0 |
| Character strips / corners emitted (corners per strip) | 1,336 / 7,274 (5.4) | 2,640 / 15,689 (5.9) | 1,197 / 5,756 (4.8) | 1,452 / 8,050 | 1,444 / 8,216 |
| Character triangles to the clipper | 0 | 0 | 0 | 0 | 0 |
| HUD and text rectangles | 20 | 27 | 23 | 53 | 60 |
| Store-queue lines (32 bytes) a picture, about | 15,800 | 27,200 | 13,700 | 16,000 | 21,000 |

The worst pictures are world pictures in LEON and FIGHT (picture 195: world 17.15 at 12,074 corners; picture 499: world
17.78 at 12,708) and character pictures on the hill (picture 171: characters 28.65, four lights a normal where the mean
is 2.4). The E1 images draw every character at full detail: eng-look's character distance levels (owner-approved step 3)
are on in the bench only; the E1 actor pass never asks for a level.

Correction to the brief: the bench's "world alone" is not world alone. Its windows draw the recorded characters too
(3,688 positions at the cross); the world is about 10.4 ms of its 27.7.

## 4. Cost per unit, against what the code should cost

| Path | Measured (MODELLED) | How measured | The code's charge (fccycles) | Where it goes |
|---|---:|---|---:|---|
| World vertex staged (asm m1_stage_world) | 0.58 us | arm S / vertices staged (0.58, 0.52, 0.56) | 0.53 us (37 charged a vertex) | as counted; 94 instructions a vertex pair |
| World corner copied | about 0.36 us | regression less staging | 0.355 us (25 charged) | 28 instructions a corner: the stage pointer reloaded every corner (the asm's memory clobber), the index times 32 in 4 instructions, 8 LS moves that cannot pair with each other |
| World corner, all-in (stage + copy + per piece) | 0.94 us | per-picture regression, r2 0.99 (LEON, FIGHT) | 0.89 us | a staged vertex is copied 0.98 to 1.09 times: the stage saves almost nothing and the copy is overhead |
| Clipped world triangle | 7.1 to 8.0 us | per-picture regression (LEON 8.0, HILL 7.7, FIGHT 7.1) | clipped() is a 560-instruction function taking three 24-byte Corner structs by value, a per-channel colour loop per cut edge, every triangle of a crossing strip sent through it (even those wholly in front), plus the C staging path for boundary pieces | about 50 times a corner |
| Selection, moving camera | 3.6 ms a picture (LEON, FIGHT), 1.4 (HILL) | arm Q | per placement a 6-plane compose; per cluster and meshlet box tests with u16-to-float conversions | about 10 us a meshlet tested |
| Character position skinned (avk kernel) | 0.59 us | bench arm K / positions | 0.72 us (50 charged; branch-heavy, so over-charged) | 37.5 real cycles by its scheduler: the tier charges it 2.5 to 3 times |
| Weight set built | 8.2 to 8.7 us | arm B / sets | about 600 charged | 12-float blend, 4 transforms, then per light a sqrt, a divide and a 3x3 rotation, all in C |
| Normal lit | 1.04 (2.4 lights) to 1.16 us (3 lights) | arm L / normals | 1.74 us with every light lit | per light a conditional branch (a new block each), per channel a clamp with branches, the loop count re-derived per normal by a multiply |
| Character corner emitted | 0.51 to 0.58 us | arm E / corners | 0.485 us (34 charged) + per strip | u, v converted from u16 per corner (6 instructions), 43 instructions a corner, outcode loop on boundary parts |
| Character corner, all-in | 1.54 (HILL) to 1.77 us (FIGHT) | per-picture regression, FIGHT r2 0.996 | | positions per corner 0.43 to 0.54, normals likewise |
| HUD rectangle | about 20 us | arm H / rectangles | layout loops over 12 levels, sin and cos per widget | small in total (0.45 ms) |

**Where the measurement is far above what the work needs** (this tier cannot show cache or queue costs, so "far above"
means far more instructions than the job): the world copy (the whole 0.36 us a corner is avoidable), the clipper (about
500 charged cycles a triangle where a lean clipper needs about 100), selection (3.6 ms where baked per-cell lists need
about 1), weight sets (about 600 charged where about 200 do) and the lighting loop (about 80 charged where one ftrv for
three lights and a branch-free clamp need about 30).

## 4b. The invisible share (census, counts only)

The census (lab arm Z on the bench, boot set DLV in the E1 images; `render/draw_cost.inc`) classes every triangle the
renderer submits on the screen positions it already made: wholly off the screen (all three corners past one edge),
back-facing under its header's culling, or kept; it adds up the kept triangles' screen area clipped to 640 x 480, and
marks the strips, staged vertices, positions and normals that no kept triangle uses. It only reads (its pictures are
checked against base pictures, section 6). Counts are means a picture over pictures 41-640 (bench: 600). Runs d5 (world,
clipper) and d6 (characters' sides), flycast-console slot fly2, dynarec, function runs (no timing).

The world's headers all cull clockwise triangles (ISP/TSP culling bits = 3, 100% of the culled-mode triangles); the
sign the chip removes is read from them (clockwise on the screen: the positive sign of the area formula). Every
character header has culling off. Which side of a character is its back is read from depth: in every scene the
triangles of the positive sign are farther on average (mean 1/w 0.00076 against 0.00081 in LEON, 0.00041 against
0.00043 on the hill), the same sign the world culls.

| A picture (mean) | LEON | HILL | FIGHT | Bench CROSS | Bench FARM |
|---|---:|---:|---:|---:|---:|
| World triangles submitted (opaque and punch-through lists) | 3,888 | 5,925 | 3,721 | 3,519 | 6,165 |
| - wholly off the screen | 815 (21%) | 1,547 (26%) | 704 (19%) | 786 (22%) | 1,404 (23%) |
| - back-facing, removed by the chip's culling | 1,414 (36%) | 2,161 (36%) | 1,393 (37%) | 1,185 (34%) | 1,582 (26%) |
| - kept | 1,657 (43%) | 2,216 (37%) | 1,623 (44%) | 1,547 (44%) | 3,178 (52%) |
| World strips with no kept triangle / of all | 804 / 1,684 (48%) | 1,117 / 2,148 (52%) | 770 / 1,611 (48%) | 806 / 1,655 | 1,262 / 2,771 |
| Their corners (copied for nothing) | 3,379 (43%) | 5,060 (47%) | 3,250 (43%) | 3,359 (45%) | 5,207 (43%) |
| Staged world vertices no kept triangle uses | 3,578 (45%) | 5,186 (53%) | 3,399 (45%) | 3,385 (45%) | 5,118 (42%) |
| Triangles given to the clipper: wholly behind / wholly in front / crossing | 235 / 62 / 69 | 234 / 87 / 94 | 263 / 40 / 70 | 276 / 53 / 70 | 413 / 40 / 92 |
| Character positions skinned that no drawn strip uses (normals lit likewise) | 512 (498) | 237 (227) | 767 (770) | 348 (333) | 289 (266) |
| Character triangles wholly off the screen | 58 | 30 | 105 | 49 | 42 |
| Character triangles back-facing, drawn because culling is off (of those on screen) | 2,455 (58%) | 5,691 (57%) | 1,892 (58%) | 2,670 (57%) | 2,734 (57%) |
| - their screen area, in screens | 0.34 | 0.21 | 0.37 | 0.35 | 0.33 |
| - if they were culled: strips, corners and positions no longer needed | 449 / 2,457 / 1,583 | 1,057 / 5,585 / 2,689 | 351 / 1,911 / 1,536 | 514 / 2,690 / 1,487 | 515 / 2,710 / 1,424 |
| Opaque world area kept, in screens (640 x 480) | 1.9 | 1.8 | 1.7 | 1.2 | 2.3 |
| Character area (both sides), in screens | 0.7 | 0.4 | 0.8 | 0.7 | 0.7 |
| Translucent area (world list 2 and hair), in screens | 0.7 | 1.0 | 0.9 | 0.8 | 0.4 |

**Who pays.** The CPU pays for every staged vertex, every copied corner and every clipper call above, whether or not
anything is seen: at the measured unit costs (0.58 us a staged vertex, 0.36 us a copied corner, 7.5 us a clipper
triangle; MODELLED) the world's invisible work is **5.1 ms (LEON), 6.6 (HILL), 5.1 (FIGHT)** a picture (dead vertices
staged 2.1 / 3.0 / 2.0, dead corners copied 1.2 / 1.8 / 1.2, wholly-behind triangles clipped 1.8 / 1.8 / 2.0), and the
characters' unused positions and normals 0.85 / 0.39 / 1.30 ms. The graphics chip pays for the dead corners a second time
(the TA takes every submitted vertex; this tier does not charge it), and for area: opaque area is depth-tested per pixel
per layer (1.7 to 2.3 screens of world plus 0.4 to 0.8 of characters), translucent area is also shaded and blended per
layer (0.4 to 1.0 screens). Overdraw is chip time, not CPU time; this tier does not see it, the deferred console run
does. The characters' back faces cost both: the CPU skins, lights and emits them, the chip depth-tests them.

## 5. What the near plane fix added (lane eng-e1l)

Arm N gives the renderer the pre-fix near plane (p23 / (p22 - 1) not a number; everything else as today), every 6th
picture:

| | LEON | HILL | FIGHT |
|---|---:|---:|---:|
| Drawing with the pre-fix plane, against today | -4.12 ms | -5.62 ms | -3.67 ms |
| of which world opaque / translucent | -2.88 / -1.01 | -3.78 / -1.75 | -2.86 / -0.76 |
| Triangles reaching the clipper a picture today (mean / worst) | 367 / 560 | 416 / 499 | 374 / 484 |
| Their cost at 7.1 to 8.0 us each (regression) | 2.9 | 3.2 | 2.7 |
| World corners copied with the pre-fix plane | -844 | -2,968 | -656 |

So the fix costs 3.7 to 5.6 ms a picture: about 2.7 to 3.2 ms of clipping (370 to 420 triangles, each about 50 times a
corner's cost) and the rest more world drawn (the pre-fix plane also changed which pieces and levels the selection chose;
not separated further). No character triangle reaches the clipper in these scenes.

The census (section 4b) shows what the clipper is given: of 366 / 415 / 373 triangles a picture (LEON / HILL / FIGHT),
**235 / 234 / 263 lie wholly behind the near plane** (the clipper emits nothing for them), 62 / 87 / 40 lie wholly in
front (they could go out as strips) and only 69 / 94 / 70 cross it. The clipper is handed whole strips that cross the
plane and walks every triangle of them. Rejecting the wholly-behind ones first leaves the output unchanged by
construction; most of the fix's cost goes with them.

## 6. Options, in the integrator's order, the two kinds kept apart

Gains in ms a picture (mean), MODELLED. **measured** = run as a lab arm in this lane (disc d4; E1 scenes interleaved
every 4th picture, bench whole windows); **estimate** = counts x (measured unit cost - the replacement's unit cost from
its code count: prototype loops compiled with the image's flags and charged by fccycles.py, `E:\RE4DC-Lanes\eng-draw1\
s\proto_*.c`). Estimated gains are applied one after another (section 7), so they add. Pixel counts: exact number of
pixels that differ from the base still in any of R, G, B, on bench pictures (pictures 1, 51, ..., 551 of each window are
handed over: STILLS40, schedule DRAWLAB3, run d6, `E:\RE4DC-Lanes\eng-draw1\s\pixdiff.py`). **The bench's drawing is not exactly repeatable from
window to window:** two base windows differ by 18,930 pixels at cross pictures 201 and 501 and by 831 at farm picture
601, and the census window (which only reads) differs from base by 8 to 858 pixels at five more pictures: something in
the drawing depends on time or on the window before (not diagnosed; the effects and the glow are the suspects). So the
counts below are taken only on the pictures where every base window and the census window agree to the pixel (CROSS
101 and 401; FARM 751, 801, 851, 1051, 1101, 1151): there a difference is the arm's own. The census control (FAIL in
`pixdiff.py` on the other pictures) is what found this. The look pairs were taken on the plain-speed dynarec (slot fly1,
no clock line), the same renderer as every other run.

### 6a. Pixel-identical: stop invisible work, change the walking order, cheaper kernels

| # | Option | What changes | LEON | HILL | FIGHT | Kind of number | Exactness | Cost to build, lanes touched |
|---|---|---|---:|---:|---:|---|---|---|
| E1 | Clipper pre-reject | A triangle of a crossing strip wholly behind the near plane is dropped before clipped(); one wholly in front goes out unclipped; only crossing ones are clipped | -2.13 | -2.28 | -2.21 | estimate (census counts x 7.5 us) | dropped ones: identical by construction; unclipped ones: to be shown by pixel count when built (their corners would come from the stage instead of the clipper's recomputation) | small; render only |
| E2 | Exact strip cull before staging | Per strip (or strip group) a baked normal cone and bounds; a strip whose every triangle the header would cull, or that lies wholly off the screen, is never staged or copied | -2.30 | -3.38 | -2.20 | estimate (70% of the census's dead strips captured by conservative cones) | exact: the chip would discard every triangle of such a strip (culled, or off the screen) | bake: cones and bounds per strip group (eng-bake1's pack format); render |
| E3 | Characters: skin and light only what a drawn strip uses | Positions and normals used only by outcode-rejected strips are skipped | -0.85 | -0.39 | -1.30 | estimate | exact (the skipped results are never read) | render; the skin kernel call is in services/actor_e1.inc (eng-svc owner) |
| W1 | World walked without a stage | Each strip corner transformed and written where it is used (no stage, no copy) | -1.33 measured (C) / -3.0 estimate (asm, baked float vertex) | -1.37 / -3.9 | -1.27 / -2.8 | measured arm X, and estimate | arm X: 0 to 2 pixels a still differ (CROSS 2, 2; FARM 0 to 2): its C loop rounds u, v differently from the asm stage; the asm loop must keep the stage arithmetic to reach 0 | render; bake (16-byte float vertex with its colour, corners with baked UV) |
| W1' | Copy loop unrolled (arm V) | The present copy, two corners an iteration | +0.24 | +0.09 | +0.33 | measured | identical (same stores) | **dropped: slower** |
| S1 | Selection without per-group tests | Meshlets inside the frustum keep all groups; boxes as floats at load | -1.92 | -0.27 | -1.85 | estimate (half of arm Q's 3.6 ms) | exact (more submitted, the same pixels) | render |
| C1 | Light kernel | Three lights per ftrv, branch-free clamp | -2.60 | -4.74 | -2.28 | estimate (0.40 us a normal from a prototype) | to be shown by pixel count (summation order) | render (source_light.inc) |
| C2 | Character emission | Corner records with baked UV; four 64-bit stores | -2.18 | -4.71 | -1.73 | estimate (0.25 us a corner) | to be shown (UV floats baked instead of computed) | render; bake (corner records) |
| C3 | Weight sets | Lights per bone, blend and project in asm | -1.01 | -2.37 | -1.00 | estimate (3 us a set) | to be shown | render |
| C4 | Skin kernel | Weight-set runs without the per-vertex switch test; outcodes only for boundary parts | -0.50 | -0.95 | -0.44 | estimate (0.45 us a position) | identical arithmetic | game/platform/avk_sh4.S (shared kernel) |

### 6b. Options that change the picture (the owner's look choices; never inside a speed arm)

| # | Option | LEON | HILL | FIGHT | Bench CROSS / FARM | Kind of number | Differing pixels against the base still (floor first) |
|---|---|---:|---:|---:|---:|---|---|
| G | No near clipping: w raised to the near plane | -2.16 | -2.41 | -2.19 | -2.36 / -3.18 | measured | CROSS 0, 0; FARM 0 to 1 a still (these bench pictures: few crossing triangles on screen); E1 pictures not paired: owed |
| W2 | World one or two levels coarser past 15 m, at most 48 pieces past 15 m (eng-look step 2) | not available in E1 | | | -0.75 / -3.11 | measured (bench) | CROSS 761 a still (0.25%); FARM 18,374 to 18,387 (6.0%) |
| W3 | Two levels coarser past 10 m, at most 24 pieces past 10 m (step 3) | not available in E1 | | | -3.98 / -6.08 | measured (bench) | CROSS 37,112 (12.1%); FARM 60,803 to 61,068 (19.8%) |
| L3 | Character distance levels (owner-approved step 3, on in the bench; the E1 actor pass never asks for a level) | not measured in E1 | | | -0.54 / -0.87 (L0 against L3) | measured (bench) | CROSS 214 a still; FARM 131 to 136 |
| P3, B3 | Far props as cards; baked character lighting | | | | -0.08 / -0.10; -0.01 / -0.04 | measured (bench) | not worth a pair |
| CB | Characters' back faces culled (their headers' culling switched on, and the strips with no front triangle skipped) | -4.0 | -7.4 | -3.6 | | estimate (census counts x today's unit costs; about half after C1 to C4) | owed: needs a build and a pair; double-sided parts (hair cards, cloth, open edges) would lose their back sides |
| C5 | Character lighting at half rate (alternate pictures) | -0.74 | -1.35 | -0.65 | | estimate | owed |
| C8 | At most three lights a character (the weakest dropped; the hill's worst picture has four) | 0 | -1.35 (worst picture) | 0 | | estimate | owed |
| UV16 | The TA's 16-bit UV format (7-bit mantissa: up to 2 texels off near u = 1 on a 512 atlas) | | | | | | owed; not proposed |

## 7. Which combination reaches 14 ms, and the floor

Applied one after another in the order of section 6a (E1, E2, E3, W1 asm, S1, then C1 to C4), estimate, MODELLED
(`s\exact.py`):

| | LEON mean / worst | HILL mean / worst | FIGHT mean / worst |
|---|---|---|---|
| Today (measured) | 27.48 / 35.02 | 37.35 / 43.72 | 26.01 / 36.14 |
| After E1 (clipper pre-reject) | 25.35 / 32.65 | 35.07 / 41.38 | 23.80 / 33.84 |
| After E2 (exact strip cull) | 23.04 / 28.95 | 31.69 / 37.64 | 21.60 / 30.11 |
| After E3 (characters' unused positions) | 22.19 / 28.10 | 31.30 / 37.19 | 20.30 / 28.81 |
| After W1 (no stage, asm) | 19.19 / 23.54 | 27.43 / 33.10 | 17.48 / 24.02 |
| After S1 (selection) | 17.28 / 21.19 | 27.16 / 32.37 | 15.62 / 21.58 |
| After C1 to C4 (character kernels) | **10.99 / 14.85** | **14.40 / 17.78** | **10.18 / 15.59** |

**The pixel-identical path is the floor this lane can show for today's content: about 10 to 11 ms mean on LEON and
FIGHT and 14.4 on the hill; 14.9 to 17.8 at the worst pictures.** No pixel-identical combination reaches the 14 ms row at
every worst picture. What closes it is a look choice (section 6b): on the hill the characters are the rest (two full
characters, about 7 ms after C1 to C4: back-face culling CB about -3.7 ms more on the hill (estimate), distance levels,
a light cap); on LEON and FIGHT the worst
pictures are world pictures (12,000 to 12,700 world corners: W2 removes 0.75 to 3.1 ms on the bench). Each needs the
owner's yes from its pixel count and still pair.

## 8. What the graphics chip could take over

The PowerVR does no transform, lighting or clipping, so it cannot take the big rows. What it can take:
- **Baked UV per corner**: the corner carries its final u, v and the CPU does no UV arithmetic (world: 4 instructions a
  corner; characters: 6): as two floats moved as one 64-bit pair (no look cost, 8 bytes a corner), or as the TA's 16-bit
  UV format (one word: the top half of each float, 7 bits of mantissa, so up to 2 texels of error near u = 1 on a 512
  texel atlas and worse on tiled world UVs: a look risk, only with a still pair). Part of options W1 and C2.
- **Back faces**: the TA culls them, but only after the CPU has transformed and sent them. Rejecting a strip by a baked
  normal cone before it is emitted (option C7) is the CPU half of that.
- **Translucency order** (autosort) and **fog** (table fog) are already the chip's.
- **Intensity vertices** (one float of light, the colour in the header): characters lit in one channel instead of three
  would cut the light kernel by about half again, but coloured lights would become white light: a look question, not
  proposed.
- **Vertex DMA** from main RAM instead of store-queue writes: on a console it would take the TA FIFO waits off the CPU;
  this tier charges neither, so it can be decided only on the console (deferred run).
- **Modifier volumes** for shadows (the bench already uses them); not in the E1 images.

## 9. Recommendation (for the integrator)

1. Keep the measurement: the DC lines, the census (DLV / Z) and the 2 ms control in every drawing lane's runs; judge each
   step on the three E1 scenes and the bench, mean and worst picture, on this tier, and give a pixel count for any step.
2. First stop invisible work (pixel-identical): E1 the clipper pre-reject (render only; about -2.1 to -2.3 ms), then E3
   (characters' unused positions and normals; -0.4 to -1.3).
3. Then E2, the exact strip cull from baked cones and bounds per strip group (about -2.2 to -3.4 ms): a pack-format change
   for lane eng-bake1, consumed by the renderer.
4. Then change the walking order: W1, the world walked without a stage, in one hand-scheduled loop over baked 16-byte
   float vertices and corners with baked UV (about -2.8 to -3.9 ms beyond E2; arm X already measured -1.3 in C).
5. Then the character kernels C1 to C4 (light kernel on ftrv, emission from corner records, weight sets, skin runs):
   about -5.4 to -12.8 ms, the hill's largest step; then S1 (selection, -1.9 on moving pictures).
6. Measure after each step: draw mean / p99 / worst, the census's dead shares (they must fall as predicted), the pixel
   count against the previous step's stills (0 for 6a steps, or explained).
7. Expected (estimate): LEON 11.0 / 14.9, FIGHT 10.2 / 15.6, HILL 14.4 / 17.8 ms; the row is not met at the worst
   pictures without a look choice: bring the owner W2, character levels in E1, character back-face culling and a light
   cap, each with its ms and its differing-pixel count, as look choices, never inside a speed step.
8. Receipts: every baked pack gets a receipt (SHA-256 of each input file, of each bake script at its git blob, and of
   the bake tool's version, mapped to the pack's own hash), written by the bake beside the pack (lane eng-bake1's
   `bake/`), printed into the disc MANIFEST by `tools/engine/build_console_disc.sh`, and checked by the integration
   gate (eng-int `GATE.md`): a pack whose receipt does not match the bake scripts at the ref being gated fails the gate
   (the hud_fix.py re-bake of H-015.7 is the kind of slip it catches).
9. Console questions this tier cannot answer, for the deferred run: the TA's intake at 14,000 to 27,000 vertices a
   picture (the dead corners cost it too), ISP time at 2 to 3 screens of opaque area, and whether the tier's 2.5 to 3.8x
   charge on hand-scheduled kernels holds.
10. Nothing in this lane changes the default picture; the lab arms (X, V, G, census) stay run-time arms.

## 10. Not done, not verified

- No console: every speed number is MODELLED on the calibrated tier, which does not charge the graphics chip's TA, ISP
  and TSP time, store-queue submission and the TA FIFO, cache misses, bus contention or disc time. At 14,000 to 27,000
  submitted vertices and 2 to 3 screens of opaque area a picture, the chip side is the first console risk this tier hides.
- Skinning in the E1 scenes is not repeated by an arm (the kernel is called from `services/actor_e1.inc`): its 0.59 us a
  position is the bench's (arm K) times the E1 counts.
- The near plane fix: the part of its cost that is not clipping (more world corners under the fixed plane) is not split
  between level choice and culling.
- Options E1 to E3, W1 (asm), S1, C1 to C8 and CB are estimates; only X, V, G and eng-look's content steps were run. The
  pixel-identical claims of E1, E2, E3 and S1 follow from what the chip discards; each still needs its pixel count when
  built. X in C differs by 0 to 2 pixels a still.
- Look pairs exist for the bench only (G, X, W2, W3, L0); G, CB, C5, C8 and character levels in the E1 images have no E1
  pair. The bench's drawing is not repeatable to the pixel from window to window (section 6): not diagnosed.
- fccycles.py over-charges loops with many conditional branches by 20 to 50% against the measured arm and failed to
  predict arm V (it predicted -25%, V measured +3 to +5%): it compares loops, it does not rank options alone.
- The PC hardware model (tools/hwmodel) was not run.
- Runner fault on 10:03 (this lane's): two of its own runs entered slot fly1 together; fly1's emu.cfg was restored from
  fly2's untouched original (identical but for the two lines); the runner now takes its lease by exclusive create.
- d3's FIGHT and d6's BENCH were marked FAILED by the selector ("no end line in the report"): this lane's lines pushed
  their reports over the console loop's cap (about 105.6 KB). Fixed (per-picture lines carry the trace prefix; census
  counters print only when the census ran); the serial logs were complete and are what was read. FIGHT's report is
  about 96 KB with this lane's lines (93.6 KB before): 9% under the cap.
