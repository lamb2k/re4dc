# eng-mem1 hand-back (2026-11-22): one owner for the main memory map, and the four lanes it takes in

**Status: finished, unaudited** (DOOR not yet OK: see 2). Branch `lane/eng-mem1`, head: last line. One train for the
integration lane: eng-skel1 (6e16d0037), eng-skel2 (e590e4b2e), eng-load1 (eac123767), eng-snd1 (707ebda0d),
origin/engine 28ad25ce7, and this lane's commits. Lane document `port/dreamcast/docs/engine/lanes/eng-mem1.md` (this
text); the map `port/dreamcast/docs/engine/MEMORY_MAP.md`.

Tiers: memory figures and scene results are **Flycast** (plain build, slots std1 / std2: function runs). Sound costs are
**MODELLED (console-build dynarec at 70 MHz, calibrated on the old port)**, slot fly2 (`Dynarec.Enabled = yes`,
`Sh4Clock = 70`, runs\c5-fly2\slot.txt). Nothing ran on a console.

## Lead
1. **The farm's figure: both were right; they count different things.** The renderer's resident part of a game pack held
   the old game's whole recording (sections 4-12: nine delta tables, a row for each of 300 frames). The engine images
   apply frame 0 once and never read the rest. 8,526,624 B is the farm pack's non-texture part with the recording;
   eng-bake1's 4,011 KiB is its census's "room content only". The engine images now keep frame 0's rows only
   (render/native_scene.inc; the bench keeps all 300): village 6,658,951 -> 2,584,263 B, farm 8,542,895 -> 3,476,207 B,
   hill 6,173,931 -> 2,036,491 B resident. KOS heap to the arena after play: **village 4,780,032 B, hill 4,931,584 B**
   (the hill ran about 8 KB into the arena before); **HILL draws the handgun 728 of 728 pictures** (d4).
2. **DOOR: not OK yet.** On d4 (head 8d0fe36e0) both loads complete (village > farm > village: the farm pack opens, the
   renderer reopens, collision pieces 2/2, arena 692,704/692,704, VRAM 2,639,720/2,639,720, skeleton tables 2/2), and it
   FAILED on two items: (a) the weapon is not drawable in the farm (90 pictures): the shared set's FARM.PAK has no weapon
   models; (b) the round trip's KOS heap is 200 B over (5,746,392 -> 5,746,592): the renderer's lit caches grow and are
   kept. Fixes made after d4: (a) a farm pack with the weapon models (eng-bake1's r103.pak, with the HUD fix, through
   bake/weapon_model.py: `E:\RE4DC-Lanes\eng-mem1\packs\R103.PAK`, RECEIPT.txt; pack_keep_check PASS) and (b) the lit
   caches given back at a room change (fa2b14aba). **Neither is verified on Flycast**: the disc built with them (d6)
   hung at boot on std1 twice and std2 once, after "fs_iso9660: disc change detected" and before the selector's CDISC
   START (no lane code runs before that line; the disc's hashes checked OK). Cause not found (stopped at the tool-call
   limit). Also: each load takes about 60 s on plain Flycast (64.0 s and 54.7 s; 657 / 888 reads), because the whole
   11.3 MB and 9.0 MB packs are read for their CRC; real disc timing is a console question.
3. **Sound on the calibrated tier, within H-025.1 everywhere (c5):** mean / worst ms village 0.46 / 0.68, hill
   0.64 / 0.87, fight 0.72 / 1.60, boss 0.57 / 0.84 (ceilings 1.0 / 2.0; pictures 41-640). HILL's 2.77 ms worst is
   explained and gone: the sound's spans read KOS's clock, which jumps 2.5 ms once a second (eng-skel1 item 8); they now
   read core/e1_clock.h.
4. **For the integrator:** the edits outside the map's files (below); the R103 pack into a shared set; the d6 boot hang.

## The map (MEMORY_MAP.md has the table per block and image)
| Block | E1 / SENDABLE | FIGHT | BOSS |
|---|---|---|---|
| Image | 0x8c010000-0x8c275e30 | -0x8c32e750 | -0x8c2d2c70 |
| KOS heap | to 0x8cc80000 (10,526,152 B) | to 0x8ce40000 (11,606,184 B) | to 0x8cc80000 (10,146,696 B) |
| Behaviour arena | 0x8cc80000-0x8cf40000 (2.75 MiB) | 0x8ce40000-0x8cf40000 (1 MiB, was 1.25) | as E1 |
| Services region | 0x8cf40000-0x8cfc0000 (512 KiB) | same | same |
| Unused / main stack / hand-off | 0x8cfc0000 / 0x8cfd0000 / 0x8cfe0000-0x8d000000 | same | same |

Margins after play (d4, Flycast): KOS heap LEON 4,780,032, HILL 4,931,584, FIGHT 290,816, BOSS 1,986,560 B; arena
heap 4 peak LEON 692,704, HILL 604,992, FIGHT 844,384 (margin 199,936), BOSS 464,576, DOOR (farm) 1,077,984 B; services
pool tables 52,064 to 115,680 B of 262,144, carve 34,816; stack high water 9,396 to 9,728 of 65,536. The worst margins
are the fight's. Before (d2, FIGHT 1.25 MiB arena): FIGHT KOS margin 28,672 B; d3 with a 48 KiB larger image: -20,480.

## Merge resolutions
- skel1, skel2, load1: no conflicts (the room archive with skel2's baked pieces lives on load1's room heap, in the arena).
- snd1: `host/e1_engine.h` map rewritten once (skel2's 512 KiB region and arena top kept; snd1's R1 met by the resident
  pack's shrink, so the E1 arena keeps 2.75 MiB; FIGHT 1 MiB). `core/main.cpp`: load1's `room_init(room, pos, ang,
  first)` with snd1's seed block in its first-room branch. `loader/selector.c`: the DOOR rule and the sound line both.
  `docs/engine/SERVICES.md`: both sections.
- origin/engine 28ad25ce7 (eng-e2d): `game/allowed_original.txt` both kept; eng-e2d's new split check then failed BOSS
  on game/snd (the sound stubs' replaced functions inlined): `game/snd` added to SPLIT_NOIPA_UNITS. Link check after:
  default 0, SENDABLE 0, BOSS 0, FIGHT 30 SERVICE functions (FIGHT built from origin/engine 28ad25ce7 here: also 30).

## The rulings
1. **setParent2:** e2c_dump.cpp's logging body is a weak empty body; the CA2 line is logged by a `--wrap` of
   `cObjChain::setParent2` (svc.mk E2C_WRAP_FLAGS) in both builds, which then calls the body (native: chain.cpp;
   odump: game/obj1d.cpp) only on an existing object (the exercise plants giants without chain objects; the first run
   segfaulted in both bodies on `this == 0`). The native reference links. e2c_check: every row as it must, CA2 lines 3
   (bell-ganado) and 6 (hill-ashley) in both builds (ev\suites-a, ev\suites-b).
2. **Sound ceiling scope:** selector diff (loader/selector.c):
   ```
   +static int tier_judged(void) { ... file_exists("TIERCAL") || file_exists("TIERCON") ... }
   -  sum_add(e, "sound %s m%u.%02u w%u.%02u@%u >1.0/2.0, voices %u, ...
   +  sum_add(e, "sound %s m%u.%02u w%u.%02u@%u >1.0/2.0 %s, voices %u, ...  ("judged (calibrated tier)" | "not judged (plain run)")
   -  else if (s->timing && g_snd_on && (g_snd_mean > 1000 || g_snd_worst > 2000))
   +  else if (s->timing && g_snd_on && tier_judged() && (g_snd_mean > 1000 || g_snd_worst > 2000))
   ```
   The disc declares its tier: `build_console_disc.sh --tier calibrated|console|plain` (default plain).
3. **The map:** above.

## Checks and their controls
- `tools/engine/pack_keep_check.py` (new): the kept layout against the whole pack on the five shared packs and R103:
  PASS; controls `--control pad` / `nopad` / `drop` FAIL on all five (ev\packkeep). PC harness of the DC loader code
  (s\harness.sh): CRC OK on all five.
- Sound ceiling on c5 (calibrated): CSNDSLOW FAILED "mean 5.65 worst 8.26 ms (pic 49)"; ASNDOFF OK (sound OFF).
  On plain discs CSNDSLOW ends OK "not judged (plain run)".
- Memory: FIGHT d3 FAILED "after-play memory line: arena margin -20480" (the selector's rule caught the overlap).
- DOOR controls on d4: CDOORPK FAILED "E1 load: missing /cd/st1/r103.arc"; CDOORLK FAILED on the weapon first (its
  LEAK reading 5,746,392/5,750,688 is there); CDOORRD not run (it was on d6).
- PC suites on fa2b14aba (ev\suites-b): svc_controls 79, camcheck, refctl, controls 18, outcome_controls 35, aim_check,
  e2check, e2bcheck, e2c_check, colmap_check, speed_controls, door_check (PASS; controls early=20 and at0 FAIL; two
  reference runs identical): every row as it must. **skent_check: `skent shot-ganado` MUST PASS row fails** (6 bone-ticks
  at 1e+30, a bone in one build only): eng-skel2 reported the same after merging eng-fix1 (origin/engine); not caused
  by this lane, not fixed.

## Files touched outside the owned list
- `render/native_scene.inc` beyond the sizing: the frame-0 load path (pack_keep, keep_layout, keep_pad, read_rest_keep,
  valid_inputs' frame count) and the lit-cache release call in native_release; `render/content_actor.inc`:
  `content_lit_release()` (4 lines). Needed for the farm to fit and for the round trip; for the integrator's ruling.
- `services/sound/aica.cpp`, `snd_svc.cpp`: the clock (snd1's files, taken in by this train).
- `hostref/svc/e2c_dump.cpp`, `svc.mk` (ruling 1); `loader/selector.c`, `tools/engine/build_console_disc.sh` (ruling 2);
  `game/Makefile` (SPLIT_NOIPA_UNITS += game/snd); `tools/engine/pack_keep_check.py` (new).

## Requests
- Integration lane: discs need eng-skel2's baked archives (PRISTINE=/root/work/lanes/eng-skel2-data/pristine-colb was
  used here) and a farm pack with weapon models for DOOR (R103_PAK / R103_VIS; this lane's pack with its receipt is a
  candidate for a shared set).
- Whoever takes DOOR next: find the d6 boot hang (runs\d6c-std2: SCENES.TXT, MANIFEST.txt, serial), then run DOOR,
  CDOORLK, CDOORRD; the farm loads would be much shorter with the recording dropped from engine packs at bake time
  (bake owner), since the load must now read 5 MB it does not keep, for the CRC.
- eng-skel1 / integrator: the skent shot-ganado row.

## Not done / not verified
- DOOR OK (above), CDOORRD, the R103 pack and the lit-cache fix on Flycast.
- FIGHT and BOSS sound on the waves or the boss's full fight beyond the 600 pictures; no console.
- The model cannot see: graphics chip fill and sort, store-queue submission, bus contention (the G2 bus to the sound
  chip above all), disc timing.

Head: see the final message (pushed `lane/eng-mem1`).
