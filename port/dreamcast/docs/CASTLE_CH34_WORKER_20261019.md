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

## r20e armour package

The old r20e fixture lacks a native armour package. Its original emleon03
entries 178 and 187 through 194 select em3c types 0, 1 and 2. The source
`r20e_startArmor` task uses these list indices directly. Existing r216 full
models `armor-em3c-00w` through `03w` cover the same source family, including
their original weapons and chainmail.

The current package producer first reproduced the qualified r216 package
byte for byte. A private copy of its input metadata then added r20e as a
room, with every other cast input preserved. The producer generated a proper
r20e package from that copy; the entire payload after its 64-byte header is
identical to r216. Only the room byte and header CRC differ. Package size:
350,368 bytes. SHA256:
`45e6e57c9b32b410bf85513fc5bcd7a7070896fc06c0575988b43d1d7f48b098`.

The actual current target package checker, compiled on the host with
address/undefined-behaviour sanitizers, accepts it for r20e and rejects it for
r216. The data fragment also stages the existing prepared em3c archive
(`e8b7effe`) and its 18 original texture packages plus the existing atlases.
No mesh, motion, weight, image or material policy changes.

Private data is C-mirrored under
`re4-assets-private/castle18-ch34-armor-20261019`; `reuse-proof.json` and
`package-qualification.json` record the producer replay and loader checks.
Its manifest SHA256 is
`b03a56bade4364f7705db8e6cdcf6475b6d7321e48f6a14d9bd9a2da932239d6`.
The initial emulator test deliberately uses Leon and a focused camera to
check armour asset admission. It cannot qualify Ashley gameplay, armour
combat, cap-four progress, or the chapter route.

### First current-runtime check and preload correction

The 55.97-second `cx-r20e-walk-armor01` diagnostic uses the current c18oimW
program (ELF SHA `746a2a5feb7cf6293ea31c2738c815a3f6ce305a29c8af82b482ca8758b2136e`)
and checks all 23 boot/overlay payload hashes. Armour types 0, 1 and 2 draw
natively with no GameCube fallback, no texture errors and no audio failures.
These are dormant statues with Leon: no active-enemy or Ashley claim follows.
The first capture held no memory squeeze, so it is not a KOS 48 KiB gate.

Its ten late uploads are original source texture keys absent from the r20e
resident list. Their actual loose/package winners were read back and hashed.
The correction adds only those ten original width/height/format tuples,
preserving all 5,591 prior resident records and every other room. No texture,
model, animation, audio or program bytes change. The source r20e TSV records
the additions; `castle18/ch34-r20e-resident-20261019.json` is the private data
fragment. Compose these entries into any newer resident union, preserving
other workers' additions.

Candidate resident SHA:
`a1233414e1c35d43dd50f59c00ee1c73d86dbd7c678c21d881e8fdeba82d3686`.
Private data: `castle18-ch34-r20e-resident-20261019`; manifest SHA:
`4d71fffffdeb65e114a11ce55eac07f998bb76f7e4a4761000a370a9246e05fd`.
A new fixture adds `squeeze 49152 0` explicitly. The fresh corrected gate is
pending; it is not a strict identical-input comparison with the unsqueezed
first capture. Neither capture can establish chapter completion.
