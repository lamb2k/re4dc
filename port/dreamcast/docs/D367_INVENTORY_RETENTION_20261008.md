# Inventory retained-storage lifetime correction, October 8

A supplied VMU reproduces missing inventory Leon and a Green Herb Examine hang
on diagnostic ELF `3894026f`. The native renderer retains a borrowed preparation
cache inside the room heap. Inventory preserves and reuses a 3 MiB window of
that heap, but the renderer kept its old pointer and wrote preparation records
over inventory weapon/model data. At `0x8caf7640`, the weapon model texture count
became `1132559807` instead of `2`; the overwritten record is 0x2400 bytes into
the retained cell at `0x8caf5240`.

The swap entry now calls the existing
`re4dc_model_detach_retained_storage()` before packing or reusing the window.
Room heap ownership remains unchanged. The storage adapter already refuses
acquisition while inventory uses heap 12; room rendering reacquires its cell
after restoration. No gameplay, AI, collision, save contents, texture assets or
memory reservations change. The platform API handles disabled-renderer builds;
the game bridge must not guard this call with the renderer's private build macro.

## Qualification

* All ten native-model host variants pass with address/undefined sanitizers.
  Repeated detach, poison, fallback draw and reacquisition preserve exact output
  packets and leave the loaned bytes untouched. Removing the detach fails the
  sentinel check. Storage checks cover heap-12 refusal, room/movie ownership
  and the actual swap entry compiled without the renderer macro.
* Clean Dreamcast cross build has no unresolved symbols. Text/data/BSS section
  sizes match the diagnostic baseline. Disassembly confirms the call in the
  final candidate; an earlier guarded build omitted it and was never run.
* Normal cold title Load of an isolated, unchanged supplied VMU into r102 works
  in Flycast. Leon is visible, Green Herb Examine works twice, and three closes
  restore all 3,145,728 bytes exactly. Ordinary movement resumes afterward.
* A second cold-load run selects the supplied save's actual Yellow Herb. Two
  examinations stay open for over 30 seconds each, keep rotating and exit
  normally. Three further closes restore all 3,145,728 bytes exactly, with hashes
  `84007a52`, `a71572be`, `57be640a`; movement resumes. The full 900-second run
  completes without the original corruption/hang diagnostics.
* Matched uncapped village-combat control/candidate fixtures compare 4,079 source
  records (0..4078): STRICT, required decisions MUST-IDENTICAL. This fixture ends
  in game-over; it does not trigger or certify the bell movie.
* Matched house fixtures compare 3,234 records (0..3233): STRICT and required
  decisions MUST-IDENTICAL. Both present all 1,465 / 571 / 340 movie frames,
  preserve the 57,504-byte s30 starting heap, restore 3,144,608 radio-backing bytes
  with hash `e4bfc3ac`, and restore all 2,621 trace spans / 148,162 bytes.

The manual candidate ELF is
`1f3d269c14907b4a12c699eeff8099e508b9eb6d30ab516983c08ba564342f80`,
built from `d3e26223` plus the narrow swap-entry change. Play uses `ACT_CAP=0`
and `DBG_WARP=0`. Matched trace fixtures use the same current play recipe with
equal diagnostic trace storage/delay and test-only warp support.

Exact private reports are `retained-cache-qualification.json`,
`yellow-qualification.json`, `retained-bell-qualification.json` and
`retained-h2-qualification.json` under
`C:/Flycast-Evidence/re4-dreamcast/reporter-20261008`.

## Remaining acceptance

Physical Dreamcast verification remains pending. These are Flycast and host
checks, not console or continuous-route acceptance. Missing herb foliage,
inventory highlight/texture pairs and fallen-lamp fire remain separate visual
work. The bridge photograph identifies a PVR presentation-fence timeout; a
connection to this overwritten cache has not been established. No public binary
release, SD write, issue comment or issue closure is authorized by this source
qualification.
