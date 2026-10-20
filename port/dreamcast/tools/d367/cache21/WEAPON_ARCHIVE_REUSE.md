# Weapon archive reuse — 2026-10-20

`WEAPON_ARCHIVE_REUSE=1` repairs same-archive reuse after a prior weapon switch. It defaults to zero and changes only `src/game/read.cpp` through its scoped Makefile flag. No extra archive or animation allocation is introduced.

## Confirmed source defect

`ReadWepData` maps logical weapons to a character-specific archive. Originally it assigns `oldWepId` before calling `ReleaseWepData`. When a prior weapon is loaded, release clears that newly assigned ID to `0xff`. Following requests for the same archive therefore reload/unlink/rebind instead of taking the intended reuse path. The first ever load after a clean release can still reuse successfully; the defect must be tested after a real archive switch.

The enabled path publishes its identity only after successful read/link and hand prefetch. Release always invalidates it. A hit requires the mapped weapon number, actual FileTbl file identity, live linked module, non-null archive, matching player archive pointer and valid loaded weapon marker. File identity prevents an equal mapped number in another character's table from being confused with the current archive. Shared grenade/egg archives update the logical loaded weapon ID on reuse, preserving later release/continue bookkeeping.

The original `weaponRelease → weaponLoad → weaponInit` sequence remains: weapon objects and effects are recreated by the ordinary initializer; archive bytes and module linkage are retained only for the same admitted file. Explicit room/player/movie release still invalidates the archive. Distinct-file alternation still reads each file; this is not a multi-weapon cache and does not eliminate first-use textures, sound or hand reads.

## Checks completed

- `test_weapon_archive_reuse.py` extracts the actual `ReadWepData` and `ReleaseWepData` bodies and source tables into synthetic low-address DVD/module/heap fixtures. Four off/on × heap4 off/on arms pass 48 cases total under AddressSanitizer and UndefinedBehaviorSanitizer.
- A real prior archive followed by 20 same-archive requests performs 21 synthetic DVD reads in the original control and 2 with reuse enabled (one initial archive plus the requested archive once).
- Shared variants, distinct alternation, cross-family file identity, explicit release, missing module/backing, failed DVD admission, unsupported entry, continue bookkeeping, overflow allocation refusal/retry and heap-body release are covered. The fixture is not a target gameplay or I/O timing result.
- `check_weapon_object.py` builds only the actual SH4 `read.o` with heap4 off/on. In both cases, the stripped default-off object is byte-identical to the unmodified `2093aeb1` parent. Real Makefile values `2`, `-1` and `yes` are rejected.
- Enabled object changes with heap4=1: text +92 bytes, BSS +2 bytes, data unchanged. With heap4=0: text +124 bytes, BSS +2 bytes. These are object sizes, not final linked-program growth or timing.

## Required target qualification

Full linked-program off identity and enabled gates remain open. Preserve the existing motion-pack comparison candidate without adding this later patch to it. In a separate successor, verify repeated same-archive equip after a distinct switch, grenade/egg variants, different weapons, inventory return, movie release/restore, continue, room change and character-family change. Check weapon object/animation/effect ownership, hands, inventory and ammo behavior, read counts, heap/VRAM and audio. Do not claim whole-system or hardware closure from this patch.

Private receipts are retained in `C:\Flycast-Evidence\re4-dreamcast\cache21-20261020`; no game payloads are committed.
