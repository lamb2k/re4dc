# eng-mem2 hand-back (2026-11-22): the memory train to the gate

**Status: finished, unaudited.** DOOR is not OK yet: one item of five is left (item 2). Branch `lane/eng-mem2`, head on the last line. It holds
lane/eng-mem1 13ca87c05 (skel1, skel2, load1, snd1 and the map), origin/engine fd79cc1db (merged with no conflicts), and
four commits of this lane. Lane document: `port/dreamcast/docs/engine/lanes/eng-mem2.md` (this text).

Tiers: every disc result is **Flycast** (plain build, slots std1 and std2: function runs). Nothing here is a speed
claim. Nothing ran on a console.

## Lead
1. **The d6 boot hang: the cause was neither the farm pack nor the lit-cache release. It was the schedule file's size.**
   - The selector read SCENES.TXT in one call into an aligned buffer, so fs_iso9660 streamed it by DMA.
   - The file's last bytes under 32 then come through the driver's single non-blocking 32-byte stream request.
   - When that request ends the stream (size mod 2048 between 2017 and 2047), plain Flycast never returns.
   - d6's SCENES.TXT is 2,045 B because of the CDOORRD line. d4's had CSNDSLOW there and was 1,887 B.
   - Fixed in the selector (a7aa266d4), with a disc control.
2. **skent shot-ganado: the engine was wrong, not the row.** The native blend table read an uninitialised matrix when a
   parent's world is singular, which made some bones NaN. Fixed (8be5927f8). skent_check now ends every row as it must.
3. **DOOR:**
   - Both loads complete, and the weapon is drawn in the farm (260 of 260 pictures, with eng-mem1's R103 pack).
   - The round trip returns these exactly: arena 692,704 B, video memory 2,639,720 B, collision pieces 2, skeleton
     tables 2.
   - The KOS heap was 200 B over. Found and fixed: a 104 B block lost at every renderer open, and a free() of a static
     object (32e5cc5d9).
   - It is still **16 B over** (5,738,088 -> 5,738,104). DOOR therefore still FAILS on "round trip LEAK kos-used". Not
     found; see "Not done".

## Per item
1. **Boot hang** (runs\sb-std1, sa-std1, sc-std1, d1-std2, d2-std1; SCENES and MANIFEST of the deleted discs are in runs\):
   - Split as briefed, both on std1, both hung at boot:
     - sb = d4's head 8d0fe36e0 plus eng-mem1's R103.PAK;
     - sa = fa2b14aba (the lit-cache release) with the shared FARM.PAK.
   - Neither change causes it. Both hang after "fs_iso9660: disc change detected", with no CDISC START.
   - sc = sa with d4's scene list (CSNDSLOW in place of CDOORRD) boots.
   - On sa and sb, the ISO directory and the sectors the selector reads have the same shape (s\isols.py on track03).
   - What differs is SCENES.TXT: 2,045 B hangs, 1,887 B boots.
   - Fix in `engine/loader/selector.c`, `disc_read`:
     - every whole sector but the last is read by the stream, which then stops at the close with a sector still in it;
     - the last sector is read through the driver's sector cache (an odd destination takes iso_read's cached path);
     - the same is used for the program images.
   - Old port: t15/int met this same request on the console and made it blocking (`game/platform/dvd_read_safe.cpp`,
     DISC_READ_VERIFY: "fs_iso9660's one non-blocking request (32 bytes) is made blocking"). Here the request is not made
     at all (see "Lifted from the old port").
   - Disc control in the repository: `build_console_disc.sh --plan-control sectorend` pads SCENES.TXT to 2045 mod 2048.
     The fixed selector must read it and run every scene.
   - Fixed selector, d1 (sectorend, 4,093 B): booted.
   - Fixed selector, d2 (the d6 schedule, 2,045 B with nothing added): booted, all 8 scenes ran.
   - The failing control: the selector of 8d0fe36e0 / fa2b14aba on the same schedule hung on every run: d6 three times
     (std1 twice, std2 once, eng-mem1), sa and sb (std1, this lane).
2. **DOOR, CDOORLK, CDOORRD** on d2 (head e8ccca56d, std1, Flycast plain):
   - DOOR FAILED "door: round trip LEAK kos-used". Both loads done (67.7 s and 54.7 s). The other marks are exact:
     arena 692,704, VRAM 2,639,720, col-pieces 2, skel-tables 2. Weapon visible 260, drawn 260, not-drawable 0.
     Disc in play: 0 opens.
   - Controls, each FAILED for its own reason:
     - CDOORLK: LEAK (the kept block);
     - CDOORPK: "E1 load: missing /cd/st1/r103.arc";
     - CDOORRD: "door: disc in play: opens 0 reads 1 sectors 1".
   - Tracking the +200 B:
     - Tool: a debug build that logs each KOS heap block's caller (local branch only, not pushed; ev\dbg1-heap-blocks.txt).
     - Finding: `render/native_scene.inc:395` callocs state[0] (104 B) at every open.
     - Cause: core/draw_e1.c then replaced state[0] with the camera service's record, so the block was lost, and
       native_close passed the static record to free().
     - Fix, in `core/draw_e1.c`: the block is freed after the open, and the slot is emptied before native_release.
     - Result: +200 -> +16.
   - The 16 B:
     - The first village visit keeps 48 B past its leave (LOADSTEP leave.collision+renderer 1,601,552 against
       setup.camera-view 1,601,504).
     - The farm visit returns exactly (1,587,472 -> 1,587,472).
     - The second village open takes 32 B less than the first.
     - The second dump (dbg2) lost part of its serial lines, so it does not settle which block it is.
3. **skent shot-ganado** (ev\suites-a\skent_check, ev\skent):
   - The failing bones: actor 4, bones 6 and 12, NaN in the native build at ticks 164, 258, 276 and 316. The reference
     has a zero-scaled matrix there.
   - These ticks became reachable through eng-fix1's routine-byte correction: the shot Ganado's routine 0x10 now runs.
   - Traced with a NaN check build (not kept) to MotionMove's blend table:
     - `PSMTXInverse` of a singular parent leaves `inv2` as it was;
     - in the native this is the original's own logic (`motion.cpp`: `Mtx inv` declared once for the loop);
     - on the first entry the matrix is uninitialised: NaN here, finite stack bytes on the PC reference.
   - Fix, in `services/skeleton/skel.cpp`: `inv2` starts as the identity, so a later entry keeps the previous entry's
     inverse, as in the original.
   - The row's expectation stands, nothing was widened. skent_check: shot-ganado bones 82,880 of 82,880 equal, log
     identical 3,489 lines.
   - Its controls (entflag, entpost, entpose, enthist, chainmid, colkeep, effect) still FAIL as they must.
4. **Clean disc d2** (LEON, HILL, FIGHT, BOSS, DOOR, CDOORLK, CDOORPK, CDOORRD; Flycast plain std1):
   - LEON, HILL, FIGHT and BOSS are OK. DOOR is as in item 2. 4 of 8 OK.
   - After play, KOS heap to the arena:

     | Scene | KOS heap to the arena | Other |
     |---|---|---|
     | LEON | 4,784,128 B | |
     | HILL | 4,939,776 B | handgun 728 / 728 pictures |
     | FIGHT | 299,008 B | |
     | BOSS | 1,994,752 B | |

   - PC suites on e8ccca56d (ev\suites-a), every row as it must:
     - svc_controls, camcheck, refctl, controls (18), outcome_controls (35);
     - aim_check, e2check, e2bcheck, e2c_check, skent_check, colmap_check, speed_controls;
     - door_check PASS, with its controls early20 and at0 FAIL; two reference runs identical.
   - Link check, SERVICE functions per image (built at e8ccca56d), before and after the same:

     | Image | Original functions kept | SERVICE |
     |---|---|---|
     | default | 615 | 0 |
     | FIGHT=1 | 1049 | 30 |
     | BOSS=1 | 709 | 0 |
     | SENDABLE=1 | 615 | 0 |

     FIGHT is 30 as on origin/engine (r101_callGanadoVoice and the cam_extra split rows).
5. **The farm pack** stays at `E:\RE4DC-Lanes\eng-mem1\packs\R103.PAK` with its RECEIPT.txt (not touched).
   `build_console_disc.sh` now takes it by option (`--r103 <pack> <visibility>`). The default stays the shared set's
   FARM.PAK/VIS, so no default points into a lane folder.

## Checks and their controls (in the repository)
- `--plan-control sectorend` (build_console_disc.sh): the fixed selector boots it. The failing control is the old
  selector on that schedule, which hangs at boot (sa, sb).
- skent_check (unchanged): every row as it must. The pre-fix run (eng-mem1 ev\suites-b) is the failing case:
  `skent shot-ganado` FAIL (MUST PASS), 8 bone-ticks at 1e+30.
- DOOR's round trip check (unchanged): it caught the +200 B, and now catches the +16 B.

## Lifted from the old port (the integrator's steer, H-032)
- What was lifted is the cause and the known edge, from t15/int `game/platform/dvd_read_safe.cpp`: fs_iso9660's
  non-blocking 32-byte stream request (DISC_READ_VERIFY), and DISC_READ_FALLBACK=2's "no stream for the last bytes"
  idea. That file's wrappers were not copied.
- The selector now never ends a stream through that request.
- For the engine images the same edge stays open (request 1).
- The KOS disc patches and the TOC fix are already in the engine (SALVAGE rows 1 and 2).

## Files touched outside the owned list
| File | What changed | Why |
|---|---|---|
| `engine/core/draw_e1.c` | 5 lines: the free after open, the slot emptied at close, stdlib.h | DOOR round trip: a lost block and a free() of a static object |
| `engine/services/skeleton/skel.cpp` | 1 line plus a comment: inv2 starts as the identity | brief item 3, "fix the engine" |

`engine/loader/selector.c` and `tools/engine/build_console_disc.sh` are the map owner's under H-032.

## Requests
1. **Disc read owner** (SALVAGE row 3, `core/play_files.c`, kosfix): the engine images read files with fs_read too.
   - The risk: any file whose size mod 2048 is 2017 to 2047, read in one aligned call, can stop the same way.
   - Suggested fix: lift DISC_READ_VERIFY's blocking 32-byte request (a `--wrap=cdrom_stream_request`, which the images
     already wrap), or a fs_iso9660 patch in `port/dreamcast/patches`.
2. **Reference owner (refctl):** the original MotionMove blend table reads `inv` uninitialised under a singular parent.
   On the PC reference the result depends on stack bytes. It is a candidate correction for the reference, with
   refctl's switchable build.
3. **Integration lane:**
   - eng-mem1's R103.PAK into a shared pack set;
   - discs still need eng-skel2's baked archives (PRISTINE=/root/work/lanes/eng-skel2-data/pristine-colb).

## Not done / not verified
- DOOR OK: the last 16 B of the round trip. Next step: a block log that keeps every line, comparing the first visit's
  leave with the second open.
- No calibrated (fly1/fly2) runs: no sound or speed question in this lane.
- No console.

