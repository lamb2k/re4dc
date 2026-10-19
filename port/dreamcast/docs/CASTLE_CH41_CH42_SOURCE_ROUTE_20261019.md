# Castle chapters 4-1 and 4-2: source route preparation

Worker B, `codex/castle18-ch34`, 2026-10-19. This is preparation for the
continuous Castle queue. No chapter completion or new hardware timing is
claimed. Chapter 3-4's playable Ashley and original end save remain open.

## Original progression

The source audit reads 40 prepared Castle room archives. Their AEV tables
are identical across the selected recovered/current copies. Ordinary door
edges alone are insufficient: the original r221 elevator descent calls
`SceAtExecRoomJump(0x22B, ...)` on its first departure. The r22b s00 event
then calls `SceSetChapterEnd(CHAPTER_4_1, 0)`.

Chapter 4-1's work queue is r206, r210, r222, r201, r219, r211, r212,
r216, r213, r214, r217, r218, r215, r229, r221 and r22b. Required return
legs include r222 to r210, both r212/r216 to r211, and r217 to r214.
This list includes item branches and is not a shortest-path shortcut.

The original item records and consumers establish these dependencies:

| Consumer | Required original source items |
| --- | --- |
| r201 ornament altar | Item 0x1f from r209, 0x39 from r20e, 0x1e from r222 |
| r211 grate | Cup 0x6f from r212 and cup 0x6e from r216 |
| r216 armour encounter | Item area 0x80 completes before the original battle starts |

Chapter 4-2 follows r220, r223, r224 and r21d. Its original grave event
calls `SceSetChapterEnd(CHAPTER_4_2, 0xC)`. Boss18 supplies r224 data;
neither boss model choice nor room initialization establishes fight progress.

Final qualification starts from the preceding chapter's original save,
obtains and uses the original items, reaches the original chapter-end event,
and reloads its save without warps or flag pokes. No artificial inventory or
progress flags can replace these checks.

## Current program and effective enemy demand

The prepared r210/r222 diagnostics retain all 23 boot/overlay payloads of
the current `c18oimW` program, ELF SHA
`746a2a5feb7cf6293ea31c2738c815a3f6ce305a29c8af82b482ca8758b2136e`.
They use the original incoming door destinations and explicitly request
`squeeze 49152 0`. They do not fabricate chapter flags. Default-player
diagnostics do not prove the partner or preceding chapter state.

The actual `ps2_enemy_ch4.cpp` was compiled on the host with address and
undefined-behaviour sanitizers against the private include selected by that
program's resolved knobs. On the staged source enemy lists it reports:

- List 4: all 101 selected baseline rows verified, 20 replaced.
- List 5: all 163 selected baseline rows verified, 16 replaced.

The resulting effective-list inventory is source demand, not an active
enemy census or a cap-four progress result. It confirms r222's em11 types
8 and 9, r216's armour family, r221's two Verdugo rows, and r224's two
El Gigante variants without treating old GameCube rows as the active PS2
configuration. No runtime source or list data was changed by this audit.

Private audit data: `castle18-ch41-enemy-audit-20261019`, mirrored on C:.
Manifest SHA:
`9815b989d0a85ab5aac8a9d88df39ad77ebfa53e8032122aa7ad222191657ead`.

The existing r222 package passes the current target preflight on the host:
185,248 bytes, SHA
`f83af42a18b4802e15f5da6e7b60561d7be22e8100f2cd0348a0db5c87999ad9`.
This establishes structural admission only; a visible native draw remains
to be checked in the emulator. r210's older audio-fit failures likewise
need a current-program result before any repair or pass claim.

## Evidence

Under `C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\workers\ch34`:

- `ch41-ch42-source-door-inventory.json`: source paths, hashes, original
  doors, required item records and scripted elevator link.
- `ch41-prepared-entry-fixtures.json`: current program preservation,
  recovered room additions and retained current-file conflicts.
- `ch41-effective-enemy-demand.json`: actual source-function receipts,
  current private-include hash and effective actor-family demand.
- `r222-existing-package-preflight.json`: existing package host result.

Original source files supporting the chapter boundary and item obligations:
`src/st2/r201.cpp`, `r211.cpp`, `r216.cpp`, `r221.cpp`, `r22b.cpp`, and
`r21d.cpp`; record layouts are in `include/sce_at.h`.

## r210 audio preparation and first current check

The actual current r210 fixture still carries raw GameCube ROOM and FOOT
banks. The existing `aica_banks.fit` prebuilds those banks into the frozen
arena alongside the unchanged player bank. The preferred caps remain
16,000 Hz for ROOM and 11,025 Hz for FOOT; no further rate reduction or
layout change is needed. All non-audio archive bytes and source wavetable
bytes are identical. The two banks use 175,552 aligned bytes, leaving
760,576 arena bytes after the player bank.

Current-program `cx-r210-walk-audiokos01` ran 56.39 seconds with exact
`held=49152 requested=49152`, minimum KOS watch headroom 48,376 bytes,
native Leon and no texture errors. The two ROOM/FOOT failures are gone.
BGM0 still reports one allocation failure. There is no partner or complete
chapter proof. The final Flycast window also shows registration time near
208 ms with no active enemies; this is an unexplained emulator observation,
not a hardware measurement or a diagnosed cause.

The remaining BGM0 failure is container entry 14. Its recovered chapter 3,
chapter 4 and Castle copies are byte-identical to the current raw bank.
The existing builder prebuilds only its ARAM slice, preserving every other
container byte, all source wavetable bytes and the frozen layout. Its eight
samples use 208,416 bytes inside the 264,576-byte BGM0 slot at the unchanged
32,000 Hz preferred cap. The existing ADPCM checker reports 24.0 dB SNR.
A matched current-program emulator check is recorded below.

Private ROOM/FOOT set: `castle18-ch41-r210-audio-20261019`, manifest
`a717f403f01ac9f1f23c87751950142172fffeed91406c742465eaa8a0ef1034`.
Private BGM14 set: `castle18-ch41-bgm14-20261019`, manifest
`996b005042e7f03898c7527be2513e47219a24b356c36da868ec7de41459b349`.
Both are mirrored on C:. The additive fixture is
`tools/d367/castle18/ch41-r210-audio-20261019.json`; compose only its checked
BGM slice into any newer container rather than replacing other bank edits.

## r210 matched audio check

`cx-r210-walk-fullaudiokos02` completed 56.30 seconds and exited its owned
emulator. All 7,032 staged payload names match the ROOM/FOOT-only control;
only `bgm/bio4midi.dat` has changed contents. All 23 boot/overlay payloads
remain exact. The allocator reports `held=49152 requested=49152`, with
49,552 bytes minimum remaining KOS watch headroom. There are no audio-fit
failures, texture errors, VRAM refusals, evictions, retries or fatal rows.
Leon draws natively (450 census samples, zero GameCube samples).

The last official VRAM row is a preload summary at frame 181. Later native
stream receipts through frame 480 retain 138 loads; they show no growth in
that observed interval, but do not certify residency through the whole
room or chapter. No partner or active enemies are present. The 46-second
still was inspected. These are diagnostic entry gates, not a complete
chapter, combat, cap-four progress or Ashley acceptance.

Late Flycast registration time still reaches approximately 208 ms with no
active enemies in both matched runs. The audio correction does not resolve
that slowdown; its cause remains open. No hardware performance claim is
made.

Evidence in the worker folder: `r210-fullaudiokos02-gate.json`,
`r210-fullaudiokos02-vram.json`, `r210-fullaudiokos02-characters.json` and
`r210-fullaudio-matched-proof.json`. The capture log SHA is
`f8144f92a30173314e3b1018311dd72825410dc1f55d8578a5ec0d5d9bb2e305`;
the staged disc SHA is
`2e5dffb688da8b50c19095c3fc7f3fef6642e7c09ad4d3b66a4d39de48df0745`.

## r222 audio preparation

The selected r222 archive also carries raw ROOM/FOOT banks. Its existing
em11 voice bank is already prepared and remains byte-identical. The normal
frozen-layout fitter selects 11,025 Hz for room ambience and 8,000 Hz for
footsteps, using 220,096 aligned bytes. Enemy voices retain their existing
8,000 Hz cap and 682,208 aligned bytes; 101,888 arena bytes remain. The
footstep image size is unchanged from its preferred-cap size. This uses the
existing fitter policy, not a new audio layout or enemy voice reduction.
All archive bytes outside the two audio ranges and all original wavetable
bytes are preserved. BGM14 reuses the r210-checked conversion; its source
container hash is verified before substitution.

Private set `castle18-ch41-r222-audio-20261019` is mirrored on C: with
manifest SHA
`741491b9ad4d30f3262753c3071b63d8279adcd7efc79f2bd5d67a0d7971b1e4`.
The additive fixture is `tools/d367/castle18/ch41-r222-audio-20261019.json`.
The current-program entry `cx-r222-walk-audiokos01` completed 56.66 seconds,
with its owned emulator exited. The exact reserve is
`held=49152 requested=49152`; minimum KOS watch headroom is 49,752 bytes.
All 23 program payloads remain identical. Audio-fit failures, texture
errors, refusals, evictions, retries and late gameplay texture uploads are
zero. The actual gameplay VRAM summary at frame 767 has 421,536 pinned,
487,104 dynamic, 1,568,672 free and 1,550,336 largest-free-block bytes;
native stream receipts through frame 1200 retain 121 loads.

Enemy draw acceptance is explicitly withheld. Three em11 actors are alive
at approximately 45 metres, but every recorded em11 draw pass is skipped:
`native=0`, positive `crowd`, and `NMRD admitted=0`. The stock CAST-GC and
NOT-DRAWN checks pass because the actors have census rows, even when those
rows report only skips. That is not evidence of a rendered native enemy.
Leon has 1,500 native census samples and no fallback. The 45-second still
was inspected. A nearer diagnostic must prove actual admission and drawing
before the enemy models can pass. No checker or runtime rule was relaxed.

The original dragon targets, combat, moving scenery, ornament pickup and
return to r210 still need progression checks; entry alone cannot qualify
them. `r222-source-trigger-geometry.json` records original trigger volumes
and effective enemy placements for the next diagnostic without fabricated
room flags. The original area 6 controls the side-dragon appearance; area
10 is the second treasure-box trigger near the active source monks.

Evidence: `r222-audiokos01-gate.json`, `r222-audiokos01-vram.json` and
`r222-audiokos01-characters.json`. Capture log SHA:
`f3c10d1e5358b410c7bccbe08e506c93e32dd040603176a14e81d395b2050863`.
Disc SHA:
`268ebbed9c8167369c55ee918ffaeec03416fef26ff5483015fb71cab58d50a6`.

## r219 cart route and audio preparation

The original r201 door area 0x21 enters r219 at its near platform. This is
more than a simple r201-to-r211 corridor: original r219 areas 2 and 3 run
`toroko_go`, then reload r219 with part 1 or 2 so `toroko_ret` can perform
the arrival. Both events check `CheckDoorJumpWithAshley`, position both
characters on the cart, use the room's original character/cart motions and
restore the hands and weapons. Departure requests stream 1:0xe4; arrival
requests 1:0xe5. Final route qualification must cover those events with
Ashley, including their audio, before the ordinary r211 exit.

The diagnostic entry fixture preserves the current 23 program files and
uses that original r201 door destination. It does not establish the
preceding chapter's partner state. The existing frozen-layout fitter
prepares the raw ROOM/FOOT banks at their unchanged preferred caps of
16,000/11,025 Hz: 135,648 aligned bytes alongside the unchanged 68,064-byte
Ashley bank, leaving 800,480 arena bytes. All non-audio archive bytes and
source wavetable bytes remain exact. This is host preparation, not an
emulator or event-audio pass.

Private set `castle18-ch41-r219-audio-20261019` is mirrored on C:, manifest
`6cf68a625106b7630762dbfdb7eb4b2920971f234007c980a0f67fd45b858d7b`.
Additive fixture: `tools/d367/castle18/ch41-r219-audio-20261019.json`.
Evidence: `r219-entry-preparation.json` and `r219-audio-fit-proof.json`.

The selected 76-stream file lacks both original cart streams, 1:E4 and
1:E5. A header inventory of 30 retained containers found neither. The
existing converter prepares those two original 32 kHz stereo sounds;
their encoded lengths are 131,072 and 180,224 bytes. The additive 78-entry
union preserves every previous descriptor, offset and encoded payload.
All 78 source descriptors match the original stream headers. The current
c18oimW resolved capacity is 80, so no program or capacity change is needed.

Private set `castle18-ch41-r219-streams-20261019` is mirrored on C:, manifest
`5e95da70d4ac1b3e4a5bbad01ec70f3087af6b779a5568a825788aa1635c3a37`.
Output SHA:
`208dcd229c1cd985b6165fdff31d9f30116f723af970003ebe5c4de389bc0143`.
The source fragment is `tools/d367/castle18/ch41-r219-streams-20261019.json`.
Compose only these two additions into newer stream unions. These are host
checks; actual playback and both original cart events remain unqualified.

The current-program entry `cx-r219-walk-entrykos01` completed 56.39 seconds,
held the exact 49,152-byte reserve and left minimum KOS watch headroom of
48,752 bytes. All 23 program payloads remain unchanged. Texture errors,
audio-fit failures, fatal stops and VRAM refusals are zero. Leon has 450
native census samples with zero fallback. The program loads both added
32 kHz stereo stream-index entries; neither cart event plays in this entry
check. There is no Ashley model census, so her HUD does not prove her model.

The last official VRAM row is only the frame-182 preload: 907,488 pinned,
zero dynamic, 1,602,592 free and 1,571,840 largest-free-block bytes. Later
stream receipts through frame 480 retain 143 loads, but complete room
residency is not qualified. The 45-second still shows the near cart platform
and Leon. Late Flycast registration reaches about 190-196 ms at global ticks
649-661, with no active enemies, similar to the unresolved r210 observation.
This is not hardware timing or an attributed cause. The original cart
sequence, partner, audio playback and chapter traversal remain open.

Evidence: `r219-entry-proof.json`. Log SHA:
`b48f5da19094c9739f378f81b30aa900c5e47a60842c813ea0d727b721644378`.
Disc SHA:
`a0a9df001abbda5f204db141a129cc54ebe93af0c6f18de60e5c60b31a076edc`.
The finished disc was retired after sealing; logs, stills and results remain.

## r211 cup-route entry preparation

The diagnostic fixture uses the original r219 area-1 destination, retains
the 23 current program payloads and adds 137 recovered room files. The
original statue tasks require cup 6E from r216 and cup 6F from r212, then
the original grate event before the r213 exit. Entry cannot qualify them.

The unchanged frozen-layout fitter prepares ROOM/FOOT alongside the
682,208-byte aligned em14 bank. It selects 11,025/8,000 Hz under its existing
policy and uses 201,056 aligned bytes, leaving 120,928 arena bytes. All
non-audio archive bytes and original wavetable bytes remain exact. This is
host preparation; runtime and preceding partner-state overlap remain open.

Private set `castle18-ch41-r211-audio-20261019` is mirrored on C:, manifest
`b400c71aa8b2394c99f231ed9602eb6781cb544c7f2a25cb34af0481c3b1fda2`.
Archive SHA:
`fb19ffd6e2afef92bfc8ffddc6b48ea65264149f223aae2ad503c524de37f4eb`.
Source fragment: `tools/d367/castle18/ch41-r211-audio-20261019.json`.

The current container still has raw BGM7. An inventory of 18 retained
containers found the exact prepared source bank in the island lane's
`island18-r300-sound-20261018` data. Its original wavetable, sample count,
source identity and frozen layout match. Reuse copies only its 637,306-byte
ARAM range at offset 4,498,016; the actual encoded sound image is 165,916
bytes at 32 kHz, inside the unchanged 264,576-byte BGM0 slot. All other bytes,
including the checked BGM14 and original MRAM, remain exact. No codec or
audio quality setting changes.

Private set `castle18-ch41-bgm7-20261019` is mirrored on C:, manifest
`25bbfb7d63dd820eb2bfa8196ccf4c17286fd21237cf1b02d814cfff437fce86`.
Output SHA:
`d413a6ee6f894baa0d83bd8326ca763822522c78522c7b4fa97b97b40c385413`.
Source fragment: `tools/d367/castle18/ch41-bgm7-20261019.json`.
Apply only that checked slice to newer containers. Actual r211 playback
and room checks remain pending.

## Supplemental first-pass checker recovery

The worker wrapper inherited a checker path into a deleted October 13
checkout. Its private invocation now points to the selected worker tree's
existing checker, with no changed gate criteria. That checker was run
against the six retained r20e, r210, r222 and r219 logs. Entry, fatal-stop,
warp-directive, PS2 world, source-fallback and texture checks pass. Overall
results remain `UNPROVEN`, because these stationary diagnostics do not
establish a short walk and the checker requires a separate asset-provenance
audit. The explicit reserve, residency and actual-admission audits above
are independent and remain unchanged. No room or chapter pass is inferred.

## r222 near-enemy diagnostic and residency correction

`cx-r222-walk-neararea10kos02` starts at the original area 10 centre,
100 mm above its trigger floor, facing original enemy-list row 23. It
changes no room flags. It completed 56.53 seconds, with the exact 49,152-byte
reserve held and minimum KOS watch headroom 49,272 bytes. The two nearby
type 9 monks now have actual `NMRM admit` receipts and positive native
draw counters: 3,000 cumulative census samples, zero GameCube fallback.
Leon has 1,500 native samples, zero fallback. Texture and audio-fit errors
are zero. This does not cover the distant type 8 dragon operator. The
46-second camera is obstructed by scenery, so visible appearance is still
unqualified despite the actual draw receipts.

The near diagnostic exposes three late texture uploads, so residency
fails. All three actual package winners and source dimensions/formats were
audited: `f96f7e1f-7f97a831` (1024x512, format 6),
`ac23b5fe-01af40e8` (64x64, format 6), and
`ec7b1745-32ce202e` (64x128, format 6). Their pixels, models and runtime
programs are unchanged. The additive candidate preserves all 5,710 newest
Worker A V12 records and every other room, adding only these three r222
records. Its prior r222 entries exactly match the control's entries.

Private set `castle18-ch41-r222-resident-20261019` is mirrored on C:,
manifest SHA
`deb8ef63b858be3b0b111ed334b7c057ad635c4f22172ee6f373b2ce360e87ff`.
The 5,713-record resident SHA is
`902a55450efcbae7be9fdbf6f4cfae986da77e350c08577bc09f31c795b7e2f4`.
The matched near-enemy check `cx-r222-walk-residentkos03` passes the bounded
residency gate. It completed 56.28 seconds and held the exact 49,152-byte
reserve, with minimum KOS watch headroom 49,272 bytes. Across 7,048 staged
payloads, only `dc/resident.bin` changes; all 23 program files, room data,
models, textures, audio, warp and input remain exact. Late gameplay uploads
fall from three to zero. The two nearby type 9 monks retain actual native
admissions and 3,000 native census samples, with zero GameCube fallback.
Texture errors, audio-fit failures, refusals, evictions and retries are zero.

The gameplay VRAM row at frame 767 reports 594,624 pinned, 471,712 dynamic,
1,410,976 free and 1,390,592 largest-free-block bytes. Later native stream
receipts through frame 1080 retain 124 loads. The 45-second still remains
obstructed; appearance, the distant type 8, combat, dragon targets, ornament
pickup and the original chapter route are not qualified. Compose the three
records into newer unions; never discard another worker's additions.

Matched proof: `r222-residency-matched-proof.json`. Candidate log SHA:
`f5240741df4474da097f7d20cf29812f4694d005baec3c46558b165522141cf4`.
Candidate disc SHA:
`841f861a1ab308d268427ee9e6f4ed3ac47ec99c0188aebf0d91aff6d8a86680`.

Evidence: `r222-neararea10kos02-gate.json`,
`r222-source-first-sight-winners.json`, `r222-source-trigger-geometry.json`
and `r222-resident-host-proof.json`. Near diagnostic log SHA:
`aec010314a3c2df5a3d0789f876a32b1bc6815f7db39056e8f570959a2dcbeef`.

## r211 original-entry short walk and preload correction

`cx-r211-walk-audiokos01` completed 56.48 seconds in Flycast using the
unchanged c18oimW program and all 23 exact boot/overlay payloads. The
allocator held exactly 49,152 bytes; minimum KOS watch headroom was 39,832
bytes. The original r219-to-r211 entry and one normal 16-tick forward input
produce 868.6 world units of horizontal displacement. This is diagnostic
setup, not original chapter traversal. Leon has 1,500 cumulative native
census samples and zero GC fallback; no Ashley or enemy coverage follows.

ROOM/FOOT and the recovered BGM7 load prebuilt. BGM7 is actually requested
and copied: 165,916 bytes, eight samples, original 32 kHz. Texture errors,
audio-fit errors, fatal rows, VRAM refusals, evictions and retries are zero.
The 45-second still shows Leon and the picture gallery clearly.

The official residency check fails on nine late uploads. At gameplay frame
767, VRAM reports 654,048 pinned, 772,736 dynamic, 1,050,528 free and
1,011,648 largest-free-block bytes. Stream receipts through frame 840 keep
183 loads. All nine actual source keys, dimensions/formats and selected
loose/package bytes were read back and hashed; no texture or model is
changed. The additive correction preserves all 5,729 Worker A V14 records,
including its new r20b cold-load additions, and adds only these nine r211
records. Every other room remains exact. The previous r211 entries equal
the control's entries.

Private set `castle18-ch41-r211-resident-20261019` is mirrored on C:.
Manifest SHA:
`0de2206ff97b266c8538fd8368dd7113e308730d79e895ae887e3e47b0977daf`.
The 5,738-record resident SHA is
`faf18768a268d1f2b3b465a8eee21ed7bd943828586f18c26b6ea78fc7049b12`.
Source fragment: `tools/d367/castle18/ch41-r211-resident-20261019.json`.
Compose only the r211 additions into newer unions. The matched rerun
`cx-r211-walk-residentkos02` passes bounded residency: nine late uploads
fall to zero. It completed 56.06 seconds, holding the same exact 49,152-byte
reserve with the same 39,832-byte minimum KOS headroom. Across 7,275 staged
payloads only `dc/resident.bin` changes. All program, room, model, texture,
audio and controller-input bytes remain exact. Both runs record the same
868.6-unit walk and 1,500 native Leon census samples with no GC fallback.

The gameplay frame-767 VRAM row reports 654,048 pinned, 772,736 dynamic,
1,050,528 free and 1,007,616 largest-free-block bytes. Later frame-840
receipts keep 183 total loads. No texture, audio-fit, fatal, eviction,
retry or refusal errors appear. The final still was inspected. The partner,
cup pickups, six-enemy ambush, gate, original exit and full no-warp chapter
remain unqualified.

Matched proof: `r211-residency-matched-proof.json`. Candidate log SHA:
`a75accc2e6af743bf15ce4ebd8715844c71b4d236a5f6071fb126dc0c92122ae`.
Candidate disc SHA:
`d11a6c3d1544e701f66a50d316893328c215e1368e070c38424c71258a7d10f2`.
The finished candidate disc was also retired after sealing its proof.

Evidence: `r211-entry-proof.json`, `r211-source-first-sight-winners.json`,
`r211-resident-host-proof.json`, and the original capture/checker reports.
Control log SHA:
`ee359317c7bd2b418a6ee6c562d7f3267e273ab9a5e97f8e49b914373a9ccaca`.
Control disc SHA:
`5599fe324677f69c178c81be759eb603718b474fa0ddf02066a5db463e55d49d`.
The finished disc was retired using the guarded worker pruner; all logs,
stills, results, program hashes and rebuild inputs remain.

## r212 original-entry audio and event preparation

The diagnostic fixture starts at the original r211 area-1 destination:
(4060, 0, 1980), facing -pi/2. It preserves all 23 current program payloads
and adds 144 recovered room files. Its unsolved puzzle source can create
Ashley through its original SubCharInit/CHASE call; the fixture adds no
partner flags, progress flags, health changes or enemy substitutions.

The existing frozen-layout audio fitter includes both the original em11
and Ashley banks, 750,272 aligned bytes together. It prepares ROOM/FOOT at
the existing 11,025/8,000 Hz policy, using 232,064 aligned bytes and leaving
21,856 bytes in the 1,004,192-byte arena. All original non-audio and wavetable
bytes remain exact. This is host preparation, not a runtime memory pass.

Private set `castle18-ch41-r212-audio-20261019` is mirrored on C:.
Manifest SHA:
`852c6fc551698bf8d0c071f785daa1c9039fccff12d4a778a63fb6e45502310d`.
Archive SHA:
`87be8ff30a4d300ee48c20ce2f4d848727949ab9f05153b7f31d7cc647d29f02`.
Source fragment: `tools/d367/castle18/ch41-r212-audio-20261019.json`.

The actual staged base BGM table has no sequence-bank request for r212.
Its two original stream choices, 0:32 and 0:33, both already have prepared
32 kHz entries in the selected 78-entry stream file. The recovered roof
movie `dc/movie/r212s00.seq` is present (4,434,758 bytes), SHA:
`70a6f8f5b0a7c4b124e323b047c0b110a9773b04bb9ee7a1e8c0d2fc6388fb12`.
These are file/table checks, not movie playback or audible acceptance.

Source progression still requires all four plates occupied by Leon,
Ashley and the two racks, the area-1 roof movie and shootable catches,
Ashley's area-13 live drill trigger, both retained drill Ganados' deaths,
the cup 6F pickup and original return. The room tasks retain enemy-list
rows D7/D8, so later cap handling must preserve those references. No room
or chapter completion is inferred. Evidence: `r212-entry-preparation.json`,
`r212-audio-fit-proof.json`, and `r212-source-events-audit.json`.

## r216 original cup and armour-wave preparation

The next diagnostic starts at the original r211 area-3 destination. It
adds seven recovered room files, retains the current 23 program payloads,
and uses the existing native armour family already source-audited for
r20e/r216. The original source cup pickup invokes area 0x80, waits for the
real item flag, closes the door and starts the first three armours. Three
source deaths release the next three; six open the exit. The room retains
enemy handles, so a cap implementation must preserve those references.
Current c18oimW has PS2_ENEMY_CASTLE=0xe7, including mask 0x04; its original
PS2 display rule sends only display armour E8. No flags or actors were
edited in the fixture, and no live wave is qualified yet.

The existing fitter keeps the preferred ROOM/FOOT rates at 16,000/11,025 Hz,
using 163,136 aligned bytes beside the 204,864-byte em3c bank. It leaves
636,192 bytes in the unchanged sound arena. All non-audio and original
wavetable bytes remain exact. The staged original BGM table has no r216
entry; this is not a claim about actual runtime sound or silence.

Private set `castle18-ch41-r216-audio-20261019` is mirrored on C:.
Manifest SHA:
`19b3ecc065ff65e2390df61ae78fcf4c9d1f8b9232eb36d54efb726b92804e3a`.
Archive SHA:
`4ee89dc7f321564f951a959416dba9bfaa9b22bac2b94b9e4c36818fee5bb06a`.
Source fragment: `tools/d367/castle18/ch41-r216-audio-20261019.json`.
Evidence: `r216-entry-preparation.json`, `r216-audio-fit-proof.json` and
`r216-source-stream-and-wave-audit.json`. Runtime audio, actual armour draw,
cup pickup, both waves, door release and the original route remain open.

## r219 original cart flow and bounded residency correction

The original A-button cart event runs from diagnostic near-platform placement:
E4 departure, original self-room part1 transition, E5 arrival, actor placement,
and resumed gameplay. The 55.86-second initial run and unchanged 56.12-second
tail share all disc/program bytes and an exact saved state; their log histories
overlap by 818 lines. All 23 boot/overlay payloads remain c18oimW / ELF746a2a5f.
The exact 49,152-byte KOS reserve holds, with 45,912 bytes minimum headroom.
TEX, audio-fit, fatal, VRAM refusal, retry and eviction errors are zero.

Read-only decompression of both original states uses five independent exact
ELF anchors. Both states prove r219, gameplay phase3 and Stop0. Leon is within
five units of the original (-78700,0,-351315) endpoint. Ashley has 600 HP and
starts exactly at the original (-79287,0,-351366) endpoint before ordinary
follow motion. Original Flycast state thumbnails and both framebuffer views
show the far hall. An earlier suspected image/log mismatch was an incorrect
inference from the missing partner census row, not a demonstrated capture bug.

Native Ashley remains unqualified: runtime actor id03 has141 parts and seven
live infos, but all seven lack current asset/adoption certificates in both
states. The joined census contains Leon only. Archive pl11 is actor03; absent
census is not evidence of an absent partner. This needs independent admission
work, not a visual-only pass or an invented solo-cart claim.

E5 records one audio underrun. Late Flycast registration time is about207ms
with zero hostile enemies; its cause remains open and it is not hardware
performance evidence. The final room generation has eight late uploads.
Across departure and arrival there are ten distinct missing source keys;
the other two appear only during departure. Their source dimensions/formats
and actual loose/package winners were read back and hashed unchanged.

The additive correction preserves all5,755 Worker A V16 records and adds
those ten r219 keys, producing5,765 records. Every other room is byte-exact.
Private set: `castle18-ch41-r219-resident-20261019`, mirrored on C:.
Resident SHA: `0f24b9b6ab80f6ee2be86c840c63f731bf1675802d6f3f104b99736cbe0ad99b`.
Manifest SHA: `5164760ea78d7c53720321c0973f016587bc435e1281f5d1818896d8e82dc5d7`.
Source fragment: `tools/d367/castle18/ch41-r219-resident-20261019.json`.
Matched runtime residency now passes: eight late uploads fall to zero,
with all ten departure/arrival source keys covered. Only dc/resident.bin
changes across 7138 payloads. The 55.66-second initial run and unchanged
55.91-second tail overlap by816 exact log lines. Exact KOS reserve remains
49,152 bytes, minimum headroom45,592. Gameplay frame767 has622,272 pinned,
377,472 dynamic,1,477,568 free and1,437,696 largest-free-block bytes. Later
frame840/960 receipts keep288 loads. Original cart flow and Ashley600 HP
remain, with no texture/fit/fatal/refusal/eviction/retry errors. One stream
underrun and about207ms late Flycast registration remain; no speed gain is
claimed. Native partner and full chapter gates remain open.

Matched proof: r219-residency-matched-proof.json. Joined log SHA:
`f7a3ab13c58fb6b9abd81ed0875f9d4e0fc71b53d0efbd77a5dfab3f1b890b55`.
Matched disc SHA: `b52bfbde48f5d5da46ea44f323d2691d90aeda3ba38eeef48349614af8c403bf`.
Compose only the r219 additions into newer unions.

Evidence: `r219-cart-flow-proof.json`, `r219-saved-state-audit.json`,
`r219-cart-continuation-provenance.json`, `r219-source-first-sight-winners.json`
and `r219-resident-host-proof.json`. Joined log SHA:
`e968cc919d2b4e34d57a48a3dd642cdfba1441b27c541338e4322d820c152b12`.
Disc SHA: `56d40692fbb0cf19596e4556f811a266ff74272aa94dfed3a432027eb2c15430`.

## r219 missing native partner package

The joined runtime log explicitly reports both r219 registry.re4nmr and
partner.re4nmr absent at both loads. The source fixture contains the exact
existing prepared pl11 archive but no partner package for this room.

Data-only preparation reuses the validated r207 full Ashley partner:
ashley11, ashley11-h1 and ashley11-h3, covering21 original source roles.
Only the room header and header checksum change; every payload byte,
geometry array, skin, source role, material, parent and bind remains exact.
The229,952-byte pack needs no new model conversion or runtime capability.

All original BIN/part facts are independently re-derived. Texture facts
match the existing generator's source-proven bump-only key rule for TPL5
indices4/6/12; their header/sampler facts remain exact. This preserves an
existing admitted capability and introduces no new drops. Six atlas/pair
tokens resolve to the already-staged packages, including derived colour-mask
pairs. The prepared pl11 archive remains SHA
`ecf3098097fcb2b2c86d632b62fd3d9112e61f5e39b56819db6a2e277fffcfa2`.

The actual host loader accepts the partner in219 with an empty primary,
and refuses the identical package in218. Private set:
castle18-ch41-r219-partner-20261019. Package SHA:
`2f25149420bb81e14ec3a546c5efe3b52513ca6a66149857eaf1026ad799ba5f`.
Manifest SHA: `b245d5bb1e1172ed2d4423d635d414feb75ea4fceaf1c6a07df913db92f1e756`.
Source fragment: tools/d367/castle18/ch41-r219-partner-20261019.json.
Runtime acquisition and submitted native drawing now pass for the bounded
original cart flow. The 55.95-second initial capture and unchanged56.12-second
continuation share exact disc/program/state bytes and801 identical log lines.
Both Ashley and Leon have4,395 summed native census counts and zero GC counts;
these are cumulative census samples, not distinct frames. Declined, registry
declined and absent remain zero. All seven live Ashley infos have original
archive assets and current adoption certificates in both final saved states.
The self-room transition retires generation1 with zero live owners/row users
and opens generation2 cleanly. Original cart end positions, phase3/Stop0,
Leon1440 and Ashley600 remain. The saved-state thumbnails were inspected:
the full partner is visible at arrival, including hair/skirt and torso.
This bounded view does not qualify every cloth pose, room route or chapter.

Exact reserve49,152 holds; periodic KOS headroom minimum48,312. Texture-check,
audio-fit, fatal, refusal, guard, eviction and retry failures are zero.
Four native atlas/mask keys still upload after each room preload. Their
correction preserves every one of Worker A V17's5,768 records, adds four
r219 entries and leaves all other rooms exact. Eleven additional source
first sightings belong to the original door-loading phase and remain in
the evidence ledger rather than being treated as native room-game uploads.

Private set: castle18-ch41-r219-native-resident-20261019, mirrored on C:.
Resident SHA: e776711c58b93c7affcea345df37cab41bdb8ddbd4f0f300f351c42b9dd80259.
Manifest SHA: e1609e574348241f6934000a499a89d00c67d148ecf75434429054d3bc059cb7.
Source fragment: tools/d367/castle18/ch41-r219-native-resident-20261019.json.
The matched native-partner residency now passes: four late uploads fall
to zero. Only dc/resident.bin changes among7,139 payloads; all23 programs,
native packages and other assets remain exact. The newer resident union
also carries Worker A's already-admitted three r20c entries. Initial55.89s
and unchanged tail55.83s overlap by800 exact log lines. KOS reserve49,152
and periodic minimum48,312 remain; later840/960/1080/1200 receipts hold265
loads. Native Ashley/Leon stay4,395 cumulative census counts each, GC0;
all seven Ashley infos remain owned/adopted and the cart completes normally.
No texture, fit, fatal or VRAM failures occur. This run reports zero stream
underruns; earlier-control underruns are retained, so no universal claim.
Final gameplay VRAM has597,696 pinned,340,608 dynamic,1,539,008 free and
1,507,328 largest-block bytes. Late registration remains around190ms.
Proof: r219-native-residency-matched-proof.json.
Matched disc SHA: f1c2c96736290b14c41521bea7db41068fa266e38ef224626efdc3d4b6ec11ae.
Joined log SHA: ddee26f91b8f3c13607808b3ff32c06b23f5d18c1bf7c286521e2c9cd87544a3.

Native-control disc SHA:
504c4709c5f3bac7b74577e4d2ff4c9e96b65e05fdfd06665b12cc8c34d9d5a0.
Joined log SHA:
f8f2091386ae4d486b0ba2d476309367be0f264190629ea5ee37642dc8afeb47.
Final tail state SHA:
08fba9314535e4e41665f291b86f9b4bc23c50ca640980b89ce73f6aa168640b.
Late zero-enemy Flycast registration remains about190ms and2.8 FPS.
The performance problem is open; no console timing or speed gain is claimed.
Proofs: r219-partner-host-proof.json, r219-partner-final-saved-state-audit.json,
r219-partner-cart-continuation-provenance.json and the native source/resident
ledgers. Finished control disc links were retired after sealing the evidence;
states, logs, stills, program bytes and source data remain.


## r212 full partner input prepared

The original unsolved-room R212TrapInit creates Ashley and selects chase.
The existing fixture had her exact prepared pl11 archive and the113,760-byte
primary enemy registry, but no native partner package. Reuse of the validated
full partner changes only its room header/checksum to212; all21 original
source roles, geometry, skins, materials, bindings and texture winners remain
exact. The actual current host loader accepts primary plus229,952-byte partner
together, and refuses the partner at wrong room211. This tests shared record
capacity; it does not qualify target heap residency or puzzle gameplay.

Private set: castle18-ch41-r212-partner-20261019, mirrored on C:.
Package SHA: 8a0224900426aead056b038147f18870983f2725ed54b429f4001587640e9998.
Manifest SHA: f5159079589894dd73647c7206e05d904cbcff96dfaf5854b055ff6399a57923.
Source fragment: tools/d367/castle18/ch41-r212-partner-20261019.json.
Runtime native/cloth, 48KiB reserve, plate/ceiling/drill/cup events and chapter
acceptance remain open. Proof: r212-partner-host-proof.json. Source-created
Ashley is retained; the entry fixture adds no partner flag or puzzle bypass.


## r212 package-derived partner preload

The four full-Ashley atlas/mask keys qualified by the r219 cart run are
also missing from r212's resident list. They are added before its first
native gate, with each actual r212 texture winner checked byte-exact.
These are package-derived expected inputs, not r212 runtime observations.
The data preserves all5,772 current union records and every other room,
adding four r212 keys for5,776 total. The loader/source dimensions and
formats remain unchanged. Actual guest residency and memory remain pending.

Private set: castle18-ch41-r212-partner-resident-20261019, mirrored on C:.
Resident SHA: 2d5d4613b96af8bc70daaafee0dce6203077097dcc37e7293d4c49d14fa9569e.
Manifest SHA: ff1ec70e8f9ff7c23c57325fecefa240017c9521c988c680cd90dc0570926760.
Source fragment: tools/d367/castle18/ch41-r212-partner-resident-20261019.json.
Proofs: r212-partner-package-texture-ledger.json and
r212-partner-resident-host-proof.json. Compose only the four r212 keys
into newer resident unions.
