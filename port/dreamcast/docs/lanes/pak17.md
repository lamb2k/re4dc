# Lane pak17: disc 1 textures all in the pack (2026-10-16)

Branch `lane/pak17` (from t15/int bd02c79b), worktree `/root/probe/lanes-20261016/pak17/tree`. Coordinator round 4 A:
drop the loose duplicates, pack the non-16-bit textures as they are, VQ the 16-bit ones (PSNR >= 29, UI / alpha stay
16-bit). For test 17. Data only: no program change, no knob. The release image is the same with or without it.

## What changes on the disc

Today a disc carries `dc/tex.pak` plus loose `dc/tex/<c>/<key>.re4tex` files from the package base tree and from the
data sets. `native_ui.cpp` looks a key up in the pack first (`texpack::find`, then the loose path), so a loose copy of
a packed key is never read. From test 17 the disc has no loose `dc/tex/<c>/` textures (4 flat-named ch2 copies stay; their keys are packed).

Tool: `tools/d367/vram/disc_pack.py --fixture <package fixture without pak17> --pkg-src <PKG_SRC> --out <dir>`.
Output (private, `/root/re4data/private/pak17-20261016`, never in Git): `tex.pak`, `loose-keys.txt`, `vq-keys.txt`,
`base.json`, `report.json`, `SUMMARY.txt`. Data set `pak17` (test11/t11-fix.py) stages the pack last and removes every
loose texture from the disc (DROP_LOOSE). `T17_DATA = T15_DATA + ',ch2,cast16,pak17'`.

Built on the ch2 data of 10-16 21:54 (input pack sha256 13340bfa..., 4,904 keys, 119,822,336 B):

| Loose keys (2,566, 95,596,544 B on disc) | Keys | Loose bytes | In the pack |
|---|---|---|---|
| already in the pack, same bytes (dropped) | 397 | 20,502,528 | 0 |
| already in the pack, other bytes (dropped; the pack's copy is the one the game reads today) | 853 | 31,692,800 | 0 |
| not 16-bit twiddled (VQ, palettized, multi-texture): as they are | 563 | 6,967,296 | 6,967,296 |
| 16-bit, kept 16-bit: alpha 228, under 16 KiB 261, PSNR < 29 dB 23 | 512 | 14,034,944 | 14,034,944 |
| 16-bit, opaque, >= 16 KiB: VQ (PSNR 29.0..99.0 dB) | 241 | 22,398,976 | 3,725,312 |

The coordinator's estimate (715 / 200 / 338) was made on the test 15 data; ch2 and cast16 added loose textures since.

- New pack: 6,220 keys, 144,570,368 B, sha256 52d9b0013315c5e9... The index keeps the first key of each 2 KiB sector
  in RAM; 6,220 keys fit the 64-sector cap (8,192 keys).
- Disc tree 1,064.0 -> 997.9 MB (Flycast package build, standard layout).
- VQ keys' VRAM when uploaded: 21,905,408 -> 3,231,744 B (sum over all 241; a room loads only its own).

**Staleness guard.** base.json records the input pack's sha256 and every loose source's sha256. When an earlier set
(ch2, cast16, ...) changes a picture, t11-fix.py stops ("rebuild pak17"). This happened once in this lane: the first
pak17 was built on older ch2 data and carried 16-bit copies of 4 keys that the new ch2 pack has as VQ (r200 pinned
VRAM +85,984 B). Rebuild: `python3 tools/d367/vram/disc_pack.py --fixture <fixture of T17_DATA minus pak17> --pkg-src
/root/probe/lanes-20261015/t15k/pkgsrc-t14cand --out /root/re4data/private/pak17-<date>`.

**Packaging.** test8/t8-pkgtree.py (outside Git) now unlinks the fixture's removed files from the package tree.
Without that, the loose files of PKG_SRC stay on the disc.

## Gates (Flycast; program out-p17rP / p17rT / p17mW, the test 17 recipe ch2/ch2-build.sh)

Evidence `C:\Flycast-Evidence\re4-dreamcast\pak17-20261016` (Flycast numbers). Old data = T15_DATA + ch2 + cast16
(test 17 without pak17), new = T17_DATA. Same program in both.

| Gate | Result |
|---|---|
| Package audit (audit17.py) | PASS: 780 / 780 staged files with the right sha256; 0 of 4,393 removed paths on the disc; 4,370 dropped keys all in the pack; 1ST_READ.BIN = the play build image 582738e9; 9 overlays = the build's; missing.txt empty |
| disc_lint loader + standard | PASS |
| Loose dc/tex files left | 4 flat-layout names `dc/tex/<key>.re4tex` staged by data set ch2 (3f690586, 4da9c3fa, 61519868, fc75dd46). All 4 keys are in pak17 and the game looks the pack up first, so they are never read |
| STRICT h2 (stA), stop 2000 | STRICT, MUST-IDENTICAL, 2,002 ticks |
| STRICT bell (stB), stop 2000 | STRICT, MUST-IDENTICAL, 2,002 ticks |
| STRICT door103 (stC), stop 2000 | STRICT, MUST-IDENTICAL, 2,002 ticks (round 3 pair cut at ~1,926 by the host capacity guard; rerun stC-o4 / n4) |
| texchk absent, 28 rooms (stage_route.py chapters 1-1 .. 2-3: every room plus r200) | 0 fails, 0 absent, 0 refusals / nocontig in every room |
| VRAM per room | equal or better in every room at the same sample (table below) |
| KOS squeeze 48 KiB (10 runs) | PASS: fight min headroom 11,016 B, call 28,456 B, door103 17,096 B, 0 Out of memory |
| GDEMU race (console, gdemu profile, 10 seeds, r101 + door103) | PASS: 10 / 10 reach r103, 0 bad reads (seed 10 first stopped by the host disk floor, rerun ok) |

Pre-existing in both data sets (not from this lane): r100 7 `allocation failed` / Em set failed (s30 heap 4) and
thrash guard 12 (old) / 11 (new) by tick 1367; r10c and r10e "qualified native room container missing" HALT
(no native room is built for them). r120 (intro) plays the 66 s r120s00 movie in a 60 s run: no room textures,
the same in both data sets. r10e / r120 warp at the room origin (god, freeze): the preload sample does not depend
on where Leon stands.

## VRAM per room (Flycast, TEXCHK=2 runs; old data = T15_DATA + ch2 + cast16)

Sample = the latest `vram room` line both runs reached (preload = after the room's resident textures; tick = in play).
Runs are 60 s (r100 150 s); bytes. Rooms where the VQ keys load show the gain: r118 +239,616 free, r11b +294,912,
r10b +55,296, r106 +38,912, r11e +12,288. r109 shows 2,080 B less free at preload f 291: the same keys and sizes are
uploaded in both runs (vramdiff 0), one picture lands a frame earlier.

| Room | runs o / n | texchk fails o / n | absent n | refusals / guard / nocontig n | sample (at, f) | pinned o -> n | dynamic o -> n | free o -> n | largest o -> n | halt o / n | alloc fail o / n |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r100 | o4 / n4 | 0 / 0 | 0 | 0/11/0 | tick 1367 | 1148216 -> 1148760 | 348320 -> 348320 | 1005312 -> 1004768 | 81920 -> 81920 | 0 / 0 | 7 / 7 |
| r101 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | tick 767 | 952386 -> 952386 | 1363734 -> 1363734 | 218496 -> 218496 | 6144 -> 6144 | 0 / 0 | 0 / 0 |
| r102 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 180 | 1381152 -> 1381152 | 0 -> 0 | 1128928 -> 1128928 | 1103872 -> 1103872 | 0 / 0 | 0 / 0 |
| r103 | o4 / n3 | 0 / 0 | 0 | 0/0/0 | preload 1187 | 1555308 -> 1555308 | 0 -> 0 | 921984 -> 921984 | 204544 -> 204544 | 0 / 0 | 0 / 0 |
| r104 | o3 / n4 | 0 / 0 | 0 | 0/0/0 | preload 179 | 1262850 -> 1262850 | 0 -> 0 | 1247200 -> 1247200 | 1149952 -> 1149952 | 0 / 0 | 0 / 0 |
| r105 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 181 | 1610848 -> 1610848 | 0 -> 0 | 899232 -> 899232 | 829440 -> 829440 | 0 / 0 | 0 / 0 |
| r106 | o4 / n4 | 0 / 0 | 0 | 0/0/0 | preload 184 | 1643616 -> 1604704 | 0 -> 0 | 866464 -> 905376 | 819200 -> 858112 | 0 / 0 | 0 / 0 |
| r107 | o4 / n3 | 0 / 0 | 0 | 0/0/0 | tick 850 | 432736 -> 432736 | 1557762 -> 1557762 | 486784 -> 486784 | 339968 -> 339968 | 0 / 0 | 0 / 0 |
| r108 | o4 / n3 | 0 / 0 | 0 | 0/0/0 | preload 182 | 1573260 -> 1573260 | 0 -> 0 | 936800 -> 936800 | 843776 -> 843776 | 0 / 0 | 0 / 0 |
| r109 | o4 / n3 | 0 / 0 | 0 | 0/0/0 | preload 291 | 1176864 -> 1178944 | 2080 -> 2080 | 1298368 -> 1296288 | 811008 -> 811008 | 0 / 0 | 0 / 0 |
| r10a | o4 / n4 | 0 / 0 | 0 | 0/0/0 | tick 767 | 429376 -> 429376 | 1129984 -> 1129984 | 917952 -> 917952 | 847872 -> 847872 | 0 / 0 | 0 / 0 |
| r10b | o3 / n4 | 0 / 0 | 0 | 0/0/0 | tick 1367 | 679296 -> 679296 | 1140800 -> 1085504 | 657216 -> 712512 | 610304 -> 665600 | 0 / 0 | 0 / 0 |
| r10e | o4 / n4 | 0 / 0 | 0 | 0/0/0 | preload 178 | 157216 -> 157216 | 0 -> 0 | 2352864 -> 2352864 | 2347008 -> 2347008 | 1 / 1 | 0 / 0 |
| r10c | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 178 | 157216 -> 157216 | 0 -> 0 | 2352864 -> 2352864 | 2347008 -> 2347008 | 1 / 1 | 0 / 0 |
| r117 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 180 | 1466080 -> 1466080 | 0 -> 0 | 1044000 -> 1044000 | 976896 -> 976896 | 0 / 0 | 0 / 0 |
| r118 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | tick 767 | 239200 -> 239200 | 1949506 -> 1709890 | 288576 -> 528192 | 182272 -> 421888 | 0 / 0 | 0 / 0 |
| r119 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 500 | 1352864 -> 1352864 | 0 -> 0 | 1124448 -> 1124448 | 1008640 -> 1008640 | 0 / 0 | 0 / 0 |
| r11b | o3 / n3 | 0 / 0 | 0 | 0/0/0 | tick 767 | 638336 -> 638336 | 1496288 -> 1201376 | 342688 -> 637600 | 288768 -> 583680 | 0 / 0 | 0 / 0 |
| r112 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | tick 767 | 773600 -> 773600 | 1228384 -> 1228384 | 475328 -> 475328 | 403424 -> 403424 | 0 / 0 | 0 / 0 |
| r111 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 182 | 2184354 -> 2184354 | 0 -> 0 | 325696 -> 325696 | 153600 -> 153600 | 0 / 0 | 0 / 0 |
| r113 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 182 | 1861964 -> 1861964 | 0 -> 0 | 648096 -> 648096 | 571392 -> 571392 | 0 / 0 | 0 / 0 |
| r11c | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 181 | 2186818 -> 2186818 | 0 -> 0 | 323232 -> 323232 | 172032 -> 172032 | 0 / 0 | 0 / 0 |
| r11d | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 182 | 1638614 -> 1638614 | 0 -> 0 | 871456 -> 871456 | 794624 -> 794624 | 0 / 0 | 0 / 0 |
| r11e | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 181 | 1646208 -> 1633920 | 0 -> 0 | 863872 -> 876160 | 839680 -> 851968 | 0 / 0 | 0 / 0 |
| r10f | o4 / n4 | 0 / 0 | 0 | 0/0/0 | preload 181 | 1968864 -> 1968864 | 0 -> 0 | 541216 -> 541216 | 440320 -> 440320 | 0 / 0 | 0 / 0 |
| r11f | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 178 | 1697920 -> 1697920 | 0 -> 0 | 812160 -> 812160 | 718848 -> 718848 | 0 / 0 | 0 / 0 |
| r200 | o3 / n3 | 0 / 0 | 0 | 0/0/0 | preload 183 | 2160898 -> 2160898 | 0 -> 0 | 349152 -> 349152 | 256000 -> 256000 | 0 / 0 | 0 / 0 |

## Landing (test 17)

Landed with motion streaming (lane ch5found16 8627a5df, generic part) on branch land/t17-pak17-motion. In the same landing:
- `tools/d367/test8/t8-pkgtree.py` is now in Git (it was `/root/probe/lanes-20261011/test8/t8-pkgtree.py`, outside Git);
  `test16/t16-package.sh` calls the in-tree copy. It unlinks the fixture's removed files from the package tree. Older
  fixtures remove nothing that is in the base tree, so they get the same tree as before.
- `release-knobs.py` `disc_files`: a DROP_LOOSE set in the list keeps loose `dc/tex/<c>/<key>.re4tex` out of the Build-Assets
  zip (the disc has none), and the `ovl` entry of data set ch2 (overlay names, built by the recipe) is skipped instead of
  failing. With `snd16,water16i,vq16w,fsh,ch2,cast16,pak17` the zip's disc part is 402 files (1,801 without pak17).
- Test 17 knob file: `release-knobs.py write` refused the chapter 2 recipe's private `PS2_ENEMY_CH22_DIR` /
  `PS2_ENEMY_CH23_DIR`. Fixed on lane/kit17 (ed993d11): both map to the Build-Assets zip's `re4dc-assets/ps2enemych2/`
  (`@ASSETS@/ps2enemych2` in the knob file), and build-public.sh drops them with `PS2_CH2_ENEMY=0` when the zip is absent.
  Proof on ed993d11 (clean checkout, kit-check steps 2 / 3 / 5): write + check 193 knobs; zip 421 files, zipcheck PASS
  (the release build read 6 private files, all in the zip); the kit build's image 582738e9 = the private ch2-build.sh rP
  build k17rP, 9 overlays identical; the no-assets build builds with PS2_CH2_ENEMY=0. Its `# disc-sets:` line is
  `snd16,water16i,vq16w,fsh,ch2,cast16,pak17` (test 16: snd16,water16i,vq16w).

### Gates on the merged tree (land/t17-pak17-motion over t15/int f30cd6f9; Flycast)

Resident-list gate (f30cd6f9 `resident_keys.py check`, t11-fix `RE4DC_RESIDENT_STRICT=1`): every fixture below was
made with it on. `resident_keys.py pack` over all 41 `vram/resident/r*.tsv` lists, then `water_resident.py pack` over
the 6 water lists, gives 3,328 + 50 records, byte for byte data set ch2's `dc/resident.bin` (cfcc77d6): 0 short lists.
pak17 adds no list and needs no resident.bin of its own (the records carry the source format, which VQ keeps).

| Gate | Result |
|---|---|
| Knob-off identity vs t15/int f30cd6f9 (fresh objdirs, ch2/ch2-build.sh rP and rT) | rP image 582738e9, rT image a1ffdda3: identical, 9 overlays identical, candidate knobs identical |
| Package audit (T17_DATA, in-tree t8-pkgtree.py: removed 1,253) | PASS: 780 / 780 staged, 0 of 4,393 removed paths present, 4,370 dropped keys all in the pack, 1ST_READ = 582738e9; disc_lint loader + standard PASS |
| KOS squeeze 48 KiB (fresh-objdir twin fpl17sqW from the clean l17rP) | PASS 10 / 10: fight min 11,016 B, call 28,456 B, door103 17,096 B, 0 Out of memory |
| STRICT h17rT (t15/int, T15_DATA + ch2 + cast16) vs l17rT (merged, T17_DATA), stop 2000 | h2 STRICT (2,002 ticks, MUST-IDENTICAL), bell STRICT (2,002), door103 STRICT (2,002) |

### Gates on land/t17-pak17-merge (lane/kit17-on-1c013bef fc827b3a merged into t15/int e46c87ac; Flycast)

e46c87ac adds T15_SO (STAGE_OVL=1 SS_POOL_TOP=1) to T15REC: the stage modules st1_0..st1_3 / st2_0 are now overlays.
`t8-pkgtree.py` put a fixed overlay list (pl0f em2f em22 em2b pl11 sscrn) on the package disc, so a T15REC package disc
lacked the stage overlays and halted at the first stage load ("route overlay missing on the disc"); the STRICT scenario
fixtures (t11-fix) lack them too. Fixed here: t8-pkgtree.py puts every overlay the play build made; the STRICT fixtures
were armed with `texchk/fixture_arm.py <fixture> <out> <label>` (adds the arm's overlays). The audit now also fails on a
play-build overlay absent from the disc. The shared copy /root/probe/lanes-20261011/test8/t8-pkgtree.py has the same
edit (backup `.bak-ovl17`).

| Gate | Result |
|---|---|
| Identity vs t15/int e46c87ac (no game source differs; fresh objdirs, ch2/ch2-build.sh rP and rT) | rP image d452f0d7, rT image 9311be27: identical, 14 overlays identical, candidate knobs identical |
| Package audit (PKG_SRC explicit = t15k/pkgsrc-t14cand, 2,561 base files before and after; output a real directory) | PASS: 1,612 files, 0 of 4,393 removed paths present, 4,370 dropped keys all in the pack, 1ST_READ = d452f0d7, 14 overlays = the play build's, 0 absent; disc_lint loader + standard PASS |
| KOS squeeze 48 KiB (fresh-objdir twin fpg17sqW from the clean g17rP; the twin disc carries all 14 overlays) | PASS 10 / 10: fight min 7,720 B, call 25,160 B, door103 13,800 B, leave100 / leave103 7,720 B, 0 Out of memory |
| STRICT e17rT (t15/int e46c87ac, T15_DATA + ch2 + cast16) vs g17rT (merge, T17_DATA), stop 2000, RESIDENT_STRICT=1 | h2 STRICT, MUST-IDENTICAL (2,002 ticks); bell STRICT, MUST-IDENTICAL (2,002); door103 STRICT (2,002), decisions differ only in `ep` at tick 1176 (the door load), which also differs between two runs of the same e17rT build (n17b vs n17c: 1238690 / 1238694 vs 1239485 on g), so it is run-to-run, not the merge |

The KOS minimum fell from 11,016 B (land/t17-pak17-motion over f30cd6f9) to 7,720 B, still a pass. Cause (measured
10-17): **not pak17, and not KOS use**. ARENA_FIT gives the game arena everything above
`ARENA_FIT_KOS_BYTES + 64` in 4 KiB steps, so KOS keeps that floor plus a 0..4,095 B rounding residue that depends on
the program's `_end`. On f30cd6f9 the residue was 3,384 B ("arena fit ... 200,056 left to KOS"); on e46c87ac's image
(d452f0d7) it is 88 B (196,760 left). 3,296 B of difference, the whole drop: the KOS headroom is already 3,296 B lower at
frame 86, before any texture loads. Minus the residue, the fight minimum is 7,720 B on both.
Control (Flycast, same program d452f0d7, KOS twin fpe17sqW): the release data without pak17 (T15_DATA + ch2 + cast16:
the older 4,904-key pack + 2,570 loose textures; legacy layout, as that data does not fit a standard disc) gives the
same 10 numbers to the byte (fight 7,808 / 7,720, call 25,248 / 25,160, door 13,888 / 13,800). The pack's index is
static (64 first-keys + one 2 KiB sector), so 6,220 keys cost no KOS heap. To make the minimum independent of `_end`,
ARENA_FIT_KOS_BYTES could rise by 4 KiB (heap 4 gives 4 KiB); not done here.

## For the test 17 release lane

- Knob file: `--disc-sets snd16,water16i,vq16w,fsh,ch2,cast16,pak17` (pak17 last).
- Package with the in-tree `tools/d367/test8/t8-pkgtree.py` (t16-package.sh does); the old copy in
  /root/probe/lanes-20261011/test8 has the same edit (backup `.bak-pak17`).
- Rebuild pak17 whenever ch2, cast16 or any earlier set changes its pictures (the guard stops the fixture otherwise).
