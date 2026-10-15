# Lane vram12: VRAM reclaim for test 12 (2026-10-14)

Owner: the VRAM reclaim lane (the user's graphics memory rule in the workspace CLAUDE.md). The VRAM map is
`C:\Game Dev\Emulators\VRAM-MAP-20261014.md`. Flycast numbers are MODELLED; the TA parameter figures come from the
TA_BIN_DIAG tiler model (stored bytes) and lane ms's flycast6 TA stats (TA input bytes, `RE4DC_TA_STATS`).

## TA vertex buffer: keep TA_VERTBUF_KB=2048

Per bank the vertex buffer is 2,000,896 B (2048 KiB, minus TA_HEADROOM 48,128 and MV_SHADOWS 48,128). Peaks per scene
(arm vr12dtW = test 11 recipe + TA_HASH=1 TA_BIN_DIAG=1 RENDER_OPTION=0 RES_MODES=0; evidence
`C:\Flycast-Evidence\re4-dreamcast\vram-map-20261014\ta-*`):

| Scene | TA input peak (flycast6) | Stored params, model peak / p99 | OPB pool peak (of 230,400) |
|---|---|---|---|
| benchmark-r101, room frames to 3600 | 2,026,272 | **1,756,744** / 1,754,376 | 140,224 |
| benchmark-r101, window to room frame 1500 | 1,638,656 | 1,418,664 / 1,405,424 | 101,664 |
| r101 house siege (crowd12) | 1,760,736 | 1,519,016 / 1,467,308 | 111,264 |
| r119 El Gigante (g3 segment, r118-r11a-r119) | 1,671,808 | 1,442,100 / 1,141,468 | 100,448 |
| r117 (ch21 segment) | 908,672 | 819,744 / 760,728 | 98,560 |
| r105 (ch12 segment) | 880,736 | 823,140 / 681,360 | 72,480 |
| r11b (segment) | 723,136 | 615,880 / 592,696 | 52,256 |

The worst scene uses 88% of a bank (margin 244,152 B, 12%). 1920 KiB would leave 6%, 1792 KiB would overflow the
benchmark's late phase. 2048 was chosen in 700e2d02 (2026-09-23): r100 needed ~1,031 KB of TA parameters per frame,
over the 1024 KiB bank on hardware; the 10-02 console check measured 1.67 MB of TA input in the r101 fight.

## Data set blackgc14v (in this branch's t11-fix.py; data only)

`tools/d367/vram/vq_pak.py` re-encodes r101's 12 large 16-bit PS2 world textures (ARGB4444, >= 16 KiB; keys from
`ps2_world_data.inc`, census `tools/d367/vram/ps2tex_census.py`) as full-codebook VQ with the pinned KOS pvrtex: same
keys, native sizes, 16-bit format, material names and CRC rule. 458,752 -> 81,920 B (-376,832). The 11 small ones
(<= 4 KiB) stay 16-bit (VQ would be larger). PSNR 29.7-50.2 dB. `blackgc14vl` adds Leon's atlas as VQ (LVQ,
524,288 -> 67,584 B; needs the user's look decision).

Gates (binary unchanged, so knob-off identity holds by construction; the play ELF is not rebuilt):
- STRICT + decisions, r101 bell-warp, trace arm vr12tT, stop tick 2000: STRICT (2002 ticks, 0 masked), decisions
  MUST-IDENTICAL (`strict-bell-ps2vq-*`).
- TEX_CHECK=2 (vr12mW) on benchmark-r101: fails=0 meta_changes=0 vram_changes=0 (`texchk-ps2vq`).
- Census (vmaptW, benchmark-r101, frames to 1800) vs the release pak: preload 1,956,736 -> 1,579,904 B; "no
  contiguous block" 4 -> 0; effect sprites queued 25,095 -> 41,900, missing 36,188 -> 19,336. With LVQ as well:
  queued 56,697, missing 4,433, fragmentation retries 417 -> 215.
- Look: `vram-map-20261014\sheets` (texture sheet ps2vq-sheet.png, r101 stills r101-ps2vq-pair/crop.png).

## D4: per-room VRAM report and the VRAM gaps gate (VRAM_ROOM_LOG=1, 2026-10-15)

The graphics memory rule asks for each room's VRAM use in benchmark and full-play logs and for refusals, "no
contiguous block" failures and GameCube fallbacks to fail a check. `VRAM_ROOM_LOG=1` (Makefile, render/log only,
default 0, needs UI_VRAM=1 VRAM_PAGES=1; in the test 12 recipe T12REC) logs, at each room-entry preload pass, every
600 frames and at the room change ("exit": the visit's minima and counters):

- `vram room:` pinned (cache bytes drawn in the last 60 frames, leased or pool-pinned), dynamic (other resident cache
  bytes), other (non-cache allocations and page padding), free, largest free block, the visit's min free / min
  largest / peak pinned, and the visit's uploads, evictions and fragmentation retries.
- `vram gaps:` the visit's budget refusals, thrash-guard skips (guard, and guard_p = those while the cache was
  evicting: VRAM pressure; the rest are the 4-new-loads-per-frame cap), no contiguous block, latched, absent packages,
  GameCube effect pictures (gc_fx, FX_PS2_PACK=1), WORLD_HOLE_FIX dropped parts, effect sprites past the queue, model
  parts without their texture, silent AICA bank blocks (snd_fail) and AICA bytes in use.
- `vram gc-fx:` each GameCube-picture effect key (first 64 per visit).

Cost: one profile-source read and pvr_mem_available() per frame, a 448-entry walk plus the allocator census every 30
frames and at each sample; about 1 KB of BSS. Knob off: play image byte-identical (ident.sh vd4otP vs t12rctP).

Gates: `tools/d367/vram/vram_gate.py <run-output.txt>` (benchmark; bench-run.sh runs it after bench-ms.py) and
`fullplay/fp_check.py` (every segment; REPORT.md gets a "VRAM per room" table). They fail on refusals, guard_p,
nocontig and gc-fx keys that ps2lib/INDEX.tsv does not list as ps2_source=NONE. Keys map to INDEX rows through
`ps2lib/effects-tex/KEYS.tsv` (`tools/d367/vram/fx_keys.py <ps2lib>`, re-run after fx_ps2_pack.py lib). Logs from
builds without the knob (test 11) are judged on rejects= and "no contiguous block" only; their thrash-guard count has no
pressure split and is noted, not failed (no new failures on the test 11 candidate gate logs g5b-183453 / pcr2-193643).

D4 gates (cedae1ad + knob file):
- Knob off: IDENTITY PASS vd4otP vs t12rctP (18c392a9; image 2292926655b1d52f, every overlay and syms identical).
- r101 bell trace pair vd4otT vs vd4tT (T12_DATA, stop tick 1802): STRICT, 1804 compared, 0 masked; decisions
  MUST-IDENTICAL over ticks 0..1802. Evidence: vram-map-20261014\d4-tr-bell-{off,on}, strict-d4-bell-*.
- Test 11 candidate gate logs (fullplay-20261014 g5b-183453, 20 segments; pcr2-193643, 8 segments), re-checked with the
  new fp_check: no new failures.
- r101 benchmark on the knob-on arm (d4-bench-b; MODELLED): min free 82,336 B, min largest block 3,072 B, 149 uploads
  after the preload, 40 evictions, 20 frag retries. The gate FAILS on 85 thrash-guard skips under pressure and 17
  GameCube effect pictures: 10 common core.das ids NOT_CONVERTED in ps2lib, 7 em13 enemy-effect pictures with no
  ps2lib row. These are real gaps, not false fails.

## D5: r101 gaps fixed (PS2 effect pictures, shrink, KOS-aware resident set; 2026-10-15)

Coordinator decision on D4: fix the gaps rather than excuse them. Commit 952e8fbf + the knob-file/doc commit. Base:
t12/rc-dry f01fcc53 + D4.

**1. GameCube effect pictures, 17 → 0.**
- fx_ps2_pack.py now decodes PS2 PSMT4/PSMT8 pictures: GS swizzle and CSM1 256-colour CLUT, via
  test12fx/ps2_tpl_decode.py.
- The 10 core.das ids that were NOT_CONVERTED are converted. ps2lib now has no NOT_CONVERTED effects-tex rows (523
  rows; 40 newly converted).
- `lib` converts the enemies' own EFFs (em11..em35, 287 rows). em13's 7 pictures share keys with em11, so their
  packages sit in folder em11.
- KEYS.tsv was regenerated: 1865 rows, 728 keys.
- Sheets: `vram-map-20261014\sheets\d5-fx-core-ps2.png` and `d5-fx-em11-ps2.png`, with columns GC | PS2 decode | DC
  PAL4.
- Two look notes for the user:
  - The GameCube glows are opaque I8 grey; the PS2 pictures carry alpha, as with fx12's earlier rows.
  - em11 0x3c and 0x4b are 32x32 on PS2, against 48x48 on GameCube.

**2. Shrink before evicting.**
- r101's 52 16-bit twiddled source textures of 64x64 or more (not effect pictures) are now full-codebook VQ:
  - VRAM 614,400 → 183,296 B.
  - PSNR 29.0..50.2 dB.
  - Keys in `vram/vq16-r101.txt`.
  - Sheet: `d5-vq16-worst16.png`.
- All r101 effect flipbooks are now PS2 PAL4: 102 packages, 201 KB.
- `test12/t12-texpak.sh` builds tex.pak (sha256 5e6ca522…, 4385 packages) and `resident.bin` reproducibly.
- `PRELOAD_LARGE_FIRST=1`: the preload loads its picks of 16 KiB or more first, then the rest, as two forward sweeps
  in disc order. On the benchmark the minimum largest free block went from 301,728 to 397,280 B.

**3. Resident set: 0 uploads after the preload.** Once VRAM was shrunk, the binding limit became the KOS heap:

- Every open texture package keeps its descriptor in the KOS heap: 184 B, in three blocks.
- ARENA_FIT leaves about 138 KB of KOS heap at r101 entry. The native model slab takes 64 KiB of it.
- With D5 data and no other change, the heap filled at about 330 packages. The result was 1,604 failed loads, tex.pak
  sector read errors, and motion files that could not open.

The fixes:

- `TEX_META_EVICT=1`:
  - A streamed package uses one KOS block (160 B).
  - The cache keeps 8 KiB of KOS heap free by evicting least recently used uploads.
  - A refused descriptor evicts and opens again.
  - The native model slab is allocated before the first room-entry preload. Without that, a trial that preloaded the
    set took the slab's memory and turned the native model path off in r101.
  - `kos=` is logged in the gaps line and in each upload line.
- `ROOM_RESIDENT=1`:
  - `dc/resident.bin` holds per-room lists of first-sight textures, built from `vram/resident/r101.tsv`: 152 keys
    from the benchmark and bell logs (`vram/resident_keys.py list|pack`).
  - The lists join each room-entry preload under the usual slot and byte limits.
- The preload stops at the KOS reserve.

`vram_gate.py` now also fails on:

- tex_rej (rejected texture packages);
- KOS heap failure lines (sbrk refused, model slab, motion read retry);
- any upload after the preload in a room with a resident list. fp_check only reports these.

Its table adds the Tex rej, KOS evict and Min KOS columns.

r101 benchmark, test 12 recipe + D5 data (MODELLED, Flycast; d11-bench-slab):

| Measure | D4 (d4-bench-b) | D5 |
|---|---|---|
| min free / min largest block | 82,336 / 3,072 B | 266,400 / 81,920 B |
| uploads after preload / evictions | 149 / 40 | 0 / 0 |
| guard_p / refusals / nocontig / gc_fx / tex_rej | 85 / 0 / 0 / 17 / 0 | 0 / 0 / 0 / 0 / 0 |
| KOS evictions / min KOS headroom | - | 0 / 8,456 B |

The bell segment (d5-tr-bell-on2) has the same zeros.

Gates:

- Knob off: IDENTITY PASS vd5otP vs vd4otP (which matched t12rctP at D4).
- Bell pair d4-tr-bell-off vs d5-tr-bell-on2 (vd5ftT, D5 data, stop 1802): STRICT, 1804/1804 compared. Decisions are
  MUST-IDENTICAL over 0..1802.
- TEX_CHECK (vd5fmW, benchmark): 0 fails.
- test 11 gate logs: no new vram failures. The two new [route] failures come from other lanes' route rules.

Speed, two models reported separately:

| Measure | Knobs off + RC data | D5 | Change |
|---|---|---|---|
| Flycast (bench-ms.py, window 300..1200) | 17.20 fps (d4-bench-b) | 17.77 fps (d11-bench-slab) | +3.3% (spread 3.2%) |
| SH-4 hw model (bench-hw.sh, frames 500..1399) | 69.60 ms (vd5-off-r101) | 71.23 ms (vd5-on-r101) | +1.63 ms (+2.3%) |

The hw-model change is inside the band (low 59.7..61.0, high 84.1..86.6). Counted instructions per frame differ by
only +0.2% (11.08M → 11.10M). Part of it is VRAM_ROOM_LOG's per-frame tracking (frame/TA/UI +0.51).

Image growth: tP end 8c40fe9c → 8c41037c (+1,248 B), tT +1,280 B. At D4 the arena fit already differed by 4 KiB
between the bell on and off runs, and that run was still STRICT.

Data for the RC:

- T12_DATA's t12tex now includes `dc/resident.bin`. t11-fix.py asserts it exists, so the RC lead reruns
  `test12/t12-texpak.sh`, which writes resident.bin next to tex-t12b.pak.
- `T12D=<dir>` points the set at a lane's own data.

Knob file: `test12/release-knobs.txt` comes from out-vd5ftP (117 knobs; image sha256 757a7a70…).
