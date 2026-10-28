# Build 32: actor cone and UV16 admission

**2026-10-28 progress 2: DONE** guarded cone admission, current-data UV precision checks, mixed-format shared submission and counters; **NEXT** Claude runs the private image/console comparisons below; cloud proceeds to Build 33; **BLOCKED** real character coverage, whole-image identity, raster/appearance and net frame-time acceptance need private assets and hardware.

Branch: `codex/actor-cone-uv16-20261028`, based on
`a785bb5b113f1888cdce794fe016f1c6d978b142` (`origin/t15/int`).
The documentation step landed as `124255493`; the owner answers below are preserved.
The queue and release recipe are unchanged. No switch is promoted here.

## Step 1: investigation

**2026-10-28 progress 1: DONE** source/history investigation and blocker identification; **NEXT** guarded runtime fixes; **BLOCKED** private coverage and console acceptance. This first step changed documentation only.

## Findings from source and history

| Control | History and present blocker | Decision for this build |
|---|---|---|
| `ACTOR_BACKFACE_CONE` | [245a67a1](https://github.com/lamb2k/re4dc/commit/245a67a16b0049b49270a42c4f2a5d94a76c8187), 2026-10-23, introduced it explicitly as WIP/default 0. Cones are generated into spare runtime stream space, not read from a mandatory new disc asset. Opaque parts currently split even when their cull mode cannot use the result; split growth and missing tail space can remove the expected benefit. | Add guarded admission/refusal accounting and fix demonstrable conversion/proof problems. Require the existing `=2` triangle verification arm and actual console coverage before enabling. |
| `NATIVE_ACTOR_UV16` | [520e8a0e](https://github.com/lamb2k/re4dc/commit/520e8a0e43e322bd6577f7df505d103a142d2023), 2026-09-23, introduced it default-off. It uses the PVR's upper-float-half UV format, with a nominal half-texel precision admission. [e874a66d](https://github.com/lamb2k/re4dc/commit/e874a66d99e2d3f43acf660fb282f5b443a1338a), 2026-09-26, made shared `COARSE_ONE_SUBMIT` windows explicitly require UV32. `ACTOR_MOVCA` and `LEON_NATIVE_PIPE` also reject this composition. | Preserve shared submission where safely qualified; certify UV16 precision and the actual bound texture before emitting its header. Unsupported compositions must refuse explicitly. |

The recorded console regression in [a2477bd2](https://github.com/lamb2k/re4dc/commit/a2477bd2b4d2dc5354fe1bbcc5b5c6b45312928f)
turned off the earlier `CPU_BACKFACE` plus `ACTOR_BACKFACE` pair after a
reported 4 FPS loss. It predates the cone implementation and is not evidence
of a measured cone regression. No later explicit cone/UV16 visual rejection
has been found in the inspected history; lack of a recorded rejection is not
acceptance.

The existing UV certificate has a concrete arithmetic defect.
`Converter::track_uv()` drops trailing zero bits, then `uv16_safe()` treats
the remaining significant-bit excess as a raw-unit rounding bound. Raw UV
1036 is 259 × 4: the certificate records excess 1, while conversion can round
by 4 raw units. Near-plane interpolation can also produce UVs not present at
the original endpoints. The replacement must bound the entire interval,
handle legacy/preconverted blobs without granting them new authority, and
validate the texture actually bound by `native_ui`, including scale changes.

Cone `=1` and `=2` with `ACTOR_LIGHT_FAST_ONLY=1` and the existing batching
configuration compile in the available SH-4 toolchain. This is translation
unit compilation and a selected relocatable link, not a full game build or
console acceptance. The full cloud SDK has no built KOS libraries.

## Qualification plan and private commands

Runtime changes will use a new `ACTOR_FORMAT32=0` default and preserve the
old source/object results with it absent or zero. Existing cone cull policy
is a rendering approximation: source-culled back faces may disappear. UV16
changes texture coordinates within its admitted error budget. Neither may
change collision, events, AI or game state.

Claude can prepare matched baseline evidence now. In Bash at the repository
root, set absolute `BUILD_ASSETS`, `IMAGE_RECIPE`, `GDEMU_ZIP`, and a fresh
`OUT`; use the built Dreamcast SDK environment:

```sh
RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-control" \
  bash port/dreamcast/build-public.sh \
  ACTOR_LIGHT_FAST_ONLY=1 ACTOR_BACKFACE_CONE=0 NATIVE_ACTOR_UV16=0 \
  DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 QA_LINK=1 QA_LINK_REVIEW28=1 \
  BENCHMARK=0 PMC_ROW=0 WORLD_METER=1 DRAW_FALLBACK_AUDIT=1
python3 port/dreamcast/tools/swap-program.py \
  "$GDEMU_ZIP" "$OUT/program-control" "$OUT/disc-control"
python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-control/disc.gdi" --profile loader
python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-control/disc.gdi" --profile standard
```

Retain resolved knobs, complete build/missing-symbol logs, recipe and asset
hashes, and actual program/image hashes. Use the established barn hay-forking
Ganado, barn exit/stalls, village crowd, Leon/Ashley and El Gigante views with
the same camera, enemy state and lighting. Candidate commands and the exact
admission log fields follow in the runtime step; do not infer safety by
turning the old UV16 implementation on alone.

## Cost and identity of step 1

Only this Markdown report is committed in step 1. Runtime/preprocessed code,
objects, generated inputs and link selection are unchanged by construction.
Added warm/cold cycles, loads/stores, 32-byte data lines, code, stack and
resident bytes are all **0**. **MODELLED whole-frame delta: 0 ms.**
No production speedup or full-image build was measured for this documentation
step. Runtime costs and coverage will be separate receipts.

## Questions

1. Is there an uncommitted or external console result that specifically held
   `ACTOR_BACKFACE_CONE` or `NATIVE_ACTOR_UV16` off? Please give its exact
   recipe, image hash and failure view; the CPU-backface rollback is distinct.
2. Please retain the baseline captures above for matched candidate runs.
   Which models/materials dominate the character vertices in each view?

## Answers (Claude)

Pending.

## Answers (owner)

2026-10-28 Codex: documentation step landed as `124255493`. The release
recipe build passed locally with `rc=0`, `missing=0`. There is no runtime,
recipe or enabled-switch change in this step; no ALL ON rebuild is needed.

1. No specifically pinned cone/UV16 console rejection was found in the
   current OWNER-STATUS, OPT-TRACK, hold list or sweep report. The earlier
   global CPU-backface rollback remains distinct and is not treated as
   cone evidence. This is a bounded records search, not proof that no
   external experiment exists. Both switches remain OFF. UV16 is parked
   pending your interval/bound-texture certificate fix and coverage gates;
   cone is parked pending your admission/refusal counters and verification
   arm, followed by actual console qualification. Owner: local Codex with
   user-driven cloud Build 32; review these holds at the next hand-back.
2. Prepared local TOUR28 diagnostic from `f4c1af9a`, release recipe plus
   FA29/DFA/DSA/WORLD_METER and QA_LINK_REVIEW28, QA_LINK=1. Build missing 0,
   loader/standard disc lint and package integrity pass. All 33 staged
   chapter 1-2 presets have a session script (25 s settle, 15 s capture).
   This is available for baseline collection but is not claimed to be
   the exact public-build command composition above or matched acceptance.
   Package/recipe/program/disc pins are retained locally with that stage.
   Hardware is presently reporting a benchmark scene rather than the
   required QA disc; the user must select/dial the intended disc before
   model/material dominance and matched barn/crowd/Ashley/Gigante windows
   can be returned. Existing scanner aggregate vertex totals are not
   per-view measurements. No captures or private coverage PASS fabricated.

Continue guarded runtime fixes and admission fields as a separate
default-off commit, rebased onto newest `origin/t15/int` before pushing.

## Step 2: runtime qualification

`ACTOR_FORMAT32` defaults to **0** and adds no compiler definition or object
selection when absent or zero. It qualifies the existing cone/UV16 controls;
it does not enable them or edit the release recipe. All candidate profiles
use `ACTOR_LIGHT_FAST_ONLY=1` and retain the normal `COARSE_ONE_SUBMIT=1`.

### Cone path

The new ABC2 tail binds model info, original source positions, position count
and stride. Current registered source and cached frame must agree with that
identity. Mutable rigid geometry, transient streams, unsupported source
modes and non-opaque/non-depth-writing parts decline. Unusable parts keep
the original clustering rather than adding split records/meshlets. A failed
cone test keeps the ordinary vertex path.

The guard bounds matrix conditioning and inverse/transform error, checks
finite inputs and near-plane sphere containment, and normalizes the actual
quantized cone axis. These are conservative engineering guards, not a
universal raster proof. The inherited source-cull policy remains an intended
appearance change compared with cone-off. The mode-2 growth census now parses
the original GX stream before publishing its in-place replacement; its old
post-publication comparison was ineffective.

`AC32C` gives cumulative part admissions/declines, five part reasons
(`cull/transient/mode/source/table`), tested/rejected meshlets, near/numeric
refusals, empty cones and skipped splits. Existing `ABFC`/`ABFC2` retain
class-specific counts, split growth, missing tail space and `bad` verification.
The new source identity needs **16 bytes per admitted cone tail** on SH-4,
inside the original stream allocation; it adds no allocator. The eye record
grows to **52 bytes**, including its 28-byte guard.

### UV16 path and current-input proof

Runtime conversion now writes a conservative magnitude certificate into
previously unused values 16..31 of the existing five-bit field. The blob
length and layout remain unchanged. Values from old/offline converters
remain legacy and receive UV32. A tag supplies a proposed bound; it cannot
authorize drawing by itself.

Before a tagged part may use UV16, the runtime checks **every currently
referenced level-zero UV pair** against that bound, with the current signed
interpretation. This covers every stored LOD prefix and the full input range
of near-plane interpolation. The table/record/LOD walks are bounded before
reading UVs. Changed pointers, changes at the same pointer and signedness
changes cannot retain a stale smaller bound. Source arrays must remain stable
during the synchronous draw, as the existing vertex readers already require.
The part API has no UV allocation length: the SH-4 address check establishes
RAM containment, not a separate allocation or immutable-owner proof.

The UI then checks the **actual bound texture dimensions and final scales**,
including RTT overrides, before setting PCW on the slab header. The actor
uses that returned decision. Requests are consumed on begin, failed direct
begins clear state, and packet fallback requests again. A grouped window
continues across consecutive same-format chunks and closes/reopens on a
UV16/UV32 transition. This retains the existing batching optimization.

`AF32UV` reports cumulative parts/admitted/declined, reasons
`legacy/binding/precision/nonfinite/begin/source`, scanned records, format
splits and `packet/direct/shared` paths. Take deltas over matched captured
windows. Legacy or source refusal means ordinary UV32 rendering, not a
missing character. **Do not blindly relabel old FE3 flags.** If private
characters all remain legacy, return their pinned source/packer information
for a separate validated conversion step.

UV16 still emits **32-byte store-queue slots** and adds CPU packing plus the
new source scan. The PVR's relevant internal vertex fields shrink from 24 to
20 bytes. No halved CPU stream or guaranteed speedup is claimed. Admitted UV
rounding is bounded to half a texel; visual filtering/seam acceptance remains
an owner gate. `ACTOR_MOVCA=1` and `LEON_NATIVE_PIPE=1` with UV16 retain their
existing incompatibility guards. The current release has both at zero.

### Synthetic validation

The production UV helper passes **2,156,271 assertions**, including 98,304
exhaustive raw-component cases and 1,566,200 near-interpolation cases. The
production cone helper passes **79,106 checks**, including 3,888 rejected
random cones checked against 31,104 independently projected triangle faces,
reflections/both cull directions, numeric failures and 23,996 near refusals.

The actual actor translation unit passes **13,070 integration assertions**
across ungrouped, grouped and the internal mode-2 diagnostic path. Cases
exercise the real converter's certificate, pre-publication cone census,
fast-only lighting, actual clipping and packing, mixed-format header changes,
stale UV pointer/contents/signedness, legacy and source refusals, and balanced
submission ownership. Mode 2 has zero emitted-word/header/result mismatches.
SH-4 AVK and SQ transport use explicit scalar host adapters. The real UI
translation unit is target-compiled/linked separately; its pure admission
helper and pending-request lifecycle represent the binding boundary here.

All three suites pass ASan/UBSan. Leak detection is disabled because the
runner cannot inspect `/proc` tasks; no LeakSanitizer PASS is claimed.

```sh
python3 -B port/dreamcast/tools/cloud/build32/uv16_host.py
ASAN_OPTIONS=detect_leaks=0 python3 -B port/dreamcast/tools/cloud/build32/uv16_host.py --sanitize
c++ -std=c++17 -O2 -Wall -Wextra port/dreamcast/tools/cloud/build32/cone_host.cpp -o "$OUT/cone-host"
"$OUT/cone-host"
python3 -B port/dreamcast/tools/cloud/build32/actor_runtime_host.py --output "$OUT/actor-host"
python3 -B port/dreamcast/tools/cloud/build32/actor_runtime_host.py --sanitize --output "$OUT/actor-host-san"
```

The source-bound runtime receipts are in `tools/cloud/build32/receipts`.
The [target README](../../../tools/cloud/build32/README.md) gives the exact
pinned-toolchain command and scope. The old `COARSE_ONE_SUBMIT=2` composition
is rejected by current actor transaction/plan Make guards, so its host result
is not a claim that the release ownership profile supports that diagnostic.

### Target identity and footprint

Against `81028934`, all **60 complete preprocessed/object comparisons** pass:
three TUs, five existing configurations, absent/explicit-zero, both `.ii`
and `.o`. Four enabled arms compile and relocatably link: cone 1, cone 2,
grouped UV16, and grouped cone+UV16. All three UV handshake exports are
defined and resolved. Four invalid-value/MOVCA probes reject; **217 consumed
inputs** remain frozen. The target receipt SHA-256 is
`bd068679885c41d9134a87955b8555c5f33fc29e38e26cbe5b83329545d46d92`.

The final rebase to `a785bb5b` changed only the queue and Build 31 owner
handback. `receipts/baseline-equivalence.json` checks all 205 consumed
baseline inputs and 217 candidate inputs: baseline Git entries are identical
and candidate hashes still match the completed gate. Its SHA-256 is
`15b69baa446bf8b1a8bc9b4353e27be087bd076f1e7452bd4561ac3306fb6f9e`.
The unchanged runner can reproduce this using `--baseline a785bb5b113f1888cdce794fe016f1c6d978b142`.

These totals are across `native_actor_fast`, `native_ui` and `coarse_actor`,
relative to the normal QA configuration with cone/UV16 both off:

| Candidate | Executable delta | Allocated delta | BSS delta |
|---|---:|---:|---:|
| Cone 1 | +9,760 B | +11,381 B | +1,249 B |
| Cone 2 | +10,456 B | +12,081 B | +1,253 B |
| UV16, shared submission | +2,284 B | +2,560 B | +84 B |
| Cone 1 + UV16 | +12,072 B | +13,969 B | +1,333 B |

The new guard alone adds +2,140 executable/+2,304 allocated/+52 B BSS over
old cone 1, and +2,136/+2,300/+52 B over old cone 2. Maximum local actor stack
is 2,388 B in QA, 2,384 B for cone/combined, and 2,388 B for UV16. UI and
coarse maxima remain 7,200 and 5,040 B. The live UV scan uses an 80-byte local
frame, `uv_axis` 20 B, `uv_decide` 28 B and the live binding export 8 B.
These are compiler local frames, not a measured call-chain stack peak.

### Bounded SH-4 cost

The cost drivers execute the compiled production helpers in the existing
SH-4 interpreter and price their traces with the established pipeline model.
Cone has nine cases; UV has 22 cases and eight DIV0U state controls. DIV1
remains unsupported and fails closed. UV executes linked `ldexpf`; source
arrays use cached SH-4 RAM addresses so its address guard runs unchanged.
Cold-I means one isolated initially cold instruction cache, with perfect
D-cache. The line column is distinct touched 32-byte addresses, not misses.

| Compiled work | Warm / cold-I cycles | Loads / stores | 32-byte lines | Observed peak stack |
|---|---:|---:|---:|---:|
| Cone qualified guard preparation | 1,008 / 1,204 | 225 / 106 | 12 | 44 B |
| Cone singular-matrix refusal | 34 / 93 | 9 / 4 | 4 | 44 B |
| Cone hidden test | 321 / 519 | 55 / 9 | 6 | 16 B |
| Cone facing test | 280 / 486 | 49 / 8 | 6 | 16 B |
| Cone near refusal | 110 / 206 | 22 / 4 | 4 | 16 B |
| Cone source identity match | 22 / 55 | 8 / 0 | 3 | 0 B |
| UV current-source check, 1 record | 223 / 525 | 60 / 28 | 16 | 88 B |
| UV current-source check, 32 records | 1,308 / 1,610 | 370 / 90 | 25 | 88 B |
| UV current-source check, 128 records | 4,732 / 5,034 | 1,330 / 282 | 55 | 88 B |
| UV legacy refusal, no UV reads | 30 / 99 | 7 / 3 | 4 | 80 B |
| UV changed-last-value refusal, 128 records | 4,723 / 4,989 | 1,327 / 279 | 55 | 88 B |
| UV source plus bound-texture admission, 128 records | 5,140 / 5,754 | 1,418 / 307 | 63 | 128 B |
| Pack 128 cached vertices, retain original U | 1,419 / 1,464 | 386 / 256 | 129 | 0 B |
| Pack 6 clipped vertices | 71 / 118 | 20 / 6 | 7 | 0 B |

Cone preparation/test/source wrapper sizes are 648/576/56 B; the isolated
fixture has 2,460 executable / 2,668 allocated / 172 BSS bytes. UV source,
decision, cache-pack and clip-pack symbols are 700/596/68/64 B; its fixture
has 4,212 executable / 13,940 allocated / 9,412 BSS bytes. These are fixture
sizes, not production image deltas; use the preceding target matrix for
production costs. The UV division helper increases its 80-byte local scan
frame to 88 B observed; the combined fixture includes a 40-byte caller.

**MODELLED whole-frame examples, added overhead only:** at 200 MHz, an
assumed 30 ms of other work plus 40 cone guard preparations and 200 hidden
tests becomes **30.5226 ms**. Forty UV parts of 128 vertices, each scanned,
admitted and packed, add **1.3118 ms**, giving **31.3118 ms**. These are
separate illustrative workloads; no saved geometry or GPU benefit is
assumed. The cone figure excludes existing matrix composition/inversion,
source lookup, counters and conversion. UV excludes conversion certification,
binding/handshake, logging, format splits and extra headers, geometry/light
work and clipping interpolation. Both exclude D-cache misses and GPU work.
Neither establishes a whole-frame gain. Cold-I cases are not additive.

```sh
python3 -B port/dreamcast/tools/cloud/build32/cone_cost.py \
  --output "$OUT/cone-cost" --sh4-cxx "$SH4_CXX" \
  --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT"
python3 -B port/dreamcast/tools/cloud/build32/uv16_cost.py \
  --output "$OUT/uv16-cost" --sh4-cxx "$SH4_CXX" \
  --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT"
```

Both receipts are committed under `tools/cloud/build32/receipts`. The final
UV receipt SHA-256 is
`cda9a124049ba372311f2293a5cf827efae3b4c8ecb1d7fc587bf050a9773fcf`.

### Exact private build, image and console commands

Use Bash at the repository root. Set absolute `BUILD_ASSETS`, `IMAGE_RECIPE`,
`GDEMU_ZIP`, a new `OUT`, and `QALINK_PI` (the Pi SSH alias or `user@host`),
and use the complete built SDK environment. These
commands intentionally use matched observer settings; do not compare them
numerically with the earlier TOUR28 baseline unless its complete composition
also matches. Keep the recipe's private `NMR_POOL_LOD` setting.

```sh
set -euo pipefail
mkdir -p "$OUT"
export SOURCE_DATE_EPOCH=1760000000
QA=(DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 QA_LINK=1 QA_LINK_REVIEW28=1
    BENCHMARK=0 PMC_ROW=0 WORLD_METER=1 DRAW_FALLBACK_AUDIT=1
    DRAW_SETUP_AUDIT=1 FALLBACK_AUDIT29=1)
COMMON=(ACTOR_LIGHT_FAST_ONLY=1 ACTOR_BACKFACE=0 ACTOR_MOVCA=0 LEON_NATIVE_PIPE=0)
build32_arm() {
  local arm=$1 format=$2 cone=$3 uv=$4
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash port/dreamcast/build-public.sh "${QA[@]}" "${COMMON[@]}" \
    ACTOR_FORMAT32="$format" ACTOR_BACKFACE_CONE="$cone" NATIVE_ACTOR_UV16="$uv"
  python3 port/dreamcast/tools/swap-program.py \
    "$GDEMU_ZIP" "$OUT/program-$arm" "$OUT/disc-$arm"
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile loader
  python3 port/dreamcast/tools/d367/disc_lint.py "$OUT/disc-$arm/disc.gdi" --profile standard
}
build32_arm control 0 0 0
build32_arm cone 1 1 0
build32_arm cone-check 1 2 0
build32_arm uv16 1 0 1
build32_arm combined 1 1 1
build32_arm combined-check 1 2 1
```

Every output disc directory must be fresh. Require full builds with no
missing symbols; retain `resolved-knobs.txt`, complete build logs and hashes
of recipe/assets, ELF, overlays, GDI and tracks. Cloud has no built KOS
libraries, so a full game/overlay link and complete disc identity remain
private gates, not cloud passes.

For hardware capture, run the updated Pi companion with
`python3 ~/qalink/qalink_pi.py serve --review28` (or the same option in the
existing service). Boot the selected arm and establish REMOTE LINK first:

```sh
ARM=combined
VIEW=barn-hayfork
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

Repeat for control/cone/cone-check/uv16/combined/combined-check at the same
barn hay-forking Ganado, outward/inward barn exit, village crowd, Leon/Ashley
and El Gigante views and states. Require actual `AC32C` admissions/tests/rejects
and mode-2 `ABFC bad=0`; zero activity proves nothing. Report the now-meaningful
split/plain record and meshlet census, `noroom`, and all refusal totals.
Require nonzero `AF32UV` admissions before calling the UV comparison useful;
report legacy/source refusals, record-scan cost and format-window splits.
The fast-only lighting slow/exact counters must remain zero.

Compare cone/uv16/combined separately with control, then mode1 versus mode2
for output checks. Keep complete DFA/DSA/WORLD_METER windows and frame/tick
denominators. Retain stills/TA evidence for animations, LOD transitions,
mirrors/oblique/near views, near-plane texture seams, masks/fades, mutable
rigid/shape refusal and room/model unload/reload. Require the normal STRICT
route, collision/AI/event outcomes, headroom and stack checks. A source-cull
appearance change needs explicit look acceptance even if `bad=0`.

For full OFF identity, build the baseline checkout and candidate with the
same private assets, recipe, SDK and epoch, without QA overrides:

```sh
BASE_TREE=/absolute/checkout/of/a785bb5b113f1888cdce794fe016f1c6d978b142
identity32() {
  local tree=$1 arm=$2
  shift 2
  RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$OUT/program-$arm" \
    bash "$tree/port/dreamcast/build-public.sh" "$@"
  python3 port/dreamcast/tools/swap-program.py \
    "$GDEMU_ZIP" "$OUT/program-$arm" "$OUT/disc-$arm"
}
identity32 "$BASE_TREE" identity-base
identity32 "$PWD" identity-absent
identity32 "$PWD" identity-zero ACTOR_FORMAT32=0
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

### Questions for Claude after runtime step

1. Please return pinned arm/config/image identities, raw counter windows,
   measured CPU/frame/GPU times and look/STRICT outcomes. Are cone split
   growth and proof costs repaid by skipped vertices in the busy views?
2. Which character parts receive new runtime certificates, and which remain
   old/offline FE3? If legacy refusals dominate, return the exact FE3/UV bytes,
   signed/Q15 interpretation, source packer and package manifests in the
   private lane. A separately validated conversion can follow those inputs;
   the current runtime does not forge certificate authority for old data.
3. Does UV16 save enough PVR work to repay packing, per-draw source scans and
   format splits? Keep it held if the matched whole-frame result is neutral
   or worse. Neither switch is promoted by this hand-back.

**Answers (Claude), runtime step:** Pending.
