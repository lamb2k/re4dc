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

### Answers (owner): combined actual-data smoke, 2026-10-28

The owner ran one bounded 60-second cache-interpreter/GDEMU-seed1 private
r105 case on full paired ALL ON33 programme/overlays `36643bf8a`, with
QA_LINK=1. The fixture arms Thompson0x34 and opens/closes inventory using
game-side input; no host keys. Original assets remain from the preserved
ALL ON31 extraction; twin mastering checks1648 unchanged files,19 permitted
programme/overlay/fixture differences,0 disallowed. This is a fixture image,
separate from the prepared unmodified console stage `4973e78a`.

Reader exit0, errors empty, overruns0, owned process exited. SSCERT restored1
and subscreen backing hashOK; gameplay continued, not full byte-restore proof.
WPLAN29 f480 planned6720/legacy0, loads1/declines0, bytes17215. AF32UV f360
admitted10206/12861, declined2655 (legacy2295/source360); binding/precision/
nonfinite/begin0, scanned1550281 records. AC32C f1354 tested11927/rejected2555,
near/numeric0. These are actual admissions/refusals, not measured frame gains.

SOB33 f480 cumulative reuse201/saved6432 bytes, completed462/incomplete0,
single346/172, large0/0 and blended0/0. SOB33B barriers55469 with source339,
deferred655,frame482,scene960,list340,send37676,direct15017, other causes0.
Large/blended coverage is absent. The old split counts/441k static vertices
are not removed work. No matched OFF arm or CPU-cost/net timing claim.

Private receipt: owner-allon33-smoke-20261028/RESULTS.json and RESULTS.md,
with exact run/log hashes and raw counters retained locally. Next independent
work is a controlled OFF arm and effective-header/vertex/order traces, then
bounded near/translucent/large/moving-door/retirement cases. Mode2, look,
STRICT, stack/memory, complete absent/zero repacked identity and matched
hardware whole-frame acceptance remain pending. Portal remains parked for
its separate compatible profile and real authored WP29 cells.

Console prerequisite: user selects intended QA disc and establishes REMOTE
LINK; barn baseline comparison is slot154 ALL ON DIAG versus151 baseline,
with matching camera/state and300+ drawn-frame windows. Existing HouseWhole27
Pi benchmark rows are from another earlier session and exact loaded-program
identity remains unresolved; they do not qualify this candidate. No SD write,
recipe enablement or publication.

### Answers (owner): controlled OFF follow-up, 2026-10-28

Pinned36643bf8a control compiled rc0/missing0 with full paired overlays.
After normalizing owned source/output paths, the complete resolved settings
differ only STATIC_OBJ_BATCH33=1/0; same ALL ON33 QA flags, assets and fixture.
OFF ELF prefixd42aa3935fa2f82f; exact digest retained locally. Twin mastering
checks1648 unchanged/19 permitted/0 disallowed files. This does not substitute
for historical absent/zero complete repacked-image identity.

Both60-second r105/Thompson0x34 cache-interpreter/GDEMU-seed1 arms open/close
inventory and return to gameplay, SSCERT restored1/backing hashOK and
WPLAN6720/legacy0, reader0/errors empty/overruns0, owned emulators exited.
The late gameplay windows both cap at29.9FPS; no speed or hardware benefit
claimed. Private result/log hashes and raw windows retained in
owner-allon33-off-20261028/RESULTS.json and RESULTS.md.

Existing TA_HASH transport hashes change under intentional header removal;
mode3 only drops empty headers and mode4 is hardware count-only, so these
are not an actual-data effective-header/vertex oracle. Some observer guards
also alter producer paths. That gate remains distinct from the392-case UI
host oracle and the current functional smoke. Next: reviewed actual transport
capture/effective-state normalization with aligned source tick/camera/pose,
large/blended/near/moving-door/retirement cases, then look/STRICT/memory,
full-image identity and matched whole-frame console qualification. No SD
write, recipe promotion or publication.

### Answers (owner): current combined-build door and UI samples

On source36643bf8a, both STATIC_OBJ_BATCH33=1/0 actual Thompson r105->r101
source-button door cases pass, freeze released and normal gameplay continuing;
WPLAN reopens r101 with loads2/declines0. Each bounded60s cache-interpreter/
GDEMU1 run ends reader0/errors empty/overruns0, owned emulator exited. This
advances room-retirement/reload coverage, not full-route/movie/STRICT or heap.
Two extra60s UI-capture runs also finish clean with3 asynchronous samples and
both buffers per arm. Reviewed inventory equipment/Leon are present, but
animation/top-label/selection phases differ and no exact source-tick alignment
exists. No broad look/effective-state equivalence PASS, post-close world-image
proof or speed claim. Private hashes and scope: owner-allon33-off-20261028/
FOLLOWUPS.json and FOLLOWUPS.md. No new Flycast observer/build or exactness
lane introduced; owner continues encounter/look and current cloud fixes.

### Answers (owner): bounded r100 house class coverage

New view on preserved36643bf8a full programme/overlay twins, QA_LINK1;
independent resolved delta only STATIC_OBJ_BATCH33=1/0 rechecked before
launch. Existing source benchmark-r100house fixture identical per arm,
SHA256 ee7841c24b7864babd0860555df09ec2ff6ef35a6627867dfec1ef119f6286f5.
Each60s cache-interpreter/GDEMU1 runner complete/reader0/errors empty/
owned process exited. No new source/build/data change. Actual counters:

- off: overruns0=True, OOM/MISSING/HALT lines=0, last complete single/large/blended classes=not logged (OFF expected absent), reuse=not logged, cumulative saved bytes=not logged.
- on: overruns0=True, OOM/MISSING/HALT lines=0, last complete single/large/blended classes={'single': [0, 0], 'large': [0, 0], 'blended': [0, 0]}, reuse=0, cumulative saved bytes=0.

Class pairs are seen/reused (category_seen/category_reused), not vertices.
These are bounded functional/counter observations, not a measured gain or
full acceptance. Any zero class remains uncovered, and OFF's absent
batching counters do not mean zero source workload. Static counts are not
proof of a live bridge class. Actual effective-header/vertex oracle,
aligned look/STRICT/gameplay, memory/stack, full-image identity and matched
whole-frame console gates remain pending. Private exact receipts in
owner-allon33-off-20261028/HOUSE-PROOF.json and HOUSE-RESULTS.json+md.
No bespoke observer, SD copy, recipe promotion or publication.

### Answers (owner): source-bound class and placement selection

Read-only audit pinned36643bf8a clarifies the next actual-data gate.
static_obj_batch33.hpp marks only kind0 IDs41/43/45/46 and kind1 ID21;
em.cpp constructors identify the four kind0 classes as door/box/rack/window.
The bridge marker uses ModelData displist_num (single1/large>16) and live
info blend_mode; Scan29's broad m_obj_split totals cannot establish that a
placed model reaches this marked submit path. Ordinary room geometry is
outside this marker set. The kind1/21 initializer is indirect; no asset
name or live class coverage is inferred for it.

EtcModelSet maps etc IDs52/53 to window variants13/14; emwindow.cpp sets
blend_mode2 for those variants, and et00.cpp names et5200/et5300.bin.
The window variant is the loader's flag argument, not the ETS slot byte.

The preserved master extraction's 29 primary DAR payloads parsed 460 ETS records, zero parser errors, and no etc52/53 placements.
This is a narrow negative placement inventory: other DAR payloads/room
blocks, runtime-created models and other ways to set blend_mode were not
excluded. It neither certifies blended coverage nor proves no blended work.
All source/helper and DAR hashes, placements/coordinates and parser scope
remain private in owner-allon33-off-20261028/PLACEMENT-AUDIT.json.

Next: bind an eligible actual model's displist count/material and live
placement/caller before a new bounded large/blended capture. Do not repeat
the zero-coverage house view or manufacture a game-data admission from a
host fixture. Prior392-case host oracle, current actual-data order/look/
STRICT/memory/full-image and whole-frame console gates remain distinct.
No source/build, private-asset change, SD write, promotion or publication.

### Answers (owner): constructor-to-named-model cross-check

Read-only source36643bf8a constructor map covers77 ETC IDs and79 literal
primary/alternate BIN names for the marked kind0 door/box/rack/window
families. In the already bounded primary-DAR placement inventory it maps
38 doors,197 boxes,15 racks and39 windows. Positions remain private; these
are source/placement links, not live model or render admission counters.

Case-insensitive cross-check against the older Scan29 by-model m_obj_split
candidate snapshot matches15 named models/178 rows; all178 report one part,
so that matched subset provides no above16-part target. The other64 named
BINs are not classified by this match. The snapshot may omit/incompletely
parse models, includes old asset bindings and repeated archive sources;
these totals are not unique live objects or proof large classes are absent.
Actual current ModelData displist_num/material and live bridge binding
remain pending. The indirect kind1/21 path is still separately unmapped.

Private exact mapping, snapshot SHA, placements and negative selection are
retained in owner-allon33-off-20261028/MODEL-MAP-AUDIT.json. No speculative
large/blended view, data injection, repeated zero-coverage house run or new
observer is launched. Existing host392-case oracle,56 target comparisons,
full absent/zero repacked-image identity and actual-data look/STRICT/
memory/net console qualification remain separate gates. The public target
helper's two-TU/relocatable matrix is explicitly not a full image test.
No source/build, private-asset change, SD write, promotion or publication.

### Answers (owner): complete release-profile OFF payload identity

Baseline14f6ef1 is the actual36643bf8a merge first parent. Compared complete
release rP baseline with candidate absent and explicit STATIC_OBJ_BATCH33=0,
same recipe blob16c25cb6/assets/SDK/epoch. Fresh baseline/0 builds pass
rc0/missing0; preserved absent output checked, all15 overlays present.
This uses the actual private recipe, not the2-TU validation matrix override.

All three3372036-byte executable programmes SHA256
fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1
and complete15-overlay sets match exactly. Allocated ELF section addresses,
sizes/types/flags/content match. Whole ELF files differ; differing section
payloads are.debug_abbrev/.debug_info/.debug_line/.debug_line_str, so no
full ELF byte identity is claimed. The raw programme extraction uses a
seekable file and asserts nonempty bytes; an earlier stdout probe returning
empty data was discarded before comparison, not used as an identity proof.

Fresh independently mastered ext4 bases use the same original extraction/
manifest/IP and unchanged existing fp_master/fp_iso helpers, cache DISABLED.
Each1648 original files unchanged/19 permitted/0disallowed. Across baseline
versus absent and versus0: all1667 ISO file payloads identical, zero differs.
Three inert full-play fixture files exist in each arm; this is exact complete
file-payload identity on fixture bases, not public-disc acceptance.

Raw track02 is identical. Raw track01-template and track03 are NOT identical;
track03 differing-byte counts7227(absent)/9533(zero). Mastering metadata/
layout localization remains pending, no raw byte normalization/cache-hit
PASS or full raw-image identity claim. No same-input rebuild/remaster is
needed to inspect these retained differences. Private full hashes/offsets/
resolved/build/manifest receipts: owner-allon33-off-20261028/
OFF-IDENTITY-BUILDS.json and OFF-IDENTITY-IMAGES.json+md; ext4 originals/
programmes/masters in owner-batch33-offid-20261028.

Enabled large/blended live coverage, actual effective-header/vertex oracle,
look/STRICT/current memory/stack/full-route and net whole-frame hardware
gates remain pending. No source change, SD copy, promotion or publication.

### Answers (owner): raw ISO timestamp localization

Read-only analysis of retained masters classifies every difference as
timestamp metadata, zero unclassified bytes. Primary/Joliet file/directory
extents, sizes and entry classes match. Track01-template differs17 timestamp
bytes per candidate. Track03 absent/zero differs7227/9533 bytes, entirely
volume/root/directory dates and Rock Ridge modified/accessed/attribute-change
times. No inode-serial field differs. Field interpretation cross-checked
against the primary libarchive ISO9660 reader implementation:
https://raw.githubusercontent.com/libarchive/libarchive/master/libarchive/archive_read_support_format_iso9660.c

All1667 FINAL file payloads per arm also match the existing manifest after
following the3 redirected fixture entries into track01. No source or image
was patched, normalized or remastered to reach this result. Literal raw
hashes remain different; no raw-byte identity claim. Exact release programme/
all15 overlays/allocated ELF sections/file-payload identity is established;
the prior raw difference is now explained as packaging-time variation.
Full ELF files remain different in recorded nonallocated.debug payloads.

Private exact offsets/categories/counts/layout/helper/source receipts:
owner-allon33-off-20261028/OFF-IDENTITY-METADATA.json+md. No reason to repeat
identical OFF builds/masters. Enabled large/blended/live order/look/STRICT/
current memory/full-route and matched whole-frame console gates remain
separate and pending; no recipe/SD/release change or new acceptance.


## EF05 first consumed lifetime slice, 2026-10-29

**DONE (source + host):** `STATIC_OBJ_LIFETIME05=1` retains the SOB heap
generation and allocation incarnation outside its room-cell `State`. The
existing room API validates heap generation, active handle, range, alignment,
exact extent and cell header before the new query reads its token. Both
ordinary/high room allocation publishers assign the next nonzero token in
existing `Room4Cell::reserved[0]`; no cell-layout change. Tokens never recycle;
counter exhaustion publishes zero and refuses retained reuse while ordinary
allocation/gameplay continue. An unbound fresh SOB cell is returned safely.
The control defaults to zero and leaves Build33 final-header coalescing intact.

`take` checks on every call, including an unchanged frame counter. `flush`
validates before touching State, snapshots pending record/lighting off the room
cell, and rechecks heap/token before every raw-source submission. A split flush
cannot append into a replacement State after reentry. Leave validates, detaches
all global/pending references, then frees only the matching live allocation.
No stale State is read to find its own identity.

Source extents/content-generation authority is not yet supplied by the recovered
model parser. The enabled slice therefore refuses persistent merged-copy reuse
and emits the current raw lists through the existing model consumer. Pointer,
total-size and first-eight-byte matching is retained only in the unchanged OFF
path. This may lose the old merged-list speed benefit; it is a correctness
slice, not a measured optimization or a promotion of mode2 lighting behavior.

Run synthetic, production-body boundaries with fresh output directories:

```sh
python3 -B port/dreamcast/tools/cloud/build33/lifetime05_host.py --output "$OUT/host"
python3 -B port/dreamcast/tools/cloud/build33/lifetime05_host.py --output "$OUT/sanitizer" --sanitize
```

Both normal and ASan/UBSan runs pass ten groups: range/epoch refusal; same-frame
reset/reused address/pending discard; invalid heap handle; same-generation
allocation reuse/stale leave; reset without leave/stale flush; OOM/refusal and
reset during allocation publication; retirement during submit; split-flush
reentry; changed byte12 in raw emitted output; token exhaustion with normal
allocations still usable and refused SOB allocation returned. The fixture
extracts the actual SOB and ordinary room alloc/free/liveness/validation/token
functions, using synthetic source records and controlled allocation/submission
edges. Retired heap storage is protected with `PROT_NONE`. High allocation
publication is source-inspected but not executed by this host allocator.
Sanitizers run with leak detection disabled. Source-bound public receipts:
`tools/cloud/build33/receipts/lifetime05-{host,sanitizer}.json`.

**NEXT:** target release absent/explicit-zero/enabled builds and complete
disabled programme/overlay/allocated-section identity; source extent/content
authority before restoring copied-cache hits; then effective output, loading
overlap, stack/headroom and setup/whole-frame cost on bound actual inputs.
Coordinator serializes SDK builds and owns integration. No SDK/Flycast/disc,
publication, SD or Pi action has been performed for this slice yet.

**Remaining EF05 sub-slice:** source inspection finds the same pre-validation
pattern in diagnostic `sobdump::frame/ensure` (`SOB_DUMP`) and static-bake
`re4dc_sob_bake_frame/decide/room_leave/skip` (`STATIC_OBJ_BAKE`, requiring
`PS2_PLACE_GATE`). These are explicitly outside this first bounded SOB commit
per coordinator scope. They need the same out-of-band identity and fixtures
for their serialization/rest-copy and placement-callback consumers, including
allocation/prepare callback reentry. The new knob does not certify them safe.

**BLOCKED only at acceptance:** actual source ownership, bound actual-data
look/gameplay/STRICT/current memory and whole-frame hardware gates remain open.
Host success is not target execution, full EF05 completion or a speed claim.
Existing earlier Build33 receipts retain their exact scope.


### EF05 target/OFF gate, 2026-10-29

**DONE (IMPLEMENTED + TARGET BUILD VALIDATED, first SOB slice only):** local
source commit `5905089fddff31f11fa194b7faa7512d34eb7dae` passes fresh full
release builds with the control absent, explicit zero and one. All actual
build logs and nonempty ELF files exist; each `missing.txt` exists and is empty.
Compiler15.2.0, KOS804b3195 and pinned sh4zam33fa4850; release recipe SHA256
`66940fea7531fd3a402dc8fc6f779d7861801c0cd39a4c91be31f7f0871816c0`.
The independently built shared control is source9ee386e3. After normalizing
only owned worktree/output paths, every resolved definition agrees except the
new `STATIC_OBJ_LIFETIME05` declaration (absent on control,0/0/1 on the arms).

Control/absent/zero have identical complete3372036-byte programmes, SHA256
`fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1`;
all15 overlays and all11 allocated ELF sections agree, including addresses,
sizes, types, flags, alignment and file-backed content. Both changed objects
(`model_bridge.o`, `ui_bridge.o`) also match allocated sections for absent and
zero. Whole ELF files differ; no whole-ELF or raw-disc byte identity is claimed.

Enabled ELF SHA256
`07eaeecf7d6c201c5becedecf4203ba8f03a1e259b634931a5f4b8b628cbb0a2`.
Its new counter symbol is4 bytes and out-of-band owner12 bytes; linked BSS is
32 bytes larger after alignment. Linked `.text` is192 bytes smaller because
the unsafe retained-copy find/build path is excluded. These are section/symbol
sizes, not peak heap, stack or timing results. The room-cell header and SOB
State layout are unchanged; no copied-cache or loading-overlap saving is
certified. Unknown source content still takes the raw path.

Exact reproduction uses the current release recipe and bound private inputs,
one fresh label per arm, and a separate programme directory with the shared
registry disabled:

```sh
source <(sed 's/\r$//' "$TREE/port/dreamcast/tools/d367/rr/recipe.conf")
# Repeat with EXTRA unset, STATIC_OBJ_LIFETIME05=0, then =1; unique LP each time.
K="$LOGS" T="$TREE" LP="$FRESH_LABEL" CH2="$CH2 ${EXTRA:-}" \
  ROUTE_PROGRAMS_DIR="$PROGRAMS" ROUTE_PROGRAMS_JSON='' \
  bash "$TREE/port/dreamcast/tools/d367/ch2/ch2-build.sh" rP
```

The owner checks fresh output paths before invoking this existing recipe,
which otherwise removes a same-label output. SDK job finished and build slot
returned; no live PID/session remains. Private exact builds, hashes, resolved
settings, actual logs and both comparison receipts are retained in the owner's
`engine-ef05-target-20261029` evidence. OFF receipt SHA256
`ee870177c618e4c673c5a026b555bef65192f7101167f0b1d6e1e5b368eb4b74`;
target bindings/object/footprint receipt SHA256
`ec1be99e2dd724b83836d53dfe1bcc023f46c61db35991b220e99431a9767022`.

**NEXT:** integrate default-off only through the coordinator's prescribed
fresh-base process, then continue parser-bound source extents/content identity
and the explicitly deferred sobdump/sobake lifetime sub-slice above. Reuse of
copied source content remains disabled in the new arm until authority exists.
**BLOCKED at actual-data acceptance only:** effective emitted order/output,
current gameplay/STRICT/look, stack/headroom/loading overlap and total hardware
cost remain distinct pending gates. No target execution, emulator, mastering,
publication, SD/Pi action, recipe promotion or full EF05 completion is claimed.


## Answers (owner): 2026-10-29 combined engine integration

DONE: `STATIC_OBJ_LIFETIME05` first slice merged default off with the other three bounded fixes into `77461a84ef85e978e44aab5d936a1b80a2cd93a4`, using four clean no-ff local integrations from `9e6662c36`. Combined release rc0, missing.txt present/empty; ELF SHA256 `49f12668242e722acfa0fee89514323c4aa7892e64014dcb970eb0473fbee0c3`. All four controls resolve zero; complete programme, all15 overlays and all allocated ELF section metadata/payloads match the bound9ee baseline. Fresh-base check and origin-only push/readback passed. A queue-row selection preflight stopped before the first build, then continued in the same clean merged candidate; no source conflict or failed build was hand-resolved.

ALL ON K includes the four new controls. Fresh ALL ON QA at source77461a84, with QA_LINK=1 and all four controls resolved1, passed compile, existing empty missing.txt, loader/standard disc lint with zero violations, ZIP test and staged checksums. Track03 is1,185,760,800 bytes, SHA256 `e70b865a2f55469f2c279094e3a9a86d4576efe22869da0d76f8e464be902c62`. This is a prepared private QA artifact, not a runtime/look/STRICT/memory/timing or physical-console acceptance result. Nothing was copied to SD.

NEXT/BLOCKED: retain this card's exact remaining source sub-slices and runtime/lifetime/look/current-memory/console gates. A first slice does not close the entire EF card. Use the verified image only for an explicitly selected compatible next check, with exact build/assets/scene/window and valid denominator. The user must select/swap intended verified media and establish reviewed link readiness where a console check requires it; current media/Pi/release holds remain. Independent EF02 producer, EF07 owner-scoped plan and EF08 producer-completion work proceeds from the integrated source. No default or frozen-release recipe promotion.
