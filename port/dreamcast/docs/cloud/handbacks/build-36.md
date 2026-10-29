# Build 36 — source-bound fallback scanner repairs

**2026-10-29 — progress 2:** Done: isolated texture selection/provenance adapter
and 40 public synthetic tests. Next: native-list and legacy-world adapters,
then the opt-in scanner integration and exact private-data commands. Blocked:
private-data completeness, to be handed to Claude after code qualification.
The scanner CLI is unchanged in this checkpoint; no new mode is exposed yet.

**2026-10-29 — progress 1:** Published the source-contract documentation
checkpoint as `95f5be02`; implementation and public qualification followed.

Branch: `codex/fallback-scan-fixes-20261029`. Rebased integration:
`2061c8380848695373714437d20462ef2b8a118d`.

## This checkpoint

Only `textures36.py`, `test_textures36.py`, and this hand-back are added/changed.
The resolver is not imported by the existing scanner. It reuses the unchanged
strict pack/texture readers. Canonical packed keys precede eligible loose data;
explicit ordered pack layers replace whole files, including removal of keys
omitted from the last pack. Unknown recipe/current-room quality stays
conditional. Physical duplicate-index, ordering, checksum, extent and overlap
refusals remain strict. Failed final layers do not restore replaced pack data.
Sources/payloads, offsets, layers and possible/shadowed variants retain hashes.

40 tests PASS: actual existing writer packages, malformed envelope/payloads,
sector-boundary duplicate/order controls, declared layer order, flat/bucket/
texlow selection, recipe unknowns, missing keys and JSON provenance.

```bash
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_textures36.py' -v
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
