# Build 36 — source-bound fallback scanner repairs

**2026-10-29 — progress 4:** Done: isolated legacy-world adapter and13 public
writer/corruption tests. Next: opt-in scanner integration, final identity
receipt and exact private-data commands. Blocked: private-data completeness.
The scanner CLI is unchanged; no new mode is exposed yet.

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

Only `world36.py`, `test_world36.py`, and this hand-back are added/changed.
The adapter is not imported by the existing scanner. It admits strict ordinary
legacy R4IM v1/v2/v3 geometry without R4PW, including oct-normal, prelit and
oct-vertex encodings. The result is geometry-only inventory: texture/pass/cull/
placement facts remain unknown and metadata is explicitly incomplete.

Any present sidecar goes through the existing strict parser, even empty bytes.
PS2 owner0x50, physical variants, v4 and unsupported appended/unknown extensions
still require their mandatory policy/adapter. Geometry extents, CRC, padding,
ownership, index/pool/strip ranges, finite grids and bounds are validated.

13 tests PASS using seven actual ordinary-writer outputs plus malformed
geometry, missing modern policy and present malformed/valid policy controls.

```bash
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_world36.py' -v
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
