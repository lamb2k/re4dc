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
A matched current-program emulator check is pending.

Private ROOM/FOOT set: `castle18-ch41-r210-audio-20261019`, manifest
`a717f403f01ac9f1f23c87751950142172fffeed91406c742465eaa8a0ef1034`.
Private BGM14 set: `castle18-ch41-bgm14-20261019`, manifest
`996b005042e7f03898c7527be2513e47219a24b356c36da868ec7de41459b349`.
Both are mirrored on C:. The additive fixture is
`tools/d367/castle18/ch41-r210-audio-20261019.json`; compose only its checked
BGM slice into any newer container rather than replacing other bank edits.
