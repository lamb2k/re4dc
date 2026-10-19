# Chapter 3-4 preparation, 2026-10-19

Worker B owns chapter 3-4, then 4-1 and 4-2. Main integrates chapters in route
order. This checkpoint qualifies playable-Ashley source texture preparation;
it does not qualify the chapter, her PS2 model, or a performance gain.

## Actual chapter boundary

The source chapter 3-3 end is `r206_die_event` in `src/st2/r206.cpp`.
Chapter 3-4 then includes the sniper rescue in that room. The source sequence
destroys partner Ashley, calls `PlSelect(1)`, and executes the original exit.
The route continues through r20d, r20e, r20d and back to r206. Its reunion
event calls `SceSetChapterEnd(CHAPTER_3_4, -1)`, transfers Ashley's collected
items and money, and opens her inventory before the terminal sequence.

The release gate must start with the original chapter 3-3 end save and finish
with the original chapter 3-4 end save, without warps or flag edits. The old
r20d/r20e entry fixtures do not prove this: they use default Leon, while
`R20dInit` sets up the puzzle differently for `pl_type == 1`. One old r20d
fixture jumps to the reunion at frame 200.

## Playable Ashley is a separate source actor

`cEmMgr::construct` creates `cPlAshley` for player model id 0 / player type 1.
`ReadPlayerData` selects FileTbl 0x22, `em/pl01.drs`, for her normal costume.
The current c18oimW symbol inventory includes her constructor, model setup,
hands and motion functions. The existing `ps2_ashley.py` conversion covers
partner pl11 / model id 3 and cannot be substituted without a separate proof.

| Role | Original BIN | Original TPL |
|---|---:|---:|
| Body | 4 | 5 |
| Face | 7 | 9 |
| Hair | 6 | B |
| Skirt | 8 | 5 |
| Extra | A | 5 |
| Default right hand | 11 | 5 |
| r20e right hand | A7 | A8 |
| Open left hand | 14 | 5 |
| Closed left hand | 15 | 5 |

These roles come from `src/game/pl_ashley.cpp`. r20e also selects a separate
original motion table. The face uses source shape data; the skirt is marked
with its original 0x40 flag. Native coverage of these states remains open.

## Verified input and prepared data

Nine recovered pl01 archives are identical, SHA256
`a85e4185a4d3cf11cd1573b229ec9d0df7397a3107edc3afc9236f97a5146ddb`.
All nine role BIN/TPL pairs and every referenced entry match the original
source after endian conversion. Original source SHA256:
`7dbffe5a7111f53dd20b491308bdaaca15cf7aab483e3a4866af8824020bb529`.
The base staging disc contains that same recovered archive, verified by
reading it back. Its absence from an additive fixture is not a missing file.
The source loader also deliberately accepts an archive without an NTR table.

The only tool change adds pl01's audited model TPL ordinals 5/9/B/A8 to
`prepare_actor_texture_fixture.py`. Existing whole-body source normalization,
upload-only selection, and preservation checks are unchanged. Every retained
BIN, FCV, SEQ and EFF payload and container/audio byte is preserved by those
checks. No game source, recipe, model geometry or residency list changes.

The prepared body is 807,968 bytes, down from 1,055,424 bytes: 247,456 fewer
resident bytes in the data representation. This is not a measured runtime
memory or speed result. The transport container appends a replacement body
and grows to 2,335,392 bytes on disc. It has 30 source texture references
backed by 25 distinct native texture files. Archive SHA256:
`3dcf9e8f50912309d49a9fe3fbbb23a7c1a944e469270dab80c3c4519bafd405`.

The actual `SourceIdentityTable` implementation was compiled into a host
probe with address/undefined-behaviour sanitizers. It accepts all 30 prepared
records, resolves their expected keys, and rejects wrong dimensions, interior
pointers, corrupt table CRC and a truncated archive. This proves the offline
identity interface, not emulator, console, or native PS2 model acceptance.

Private evidence and data (not tracked in Git):

- `C:/Game Dev/Emulators/re4-assets-private/castle18-ch34-source-audit-20261019/audit.json`
- `C:/Game Dev/Emulators/re4-assets-private/castle18-ch34-player-textures-20261019/fixture-report.json`
- The same data folder's `host-qualification.json`, `fixture-additive.json`
  and `SHA256SUMS`.
- Reproduction scripts under `codex-lanes/castle18/workers/ch34/`.

## Next checks

Prepare fixtures against the current Castle programs and source door graph.
Check the real Leon-to-Ashley transition, her source model/motion/cloth/hands,
lantern and crank interactions, r20e puzzle and armour encounters, return to
Leon, inventory transfer, and original chapter save/reload. Native model,
residency, audio, KOS 48 KiB and complete no-warp progress all remain open.
