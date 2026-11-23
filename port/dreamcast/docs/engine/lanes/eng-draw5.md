# eng-draw5 hand-back, 2026-11-22

**Status: finished, unaudited** (items 1, 2, 5, 6 answered; item 3 left with evidence; item 4 built, its run and sheet
not finished - see "Not done"). Branch `lane/eng-draw5` from `lane/eng-draw4` e2092e728. Lane document:
`port/dreamcast/docs/engine/lanes/eng-draw5.md` (this text). Evidence: `E:\RE4DC-Lanes\eng-draw5\` runs\ (r0a r0b base,
r2a r2b step 2, rst LSTAG, r3 base of the arms' image, rlx LVLX, plus any of rlv rsk rlo rlh rpx that finished after
this was written: their `drawcost.txt` / serial are in place), s\ (scripts), STATUS.md, DELETED.txt.

Tier of every speed number: **MODELLED (console-build dynarec at 70 MHz, calibrated on the old port)**, `Sh4Clock = 70`,
`Dynarec.Enabled = yes` (each run's `emu.cfg.used`), one session 2026-11-22 09:36-11:00. Engine runs: fly1 (base and step
2 and LSTAG) and fly2 (the arms' image d3 and its arms; each arm against its own base on the same slot). The standard
build reads the engine 3 to 10% kinder. What the model cannot see: the graphics chip (TA intake, ISP/TSP fill and sort),
store-queue submission time (SQ stores charged as instructions), cache and bus contention, disc timing. Pixel counts are
Flycast's. Budget row: drawing 14 ms; no scene meets it.

## Item 1: the measuring stick (old port, same scenes, same tier)

The old port's own per-model timer (PROP_PROF) does not build any more (`re4dc_otp_now_us`, `re4dc_stream_model_bytes_now`
are defined nowhere in the tree); fixing it would be changing the old port, so it was not used. Its other counter was:
the **PC sampler** (PC_SAMPLER=1, TMU1 at 1000 Hz, ring read by `tools/flycast-harness/read_pcs.py`). Image `oldS`: the
release recipe's warp twin as eng-cmp1's image A (CH2 + T15REC, DBG_WARP=1, PACE_HOLD_LOG=2, GAME_TICK_LOG=1) plus
PC_SAMPLER=1 (ELF sha256 386e35ce550a71b2...), built from this worktree's old-port source, never tuned. Runs vil-S1, hill-S1,
fight-S1 on fly1 at 70 MHz, eng-cmp1's fixtures and windows (game frames 225-824, 413-1012, 225-824). Reader
`s\pcs_split.py`: a group's share of the window's samples x the window's time a shown picture (the game's own iteration
totals / pictures shown). Check: samples a second 965 / 1020 / 792 against 1000 (the reader lost 8% / 0% / 23% of
records in gaps: shares assume the losses fall evenly). The old port shows 384 / 300 / 325 pictures in the window at
60.0 / 87.6 / 63.3 ms a picture (eng-cmp1: 54.9 / 86.6 / 62.4 ms work, 16.4 / 11.3 / 15.6 a second).

| ms a shown picture, MODELLED | Village route (LEON) | Hill (HILL) | Fight (FIGHT) |
|---|---|---|---|
| **Old port** skinning (`re4dc_avk_pos_*`, `sk1`, coarse skin) | 3.11 | 8.21 | 2.59 |
| Old port lighting (`re4dc_avk_light_*`) | 1.95 | 2.69 | 1.41 |
| Old port classes, set-up, LOD choice and emission (`native_actor_fast.cpp`; its meshlet copy `Part::whole` alone 1.02 / 2.45 / 0.61) | 4.48 | 5.54 | 3.30 |
| Old port coarse actor / Ganado submission | 1.05 | 2.31 | 1.07 |
| **Old port characters, the four rows** | **10.6** | **18.8** | **8.4** |
| Old port matrix kernels shared with the world (`pwc`, `pmc`, `MTXConcat`; not split) | 4.10 | 5.11 | 2.38 |
| **Engine characters** (base r0a, same session) | **11.73** | **23.16** | **9.97** |
| Engine skinning / lighting / emission / weight sets (eng-draw4 per-kernel arms) | 2.16 / 4.23 / 4.10 / 1.10 | 4.06 / 7.47 / 8.62 / 2.36 | 1.89 / 3.08 / 3.13 / 1.01 |

Scope (not like for like): the old port draws Leon and the Ganados with its PS2 detail levels (its `Converter::levels`
runs every picture), the village Ganados are alive 100 m away (culled), on the hill four Ganados are alive 26 m away
besides Leon and Ashley; the engine draws Leon (and Ashley) at full detail and has no Ganados in LEON and HILL. Per
phase: the old port's **lighting is 2 to 3 times cheaper** (at most 3 lights, one FTRV a normal) and its emission and
set-up together are cheaper than the engine's emission alone; its skinning is dearer (it skins one record per
position-normal-uv combination). So items 3 and 4 were not skipped on cost grounds.

## Item 2: skinning without the outputs nobody reads (exact) - taken

`m1_avk_pos_skin_xy` (`render/avk_xy_sh4.inc`, included by `render/stage_sh4.S`): the released kernel generated again by
its own tool (`tools/game30/avk/mkavk.py`, imported unchanged; it reproduces `avk_sh4.S` byte for byte) from a template
without the texture-coordinate lines (`render/gen/pos.tpl`, `render/gen/mkavk_xy.py`): 29.50 model cycles a vertex
against 37.50. Commit 92f67e405.

| characters mean / p99 / worst ms | LEON | HILL | FIGHT |
|---|---|---|---|
| base r0a | 11.73 / 14.35 / 14.53 | 23.16 / 26.49 / 28.88 | 9.97 / 14.37 / 16.78 |
| step 2 r2a | **11.24 / 11.59 / 14.06** | **22.31 / 25.61 / 27.88** | **9.57 / 13.78 / 16.01** |
| drawing row (mean / p99 / worst) base -> step 2 | 25.46/30.58/30.70 -> 25.00/30.12/30.30 | 34.96/40.29/40.44 -> 34.10/39.43/39.59 | 22.96/30.11/30.26 -> 22.55/29.60/29.73 |

Saving -0.49 / -0.85 / -0.40 ms (the estimate was -0.7 / -1.3 / -0.6). Pixels: on the 52 of 59 stills where both the
base's two runs (r0a, r0b) and step 2's two runs (r2a, r2b) repeat themselves, **52 identical** (`s\floor4.py`). The
stills that do not repeat differ by 1 to 13 px run to run on the same disc (r2a vs r2b: 8 stills), as eng-draw4 found.
Controls: the 2 ms arm reads +2.005 ms (PASS, r2a set B); the pixel comparison's control PIXCTL (run rpx, one blue step
on every character colour) FAILS as it must: E1 0 of 34 stills identical, FIGHTS 3 of 19 (s\cmp.py r2a rpx r2b).

**Skinning's shares (H-038)**, MODELLED, LEON / HILL / FIGHT: the blend (weight sets: blend, projection into the kernel's
matrix, per-set light terms) 1.10 / 2.36 / 1.01; the position transform 2.16 / 4.06 / 1.89 before this step, of which the
unused u, v outputs were 0.49 / 0.85 / 0.40 (now gone), the transform itself 1.67 / 3.21 / 1.49. Skinning redone the
engine's way in C on SH4ZAM: lab arm SKC (`render/actor_skin.inc`, `m1_skin_pos_c`: FTRV and FSRRA through SH4ZAM, the
part's stream read in place, no records, no u, v). Its run rsk against r3 (same image, fly2) is the C figure; see the
table at the end if it finished. Assembly stays only if it beats the C on mean and p99.
Layout for the successor (eng-load2's finding): both kernels use exactly the order `native_actor_open` builds (each part's
positions and normals sorted by weight set, the strip corners re-indexed in place); nothing else is needed, so that
work can move to the bake unchanged and the pack carry the final order.

## Item 3: the old emitter on a baked layout - left (taken as an idea only, not built)

Under H-035 only the idea could come in. The old emitter is cheaper per corner because each corner is a copy of a
pre-built 32-byte vertex (u, v already floats, colour already in place); the price is paid upstream: the old port skins
and lights one record per position-normal-uv combination (its skinning above is the dearer phase). In the engine's
format the separable idea is "u, v converted at load": it needs 12-byte corners (strip memory +50%; FIGHT is already
over its memory line: arena margin -20,480 B on the base) or 16-bit u, v (not exact: 7-bit mantissa). Neither fits
the engine as it is, so item 3 was not built.

## Item 4: the released lighting as a look arm (LOLD) - built, off by default

`render/actor_light_old.inc` + `m1_avk_light_skin_n16w` (the released kernel generated by its own tool, colour store
stride 4 for the engine's colour array; 34.50 model cycles a normal). At most 3 lights (LCAP's pick), directions and
distance terms once a character at the object position, FTRV sum, clamp after the material scale. Boot file LOLD.
Disc dlold; run rlo queued last on fly2 (see "Not done").

## Item 5: lighting every other picture, staggered (LSTAG) - not landed, stays an arm

Boot file LSTAG (`services/actor_e1.inc`): each character lights on the pictures of its own parity. Run rst against r2a
(same image 92f67e405, fly1):

| characters mean / p99 / worst | LEON | HILL | FIGHT |
|---|---|---|---|
| step 2 (r2a) | 11.24 / 11.59 / 14.06 | 22.31 / 25.61 / 27.88 | 9.57 / 13.78 / 16.01 |
| LSTAG (rst) | 9.07 / 11.77 / 14.26 | 17.98 / 25.38 / 27.39 | 8.08 / 13.56 / 16.95 |

| LHALF (rlh, same image, same session) | 9.07 / 11.97 / 14.46 | 17.98 / 25.58 / 25.65 | 8.06 / 14.65 / 15.06 |

Against LHALF, staggering keeps the mean and lowers p99 by 0.20 / 0.20 / 1.09 ms (FIGHT's worst picture is 1.9 ms higher).
Against today, the mean falls 2.2 / 4.3 / 1.5 ms but **p99 barely moves (+0.18 / -0.23 / -0.22) and the worst picture does not**: the
worst pictures are set by skinning and emission peaks, not by the lighting being in phase. Memory: FIGHT's arena
margin -32,768 B against -20,480 B on the base (12,288 B of colour buffers; this lane is not on lane/eng-mem2's base:
bytes stated, not checked against its MEMORY_MAP.md). Stills: up to 29,621 px (FIGHTS 360) against the base, eng-draw4's
approved LHALF sheet up to 30,778 px. Because it does not help p99 and costs memory in the one scene that is over its
line, it is **not landed**; it stays a lab arm.

## Item 6: why a Ganado differs under LVL - explained; LVL not landed until the fault is fixed

The level drawn is not the cause: arm **LVLX** (LVL's pick runs, the base model is always drawn) reproduces eng-draw4's
FIGHTS differences to the pixel against its own base (r3 vs rlx: 1,087 / 1,742 / 345 / 1,589 / 806 / 2,098 px at pictures
1, 40, 80, 120, 400, 440; E1 stills within the run-to-run floor). The one drawing difference LVL makes that LVLX keeps is
in the translucent call: `e1_actor_pass_one` draws a character's role-8 parts from `e1_lvl_slot[slot]` (the model of the
LAST opaque call in that slot) under LVL, and from the caller's model without it. Every character but Leon shares slot 1
(its part states, projected positions and colours), so for every Ganado but the last one drawn, the translucent parts are
drawn from another character's data in both cases - a pre-existing fault of the shared slot, which LVL only changes the
look of. The new log lines also show the old counter was wrong to say "no Ganado changed level": the per-model picks
(`E1 ARM LVL model` lines) put FIGHT's Ganado models at levels 1 to 3 and rigid on hundreds of pictures; the variant
was refused when its bone count exceeds the skeleton's (`cat->m[v].h[0] <= bones`) and the counter then logs level 0.
Fix needed (not done here, memory): per-character translucent data (part states and pools) for slot 1, or drawing each
character's role-8 parts from its own buffers. LVL should land after that fix.

## Old-port pieces considered (H-035, H-036, H-038)
- Skinning routine `avk_sh4.S`: **taken as a routine** (generated by its own tool without u, v); open to the C version (SKC).
- Light kernel `re4dc_avk_light_skin_n16`: **taken as a routine for a look arm only** (LOLD), not the engine's lighting.
- Meshlet vertex-cache layout and emitter (`native_actor_fast.cpp`): **left** (structure; the idea does not fit the
  engine's memory or exactness, item 3).
- PROP_PROF timer: **left** (broken in the old tree). PC sampler: **used as a measuring tool** (not lifted).

## Files
Owned: `render/gen/*` (new), `render/avk_xy_sh4.inc` (new, generated), `render/actor_light_old.inc` (new),
`render/actor_skin.inc` (new), `render/stage_sh4.S`, `render/native_actor.inc`, `services/actor_e1.inc` (eng-draw4's
characters file, as before). No stubs, no original unit linked: default image check_link PASS (407 kept, SERVICE 0); FIGHT
links. Commits 92f67e405, 7a7105b0b.
