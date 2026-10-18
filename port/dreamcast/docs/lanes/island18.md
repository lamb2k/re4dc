# Island18 (2026-10-18)

Island room/progress lane, branch `codex/island18`, based on freshly fetched `origin/t15/int` 7d7c05ab.
No integration-branch merge, release, or physical-console acceptance.

## Foundations merged
- e589d47f: lane/stress16b 44c2bdf4, preserving later recipe/castle/CH3/benchmark changes.
- 057edac3: lane/final16 926ad6f2. Both texture-skip predicates operate when enabled together. Final em31 module89
  is independent of WORLD_ROOM_MODULES exclusion; its slot remains ROUTE_FINAL-only.
- 58b87637: lane/ch5found16 249effe5, default-off RESIDENT_SKIP_LOG.

## Current Disc 1 identity
Fresh builds at 7d7c05ab and 58b87637, each current T15REC `rP` (not historical kP). Same pinned SH4ZAM
33fa4850, toolchain/private input paths and SOURCE_DATE_EPOCH 1760000000. Build guard, JOBS=4, separate fresh outputs.
Recipe source unchanged. Resolved knobs match after normalizing checkout/output paths; five added knobs are 0:
ROUTE_FINAL, STRESS_SADDLER, SADDLER_MASK_OPAQUE, NMR_PRELOAD_SKIP and RESIDENT_SKIP_LOG.

PASS: scrambled 1ST_READ.BIN and all ten overlays have identical names, sizes and bytes. Program is 3,218,448 B,
SHA256 `9dbb243431064e5b65c875f44ae4b75a14047a9c20f309d7c41b2b6c83d80c23`. Un-scrambled objcopy images also match.
Both builds have missing symbols 0 and `_end=8c400eb8`.
ELFs differ because their debug/source paths differ; program identity uses the actual packaged payloads.

Evidence: `C:\Flycast-Evidence\re4-dreamcast\island18-20261018\identity\identity-result.json`,
`effective-knobs-comparison.json`, private-input hashes and per-arm resolved-knobs/candidate logs.
Baseline retained read-only for castle18/logic18 identity reuse. No room/STRICT/KOS gate is implied by byte identity.

## Remaining work
Current detailed blocker reconciliation and room gates: workspace `codex-lanes/island18/STATUS.md`.
The recovered 33-room entry pass is earlier Flycast evidence, not a completed route or unseen boss/event proof.
U-3 resident body is 4,693,536 B and still needs an audited streamed-motion archive. Krauser's recovered streamed
body is already 1,423,712 B; gate it before regenerating. Saddler mesh/skeleton acceptance is under an independent
read-only audit: the stress preset's GC head table is not automatically PS2 skeleton equivalence for gameplay.
