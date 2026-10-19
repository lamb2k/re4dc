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
