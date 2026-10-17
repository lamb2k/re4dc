# PS2 head-burst stumps and hand poses (lane stump17, 2026-10-17)

Coordinator 10-17, after CAST-GC found the r200 em12 head-burst stump (castgc17.md): "the user's rule is no GC
fallback, so don't park the stump work in test 18 ... PS2 stump conversions for BIN 475/447/479/483 (em15 460), with
ACTOR_GANADO_PS2_STUMP covering all appearances", then "Go ahead with hand poses 449/450/454/455 ... Move the
stump/hand descriptors/tables out of the program image into loaded data".

The PS2 Ganado cast has five appearances, each with a body, a head and two hands. During play em10 swaps infos the
cast had no row for, and the whole Ganado then fell back to the GameCube path:

- em10HeadSet (src/em10/em10.cpp) swaps the head to mot[3], the lost-head stump, when a kill lands on the head (partsNo
  5) or is a critical: BIN 475 / 447 / 479 / 483 / 460 for appearances 0..4.
- em10HandSet type 1 / cEm10::setHand(1) (events): 449 right, 454 left. em10HandSet type 2 (the alert pose): 450 right
  (left stays 453), or with the left-handed flag 0x01000000 455 left (right stays 448). cEm10::setHand(2) returns early.

## What ACTOR_GANADO_PS2_STUMP=1 does now (default 0)

- Conversions: `ps2_cast.py` presets `ganado-<app>-stump`, `ganado-<app>-h1` / `-h2` (stumps of em12-01 / em15-00 /
  em15-04 / em15-0b, hands of all five); each stump matches the GC BIN (0 mm); hand chunks are the same geometry for
  every appearance and use the appearance's atlas.
- `tools/d367/ps2_ganado_stump.py` (v3) writes the disc package `dc/native/ganado/ganado_var.re4gv` ('RGV1', 9 records:
  5 stumps + 4 hands, 18,368 B, sha256 15525a04...) and a private header with its layout and FNV-1a digests only
  (no mesh bytes in the program). Private store `/root/re4data/private/stump17-20261017` (header, package, manifest,
  SHA256SUMS); data set `stump17` in test11/t11-fix.py (STUMP17D). Public facts: `game/actor_material_records_ps2_stump.inc`.
- Runtime (`coarse_actor_owner_ganado.inc` ganado_var): the first owner plan in a room that selects a variant reads the
  package into one heap-4 room cell (re4dc_static_alloc: 18,368 + 1,248 B skin groups + 32), checks names / atlas keys /
  header / records / digests, proves the immutable chunks and builds the FTRV skin groups. Room leave frees it. A route
  movie whose heap-4 staging falls short borrows it (native_movie.cpp, like the model cache loan); the next variant
  plan after the movie reads it again. Not loaded (no file, bad bytes, three failures in the room, lent): the plan
  declines and that Ganado keeps the source path, as before.
- Binding: role rows for the 5 stumps and 4 hands x 5 appearances, source blobs for the 9 BINs; owner_ganado_bind
  accepts the package's hand BINs. One stump near gate per appearance (kStumpGateApp + a) shares the gate pool.
- Room for the extra identity rows (all under the knob, the knob-off layout unchanged):
  - fixed roles 63 -> 88 and blobs 30 -> 39 with the pool recipe; r117's room package needs 42 roles / 31 blobs, so the
    pool layout takes the ROLES5 widths (160 role bits, 128 blob bits); ROLES5 plus the knob 192 role bits.
  - a Ganado archive admits up to 8 more assets (em12 / em13 / em15): lifetime assets 48 -> 64, SS_CERT park 16 -> 24.
    At 16 the r100 s20 movie window revoked em12's archive (12 -> 20 assets) and r100's Ganados drew GC for the rest
    of the room (h2: 2,753 GC rows) - found by the h2 gate, fixed in 0bea8b48.
  - kGatePool stays kTierApps x kBones x 2 (a gate app takes 28..31 balls; at most 141 of 680 seen in use).
- Rig (dbgwarp, warp arms only): `killpart <partsNo>`, `killnear`, `handpose <frame> <type 1|2|4> <em id>`,
  `bring <distance> [side]`. Warps in tools/d367/castgc/warps: stump-r101 / -r103 / -r200 (every kill a head shot),
  stump-still-r101, hand1 / hand2 / hand4-still-r101.

## Cost (lane/stump17 b0e325db on t15/int 9965feae; Flycast emulator measurements)

| | knob off | knob on | delta |
|---|---|---|---|
| play image rP _end | 8c407e38 | 8c408d38 | +3,840 B (.text +3,776, .rodata +64) |
| character data block (16 KiB padded) rP / rW | 0x74440 / 0x757e0 | 0x76ae0 / 0x77e80 | +9,888 B inside the block: 5,408 B (rP) / 384 B (rW) left before the next 16 KiB step |
| s30 heap_before (rW, h2 and h2k, T17V_DATA + stump17) | 150,848 | 146,752 | -4,096 (one ARENA_FIT 4 KiB step); 340/340 both |
| KOS free at s30 | 18,656 | 18,880 | +224 (ARENA_FIT slack) |
| heap 4 while a variant is in use | - | 19,648 B room cell | only in a room that draws a stump / hand pose; freed at leave; lent to movies |

The 18.1 KB static of the v2 header (meshes in the image) is gone: only code, digests and the identity tables stay.

## Gates (Flycast, <= 60 s per run except h2 through s30, census period 30)

| Gate | Result |
|---|---|
| CAST-GC head-shot rigs, knob on (s30erW) | stump-r101 PASS (0 GC; off: 2,401 GC rows), stump-r103 PASS, stump-r200 PASS. Every stump BIN drawn (GANADOVAR first k=0..4) |
| CAST-GC normal rigs r101 / r103 / r200, h2, h2k | PASS (0 GC / MIXED) |
| cast16 near-kill rig near-r101 (extra gate) | PASS 0 GC (off: 628 GC rows; hand 450 drawn, k=6) |
| With / without NATIVE_MODEL_REGISTRY_DYING | on 466d8ca7 (no DYING) r101 kept 76..91 GC rows, all semantics=3 (fades); with DYING cherry-picked both rigs PASS 0, DYING alone 388 / 2,073. On 9965feae DYING is in T15REC: PASS above |
| Still pairs (stills-20261017) | stump 447 and hand poses 449/454, 450, 455 drawn PS2 (knob on) vs GameCube (off), same frame |
| s30 | 340/340, heap_before above, 0 Em set / allocation failures |
| KOS squeeze 48 KiB | 10/10 PASS (fight min 6,072 B, call 25,800, door 12,040, leave 6,280), 0 OOM |
| Knob-off identity rP vs t15/int 9965feae | IMAGE IDENTICAL (4fea9a2e, 14 overlays, symbols); rT / rW differ only in dbgwarp_bridge (the rig) |
| Host test tests/test_actor_ganado_ps2_stump.py | PASS 4 configurations, also ASan / UBSan (package through a kos/fs.h shim: stump 479, hands 450 / 454, a flipped byte and a missing file refused, room leave, lend / return) |

Evidence: C:\Flycast-Evidence\re4-dreamcast\castgc17-20261017 (g30-* / g30o-* CAST-GC, w30e-* / w30o-* h2 through s30,
p1-* / p0-* stills, kon-* KOS, y24-* / z24-* the DYING pair, stills-20261017\*-pair-crop.png).

## Landing (not done in the lane)

- Recipe: ACTOR_GANADO_PS2_STUMP=1 ACTOR_GANADO_PS2_STUMP_DIR=<private stump17 dir>; data set `stump17` in the test 17
  data line (T17V_DATA) and the release `--disc-sets`.
- Kit: the private dir (header) and the package go in the Build-Assets zip; build-public.sh builds the knob off when
  they are absent.
- Then remove the r200 `12` row from tools/d367/castgc/allow.tsv.

## em14 / em16 / em17 pool heads (round 2, 10-17)

The "not covered" line above meant the ACTOR_GANADO_PS2_STUMP package, not the registry pools. These models do not
take that path: their hit-head BINs are sections of the pool descriptors, converted from the PS2 (no GameCube
fallback):

- em14 types 7 / 8 / 9: stump 0x1FF and parasite head 0x200 are `head-hit` / `head-hit2` sections of
  zealot-em14-07p / 08p / 09p (ps2_cast.py `_zealot_pool`; package ps2-ch3-em14p.json, rooms r20f, r211, r214, r227).
  The test 17 recipe has no chapter 3 / 4 rooms or warps, so no head-burst rig runs on it; the ch3 / ch4 lanes' recipes
  own that gate (CAST-GC kill rig with `killpart 5` in r20f).
- em17 type 12 / em16 type 12: stump 0x1D0 is `head-hit` of ganado-em17-0cp (r108 / r113 / r118 packages); em16 type 11:
  0x1CC is `head-hit` of ganado-em16-0bp (r11d).

Gate (lane/stump17b, t15/int 71f81002, census arm s33erW = ch2-build.sh rW with the census at period 30, data T17V_DATA,
60 s each, evidence castgc17-202610171-*): `castgc/warps/stump-r108 / -r111 / -r113 / -r11d.txt` are the ch2 kill
rigs plus `killpart 5` (every kill lands on the head). CAST-GC PASS in all four, 0 GC / MIXED rows:

| Room | Kills (60 s) | em rows | Result |
|---|---|---|---|
| r108 em17 | first at frame 303 (3 hits) | PS2 19,980, ganado-em17-0cp | PASS |
| r113 em17 | first at 307 (7 hits), 28 repeats armed | CROWD-SKIP (not GC) | PASS |
| r111 em17 | armed, no kill in the window (Ganado cast PS2 300 rows) | PS2 | PASS (weak: no kill) |
| r11d em16 | first at 304 (4 hits) | PS2 405, ganado-em16-0bp | PASS |

A diag build (atx-tpl patch, ACTOR_TRANSACTION_DIAG=1, s33grW) over r108 / r11d: no ATX_INFO decline row after the
kills. Not proven: a head-burst on an em16 type 12 Ganado (the rig kills the nearest em16, type not logged), r111 /
r113 kills with the corpse in view (r111 no kill, r113 skipped by the crowd policy). Image and data are unchanged
(warps and this doc only): knob-off identity, STRICT trio, s30 and KOS are unchanged from the stump17 gates above.
