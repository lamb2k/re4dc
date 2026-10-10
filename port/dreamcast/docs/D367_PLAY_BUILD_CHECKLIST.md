# D367 play build checklist (user, 2026-10-09 current state at top)

## 2026-10-10: WATER45_NATIVE (r10b lake water, play recipe)

No new flag: ROUTE_CH13=1 now also brings **WATER45_NATIVE=1** (the lake surface drawn natively, the PS2's r10b
sprite set). No new staged file. Check: r10b dock and boat views show dark water, no pale sheet (route doc "r10b lake water").

## 2026-10-10: stream 1:148 (the r11b radio call voice) in bgm/aica_str.dat

Stage **bgm/aica_str.dat built with `aica_banks.py streams --mirror <LE mirror with the .sbb> --out DIR --streams
ch21`** (16,504,832 B, sha256 c49229aa..; lane r11b rooms/str-r11b-ch21, staged by lane r11b mkfix r11b()): the r11b
14-stream file plus 1:148 appended (earlier entries byte-identical after the header). Check: on r11b entry `stream
1:148 start` after 1:3, no "sbb=9900000 not in aica_str.dat". Still silent, not covered: 0:29 on the chapter 1-3
results screen (route doc "stream 1:148").

## 2026-10-10: material pair 18d0fd82-2c9a9309 (r10b / r11b, disc data)

Add **dc/tex/1/18d0fd82-2c9a9309.re4tex** (/root/probe/lanes/route/pairs-r11b, VQ, 18,576 B) to the texture set
that goes into the pack: lane r11b tools/mkfix.py r11b() now does (r11b / r11a discs); a chapter 1-3-only disc needs
it too (r10b opens it after s00). Rebuild: `tools/d367/pairs_from_log.py --iso <GC disc 1> --file st1/r11b.das --log
<run log with its "pair missing" line> --output DIR`, then vq_native_ui.py --model-min-bytes 16384 (route doc "material
pair 18d0fd82"). pack-fixture.sh packs only the staged loose dc/tex files and its output replaces the fixture's
existing dc/tex.pak: merge the catalog pack (d87983e1) in first. Check: no `open failed` for 18d0fd82 in r10b / r11b.

## 2026-10-10: WATER42_GRID_SKIP (r10a / r11a lake water, play recipe)

No new flag: ROUTE_CH13=1 now also brings **WATER42_GRID_SKIP=1** (espgen42 keeps only its water plane; the height
grid and its per-frame update are gone; init RNG draws kept). No disc change. r11a quiet 58.8 -> 41.2 hw ms of work
(Flycast 22 -> 30 fps), Ganados 68.1 -> 49.3; heap 4 +1.1 MB in r11a, +1.0 MB in r10a. `WATER42_GRID_SKIP=0` restores
the grid. Gates: docs/lanes/route.md "WATER42_GRID_SKIP".

## 2026-10-10: next TEST build adds PVR_READY_STRICT=1 PVR_LATCH=1 (issue 9; not the play recipe yet)

For the next console test disc (the r108 -> r109 bridge door hang, issue 9) add **PVR_READY_STRICT=1 PVR_LATCH=1**
to the route-build.sh play flags (both need CRASH_SCREEN=1 and PVR_PIPELINE=2, already in the recipe). They go into
the default play recipe only after a console confirms. No disc change.
- PVR_READY_STRICT (default 0; knob-off image byte-identical apart from the time stamp): KOS's
  pvr_start_ta_rendering() ignores pvr_wait_ready()'s 100 ms timeout and writes the next scene into the TA bank whose
  previous scene was never handed to a render (and, with one bank, into the bank being rendered). Link wraps of
  pvr_list_begin / pvr_set_presort_mode keep waiting in 100 ms slices (bounded at 10 s, then the stop screen names
  the wait); present_fence keeps waiting for pvr_present_wait the same way instead of stopping after one 100 ms
  wait. platform/native_ui.cpp namespace pvr_ready documents every PVR wait that was checked.
- With PVR_LATCH the stop screen gets a row `rdy K<n> Q<n> Y<n> first <ui frame> last <ui frame>` (expired slices:
  K TA bank, Q render done, Y present fence; `rdy K0 Q0 Y0` = the path never fired) and the event ring the codes
  K / Q / Y. Test aid: dc/crashtest.txt `pvrwait` (never on a play disc) forces three K slices and the stop screen.
- Gates (D:/Flycast-Evidence/re4-dreamcast/kosfix-20261010): see docs/lanes/route.md "PVR_READY_STRICT".

## 2026-10-10: SBB_STUB=1, the GC stream banks leave the disc (play recipe)

Play ELF: add **SBB_STUB=1** to the route-build.sh flags below (r11b / r10b recipes). Disc: **remove
bgm/bio4bgm.sbb (139,395,072 B) and bgm/bio4evt.sbb (193,495,040 B)**: 332,890,112 B (162,544 sectors) leave
track 3; no new file is staged (keep bgm/bio4str.hed and bgm/aica_str.dat). Why it is safe: the recovered stream
player (src/game/snd_str*.cpp) only opens the banks (DVDOpen in Snd_str_init; SndStrReq refuses a stream whose
FileTbl entry is -1). Its headers (lengths, loop points, rates, the .sbb offsets aica_str.dat is keyed by) come from
bio4str.hed; its only reads of the banks are the wrapped, skipped ones (platform/audio_strm.cpp
__wrap_DVDReadAsyncPrio, every build since the AICA work); the heard audio is aica_str.dat. With the knob,
platform/dvd.cpp gives both FileTbl entries their retail size without opening them, so entry numbers,
DVDFileInfo.length and every stream state are unchanged. A knob-off ELF needs the banks on the disc (every stream
request would fail "SND: File Not Found"). aica_banks.py still reads the banks from the source mirror
(/root/re4data), never from a staged disc. io_probe.cpp (IO_PROBE builds) still names them: not for play discs.
Gates (lane sbb, evidence D:/Flycast-Evidence/re4-dreamcast/sbb-20261010): see docs/lanes/route.md "SBB_STUB".

## 2026-10-10: r119 (El Gigante, after r11a) staging recipe (not built, not released)

The r11a recipe with ROUTE_CH21=1 SBB_STUB=1; the build writes a fifth overlay, **em2b.ovl: stage dc/em2b.ovl**.
Add (lane r119 tools/mkfix.py `base`): st1/r119.arc (released) + st1/r119.dar (aica-r119), **em/em2b.drs = the
prepared archive** (prepare_enemy_motions --textures tex-em2b, then aica_banks; the GC body does not fit heap 4) and
its 89 motion keys dc/mot/*.fcv, bgm/aica_str.dat with stream 0:5, dc/native/r119/{MAINSCENARIO.re4mesh,
ps2-world.r4pw/.re4mesh/.ids}, dc/movie/r119s00/s10/s20/s30.seq, and the r119 / em2b / PS2 world textures (VQ
overlays first) plus pair 41387140-38190dc7 (into the pack). Checks: r11a door 0 -> r119, the four movies, the
giant textured, door 0 / 6 "Coming Soon", door 1 -> r11a.

## 2026-10-10: r11a (chapter 2-1, after r11b) staging recipe (not built, not released)

The r11b recipe below with SBB_STUB=1; no new build flag (ROUTE_CH21=1 covers r11a). Add (lane r11a tools/mkfix.py
`base`): st1/r11a.arc (released) + st1/r11a.dar (aica-r11a: ROOM / FOOT / em12 / em24 prebuilt),
dc/native/r11a/{MAINSCENARIO.re4mesh, ps2-world.r4pw/.re4mesh/.ids}, and the r11a + r11a PS2 world textures (into
the pack). em12 / em24 .drs, bio4midi.dat and aica_str.dat stay as r11b's. Disc +11.3 MB. Checks: r11b door 0 ->
r11a, r11a door 0 -> "Coming Soon" (r119), door 1 -> r11b, the Ganados at the r119 door.

## 2026-10-10: r11b (chapter 2-1's start) staging recipe (not built, not released)

The r10b recipe below plus ROUTE_CH21=1 on the play ELF; the build writes a fourth overlay, **em22.ovl: stage
dc/em22.ovl** with dc/pl0f.ovl + dc/em2f.ovl. Add (lane r11b tools/mkfix.py `base`): **etc/emleon01.esl le_mirror'd**
(the disc carried the raw GC file; without it R11bInit hangs), st1/r11b.arc + r11b.dar, em/em22.drs (rel-stripped;
**drop it from the r10b removal list**), bgm/aica_str.dat with streams 0:17 + 1:36 + 1:148 (`--streams ch21`, 16,504,832 B), bgm/bio4midi.dat
with #10 prebuilt, dc/native/r11b/{MAINSCENARIO.re4mesh, ps2-world.r4pw/.re4mesh/.ids}, dc/movie/r11bs00.seq,
the r11b + em22 + PS2 world textures and the material pair 18d0fd82 (pairs-r11b) (into the pack). Disc +31.5 MB loose (~42 MB free on track03). Checks: the
chapter 1-3 save, door 6 into r11b, s00, the radio call, the ambush, the three "Coming Soon" doors.
With SBB_STUB=1 (section above) also remove bgm/bio4bgm.sbb and bgm/bio4evt.sbb: track03 then has ~343 MB free (~10 MB + 332.9 MB).

## 2026-10-10: r10b (chapter 1-3's end) play disc staging recipe (not built, not released)

Play ELF = route-build.sh with the 2026-10-09 test-build flags plus `PRIM_CAP_R10B=327680` (DBG_WARP=0
PC_SAMPLER=0 PACE_DEBUG=1 ROUTE_CH13=1 ACT_CAP=0 PS2_INTERIOR_ACTORS=2 GAME_ATLIST_OVERFLOW=1 GAME_ATLIST_512=1
LEON_NATIVE_PIPE=0 LEON_FACE_LAZY=0 NATIVE_LASER=1 ACTOR_GANADO_SOURCE_LIGHT=0 PRIM_CAP_R10B=327680). ROUTE_CH13=1
brings ROUTE_OVL=1, WATER45_GRID_SKIP=1 and the em27 slot fix by default. The build writes **three overlays next to
the ELF: sscrn.ovl, pl0f.ovl, em2f.ovl.** Never stage the warp test aid (r10b-warp-testaid.patch) into a play image.

Disc = the 2026-10-09 test disc contents (631cb271 fixture + tex pak d87983e1 + the audio overlay) plus r10b
(lane r10b tools/mkfix.py `base`):
- st1/r10b.arc + r10b.dar, em/pl0f.drs (rel-stripped: le_mirror --compact-static-rel=pl0f), em/em2f.drs,
  bgm/aica_str.dat with stream 0:4 (the boss), the r10b PS2 world (dc/native/r10b/ps2-world.*), MAINSCENARIO.re4mesh,
  the six r10b movies (r10bs00/s10/s20/s20c/s21/s22), r10b textures in the pack;
- **dc/pl0f.ovl and dc/em2f.ovl from the same build** (lane tools/addovl.py adds them to a fixture; stage-scenario.py
  places only 1ST_READ.BIN and dc/sscrn.ovl itself). Without them entering r10b stops in "route overlay missing";
- removals (never read by the play route; D:/Flycast-Evidence/re4-dreamcast/r10b-20261009/disc-audit.json): em/em10,
  em11, em1f, em20, em22, em25, em2b, em2c, em2d .drs; st1/r100, r101, r103, r120 .das; st1/r120.dar + .arc;
  le_mirror_report.json. Payload 990,220,914 B against the GD's 1,032,499,200 B.
- no dc/warp.txt, no dc/padscript.txt.
Checks before the SD card: pack keys and file list against the 10-09 disc (only the r10b files, the overlays and
1ST_READ.BIN differ; the removals above are gone); boot the real disc in Flycast to the VMU prompt; New Game intros
1971 / 2360; the r10a -> r10b door, boarding, the QTE, "Coming Soon". The bio4bgm / bio4evt.sbb lever is done:
SBB_STUB=1 (top section).

## 2026-10-09: test build for issues 9 and 15

Play ELF = route-build.sh with the 631cb271 flags (DBG_WARP=0 PC_SAMPLER=0
PACE_DEBUG=1 ROUTE_CH13=1 ACT_CAP=0 PS2_INTERIOR_ACTORS=2 GAME_ATLIST_OVERFLOW=1
GAME_ATLIST_512=1 LEON_NATIVE_PIPE=0 LEON_FACE_LAZY=0 NATIVE_LASER=1
ACTOR_GANADO_SOURCE_LIGHT=0); built at cc5da41b it reproduces the 631cb271
image byte for byte. Disc = the 631cb271 qualification fixture
(reporter-goal-20261008/inventory-world-sort-ram-v2.json, catalog pack d87983e1,
padscript removed) plus an audio overlay:
- bgm/aica_str.dat rebuilt with the 631cb271 stream list (index identical);
- every prebuilt bank refiltered in place:
  `aica_banks.py reconvert --root <631 disc sound files> --mirror /root/probe/d362-mirror,/root/probe/codex-audio-20261007/mirror --out <overlay>`
  (each file proved: the box conversion of the mirror source reproduces the old image).
Payloads must equal the 631cb271 disc manifest except 1ST_READ.BIN, dc/sscrn.ovl,
bgm/aica_str.dat and the 39 bank files. Any new bank build gets the filter
automatically (FILTER_VERSION in the cache key). TA_GUARD stays 0.

## 2026-10-07: native Ganado prelit lighting and missing beam

The user reconfirmed Leon's baked-lighting performance choice and requested the
same path for Ganados. The play recipe now sets ACTOR_GANADO_SOURCE_LIGHT=0;
native Ganados use Leon's existing prelit/constant record. NATIVE_LASER=1 also
restores the missing source weapon beam through the existing effect queue;
target/dot/collision are unchanged. Both changes pass complete 2,911-record
STRICT and required-decision comparisons in the matched aim fixture.

The final 512-entry movie/radio gate completes s03/s20/s30, with s30 340/340 at
63,584 starting heap bytes and both radio backing hashes restored. Clean final
text +1,120 and character data -32 bytes leave BSS, allocated addresses, linked
end and arena unchanged. The Ganado wall-aim balanced model sample improves
48.350586 -> 47.786288 ms; this small local four-tick result is not console FPS.
See [the source bug qualification](D367_BUG_QUALIFICATION_20261007.md) for build
identities, modes, scope and preserved aborted attempts. No new release or SD
write follows. Inventory/bridge console failures remain un-reproduced and open;
reduced-distance fog and baked Leon are intentional user choices. The outdoor
candidate below remains unaccepted.

## 2026-10-07: outdoor follow-up remains unaccepted

The bounded current-Trans eligibility guard saves 0.699766 modeled ms of
synchronous owner work per drawn r101 square sample. Host checks, cold-cache
interior/checker runs, complete STRICT Bell (6,370)/H2 (3,237), ordinary radio resources
and final automated New Game pass. Clean ON adds 64 text bytes without linked-end
or arena growth. Final exact rendering qualification remains REVIEW_REQUIRED:
493 movie-only TA hash differences and held framebuffer pixel differences 0/8
and 5/0. Their cause is unproven; no new exclusions or thresholds are accepted.
The guard and observer stay private/off. No runtime/recipe/play-disc/SD/release
change follows. See [the final qualification](D367_OUTDOOR_PERF_20261007.md).
The larger outdoor 30 fps gap remains open; the remaining-stage and Leon donor
audits establish no additional authorized implementation.

## 2026-10-07: ordered optimization complete; collision capacity accepted

The play recipe now enables GAME_ATLIST_512=1 alongside the existing overflow
guard. Only the two ordered alive-list arrays grow from 320 to 512 entries;
the 96-collidable cache bound, live change notifications, ordering and complete
over-capacity fallback remain unchanged. The general make default remains 0.
Runtime candidate 6c7cc182 is integrated as 09ac28d7. See
[the capacity evidence](D367_ATLIST_CAPACITY_20261007.md) for reproduction and
[the rejected r104 visibility experiment](D367_R104_WORLD_CELL_20261007.md).

The uncapped r104 cabinet sample improves 39.832->36.338 nominal SH-4 modeled
ms per tick (-3.494, 8.77%): drawn 53.062->50.376, skipped 26.592->22.288.
Eight consecutive traces at source 1200..1207 have four drawn/four skipped
ticks per arm. The 32-frame census is 16/16 OFF and 17/15 ON; sample-to-census
mode deviation reaches 4.29%. These are balanced sample means, not a timed
32-frame mean, rendered FPS or physical-console measurements. The existing
470-object candidate walks disappear; ObjHitCheck still visits every object.

Host capacity/lifetime/overflow checks pass. The actual cabinet checker sees
470 through 479 objects, 196,573 candidate-cache hits and zero list/candidate
mismatches. Bell is STRICT with required decisions identical on all 6,370
shared records. Ordinary H2 has only 475 borrowed-memory object-matrix hash
differences, with required decisions identical. Preserved-memory tracing
resolves those bytes but exposes a one-tick wall-time radio-close difference.
The single existing 1,000-us diagnostic-delay qualification matches all 3,237
shared gameplay records and required decisions, including the entire radio
interval, with no added exclusions. Two informational sound-query records
differ; they follow audio timing. All three outcomes are retained. Production
and performance builds keep delay=0 and preserved-memory tracing disabled.

Static data grows 1,536 bytes and text shrinks 32 bytes. Linked end grows
1,536 bytes, crossing the existing ARENA_FIT 4-KiB rounding boundary: arena
12,365,824->12,361,728 and untraced s30 heap 67,680->63,584 bytes. All movies
complete, including s30 340/340. Radio replay 5518..6079 restores 3,027,520
bytes with hash verification and returns to the event world. The initial
linear heap-loss assumption and its failed assertion remain in the evidence.
No missing modules, halts or misalignment were reported by the bounded gates.

Leon qualification is complete and both LEON_NATIVE_PIPE and LEON_FACE_LAZY
remain disabled. The combined path reduced a matched radio-free r101 square
sample by 1.738 modeled ms per draw/skip pair (1.75%), but required model,
work-backing and createSat allocations fail in traced and untraced r100 runs.
H2 first diverges at frame 661. Complete movie counts and exact restoration did
not detect these missing required objects; the later higher free-heap figure
is not a safety margin. Four frozen framebuffers and 2,527 normalized TA rows
matched, but rendering equality does not override the resource/gameplay fail.
The smaller face-only arm adds 704 text bytes without moving linked end; its
derived cabinet draw/skip pair gain is only 0.438 ms (0.60%) with unmatched
drawn subsets, so it remains off without further qualification. See
[the Leon requalification record](D367_LEON_REQUALIFICATION_20261007.md).

Final capacity-only automated New Game completes 1,971/2,360/1,175 movie
frames and reaches live r100 with no required model/atari/work-backing
allocation failures. This gate uses DBG_WARP=1 and PC_SAMPLER=1 with the title
input script; it is not an exact clean-disc manual playthrough.
Clean play ELF 5ad665ec5086d3308111a5877545d5100a4704c89e122f4f885bdb6da9154dc5
is built from reviewed source 96e0f20c with only GAME_ATLIST_512 newly enabled
relative to r22j. Both Leon knobs, debug warps, PC/logic/decision tracing,
forced pacing, freezes and diagnostic delay are off; ACT_CAP=0.
The CUE and GDI live in D:/RE4DC-Play-Discs/ordered-optimization-20261007-*
with launcher D:/RE4DC-Play/Play-Ordered-Optimization-20261007.cmd. All 1,195
GDI payloads read back in both namespaces; the exact GDI separately boots in
Flycast. Evidence: /root/probe/codex-ordered-20261007 and
D:/Flycast-Evidence/re4-dreamcast/ordered-optimization-20261007.

Published r22j and the hash-verified SD folder154 are unchanged. These local
checks do not resolve issue2 or establish continuous whole-route, physical
Dreamcast or 30 fps acceptance.

## 2026-10-07: r22j audio and performance release

The [r22j prerelease](https://github.com/lamb2k/re4dc/releases/tag/play-r22j-audio-performance-20261007) packages the validated music, indoor culling and CPU
changes below, plus every r22i fix. Windows, SteamOS, CachyOS and GDEMU archives
contain the same checked disc bytes; every archive member was read back and
hashed. All public asset sizes/digests and download responses were verified.

Release source is 8b0b9623. The clean play runtime was built at 10eb831f with
GAME_ATLIST_OVERFLOW=1; the release commit adds only matching recipe activation
and documentation. Its ELF SHA256 is
`8eba3bb57d70cd08b7c8c736561efd1d41fd373a965a524b22c7794925f4751d`.
The corrected bank-9 asset is included, with the 3,749-entry herb pack retained.
All 1,195 GDI payloads match in both namespaces and the exact GDI boots from
its high-density TOC to the VMU prompt. Test-control files are absent.

The prior candidate sections record the combined New Game, movie/radio, logic,
audio and modeled-cost scope. Earlier statements that these changes are absent
from r22i are historical and remain true; r22j now delivers them. No continuous
whole-route, physical-console, mixed-audio listening or 30 fps acceptance is
claimed. The r103 save-load freeze in issue #2 remains unresolved.

## 2026-10-07: oversized alive-list retry optimization accepted

GAME_ATLIST_OVERFLOW=1 is now in the play recipe; its general make default stays
0. The existing head/generation guards remember a failed 320-entry alive-list
build. Every required full collision walk still runs in its original order;
capacity, collision decisions and source state are unchanged. Eight host knob
combinations and the negative/lifetime controls pass. Knob-off executable and
overlay are byte-identical to the accepted culling baseline. The enabled image
adds 96 text bytes, with no other allocated-section or linked-span growth.

The uncapped r104 cabinet 0x2A view measures 41.310->39.832 SH-4 modeled ms per
tick (-1.478 ms, 3.58%): drawn 54.961->53.062, skipped 27.647->26.592. Eight
consecutive traces at source 1200..1207 contain four drawn/four skipped ticks;
the 1200..1231 census contains 16/16. Draw parity flips between arms, so these
are mode averages, not exact-frame pairs. Sample instruction means differ from
the full census by -0.62%/-0.47%; the largest per-mode deviation is 2.72%.
This is eight timed frames, not a fully timed census or a rendered-FPS estimate.
The cabinet fixture, input, warp, music bank and resolved knobs match apart from
GAME_ATLIST_OVERFLOW; ACT_CAP=0 and HWTRACE_ALIGN=1, with zero misalignment,
halt or missing-module markers. Full fallback body visits remain unchanged;
the saved time comes from removing repeated failed prefix builds.

Against the accepted culling trace, all shared H2 records 0..5698 (5,699) and
bell records 0..6371 (6,372) are STRICT and decision-identical, including H2's
previously excepted object-matrix interval. Bounded capture tails differ in
length. The untraced s30/radio check completes 340/340 frames with 67,680 bytes
free before s30, unchanged from its matched culling control, then restores the
room backing. Final combined New Game completes 1,971/2,360/1,175 movie frames
and reaches live r100. These gates include the corrected r104/r107 music bank.

These results are bounded emulator and hardware-model evidence, not physical
Dreamcast, whole-route or 30 fps acceptance. The stair-ascent culling and cabinet
CPU gains are different scenes and must not be added together. Published r22i
is unchanged; the new audio asset must accompany this source in later builds.

## 2026-10-07: owner-path interior culling

The recipe now selects PS2_INTERIOR_ACTORS=2. The integrated owner-path rejection
keeps actor admission, leases, crowd ranking and all source simulation; identity
replacement discards a prior cull mark. Knob-off image and overlay remain
byte-identical to the c36 issue-fix diagnostic build. The lifetime host test and
its failing negative control cover serial/data/parts replacement and generation wrap.

H2 is STRICT for 0..740, 1218..5696 and 1450..1569; decisions match for 5,696
records. The established object-matrix-only interval 741..1215 remains outside
those STRICT windows. Bell is STRICT and decision-identical for 6,372 records.
The checker reports 1,494 displayed framebuffer scans with zero magenta hits,
191 owner replay checks with zero mismatches, and 303 checked bounds with no
overflow. This is displayed-frame coverage through its UI 2160 summary, not every
source tick. Stair-ascent and settled-window screenshots look normal.

The linked image grows 8,256 bytes (allocated payload +4,864, including 608 bytes
of custom-section data). The matched untraced movie/radio twin has 67,680 bytes
free before s30 versus 75,872 for control; all 340 movie frames complete and radio
replay 5520..6080 restores the room. Traced H2 has 67,584 bytes free in both arms.
Do not compare traced and untraced heap values.

The SH-4 model pair covers source 1760..1839 while Leon climbs toward the upstairs
window. Twelve traces at stride 7 split 6 drawn/6 skipped; the 80-frame census is
40/40, with sample instruction means within 0.32% of their respective census means.
Drawn cost 55.756->53.908 ms, skipped 22.771->22.829 ms, equal-weight mean 39.264->38.369 ms.
ACT_CAP=0, HWTRACE_ALIGN=1, and MISALIGN=0 in both arms. This is a bounded model
result, not stationary stair-foot, whole-route, 30 fps or physical-console acceptance.

The existing interior.cell is retained; no new derived geometry is required.
Final combined New Game validation passes with the CPU change above. These
changes are not included in the published r22i download.

## 2026-10-07: room music bank preparation

This change is a candidate after published r22i; r22i does not include it.

The room table selects `bio4midi` entry 9 for r104 and r107. `ROOM_BGM0`
now includes both rooms, so the converter puts this bank into the existing
264,576-byte BGM0 slot instead of attempting runtime allocation after the pool
is occupied. Its image is 236,640 bytes; the frozen layout and movie reserve
are unchanged. The 32 kHz cap preserves two samples at 32 kHz; seven longer
samples use 8 kHz under the existing 65,534-sample channel-length limit.

Regenerate the chapter 1-3 music overlay from an unconverted private mirror:

```sh
python3 port/dreamcast/tools/aica_banks.py build \
  --mirror "$MIRROR" --out "$NEW_AUDIO_OVERLAY" \
  --route title,r100,r101,r103,r104,r107,r102,r108,r109,r10a \
  --fixed-route title,r100,r101,r103 --weapons --check
```

Stage only the resulting `bgm/bio4midi.dat` into the existing chapter 1-3
fixture. The default base route in `stage.sh` does not include the later rooms
and does not regenerate this overlay. Keep the established weapon and room
files and the current herb texture pack from their reviewed fixtures.
The new file must differ only in entry 9's ARAM span; all other bytes, including
prior music banks and archive metadata, remain identical to the prior overlay.

Validation: seven converter host tests pass. A same-binary r107 A/B changes
0 music notes / 39 unmapped events to 39 / 0 in the matched periodic summary.
The r104 normal-arrival fixture passes the source QTE, skips the following movie
through its source completion path, closes the radio with START, restores the
room and plays bank-9 notes at -28/-27 dB. Room return has source/draw log
markers; the next test input opens Map, so later screenshots do not establish
sustained world play. Fresh warps with the arrival flag already set are not an
equivalent r104 music test. No runtime code changes or heap-4 growth are involved.

All three player grenade types consume one item and key on the expected nonzero
PL-bank sample in a quiet r102 Flycast replay: hand PL/0x14, fire PL/0x22 and
flash PL/0x13. The runtime PL image hash matches the existing packaged bank.
These are the `cSubWep` detonation paths, not generic scenery `obj01` effects.
No grenade audio change is indicated by these tests. This is source/driver/sample
validation, not captured mixed audio, listening acceptance or a console test.

## 2026-10-06: r22i inventory and animation release

The [r22i prerelease](https://github.com/lamb2k/re4dc/releases/tag/play-r22i-inventory-animation-fixes-20261006) packages the validated
c36a08cc runtime with the 3,749-entry herb texture pack. Windows, SteamOS,
CachyOS and GDEMU archives retain the tested disc bytes; every archive member
was read back against its input hash. The play ELF is
`db89a3fd215236c20e4ee028588b1d0bcd0cd0f0ee963672de167c0d6bf8645b`.

In addition to the candidate checks below, the final diagnostic twin passes
r102 well, r103/r106 cupboard, r107 kiln and the complete r108 cemetery dial
solution. The source changes animate the audited unique placement IDs; this
does not add general duplicate-ID animation. Separate inventory fixtures invoke
the real Equip command for all three grenades in r101 and exit to gameplay
without the reported DLL halt. The test setup only gives/selects the item.

No physical-console or continuous whole-route acceptance is claimed. Issue #2
remains unresolved. The r104/r107 music and grenade sound work, and the pending
PS2_INTERIOR_ACTORS=2 integration, are not part of r22i.

## 2026-10-07: issue fixes candidate after r22f

The recipe enables ITEM_UI_ORDER=1, PS2_WORLD_PARTS=1 and MOVIE_STAGE_ORDER=1.
Item pickups now use the source UI/model submission order. Scenery with a changing
child pose hands its complete hierarchy to the existing source renderer and hides
its baked PS2 placement; owner serials and room retirement guard borrowed parts.
The native r104 already-open callbacks receive their item-event index explicitly.
Unmodified scenery retains the PS2 path. Duplicate placement IDs retain the prior
baked behavior, so this is not a claim that every interactive object is covered.

The disc must also contain the two missing green/red herb color-mask pairs in
`dc/tex.pak`. Prepare them with `tools/prepare_inventory_pairs.py SOURCE BASE_PACK
NEW_OUTPUT_DIRECTORY`. The verified candidate has 3,749 entries; all 3,747 prior
entries are byte-identical. Keep these derived assets outside the public source tree.

The extra part-pose storage exposed an r100 s30 staging failure at 84,064 B free.
MOVIE_STAGE_ORDER, adapted from 25c4cd0f, stages the same buffers largest first.
The combined candidate plays all 340 s30 pictures at that same heap level, then
opens and closes a source radio replay. This replay tests resource handoff; it does
not change or establish normal route event order. New Game movies complete
1,971 / 2,360 / 1,175 pictures. Inventory herb visibility, pickup layering, opening
an r104 cabinet and reloading its open pose have Flycast screenshot evidence.

Issue #6: prepared em13 enemies are visible and attack in r104. The normal merchant
intro, greeting, menu exit and standing merchant with Talk prompt work in the tested
warp route; a direct debug jump past the intro is not equivalent coverage.
Issue #2 remains unresolved: a normal r103 typewriter save, fresh emulator boot,
load and movement complete without a halt. No physical-console fix is claimed.

Validation: the actual dynamic-part adapter passes ASan/UBSan cases for child
changes, owner retirement and object-pool address reuse across scenery IDs. The
old address lookup fails the new negative control. Native I/O and task-exit tests
pass. Shared PPC conditional source tokens are unchanged (includes stripped for
comparison; this is not a new full PPC build).

Final H2: STRICT 0..740 (741), 1218..5696 (4,479) and 1450..1569 (120);
MUST-IDENTICAL decisions (5,696), zero player/enemy drift. The whole-run difference
is limited to the existing object-matrix interval 741..1215 (475 rows). Both arms
play the movies successfully with MOVIE_STAGE_ORDER=1. Bell STRICT and
MUST-IDENTICAL both cover 6,390 records. The chapter-1-3 twin plays s30 340/340 at
heap_before 75,872, then opens/closes radio replay frames 5518..6079. The play
image disables test controls, completes New Game 1971/2360/1175 and reaches live
r100. Its exact GDI boots via the high-density TOC to the VMU prompt. All five
final runs exit normally with zero HALT, MISALIGN or RE4DC MISSING records.
This validated candidate is packaged as r22i; see the release section above.

Cost gate (SH-4 hardware model, not physical-console acceptance): r104 cabinet
0x2A, view (21821,-64,-30700), angle pi; ACT_CAP=0, PACE_DEBUG=1, ROUTE_CH13=1.
Count window 1200..1231; eight consecutive traced frames 1200..1207 cover both
drawn and skipped frames. Control af4b5016: 41.28 ms (24.22 modeled fps); fixed
51dbc3e8: 41.39 ms (24.16 modeled fps), +0.11 ms in this sample. Trace instruction
means are within 0.2%/0.6% of the 32-frame census. The earlier stride-10 sample
aliased drawing cadence and is rejected. This is a bounded view, not a whole-route
performance or 30 fps acceptance claim.

## 2026-10-06: WEAPON_HEAP4 in the recipe (next play build)

WEAPON_HEAP4=1 (issue #1 option 3) is in build-r21.sh: the r104 merchant's rifle, TMP and rocket launcher load into
heap 4 instead of halting (about +0.3 s per door while held; heap 4 short reverts the equip). r107 keeps only
~100-109 KB of heap 4 with one held, and the scoped rifle reverts to the plain rifle there (route doc "WEAPON_HEAP4").
The play fixtures' em/em13.drs never loads in r104 (route doc "Pre-existing r104 em13 read failure"); r22e on carries
the native-scene lane's prepared em13 (6,829,984 B, MRAM 1,231,776 B). PRIM_CAP_R107=327680
WEAPON_HEAP4_TOP=1 (recipe): the scoped rifle no longer reverts in r107 (360-367 KB heap 4 left).

## 2026-10-06: r22f (play build)

r22f = r22e + the issue #2 crash screen (575b9970, 6cac28d8), PS2_WORLD_DYNAMIC=1 (98ef215d, recipe e9e036f7) and the
r105 emblem check fix (a64cef05). Not in it: the pc2 owner-path interior cull (s30 heap 4, route doc "r22f").
Source a64cef05 + build-r21.sh `DBG_WARP=0 PC_SAMPLER=0 PACE_MODE=fast PACE_DEBUG=1 ROUTE_CH13=1`. **The play fixture
must stage dc/native/rXXX/ps2-world.ids** for every PS2 world room (private store 81efcf2, tools/ps2_room_ids.py); without
them the rooms draw as before (the emblem does not turn). Fixture: the r22e fixture plus the 11 ids files.
Gates on the combined tree: knob-off image and overlay byte-identical for CRASH_SCREEN and PS2_WORLD_DYNAMIC; H2 STRICT
1450..1569 / ..740 / 1218.., whole room om only, decision_cmp MUST-IDENTICAL (7,028 ticks); r101 bell STRICT +
MUST-IDENTICAL (5,133 ticks); 0 MISALIGN (interpreter, r105 puzzle); missing.txt empty; r100 s30 340/340 (heap_before
87,456; 56,576 with the scoped rifle armed). Checks: New Game 1971 / 2360 / 1175; r105 emblem turns and the door opens
(Room_flg bit 0); crashtest.txt "block" shows the new screen naming the blocked task; issue #1 exact steps (shotgun
loaded, life 600 to 1200, no REJECTED); shotgun fire with no weapon-bank "does not fit". Disc hashes: READY.txt in each
disc folder.

## 2026-10-06: r22e (play build candidate)

r22e = r22d + WEAPON_HEAP4 (merchant rifle, TMP and rocket launcher load into heap 4), PRIM_CAP_R107=327680
WEAPON_HEAP4_TOP=1 (scoped rifle stays equipped in r107), the prepared em13 (r104 enemies spawn), PS2_INTERIOR_CULL
(r100 house cell, dc/native/r100/interior.cell), EFFECT_PS2_HAZE=1 EFFECT_PS2_STREAK=2 (PS2 haze and light shaft) and
the prebuilt weapon sound banks (stage knob AICA_WEAPONS=1: em/wep01, 07, 09, 11, 13, 19, 20, 21, 24 in the fixture).
Source d3a36242 + build-r21.sh `DBG_WARP=0 PC_SAMPLER=0 PACE_MODE=fast PACE_DEBUG=1 ROUTE_CH13=1` (ELF 3022bd3b).
Disc check against r22d: tex.pak identical (3,747 packages); changed 1ST_READ.BIN, dc/sscrn.ovl, em/em13.drs and the
nine weapon files; new: 10 em13 motion files and interior.cell. GD high-density area 97% (1,006 of 1,032 MB).
Flycast checks on the shipped contents, HALT 0 / MISSING 0 everywhere: GDI boot from the high-density TOC; New Game
1971 / 2360 / 1175; issue #1 exact steps through the real case (combine R+G, equip the shotgun, use the herb, close:
r22c halts with "asset exceeds selected resident budget", r22e loads the shotgun and heals); shotgun fire with no
weapon-bank "does not fit"; every weapon in r104 and r107; r104 em13 loads; r100 s30 340/340 (heap_before 92,640 on
the play fixture, 102,944 in the H2 run); chapter 1-3 to "Coming Soon"; r101 bell; 0 MISALIGN. Gates: H2 STRICT
1450..1569 / ..740 / 1218.., decision_cmp MUST-IDENTICAL, bell STRICT, missing.txt empty.
GDEMU tracks: disc.gdi 1bac5c9d, track01 fc82b979, track02 9c97e0db, track03 d366bfd3; copied to the SD card (folder
152) and hash-checked there. Known: r104 and r107 have no room music (aica blk 3 does not fit; no ROOM_BGM0 entry in
aica_banks.py); the rifle's weapon bank is 8 kHz (user 2026-10-06: keep). Release: the user publishes.

## 2026-10-06: r22d (console test disc, not released)

r22d = r22c + the issue #1 fix: d72fd6a4 (recipe WEAPON_RESIDENT_BYTES=275424 WEAPON_MODULES=1, plus GAME_ROT_FSCA,
CROWD_INVIS_SKIP and EFFECT_FADE_CLAMP since r22c), build-r21.sh + `DBG_WARP=0 PC_SAMPLER=0 PACE_MODE=fast
PACE_DEBUG=1 ROUTE_CH13=1` (ELF 2d70fb22), fixture /root/probe/lanes-20261005/i1/fixtures/title-r22d-candidate-pak.json
(the r22c pack fixture plus em/wep20, wep21, wep24). Disc check against r22c: tex.pak identical (3,747 packages); only
1ST_READ.BIN and dc/sscrn.ovl change; only em/wep20 / 21 / 24 are new. Flycast (vsync off): GDI boots to the VMU
system-info prompt; New Game intros 1971 / 2360, r100s40 1175, HALT 0 / MISSING 0; shotgun and grenades equip in r101
with no halt; chapter 1-3 to "Coming Soon" at r10b; r101 bell HALT 0; 0 MISALIGN. Local discs r22d-title + r22d-gdemu
(Play-r22d.cmd); not on the SD card, not released. Known: the r104 merchant's rifle, rocket launcher and TMP still halt
when bought; non-handgun weapons are silent (route doc "Issue lamb2k/re4dc#1").

## 2026-10-06: PS2_INTERIOR_CULL and PS2_INTERIOR_ACTORS in the recipe (next play build): stage interior.cell

PS2_INTERIOR_CULL=1 PS2_INTERIOR_ACTORS=1 (lane pc, render-only) are in build-r21.sh. **The play fixture must stage
dc/native/r100/interior.cell** (tools/d367/ps2world/interior/interior-r100.cell): pack-fixture.sh adds it to any fixture
that stages the r100 PS2 world; for an existing fixture run `tools/d367/ps2world/interior/add_cell.py <fixture.json>
<out.json>` (e.g. title-r22d-candidate-pak.json). Without the file the game runs but does not cull ("PCCULL cell file
missing" in the log). Check in the log: "PCCULL cell file loaded", "cell lent to a movie" at each route movie, r100 s30
340/340. Heap-4 gate (coordinator 2026-10-06): every landing that grows .text, .rodata or .bss, or uses more heap 4,
runs H2 through r100 s30 with its knobs on, confirms s30 plays 340/340 and reports heap_before at s30; the New Game
gate stops before s30 and does not count.

## 2026-10-05: CROWD_INVIS_SKIP and EFFECT_FADE_CLAMP in the recipe (next play build)

CROWD_INVIS_SKIP=1 (lane iv, render-only) and EFFECT_FADE_CLAMP=1 (lane ph, the near-fade wrap fix: no white
upstairs-window glare) are in build-r21.sh (user approval 2026-10-05), so the next play build includes them, with the
same play flags and fixture as r22c. EFFECT_PS2_HAZE / EFFECT_PS2_STREAK stay off: the haze look waits for the user's
r22h console session (local test disc, X + START steps the looks). GAME_LQ_MEMO (lane el) stays off. Route doc lane
ph / iv bullets.

## 2026-10-05: GAME_ROT_FSCA in the recipe (next play build)

GAME_ROT_FSCA=1 (user approval 2026-10-05) and LINK_ORDER link-order/r22-fsca-c3-8k.ld are in build-r21.sh, so the next
play build includes them (same play flags and fixture as r22c). Play image New Game -> r100 checked in Flycast (HALT 0 /
MISSING 0); route doc "GAME_ROT_FSCA adopted". The console playtest comes with the next test disc.

## 2026-10-05: r22c (current play build, released)

r22c = r22 + chapter 1-3: 2bb24730, build-r21.sh + `DBG_WARP=0 PC_SAMPLER=0 PACE_MODE=fast PACE_DEBUG=1
ROUTE_CH13=1`, fixture /root/probe/lanes-20261005/r22c/fixtures/title-r22c-pak.json (route doc "r22c"). Released by the
user as play-r22c-chapter-1-3-20261005 (prerelease); local discs C:/RE4DC-Play-Discs/r22c-title + r22c-gdemu. Flycast:
boot, New Game, chapter 1-3 route to "Coming Soon", content superset of r22. Console play pending. Disc rule (from
the r21z-c13 fault): before a disc goes to the SD card, compare its tex.pak keys and file list with the last good
disc and boot the real disc; pack-fixture.sh replaces a fixture's existing dc/tex.pak, so every package must be loose
in the raw fixture. The r21z-c13 disc (SD folder 156) lacks most textures: not for play.

## 2026-10-05: r22 and r22g test discs (local, not released)

r22 = the integrated perf lanes (3f4b599d recipe; route doc "r22 test disc ..."); r22g = r22 + PACE_VMU_GPU=1 (the
VMU's GPU line). Both boot (GDI checks); on the GDEMU SD card (folders 154 r22, 157 r22g). First console session (user,
r22g): fight 70% / 10.4 fps, no crash; full readings in the route doc. Not released yet: release after the next
console playtest (with any adopted round-2 knobs, e.g. GAME_ROT_FSCA if the user approves it).

## 2026-10-05: integrated perf lanes (next play build candidate, not released)

build-r21.sh (616a5a11 on perf/int-20261005, local) adds SKIN_PALETTE_LAZY ESP_SPRITE_FAST ESP47_SKIP_LEAN
MODEL_PREP_KEEP CROWD_READOPT_MEMO ACTOR_BIND_REUSE PS2_WORLD_HDR_CACHE MESH_CLIP_ACCEPT PS2_PASS_MASK GAME_HF_REG
GAME_CLOTH_SPRING GAME_SND_WALL_ALT (all =1) and LINK_ORDER link-order/r21z-perf-c3-8k.ld; route doc "2026-10-05:
integrated perf lanes". Same play flags and disc fixture as r21y. Checked on the play / warp images: New Game (intros
1971/2360, s40 1175), radio call, inventory restore x2, r100 window jump (no reset), HALT 0 / MISSING 0, 0 MISALIGN.
PS2_FOLIAGE_FAR stays off (look decision pending). A play disc from it still needs the user's console play.

## 2026-10-04: chapter 1-3 (ROUTE_CH13, default off)

Landed default-off (route doc "chapter 1-3"): r101 1-3 state, r102, r108, r109, r10a; resident BGM0 tracks for the
second-slot music; "Coming Soon" at doors into rooms not on the disc. Test disc r21z-c13 (local, not released) waits
for the user's console play before ROUTE_CH13=1 goes into build-r21.sh.

## 2026-10-04: r21y (previous play build)

r21y = r21x + the camera crash fix (dd995a7b) + the VMU CPU line as a percentage (564f5168); route doc "r21y". Same
recipe and fixture as r21x. Disc and checks in step 6. Public release play-r21y-camera-fix-20261004 supersedes r21x.

## 2026-10-04: r21x (the VMU speed build)

r21x = r21v + the fixes from the first console play of r21v (route doc "r21x"): the Trans sub screen guard (crash after
the radio call / on Y), COARSE_SAT_SCENERY_ONLY=1 (r100 bridge blocker), SS_BG_BLACK=1 (tan frame), PACE_VMU=1 (speed
page on the VMU LCD; user: the main build from now on), all in build-r21.sh (a0618068). Play discs also need the radio
call voices in bgm/aica_str.dat (tools/aica_banks.py disc --call-voices, or stage.sh AICA_CALL_VOICES=1; fixture
/root/probe/main-20261004/fixtures-x/title-x-pak.json). Disc and checks in step 6. Public release play-r21x-vmu-20261004 (page removed 2026-10-04, tag kept) superseded
r21v.

## 2026-10-04: r21v (previous play build)

r21v = the play recipe + the supervisor performance knobs (build-r21.sh, fe50a85a); disc and checks in step 6, details
in the route doc "r21v". Play discs now also need the registry packages, the pl08 pack and their textures in
tex.pak (fixture /root/probe/main-20261004/fixtures-v/title-v-pak.json). Public release
play-r21v-performance-20261004 (page removed 2026-10-04, tag kept) superseded r21t. The first console test is the user's.

## 2026-10-04: review follow-ups for the next play disc

Details in the route doc, "2026-10-04: review of 2026-10-03/04". For play discs:
- New rule: every play disc opens and closes the inventory in r100 and r104 ("Play build rules", inventory check).
- r21t GDEMU image: the released zip boots in Flycast (built-in HLE BIOS) from disc.gdi to the VMU prompt, the title
  and r100 gameplay (route doc). GDEMU and a console are still untested.
- experiment/supervisor-20261004's code is LANDED default-off after r21u (route doc "supervisor code landed
  default-off"). It is not in the play recipe; play discs are unchanged (knob-off identity).
- lane/review-fixes-20261004 is LANDED (gates in docs/lanes/review-fixes.md "Landing"): TEX_PACK retry spacing plus
  a preload re-run after the pack recovers (both change the play image's error path only), the TA_HASH
  whole-meshlet hook, a native_static `#error` guard, build-r21.sh failing on knobs no makefile reads (five dead ones
  dropped from the recipe), route-build.sh failing without resolved-knobs.txt and printing link.sh's missing symbols
  (`$O/missing.txt`, copied from the tree's game/obj). r21u is cut from the landed tip b730bf1a
  (step 6: C:/RE4DC-Play-Discs/r21u-title + r21u-gdemu, launcher Play-r21u-Review-Fixes.cmd; every check passed; not
  released).

## 2026-10-04: local experimental checkpoint and delivery audit

The combined full-module candidate measured 90.0806 -> 82.6492 ms in the uncapped r101 square (ticks 1330:1389, 60
frames, stride 1, tail 3; ACT_CAP=0 / PACE_MODE=off; SH-4-model CPU work excluding waits). Seven controlled schema-5
source/candidate pairs pass 24,279 complete state/decision/effect frames. This is not 30 fps, natural-transition,
visual or physical-console acceptance. The r104 inventory looked broken in both controls. Correction (local session, 2026-10-04): that was 6819f3a2's bug,
already fixed on dreamcast-port. Since ad0c59d0 (PS2_WORLD_ROOMS=2) the inventory's rigid models were taken for room
scenery and the PS2 world was submitted inside the sub screen's single TR stream. Both controls predate the fix, so
source and candidate showed it alike; these experiments did not cause it. The knob set is recorded in
[SUPERVISOR_BASELINE_20261004.md](SUPERVISOR_BASELINE_20261004.md) ("Knob set of the 82.65 ms candidate").

Source checkpoints 4386239f and 3739a8e0 are on experiment/supervisor-20261004. The latter preserves a default-off
early-admission experiment that lost 6.1125 ms and must not be enabled. No play recipe change. The diagnostic
16f0da96 has since landed on dreamcast-port.

The supervisor did not follow incremental delivery promptly. A rejected publication attempt remained unresolved while
local work accumulated. Live GitHub verification shows lamb2k/re4dc is public, contradicting the old private
description; the publication question now explicitly states that fact. The remote was ce39455f at audit time. See
[delivery audit](SUPERVISOR_DELIVERY_AUDIT_20261004.md) and [combined baseline](SUPERVISOR_BASELINE_20261004.md) for
results and preserved failures.

## 2026-10-04: r21t public play downloads

User-authorized public release:
play-r21t-inventory-fix-20261004 (release removed 2026-10-04 with the other pre-r21v releases; the tag stays).
Windows, SteamOS, CachyOS and GDEMU archives package the already verified r21t images. Every archived
file is read back and hash-checked; GitHub asset digests and sizes match the local release manifest.
SHA256SUMS.txt and inline release-note hashes support manual and existing scripted downloads.
The runtime remains 6819f3a2, ELF b9dc7b75819fb03e; packaging fix 0b9f6a35. No game-code rebuild or new
performance claim accompanies publication. The continuous chapter playthrough, GDI boot test,
physical-console acceptance and separate SteamOS/CachyOS runtime checks remain pending.

## 2026-10-04: inventory room-replacement ownership repair

The approved 16f0da96 play code reproduces the broken inventory in r100 and r104 with the title-c14 pack.
SS_PACK=0 reproduces it too. Inventory rigid models carry static_geometry; PS2_WORLD_ROOMS=2 therefore
mistook them for the first room-scene draw and submitted the PS2 world inside SS_UI_ORDER's single TR
stream. This closed that list and sent later UI parts through CLOSED_PASS_KEEP, corrupting the case,
items, menu bars and Leon preview. The missing inventory texture was a separate packaging issue.

native_static now uses the existing re4dc_ss_ui_order owner query to exclude swapped subscreen models
from room replacement. subscreen.mk supplies the existing generated setting to that object. No new
renderer, gameplay change, experimental optimization, or play-recipe knob is introduced.

Validation: the same assets before/after show the inventory restored in both rooms; each 180-second
Flycast run opens and closes it, restores the saved area with the matching hash, and returns to gameplay
with HALT 0 / MISSING 0. The matched source/fix gameplay trace pair passes STRICT for 1,804 r100 frames
(room offsets 0..1803, anchors 182/182), no gaps or duplicates, ACT_CAP=0 / PACE_MODE=off. This trace
covers ordinary gameplay, not the swapped inventory memory; the inventory gate is visual plus restore
checks. Production and traced builds report zero missing stubs.

The new title-invfix pack adds the already recovered cd5691f8-b993e9b1 material (656 bytes); all 3,241
existing package payloads are byte-identical. The production image uses the current play recipe,
DBG_WARP=0 / PC_SAMPLER=0 / GAME_PWC_DIAG=1 / PACE_MODE=fast / PACE_DEBUG=1. The final pack passes two inventory open/close cycles in each room with matching restore hashes,
zero missing packages and zero upload failures. The production title/New Game run completes the three
opening movies (1971/1971, 2360/2360 and 1175/1175 pictures) and reaches r100 gameplay.

The existing chapter-end fixture starts in r106: its ending movie plays 1738/1738, the chapter 1-1
results and Save prompt appear, VMU save and syswrite return 0, and r104 is entered. Its s00 movie
finishes and the expected missed-QTE branch reaches Continue. These checks are separate endpoints,
not a continuous manual title-to-chapter-end playthrough or QTE-success qualification.

r21t is installed locally: C:/RE4DC-Play-Discs/r21t-title/disc.cue and r21t-gdemu/disc.gdi; launcher
D:/RE4DC-Play/Play-r21t-Inventory-Fix.cmd. Runtime source is 6819f3a2; production ELF SHA-256 begins
b9dc7b75819fb03e. CUE disc SHA-256 is 226db5f2b4cadc91ee350b325c6a15db17b1cac463b740d853a44894d324bddf.
The CUE has 458649 logical sectors. The newly authored GDI has 458647 raw 2352-byte data sectors at
LBA 45000; all 1143 file payloads match, with the expected unscrambled boot-program difference.

GDI packaging now accepts INPUT_CHARSET (legacy iso8859-1 default unchanged). The UTF-8 tree extracted
from the tested CUE is packaged with INPUT_CHARSET=utf-8, preserving one legacy text filename that
the first draft re-encoded. Both drafts remain private; only the fully verified UTF-8 image is delivered.
The packager change does not change the compiled game. Final evidence: delivery-report-r21t.json and
r21t-gdemu-utf8-verification.json in the private playable-first directory.
The first route milestone remains title -> r120 -> r100 -> r101 bell -> r103 -> r106 results/save -> r104.
Later emblem/key pickups and full chapter-route acceptance are still unproven; this repair does not
establish 30 fps or physical-console acceptance.

Evidence: private architect-review-20261003/tools/supervisor-20261003/playable-first/; scenarios
route-play-main-r100-inventory-r1, route-play-main-r104-inventory-r1,
route-play-main-r104-inventory-unpacked-r1, route-play-invfix-r100-r2, route-play-invfix-r104-r2,
route-play-inv-control-strict-r1 and route-play-inv-fix-strict-r1. The first repair prototype omitted the
native_static generated-header dependency and compiled the check out; it is retained as a failed check.

## 2026-10-03: native vertex coverage in graphics diagnostics

`TA_HASH` now includes the direct store-queue strips emitted by `vp::emit_sq` (PS2 world/mesh fast path)
and the native actor fast path. Previously both bypassed `re4dc_ta_put`, so matching hashes did not cover
their vertex data. The diagnostic hashes the copied words with the final vertex's EOL flag. Direct
store-queue writes in `coarse.cpp` and `coarse_world.cpp` are still outside this coverage.

This repair compiles out with the normal `TA_HASH=0`. On a standalone ce39455f-based image, fresh
`sup-ps-id-base` vs `sup-ps-sq-off` builds have identical .text/.data/overlay, .bss (803644 bytes) and
`_end` (8c3afffc); only four __TIME__ bytes differ. `sup-ps-sq-t1` with TA_HASH=1 also builds with zero
missing symbols. The enabled hooks ran in the stacked diagnostic route checks, including 3754 matched
r101 frames; the standalone TA_HASH=1 image is build-verified, not separately route-tested.

Evidence: private architect-review-20261003/tools/supervisor-20261003/pass-share/ARCHIVE.md,
sqfix.log, sqfix2.log and tacmp-k.txt. This does not adopt PS2_PASS_SHARE (parked after mixed cost
results), change the play recipe, establish complete TA equivalence against the old baseline, or
claim a performance/physical-console result. Native scene coverage remains under implementation.

Correction (review 2026-10-04): the actor fast path is only partly covered. Its whole meshlets (`Part::whole` ->
`emit_meshlet<true>`, the common case under NATIVE_ACTOR_DIRECT=1, also in the COARSE_ONE_SUBMIT window) still go
to the store queues unhashed, so matching `ta_hash:` lines do not prove matching actor geometry. The hook is on
lane/review-fixes-20261004 (docs/lanes/review-fixes.md), not landed. Merging experiment/supervisor-20261004 would
add MESH_STRIP_LEAN paths that also bypass or misattribute the hash (=1/=3 write the store queues in their own
assembly; =2 hashes a dry-run copy that never reaches the TA).

Goal: one play build that feels like the game from the title as far as it goes (r120 intro -> r100 -> r101 -> r103),
on the fastest measured render pipeline, with every existing fix landed. Update this file with every step (status,
commit, evidence). Do not start a later step's work inside an earlier step. Before calling the build complete, re-run
the unlanded-work sweep (every local tree's files hashed against every dreamcast-port blob) and account for every hit.

## Play build rules (verified 2026-09-29)

- Recipe: `tools/d367/build-r21.sh` plus `DBG_WARP=0 QUALITY_PICKER=0 ARENA_FIT_KOS_BYTES=147456 PACE_MODE=fast
  PACE_DEBUG=1 LOGIC_TRACE=0 GAME_DECISION_TRACE=0 ACTOR_TRANSACTION_DIAG=0`; keep `GAME_PWC_DIAG=1` (an exact logic
  cut; only =2 is test-only). Test spots use a `DBG_WARP=1` twin; the pad fixture works without it.
  Recipe truth (2026-10-03, 8f34aa63): build-r21.sh writes `$OUT/resolved-knobs.txt` (make's own resolved values;
  route-build.sh records its path in programs-route.json): read that, not the make line. MESH_CLIP_LEAN=1 is in the
  play recipe since 2026-10-03 (user; H2 -2.18 hw ms, STRICT, off/on captures); MODEL_DRAW_PLANS is forced to 1 by the D349 renderer-stack
  override in the Makefile.
- Calls and cutscene memory (2026-10-02, r21n play): build-r21.sh sets `SS_PACK=1` (the sub screen packs its
  3 MiB into TA bank 1 instead of releasing ~2.3 MB of room textures per call) and `MOVIE_HEAP_EVICT=1` (a route
  movie short of heap 4 evicts unpinned motion keys; the r100 s30 cliff cutscene failed without it).
- PS2 world packages (2026-10-03, r21o play): play fixtures stage the `--lod-uv-guard 0.002` rebuilds
  (tour/play/title-c13-pw.json; the unguarded LOD shears wall textures). build-r21.sh sets `CLOSED_PASS_KEEP=1`
  (an opaque draw after the translucent list no longer halts; a crash-avoidance fallback with unresolved
  ordering / alpha / depth, not proof of correct rendering: each caller needs a visual gate) and `PS2_PRELOAD_LEAN=1` (PS2 world rooms preload
  the package's textures, not the replaced GameCube scenery's).
- Crowd knobs (user 2026-10-03, implementation handoff WP2): build-r21.sh sets `CROWD_READOPT=2 CROWD_CULL=1
  CROWD_FOGSKIP=1`. Leon re-proves his native-cast records after the r100 s20 cutscene (H2 -7.09 hw ms; the r100
  post-cutscene Leon is now the 4K cast, as in r101/r103); Ganados outside the view or past the fog are not drawn.
  Gate on ed818b8e: STRICT H2 120/120 + r100 1391/1391, r101 bell 120/120 + r101 941/941; route checks r100 calls,
  r101 bell, r103 entry HALT 0 MISSING 0; Leon captures (aim, fire, reload, walk, damage) normal. The recipe image
  equals the gated build (.text/.data/overlay identical, 5 __TIME__ bytes).
- Texture pack (2026-10-03): build-r21.sh sets `TEX_PACK=1`; a play disc stages the pack fixture made by
  `tools/d367/route/pack-fixture.sh tour/play/<fixture> <arm> tour/play/<fixture>-pak.json` (re-run whenever the
  fixture's or the base disc's textures change). Without dc/tex.pak the build loads per file, as before.
  Failure policy (2026-10-03, 766a5fa5; route doc "Pack failure policy"): an absent pack loads per file, which is
  fine only on a loose-file disc. pack-fixture.sh play discs drop the packed loose files, so there a read error
  means no texture until a retry (init 3 times, then once per room load) and an INVALID pack means missing
  textures. pack-fixture.sh (13eaccec) writes verified `<name>.<sha16>.pak` packs with a provenance manifest and
  refuses to overwrite without `--replace`; check a pack with `texpack.py --verify`.
- Benchmark fixtures vs the play image (architect review 2026-10-03). Keep them apart:
  - **H**, the original house timing fixture: unguarded PS2 worlds and the 2,512-entry pack.
  - **H2**: UV-guarded PS2 worlds and the title-c14 pack (3,241 packages), the play image's assets. A diagnostic
    house fixture, not a full play validation. Measured with same-binary late activation (warp.txt
    `late <mask> 1400 0x100`; tools/d367/README.md "Late activation").
  - Neither replaces the route checks of a play disc (r21s and later).
- Inventory check (review 2026-10-04): every play disc opens and closes the inventory in r100 and r104 before it is
  called done (route-play-invfix-r100-r2 / -r104-r2 pattern: matching restore hash, and a capture showing the case,
  items, menu bars and Leon preview). HALT / MISSING counts never open it: the corruption fixed by 6819f3a2 came in
  with ad0c59d0 (PS2_WORLD_ROOMS=2, 2026-09-29) and was very likely in every disc from r21i to r21s, the public
  r21k, r21l and r21m included.
- Crash screen (user 2026-10-02): build-r21.sh sets `CRASH_SCREEN=1` for every play build. Before a console disc
  the build must log 0 misaligned accesses over its rooms (`tools/d367/hwready/route-hw.sh align`).
- Disc: `debug/config.txt` ROOM 0x20 (New Game -> r120 intro), no `dc/quality.txt`, the r100 release (route fix e)
  re-cut from the disc's own r100.dar (A1 blocks + A2 archive; the old A2 dar would drop r100's AICA overlay).
  Two artifacts per disc (route doc "Goals and decision rules", disc artifacts): `<rNN>-title` is the Flycast image (`disc.cue`, one
  MODE1/2048 track of 2048-byte logical sectors); `<rNN>-gdemu` is the GDEMU image (`disc.gdi`, `SECTOR=2352` raw
  sectors, track 3 at LBA 45000). Same data-track sector count (r21s: 458,648); data sector n is at byte n x 2352 + 16
  of track03.bin (GD LBA 45000 + n) and n x 2048 of disc.bin. A Flycast boot of the CUE image does not validate the GDEMU TOC or physical media.
- World: the PS2 world in r100, r101 and r103 through PS2_WORLD_MESH + PS2_WORLD_ROOMS=2 (64-vertex packages; r101
  the adopted world-mesh-r21 package, r100/r103 from tools/ps2_room_r4im.py). The disc must stage
  dc/native/r100|r101|r103/ps2-world.{re4mesh,r4pw} and their dc/tex files (tour/play/*-pw.json); a room whose
  package is missing falls back to its Standard scenery.
- r106 (route lane, landed f66e8c5b, 2026-10-01): the play image reaches r106 through the r103 door. Its disc needs
  st1/r106.{dar,arc} (compact + release), dc/native/r106/MAINSCENARIO.re4mesh (release identity), the PS2 world
  dc/native/r106/ps2-world.* from ps2rooms out/r106-ps2 (`--color-light ps2`, TEV x4) with its tex, the r106 room
  textures, dc/movie/r106s00.seq, and the dc/native/r106 directory (stage-scenario.py creates missing directories).
  tools/d367/route/make-route-fixtures.py writes these fixtures (recipe in docs/lanes/route.md). Open: a direct start
  in r106 (warp or a save made there) fails every disc open after the room read.
- r106 end of chapter 1-1 (route lane, 2026-10-01): also the chapter results pictures (tex-chap01-vq + tex-chap01) and
  the em2a picture (tex-em2a); make-route-fixtures.py sets chap01 / em2a.
- r104 (route lane, 2026-10-01; lane/route d4424cf3, landing pending): the build needs PLAYER_RESIDENT_BYTES=869728 (in
  build-r21.sh) and em13 in MODULES (em10g group). The disc needs:
  - st1/r104.{dar,arc} and em/em13.drs from the r104 AICA build;
  - em/pl08.drs, textures-only (Leon without the jacket);
  - dc/native/r104/MAINSCENARIO.re4mesh and ps2-world.* from ps2rooms out/r104-ps2, with its tex;
  - the tex-r104 / tex-em13 / tex-pl08 pictures;
  - dc/movie/r104s00, s00c, s01, s02, s10, s20 .seq.
  make-route-fixtures.py sets r104, em13, pl08 and r104mov stage these files.

## Steps

| # | Step | Status | Evidence / commit |
|---|---|---|---|
| 1 | MOTION_RESERVE (ambush: cold-clip slots at bind) onto the tip; ambush run | done | 8c000e81: on in build-r21.sh. Knob-off .text/.data == p9w; STRICT vs r20k3w 0..1941; r100-s20 ambush preset (s20 571/571, em21/em2a, post-house call, 5100 frames) no HALT / no OOM; New Game -> r100, r101 entry, r103 entry no HALT. Slabs 2x27584 (55 KB heap 4); the idle script used 0 (its 75 loads were hot clips): the reserve covers player-driven cold clips. Also landed default off: MOTION_USAGE_LOG, HEAP_REPLACE_LOG, HEAP_CENSUS. Follow-up 121fcc4e MOTION_RESERVE_SPILL=524288 (in build-r21.sh): the two slabs thrashed in the r101 fight (net_crc32le 18.85% of non-idle PC samples, ~50 key reloads/s); a cold key now spills into heap 4 while 512 KiB stay free: r101 entry 3480 -> 4413 frames / 200 s (+27%), r100 ambush 0 spills (under the margin, slabs as before), STRICT vs r20k3w 0..1941 with 4 spills taken |
| 2 | Effects: coarse mode hands qualified effects to EFFECT_SPRITES instead of markers; land EFFECT_ROOM | done | fe79a373: COARSE_FX_SPRITES=2 in build-r21.sh (weapon / shot / blood sprites, no opaque markers): r101 kite fight windows (ticks 300..1200) equal to the control, r100 after the call -0.45 ms, first window +62 ms once (correction: the kite fixture's Leon dies ~80 s in, so its later "quiet" windows are the Continue screen; fe79a373's "r101 quiet" figures measured that screen); STRICT 0..1941; knob-off identical. EFFECT_ROOM landed default 0. Found on the way: fbb2ee2e, a short MOTION_FAST_READ (GD DMA in flight) halted "motion key read"; now falls back to the storage reader (forced-short test: no halt) |
| 2b | Room effects in coarse (user 2026-09-29: after 2): EFFECT_ROOM=7 costs +3.4 ms r101 / +3.9 ms r100 and thrashes VRAM in r101 fights (1598 vs 291 loads). Do: hw profile (PC sampler) of the +3 ms; a resident VRAM slab for effect textures; sprite paths for the non-EspCommonTrans classes (r100 leaves d0/4e, light shafts d0/08 Esp08, trails Esp16) | done | Cause (PC sampler + texture counters, 2026-09-29): with EFFECT_ROOM=7 the r101 fight runs 2203 frames / 200 s at 61% idle vs 4413 without (both with MOTION_RESERVE_SPILL); the UI texture cache thrashes (2990 loads / 2239 evictions in 1680 frames vs 766 / 91 in 3960): the room effects add ~1.5 MB of CI8 flip frames (45 x 96x96 at 32 KB 16-bit) to a working set already over the 2.44 MB UI budget, so textures cycle through disc reads. Measured fixes (r101 entry fight, EFFECT_ROOM=7, frames / 200 s; effects off = 4413): control 2203-2369 (idle 58-61%); the 32 loaded 96x96 effect frames as VQ (re4-assets-private/fx-vq-20260929, 1.18 MB -> 213 KB, PSNR 36-46 dB; fixture tour/rel-r101-entry-pw-fxvq.json) 2343; plus TEX_SLOTS=448 2773 (idle 50%). The 192-entry table recycles a slot on every new key (not counted as an eviction; 432 unique in-room keys); 448 needs the entry hints widened (COPY_LEAN, patches/tex-slots-hint-wide.patch, default image unchanged by construction) and costs ~63 KB of image (+57 KB .data), which heap 4 pays. Still VRAM-bound after that (1906 evictions): the effects-on working set is ~5.5 MB against the 2.44 MB UI budget. Next options, each lossy or costly, to decide by hw ms: VQ the large 16-bit room/model textures (vq_native_ui.py --model-min-bytes), a room-effects texture budget, fewer simultaneous effect classes. EFFECT_ROOM stays 0 in the play build until then. Model/room VQ measured 2026-09-29 (vq_native_ui.py --model-min-bytes 32768 over the 132 r101 fight textures >= 32 KB padded: 12.0 MB -> 1.77 MB VRAM, PSNR median 34.1 dB, p10 30.2, worst 25.6 = an alpha mask; the low ones are foliage / grass / alpha cut-outs; assets re4-assets-private/model-vq-20260929, fixture tour/rel-r101-entry-pw-mvq.json, look sheet model-vq-look.png): on the TEX_SLOTS=448 ELF with effect VQ, 3663 frames / 200 s (18.3 fps) vs 2773 (13.9) without it and 4413 (22.1) effects off; idle 31% (was 50%), loads 1185 (was 2578), freed 616 (was 1906); HALT 0, MISSING 0 (scenario kite-r21mvq1). Flycast proxy only, no hw ms yet. Room effects then cost ~9 ms/frame of Flycast time (was ~27). To land: TEX_SLOTS=448 (patches/tex-slots-hint-wide.patch) + the fx and model VQ packages in the staging; user decides the lossy look. LANDED 2026-09-30 (user: "do what makes sense"): EFFECT_ROOM=7 + TEX_SLOTS=448 in build-r21.sh; COPY_LEAN entry hints and the UI_HANDLES handle entry widened past 255 slots (the handle bug drew entries 256-447 with a wrong texture); the EFFECT_ROOM thrash guard (native_ui.cpp: an effect sprite never evicts; under pressure it draws only from resident textures, <= 4 new effect loads a frame). Found by the STRICT gate: without the guard the r101 bell fight with 16-bit effect frames reloaded textures every frame (6% game speed, ~1 tick/s; not a hang: the vblank heartbeat ran to the deadline). Play assets: tools/d367/texture-vq-rooms.sh, 304 model/room + effect textures as VQ (23.2 MB -> 3.5 MB VRAM, PSNR median 34.2 dB; PS2 world, manual and file keys excluded), staged by make-pw-fixtures.py. Gates: knob-off image = pw5 (.text/.data/overlay identical; .rodata differs only in the 5-byte __TIME__); STRICT tr8k (traced, ARENA_FIT_KOS_BYTES=147456 as in the play recipe; the default 131072 runs out of KOS heap with 448 slots + VQ) on the kite fixture: STRICT_TRACE_PASS over 0-1941 and --align room. With the VQ fixture the trace shifts at tick 184 (the room's enemies spawn a few ticks earlier): the entry preload fits 184 packages instead of 160 and takes 4.87 s instead of 4.4 s, so background DVD loads land on other ticks (the door-frame IO-timing class, not a logic change; an equalised arm is the open proof). r101 bell fight game speed per 300-tick window (Fast pacing): r21j effects off 25/43/15/59/85%; this build, effects on + VQ 26/47/36/75/95% |
| 3 | POST_F00 (Filter00 glow + contrast) + PVR_DITHER | done: off | a7dbcd3a landed default off, ~0 ms. Decision 2026-09-29 (user asked for my call): off in the play build. On the r101 PS2 world (r101-entry fixture) the play build is already at / above GameCube brightness (view mean 47 vs Dolphin r101 26-44); =1 / =4 lift it to 68 / 67. The "matches GC with Filter00" note came from the source-renderer world. PVR_DITHER is a no-op (KOS already dithers). Note: the default kite fixture stages no PS2 world (PS2MESH open failed, flat fallback): judge looks on rel-r101-entry |
| 4 | Door loading U0/U1/U2/U6 (IO_PROBE + dvdhold, TEX_KEEP, IO_ALIGNED, DVD_WAIT, DVD_FDCACHE); main-checkout extras (mkdisc.sh, tests, bake_room_prelit.py); PACE_PAGE vs the Options row | done | 4e9b4ccb: build-r21.sh sets TEX_KEEP=1 IO_ALIGNED=1 DVD_WAIT=1; DVD_FDCACHE lands default off. r100 -> r100 door x3 (tour/door-cycle-pw.json, emulated): baseline 13.1 s / 41 game frames per door, recipe units 8.3-9.6 s / 41 frames (the saving is CPU), all units incl. FDCACHE 7.6-8.9 s / 29 frames. Door-frame rule: the equalised arm holds each source request at its start (cDvdQueue::Read m_Rno0==0 && step==0; gating every step held reads in flight, +1 frame per door) until its baseline frame (tour/door/dvdhold.txt, 186 per-read targets), yielding like a contended step. U1+U2 (kite-r21dh12ch) and DVD_WAIT (kite-r21dh6wh) held: 41/41/41, aligned STRICT over the whole run. FDCACHE is parked: it moves the in-frame MemorySwap queue drain earlier (df 26 vs 38); the hold releases a drained request after 100 ms without a frame (no more HALT) but the doors come out 49-50 frames and FAIL, so it needs a different equaliser (worth ~0.7 s per door). Recipe arm (traced, kite-r21dkt) STRICT vs r20k3w 0..1941, resource 80; knob-off .text/.data identical. Extras landed fb082cbf (mkdisc.sh hardening, fixture-clock + r100 event-completion tests pass; test_event_file's host-compile error is pre-existing on the tip). PACE_PAGE not landed: it is a page of the boot quality picker, which the play build disables (QUALITY_PICKER=0, no boot picker); the title Options row stays a separate item and play discs keep Fast pacing + the R+START cycle |
| 5 | r100 + r103 PS2 worlds: extraction -> ps2_world_r4im -> any-room PS2_WORLD_MESH runtime | done (moved ahead of 4, user 2026-09-29: the fixes must be seen in the new world) | PS2_WORLD_ROOMS=2 in build-r21.sh. tools/ps2_room_r4im.py builds any room from the JADERLINK OBJ export (r101 reproduces the committed package: 190 meshes / 209 placements / level 0 47,770 vs 47,772; every triangle matches the wrapper in winding, UV, colour bytes, texture). r100 1.65 MB (177 meshes / 283 placements, 106 instanced), r103 1.14 MB. =2 opens the package at the room's first scenery bind and skips the Standard scenery package (r103 cannot hold both: 80 KiB heap-4 reserve); non-coarse images (route movies, events) draw the PS2 world at their first scenery part. Heap 4 free after open: r100 3.80 MB, r101 4.12 MB, r103 4.39 MB. Flycast steady ms control -> =2: r100 s20 37.1 -> 37.3, post-radio 26.8 -> 26.0, r101 entry 79.1 -> 78.8, r103 entry 67.3 -> 58.4. Knob-off identity; STRICT (traced, r101 package staged) passes 0..1941. Look: r100 forest floor / trees and r103 fences, house, trees now drawn (Standard showed dark ground and placeholder squares). Open: r100 authored colours are mostly saturated (median vc 1.99 vs r101 0.41), e.g. the gate hedge after the radio call is flat and bright; PS2 SMX colour semantics unknown. Staging: tour/*-pw.json (make-pw-fixtures.py); the play disc needs the same files |
| 6 | Full scripted run title -> r103 with screenshots (scenery, effects, manual, ambush); Windows + SteamOS packages | in progress | Play disc r21y (2026-10-04, 564f5168 = r21x + the camera fix + VMU CPU %): ELF route-build.sh z-play (sha f6a82e3f), C:/RE4DC-Play-Discs/r21y-title (fixture fixtures-x/title-x-pak.json; disc.bin sha 6808dc0b), GDEMU r21y-gdemu (track03.bin 7a37f37a), launcher D:/RE4DC-Play/Play-r21y.cmd. Checks: z-window (z-warp, camcrash fixture cw4: s20, A on the dead s03 Ganado = look-down camera, then the window jump): no reset, room enter 100 (#2), ~27 fps (y-warp resets at the jump every pass); z-newgame (z-play, newgame-x, 720 s): r120s00 1971/1971, r120s01 2360/2360, r100 s40 1175/1175, 26-30 fps ~100%; z-calls (calls-x): HALT 0; z-inv100: two restores ok; every run HALT 0, MISSING 0; H2 STRICT (z-tr vs y-strict): STRICT 1450..1569, to 740, from 1218, whole room DISCRETE with om only in the call window; GDI boot (gdi-r21y): VMU prompt, crash screen armed. Release archives read back member by member. Released as play-r21y-camera-fix-20261004. Play disc r21x (2026-10-04, a0618068 = r21v + the console fixes and PACE_VMU in build-r21.sh; route doc "r21x"): ELF route-build.sh y-play (DBG_WARP=0 PC_SAMPLER=0 PACE_MODE=fast PACE_DEBUG=1, sha fe7a3895), C:/RE4DC-Play-Discs/r21x-final-title (fixture fixtures-x/title-x-pak.json = title-v-pak + the call-voice aica_str.dat; disc.bin sha 81fc2d00), GDEMU r21x-final-gdemu (UTF-8, SECTOR=2352; track03.bin d44fcb0e), launcher D:/RE4DC-Play/Play-r21x.cmd. Checks: y-newgame (y-play, fixtures-x/newgame-x, 720 s): tex.pak 3,249 packages, r120s00 1971/1971, r120s01 2360/2360, r100 s40 1175/1175, r100 PS2 world, 27-30 fps at ~100% speed; y-calls (y-warp, calls-x): call voice stream 1:141 plays, no 'not in aica_str.dat', backing restore hash ok; y-inv100 (y-warp): two open/close restores ok, the Trans guard logs during the inventory; y-bridge (y-warp, bridge fx-near): no wall at the bridge; every run HALT 0, MISSING 0; H2 STRICT (y-tr vs w-strict): STRICT 1450..1569, to 740 and from 1218, whole room DISCRETE with om only in the call window (as r21w/x-tr); GDI boot (gdi-r21x-final, the GDI in Flycast, 240 s): VMU system-info prompt, crash screen armed, no fault. Release archives: every member read back against its source. Released as play-r21x-vmu-20261004 (supersedes r21v). Play disc r21v (2026-10-04, fe50a85a = r21u + the supervisor performance knobs in build-r21.sh; route doc "r21v"): ELF route-build.sh r21v-play (DBG_WARP=0 PC_SAMPLER=0, sha 0ceb121e; .text/.data/overlay = the gated v-play), C:/RE4DC-Play-Discs/r21v-title (fixture fixtures-v/title-v-pak.json: r21u's + registry r100/r101/r103 + pl08 pack, tex.pak 3,249 packages sha 2336f75b; disc.bin sha eced1c2b), GDEMU r21v-gdemu (UTF-8, SECTOR=2352; track03.bin 34624db0; also on the user's SD card as folder 150), launcher D:/RE4DC-Play/Play-r21v-Performance.cmd. Checks: inventory r100/r104 restore ok; New Game intros 1971/2360 + s40 1175, r100 25.9 fps (r21u 24.3); chapter end r106 -> save rc=0 -> r104 -> QTE miss; r100 calls, r101 bell (steady 24.8 ms vs 27.1), r103 entry; HALT 0, MISSING 0; H2 STRICT vs a timing-matched control; the GDEMU image boots in Flycast (high-density TOC) to the VMU prompt, crash screen armed, no fault. Released as play-r21v-performance-20261004 (supersedes r21t). Play disc r21u (2026-10-04, b730bf1a = r21t + lane/review-fixes-20261004: TEX_PACK retry spacing + the preload re-run after a pack read error; the play image differs from r21t's source in native_ui.o and texture_package.o only): ELF route-build.sh r21u-play (TREE=b730bf1a, DBG_WARP=0 PC_SAMPLER=0, sha d8d7abbe; .text/.data/overlay = the gated m4-lfp, 4 __TIME__ bytes), twin r21u-warp (sha f1238df0; = m4-lfw, the route-check build, 4 __TIME__ bytes), C:\RE4DC-Play-Discs\r21u-title (fixture title-invfix-pak-r1.json, STAGED_PAYLOAD_IDENTITY_PASS; disc.bin sha 709bb5a4, disc.cue 881f64d2), GDEMU r21u-gdemu (INPUT_CHARSET=utf-8 SECTOR=2352; disc.gdi 1bac5c9d, track03.bin 6abb499d; GDI_ALL_PAYLOADS_PASS, 1,143 files, 458,647 sectors at LBA 45000), launcher D:\RE4DC-Play\Play-r21u-Review-Fixes.cmd. Checks: GDI boot (gdi-r21u-boot, the GDI itself in Flycast, 240 s): high-density TOC, data track FAD 45150, the VMU system-info prompt, crash screen armed, no fault; u-newgame (r21u-play, newgame-invfix-pak, 720 s): tex.pak 3,242 packages, r120s00 1971/1971, r120s01 2360/2360, r100 PS2 world, r100 s40 1175/1175, ~30 fps at 100% speed; u-chapter (r21u-warp, chapter1-end-invfix-pak, 600 s): r106s00 1738/1738 -> VMU syswrite rc=0 -> r104s00 4856/4856 -> missed QTE -> s02 25/25; inventory u-inv100 / u-inv104 (r21u-warp): open/close restore hashes e0beb775, 897ceed3 (r100) and 4075bead, 46f4dcf7 (r104), all ok, the same as the landing-tree gate; route checks (m4-lfw = r21u-warp's code): r100 calls 1465/571/340, r101 bell events released, r103 entry; every run HALT 0, MISSING 0. Not released. Play disc r21s (2026-10-03, 4e387548 = r21r + the MOVIE_HEAP_EVICT cache loan; r21r can skip the r100 cliff cutscene): ELF route-build.sh pc18 (TREE=step1, DBG_WARP=0 PC_SAMPLER=0, sha c75b60a2), C:\RE4DC-Play-Discs\r21s-title (fixture tour/play/title-c14-pak.json, the r21r pack; disc sha 457e4454), GDEMU r21s-gdemu (SECTOR=2352), launcher D:\RE4DC-Play\Play-r21s-Cliff-Fix.cmd. Checks: route-ng15 (pc18, newgame-c14-pak, 720 s): r120s00 1971/1971, r120s01 2360/2360, r100 s40 1175/1175, r100 PS2 world 20 fps at 100% speed, pack in use, HALT 0, MISSING 0, rejects 0, upload failures 0; calls18 (the same source): route-hm4 the cliff movie 340/340, cache back. Not released. Play disc r21r (2026-10-03, b6d1798b = r21q + TEX_PACK): ELF route-build.sh pc17 (TREE=step1, DBG_WARP=0 PC_SAMPLER=0, sha bdb0d9ab), C:\RE4DC-Play-Discs\r21r-title (fixture tour/play/title-c14-pak.json = route/pack-fixture.sh of title-c13-pw: dc/tex.pak 3,241 packages, 92,399,616 B, sha bacdb614; disc sha 59bec3c6, 939 MB), GDEMU r21r-gdemu (SECTOR=2352, boots from the high-density TOC), launcher D:\RE4DC-Play\Play-r21r-Texture-Pack.cmd. Checks: route-ng14b (pc17, newgame-c14-pak, 720 s): intros -> r100 PS2 world, 20 fps at 100% speed, pack in use, HALT 0, MISSING 0, rejects 0, upload failures 0, textured; calls15 (the same source + IO_PROBE): route-pak7 preload 7.2 -> 3.1 s, route-pak8 6.5 -> 2.7 s. Knob off = r21q (.rodata __TIME__ only). Not released. Play disc r21q (2026-10-03, 31470549 = r21p + PS2_PRELOAD_LEAN): ELF route-build.sh pc16 (TREE=step1, DBG_WARP=0 PC_SAMPLER=0, sha 7856266b), C:\RE4DC-Play-Discs\r21q-title (fixture tour/play/title-c13-pw.json, disc sha 200bb415), GDEMU r21q-gdemu (SECTOR=2352), launcher D:\RE4DC-Play\Play-r21q-Walls-Loading.cmd. Checks (calls10 = the same knobs): route-lean1 (r100 s20..cliff) preload 16.3 -> 7.2 s, route-lean2 (east walk) evictions 73 -> 0, HALT 0, MISSING 0, fully textured. Play disc r21p (2026-10-03, dcda51ca = r21o + UV-guarded PS2 world packages + CLOSED_PASS_KEEP): ELF pc15 (sha 73274a0e), r21p-title (fixture title-c13, disc sha 55176b25, the seven -uvg packages staged), r21p-gdemu, launcher Play-r21p-Walls-Crash.cmd. Checks: route-uvhg house walls straight; r101 entry +0.6..1.3 ms. Knobs off = r21o / r21p (.rodata __TIME__ only). Not released. Play disc r21o (2026-10-02, 3d895078 = r21n + SS_PACK + MOVIE_HEAP_EVICT, the user's r21n play findings): ELF route-build.sh pc14 (TREE=step1, DBG_WARP=0 PC_SAMPLER=0, sha 830a66de), C:\RE4DC-Play-Discs\r21o-title (fixture tour/play/title-c12-pw.json, disc sha 94308391), GDEMU r21o-gdemu (SECTOR=2352), launcher D:\RE4DC-Play\Play-r21o-Calls-Cliff.cmd. Checks (calls6 = the same knobs): route-pk1 post-house call 0 textures released, no preload after it; route-s30d the r100 s30 cliff movie 340/340 with audio, then the examine view; HALT 0, MISSING 0. Knobs off = r21n (.text/.data/overlay identical, .rodata __TIME__ only). Not released. Hardware-test disc r21n (2026-10-02, 4fb5e61f = r21m + the SH-4 alignment fixes + CRASH_SCREEN): ELF route-build.sh pc13 (TREE=step1, DBG_WARP=0 PC_SAMPLER=0, sha 20f90b92), C:\RE4DC-Play-Discs\r21n-title (fixture tour/play/title-c12-pw.json, disc sha 823b9c4e), GDEMU r21n-gdemu (SECTOR=2352; boots in Flycast via the high-density TOC to the VMU system prompt, crash screen armed). Gates against r21m (pc12w): kite frame 2100 identical, heap 4 -12,288 B; bridge / r105 / chapter end / r107 state identical apart from heap figures; align runs 0 misaligned over r100-r107, movies, VMU saves, QTE, manual (route doc "Hardware readiness"). Not released. Play disc r21m (2026-10-02, chapters 1-1 + 1-2, dafd193e): ELF route-build.sh pc12 (TREE=step1, DBG_WARP=0 PC_SAMPLER=0, sha c77e5276), C:\\RE4DC-Play-Discs\\r21m-title (disc sha 9de549ae), GDEMU r21m-gdemu (SECTOR=2352, boots in Flycast via the high-density TOC), launcher D:\\RE4DC-Play\\Play-r21m-Chapter-1-2.cmd, packages RE4DC-r21m{.zip,-SteamOS,-CachyOS} (local). Fixture tour/play/title-c12-pw.json = the union of the r106/r104, r104/r107 and r105 route fixtures without warp/padscript/quality (72 shared keys, all byte-identical). Checks (pc12/pc12w): New Game 720 s (intros -> r100, 21 fps 100%), bridge (s44 x16, steady 27.5 fps 100%; was 3 fps 12% before d498fd14 + MOVIE_WINDOW), r106 chapter end -> save -> r104, r104 -> r107 (14.5 fps 97%), r105 chapter 1-2 end -> save -> s10 (then 11 fps 74%): HALT 0, MISSING 0, OOM 0. Play disc r21l (2026-10-02, chapter 1-1 + r104, ba84cbdf): ELF route-build.sh pc11 (TREE=step1, DBG_WARP=0 PC_SAMPLER=0, sha 24869fe7), C:\\RE4DC-Play-Discs\\r21l-title (disc sha ba88d618), launcher D:\\RE4DC-Play\\Play-r21l-Chapter-1-1.cmd. Fixture tour/play/title-c11-pw.json = route-rel-r106-r104-chapter2-pw.json without dc/warp.txt / padscript / quality (1017 files: r106 + r104 rooms, movies, PS2 worlds, chap01, em2a, pl08, em13). Checks: route-c11ng (pc11, New Game 720 s: r120 intro 1971 + 2360 -> r100 PS2 world -> r100 s40 1175, ~20.7 fps at 100% speed), route-c11walk (twin pc11w: r103 -> r106 door, PS2MESH 106 open, ~12.5 fps / 84% speed in r106), route-c11chap (pc11w: r106s00 1738/1738 -> results -> VMU syswrite rc=0 -> r104 s00 4856 -> QTE miss -> s02): HALT 0, MISSING 0, OOM 0, open failed 0/0/1 (the known early r104 PS2 world open at the chapter end, retried). No single run plays title -> r106; the user's play is that check. Play disc r21k (2026-09-30, ac855419 = r21j + room effects, thrash guard, 448 texture slots, texture VQ): ELF pw8 (clean objdir), C:\\RE4DC-Play-Discs\\r21k-title (disc sha c1e7cbb4), launcher D:\\RE4DC-Play\\Play-r21k-Room-Effects.cmd; packages RE4DC-r21k.zip (590,177,701 B, sha256 5f502126...) and RE4DC-r21k-SteamOS.tar.gz (583,374,756 B, sha256 0fa84fdc...), local only. New Game pad fixture (kite-r21pw8ng, 720 s): r120 intro -> r100 PS2 world with room haze, HALT 0 / MISSING 0 / OOM 0. Warp tour on pw8w (kite-r21t8*): all 7 spots HALT 0, MISSING 0, OOM 0, PS2 world open; frames vs the r21j tour (effects off) within 0-12% except the bridge police-car scene (720 vs 960 frames / 240 s; that spot is 10-16% game speed in r21j too). Earlier: Play disc r21j (2026-09-29, 4f52c954 + fb082cbf tools): ELF pw5, C:\\RE4DC-Play-Discs\\r21j-title (disc sha bc00d36b), launcher D:\\RE4DC-Play\\Play-r21j-Doors-Manual.cmd; New Game pad fixture (kite-r21pw5ng, 720 s): intro movies -> r100 PS2 world -> next movie, no HALT / MISSING. Warp tour of the same build with DBG_WARP=1 (ELF pw5w, fixtures tour/rel-*-pw.json, 240-360 s each, scenarios kite-r21tj{prad,s20,brdg,east,r101,bell,r103}): r100 after the radio call, the s20 ambush, the bridge (police car scene), the east door, r101 entry, r101 after the bell at the door, r103 entry: all HALT 0, MISSING 0, the PS2 world open in each room (PS2MESH room=100/101/103), 11-17 screenshots each (contact sheet r21j-tour.png, session scratchpad). Packages built locally, not uploaded: C:\\RE4DC-Play-Discs\\pkg\\RE4DC-r21j.zip (590,365,151 B, sha256 2bd860a3...) and RE4DC-r21j-SteamOS.tar.gz (583,573,045 B, sha256 2cf6635e...). Earlier: Play disc r21i (2026-09-29): ELF pw4 = ad0c59d0 recipe + DBG_WARP=0 (checklist play flags), tour/play/title-pw.json -> C:\\RE4DC-Play-Discs\\r21i-title (disc sha 13291cb6), launcher D:\\RE4DC-Play\\Play-r21i-PS2-Worlds.cmd. New Game pad fixture (newgame-pw, 720 s): r120 intro -> r100 with the PS2 world, no halt |
| 7 | Clean up the local copies (186 clones/worktrees, 35 plain trees) once nothing unlanded remains | in progress | Sweep re-run 2026-09-29 evening (tip ad010aff): 85 knob names in novel files are absent from the tip, all accounted for. Diagnostics only (POOL_PEAK_LOG, SKEL_AUDIT, COL_STATS, CAM_LOG, WQ_CAMLOG, MOTION_MISS_LOG, H4DIAG, ROUTE_ACTION_DIAG, NO_STD_CENSUS, SOURCE_CENSUS, WD_FREEZE_AT, TEST_BSS_PAD, EC_COUNT, SCEN_LOG, GPMEMO_LOG, HWCAL_*, DBG_BUILD_ID, MOTION_HASH, COLLISION_QUERY_OBSERVER: read-only, no speed claim). Rejected by the user: CUT_GORE (gore stays); QUALITY_LOW, PACE_PAGE, DBG_AUTOLOAD_QUALITY (the boot picker; QUALITY_PICKER=0). Superseded: scenery-trials CULL_/FOG_/TREE_/LANDMARK_ knobs, COARSE_HOUSE, COARSE_WORLD_LAYERS, COARSE_SOURCE_POLICY, CW_KERNEL, OT_LOD0/OT_GXNRM/OT_SKYNOFOG (all coarse- or original-world trials; the PS2 world mesh won), UI_TEXTURE_SLOTS (frontier/tree4; now TEX_SLOTS), FIX_R101_CALL_DONE (a test knob; the call reset itself landed as 4980a40 + 976c93d), A30_OBJSCR, ACTOR_CROWD_OPEN, FENCE_SPLIT. Measured and dropped: SKEL_PF (sq58/59), IK_PASS (excluded from ddea9bf on purpose), HERMITE_FLAT / GETPOS_MEMO (P7/P8), Codex MOTION_LEASE_LEAN / GAME_HF_ASM (G 29.18 / 29.76 vs control 29.17 ms: keep 0). Before deleting, every novel file and each git tree's uncommitted diff + local commits go to /root/probe/unlanded-archive-20260929 |

## Known open items outside these steps

- Player's Manual / file pictures: FIXED 4f52c954. ss_item_draw.cpp's GameCube MRAM range check rejected every DC address (no file picture was ever drawn); the route's 1 MiB RGB565 page packages could not upload in-room (~300 KB VRAM free) and are staged as VQ (re4-assets-private/manual-vq-20260929); every other file picture is adopted by its own key (re4-assets-private/file-pictures-vq-20260929, all 49). Fixture: tour/manual-pw.json (w11 file opens).
- Diagnostics to land default-off or archive (HEAP_CENSUS, HEAP_REPLACE_LOG landed 8c000e81): POOL_PEAK_LOG, SKEL_AUDIT, COL_STATS,
  SKEL_PF, IK_PASS, CAM_LOG, WQ_CAMLOG, MOTION_MISS_LOG, H4DIAG, ROUTE_ACTION_DIAG.
- Codex 09-27 trials to check: GAME_MOTION_PROGRAM / COLLISION_QUERY_OBSERVER, COARSE_SOURCE_POLICY / SOURCE_CENSUS.
- Not landing (rejected / superseded): CUT_GORE, scenery-trials CULL/FOG/TREE knobs, OT_GXNRM / OT_SKYNOFOG / OT_LOD0,
  COARSE_WORLD_KERNEL, HERMITE_FLAT, DBG_AUTOLOAD, HWCAL_*, FIX_R101_CALL_DONE, A30_OBJSCR, CROWD_LOD_OPEN, FENCE_SPLIT,
  QUALITY_LOW.
