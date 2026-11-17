# island-gca (lane, 2026-11-17)

Branch lane/island-gca from lane/world-ch5 ee61884ce. Goal: GC-ASSET on Disc 3 (945 unreviewed rows, 590 unique).

## Landed in this lane (data and provers, Disc 3 only)
- isnd5 (D3_DATA, store re4data/private/isnd5-20261117): PS2 PCM in place for em/em1d.drs (141 of 151 samples) and st3 r30a r311 r317 r31b r31c r320 r327 r333 .dar
  (466 of 501 PS2, 35 keep GC, rows in gc_port23/sound-kept-gc.tsv). Same file sizes. Replaces sound-mram 3a258d2c / sound-aram 2b738457.
- provenance-reviewed.tsv: 315 texture rows (dcf3isl/isl15 provenance.tsv rows by output sha, or exact bytes of a store file / pak member whose picture header names
  its PS2 conversion) and 16 motion rows (ps2_motion_prepared.py rewrite on island archives: 0 changed clips = byte-identical to the PS2 slot).
  Provers: tools/d367/island_gca/island_tex_prov.py, island_motion_prov.py.
- isle5 (store isle5-20261117, DATA set registered, NOT in D3_DATA): PS2 island enemy lists emleon06/07. island_enemy_audit.py result: differing rows r301 6, r30a 1,
  r30c 2 (start dead), r311 6, r320 1, r327 23 (3 start dead), r330 4, r331 1; r334 27 (Separate Ways, PS2-only). Other island rooms identical to GC.

## Not done (with the reason)
- Texture: 57 unique shas stay unknown (headers say "source"/"source-pair" or no material; dcf3pak-only members). d17e9c56-fa23c229 is the user-approved GC A button (font22).
- em1d body 49a59e4e, pl01 bodies dc550af6 17c2d1a1 9d447531 ddfc4b21 etc: consumer=source_geometry. These GC BINs are the digest source the native cast acquires by exact
  bytes (ps2_ganado_bins.py "LEFT ... native cast source BIN: kept"); rebuilding them as PS2 breaks the cast binding. Same gap as Disc 2 (model gc 21). Needs the registry
  packages to carry PS2-derived source blobs: engine/assets-dc work, not a data set.
- Island ETM props (c8719df3, eaea211d, 18f19ade in st3/r300.dar, r309.dar): need ps2_objects.py regeneration of the room objects (castlegca34 pipeline) over r300.dar,
  which isnd300 already rewrites; not started.
- Motion: 5e560e7d (em39), 8f1d9147 (r30c), 27ce1add (r30f) unproven (r30c / r30f rewrite needs --keep-gc slot handling).
- r300 133 unmapped-texture-address: only r300 (--DOORDEMO); needs a GC_ASSET_PROF probe build.
- Chapter 5 spawn logic as one unit: PS2_ENEMY_ST3=23 (bits r30f, r301, r327, r311 skip) already in D3REC; lists (isle5) and r30c/r320/r330/r331 room code not ported or run.
- Still pairs, r332 TEXCHK keys: not run.

## Gate result (Disc 3 rr cycle ig1, test commit 9dc1e475 = lane head 392c124f0 + RR_DISC3, Flycast plain, other lanes running; evidence E:\RE4DC-Lanes\island-gca\rr\1117-0849-9dc1e475)
Judge: E:\RE4DC-Lanes\world-ch5\rr\judge-d3.sh (rr-judge has no Disc 3 rows). Not the console-like profile: plain 60 s runs as in world-ch5 round 4.
- CAST-GC PASS (243 census lines, 50 room/model rows, 0 GC or MIXED); LEON-GC 36/36 PASS; TEXCHK 37 pass 0 fail; HALT/FAULT/MISSING/OOM none; 36/36 rooms entered.
- GC-ASSET still FAIL. Unique unreviewed rows 590 -> 269 (and 13 of the 269 are proven by the round 2 reviewed rows added after, so 256 expected on the next cycle). Failures lines 945 -> 631
  (631 = 269 rows over rooms + 362 non-row: r300 unmapped-texture-address 351 and two new "no checkpoint" lines r301 visit 5, r310 visit 3; those two are cycle timing next to 2 other lanes' Flycasts, not asset rows).
  By kind (unique rows, before -> after): texture unknown 440 -> 138 (124 are the 57 unproven shas across rooms, 14 new draws, 13 of them now proven), model gc 54 -> 54, model unknown 36 -> 51 (coverage variance:
  same shas as before plus 1 new), motion unknown 16 -> 5, motion gc 3 -> 1, sound-mram/aram unknown 20 -> 8, sound gc 18 -> 8 (em1d 3a258d2c is gone; 8 sound-aram gc rows remain, other em1d aram image, to trace), texture gc 1 -> 2, geometry 1, movie 1.
- Not run in this cycle: KOS 48 KiB door + fight on Disc 3 (the d3kos dirs exist; the cycle did not judge them: read d3kos/kos in the evidence dir), Disc 1 knob-off identity (recipe unchanged for Disc 1; D3_DATA and gc_port23 tables only; image not compared). Re-run before landing.
- The Disc 3 image was NOT given the em1d sound set as verified by ear or look: ps2_audio in-place PCM, same file sizes; only the census (HALT 0) and the catalog rows prove it loads.

## Round 2 (2026-11-17 afternoon, coordinator decisions)
Landed (lane/island-gca 7831dec83, pushed): d17e9c56-fa23c229 allowlist rows for the 24 Disc 3 rooms (reason "user-approved font22 pad picture (10-22)", owner island-gca);
isnd5 now covers em1d em1e em1f em31 em32 em36 em3a pl0e + the 8 room banks; isnd5b = em39 (bossk copy) PS2 PCM, D3_DATA after bossk. The 8 rooms still showing sound-aram 2b738457 (r301 r305 r30b r30c r30e r311 r316 r330)
use em1e, which shares em1d's GameCube aram image: expected cleared on the next cycle (not yet proven).
Banks changed on Disc 3 (PS2 PCM in place, same sizes; no ear check possible): em/em1d em1e em1f em31 em32 em36 em3a em39 pl0e; st3 r30a r311 r317 r31b r31c r320 r327 r333 (plus isnd300's r300). 38+ samples keep GC (sound-kept-gc.tsv).
Cycle ig2 (console-like Flycast: RE4DC_EMU=console RE4DC_GD_PROFILE=gdemu, test commit 7ddfc1d85, driver E:\RE4DC-Lanes\island-gca\rr\run-ig2.sh, evidence rr\1117-1100-7ddfc1d8) was started 11:00; at 13:30 it was still in the disc3 step
waiting on fp_iso extract from E: (three lanes in D-state on the same disk). NOT judged. When ALLDONE is in rr\run-ig2.out: bash E:\RE4DC-Lanes\world-ch5\rr\judge-d3.sh <evidence dir> /root/work/lanes/island-gca-rrsrc, then read the d3kos / kos dirs for the 48 KiB door + fight, and compare the Disc 1 image to a205f8a035e4d465.
Findings, not done:
- r30c: ps2_motion_prepared.py rewrite --keep-gc 28 -> 5 clips PS2-changed (real motion replacement; needs the gameplay-equivalence gate); r30f: --keep-gc needs 25 slots (37-43 46-63), 8 clips PS2-changed. 8f1d9147 (r30c) is a kept-GC slot (stays GC, PS2 has no entry); 27ce1add (r30f) is a PS2-changed clip.
  pm*-named store provenance would credit the kept-GC keys too, so use reviewed rows by sha after the rewritten dars exist. Three new unproven keys 13fa4799-fb06fa62, 77903604-c5f8ac6e, f1ad500d-868a5a9f not located.
- 57 texture shas: material strings are the generic "source" / "source-pair" binding names (prepare_native_ui / pack merge), identical in island-d3's own pack; no PS2 trace without matching PS2 TPL pixels. Unproven.
- Not started: ETM props regeneration (r300/r309), r300 PROF probe, isle5 per-room gating (r301 r30a r30c r311 r320 r327 r330 r331; r334 parked) and the D3_DATA entry. isle5 stays out of the recipe.
- Trap: /tmp is shared between lanes (another lane overwrote /tmp/w.sh and /tmp/a.sh); keep lane scripts in the scratchpad.
