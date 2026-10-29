# Build 29 — whole-game fallback sweep and offline asset scan

## Answers (owner): 2026-10-29 EFM and line source landings

DONE: EFM `47679acd4824b24b64978ce0252f056a0fa7e2ae` clean no-ff landed `ce38b99649bb61631fe4d4f622313ddc16be7c0f`, then line `00ecd54840c1ffb1dde595618a77a567e8bf2492` clean no-ff landed `6e1e5a0638d10bd7a59670a61e2f4b1f9a536e02`, both default0. Source/peer review and existing normal/sanitizer/extracted-host OFF gates passed. Each local pinned-SDK absent/explicit0/ON full release links with existing empty missing.txt; each absent/zero programme, all15 overlays and every allocated section metadata/payload match its bound prior integration. Actual527 C++ commands per arm were inspected: EFM ON global to game/platform/room consumers, line ON only atari.cpp. No source conflict was hand-resolved. Fresh-base origin-only push/readback passed after these gates.

Combined ALLON K30 adds both controls using current FX_SCAN1/list1/workAt1 and LINE_WALK1/piece1/yrow1/FP-contract-off. QA_LINK1, compile/missing/global542 EFM/ABI macros and exact line consumer, loader/standard lints, ZIP, staged checksums and actual final program/all15 overlays match SDK. Track03 `08b14816728d15e9b68f16e86199604bc286ef41db3eef15eade58d39649c429`. PREPARED only; no current EFM/line gameplay/STRICT/heap/stack/cost/hardware acceptance or SD/recipe promotion.

OPEN SOURCE/TEST FOLLOW-ONS, cloud-owned: EFM fixtures do not exercise constructor-time reentry, nested index rebuild before outer continuation, or >65535 slot refusal. Preserve saturating token/serial source fallback and exact i+1 continuation. Line valid profiles have no demonstrated traversal blocker, but harden line_resume29.mk to one literal0/1 and WALK in1/2: current multiword/pattern values can silently selectOFF and WALK3 is admitted. Add an explicit equal-nearest tie oracle. Actual LINE_LEAF/TAIL target assembly and live results remain local gates; ON no longer increments ELC_W_LEAVES, so do not use it as matched cost evidence. Do not weaken current source guards or claim unsupported profiles passed.

COLLISION runtime follow-up on pinned prior source39ed524a, CACHE2 controls0/1: same1648 external asset files, same stock room fixture and source/QA name, exact16 SDK payloads per image/base. Both60s no-key/no-state runs reached r101. Observed emitted control row hit8182/miss10/mismatch0; enabled rows hit8182/miss10/mismatch0 and hit16374/miss10/mismatch0. Neither reported dirty overflow in these samples. Raw logs contain4138/3702 NUL bytes and are retained unmodified. This is scoped reference-comparison evidence at reported cutpoints, not whole-window absence of mismatch, route/STRICT, speed or memory-headroom acceptance. Source counters/sample counts are not a performance comparison. No identical retry or longer run is justified by this result alone.


## 2026-10-29 EF03: consumed strip/cloth result slice

**DONE (IMPLEMENTED + TARGET VALIDATED; default 0):** `NATIVE_DRAW_OUTCOMES=1`
(default 0; requires `FX_STRIP21=1`) carries explicit submitted, queued,
culled, policy-skip, unsupported-before-publication, refused and partial-abort
outcomes through the existing quad/mesh FIFO and actual source strip/cloth
adapters. The old `int` symbols retain their ABI. Their routing/count values
remain insufficient as coverage proof; new consumers use `NativeDrawResult`.

The source defects were concrete: the strip adapter returned handled after an
ignored quad refusal, and cloth ignored every band result while its mesh emitter
lost clipped-cell failures. A producer now stops on its first failure. An earlier
accepted FIFO node or submitted packet turns that failure into partial-abort;
a whole-producer fallback is forbidden after that publication. Every accepted
mesh row pins its texture even when a later row fails. Queue sizes, allocation
services, FIFO packet layout, pass order and source simulation remain unchanged.
Queued means copied ownership accepted by the existing FIFO, not a promise of
presentation after a later frame abort. Unsupported/refused before publication
permit existing source routing; the Dreamcast GX geometry sink still does not
provide visual coverage. This slice does not restore those unsupported families.

Host checks (actual production include and extracted source functions):

```bash
python3 -B port/dreamcast/tests/test_native_draw_outcomes.py
python3 -B port/dreamcast/tests/test_effect_strip21.py
```

The new suite passes 5 tests: strict Make control/three-consumer propagation;
parent/absent/zero native-emitter object identity; all seven outcomes and actual
header/vertex/FIFO order; source `EspStrip_draw_poly` refusal and no duplicate
fallback after publication; actual cloth band aggregation and first-error stop.
ASan/UBSan packet fixtures cover texture/cap/queue refusal, selection failure,
post-send abort, intact-row and near-clipped-cell partial publication, texture
pins, and the existing r200-tail selection branch. The existing strip suite
passes 4 tests, retaining its 261,120 source UV/order comparisons. Its fixture
needed two current-production compatibility definitions (queue margin and the
existing GC-asset send wrapper); renderer behavior was not changed for that fix.

The broader existing `test_fx_r200_entry_cap.py` passed its first 50 cases /
128,729 assertions, then its absent-arm scaffold failed to compile because it
omits the existing unrelated `DFA26_HIT` macro. That is not a passing full-suite
receipt and no production failure is inferred from that stale fixture.

**Target checks DONE (2026-10-29):** runtime source commit
`cd57337c9747f8182487c625ae0895dd39315f80`. The Make-derived SH-4 gate compiled
`native_ui`, `esp_sub` and `cloth` in parent/absent/zero/ON arms; all six disabled
objects are byte-identical to base `9ee386e3`. The enabled three objects compile.
The selected public profile, flags, compiler/KOS/SH4ZAM hashes and source hashes
are recorded separately from the full release recipe in the
[compact target receipt](../../../tools/cloud/build29/receipts/native-draw-outcomes-target.json).

The actual current release recipe (`rr/recipe.conf` SHA256
`66940fea7531fd3a402dc8fc6f779d7861801c0cd39a4c91be31f7f0871816c0`)
built in OFF0 and ON arms, each real rc=0 in 41 seconds with a nonempty ELF and
an existing empty `missing.txt`. The shared fresh base9ee release control was
reused, not rebuilt. After normalizing only each exact output/checkout root and
whitespace, the base/OFF resolved fields differ solely by the new absent-to-0
knob; OFF/ON differ solely by 0-to-1. `CLOTH_NATIVE=1` is already in that recipe.

- OFF ELF SHA256: `6aa2fc222fbf1dc61d934205e489b36e4edf08ebca7c8672f65e1bf32e9b2138`.
- ON ELF SHA256: `3fdea8e3e6ac7d754fffaffe227139f309eb21827e1bd176c294e90d4989622e`.
- OFF raw programme: 3,372,036 bytes, SHA256
  `fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1`,
  identical to base; all 15 overlays and all 11 allocated ELF sections
  (metadata and payload) also match. Whole debug ELFs differ.
- `_end`: OFF `8c4170d4`, ON `8c417674` (+1,440 bytes). Selected public-profile
  local frames include mesh 7,200 -> 7,260 bytes and `clothTrans` 3,600 -> 3,664;
  these are not whole-stack bounds, runtime headroom or hardware cost.

The local complete receipts are under
`/root/probe/engine-ef03-20261029-target-r3/`: `objects/result.json`,
`off-final.json`, and `resolved-normalized.json`. Full arms are
`/root/probe/lanes/route/out-ef03w3offrP` and `out-ef03w3onrP`. Their logs retain
actual commands and definitions. Setup attempts r1/r2 stopped before compilation
(path spelling and archive/profile directory collision); they are not runtime
failures. The target helper's defaults were corrected before the passing r3 run.

Reproduce the public three-TU gate while holding the coordinator's SDK slot:

```bash
python3 -B port/dreamcast/tools/cloud/build29/native_draw_outcomes_target.py \
  --output "$EF03_FRESH_TARGET_OUT"
```

The helper uses base `9ee386e3ef8d46bcd7ae8586d2064cd1ae22864e`, the
installed SH-4 compiler and `/root/work/kos-re4dc-d367` at `804b3195`. It needs
an initialized pinned SH4ZAM submodule and a fresh output directory. Reproduce
an enabled full recipe arm with actual existing private build inputs:

```bash
set -euo pipefail
source <(tr -d '\r' < port/dreamcast/tools/d367/rr/recipe.conf)
T="$PWD"
K="$EF03_FRESH_BUILD_LOGS"
export T K
export ROUTE_PROGRAMS_DIR="$EF03_FRESH_PROGRAMS_DIR" ROUTE_PROGRAMS_JSON=''
test ! -e "/root/probe/lanes/route/out-${EF03_LABEL}rP"
LP="$EF03_LABEL" CH2="$CH2 NATIVE_DRAW_OUTCOMES=1" \
  bash port/dreamcast/tools/d367/ch2/ch2-build.sh rP
O="/root/probe/lanes/route/out-${EF03_LABEL}rP"
test -s "$O/re4dc-game.elf"
test -f "$O/missing.txt"
test ! -s "$O/missing.txt"
```

`EF03_FRESH_TARGET_OUT`, `EF03_FRESH_BUILD_LOGS`, `EF03_FRESH_PROGRAMS_DIR` and
`EF03_LABEL` must name new lane-owned outputs/label. OFF uses the identical
recipe with `NATIVE_DRAW_OUTCOMES=0`. Build34's existing `upload_compare.py`
compares those full OFF bytes to the bound baseline; retain the compact receipt's
exact distinction between whole debug ELF and allocated executable identity.

**NEXT:** coordinator review/integration default off, then EF03 family-wide
native coverage and GX attribution as the next bounded slice. EF11 wide sheets /
`pTobjA` materials and EF12 effect-family restoration remain open. No universal
GX interpreter or new renderer was added.

**BLOCKED (scoped acceptance only):** source-clock/material/look/lifecycle and
physical-console acceptance need actual supported game inputs and the existing
owner/human gates. No Flycast or hardware run, gameplay/look acceptance, speed
win, family-coverage closure, default promotion or publication is claimed.
The SDK slot is released with no live job.

Branch: `codex/fallback-scan29-20261028`.

Integration base: `5f104e301f328c56a07ce9f57e3fb94d758d4999` on
`origin/t15/int`. The final fetch and rebase confirmed this integration tip;
the complete composed configuration was rebuilt afterward. Its 17 complete
preprocessed sources and objects match the full qualification run, as recorded
in [mergeability.json](../../../tools/cloud/build29/receipts/mergeability.json).
This build has one commit, targets `origin` only, and leaves the queue and
release defaults to Claude. It introduces no production assembly or linker changes.

## What is delivered

1. A [whole-source sweep](build-29-sweep.md), covering skinning and motion,
   cloth, collision, effects, texture residency/refusals, gameplay disc reads,
   sound streaming, GX/legacy dispatch, frame/matrix caches, sorting and
   adjacent gameplay caches. Its 72 reviewed split groups have current source
   locations, resolved Make values, triggers, structural MODELLED work/traffic,
   chapter reachability and counter/scanner coverage. The accompanying corpus
   manifest and unclassified candidates make the limits inspectable; a
   keyword search is not a claim that every semantic fallback is proven.
2. The [offline scanner](../../../tools/d367/fallback_scan/README.md), with
   ranked room/model reports, part/material/meshlet rows, `barn.tsv`, native
   ESL spawn inventory, source hashes and a hash-bound context template.
   It reads the converted disc formats and owning format validators rather
   than treating a private JSON inventory as the asset input.
3. Two independent, default-off [conversion options](../../../tools/d367/fallback_scan/CONVERSIONS.md),
   plus extraction and same-size package grafting. They reuse the existing
   FE/v3 meshlet/RGB565/BakeBlock format for ordinary source ModelData.
4. Default-off runtime diagnostics, bounded actor attribution and an adapter
   for those explicitly converted source streams. Existing DFA rows and the
   Build 28 immutable multipart link carry the complete diagnostic snapshot.
5. A focused [r103 barn-exit world audit](build-29-barn-exit.md), covering the
   newly added outdoor-view target, doorway/cell selection, live camera and
   draw distance, clip-counter units and per-piece setup. It ranks five
   default-off proposals and gives exact owner capture commands. These world
   switches are proposals, not implemented Make assignments.

The final integration update enables `ACTOR_LIGHT_FAST_ONLY=1` in the current
recipe. Build 25 therefore owns lighting and bypasses the old probe/exact paths
and this build's bake adapter. The scanner honors that policy. The historical
barn exact-light observations must be reproduced with their original image's
recipe; the FAST_ONLY=0 conversion experiment below is a separate variant,
not an incremental speedup over the current FAST_ONLY=1 release.

For the second target, the current public configuration supplies no doorway
occlusion in r103. The existing compiled interior cell is r100-only; generic
PCL2 and PVS need qualified room data. Enabling them also makes surviving parts
decline fast chunk selection, so a useful portal/table proposal must measure
survivor setup as well as geometry rejected. The appendix distinguishes this
source finding from the owner's still-pending world timing attribution.

The r103 figures in the queue motivate this work; they are not measurements
made here. There are no private game assets or console in this environment.
**The offending Ganado/tool/hay/prop source keys remain an owner result.**
The scanner and new attribution rows provide the source binding needed to
identify them without guessing from an enemy ID or a package's presence.

## Switches, ownership and changed output

| Switch | Default | Requirement and effect |
|---|---:|---|
| `FALLBACK_AUDIT29` | 0 | Requires `QA_MENU=1 DRAW_FALLBACK_AUDIT=1`. Adds 33 non-draw reason bins and up to 32 actor attribution rows. With `QA_LINK=1`, also requires `QA_LINK_REVIEW28=1`. |
| `FALLBACK_SCAN29` | 0 | Requires `NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 MODEL_STREAM_FIX=1 NATIVE_ACTOR_PRELIT=1`. Admits only the new validated offline tag and compatible live material/light state. |
| `--fold-light-scale=1` | 0 | Selects captured constant-channel, clamp-diffuse scale declines and bakes the captured material/lighting response into RGB565 records. |
| `--bake-probe-decline=1` | 0 | Selects explicitly established probe declines and bakes the captured pose/light response. Probe decline alone does not prove the generic exact-light path was selected. |

With both data flags absent or zero, the converter copies any input byte for
byte without parsing or normalizing it. Enabled conversion keeps the source
positions, normals, bones, weights, UV/corner indices, ordered triangles,
degenerates, material bytes and every byte outside the selected original
stream allocations. A candidate that cannot fit is refused. Package size and
resident bytes do not grow. The conversion receipt records the context hash;
grafting validates package/member/converted-output hashes and checks unchanged
NTR/ESQ offsets, CRCs, extents and referenced bytes. It does not reread the
separate capture context.

The changed output is **lighting RGB**: RGB565 quantization and a spatial
pattern baked from the captured pose/directions/attenuation approximation.
Current animation still moves the original geometry. A per-part RGB energy
ratio follows current ambient/material/TEV and selected-light colour, including
flashes, but cannot reproduce new directions, distance attenuation, pose-based
shading or saturation recovery. Current constant alpha stays exact. An
admitted bake also supersedes the crowd/rigid flat-colour approximation.

The converter refuses morphs, animated vertex palettes/material policy,
nonopaque blends, per-vertex alpha, mask/specular/bump material flags,
invalid/missing capture state and special Leon/headroom markers. The live
adapter also refuses incompatible state and keeps its offline palette
immutable while the existing evaluator draws that state. These explicit
refusals are required behavior, not removed fallbacks. With
`ACTOR_LIGHT_FAST_ONLY=1`, Build 25 retains ownership; paired production-renderer
fixtures produce identical output with the new runtime knob off/on.

NMR/compiled casts/coarse actor certificates and GC-ASSET source proofs have
different owners. This converter deliberately does not rewrite or recertify
their input facts. Its useful first deployment is a verified ordinary
source-path PS2 prop/actor member. Two total-frame tradeoffs remain: preencoded
FE parts cannot join the existing `STATIC_OBJ_BATCH` merged-GX batch, and this
step emits level-zero original geometry without new LODs or cones. Reduced
lighting work can be offset by setup, submission or geometry work; measure the
actual replacement before enabling it.

## Runtime evidence and denominators

FA29 counters use the existing game tick and draw decision. IRQ save/restore
serializes game, disc and sound-thread updates. A new room resets totals;
pause stops collection; the last completed tick that attempted drawing is
retained across skipped ticks. Saturation and work outside an active tick are
explicit. `FA29T` is a room total including skipped/async work; `FA29D` belongs
to the last completed drawn tick. Bytes are requested/retry bytes unless the
row says otherwise, not completed unique payload.

`F29A`, `F29P` and `F29L` add source model kind/ID/type, model-info ordinal,
validated part offset, source texture selector, counts, material flags and
latest material/ambient/TEV/control/mask values. The internal lookup key also
uses the source model serial to separate recycled addresses. `verts=` counts
actual vertices processed by the exact evaluator; `calls=` and `exact=` count setups. Path
codes are 0 probe, 1 generic fast/baked-capable setup, 2 exact setup and
3 constant setup. Successful nonconstant probes are omitted to reserve the
bounded table for the relevant declines. Overflow is reported as `spill=`;
it is not silently merged into a different owner.

These actor totals can include the current partial tick when QA pauses; the
core totals are sealed at the preceding end-tick. Never divide actor counts
by core `draws` or equate them with last-draw DFA. `changes=0` covers only the
emitted fields; it says nothing about pose, basis or light vectors. Control
bit 24 records the Leon source marker and bit 25 the headroom marker. Neither
these rows nor a BIN provides the complete pose/light capture required for a
bake. A verified owner must supply that stronger context separately.

The dedicated 24,576-byte snapshot uses an independent new-knob block; old
DFA/DSA conditions are not widened. Full production formatting, pagination and
both review28 T/D senders are tested under a 2,400-byte queue cap and repeated
enqueue refusals. The conservative maximum composition, including OCC,
uses 24,279 bytes (296 bytes plus the terminating NUL remain). An actual
maximum-field `snap_diag` composition uses 24,126 bytes. The old non-review D
sender is not a supported FA29 link configuration. The old T test is only a
component regression.

## Validation

| Gate | Result |
|---|---|
| Complete preprocessing and target objects, knobs absent/explicit zero | **192 byte-identical comparisons**, 16 existing TUs × 3 old-knob profiles × 2 new-knob controls × 2 artifact types |
| Enabled target configurations | **5 PASS**, including standalone audit, audit+link, scan knob, both knobs+link, and composed DFA/DSA/XLU/FAST_ONLY/clip features; 17 TUs when the core is enabled |
| Invalid knob/prerequisite assignments | **13 rejected**; release defaults remain zero and omit the diagnostic core object |
| Integrated host suite | **54 tests PASS**: 38 scanner, 11 converter, 4 package and 1 complete production-renderer method with seven configurations |
| Actual production renderer and native-model FE dispatcher | Seven renderer configurations pass normally and under ASan/UBSan; existing full native-model dispatch regression also passes under ASan/UBSan |
| Counter core / actor attribution / QA composition | Normal and ASan/UBSan PASS; 160,000 concurrent core updates, saturation, lifecycle/serial/pause boundaries, complete pagination and bounded T/D transport |
| Cost fixtures | 14 core, 8 actor and 6 lighting cases PASS on compiled SH-4 instructions |

The [target receipt](../../../tools/cloud/build29/receipts/target-controls.json),
[integrated host receipt](../../../tools/cloud/build29/receipts/host-suite.json),
[conversion proof](../../../tools/d367/fallback_scan/conversion-validation.json),
[actor proof](../../../tools/cloud/build29/receipts/actor-attribution.json) and
[diagnostic receipts](../../../tools/d367/fallback_scan/AUDIT29.md) retain
source hashes and reproduction details. LeakSanitizer is disabled because
this environment prevents its `/proc` task inspection; address and undefined-
behavior checks remain enabled. The old source-registry writer emits its
existing file-closure ResourceWarning in synthetic tests; no test fails.

The target gate archives the integration commit independently, derives real
per-TU flags/headers from Make, and compares complete preprocessed sources and
complete SH-4 objects. Debug records and preprocessor line markers are disabled
consistently; there is no body extraction, byte rewriting, source overlay or
post-build normalization. New blocks preserve original logical `__LINE__`
values used by recovered allocation diagnostics and KOS scoped-lock names.

The toolchain is GCC 15.2.0 / binutils 2.45.1, KOS
`804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`, SH4ZAM
`33fa4850cacb30dd0ad35485ef035526ec4ce782`; executable hashes are verified.
The public target profiles use `NMR_POOL_LOD=0` because private generated LOD
inputs are unavailable, identically on both sides. This is not a full private
ELF/overlay/disc identity proof. Enabled partial links resolve every new hook;
ordinary game/KOS references remain outside that link's scope.
All five profiles inherit the current recipe's FAST_ONLY=1 policy. The
FAST_ONLY=0 adapter is separately compiled and linked in the real production-TU
lighting-cost fixture and exercised by the complete host-renderer matrix.

## MODELLED costs and traffic

All cycle figures execute compiled production routines on bounded synthetic
inputs and use the existing SH-4 scheduling model. Warm I means perfect
I-cache; cold I means one initially cold 8 KiB I-cache with the synthetic ELF
layout. Both assume perfect D-cache. Loads/stores are executed architectural
accesses and lines are distinct 32-byte addresses, including stack/literals;
they are not console misses, DRAM transactions or measured milliseconds.

| Piece | Warm I cycles | Cold I cycles | Loads | Stores | 32 B lines | Observed stack B |
|---|---:|---:|---:|---:|---:|---:|
| FA29 active hit | 101 | 177 | 21 | 7 | 7 | 20 |
| FA29 same-room begin | 163 | 258 | 20 | 46 | 10 | 28 |
| FA29 drawn-tick seal | 271 | 388 | 98 | 83 | 23 | 12 |
| Actor setup, first of 32 keys | 283 | 604 | 82 | 25 | 21 | 72 |
| Actor setup, last of 32 keys | 717 | 1,038 | 206 | 25 | 36 | 72 |
| Add 128 exact vertices, last of 32 keys | 522 | 606 | 151 | 5 | 26 | 16 |
| New actor row, unknown-owner callback | 365 | 760 | 107 | 56 | 26 | 72 |
| Unconverted exact-light setup | 936 | 1,471 | 210 | 312 | 55 | 952 |
| Unconverted exact pass, 128 records | 70,541 | 71,353 | 15,199 | 2,775 | 259 | 920 |
| Tagged bake setup / live gain | 1,374 | 1,930 | 229 | 99 | 38 | 724 |
| Baked copy pass, 128 records | 4,590 | 5,051 | 283 | 215 | 195 | 328 |
| Baked live-flash gain pass, 128 records | 9,069 | 9,527 | 671 | 215 | 195 | 328 |

The [core receipt](../../../tools/d367/fallback_scan/receipts/counter-cost29.json)
contains 14 cases, the [actor receipt](../../../tools/cloud/build29/receipts/actor-cost.json)
eight key/lifecycle cases, and the [lighting receipt](../../../tools/cloud/build29/receipts/light-cost.json)
six 16/128-record cases. Actor attribution uses 2,828 B of BSS. Fresh valid
model-info/part-table traversal is unpriced; the fresh-row fixture deliberately
executes the real unknown-owner return. Later rows avoid that traversal.

**Whole frame, MODELLED:** assume 200 MHz, 120 copies of the 128-record lighting
fixture (15,360 records) and a fixed 30 ms of all omitted work. Then
`30 + 120 × (setup + pass) / 200000` gives **72.8862 ms** for the
unconverted exact path, **33.5784 ms** for baked copy and
**36.2658 ms** for live RGB scaling. This is a synthetic
sensitivity calculation, not the measured barn distribution or a console
prediction. Cold-cache phases are separate experiments and cannot be summed
as a frame. Static-batch/LOD tradeoffs and real D-cache behavior are omitted.
This lighting fixture explicitly sets `ACTOR_LIGHT_FAST_ONLY=0`; it does not
estimate a gain over the current release's FAST_ONLY=1 path.

Separately, an assumed 1,000 active FA29 hits plus one begin/seal adds
0.50717 ms, making **30.50717 ms MODELLED** with the same 30 ms
background. Adding 120 last-of-32 attribution setup/count pairs adds another
0.74340 ms, for **31.25057 ms MODELLED**. These
observer frequencies are assumptions, not room measurements. Diagnostics
therefore have a cost and must be held constant in a timing comparison.
The refreshed actor fixture uses the current FAST_ONLY=1 recipe and directly
invokes the independent vertex-accounting helper. Its assumed count frequency
does not establish exact-light activity under that recipe.

The lighting fixture uses 128 stored records, a scaled material, one lamp at
unit distance (the interpreter's qualified reciprocal domain), and unchanged
geometry/alpha. Both arms run the same current compiled TU; the unconverted
arm retains the ordinary exact path. The baked pass reads no source positions
or normals for lighting. The brighter-light case exercises live RGB gain.
Unexecuted mutable-bake/AVK dependencies are bound to fail-closed addresses:
entering one aborts the model, rather than substituting a successful stub.
Real model-kind discovery is separately excluded by the fixture and disclosed
in its receipt. Deformation, clipping, textures, submission, device waits,
interrupt delivery and D-cache misses are unpriced.

Complete selected production-TU sizes before final link/garbage collection,
compared with the same old-knob profile on the integration base:

| New configuration | Executable delta | Allocated delta | BSS delta |
|---|---:|---:|---:|
| FA29 over DFA, link off | +3,988 B | +26,406 B | +20,836 B |
| SCAN29 only, current FAST_ONLY policy | +112 B | +112 B | +0 B |
| Both knobs over composed DFA/DSA/XLU/FAST_ONLY/link/clip features | +4,088 B | +33,674 B | +28,004 B |

Allocated bytes include code, rodata, data and BSS; do not add BSS again.
The [production metrics](../../../tools/cloud/build29/receipts/production-metrics.json)
retain per-TU deltas and changed local frames. These are current-recipe
FAST_ONLY=1 sizes, not the FAST_ONLY=0 conversion experiment. With SCAN29,
`re4dc_actor_submit_chunks` grows 592 → 624 B; in the fully composed profile,
`re4dc_actor_submit` changes 1,016 → 1,008 B. The largest actor TU local frame
stays 2,388 B. The attribution note has a 72 B local frame; the real source
identity helper is 8 B. The
counter core's largest local frame is 60 B. QA's maximum local frame stays
2,280 B without link / 3,092 B in the composed link profile. The extra snapshot
and attribution tables are static storage, not new per-frame allocations.

The offline scanner/converter adds zero console work when it is not used.
Absent/zero runtime knobs have zero target-object, code, data and stack delta
in the qualified profiles. Compiler local frames and fixture-observed stack
depths are different measurements; neither proves whole-game/IRQ margins.

## Exact owner workflow on private data

Use new output directories outside the input tree. The following variables
refer to the owner's existing composed converted disc, Build-Assets and pinned
toolchain environment; none is supplied by this repository.

```sh
SCAN=port/dreamcast/tools/d367/fallback_scan
PRIVATE=/absolute/private/build29
DISC=/absolute/private/composed-disc-tree
BUILD_ASSETS=/absolute/private/re4dc-assets
IMAGE_RECIPE=/absolute/private/exact-source-image/release-knobs.txt
mkdir -p "$PRIVATE"

# Pin the source image's recipe; build-public otherwise defaults to test24.
RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$PRIVATE/audit-build" \
  bash port/dreamcast/build-public.sh \
  DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 BENCHMARK=0 PMC_ROW=0 \
  DRAW_FALLBACK_AUDIT=1 FALLBACK_AUDIT29=1 FALLBACK_SCAN29=0 \
  QA_LINK=1 QA_LINK_REVIEW28=1

python3 -B "$SCAN/scan.py" "$DISC" --out "$PRIVATE/scan-unbound" \
  --knobs "$PRIVATE/audit-build/resolved-knobs.txt"

python3 -B "$SCAN/scan.py" "$DISC" --rooms r103 \
  --out "$PRIVATE/barn-unbound" \
  --knobs "$PRIVATE/audit-build/resolved-knobs.txt" --strict
```

Add repeatable `--input` arguments for the exact compiled cast headers and
standalone replacement packages used in that image. Supply the actual chapter
route with `--rooms`/`--room-list`; the default r100–r11f selection is not a
claim that every route asset lives in those rooms. `--strict` exit 1 still
writes an incomplete report: resolve its rejected/missing inputs instead of
treating them as zero work. Do not substitute the public recipe's private-off
character settings for the console image's resolved knobs.
For the earlier exact-light observation, pin the actual earlier source-image
recipe. Under the current FAST_ONLY=1 recipe, zero probe/exact rows are expected
and cannot disprove the earlier observation. Use the separate world-observer
commands in [the barn-exit appendix](build-29-barn-exit.md) for the ALL ON
outdoor/stalls comparison, preserving its current lighting policy.

Stage the observer through the existing disc pipeline and capture the same
r103 viewpoint, animation and nearby actors. Run the already paired review28
Pi service and PC client; for the owner's configured DreamPi:

```sh
python3 port/dreamcast/tools/qalink/qalink.py \
  --pi "$QALINK_PI" --review28 --out "$PRIVATE/barn-capture" capture start barn29
python3 port/dreamcast/tools/qalink/qalink.py \
  --pi "$QALINK_PI" --review28 --out "$PRIVATE/barn-capture" send DIAG
python3 port/dreamcast/tools/qalink/qalink.py \
  --pi "$QALINK_PI" --review28 --out "$PRIVATE/barn-capture" capture stop barn29
```

Check multipart completion, room/tick/image identity, overflow and table spill.
Bind exact source/member/model keys using the template, part offsets, source
texture bytes, geometry counts, owner/placement and runtime kind/ID. Bind the
Ganado, attachment, hay and props separately; an ID alone is insufficient.
Keep missing basis/light/pose facts unknown. A changed or incomplete context
cannot authorize baking. After producing the owner-verified scanner context:

```sh
python3 -B "$SCAN/scan.py" "$DISC" --rooms r103 \
  --out "$PRIVATE/barn-bound" \
  --knobs "$PRIVATE/audit-build/resolved-knobs.txt" \
  --context "$PRIVATE/barn-context.json" --strict
```

Read `barn.tsv` and `by-model.tsv` together with F29P exact vertices, preserving
their different denominators. Source probe decline can still take generic
fast lighting. A tag plus enabled knob is a conditional candidate, because
live-state admission can refuse it. This is how the private run identifies
which source models actually account for probe/scale/exact work.

For a verified ordinary source-model member, list/extract and capture the full
bake context before conversion. Use the exact key emitted by `package.py`:

```sh
SOURCE=/absolute/private/composed-disc-tree/st1/r103.dar
python3 -B "$SCAN/package.py" list "$SOURCE" > "$PRIVATE/members.json"
MEMBER_KEY='REPLACE_WITH_EXACT_KEY_FROM_MEMBERS'
python3 -B "$SCAN/package.py" extract "$SOURCE" "$PRIVATE/source.bin" \
  --key "$MEMBER_KEY" --receipt "$PRIVATE/member.json"

python3 -B "$SCAN/convert.py" "$PRIVATE/source.bin" "$PRIVATE/folded.bin" \
  --context "$PRIVATE/bake-context.json" --fold-light-scale=1 \
  --receipt "$PRIVATE/conversion.json"
python3 -B "$SCAN/package.py" graft "$SOURCE" "$PRIVATE/folded.bin" \
  "$PRIVATE/r103-candidate.dar" --member-receipt "$PRIVATE/member.json" \
  --conversion-receipt "$PRIVATE/conversion.json" --receipt "$PRIVATE/graft.json"
```

Use separate new outputs with `--bake-probe-decline=1` to isolate the second
option, then both flags if warranted. The [capture schema and refusal list](../../../tools/d367/fallback_scan/CONVERSIONS.md)
are part of the command contract. No synthetic example values should be
filled into missing private light or pose fields.

Stage the grafted package at its original relative disc path, scan that new
disc tree with a newly hash-bound context, and build its matching runtime:

```sh
RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$PRIVATE/candidate-build" \
  bash port/dreamcast/build-public.sh \
  DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 BENCHMARK=0 PMC_ROW=0 \
  DRAW_FALLBACK_AUDIT=1 FALLBACK_AUDIT29=1 FALLBACK_SCAN29=1 \
  NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 MODEL_STREAM_FIX=1 NATIVE_ACTOR_PRELIT=1 \
  ACTOR_LIGHT_FAST_ONLY=0 QA_LINK=1 QA_LINK_REVIEW28=1
```

Keep the original package and run the same recipe with `FALLBACK_SCAN29=0`
for the unconverted control. Compare the independently enabled data flags and
the existing FAST_ONLY policy. Include actual total frame time, exact-light
vertices, setup/batch/LOD counts, textures, moving views/animation/flashes,
STRICT gameplay equivalence, GC-ASSET coverage, heap4/KOS/VRAM and stack
margins, room transitions and the s30 movie return. Run full private image
identity with both new knobs absent/zero. The cloud gates do not replace those
acceptance checks and no default is changed here.

## Reproduce the public gates

The [target control script](../../../tools/cloud/build29/build_controls.py)
accepts the pinned compiler/KOS/SH4ZAM/toolchain receipt paths explicitly:

```sh
python3 -B port/dreamcast/tools/cloud/build29/build_controls.py \
  --output /tmp/build29-target-new \
  --baseline 5f104e301f328c56a07ce9f57e3fb94d758d4999 \
  --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT" \
  --toolchain-receipt "$TOOLCHAIN_RECEIPT"
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_*.py' -v
python3 -B port/dreamcast/tools/d367/fallback_scan/test_audit29.py --sanitize
python3 -B port/dreamcast/tools/d367/fallback_scan/test_qa29.py \
  --sanitize --output /tmp/build29-qa-new
python3 -B port/dreamcast/tools/cloud/build29/actor_attribution_host.py \
  --sanitize --output /tmp/build29-actor-host-new
```

`actor_cost.py`, `light_cost.py` and `counter_cost29.py` use `--output`,
`--sh4-cxx`, `--kos-root` and `--sdk-root`. Their receipts include input/trace
hashes, warm/cold costs, data traffic and stated fixture exclusions.
`compact_receipts.py` rejects stale source hashes before retaining reviewable
target, cost and production-size evidence. The sweep appendix documents
reproduction of its recipe/corpus manifest. All fixtures are synthetic; no
game bytes, private contexts or generated game packages belong in Git.


## Cloud progress 2026-10-29: resumable ordered line traversal (review 9.3)

**DONE:** source implementation on `codex/line-resume-20261029`, delivery base
`39ed524a3b0a4727148aaa5a45eaaea4d211cede`. The cloud writer owns only
`src/game/atari.cpp`, `src/game/line_resume29.h`, the dedicated
`game/line_resume29.mk` and Build29 line fixtures. The coordinator included
the fragment in the shared Makefile after the local EF16 delivery landed.

`GAME_LINE_RESUME=1` uses a bounded cursor to deliver overlapping leaves in
source order directly to the existing polygon consumer. It removes the
64-leaf gather limit and the whole-chain restart at leaf65. Sixteen pending
sibling continuations fit in the cursor. At the depth boundary, the cursor
hands off only the untouched child chain, with the current polygon bitset,
hit and normal state, then resumes its siblings. A published prefix is never
replayed. No SAT representation, polygon kernel or assembly is replaced.

PIECE mode retains the original contract-off x/z operation order and rejects
empty pieces before the y rows/full transforms and polygon-bit clear.
YROW and current-end reuse remain after admission. The feature defaults0,
requires `GAME_LINE_WALK=1/2`, and only changes `atari.o` definitions.

**Validation performed:** the frozen production-consumer fixture passed:

```sh
python3 -B port/dreamcast/tools/cloud/build29/test_line_resume29.py
git diff --check
```

There are44 compared cases in each of eight normal/ASan+UBSan configurations:
WALK/PF1 and2; PIECE/YROW0,1 and2. Cases cover64/65/129/150 leaves, zero and
multiple hits, repeated polygon indices, transformed moving pieces and
fractional matrices, wall/floor selection, and depths15/16/17/18/33 after an
already processed prefix. Comparisons include return value, hit/end/winning
piece/normal, polygon bitset and ordered polygon visits. The ON arm asserts
one overlap test per traversed block at the tested continuation boundaries.

The fixture extracts production `hitCheck2`, overlap and block/polygon
consumers. Host shims stand in for the SH-4 gather ABI and polygon intersection
results; this establishes consumer order/state parity, not target instruction
or complete collision-kernel validation. In mode2 the OFF reference arm
actually runs LNW/LWP/LNP comparisons and asserts zero mismatches. ON bypasses
those gather wrappers; their inactive counters are not counted as evidence.
YROW comparison remains active in both arms. LeakSanitizer alone is disabled
for the managed executor's thread-walk limitation; ASan/UBSan remain active.

The same runner proves original-source, absent and explicit-zero preprocessing
and host object bytes identical in both tested PIECE profiles. Its original
`e6939459` atari.cpp blob is unchanged at the delivery base. Actual Make
dry-runs select the new definition only for `atari.o`; absent/zero compile
commands match, and invalid control/dependency combinations are refused.

**Storage/cost:** no retained allocation or global cursor is added. Nominal
32-bit cursor size is108 bytes, replacing a256-byte leaf-pointer array at
these call sites. Deep child handoffs can add nested frames, so this is not a
whole-stack bound. An extracted x86-64 `-O2 -ffp-contract=off` proxy measured
text7,886->9,094 bytes, BSS8,232 unchanged, `hitCheck2` local frame832->416,
`blkPolyLineCk`736->272 and the new runner96 bytes. These include host ABI
and fixture effects; no SH-4 size, stack, warm/cold cycles, data-line traffic
or whole-frame **MODELLED** improvement is asserted.

**NEXT / exact local commands:** the public SDK is unavailable in cloud.
Use the existing pinned SDK (KOS804b3195 plus repository patches,
GCC15.2.0/binutils2.45.1/newlib4.6.0.20260123 and SH4ZAM33fa4850) and the
owner's existing private recipe inputs. Supply a fresh label/log/programme
directory and the retained ordinary-release output bound to delivery base
39ed524a (including the qualified default-off collision slice):

```bash
set -euo pipefail
: "${LINE29_LABEL:?fresh lane label}"
: "${LINE29_LOGS:?fresh log directory}"
: "${LINE29_PROGRAMS:?fresh programme directory}"
: "${LINE29_BASE_OUTPUT:?bound current-base ordinary-release output}"
source <(tr -d '\r' < port/dreamcast/tools/d367/rr/recipe.conf)
export T="$PWD" K="$LINE29_LOGS"
export ROUTE_PROGRAMS_DIR="$LINE29_PROGRAMS" ROUTE_PROGRAMS_JSON=''
test ! -e "/root/probe/lanes/route/out-${LINE29_LABEL}offrP"
LP="${LINE29_LABEL}off" CH2="$CH2 GAME_LINE_RESUME=0" \
  bash port/dreamcast/tools/d367/ch2/ch2-build.sh rP
test ! -e "/root/probe/lanes/route/out-${LINE29_LABEL}onrP"
LP="${LINE29_LABEL}on" \
  CH2="$CH2 GAME_LINE_WALK=2 GAME_LINE_WALK_PF=2 GAME_LINE_PIECE=2 GAME_LINE_YROW=2 GAME_LINE_RESUME=1" \
  bash port/dreamcast/tools/d367/ch2/ch2-build.sh rP
for arm in off on; do
  O="/root/probe/lanes/route/out-${LINE29_LABEL}${arm}rP"
  test -s "$O/re4dc-game.elf"
  test -f "$O/missing.txt"
  test ! -s "$O/missing.txt"
done
python3 -B port/dreamcast/tools/cloud/build34/upload_compare.py \
  --baseline "$LINE29_BASE_OUTPUT" \
  --arm "/root/probe/lanes/route/out-${LINE29_LABEL}offrP" \
  --output "$LINE29_LOGS/line29-release-off.json"
```

A matched runtime reference uses the identical ON profile with
`GAME_LINE_RESUME=0`; retain its resolved definitions separately from release
OFF identity. Check live ordered collision/STRICT behavior, moving pieces,
target stack/code and warm/cold cost before enablement. **BLOCKED** remains
only SH-4/full-image/private-runtime/console acceptance; there is no SDK,
private asset set or console in this workspace. Cloud continues the assigned
frontend/world and other source slices. No release default or media changes.


## Answers (owner): 2026-10-29 combined engine integration

DONE: `NATIVE_DRAW_OUTCOMES` first slice merged default off with the other three bounded fixes into `77461a84ef85e978e44aab5d936a1b80a2cd93a4`, using four clean no-ff local integrations from `9e6662c36`. Combined release rc0, missing.txt present/empty; ELF SHA256 `49f12668242e722acfa0fee89514323c4aa7892e64014dcb970eb0473fbee0c3`. All four controls resolve zero; complete programme, all15 overlays and all allocated ELF section metadata/payloads match the bound9ee baseline. Fresh-base check and origin-only push/readback passed. A queue-row selection preflight stopped before the first build, then continued in the same clean merged candidate; no source conflict or failed build was hand-resolved.

ALL ON K includes the four new controls. Fresh ALL ON QA at source77461a84, with QA_LINK=1 and all four controls resolved1, passed compile, existing empty missing.txt, loader/standard disc lint with zero violations, ZIP test and staged checksums. Track03 is1,185,760,800 bytes, SHA256 `e70b865a2f55469f2c279094e3a9a86d4576efe22869da0d76f8e464be902c62`. This is a prepared private QA artifact, not a runtime/look/STRICT/memory/timing or physical-console acceptance result. Nothing was copied to SD.

NEXT/BLOCKED: retain this card's exact remaining source sub-slices and runtime/lifetime/look/current-memory/console gates. A first slice does not close the entire EF card. Use the verified image only for an explicitly selected compatible next check, with exact build/assets/scene/window and valid denominator. The user must select/swap intended verified media and establish reviewed link readiness where a console check requires it; current media/Pi/release holds remain. Independent EF02 producer, EF07 owner-scoped plan and EF08 producer-completion work proceeds from the integrated source. No default or frozen-release recipe promotion.


## Cloud progress 2026-10-29: EFM slot-class identity (review 9.1)

**DONE — source candidate, default 0.** Based on published source `e693945933cf088a13782e756fc356008cdba4b8`; fast-forwarded to current integration `39ed524a3b0a4727148aaa5a45eaaea4d211cede` before freeze. Branch `codex/efm-class-identity-20261029`; coordinator-reviewed source delivery. Owned production changes are `include/cManager.h`, `src/game/esp_efm.cpp`, and the narrowly reserved cObj mapping/backing publication in `port/dreamcast/game/parts_bridge.cpp`; dedicated `port/dreamcast/game/efm_class_identity.mk` and EFM host fixture are new. The coordinator includes the fragment in the top Makefile; production ownership remains otherwise unchanged. The bridge file is the one additional source reservation agreed with the coordinator because cObj's `arrayAlloc`, `arrayFree`, and `prepareWork` are explicit bridge specializations that manager-header hooks cannot observe.

`GAME_EFM_CLASS_IDENTITY=1` keeps the existing 64-entry EFM class index keyed to a separate object-class/mapping incarnation. `cManager<cObj>` publishes before `memClear` and after every constructor attempt (including a failed constructor that leaves new bytes); `create(id)`, `create(id,no)`, and `createBack` are covered. Manager `roomInit`, push and pop, and specialized bridge pool free/alloc/new page publication also invalidate the token. An ordinary deletion does not; the existing `re4dc_alive_gen` still advances for alive-list consumers. The cache continues to include dead mapped class 4/5/9 slots, keep source slot order and filter globals, and refuse its index beyond 64 entries (also when a slot index exceeds `u16`). Both incarnation counters saturate at their terminal `u32` value; reaching either terminal forces the source scan for that call and all subsequent calls, so an earlier token cannot reappear after wrap. Frozen/pushed pools use the source scan. After a callback changes the class epoch, pool, frozen/push state, or nested cache build, the current call resumes the source loop at exactly the next slot. No list, manager layout, allocator budget, or assembly change.

**Host validation DONE.** `python3 -B port/dreamcast/tests/test_efm_class_identity.py` passed in ~8 seconds. It compiles an actual excerpt of production `EfmDelete`/`EfmDeleteSub`, production `cManager` methods, and production `parts_bridge.cpp` against small synthetic object/model stubs. The only header ABI adaptation replaces `cUnit`'s 32-bit sized-delete parameter with host `size_t`; the host uses the bridge `workAt` because its 64-bit pool header cannot use the SH-4 +64 slot offset. Normal and ASan/UBSan builds both pass all 13 source-loop parity scenarios for `RE4DC_FX_SCAN=1` and `=2`: repeated deletion with unchanged class epoch but advanced alive epoch; death/reconstruction at the same slot; failed front/back construction leaving class bytes; same-address pool free/reallocation; new and pinned backing pages; successful front/back creation; push/pop; frozen selector; 65 candidates/refusal; nested delete then create with changed filter globals; callback pool push with exact continuation, and forced class-epoch and build-serial near-exhaustion followed by further mapped-slot mutations. Each case compares candidate visitation order and final mapped object flags/class/core, including source results after nested effects. LeakSanitizer is disabled because this managed executor cannot read `/proc` task entries; ASan and UBSan ran with halt-on-error.

Synthetic repeated-sweep evidence: 9 indexed versus 96 source `EfmDeleteSub` calls for the fixture's three passes over four eight-slot pages; candidate visitation and final state match. This is a call count, not a frame-time or hardware gain. An x86-64 `-O2 -g0` excerpt comparison measured `.text` 592 -> 700 bytes, `.text.unlikely` 252 -> 300 bytes, `.bss` 216 -> 224 bytes, and `EfmDelete` stack-use 48 -> 64 bytes. These host measurements include fixture ABI/data layout and must not be presented as SH-4 size. The production additions are two `u32` words (class epoch and nested build serial, 8 declared target bytes before linker alignment); the existing 64 x `u16` index is unchanged. Target code size, stack and cache-line traffic remain unmeasured. Source diff has 117 insertions/11 deletions in three existing production files, plus the dedicated fragment and fixture (all within scope).

**OFF identity DONE at host scope.** The test compares baseline versus current with `RE4DC_EFM_CLASS_IDENTITY=0` for the real EFM excerpt, manager methods, and bridge. Their complete `-E -P` preprocessor bytes, including whitespace, and complete `-O2 -g0` object bytes match. Object SHA256 prefixes are respectively `4c32efe6a5191650`, `030672eb0d2d10d3`, and `245c2e6ac90d1693`. `make -f Makefile -n` verifies absent and explicit zero produce the same five representative compile commands with no new define, while an explicit empty value is rejected; ON publishes the flag to `esp_efm`, `obj`, a stage REL (`r101`), `parts_bridge`, and `native_static`. All C++ compile rules in this Makefile use `GAME_CPPFLAGS` or `PLATFORM_CPPFLAGS`, including module objects and source re-includes. The coordinator added the top-level include after EF16 landed; the fixture now tests the normal Makefile without a second fragment include.

**NEXT — coordinator review/integration and real comparisons.** The source and shared include are ready for serialized local integration. Rebuild the pinned public target source with absent/zero/ON controls, checking affected translation-unit byte identity with the switch off and SH-4 BSS/stack/code size. The local owner then runs the private release recipe and existing-empty `missing.txt` gate, source/STRICT and room/view/enemy gameplay comparisons, compatible ALL ON QA, Flycast function, actual current-memory overlap, and real-console warm/cold timing. The synthetic 9/96 call count is an incidence hint only; no whole-frame ms claim or knob promotion follows from it.

**BLOCKED only at target/private gates.** No SH-4 SDK/compiler, private Build-Assets/package inputs, Flycast capture, or physical Dreamcast are available in this worker environment. Consequently there is no target object, full image, runtime, current memory, warm/cold I-cache, data-line, MODELLED whole-frame, or console result. No release, media, or SD publication is included in this source delivery.

**Exact local follow-up commands (not executed in cloud):** use the existing
pinned SDK and private recipe inputs. Public pins are KOS804b3195 plus repository
patches, GCC15.2.0/binutils2.45.1/newlib4.6.0.20260123 and
SH4ZAM33fa4850cacb30dd0ad35485ef035526ec4ce782. Set fresh lane-owned paths and
the ordinary-release output bound to this delivery base:

```bash
set -euo pipefail
: "${EFM29_LABEL:?fresh lane label}"
: "${EFM29_LOGS:?fresh log directory}"
: "${EFM29_PROGRAMS:?fresh programme directory}"
: "${EFM29_BASE_OUTPUT:?bound current-base ordinary-release output}"
source <(tr -d '\r' < port/dreamcast/tools/d367/rr/recipe.conf)
export T="$PWD" K="$EFM29_LOGS"
export ROUTE_PROGRAMS_DIR="$EFM29_PROGRAMS" ROUTE_PROGRAMS_JSON=''
test ! -e "/root/probe/lanes/route/out-${EFM29_LABEL}offrP"
LP="${EFM29_LABEL}off" CH2="$CH2 GAME_EFM_CLASS_IDENTITY=0" \
  bash port/dreamcast/tools/d367/ch2/ch2-build.sh rP
for value in 0 1; do
  label="${EFM29_LABEL}check${value}"
  test ! -e "/root/probe/lanes/route/out-${label}rP"
  LP="$label" CH2="$CH2 GAME_FX_SCAN=2 GAME_ATCHK=1 GAME_ATCHK_LIST=1 GAME_WORKAT_INLINE=1 GAME_ESP_OWNER=1 OBJECT_DEMAND=1 ENEMY_DEMAND=1 GAME_EFM_CLASS_IDENTITY=$value" \
    bash port/dreamcast/tools/d367/ch2/ch2-build.sh rP
done
for arm in off check0 check1; do
  O="/root/probe/lanes/route/out-${EFM29_LABEL}${arm}rP"
  test -s "$O/re4dc-game.elf"
  test -f "$O/missing.txt"
  test ! -s "$O/missing.txt"
done
python3 -B port/dreamcast/tools/cloud/build34/upload_compare.py \
  --baseline "$EFM29_BASE_OUTPUT" \
  --arm "/root/probe/lanes/route/out-${EFM29_LABEL}offrP" \
  --output "$EFM29_LOGS/efm29-release-off.json"
```

The `check0/check1` profiles are the matched source/index comparison pair;
they are distinct from ordinary-release OFF identity. Keep actual resolved
definitions and check the existing FX_SCAN2 EFM mismatch counter, callback
order, creation/deletion and room/pool lifecycle in the same selected runtime.
Current-image memory/STRICT/look and console cost remain separate gates.
Cloud proceeds with the assigned world continuation while those gates are local.


## Answers (owner): 2026-10-29 cloud implementation assignment

EF13 water-layer producer/schema/compiled-adapter/current-consumer implementation is assigned to the cloud now, using public source tables and synthetic fixtures. Local EF11 retains cloth/effect include ownership; do not edit those files or effects30.mk. This is a scoped source implementation assignment, not accepted water coverage. Real private packages, live look/gameplay/lifecycle and console cost remain separate owner gates. See the [exact tasks, file grants and executable checks](systemic-performance-20261029.md#answers-owner-2026-10-29-cloud-source-only-implementation). Start from newest origin/t15/int, retain all prior answers, and hand back small buildable consumed changes with default0 and meaningful OFF/host evidence.


## 2026-10-29 EF13 Build29: bounded, source-bound compiled water layer adapter

**DONE (first public-source slice).** Against current integration `39ed524a3b0a4727148aaa5a45eaaea4d211cede` (the unchanged `espgen45.cpp` base blob is `130ffee540ccf28df31b5696312cb6993eac1bd6`), the default-off `WATER_LAYER29` fragment selects only `espgen45.o` and requires `ROUTE_CH13=1` and `WATER_PS2=1`. The primary game Makefile includes `water_layer29.mk` exactly once. The feature adds a versioned `Water29Definition`, explicit room/source-family key and owner/incarnation, a bound count of 32 rows, exact row byte extents, and per-family `Water29SourceBytes` backing with owner/incarnation, alignment and range checks before any row read. Publication uses overlap-safe `memmove` into one bounded store; invalid publications leave the prior bound view and compiled fallback intact. Misaligned or truncated headers, bad version/extents/counts, nonfinite or nonpositive geometry, wrong room/source/owner, misplaced row pointers and disabled room masks are refused. A retired owner/incarnation cannot retire a newly published different incarnation.

The public `water_layer29_source.py` producer reads the already checked-in `water_ps2_table.inc` and `water_ps2_ext.inc`, verifies each row's original EFF-family provenance and contiguous room spans, and emits `water_layer29_source.inc` with version, source key, offset and count. The current `re4dc_water_ps2_rows`, queue, draw and r10b replacement path consume the adapter. One current-room compiled view and the published store view avoid repeated row/numeric validation in the queue and draw hot path. Existing layer encounter order, room/area/display predicates, FX-level filter, texture pattern and vblank phase, transform, color, blend, projection and viewport remain in the production draw loops. `Re4dcWaterLayer -> WaterNode -> water_emit` is unchanged; its native texture resolution and deferred node copy remain authoritative. Definition outcomes are `UNBOUND`, `NO_WATER`, `BOUND` and `REFUSED`; native return outcomes are separately `NOT_ATTEMPTED`, `ADMITTED`, `PARTIAL_REFUSAL` and `TOTAL_REFUSAL`. These native outcomes describe queue/immediate admission, not deferred completion. A fully refused r10b image falls back to its existing native GameCube surface; partial refusal is counted and logged without duplicating already admitted layers.

**Validation.** `python3 port/dreamcast/tools/cloud/build29/water_layer29_fixture.py` passes 4 tests. `ASAN_OPTIONS=detect_leaks=0 WATER29_SANITIZE=1 python3 port/dreamcast/tools/cloud/build29/water_layer29_fixture.py` passes the same 4 tests under ASan/UBSan. The fixture extracts and compiles the actual production source table declarations, generated adapter, selector, draw, queue and replacement functions. It compares effective layer fields and order for feature OFF and ON across the six main rooms, three extension rooms, an unsupported room, three ticks (including animated selection), three FX levels, extension disabled and a main-room mask. It tests source metadata regeneration, malformed provenance, no-water/unbound, header/row-span truncation, version/count overflow, source and owner mismatch, aligned-range rejection before dereference, row mutation/address reuse, retirement, overlapping publication and full/partial native refusal. Its pinned `c027b26e` versus current feature-OFF preprocessing and non-debug host object-byte comparisons pass in the three profiles; the source blob is identical at the latest base. `git diff --check` passes.

With a temporary empty KOS `Makefile.rules` solely for make dry-run parsing, `make -f Makefile -n obj/src/game/espgen45.o KOS_BASE=/tmp/water29-kos ROUTE_CH13=1 WATER_PS2=1 WATER45_NATIVE=1 WATER_LAYER29=1` selects `-DRE4DC_WATER_LAYER29=1` alongside the existing water flags. Dry-run comparisons for `espgen45.o`, `espgen.o` and `platform/native_ui.o` show absent control equals explicit zero, while ON affects only `espgen45.o`. Empty, multi-token and invalid controls, missing route and missing WATER_PS2 are rejected. This primary-Makefile proof is part of the fixture. This is Make-selected flag proof, not a target compile.

**Footprint.** Host x86-64 source-extracted `-O2` object with extension ON: `.text` 1829→6575 B, `.data` 12→20 B, `.bss` 6220→10732 B and `.rodata` 1344→3168 B. With extension OFF, `.text` is 1781→4543 B and `.bss` 6220→8268 B. The bound store is 4304 B host and 4288 B under a `g++ -m32 -nostdinc` compile of the actual schema header; with extension OFF it is 1872/1856 B. The 32-bit row sizes are 56 B main and 76 B extension, definition 60 B and view 40 B. Host `-fstack-usage` reports draw 368→528 B with extension ON (368→448 B OFF), water45 queue 8→80 B, new Select 192 B and bind 176 B (extension ON). These are host extracted-source numbers with fixture stubs, not a measured SH target delta; the native WaterNode and tessellator are unchanged. This slice spends fixed memory for source authority and does not claim memory savings.

**NEXT.** The Build29 owner should build the affected SH target object with the pinned public SDK if available, then run the private full-image/overlay OFF identity and compatible ALL ON QA gates. A later source-package slice must establish actual loaded-package row spans/owner retirement at the asset-pipeline boundary and prove additional room definitions from authorized source packages. Compare current visual/look output, deferred completion and texture lifetime, room reentry, clipping/fog/extents, current heap/VRAM and console cost before acceptance.

**BLOCKED external gates.** This cloud workspace has no `sh-elf-g++`, `kos-c++`, KOS SDK or private Build-Assets, and no physical-console/live image. Therefore no SH target compile, full image, private package generation, Flycast look, current-memory or console-timing claim is made. No asset replacement, release/media publication, SD copy or Pi restart is included.


**NEXT for Claude — target and private qualification.** The public pins are KOS
`804b3195` plus repository patches, GCC 15.2.0 / binutils 2.45.1 /
newlib 4.6.0.20260123 and SH4ZAM
`33fa4850cacb30dd0ad35485ef035526ec4ce782`. The cloud has no initialized pinned
SDK. From the candidate checkout with that SDK and the existing private recipe
inputs available, use fresh paths and labels:

```bash
set -euo pipefail
: "${W29_BASE_TREE:?fresh base worktree path}"
: "${W29_LOGS:?fresh log directory}"
: "${W29_PROGRAMS:?fresh programme directory}"
: "${W29_LABEL:?fresh lane label prefix}"
W29_CANDIDATE_TREE="$PWD"
git worktree add --detach "$W29_BASE_TREE" 39ed524a3b0a4727148aaa5a45eaaea4d211cede
source <(tr -d '\r' < port/dreamcast/tools/d367/rr/recipe.conf)
export ROUTE_PROGRAMS_DIR="$W29_PROGRAMS" ROUTE_PROGRAMS_JSON=''
candidate_build() {
  local tree="$1" label="$2" extra="$3"
  local output="/root/probe/lanes/route/out-${label}rP"
  test ! -e "$output"
  T="$tree" K="$W29_LOGS" LP="$label" CH2="$CH2 $extra" \
    bash "$tree/port/dreamcast/tools/d367/ch2/ch2-build.sh" rP
  test -s "$output/re4dc-game.elf"
  test -f "$output/missing.txt"
  test ! -s "$output/missing.txt"
}
candidate_build "$W29_BASE_TREE" "${W29_LABEL}base" ""
candidate_build "$W29_CANDIDATE_TREE" "${W29_LABEL}absent" ""
candidate_build "$W29_CANDIDATE_TREE" "${W29_LABEL}off" "WATER_LAYER29=0"
candidate_build "$W29_CANDIDATE_TREE" "${W29_LABEL}ctrl" \
  "ROUTE_CH13=1 WATER_PS2=1 WATER45_NATIVE=1 WATER_LAYER29=0"
candidate_build "$W29_CANDIDATE_TREE" "${W29_LABEL}on" \
  "ROUTE_CH13=1 WATER_PS2=1 WATER45_NATIVE=1 WATER_LAYER29=1"
python3 -B port/dreamcast/tools/cloud/build34/upload_compare.py \
  --baseline "/root/probe/lanes/route/out-${W29_LABEL}baserP" \
  --arm "/root/probe/lanes/route/out-${W29_LABEL}absentrP" \
  --arm "/root/probe/lanes/route/out-${W29_LABEL}offrP" \
  --output "$W29_LOGS/water29-release-off.json"
```

Retain all resolved flags and build logs, and verify the intended definition on
each affected TU. The release OFF comparison includes the complete programme,
all overlays and allocated ELF sections. Keep the matched `ctrl/on` pair
separate from release identity. After serialized integration, rebuild the
compatible ALL ON QA with `QA_LINK=1` using the existing local QA workflow.
Actual current-image look/gameplay/STRICT, memory margins, loaded-package
lifetime and console timing remain local gates. This source commit does not
enable a release default, publish media, copy to SD, restart the Pi or close
the sixteen-card backlog.

**Private water follow-up:** bind only definitions generated from the authorized loaded package, with the exact row backing extent and owner/incarnation. Re-run current r10b replacement plus main/extension rooms through the matched images; check partial refusal never replays accepted layers, full refusal preserves the current surface, and same-address reload/retirement cannot reuse old source or upload authority. The public compiled-source adapter and table regeneration are complete; new private room coverage is unclaimed.


## Answers (owner): 2026-10-29 expanded cloud ownership

The user assigns all remaining source/synthetic implementation in this build to the cloud, including the relevant continuations from7c4c9200. See the [ready parallel work, exact file handoffs and next consumed slices](systemic-performance-20261029.md#answers-owner-2026-10-29-all-source-work-cloud-assignment). Preserve the already-running local frozen slices and all existing evidence. Cloud owns their source follow-ons after published landing/file release; local owns private assets, actual runtime/console checks and serialized integration. No full-card or hardware acceptance is implied.


## 2026-10-29 EF11: consumed bounded cloth sheet, source/host checkpoint

**DONE (source/host; target pending):** `CLOTH_SHEET11=1` (strict 0/1,
default 0) requires `CLOTH_NATIVE=1 NATIVE_DRAW_OUTCOMES=1
PS2_UPLOAD_INCARNATION=1`. Existing `Esp4e::SetFreeWork` creates a pool-backed,
single-texture grid capped at 100 columns / 50 rows and passes `pTobjA=NULL`.
That real `clothTrans -> re4dc_cloth_native` consumer now prepares one native
material before geometry publication and submits two rolling rows through the
existing effect FIFO. The old mesh/public ABI is unchanged.

The prepared material is a frame-scoped 256-byte opaque receipt. It retains no
source grid/pixel pointers, pins the existing Entry upload and checks Entry
validity, exact nonzero EF06 upload incarnation, current frame and stream owner
before each band/publication. Texture/header preparation happens once; clipped
cells use the same prepared header. Known source/dimension/projection/material
and texture refusals occur before the first packet. Subsequent queue/capacity /
owner refusal is explicit EF03 partial-abort, never a whole-sheet fallback.

Two fixed 100-column rows transform each source point once for an admitted
complete sheet. Triangle strips and bands remain in source row order. Near-plane
cells now emit `(TL,BL,TR)` then `(TR,BL,BR)` through the existing clipper. The old
quad helper used the opposite diagonal and changed noncoplanar cloth UV/geometry.
Source UV progression, strip parity, existing native blend/depth/header policy
and packet order are preserved. A render-only 32-byte incarnation sidecar for
`ClothWk[8]` revokes before Set/Destroy/Init mutation/free; range/alignment and
nonzero identity are checked before use, after texture I/O and before every row.
Wrap stays exhausted at zero, including after Init. No Cloth ABI, simulation,
normal/spring/wind/RNG algorithm or source grid byte is changed.

```bash
python3 -B port/dreamcast/tests/test_native_cloth_sheet11.py
python3 -B port/dreamcast/tests/test_native_draw_outcomes.py
python3 -B port/dreamcast/tests/test_effect_strip21.py
```

The new actual-code suite passes five tests, using ASan/UBSan. It exercises the
real source helper and backend: widths 2/99/100; explicit before-publication
refusal for 101/255; exactly rows*columns transform calls and one texture/header
preparation; source-array identity; actual Destroy/Init hooks during simulated
texture-I/O reuse; pool membership/alignment and zero-token exhaustion; missing
texture, frame/upload/Entry refusal, first/later queue pressure and no duplicate
fallback. A captured actual source strip loop supplies the noncoplanar near-clip
triangle oracle; the old diagonal is explicitly rejected. Packet tests include
the r200-tail branch. Strict Make dependencies/two-consumer propagation and
parent/absent/zero host emitter object identity pass. Existing EF03 5/5 and strip
4/4 checks pass. These are synthetic source/host results, not live look or speed.

**NEXT:** hold the coordinator's SDK slot, run the prepared Make-derived
cloth/native_ui release and dependency-enabled OFF/ON profiles, then full release
OFF, dependency control and candidate ON builds. A fresh output is required:

```bash
python3 -B port/dreamcast/tools/cloud/build29/cloth_sheet_target.py \
  --output "$EF11_FRESH_TARGET_OUT"
```

The helper uses base `255964fdc7d22a61acff1ef59734a36ec91ebff0`, the installed
compiler15.2.0, pinned KOS and initialized SH4ZAM. Full build overrides are
`CLOTH_SHEET11=0` for release OFF;
`NATIVE_DRAW_OUTCOMES=1 PS2_UPLOAD_INCARNATION=1 CLOTH_SHEET11=0` for the matched
existing-native control; and the same dependencies plus `CLOTH_SHEET11=1` for
the candidate. Do not attribute dependency-bundle footprint/cost to this slice.
The current runtime recipe and private build inputs remain unchanged.

**Required unresolved concepts:** this preserves the existing native cloth
approximation, not complete source material equivalence. Source normal cloth
uses alpha `>4` and enabled Z-write; the current native translucent header has
no equivalent alpha test and disables Z-write. The source's stage0 RGB/alpha
multiply-by-four then clamp is also not represented by that simple native
modulation. `pTobjA` adds same-UV stage1 RGB/alpha modulation of the clamped
previous result and selects ordinary alpha blending. Texture-product
precomposition and framebuffer multipass are not generally equivalent. Existing
`model_mask_key` / `resolve(...masked...)` packages implement a distinct
color/mask operation; they cannot be relabeled as this cloth operation. Future
material correction must use a source-bound certified operation through the
existing package/material path or a separately proven native route.

Widths above100 remain explicitly unsupported in this first slice. Follow with
row-major horizontal tiles sharing one boundary column and global UVs; do not
reorder an entire translucent sheet tile-major or claim transform-once wide grids
without a bounded row workspace. EF14 batching can later consume the row helper
through existing matrix wrappers; no assembly or new renderer is introduced.

**BLOCKED (scoped):** SDK slot not yet granted. Target layout/OFF identity,
current supported asset look, runtime retirement/reentry/pressure and complete
cost/headroom/hardware acceptance remain pending. No whole-EF11 closure,
default promotion, emulator/console run, publication or source-material coverage
claim is made by this checkpoint.


### 2026-10-29 EF11 review: terminal source revocation

**DONE (reviewed source/host; corrected target pending):** source revocation is
terminal even with zero packets published. Always check the pool incarnation,
source frame, grid pointer and dimensions after material preparation, including
when preparation failed, before considering an ordinary preflight result.
Revocation uses EF03 PartialAbort (possibly zero accepted packets), so the actual
clothTrans routing cannot enter its source GX walk through retired/reused data.
Recheck before row reads and after band submission/refusal; accepted counts are
preserved. A callback reaching an already retired pool cell stops before texture
or grid dereference; a live cell with its draw bit cleared is explicit PolicySkip.
Ordinary supported-source resource refusal retains its previous routing.

The new suite remains 5/5. Its actual clothTrans routing block and recovered GX
strip loop are now instrumented: simulated successful/failed texture-I/O
retirement, source-frame revocation, already retired callbacks and a band refusal
following source retirement produce zero fallback reads/draws. Missing texture
with a still-valid source reaches the old source loop, distinguishing that case.

Original source `2626ba4f27efb16d089cd97bd585ac00bf6e15a9` completed its original
matrix before this review: 8 exact release/dependency OFF object comparisons,
two enabled objects, and full release OFF / dependency control / original sheet
ON all rc0/41s, nonempty ELF and existing empty missing.txt. Original release OFF
raw programme, 15 overlays and 11 allocated ELF sections match bound base
`255964fdc7d22a61acff1ef59734a36ec91ebff0`. Full original ON remains pre-review
and does not qualify the corrected source lifetime handling. Receipts/outputs
are retained under `/root/probe/engine-ef11-20261029-target-r1/` and
`/root/probe/lanes/route/out-ef11w1{rel,ctrl,on}rP`.

**NEXT:** coordinator-granted narrow target recheck: cloth-only release /
dependency parent/absent/zero plus supported ON (`--units cloth`), then one
corrected sheet ON full build. Backend/old controls are unchanged and their
valid original checks are retained; compare the corrected OFF object to the
original matrix before reusing those full controls. No SDK retry starts without
the coordinator slot grant. Material debts and wide-grid refusals above remain.


### 2026-10-29 EF11 final target handback

**DONE: IMPLEMENTED + TARGET VALIDATED bounded slice, default0.** Reviewed
runtime `9bbff5d26d4f478e865899854811ce30ccb83228` passes the cloth-only release /
dependency parent/absent/zero target recheck (four exact OFF object comparisons)
and supported ON compile. All four changed cloth OFF objects match the retained
original matrix. Backend/API/geometry bytes are unchanged, so the original full
release/dependency controls and backend object checks remain valid.

Corrected full sheet ON: real rc0/42s, nonempty ELF, existing empty missing.txt,
SHA256 `36add09d9203c9d9f1523d71065c79dbcbddc9cfb02cf968ff356d7a2d5ae481`.
The original release OFF programme, all15 overlays and all11 allocated ELF
sections match the bound255/runtime064 control; whole debug ELF equality remains
separate. After normalizing exact output/checkout roots and whitespace, release
OFF differs from the control solely by new CLOTH_SHEET11 absent->0. The matched
dependency control and corrected candidate differ solely by CLOTH_SHEET11 0->1.
The production OFF/control comparison also enables NATIVE_DRAW_OUTCOMES and
PS2_UPLOAD_INCARNATION, and is not a one-variable sheet comparison.

[Compact source/target receipt](../../../tools/cloud/build29/receipts/cloth-sheet11-target.json).
Complete reviewed evidence: `/root/probe/engine-ef11-20261029-target-r2/`;
corrected full ON: `/root/probe/lanes/route/out-ef11w2onrP`. Original matrices and
three full arms remain under target-r1 / out-ef11w1{rel,ctrl,on}rP. Recipe SHA256
is unchanged `66940fea7531fd3a402dc8fc6f779d7861801c0cd39a4c91be31f7f0871816c0`.

`_end`: releaseOFF8c4170d4, dependency-control8c417e74, reviewedON8c418334:
+1,216 bytes for the sheet versus its matched dependencies; +4,704 bytes for
the complete dependency+sheet bundle versus production. The cloth sidecar is
32 linked data bytes. Selected local frames: clothTrans3664->4004 bytes;
prepare300 and band7436 bytes in the supported target profile. These are local
frames/linked footprint, not whole-stack bounds, runtime headroom or timing.
Host5/5 (actual code plus ASan/UBSan) and retained EF03 5/5 / strip4/4 checks
remain scoped as above. No live look, gameplay, private-input memory/retirement,
physical-console timing or speed result is claimed.

**NEXT / ownership:** coordinator integration default0 and actual private /
runtime gates. Further wide-grid, material and effect source implementation is
reserved to the user-directed cloud source lane after this delivery lands.
Widths101/255 and the named alpha/depth/TEV/pTobjA material concepts remain open;
this is not whole-EF11 closure. The SDK session completed and slot is released;
no live job, source promotion, emulator, media change or publication follows.


## Answers (owner): 2026-10-29 frozen local source release

EF04/EF09/EF11/EF16 first slices landed at `c027b26e32229dc9035b9fe2e1ac399bd9ee20b0` via four clean no-ff merges from8f222fb4. All48 non-handback files match the exact target-qualified delivery blobs; current owner prefixes were preserved and no source conflict was hand-resolved. Combined release rc0, actual nonempty ELF and existing empty missing.txt; all new controls resolved0. Full programme, all15 overlays and every allocated ELF section metadata/payload match bound runtime064bfa4ea. ELF SHA256 `49a40830684f8676336f042fe54c28e20e220f378f6f4ab0fe146e1d2f1bee71`. Fresh-base origin-only push/readback passed.

Compatible ALLON K27 adds NATIVE_FE_CONTINUATION=1, WORLD_PREPARED09=1 and CLOTH_SHEET11=1, with QA_LINK=1. Compilation, existing empty missing.txt, actual global ABI macros across542 C++ commands, affected consumer flags, loader/standard disc lint (zero violations), ZIP test and staged checksums passed. Private QA track03 SHA256 `97c00661821b5577fb987cc597ea1469877a6f9ed8321c1371cd038a92c78fd5`. Prepared only: no current-image gameplay/look/STRICT/full-memory/cost or hardware acceptance and no SD copy. LOG_ATOMIC16 remains0 and individually parked outsideALLON pending bounded IRQ/fault/NMI/cache qualification. WORLD_PORTAL29/WORLD_PORTAL_COMPLETION remain0 in this broad profile; supported separate-profile proof and composition work remain open.

EF04 original failed ON target remains retained; only the guarded placement-new repair was requalified. EF11 source retirement after failed or successful preparation is terminal even before publication, with no stale GX fallback. EF09 uses existing allocator authority outside a candidate before read/free, bounded optional facts and copied queue records. EF16 is only a selector for the existing whole-call guard plus invalid fault-length/null handling; it is not a bounded or NMI-safe logger and does not repair the historical failed memory capture. These scoped results do not close their EF cards.

Cloud ownership takes effect at this exact integrated source SHA. Do not redo these first slices. Continue the all-source assignment below: transactional/demand skin preparation, current-image actor class presentation, ordered world pages/whole-part completion, stream then qualified clip composition, real mutation publishers, prepared actual binding, static content/spans, wide/material-correct cloth and remaining effects, useful batches/skin reuse and bounded logger. The independent water/frontend/EFM/collision/line assignments remain ready. Local delivery-file holds are removed; actual source producer dependencies and one-writer-per-file reservations still apply, especially native_ui/native_model and actor shared headers. Local data is not a prerequisite for independent source/synthetic work.

Local next: bind actual final programme/overlays and private packages, choose a distinct stock current-image affected scene/fixture, then run supported output/look/gameplay/STRICT/current-memory/cost checks. No repeated no-input menu capture or unchanged failed-memory retry. Physical console gates require the intended media selected/swapped by the user and reviewed link readiness. Frozen Test24b, Pi/media/look/Castle/Ashley and all explicitly incomplete historical gates remain held.

Exact shared-file grants: [systemic owner handoff](systemic-performance-20261029.md#answers-owner-2026-10-29-frozen-local-source-release).

## Cloud progress 2026-10-29: distinct collision-body changes (review 9.2)

**DONE:** implemented the assigned collision slice on
`codex/collision-distinct-20261029`, rebased to
`8f5a269e5e06dd4ec02857cf5beb0e71f3c4561b`. The source input was
`e6939459`; subsequent integration updates were replayed before delivery.
The exclusive production files are `include/atariInfo.h` and
`src/game/at_mod.cpp`. The cloud coordinator added
`game/atchk_distinct29.mk` and its top-level Make include after the local
EF16 `game30.mk` change landed. No manager lifecycle hook is changed here.

`GAME_ATCHK_DISTINCT29=1` replaces the existing 64-write history with at most
64 distinct body addresses and independent enemy/object pending bits. A query
clears only its own successfully applied or recollected changes. Repeated
toggles cannot exhaust the table by themselves; intermediate queries still see
the state at that query. A reader that falls behind is conservatively invalidated
without discarding the other reader's progress. More than 64 distinct pending
bodies, an oversized source list or a full candidate list retains the source
fallback. No generation-wrap dependency or dynamic allocation is introduced.

Every noted address is matched to the current generation-bound ordered list
before dereferencing a body. A proven nonmember is skipped safely, including a
dead body still executing its move. Insertions/removals preserve source order;
manager generation/head/length changes rebuild before reuse. The existing
`GAME_ATCHK_CACHE=2` comparison remains the live reference. The control defaults
to 0 and requires `GAME_ATCHK`, `GAME_ATCHK_LIST` and `GAME_ATCHK_CACHE`.
Its definition reaches all game/room/platform consumers of the field wrappers.

**Validation performed:** the production-extracted wrapper/list/candidate
fixture passes in cache modes 1 and 2, both normally and with ASan/UBSan.
It covers 257 toggles of one body, 65 distinct bodies, independent reader
progress, query boundaries, return-to-original changes, ordered mixed updates,
dead/absent/reused/reordered bodies, candidate/list overflow and a deliberately
unnoted-write negative control. Both existing alive-list suites pass all eight
configurations each. LeakSanitizer alone is disabled because this managed
executor prevents its thread walk; address and undefined-behavior checks run.

`check_atchk_distinct29_off.py --baseline 8f5a269e...` proves baseline,
absent and explicit-zero preprocessing and **32-bit host excerpt objects**
byte-identical in both cache modes. Object SHA256s are
`38c896c7a9946bcd63a259c5fa8cd2f9d7920dba1012ff29585323ad81a8d1e9`
(cache1) and
`5a1b87d2949e722f05bb57b0fe697ae5bf830d4122025900b057c0ddfed58a0e`
(cache2). These are not complete SH-4 objects or image identity claims.
The real Makefile's dry-run commands select the new definition for
`at_mod.o`, a room overlay TU and `native_ui.o`; absent/zero omit it.
An empty KOS rules file was used solely to inspect Make command selection,
without executing a target compiler.

Reproduce the executed source/host gates from this branch:

```sh
python3 -B port/dreamcast/tests/test_atchk_distinct29.py
ASAN_OPTIONS=detect_leaks=0 ATCHK_SANITIZE=1 \
  python3 -B port/dreamcast/tests/test_atchk_distinct29.py
python3 -B port/dreamcast/tests/check_atchk_distinct29_off.py \
  --baseline 8f5a269e5e06dd4ec02857cf5beb0e71f3c4561b
python3 -B port/dreamcast/tests/test_atlist_capacity.py
python3 -B port/dreamcast/tests/test_atlist_overflow.py
git diff --check
```

**Storage/cost:** the declared 32-bit candidate/tracker fields total 1,130
bytes versus 1,140 before this switch (two 404-byte candidate records plus
322 bytes of tracking, versus two 440-byte records plus 260 bytes). Linker
alignment can change the final delta; this is a layout calculation, not target
BSS measurement. Tracking performs a bounded linear search over distinct
addresses; the change avoids repeated-write overflow and full recollection,
but does not establish a speedup for every low-dirty workload. SH-4 code/stack,
warm/cold cycles, loads/stores/32-byte lines and whole-frame **MODELLED** delta
remain unmeasured. No frame-time saving or memory-headroom result is claimed.

**BLOCKED validation inputs:** no SH-4/KOS SDK or initialized SH4ZAM is installed
in this cloud workspace, and no private recipe inputs or console are available.
The required public pins remain KOS `804b3195` plus repository patches,
GCC15.2.0/binutils2.45.1/newlib4.6.0.20260123 and SH4ZAM
`33fa4850cacb30dd0ad35485ef035526ec4ce782`. This holds target/full-image/live
acceptance only. Cloud continues EF13 water and the other assigned source work.

**NEXT for Claude:** run the existing private release recipe on the exact base
and candidate, then a matched collision comparison profile. These commands use
fresh lane-owned paths/labels supplied in `C29_BASE_TREE`, `C29_LOGS`,
`C29_PROGRAMS` and `C29_LABEL`; the base tree must not already exist. Run
after the normal pinned SDK environment and private inputs are available:

```bash
set -euo pipefail
: "${C29_BASE_TREE:?fresh base worktree path}"
: "${C29_LOGS:?fresh log directory}"
: "${C29_PROGRAMS:?fresh programme directory}"
: "${C29_LABEL:?fresh lane label prefix}"
C29_CANDIDATE_TREE="$PWD"
git worktree add --detach "$C29_BASE_TREE" 8f5a269e5e06dd4ec02857cf5beb0e71f3c4561b
source <(tr -d '\r' < port/dreamcast/tools/d367/rr/recipe.conf)
export ROUTE_PROGRAMS_DIR="$C29_PROGRAMS" ROUTE_PROGRAMS_JSON=''
c29_build() {
  local tree="$1" label="$2" extra="$3"
  local output="/root/probe/lanes/route/out-${label}rP"
  test ! -e "$output"
  T="$tree" K="$C29_LOGS" LP="$label" CH2="$CH2 $extra" \
    bash "$tree/port/dreamcast/tools/d367/ch2/ch2-build.sh" rP
  test -s "$output/re4dc-game.elf"
  test -f "$output/missing.txt"
  test ! -s "$output/missing.txt"
}
c29_build "$C29_BASE_TREE" "${C29_LABEL}base" ""
c29_build "$C29_CANDIDATE_TREE" "${C29_LABEL}off" "GAME_ATCHK_DISTINCT29=0"
c29_build "$C29_CANDIDATE_TREE" "${C29_LABEL}ctrl" \
  "GAME_ATCHK=1 GAME_ATCHK_LIST=1 GAME_ATCHK_CACHE=2 GAME_ATCHK_DISTINCT29=0"
c29_build "$C29_CANDIDATE_TREE" "${C29_LABEL}on" \
  "GAME_ATCHK=1 GAME_ATCHK_LIST=1 GAME_ATCHK_CACHE=2 GAME_ATCHK_DISTINCT29=1"
python3 -B port/dreamcast/tools/cloud/build34/upload_compare.py \
  --baseline "/root/probe/lanes/route/out-${C29_LABEL}baserP" \
  --arm "/root/probe/lanes/route/out-${C29_LABEL}offrP" \
  --output "$C29_LOGS/collision29-release-off.json"
```

Keep the matched `ctrl/on` outputs and resolved definitions separate from the
release OFF identity pair. After a compatible local runtime is selected,
check `ATC mismatch=0`, ordered collision behavior and retirement/room-change
cases in that matched pair; collect target cost and actual memory margins.
The hardware/media/link prerequisites remain unchanged. No switch is promoted,
no release/media binary is published, and this source slice does not close
Build29 or the wider simulation/runtime acceptance gates.


## Answers (owner): 2026-10-29 distinct collision integration

DONE: `09adad45f880f8bdc8c77fe6297f6292a7e3cf55` landed via a clean isolated no-ff merge `10e5f887b427035c538599a98a6734271f59ef0c` from8f5a269e, default0. Reviewed reader-specific pending consumption/overflow, current ordered membership before dereference, source-order insertion and successful recollection. Existing manager generation/head/length remains the lifetime authority; this slice does not repair/prove inherited32-bit generation wrap.

Repeated source-host fixture, ASan/UBSan, baseline/absent/zero host preprocessing/object comparison and both existing list suites PASS. Pinned local SDK full recipes: default release absent, explicit0, matched CACHE2 control0 and CACHE2 enabled1 all compile/link with existing empty missing.txt. Actual global C++ command propagation was checked in every arm. Complete programme/all15 overlays/all allocated ELF-section metadata and bytes of absent/zero match the bound c027 release baseline; intervening8f5a updates are docs-only. The adapted helper's post-build qualification ran before its fresh-base origin-only push/readback. No conflict resolution or source guard change.

ALLON K28 adds GAME_ATCHK_DISTINCT29=1 with its existing GAME_ATCHK=1/LIST1/CACHE1 dependencies and QA_LINK1. Compatible QA compilation, existing empty missing.txt, actual global macro commands, loader/standard lints, ZIP and staged checksums PASS. Track03 SHA256 `e32f98c16b3ebd98efad6834245dde5d4886da9847ff3fea526d7910459fdd72`. Prepared only, no SD copy, recipe promotion or current-QA runtime acceptance.

NEXT: matched CACHE2 control/enabled live ATC comparison, actual ordered collision/intermediate query/retirement/room transitions and full cost/memory/console qualification. No speed or memory-headroom gain is inferred from host logic, target links or declared layout. Console requires intended media selected/swapped by the user and reviewed link readiness. Other cloud EFM/line/water/frontend and source continuations remain independently assigned.

The separate natural portrait/cloth route is still bound to c027's prior QA image: its saved state must not be reused on this new image. Its exact-image window2 entered New Game/movie12000; window3 visibly played the opening cinematic and saved state03 with the15unexecuted phone rules. That is scoped old-image functional evidence, not current collision or live actor/cloth acceptance; historical damaged logs and holds remain.
