# Lane world-ch4 (chapter 4 on Disc 2, 2026-11-02)

Branch `lane/world-ch4` from t15/int 15ed29fe5. User 11-02: "the remainder of disc 2 build today"; build now, warp and
play-through testing later. Disc 1 program and data unchanged.

## Chapter 4 rooms and events

Boundaries are the SceSetChapterEnd calls: r206 ends 3-4 (its door 7 leads to r210), r22b ends 4-1, r21d ends 4-2,
r225 ends 4-3, r22a ends 4-4 (door 1 to r300, chapter 5). The PS2 USA release is one DVD (one ISO), so the PS2 has no
disc swap here; Disc 2 (castle, chapters 3 and 4) ends at r22a -> r300.

| Sub-chapter | Route (doors from worldch4/doors-ch4.tsv) | End event |
|---|---|---|
| 4-1 | r206 -> r210 -> r222 -> r210 -> r201 -> r219 -> r211 (hub: r216, r212) -> r213 -> r214 <-> r217 -> r218 -> r215 -> r229 -> r221 (Verdugo) -> r22b | r22b s00 (now a PS2 movie) |
| 4-2 | r22b -> r220 -> r223 -> r224 (El Gigante) -> r21d | r21d grave lift |
| 4-3 | r21d -> r225 -> r21b (mine cart) -> r225; optional r21a | r225 lift |
| 4-4 | r225 -> r226 (statue) -> r227 -> r228 (Salazar) -> r22a -> r300 | r22a s00 (now a PS2 movie) |

r22c (castle hub, doors to r204 r211 r220 r305 r31d) is reachable from r211 / r220.

## What Disc 2 lacked, and the data sets that add it (D2_DATA, Disc 2 only)

- No chapter 4 room archive (castle content st2 had r200..r20f only) and no chapter 4 PS2 world package.
- `c4world`: ps2lib/world packages for 26 rooms + 1,410 picture keys.
- `c4gca` / `pmc4gca`: 26 room archives (base: ch4found16 rel31 SMD-released archives; Codex mirror for r221 r228 r22c)
  with PS2 objects, items, debris pictures, motion and PCM, plus the enemy archives em11 em13 em15 em16 em18 em25 em29
  em2d em3c (PS2 BIN geometry where the PS2 has the member, PS2 motion). Generator `tools/d367/worldch4/gen-all.sh`.
- `c4mov`: PS2 movies r213s00 r22bs00 r22as00; program knob `ROUTE_MOVIES_CH4B=1` (Disc 2 program only) plays them
  instead of the GameCube evd.

## Gaps left
- em24 has no PS2 input in the ps2cast inputs (skipped; castle content copy).
- em18 / em25 / em29: no BIN member converted (0 members matched); the merchant draws through its cast package.
- r229 room motion: the PS2 motion rewrite failed (a PS2 FCV shorter than its header); motion kept.
- Bosses (em2c, em38, em2b): lane boss-check.
- r217 / r221 death-demo movies (movie/r214_ev.sfd, r229_ev.sfd) use the Sofdec path (dmy fallback), as other chapters.
- Interior cells (CH-FIXES row 6): none for chapter 4 rooms (drawn unculled).

## Test tooling
- `worldch4/warps/<room>.txt`: entry preset per room (door destination, chapter, god, census).
- `worldch4/routes/ch4-4-N.txt`: room / door chain from each chapter start to its end.

## Status 2026-11-02 (hand-back)
- Commits: 754f2ba3e (data sets, ROUTE_MOVIES_CH4B, tools, warps, routes) + this doc update. Stores sealed:
  /root/re4data/private/{c4world,c4gca,pmc4gca,c4mov}-20261102 (not yet mirrored to re4-assets-private / manifest.py).
- Gates run: Disc 1 rP image f6f938e6 = rr 15ed29fe (all overlays identical); Disc 2 rP image 845f373d = rr, only
  st2_2 / st2_3 differ (r213 r22a r22b link RouteMoviePlay). Not run yet (testing later, user 11-02): Flycast room runs,
  Disc 2 GC-ASSET / CAST-GC / TEXCHK / VRAM / KOS 48 KiB with the new sets.
- Disc 2 size: about +98,600 sectors (st2 + em + mot 151.9 MB, worlds + pictures 35.6 MB, movies 13.6 MB) on 454,653
  -> about 553,200 sectors before packing. That is at the GD-ROM high-density limit (549,150) with chapters 3-2..3-4
  and 5 still to add: needs a capacity decision (each room ships both .dar and its .arc payload copy; ~half the st2 bytes).
- em16 was regenerated without a Disc 1 cast tree (the castle-gca-26 scratch was cleaned): rerun gen-em.sh with a
  Disc 1 release tree before landing and confirm em16 equals the first run (the other eight enemies matched).
- CH-FIXES-CARRY rows: 1/2/14 done by c4gca (16 GC samples kept, rows in the bank map); 5 already on (PS2_CH4_ENEMY +
  cap 4 in CH4REC, r214 documented exception); 15 resident lists exist in vram/resident for 22 rooms (r21a r221 r228
  r22a r22c missing) but the Disc 2 resident.bin is the castle one: needs the shared pack; 6 no cells; others global.
