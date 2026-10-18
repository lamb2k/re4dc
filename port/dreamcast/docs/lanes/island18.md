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

Host tests exercised the actual 98 private clips, malformed archives, allocation/read failures and pin exhaustion under bounded/large/fast-read combinations. Legacy v2 and recovered v3 archives passed with the new knob enabled. Historical PPC-source comparison also fails the pristine 7d7c05ab control; the source evaluator is unchanged. The subsequent pinned private host helper passes all98 raw clips and294 sampled evaluated source poses on the97-part source skeleton (IKfalse). This does not establish PS2 retarget, SH4 arithmetic, visual or fight acceptance. Evidence: u3-pose-transport/result.json.

Fresh Flycast `i18u2mW` ELF `16e28e8bad4d61bd23107a9482e2885fff3128c474c9830f2937b2cfa600e806`, source `564938ba`, configured capture 60 seconds, `r31b` scenario `cx-r31b-walk-u3s1`:

- Actual staged boot and every selected overlay matched the candidate SHA before capture.
- Real r31b event/movie callback sends U3 and advances routines 1/9 -> 1/16 -> 1/8. No HALT/FAULT/MISSING; TEX and LEON checks pass. This is not boss completion.
- Motion archive binds 98 clips. Nine cache misses, four spill allocations and two evictions were observed. Simultaneous consumers therefore exceed the two fixed cells; no zero-read-in-play or complete-fight residency acceptance.
- Heap4 observed minimum 314,720 bytes / largest 314,144. The earlier allocator-only movie kos_free3,384B is not total KOS headroom. Subsequent original-partition i18k3mW holds49,152B and reaches the same real-event phase; minimum total KOS44,680B/top43,680B. VRAM end used 2,178,272 / free 299,040; dynamic/pinned/largest peak ledger remains open.
- CAST remains FAIL: `ATX_WHY semantics=16 detail=131076`, info2 flagsDC4. Source em32 move installs active texture blend ratio255/type2, so the existing idle-blend exception cannot admit it. Model/material work belongs to boss18 (I-005); no gate was relaxed.
- Recovered em32 archives retained raw GC sound. Existing `aica_banks.py fit` prebuilds EM0 into the frozen room arena: 374,736 bytes at 11,025Hz, reported ADPCM SNR20.8dB, arena remainder146,720 bytes. Only the sound payload changed; native archive/motion bytes compare identical. Guest now plays block8 SEs, prebuilt/runtime blocks8/0 and no sound fit refusal. Audible quality is not user acceptance.

Private verified sets, Windows mirrors under `C:\Game Dev\Emulators\re4-assets-private`:

| Set | SHA256SUMS SHA256 | Scope |
|---|---|---|
| island18-u3large-20261018 | 66e246f71cf4fa56fb0dc1d7a18a787ec22e42a6be8619008f14e0ca412376aa | 98 streamed clips and sealed all-cold archive, diagnostic only |
| island18-u3sound-20261018 | e28590f10a07a5d06d5b05ad0a0c9af0a955a1ece3a9e9e6297bf6d5f3fae32a | sound-only derivative, em32 DRS SHA97315b825f1600e82f2f9152b96fbbade04732f22cad9520d509cb1dfdc36035 |

Evidence: `C:\Flycast-Evidence\re4-dreamcast\island18-20261018\h-i18u2\scenarios\cx-r31b-walk-u3s1` and preceding `u3e3` semantic control. Frozen Disc1 T15REC rP post-large program and ten overlays remain byte-identical to 7d7c05ab; `identity/postlarge-identity.json` records actual bytes. Chapter diagnostic recipe is isolated in `tools/d367/island18/recipe.sh`, never T15REC.

## Island residency recovery and first QTE, 2026-10-18

Recovered `resident.bin` SHA5cd0e26a carried zero of the existing nonempty island TSV lists, although entry-only gates passed. The private derivative preserves all 3,996 base/core records and restores 1,371 records from the current 40 tracked island lists. It changes no program or texture bytes. Host coverage of every island list passes. Blob86,016B SHA865aa5cf29fbdd816ef95338d1d3268257281aa8e7989790367cea19700c8088; Windows mirrored set `island18-resident-20261018`, SHA256SUMS6584d997142da2cd0c4d21fd05421ca38254083d2e2d017c3e5b05b35ce1784e.

Fresh Flycast i18u2mW (same ELF16e28e8bad4d61bd) 60-second configured runs, actual staged boot/all overlays checked:

| Scenario | Current result | VRAM tick767 pinned/dynamic/free/largest bytes | Limit |
|---|---|---|---|
| cx-r310-walk-res1 | entry/no fatal/CAST/TEX/LEON/short walk PASS; sound refusal0; swap/restore CRC27fd456f | 637024 / 1561632 / 278656 / 251904 | loads160 by final preload181 remain160 through840, eviction/retry0 (previous partial list51/1). Full route/model provenance still unproven. |
| cx-r30f-walk-res1 | entry/no fatal/CAST/TEX/LEON PASS; sound refusal0; 8 kills and actual cap peak4 with held sends released | 494848 / 780064 / 1202400 / 1163264 | loads172 by final preload181 remain172 through960, eviction/retry0. SceCountEmAlive counts held sends by PS2 design, so its6 is not six active enemies. Full bulldozer completion unproven. |

Sound-only derivatives use the existing frozen arena and preserve every byte outside sound payloads. Set `island18-room-sound-20261018` is mirrored, SHA256SUMSd77eda23649bd7cb18aadfdf0bb1477dbf077738e52db6672cb53ce98e6157f0. em36 EM0 at11,025Hz362,788B/SNR20.3dB leaves234,880B with actual r310 room/Ashley banks. r30f ROOM11,025Hz294,356B/SNR22.0dB and FOOT8,000Hz50,872B/SNR20.2dB leave45,632B with soldier/Ashley. Sound load/play verified; audible quality not user acceptance.

No recovered r317 movie sequences existed. Unchanged converter and existing288x192 full-range policy produced all15 PS2 SFDs s00–s14,42,500,860 seq bytes; s15 is EVD-only (no SFD in source AFS). All transport sizes/frame counts/bounds/source-member hashes verified and immediately Windows mirrored: `island18-r317-movies-20261018`, SHA256SUMSe99170475fe39bdd8c97d544fb0717942e1dc73149b1402c8e64012db0c4c882. Companion PS2 EVDs are retained as analysis, not substituted for GC EVD execution.

Fresh r317/qte1 plays s00 and the s08 failure branch, with failed actual A+X input. qte2 uses actual source L+R/A+B exclusive chord inputs: s00 passes1/19, s07 passes82/96, s09 starts before the capture ends. No state-bit clearing, forced success or validation change. Entry/no fatal/CAST/TEX/LEON pass; complete QTE chain remains open. New room/foot prebuilt set `island18-r317-sound-20261018`, SHA256SUMSb2318c23e6ed8bdedcf4faf43b6549d9fdc0177e542996a95f6375b817628be5, removes both sound refusals in qte2. Allocator-only movie kos_free3,192–3,832B excludes extendable break. Original-partition i18k3mW with49,152B held passes these two QTEs with total KOS minimum56,936B/top56,128B. No partition recipe change is required by these windows.

## Current shadow and event checkpoints (2026-10-18)

Default-off ACTOR_CAST_SHADOW_EMPTY only refines the broad source shadow-receive refusal for exact PS2 Leon plans0x100/0x108 when a bounded, stride-validated light manager has zero source pre-frustum candidates. Any candidate, null work or invalid manager still refuses. The actual source selector and actual helper pass4,608 host states, including masks/index31/32, mode, kind/frustum and invalid managers. No source shadow-manager allocation is called by the helper. It remains out of the chapter recipe pending room gates.

Fresh Flycast i18s2mW (ELF4d033dba3d6c03c4f030e61955d49a4cd75f1816e5e1045b226c21ec987113ac), r300/sh2, natural980-frame landing movie and radio, original KOS partition with49,152B held: repeated semantics11 fallback is removed, native Leon draws30/60 at frames213/243 with zero declines. One frame180 identity fallback remains, so CAST/LEON FAIL; TEX/no fatal/audio pass. No room acceptance. i18d3rP with this knob off reproduces frozen7d7c05ab 1ST_READ.BIN and all10 overlays byte-exact; evidence identity/shadow-empty-off-identity.json.

r317/skip3 uses ordinary START/chord/mash inputs, passes six chord windows and clears the17-press mash failure bit, then ends final s05 and schedules radio. The resulting wound adds GC ARC0xE/0xF as a tenth info; pl08 expects9 and missing32x16 key8f359de1-44158660 is observed. CAST/TEX/LEON fail; elevated asset/contract investigation is requested through the parent. Skipped movie cancellation lacks most source cancel clips, so this is route-input progress and not visible QTE acceptance.

r327/busy1 with current resident union enters and passes drawn CAST/TEX/LEON checks, but late18,432B key1aad1b6c-e247646e still loads after preload. Existing-knob ownership-skip diagnostic is pending. I-006 adds an explicit alive-vs-drawn enemy gate: recovered r31c CAST pass cannot qualify invisible em39; boss18 owns that model, island18 still owns motion/room progress.

## r327 explicit shared resident key (2026-10-18)

RESIDENT_SHARED_R327(default0, now in island-only recipe) preserves exactly the explicit r327 record1aad1b6c-e247646e/256x256/fmt14 from TEX_PKG_SKIP. It does not disable inferred enemy preloads or any other role-key exclusion. Registry68d1d0e2a5a621d names it as appearance202/bodyrole0/BIN22b/TPL22c/ftex25, but current play still needs the source key.

Fresh Flycast i18s5mW f4ae39095879c2451f87c6aa62c2eff9171d7d47bff7dc3a1f7f31c2f6ea4815, r327/res3, original49,152B KOS held, own staged boot/alloverlays verified: key loads during preload178; total280 loads by180 remain280 through840. No fatal/CAST/TEX/LEON/audio checks pass. Tick767 pinned1,139,040/dynamic767,296/free570,976/largest471,040; peakpinned1,906,336; evictions/retries0/0. No fullroute, all-actors visibility or model-source acceptance. Source8a67905f plus pinned exact override draft; later4ad2113a changes only MCHECK context logging.

Current T15REC off i18d5rP has identical program9dbb2434 and all10 overlay names/sizes/bytes to frozen7d7c05ab. Evidence identity/shared-resident-off-identity.json. Actual extracted source/replaces-key predicates pass1,625 queries on this package. All nonzero identities agree. Null ftex26(0/0,128x128/fmt3) is explicitly rejected by source_key and matched by replaces_key; that pre-existing distinction is retained. Evidence registry-predicate-equivalence.cpp/json.

## Krauser actual-event diagnostic (2026-10-18)

Recovered r2 entry/pressure run ksq1 fits but does not trigger first appearance. Fresh actual source area7/movie rig kev1 uses emlog39: live hp10,000/type1/be03002077 moves and changes routines, with no id39 NMRS draw rows. It is an invisible-enemy FAIL even though drawn CAST/TEX/LEON checks pass. Existing1,423,712B/154clip archive hot67,712B thrashes432+ misses/429+evictions (repeated4/48/50 and4/6/83, one145,657us wait); texture evictions67/retry1. This event window is not a residency or play pass. Hotset/peak-budget audit is next; boss18 owns model visibility.
