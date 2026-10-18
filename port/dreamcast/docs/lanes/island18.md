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

## U3 motion admission and audio diagnostic, 2026-10-18

`bf7bf79d` adds default-off `MOTION_LARGE_CLIPS=1` for the exact sealed all-cold em32 v2 archive only. The existing cache owns the two 102,336-byte slabs; the SH4 target slot size is 16 bytes. Requested fixed footprint is body 1,132,416 + slabs 204,672 + metadata 1,568 = 1,338,656 bytes. The body's 50,816 bytes of FCV headers are already counted. Actual play also used spill/cold-pool cells: this fixed number is not a total live peak or a stable-residency claim.

Host tests exercised the actual 98 private clips, malformed archives, allocation/read failures and pin exhaustion under bounded/large/fast-read combinations. Legacy v2 and recovered v3 archives passed with the new knob enabled. Historical PPC-source comparison also fails the pristine 7d7c05ab control; the source evaluator is unchanged. A separate current host pose-helper attempt failed during source extraction before any pose comparison, so evaluated-pose transport equality is not claimed.

Fresh Flycast `i18u2mW` ELF `16e28e8bad4d61bd23107a9482e2885fff3128c474c9830f2937b2cfa600e806`, source `564938ba`, configured capture 60 seconds, `r31b` scenario `cx-r31b-walk-u3s1`:

- Actual staged boot and every selected overlay matched the candidate SHA before capture.
- Real r31b event/movie callback sends U3 and advances routines 1/9 -> 1/16 -> 1/8. No HALT/FAULT/MISSING; TEX and LEON checks pass. This is not boss completion.
- Motion archive binds 98 clips. Nine cache misses, four spill allocations and two evictions were observed. Simultaneous consumers therefore exceed the two fixed cells; no zero-read-in-play or complete-fight residency acceptance.
- Heap4 observed minimum 314,720 bytes / largest 314,144. Movie KOS minimum 3,384 bytes is low; the required 48 KiB squeeze remains unpassed. VRAM end used 2,178,272 / free 299,040; dynamic/pinned/largest peak ledger remains open.
- CAST remains FAIL: `ATX_WHY semantics=16 detail=131076`, info2 flagsDC4. Source em32 move installs active texture blend ratio255/type2, so the existing idle-blend exception cannot admit it. Model/material work belongs to boss18 (I-005); no gate was relaxed.
- Recovered em32 archives retained raw GC sound. Existing `aica_banks.py fit` prebuilds EM0 into the frozen room arena: 374,736 bytes at 11,025Hz, reported ADPCM SNR20.8dB, arena remainder146,720 bytes. Only the sound payload changed; native archive/motion bytes compare identical. Guest now plays block8 SEs, prebuilt/runtime blocks8/0 and no sound fit refusal. Audible quality is not user acceptance.

Private verified sets, Windows mirrors under `C:\Game Dev\Emulators\re4-assets-private`:

| Set | SHA256SUMS SHA256 | Scope |
|---|---|---|
| island18-u3large-20261018 | 66e246f71cf4fa56fb0dc1d7a18a787ec22e42a6be8619008f14e0ca412376aa | 98 streamed clips and sealed all-cold archive, diagnostic only |
| island18-u3sound-20261018 | e28590f10a07a5d06d5b05ad0a0c9af0a955a1ece3a9e9e6297bf6d5f3fae32a | sound-only derivative, em32 DRS SHA97315b825f1600e82f2f9152b96fbbade04732f22cad9520d509cb1dfdc36035 |

Evidence: `C:\Flycast-Evidence\re4-dreamcast\island18-20261018\h-i18u2\scenarios\cx-r31b-walk-u3s1` and preceding `u3e3` semantic control. Frozen Disc1 T15REC rP post-large program and ten overlays remain byte-identical to 7d7c05ab; `identity/postlarge-identity.json` records actual bytes. Chapter diagnostic recipe is isolated in `tools/d367/island18/recipe.sh`, never T15REC.
