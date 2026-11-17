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
