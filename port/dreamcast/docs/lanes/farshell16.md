# Lane farshell16: far shell beyond the View distance cut (proof of concept, 2026-10-16)

User 10-16: "Try idea 1 at r101, r100 and the lake (r10b) since users can't see what's happening far in the horizon",
then "I do like the 12.5 option, we just need to have the shell solution too so players know where they are going."
Target: View distance Short (12.5 m) + far shell, shipping with VIEW_DIST_OPTION. Branch lane/farshell16 on
lane/viewdist16 (c3fedcaa). Knob FAR_SHELL (default 0, render only, needs VIEW_DIST_OPTION=1).

## What it does

At Near / Short the PS2 world's opaque pass stops at the cut as before. With FAR_SHELL=1 the fog, the PT / TR world
passes, actors and objects keep Full's far (25 m), and the room's far shell is drawn in the opaque list between the cut
and Full (`game/platform/far_shell.inc`, called from `native_ps2_world.cpp` after pass 0). The shell is built offline
(`tools/d367/farshell`, README there) from the room's PS2 world package: the opaque faces seen beyond the cut from the
room's reachable eyes, simplified (6000 triangles per room), each triangle textured with the world texture under it
and its prelit colour baked per corner. Its z is 1/w x 0.97 so the real world wins where the two overlap at the cut.
Warp line `farshell 0|1|2` (0 = the View distance cut as before, 1 = shell, 2 = opaque cut only, for pricing).

Deviation from the brief ("textures baked offline into an atlas"): tried first and rejected on evidence. A 512 x 512
atlas over the far-seen surface gives ~1.6 texels/m where 12.5-25 m needs 16-33 (a colour wash, preview in
farshell-20261016\work\r101\bake-evidence), and r101 has no VRAM for a bigger one (measured free 196,256 B, largest
block 12,288 B). The material shell reuses the world's resident textures: 0 B of new VRAM, original texel density.

## Cost (MODELLED, SH-4 hw model; console-fit column in brackets; not console measurements)

Build t15 recipe + VIEW_DIST_OPTION=1 + FAR_SHELL=1, PACE_MODE=off PC_SAMPLER_BYTES=8192 (W arm), 15 traced frames per
window, stride 60. Arms by warp line: F = Full; S = Short as VIEW_DIST_OPTION (every pass, fog and actors cut);
O = opaque world cut only (Full fog / PT / TR / actors, no shell); X3 = O + far shell v3. ms per frame (every tick draws).

| Scene (window, global frames) | Full | Short | O | Short + shell (X3) | shell draw fn | X3 vs Full |
|---|---|---|---|---|---|---|
| r101 cross, benchmark-r101-v3 (500:1399) | 65.03 (69.28) | 56.35 (60.04) | 58.26 (62.14) | 62.28 (66.33) | 2.83 (2.93) | -2.75 (-2.95) |
| r100 house siege, bench scene 2 pre window jump (1300:2199) | 69.18 (72.09) | 69.00 (71.89) | 69.24 (72.15) | 69.05 (71.98) | 0.43 (0.46) | -0.13 (-0.11) |
| r10b Del Lago boat, bench scene 3 (780:1679) | 69.24 (71.92) | 69.25 (71.86) | 69.18 (71.87) | 70.32 (73.20) | 0.33 (0.37) | +1.08 (+1.28) |

- r101 F / S from arm fs16arW, every O and the r100 / r10b F / S from fs16crW (earlier shell code; F / S / O never run
  it), X3 from fs16drW (final code = ce87185f content). Evidence C:\Flycast-Evidence\re4-dreamcast\farshell-20261016\
  hwmodel-fs16{,c,d}-<scene>-<arm>. The r10b X3 row carries +0.4 ms of effect work (EspDelete / Ps2fxClass) that the other arms do not: noise of
  the run, not the shell (the shell function itself is 0.33 ms).
- r101 cross: per drawn frame 92 groups, 3,537 vertices transformed, 4,470 strip vertices, 31 texture headers, 0 refused.
  The first C loop cost 2.31 ms for 1,723 vertices (505k instructions); the ftrv loop 2.83 ms for 3,537 (554k).
- Inside the house and on the lake the cut saves nothing (S = F): there is almost nothing beyond 12.5 m to cut.
- Where the money goes at the cross: Full -> O (opaque cut) -6.8 ms; + shell +4.0 ms; S - O = 1.9 ms is what keeping
  fog / PT / TR / actors at Full costs.

## Memory

| Room | .fsh bytes | groups / materials / vertices / triangles | static heap at room entry | VRAM new |
|---|---|---|---|---|
| r101 | 216,730 | 494 / 57 / 13,457 / 5,997 | 218,880 B (3,326,944 -> 3,108,064) | 0 |
| r100 | 222,018 | 455 / 25 / 14,177 / 5,995 | 224,192 B (3,295,136 -> 3,070,944) | 0 |
| r10b | 195,702 | 650 / 35 / 11,134 / 6,000 | 197,856 B (3,822,272 -> 3,624,416) | 0 |

The file is read at room entry with the PS2 world package (static heap, +2 KiB colour table) and freed with it, also
when the option is at Full, so switching to Short never reads the disc mid-room. (Superseded by lane farshell17: that
heap-4 block at every View distance starved r100 after the ambush and pulled the shell from test 16; the shell is now
read at Short only, lent to movies and given back when heap 4 runs short, docs/lanes/farshell17.md.) VRAM room log (VRAM_ROOM_LOG) is
identical in F / S / X runs: r101 pinned 2,313,784 free 196,256 largest 12,288; r100 pinned 1,281,760 free 1,228,320
largest 1,187,840; r10b pinned 2,210,336 free 299,744 largest 284,672; refusals 0, nocontig 0 in every run.
Reclaim check (fs_vram.py, coordinator 10-16): textures only ever seen beyond 12.5 m from any reachable eye are
r101 5 keys / 27,344 B (1 used by the shell), r100 0 B, r10b 6 keys / 23,472 B: the far world reuses the near world's
textures, so dropping "far textures" frees almost nothing.

## Look (Flycast stills, FARSHELL-SHEET.png in C:\Game Dev\Emulators\farshell-20261016)

Short + shell v3 is close to Full at the r101 cross (houses beyond the cut back), the r101 entry walk (moving pair:
hill, trees and the shed slide with the camera, no flat backdrop), r100 forest, the r100 rope bridge (cliffs back) and
the lake pier; through a shed window the village shows where Short shows fog. Where it gives itself away:
- thin things beyond the cut: fence slats and posts, wires, bare branches (trunks stay), props under 1.5 m: missing;
- PT foliage and TR surfaces are not in the shell (they stay at Full, which is why the opaque cut alone saves 6.8 ms
  not 8.7);
- decimated silhouettes and occasional texture smears where a corner's extended UV runs far from its source triangle;
- v1 (2,600 triangles) left holes in big rock faces (rope bridge): v3 uses 6,000 triangles and keeps far-off spikes.

## Gates (final code ce87185f)

| Gate | Result |
|---|---|
| Knob-off identity (t15 recipe rP, fs16yrP vs fs16vrP = viewdist16 c3fedcaa) | PASS: image c83c4195579f361b + 6 overlays + syms identical |
| _end | play rP +3,232 B (fs16zrP 8c420218 vs 8c41f578), trace rT +3,360 B |
| KOS squeeze 48 KiB (fp_twin fpfs16sqW from the FAR_SHELL=1 release arm, base t14cand tree) | 10/10 PASS, 0 OOM lines: fight min 12,704 B, call 43,304, door 19,464, leave100 12,904, leave103 12,904. The door pair first ran at 60 s and stopped before its r103 marker (0 OOM); rerun at 75 s with t15/int's kos_squeeze.sh (s30movie16 change) PASS. The base disc has no far-shell.fsh (fixture identity), so the shell's static-heap load is not in it; it does not use the KOS heap |
| STRICT + decisions at View distance Short (control fs16brT FAR_SHELL off vs fs16yrT FAR_SHELL=1, same fsh3 fixture) | fight STRICT 802 ticks, bell STRICT 397, door103 STRICT 1702 (rooms 0101 / 0103 / 0120), 0 overruns; decisions MUST-IDENTICAL 801 / 397 / 1701 |
| TEXCHK (fs16ymW, TEX_CHECK=2 MCHECK_LEONGC, Short + shell: r101 cross, r100 bridge, r10b pier) | 3/3 PASS, LEON-GC 0, pair missing 0, wrap 0 |
| VRAM room log | refusals 0, nocontig 0, dropped 0 in every F / S / X run; shell adds 0 B |
| Shell runtime | refused 0 headers in every run |

Evidence: C:\Flycast-Evidence\re4-dreamcast\farshell-20261016 (identity-*.txt, strict-sts3-*.json, decisions-sts3-*.json,
kos-sq.log + kos-sq-door75.log, *-tc runs, stills, hwmodel-*).

## Landing (10-16 evening; user: "short + far shell looks good")

Merged onto t15/int 43284ef9 (viewdist16 landed with its indoor rule, resident16). Recipe: T15REC + T15_FS
(FAR_SHELL=1; T15_FS="" builds the control). Data: T15_DATA + fsh = the approved v3 shells for r100 / r101
(re4-assets-private/farshell-20261016/fsh3/<room>/far-shell.fsh -> dc/native/<room>/far-shell.fsh; release kit:
add both files to the Build-Assets zip). r10b gets no file: viewdist16 never cuts the lakes (kViewRoomMin).
Change found while landing: shell mode (Full fog, PT / TR at Full) now needs the current room's shell loaded; before,
a room without a file (r103) at Short would have had Full fog over an opaque world cut at 12.5 m.

Vertex cut (coordinator 10-16), both measured negative, the approved v3 data ships:
- Continuous UVs (fs_uvfield.py): the source surface's UV at each shell vertex reproduces a shell triangle's own
  mapping on only 10-16 % of r101's triangles; field UVs everywhere would cut vertices 13,457 -> 8,689 but about half
  the triangles get a flipped or > 6x stretched texture (streaks): the look would change.
- Distance levels (FSH1 version 2, fsh5: a ~2000-triangle coarse level beyond 18.75 m): 3,397 vs 3,537 vertices per
  frame at the cross, shell 2.94 vs 2.83 ms (MODELLED), +79 KB per room: no gain, not used. The runtime keeps reading
  version 2 files (per-group boxes for culling, the cell box for the level choice).

Final numbers on the merged tree (hw model, MODELLED; console-fit in brackets; r101 cross benchmark-r101-v3, global
500:1399, arm fs16frW, T15_DATA + fsh3): Full 64.84 (69.20), Short 54.79 (58.49), opaque cut only 56.53 (60.39),
Short + shell 61.08 (65.10): -3.76 (-4.10) vs Full; shell draw 2.90 (2.99) ms, 3,537 vertices / 4,470 strip vertices /
92 groups / 31 headers per frame. r100 house siege: Short + shell 68.28 (71.16), shell 0.43 ms (the cut saves ~0
inside the house). Static heap: r101 218,880 B, r100 224,192 B (+2 KiB colour table each). VRAM: 0 B new; r101 room
log pinned 2,314,072 free 220,544 largest 10,240, r100 pinned 2,015,286 free 494,784 largest 387,072, refusals 0.

Gates on the final code (c13f20d1 image; docs after):
| Gate | Result |
|---|---|
| Knob-off identity (T15_FS="" rP fs16krP vs t15/int 43284ef9 rP fs16trP) | IDENTITY PASS (image + overlays + syms) |
| _end | rP +3,904 B (fs16hrP 8c422b58 vs 8c421c18), rT +4,064 B |
| KOS squeeze 48 KiB (fp_twin fpfs16sq2W from fs16hrP; base t14cand tree, no shell files on it) | 10/10 PASS, 0 OOM: fight min 10,336 B, call 40,936, door 17,096 (75 s), leave100 10,536, leave103 10,536 |
| STRICT + decisions at Short (fs16krT T15_FS="" vs fs16hrT; same T15_DATA + fsh fixture) | fight STRICT 802 ticks, bell 397, door103 1702 (rooms 0101 / 0103 / 0120), 0 overruns; decisions MUST-IDENTICAL 802 / 397 / 1701 |
| TEXCHK (fs16hmW, Short + shell: r101 cross, r101 entry walk, r100 bridge, r100 house interior) | 4/4 PASS, LEON-GC 0, pair missing 0 |
| VRAM room log | refusals 0, guard 0, nocontig 0 in every run |
| Indoor (r100 house interior, viewdist16 rule in) | interior unfogged as Full; the window shows the shell (cmp-indoor.png); the shed window at the r100 path shows the village (cmp-houseF-merged.png) |

## Vertex cut and Short only (10-16 late; user: "short shell + half vertices seems like the right balance")

Shipped: fsh6 (params v6) and the shell at Short only (`far_shell_cut_on()` needs View distance 2; Near keeps its plain
cut). r101 3,191 triangles / 6,634 vertices (v3 5,997 / 13,457), r100 2,886 / 7,044 (v3 5,995 / 14,177); files 119,744
/ 122,363 B (v3 216,730 / 222,018); static heap at room entry r101 121,888 B, r100 124,512 B (v3 218,880 / 224,192).
How: fs_blender.py weld 150 mm (was 20; the far-seen faces become connected sheets instead of a soup that is 80 % border
vertices), collapse to the budget weighted by `protect_by: border` (border vertices weight 0.3: plain collapse erodes
open sheets from their borders, which is what made v1 / v7 lose the r100 bridge cliffs and r101 roofs), and fs_pack.py
integer UV shifts (repeat-wrapped textures: a triangle's UVs move by whole tiles so neighbours share corners; same
pixels; -5 % vertices). Lost against v3: posts and slats thinner than ~15 cm beyond 12.5 m (welded away). The bridge
reads better (no floating plank shards).
Tried and dropped: continuous UVs (fs_uvfield.py: streaks on ~half the triangles), shared planar maps per cell
(fs_uvaffine.py: 11,640 vertices at best), corner UVs carried through the collapse (uv_mode loop: 12,492), plain
3,000-triangle collapse (7,093 vertices but holes in cliffs and houses), steep-face / distance weights (holes), a
coarse distance level (fsh5: no gain).

Final numbers on the merged tree e5c1d6f6 (lane + t15/int 6b5bc9b0: world32 r101, water16, Foliage Near default),
hw model MODELLED, console-fit in brackets, not console; r101 cross benchmark-r101-v3, global 500:1399, arm fs16mrW,
fixture t14rc package + T15 data after T14 incl. water16h, wv32r101 and fsh (= fsh6):
| Arm | ms / frame |
|---|---|
| Full | 60.69 (64.57) |
| Short | 50.37 (53.81) |
| Short + shell (fsh6) | 57.58 (61.38): -3.11 (-3.19) vs Full |
Shell draw 2.23 ms there (v3 on the pre-merge arm: 2.90); per frame at the cross 2,073 vertices / 90 groups (v3 3,537 /
92). Same arm and data before the merge (fs16frW): v3 61.1 -> v6 60.4, shell 2.90 -> 2.06. r100 house siege (fs16frW):
shell 0.43 -> 0.38 ms. The rest of Short + shell over Short is Full's fog, PT / TR world passes and actors beyond the cut.

Gates on the merged tree (evidence C:\Flycast-Evidencee4-dreamcastarshell-20261016):
| Gate | Result |
|---|---|
| Knob-off identity (T15_FS="" fs16nrP vs t15/int 6b5bc9b0 fs16urP) | IDENTITY PASS |
| _end | rP 8c4240f8 -> 8c425038 (+3,904 B) |
| STRICT + decisions at Short (fs16nrT T15_FS="" vs fs16mrT, fixtures with fsh6 + world32) | fight STRICT 802 ticks, bell 397, door103 1702, 0 overruns; decisions MUST-IDENTICAL 802 / 397 / 1701 |
| TEXCHK + stills (fs16mmW: r101 cross, walk B, r100 bridge, house window, shed window) | 5/5 fails 0, LEON-GC 0, MISSING / HALT 0; FARSHELL-V6-STILLS.png |
| VRAM room log | 0 B new; r101 pinned 2,314,072 free 220,544 largest 10,240; r100 pinned 2,015,286 free 494,784 largest 387,072; refusals / guard / nocontig 0 in every run |
| KOS squeeze 48 KiB (twin fpfs16sq3W from fs16mrP, release identity OK; base t14cand package, no shell files on it) | 10/10 PASS, 0 OOM: fight min 9,024 B, call 39,624, door 15,784 (75 s), leave100 9,224, leave103 9,224 |
## Next (not done)

- Remaining chapter 1 outdoor rooms (r103 farm, where the console cut saved 12.2 ms, r104 ... r10a): build a shell per
  room with tools/d367/farshell and add the room to DATA['fsh'].
- Console confirmation (geometry lever >= 3 ms: the trust policy needs a console A/B before an fps claim).
