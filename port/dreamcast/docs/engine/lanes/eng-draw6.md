# eng-draw6 hand-back, 2026-11-23

**Status: finished, unaudited.** Branch `lane/eng-draw6` (from `lane/eng-draw5` bd77d8edd), head: the commit that carries this document, origin/engine
8b68c925d merged. Lane document: `port/dreamcast/docs/engine/lanes/eng-draw6.md` (this text). Evidence:
`E:\RE4DC-Lanes\eng-draw6\` runs\ (rA1 rL timing, rV census, sA1 sA2 sA3 base, sL1 levels, sP2 control, sN1 the
image after the removal: stills; sP1-killed is the interrupted first control), s\ (scripts), sheets\LOLD-vs-engine.jpg, STATUS.md, DELETED.txt.

**Headline: character detail levels are out of the build.** Their stills check failed, first with one floor run and
then (integrator's ruling 2026-11-23) against the gate's two-base-run floor. So, as ruled, the level code came out of
the default build entirely, with no arm left that is off (commit bd02b883a). The image with that change draws the same
stills as the base on 49 of 50 judged stills (the 50th is 1 px, one colour step). The look sheet LOLD-vs-engine.jpg
waits for the owner; the look is unchanged.

Tier of every speed number: **MODELLED (console-build dynarec at 70 MHz, calibrated on the old port)**, fly2,
`Sh4Clock = 70`, `Dynarec.Enabled = yes` (each run's `emu.cfg.used`). Counts and stills without a tier are plain
Flycast counts, not speed. What the model cannot see: the graphics chip (TA intake, ISP/TSP fill and sort), store-queue
submission time, cache and bus contention, disc timing. Budget row: drawing 14 ms; no scene meets it.

## Item 1: each character's own data (the eng-draw5 item 6 fault)

- Finding: only Leon's models (catalogue 0 and his levels) have translucent (role 8) parts in the fight, hill and
  cross packs (`s\roles.py` on bake/native_models.py output); the translucent call is Leon's alone and reads his own
  slot 0. The shared slot-1 data never reached the screen. LVL's FIGHTS differences came from the fight's own Ganado
  pick (fight_draw.inc content_pick) that LVL switched on through CS_LEVELS = 3.
- Change (f3ddc7c32): the two slots' positions, colours and outcodes (303,104 B of .bss) are sized at pack open to the
  catalogue (FIGHT 161,248 B, HILL 252,968 B), given back at close; a model larger than its slot is refused and
  counted (guard `actor_pool_refused`, 0); a translucent model outside slot 0 is counted (guard `actor_trans_other`, 0).
- **Bytes for the memory map's owner:** the .bss drops by 303,104 B; the heap takes 161,248 B (FIGHT) / 252,968 B
  (HILL) while a pack is open.
- FIGHT arena margin after play: **+544,768 B** (rA1, rL; was -28,672 B on eng-draw5's r3/rlv/rsk/rlo). LEON
  4,853,760 B, HILL 4,911,104 B. (Plain counts from the serial `CDISC SUM` line, on the fly2 runs.)
- Counter (asked vs drawn), rL: LEON 0>0 1,099, 1>1 180; HILL 0>0 1,335, 1>1 583; asked level not drawn 0, pool guard 0.
  FIGHT's line is lost to the tick-log overflow (below). The counter came out with the level code (bd02b883a); the
  pool guards stay as the "E1 POOL guards" line (sN1: 0 and 0).

## Item 2: skinning kernel

The generated assembly stays; the C arm SKC is deleted (f3ddc7c32). r3 vs rsk (eng-draw5, same image, fly2, one
session), MODELLED: C slower by 0.45 / 0.86 / 0.39 ms mean and 0.45 / 0.84 / 0.54 ms p99 (LEON / HILL / FIGHT), and
worse on the worst picture in all three.

## Item 3: detail levels (LVL) - stills check FAILED, level code removed

Speed pair, MODELLED, characters' drawing mean / p99 / worst ms, rA1 (levels off) -> rL (levels on), f3ddc7c32:

| scene | levels off (rA1) | levels on (rL) |
|---|---|---|
| LEON  | 11.40 / 13.02 / 14.21 | 11.30 / 13.62 / 14.24 |
| HILL  | 22.61 / 26.06 / 28.41 | 20.82 / 24.13 / 26.57 |
| FIGHT | 9.71 / 14.04 / 16.30 | 9.65 / 13.81 / 16.06 |

Stills check (`tools/engine/lvlcheck.py sA1 sL1 sA2`: base, levels, base again as the run-to-run floor; plain counts):
59 stills in both runs, 10 left out on the floor, 49 compared, 25 with a level change. Inside the boxes of characters
drawn at another level 194,840 differing pixels; **outside 23 on 3 stills: FAIL** - LEONS (0,1,240) 1 px, FIGHTS
(1,0,240) 2 px, FIGHTS (1,0,360) 20 px (no character changed level on that still). Every outside pixel is one colour
step (largest difference 4, 8, 9 on 0-255), scattered over world pixels across the screen. Base against base (sA1 vs
sA2) shows the same kind of difference on 10 stills (1 to 54 px, largest 9). Reading: most likely run-to-run noise the
single floor run did not catch, not a level fault; but the rule was "fails with the floor applied: levels off", and the
lane did not loosen the check; levels went back to an off arm (09fea1973) pending a ruling.

**Integrator's ruling (2026-11-23) and its result.** A third base run sA3 of the same build (bd5dd878d, LVL0; disc sA
rebuilt with that commit's own disc script, the same m1_state addresses as sA1) gave the gate's two-base-run floor
(`eng-int\s\stillsfloor.py` rule: a picture where the two base runs differ is not judged; no tolerance). `lvlcheck.py`
now takes several base runs for the floor. Results (plain counts):

| check | floor stills | compared | outside the changed boxes | verdict |
|---|---|---|---|---|
| lvlcheck sA2 sL1 sA3 (base sA2, floor sA3) | 9 | 50 | 22 px: FIGHTS 240 (2), FIGHTS 360 (20) | FAIL |
| lvlcheck sA1 sL1 sA2 sA3 (floor: any base differs) | 14 | 45 | 22 px, the same two stills | FAIL |
| control lvlcheck sA2 sP2 sA3 (PIXCTL) | 9 | 50 | 371,958 px | FAIL, as it must |
| control lvlcheck sA1 sP2 sA2 sA3 | 14 | 45 | 319,487 px | FAIL, as it must |

The base runs sA2 and sA3 agree to the pixel on FIGHTS 240 and 360, and the levels run differs there outside the
changed characters' boxes. FIGHTS 360 has no character at another level at all. So the outside pixels are not within
the two-run floor, and under ruling 2 the level code came out (bd02b883a). Removed: the LVL boot file, the E1 pass's
own pick, the asked/drawn counter, the LVLBOX lines, and content_actor.inc's caller marks (back to bd77d8edd's file).
Kept: the slot pools sized at pack open and their two guards (one "E1 POOL guards" line). Every character draws its
base model, as the LVL0 arm did. Why they fail is not found: FIGHTS 360's 20 pixels are one-step world pixels spread
over the screen, on a still with no character at another level, so something from the levels persists past the
character's own pixels. The lane did not chase it further because the ruling takes the code out; a later level design
should start from this still.

A note on the floor itself: by the gate's own tool, the base run sA1 fails against the pair sA2/sA3 (`stillsfloor.py
sA1 sA2 sA3`: 5 judged FIGHTS stills differ, 2 to 37 px, each one colour step). Three runs of one disc are not
pixel-stable on FIGHTS in this tier, so a two-run floor rejects about 1 in 10 FIGHTS stills of a same-disc run. That
is for the gate's owner; it does not change this lane's outcome, which fails on stills where the base runs agree.

**The image after the removal** (disc sN, head bd02b883a with origin/engine merged, run sN1 on fly2):
`stillsfloor.py sN1 sA2 sA3`: LEONS 17/17 identical, HILLS 15/15 identical (4 on the floor), FIGHTS 17 of 18 identical
(5 on the floor), 1 still differs by 1 px (FIGHTS 520, pixel 637,379, one red step 123 to 131): the gate's exit 1, the
same one-step kind as sA1 against sA2/sA3. All three scenes OK, disc in play 0 reads, POOL guards 0 and 0.

Control (disc sP: base plus PIXCTL, one blue step on every character colour, levels off), run sP2 on fly2:
both checks FAIL as they must. `lvlcheck.py sA1 sP2 sA2`: 49 compared, 0 with a level change, 349,923 pixels outside
any changed box (worst 13,540 at LEONS (0,0,240)), exit 1. `s\cmp.py sA1 sP2 sA2`: E1 34 compared, 0 identical, 224,786
px; FIGHT 15 compared, 3 identical, 125,137 px; exit 1. (Plain counts; sP2 is the re-run of the control killed on
2026-11-22, kept as runs\sP1-killed.) The serial confirms the arm: "E1 PIXCTL: control, one blue step flipped on every
character colour".

## Item 4: sheet for the owner

`sheets\LOLD-vs-engine.jpg`: the released (old port) lighting LOLD beside the engine's, one variable. Modelled cost,
characters' drawing (r3 vs rlo, eng-draw5 image, fly2): LOLD saves 2.72 / 4.63 / 1.92 ms mean and 2.78 / 5.54 / 2.72 ms p99
(LEON / HILL / FIGHT), MODELLED. Waits for the owner; the look is not changed. LSTAG stays an arm, no sheet.

## Item 5: fill cost (estimate from the code; the model cannot see the graphics chip)

Census rV (std1, plain Flycast, counts only), screen area in pixels a picture, mean (worst); time against ISP 3.2 Gpx/s
and TSP 100 Mpx/s at 100 MHz. **Estimate from the code**, not a measurement:

| scene | world opaque | characters | translucent | estimate ms a picture |
|---|---|---|---|---|
| LEON  | 570,805 (1,151,242) | 226,410 (586,312) | 221,769 (324,313) | about 5.6 (7.0) |
| HILL  | 563,913 (579,632) | 143,261 (322,703) | 301,963 (490,146) | about 6.4 (8.4) |
| FIGHT | 531,238 (651,311) | 246,822 (383,710) | 272,362 (410,711) | about 6.1 (7.6) |

The graphics chip works in parallel with the CPU on the previous picture, so this is a separate row from the CPU's
drawing time; it fits a 33 ms picture with room on all three.

## Images (head bd02b883a and later, origin/engine 8b68c925d merged, make -j2)

default PASS (615 allowed, 0 SERVICE); SENDABLE PASS (615, 0); BOSS PASS (709, 0); FIGHT links, check_link FAIL
with SERVICE 10 (4,476 B, em10's ten functions), the same as origin/engine's gate base-c8642d132 (not risen).
Text sizes after the removal: default 711,596 B (was 714,796), FIGHT 995,208 B (was 997,912).

## Requests for other owners

- Memory map owner: FIGHT's room carve is refused every tick (SVCMEM region 8cf40000-8cfc0000, carve fails 174,592)
  and floods the tick log (about 1,596 lines dropped), so FIGHT's timing record fails "no E1 FIELDS line". Same on the
  integration lane's base-c8642d132 FIGHTS; not this lane's.
- core/draw_e1.c owner: CS_LEVELS starts at 0 in E1 images and nothing in E1 sets it now; the fight's own Ganado pick
  (fight_draw.inc content_pick) and the bench's level steps stay in their images, inert at step 0 in E1/FIGHT.

- Integration gate owner (stillsfloor.py): on FIGHTS in this tier a third run of the same disc fails the two-run
  floor (sA1 against sA2/sA3: 5 stills, 2 to 37 px, each one colour step); the new head's sN1 fails it by 1 px. A
  same-disc run fails the rule about 1 still in 10 on FIGHTS.

## Old-port parts considered

- Skinning routine: left (not gold, per the owner 2026-11-22); the engine's generated assembly kernel won on numbers.
- Released lighting (LOLD): built as a look arm only, for the owner's sheet; taken or left by the owner's choice.
- Slot buffer sizing: none in the old port fits (its per-model buffers follow its own layout); written the engine's way.

## Housekeeping

- Commits f3ddc7c32 and bd5dd878d (pushed 2026-11-22) carry the author "eng-draw6 <noreply@anthropic.com>", not
  lamb2k; left as they are (no force push). Commits from 09fea1973 on are authored lamb2k.
- Test discs deleted after use (sA, sN on 2026-11-23 too): see DELETED.txt. No Flycast, lease or keeper of this lane left running.
