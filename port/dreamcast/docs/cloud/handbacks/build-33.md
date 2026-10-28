# Build 33: ordered static-object output batches

**2026-10-28 progress 2: DONE** guarded ordered header coalescing, per-cause
barrier census, exact/sanitized host oracle and SH-4 identity/cost gates;
**NEXT** Claude's private comparisons; cloud proceeds to Build 34; **BLOCKED** real coverage,
complete image identity, appearance/STRICT and net console benefit require the
owner commands below.

Branch: `codex/static-object-batch-20261028`, based on
`14f6ef1ef864682d183e7f8647a06fea514578fe` (`origin/t15/int`).
The first, documentation-only step was pushed as `b5be403e`; its progress was
source/history and ordering design complete, runtime validation next, private
coverage blocked. The runtime step keeps the new switch at zero and leaves
the queue, release recipe and assets unchanged.

## Source findings and selected implementation

`STATIC_OBJ_BATCH` was introduced by
[63d86137](https://github.com/lamb2k/re4dc/commit/63d86137) on 2026-10-15.
[76ffb399](https://github.com/lamb2k/re4dc/commit/76ffb399) moved its storage
into heap-4 room cells and distinguished exact centre-independent lighting
(`=1`) from merging centre-lit groups (`=2`, an existing appearance tradeoff).
The release uses `=2` with `STATIC_OBJ_BATCH_WORDCMP=1`.

`model_bridge.cpp` currently concatenates original GX lists only when their
whole part records and lighting agree, for the same model/info. It requires
opaque blend, 2..16 parts and qualified room storage. The scanner's
`m_obj_split` structural trigger therefore includes single-part objects,
larger infos and blended parts. A trigger's vertex count is potential coverage,
not duplicate vertices or a measured saving.

Simply concatenating lists across placements would use the wrong transform,
source arrays or lighting. The new `STATIC_OBJ_BATCH33=0` control instead
coalesces **consecutive identical final TA polygon headers**, after each
placement keeps its original transform, lighting, texture binding and vertex
generation. It saves redundant 32-byte header submissions; it does not remove
vertex transforms, per-part binding or store-queue lock pairs.

The old `sob::take` refusal counters remain meaningful for the raw-GX merger:
`m_obj_split` can still increase while the new output batch saves headers.
Report new eligible/coalesced-header counts separately. The scanner's
441k vertices are not claimed as removed processing or traffic.

The existing bridge's static classes receive a marker in the unused
`source_key[3]` byte; no struct or asset ABI extension is needed. Full part
copies already carry that byte through the existing unified deferred queue.
Opaque, cutout and blended runs remain in their original list and encounter
order. Blended work is never gathered into an independent queue or sorted
around other models/effects. Single-part placements and infos above 16 parts
can then use the same output batching without changing the old GX merger.

Admission must prove identical final 32-byte headers, the same scene/frame
and list, completed strip boundaries, and no intervening foreign submission.
Every other stream/direct producer, list/scene transition and abort is a
barrier. Different header/UV format, texture state, fog, depth, cull, alpha or
unknown output boundaries retain the original header. The synthetic oracle
will compare each vertex word with its effective header in original order;
only a repeated identical adjacent header may disappear.

## Step 1 identity and cost

This commit changes documentation only. Runtime/preprocessed code, object
selection and image inputs are unchanged by construction. Added warm/cold-I
cycles, loads/stores, 32-byte lines, code, stack and resident bytes are all
**0**. **MODELLED whole-frame delta: 0 ms.** No new image build, target timing
or gameplay acceptance is claimed. The runtime step must carry its own
disabled identity, correctness and cost receipts before publication.

## Exact baseline commands for Claude

In Bash at the repository root, set absolute `BUILD_ASSETS`, `IMAGE_RECIPE`,
`GDEMU_ZIP`, a new `OUT`, `SDK_ENV` (the pinned toolchain's `PREFIX/env.sh`)
and `QALINK_PI` (SSH alias or `user@host`). The SDK must contain built KOS
libraries; its environment defines `RE4DC_KOS_BASE` and `RE4DC_KOS_CC_BASE`.
The baseline command is:

```sh
set -euo pipefail
source "$SDK_ENV"
git submodule update --init -- port/dreamcast/game/third_party/sh4zam
mkdir -p "$OUT"
export SOURCE_DATE_EPOCH=1760000000
RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-control" \
  bash port/dreamcast/build-public.sh \
  STATIC_OBJ_BATCH=2 STATIC_OBJ_BATCH_WORDCMP=1 \
  DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 QA_LINK=1 QA_LINK_REVIEW28=1 \
  BENCHMARK=0 PMC_ROW=0 WORLD_METER=1 DRAW_FALLBACK_AUDIT=1 \
  DRAW_SETUP_AUDIT=1 FALLBACK_AUDIT29=1
python3 port/dreamcast/tools/swap-program.py \
  "$GDEMU_ZIP" "$OUT/program-control" "$OUT/disc-control"
python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-control/disc.gdi" --profile loader
python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-control/disc.gdi" --profile standard
```

Run the Pi companion with `python3 ~/qalink/qalink_pi.py serve --review28`,
boot this disc and establish REMOTE LINK. Capture the barn props and doorway,
village racks/windows/doors, and a view containing overlapping blended props
and effects, preserving identical camera and game state for later A/B:

```sh
ql() {
  python3 port/dreamcast/tools/qalink/qalink.py --pi "$QALINK_PI" --review28 \
    --out "$OUT/capture/control" "$@"
}
VIEW=barn-props
ql status
ql send MENU
ql capture start "$VIEW"
ql send RESUME
read -r -p 'Run the matched view for at least 300 drawn frames, then press Enter: '
ql send MENU
ql send DIAG
ql capture stop "$VIEW"
```

Retain resolved knobs, complete build/missing-symbol logs, recipe/assets and
ELF/overlay/GDI/track hashes, raw DFA/DSA/WORLD_METER windows and their frame
denominators. The cloud has no built KOS libraries or private assets; full
game/overlay/image and console gates remain with Claude.

## Questions

1. Which private `m_obj_split` entries are single-part, above 16 parts, or
   blended, and which actually appear consecutively with the same material
   in the matched views? Return model/part identities and measured windows,
   not the aggregate scanner vertex totals as performance evidence.
2. Retain the baseline captures for the candidate run. Translucent overlap,
   cutout edges, moving doors/props, texture animation, room reload and the
   normal STRICT route will be acceptance gates.

## Answers (Claude)

Pending.

## Answers (owner)

2026-10-28 Codex: design-only step merged as `419720efb`. The release
recipe build passes rc=0/missing=0; ELF SHA-256
`bfa25b6d2e918efad8001f30d531fc3b37b4d38f55c42abcaf902a8bb75264ef`.
No runtime switch was added here, so the prepared ALL ON32 candidate is not
rebuilt for this documentation-only step. Runtime/default-off order oracle
and cost qualification remain your next small commit.

1. Local reclassification of the existing Scan29 snapshot at `894454ec`
   (not a fresh current-image scan) found 6,980 `m_obj_split` candidate rows:

   | Recorded part-count class | Candidate part rows | Static vertices | Model entries |
   |---|---:|---:|---:|
   | single-part | 5,064 | 253,742 | 5,064 |
   | above 16 parts | 1,916 | 187,282 | 52 |

   The candidate total is 441,024 static vertices. There are a further
   12,558 rows with status `unknown`, excluded from that table. This
   partition uses the scanner's recorded `part_count` evidence; it does not
   prove live static-bridge class, blend/lighting/state eligibility or
   duplicate work. The snapshot includes non-static/global/unassigned
   entries and has the already disclosed layered-texture/old-world gaps.
   It cannot supply a separate reliable blended count or consecutive final
   TA-header equality. Those need the runtime/order counters and matched
   views; no FPS saving is inferred from these totals. The compressed source
   TSV SHA-256 is `9a566568dafd67fcf0981fc03e91d4f65752db5286b7fe88ed73c5bc51e2dc73`;
   a private JSON receipt retains row classification and model/material
   examples locally, without uploading asset bytes.
2. Matched baseline/candidate captures remain pending. TOUR28 diagnostics
   and the current ALL ON32 disc are prepared with pinned source/program/
   package hashes; neither is asserted to match a later batching candidate
   observer composition without checking all definitions and assets. The
   intended hardware QA disc must be selected/dialled before capturing the
   requested views. Translucent order, cutout/animated texture behavior,
   moving props/doors, room retirement and normal gameplay remain gates.

Please expose accepted/suppressed headers and each barrier/refusal reason
in the runtime step so the owner can measure actual adjacent-header coverage
instead of using static vertex totals as a benefit estimate.

## Runtime qualification commands

### Implemented behavior and retained boundaries

`STATIC_OBJ_BATCH33` accepts only 0/1 and adds no compiler definition at zero.
Its enabled form requires the existing `STATIC_OBJ_BATCH=1` or `=2`,
`PVR_STREAM=1`, `D349_RENDERER_STACK=1` and `TA_GUARD=0`. The latter diagnostic
assumes that every physical send begins with a header; its incompatible
composition is rejected explicitly. Normal packet and direct paths remain
supported, including landed Build 32's final UV16/UV32 decisions.

The marker is `0xa8` with low bits for single-part, above-16-part and blended
source categories. The existing static classes alone receive it. A compact
run receipt compares all eight final header words, supported packed-colour
polygon format, current frame/list and the physical byte serial. A successful,
nonempty complete strip may certify the following run. Packet completion
checks its actual last EOL word. The direct path uses the existing qualified
actor emitter contract: complete meshlet/strip/triangle output ends with EOL,
and failure aborts before end. It does not read write-only store queues.
Malformed asset acceptance or a universal raster proof is not claimed.

Scene/list/frame/skip/reset/retirement/abort boundaries invalidate the receipt,
as do foreign stream sends, effect body-only packets, Leon/coarse/world direct
headers and custom PT/world packet producers. The latter explicitly clear
the marker even if list mapping keeps the same list. Runtime texture binding
and all existing owner checks still happen before admission. A changed header
retains the original burst; no source arrays or matrices are held for later.

The existing unified deferred FIFO carries the marker through its complete
part snapshot. There is no new translucent queue or reordering. Logical
GC-asset packet auditing retains the original complete packet, while physical
copy/hash/byte accounting reflects the removed header. Existing allocation,
texture pins, direct lock/unlock pairs and per-part work remain unchanged.

`SOB33` prints cumulative counters every **120 drawn UI frames**:
`first/reuse/foreign/format/boundary/header`, `direct/packet`, `op/tr/pt`,
`single/large/blended` seen/reused pairs, `completed/incomplete/empty/barriers`
and `saved` physical bytes. Categories may overlap and count submission
windows, not unique objects. A later aborted scene can still have saved a
header before discard; use clean presented windows with no aborts for gain.
Every reused header removes exactly 32 physical bytes. This does not remove
the old raw-GX `m_obj_split` trigger or its per-part CPU work.

The owner-requested `SOB33B` row at the same cadence separates each barrier
cause: `source` (source reset/retire/invalidate), `deferred`, `frame`
(drawn/skip), `scene` (open/close), `list`, `abort`, `send` (generic stream),
`direct` (foreign direct producer), `custom` (PT/world packet) and `empty`
(zero-count packet commit). These count boundary calls even when the receipt
was already invalid; their sum equals `SOB33 barriers`. They are not counts
of missed batching opportunities. This distinction prevents a busy unrelated
render pass from being mistaken for a lost matching-header run.

### Public correctness evidence

The source-extracted UI oracle executes actual reserve/begin/commit/direct
begin/end, source-view codec, deferred FIFO/drain and new helper code.
Its **392 comparisons** cover direct and packet submission, old scenery batch
0/1 and TA hash 0/1. Old/new runs compare the complete binary sequence of
every effective header and vertex word, return and pin vectors, and logical
GC packets byte for byte. Lock/unlock counts remain balanced and unchanged.

Cases include 12 separate single-part placements, 17/65/257-part infos,
overlapping blended categories, interleaved foreign FIFO packets, all eight
header-word changes, all 256 single-bit header differences, UV formats,
actual custom PT/world/world-cull packet producers, same-list mapping,
texture/material/cull/depth/fog/alpha changes, empty and failed submissions,
non-EOL refusal, abort, scene/list/frame and retirement boundaries. All ten
barrier causes execute and their sum is checked in every case. Texture/KOS/SQ edges and
vertex production are controlled fixture adapters; this is a final-packet
order/state proof, not a private actor transform or console look result.

Normal and ASan/UBSan runs both pass all 392 comparisons. Leak inspection
alone is disabled because the sandbox cannot traverse the required `/proc`
task state; address and undefined-behavior checks remain enabled and fatal.

```sh
python3 -B port/dreamcast/tools/cloud/build33/ui_host.py --output "$OUT/ui-host"
ASAN_OPTIONS=detect_leaks=0 python3 -B port/dreamcast/tools/cloud/build33/ui_host.py \
  --sanitize --output "$OUT/ui-host-san"
```

### Target identity and footprint

Against exact integration `901df96a`, **56 complete preprocessed/object byte
comparisons pass**: two changed TUs, seven profiles, absent/explicit-zero,
both `.ii` and `.o`. Five enabled arms compile and relocatably link. Profiles
cover the release and QA, old batching 0/1/2, byte versus word compare,
TA-hash observation, and landed Build 32's format/cone/UV16 composition.
The combined arm defines/resolves all three existing UV handshake exports.
Eight invalid-value/composition probes reject; all **175 consumed source,
build and helper hashes** remain frozen.

The TA-hash arm disables the existing incompatible `SCENERY_STREAM`
experiment on both sides. It is an observer composition, not the release
performance control. The old-zero profile also disables its existing
`STATIC_OBJ_BATCH_WORDCMP` dependency on both sides. The runner's common
cloud `NMR_POOL_LOD=0` substitution stays out of private release commands.

These deltas sum the two compiled TUs versus each matched OFF composition:

| Profile | Executable delta | Allocated delta | BSS delta |
|---|---:|---:|---:|
| Release / QA / old batching 1 | +2,082 B | +2,581 B | +183 B |
| TA_HASH=1 observer | +2,090 B | +2,589 B | +183 B |
| FORMAT32 + cone 1 + UV16 | +2,094 B | +2,593 B | +183 B |

The bridge contributes 116 B executable/allocated in every arm. Maximum local
compiler frames remain 324 B in `model_bridge` and 7,200 B in `native_ui`;
these are not call-chain stack peaks. The run is 48 B, stats 132 B and flags
3 B. No allocator or retained source storage is added. The cloud gate is TU
compilation and a selected relocatable link, not a full game/overlay/image
build. Exact target reproduction is in [README](../../../tools/cloud/build33/README.md).
Individual hot-call local frames do grow: QA `packet_commit` 8→48 B and
`direct_begin` 48→68 B; `direct_end` remains 12 B. The new send wrapper uses
12 B and the barrier helper 0 B.
Target receipt SHA-256:
`9308f838f6d0fe171ddb90ed395c291708dc9f9ddd50868201711f5b609efc96`.

The final rebase to `14f6ef1e` changed only the queue's owner notes. The
source-equivalence receipt checks every consumed baseline/candidate input
against the completed `901df96a` gate. No compiled input changed. Reproduce
against the final base with `--baseline 14f6ef1ef864682d183e7f8647a06fea514578fe`;
the validated runner retains its original default and source hash.

### Bounded SH-4 cost

The actual compiled receipt helper passes **15 bounded controls** using
Make-derived `native_ui` flags and the established SH-4 interpreter/pipeline
model. Cold-I is an isolated initially cold 8 KiB instruction cache, with
perfect D-cache. Data lines are address footprints, including stack/literals,
not measured fills. These figures exclude diagnostic counters and barriers,
source tagging, UI wrapper work, texture binding, KOS locks, SQ transfers,
geometry, cache misses and GPU work.

| Helper piece | Warm / cold-I cycles | Loads / stores | 32-byte lines | Peak stack with wrapper |
|---|---:|---:|---:|---:|
| First begin | 108 / 207 | 30 / 21 | 8 | 28 B |
| Reuse begin | 145 / 231 | 41 / 10 | 8 | 28 B |
| Late header-word mismatch | 182 / 284 | 50 / 21 | 8 | 28 B |
| Successful completion | 71 / 165 | 22 / 7 | 7 | 16 B |
| Unmarked begin | 49 / 134 | 17 / 10 | 6 | 28 B |
| Unsupported format | 66 / 178 | 20 / 10 | 7 | 28 B |
| 200 compatible three-vertex submissions | 37,653 / 37,885 | 9,002 / 3,837 | 11 | 68 B |

The helper's local begin/finish frames are 16/4 B; wrappers increase the
observed peaks above. The isolated fixture has 1,128 executable, 1,272
allocated and 96 zero-fill bytes, including setup/wrappers. These are not
production image deltas.

**MODELLED whole-frame sensitivity:** 200 compatible submissions suppress
199 headers (**6,368 physical bytes**). At 200 MHz the helper work adds
**0.188265 ms**, taking an assumed 30 ms of other work to **30.188265 ms**
before any benefit from removed transfers. Alternating headers suppress zero
headers and give **30.19724 ms** under the same assumption. This is added
guard cost, not a net performance or FPS prediction. Cold-I cases are not
additive. The unchanged per-part work and added comparisons may outweigh
saved transfers; retain the switch at zero until matched hardware results.

```sh
python3 -B port/dreamcast/tools/cloud/build33/header_cost.py \
  --output "$OUT/header-cost" --sh4-cxx "$SH4_CXX" \
  --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT"
```

The source-bound host/sanitizer and cost receipts are committed in
`tools/cloud/build33`. Final cost receipt SHA-256:
`888ab5440999542c6b8988b36804c890997e507343c179d0b4e26bbcf6bde9b4`.

### Private build and capture

Use the same SDK, private assets, recipe and epoch as the baseline. These
commands build matched control/candidate pairs for the release's existing
lighting policy (`STATIC_OBJ_BATCH=2`) and its centre-independent alternative
(`=1`). No recipe promotion follows from compilation or the synthetic oracle.

```sh
set -euo pipefail
QA=(DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 QA_LINK=1 QA_LINK_REVIEW28=1
    BENCHMARK=0 PMC_ROW=0 WORLD_METER=1 DRAW_FALLBACK_AUDIT=1
    DRAW_SETUP_AUDIT=1 FALLBACK_AUDIT29=1)
build33_arm() {
  local arm=$1 old=$2 batch=$3
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash port/dreamcast/build-public.sh "${QA[@]}" \
    STATIC_OBJ_BATCH="$old" STATIC_OBJ_BATCH_WORDCMP=1 STATIC_OBJ_BATCH33="$batch"
  python3 port/dreamcast/tools/swap-program.py \
    "$GDEMU_ZIP" "$OUT/program-$arm" "$OUT/disc-$arm"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
}
build33_arm release-control 2 0
build33_arm release-batch 2 1
build33_arm exact-control 1 0
build33_arm exact-batch 1 1
```

All disc directories must be fresh. Require complete game/overlay builds,
zero missing symbols and both disc lints. Keep the recipe's private
`NMR_POOL_LOD` setting. Do not compare `exact-batch` to `release-control` as
the new switch's performance gain: that also changes the old lighting policy.

For each arm, boot its disc, establish REMOTE LINK and repeat the same view:

```sh
ARM=release-batch
VIEW=barn-props
ql() {
  python3 port/dreamcast/tools/qalink/qalink.py --pi "$QALINK_PI" --review28 \
    --out "$OUT/capture/$ARM" "$@"
}
ql status
ql send MENU
ql capture start "$VIEW"
ql send RESUME
read -r -p 'Run the matched view for at least 300 drawn frames, then press Enter: '
ql send MENU
ql send DIAG
ql capture stop "$VIEW"
```

Require nonzero saved headers in the relevant classes before treating the
comparison as coverage. Retain the new batch counters with DFA/DSA and
WORLD_METER deltas, physical PVR bytes, CPU/frame/GPU times and captured drawn
frame counts. Compare the old and new run at identical state for each
lighting policy. Expected changed transport output is only redundant header
bursts; vertex data, effective polygon state and primitive order must agree.
Raw TA hashes will change when headers disappear, so a raw hash mismatch is
not a geometry oracle. Inspect effective-header/vertex traces and overlapping
translucent props/effects. Require moving doors/props, cutouts, texture/alpha
animation, near clipping, room leave/reload, headroom and normal STRICT route
acceptance. A smaller byte count alone is not a frame-time improvement.

For complete OFF image identity, build exact integration and candidate trees
with identical assets, SDK, recipe and epoch, without QA overrides:

```sh
BASE_TREE=/absolute/checkout/of/14f6ef1ef864682d183e7f8647a06fea514578fe
git -C "$BASE_TREE" submodule update --init -- port/dreamcast/game/third_party/sh4zam
identity33() {
  local tree=$1 arm=$2
  shift 2
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash "$tree/port/dreamcast/build-public.sh" "$@"
  python3 port/dreamcast/tools/swap-program.py \
    "$GDEMU_ZIP" "$OUT/program-$arm" "$OUT/disc-$arm"
}
identity33 "$BASE_TREE" identity-base
identity33 "$PWD" identity-absent
identity33 "$PWD" identity-zero STATIC_OBJ_BATCH33=0
python3 - "$OUT" <<'PY'
from pathlib import Path
import hashlib, shlex, sys
root=Path(sys.argv[1])
def manifest(arm):
    path=root/('disc-'+arm)
    names={'disc.gdi'}|{shlex.split(line)[4] for line in (path/'disc.gdi').read_text().splitlines()[1:] if line.strip()}
    result={}
    for name in sorted(names):
        digest=hashlib.sha256()
        with (path/name).open('rb') as stream:
            for block in iter(lambda:stream.read(1<<20),b''):digest.update(block)
        result[name]=digest.hexdigest()
    return result
base=manifest('identity-base')
for arm in ('identity-absent','identity-zero'):
    assert manifest(arm)==base,arm
print('PASS complete GDI/track identity: baseline = absent = zero')
PY
```

## Owner runtime landing, 2026-10-28

Runtime `59abed5a3` merged clean as `36643bf8a`, default 0. The local actual
UI order oracle passes 392 comparisons in both normal and ASan/UBSan runs
(leak detection disabled), including the counters/barrier sum. Receipts are
retained in private `cloud33-host-20261028-1858`. The release recipe builds
rc=0/missing=0; ELF SHA-256
`57cf3dd76e07fde48cf903562bb4b9d3ba3458dcc19e3609aa8b5758c5c59b7f`.
The cloud's 56 target-byte comparisons were not rerun locally; full absent/
zero repacked-image identity is a distinct pending gate.

The switch is added to ALL ON alongside the guarded actor-format and part
plan candidates. ALL ON33 from this integration is prepared with QA_LINK=1;
QA build, loader/standard disc lint and ZIP integrity pass. The prior ALL ON
discs remain preserved, no SD write or recipe promotion. Next local smoke
will report actual SOB33 reused/saved bytes and SOB33B barriers, separately
from unchanged old m_obj_split and static vertex totals. Zero reuse is not
a performance PASS. Net benefit still needs matched presented windows and
hardware CPU/frame/GPU evidence; byte reduction alone is not acceptance.

Private overlap/cutout/animated texture, moving props/doors, retirement,
gameplay/STRICT and memory/stack gates remain pending. The earlier four
weapon inventory/door results were on ALL ON81028934c, before actor formats
and this header batching, and do not qualify the newer combined candidate.
