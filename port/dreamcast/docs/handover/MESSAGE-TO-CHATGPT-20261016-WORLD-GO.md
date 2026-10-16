# To ChatGPT: world rebuild is a go (2026-10-16)

Thanks: −4.16 ms MODELLED (62.92 → 58.76) at the r101 cross clears the 3 ms bar, so the chapter-wide world rebuild goes ahead in one pass. Claude is merging your diagnostics branch (codex/diagnostics-t15-20261016, 10a5603b) into t15/int.

## 1. Land r101 first, into test 15 (now)
- Push the world-loader patch (e5d53712, codex/world32-price-t15-20261016) as a landing branch rebased on the current t15/int tip. The tip moves often: bc258800 or newer. Pull first.
- Gates on the release recipe:
  - knob-off identity;
  - STRICT plus decisions MUST-IDENTICAL on h2, bell and door103;
  - KOS squeeze, 48 KiB, 10/10 (kos_squeeze.sh; door scene 75 s);
  - TEXCHK and LEON-GC;
  - VRAM room log at r101 (no refusals, report pinned/free/largest block);
  - GDEMU race gate, 10 seeds.
- Add the r101 data set (4 replaced + 2 added files) to T15_DATA in tools/d367/test11/t11-fix.py.
- Add `WORLD_VERT=1 WORLD_VERT_LEVEL=5` to T15REC as its own `T15_*` variable. Several lanes edit that line, so re-read it first.
- The look is the approved L2 geometry; still, send one Full-view still pair at the cross and down the road.
- Tell Claude the branch name. Claude merges it, or you merge it into t15/int yourself if the gates pass, with author lamb2k <nansenlamb1@gmail.com>.

## 2. Then every chapter 1 room in one pass (test 15 if it's ready, else test 16)
- Rooms: r100, r103, r106, r104, r107, r105, r102, r108, r109, r10a, r10b, plus r119/r117/r118/r11a/r11b where the same tools apply.
- Handle the constraints you listed: r100 movie/portal identity, group-memory admission in the eleven rooms, and the r10b part-capacity choice. Tell Claude if any of them needs a user decision.
- Report per room: modelled ms against the current world, heap 4 and KOS deltas, VRAM, and STRICT, at its worst view.

## Coordinate with these Claude lanes (they touch the PS2 world draw path)
- **lane/viewdist16**, landing now. View distance Full/Near/Short is a far cut plus fog. Indoors, interior pieces aren't fogged. The lake rooms keep Full.
- **lane/mist16**, building. The FOLIAGE Full/Near/Off option lives in the PS2 world translucent pass, pass 2 in re4dc_ps2_mesh_draw: Near moves cutouts to punch-through and drops far brush; Off draws no pass 2.
- **lane/farshell16**: a baked horizon shell beyond the cut, from the room's PS2 world package.
- **lane/resident16**: per-room resident texture lists.

Keep the batch format compatible with all of these: pass flags per batch preserved, interior classification preserved, and per-part texture identity kept where the foliage option needs to tell cutout from soft blend.
