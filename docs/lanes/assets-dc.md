# Lane assets-dc: no GameCube asset, retroactively; every asset in Dreamcast form

User 2026-11-02: "Let's also ensure our no GameCube asset policy is applied retroactively to ensure all assets are
Dreamcast optimized including mip maps etc."

Base: origin/t15/int 15ed29fe5. Audited disc: rr candidate `RE4DC-RR/cand-15ed29fe` (Disc 1 gdemu track03), catalogs
from rr cycle `1102-0659-15ed29fe` (gca = Disc 1, gca2 = Disc 2). Audit scripts: `tools/d367/assetsdc/`
(texaudit.py, texbreak.py, reach.py). All numbers below are offline counts of disc bytes, not timings.

## Part A: GameCube or unproven rows (catalog, Disc 1)

Static reachability. "room-loaded" = in a route room's archive, so it is loaded at room entry; whether it is drawn
needs the runtime counter (the gate judges only its run windows).

| Kind | Prov | Reach | Rows | Example |
|---|---|---|---|---|
| texture | unknown | dc/tex.pak | 4148 | "source" materials: GC-picture-keyed replacements, provenance unproven |
| model | gc | room-loaded | 2016 | st1/r11a.arc |
| model | unknown | room-loaded | 855 | st1/r11d.arc |
| motion | gc | em/*.drs | 961 | em2f, em2b, em35, em22, pl0a... |
| model | gc | ss/ (sub screen) | 326 | ss/eng/ss_map.dat |
| model | gc | em/*.drs | 98 | em14, pl01 |
| geometry | unknown | dc/native registries | 73 | r102 registry.re4nmr (our derived data; needs a proof row) |
| movie | unknown | dc/movie | 42 | r100s40.seq (PS2 movies; needs proof rows) |
| motion | gc | ss / op / room | 41 + 24 + 38 | ss_wep28, op01.das, r104.arc |
| font | unknown | runtime harvest | 29 | |
| texture | gc | dc/tex.pak | 13 | |
| sound | gc | em/pl04.drs | 2 | |

Disc 2 (gca2): model gc 1998 (st2 room arcs 1620), motion gc 1390, sound gc 86, texture unknown 4125.
Reviewed GC sound samples: sound-kept-gc.tsv 322 rows (largest: pl07 21, pl02 19, r11b 15, r11d 13, r10f 13, r107 13).
Allowlist: 44 rows (unchanged so far).

Static actor reachability (ESL/EVD id -> drs) is not resolved by name search; the next step is the runtime counter over a
whole-route walk (every room, not the gate windows), which also splits "loaded" from "drawn".

## Part B: texture formats (Disc 1 dc/tex.pak, 7375 packages, 163.3 MB)

| Format | Payload | Mips | Count | Bytes |
|---|---|---|---|---|
| RGB565 | twiddled | no | 1061 | 54.6 MB |
| ARGB4444 | twiddled | no | 1392 | 35.5 MB |
| RGB565 | VQ | no | 2292 | 35.0 MB |
| RGB565 | VQ | yes | 1101 | 10.1 MB |
| ARGB4444 | twiddled | yes | 201 | 5.3 MB |
| ARGB4444 | VQ | no | 466 | 5.0 MB |
| PAL4+alpha | twiddled | no / yes | 489 / 154 | 1.4 / 0.6 MB |
| ARGB1555 | twiddled / VQ | mixed | 102 | 2.4 MB |
| PAL8+alpha | twiddled | yes | 2 | 0.1 MB |

All sizes are powers of two; none linear.

| Class | Count | Bytes | Raw 16-bit | Raw bytes | No mips (minified) | of them >= 64 px | VQ+mips would save |
|---|---|---|---|---|---|---|---|
| World, GC-keyed "source" | 3354 | 108.4 MB | 2087 | 81.7 MB | 3347 | 2841 | 64.1 MB |
| PS2 room objects | 2991 | 33.1 MB | 640 | 13.9 MB | 1658 | 1576 | 10.6 MB |
| Characters | 223 | 6.1 MB | 34 | 1.9 MB | 113 | 107 | 1.5 MB |
| World, PS2 source | 658 | 2.1 MB | 0 | 0 | 498 | 358 | 0 |
| Items, weapons, breakables | 145 | 0.7 MB | 27 | 0.2 MB | 139 | 123 | 0.1 MB |
| Total | 7375 | 150.5 MB | 2789 | 97.7 MB | 5757 | 5007 | 76.4 MB |

The saving column is disc and per-load VRAM bytes for the whole pack; per-room VRAM is the share of these keys a room
keeps resident (next step: join with the VRAM room log).

## Plan (priority = VRAM/RAM saved, then shimmer)

1. World "source" set: replace by the PS2 picture (part A) and convert to VQ + mips in the same pass (part B). 2087 raw
   textures, ~64 MB of pack, the largest VRAM share in every outdoor room. One data set, default off.
2. Room-object raw 16-bit (640) and missing mips (1658): VQ/PAL + mips, data set, default off.
3. Characters and items: mips on 113 + 139 minified textures; VQ the 61 raw ones.
4. Runtime GC counter over a whole-route walk (all rooms) to finish part A reachability for room arcs, drs motion, ss.
5. GC motion (961 + Disc 2 1390) and GC room models via the existing pm* and ps2_objects converters; sound-kept-gc.

Each batch: knob-off identity, GC-ASSET + CAST-GC PASS (allowlist <= 44), TEXCHK, VRAM per room, KOS 48 KiB, pixel diff.
