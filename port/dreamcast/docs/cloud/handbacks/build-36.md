# Build 36 — source-bound fallback scanner repairs

**2026-10-29 — progress 3:** Done: isolated native-list membership adapter and
28 source-contract/identity tests. Next: legacy-world adapter, then the opt-in
scanner integration and exact private-data commands. Blocked: private-data
completeness. The scanner CLI is unchanged; no new mode is exposed yet.

**2026-10-29 — progress 2:** Published texture selection/provenance and 40 tests
as `0b1a3824`; native-list/world adapters and integration were next.

**2026-10-29 — progress 1:** Published the source-contract documentation
checkpoint as `95f5be02`; implementation and public qualification followed.

Branch: `codex/fallback-scan-fixes-20261029`. Rebased integration:
`bb5f18e0e3b3fac4c76bd42d0c9d8107385c568c`.

## This checkpoint

Only `room_lists36.py`, `test_rooms36.py`, and this hand-back are added/changed.
The helper is not imported by the existing scanner. It reads all four 64-entry
enemy tables, the 254-entry FileTbl and 11 stage list names from production
source, then binds recognized native ESL records through exact loader paths
and hashes to scanned ModelData keys. Player/costume/list alternatives remain
conditional; all BIN members are potential and instance counts are unknown.
The source-table hashes and list/record/archive/model provenance are retained.

Mutable non-DLL filenames, unsupported/core IDs, missing targets and ambiguous
case identities remain unresolved. Source-less replacements stay unassigned.
Changed unsupported Ashley/DRS/normalization contracts refuse mapping. No
filename is guessed from an enemy ID and no active actor/draw is asserted.

28 tests PASS: actual source aliases and four player alternatives, Ashley
costumes, mutable filenames, malformed source contracts, exact hashes,
missing/rejected archives, ambiguous paths, retained list alternatives,
source-less replacements, symlink containment and nonmutating output.

```bash
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_rooms36.py' -v
```

The tracked scanner entry point, all target sources/headers, build recipes,
game data and assets equal the rebased integration. Warm/cold runtime cycles,
loads/stores, 32-byte lines, code/data/stack/heap deltas are all zero.
**MODELLED whole-frame delta: 0 ms.** No target binary/image, private-data
completeness or console benefit is claimed from this isolated helper.

## Questions

None blocking code work. Final private rescan commands will be published with
the integrated `--scan36=1` entry point, which is not part of this checkpoint.

## Answers (Claude)

Pending.
