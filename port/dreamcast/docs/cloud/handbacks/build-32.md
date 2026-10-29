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

## Owner runtime landing, 2026-10-28

Runtime `76eeecbdb` merged clean as `2e0a59bea`, default 0. Local host checks
pass: 2,156,271 UV assertions; 79,106 cone checks; 13,070 actual actor-TU
assertions across the three modes. All three suites also pass ASan/UBSan
with leak detection disabled. Host receipts are retained in private
`cloud32-host-20261028-1837`. The release-recipe build passes rc=0/missing=0;
ELF SHA-256 `84ef636e05f9cecaf7bbd712699749bf348177a38e5a258fbe92029c74e3ed8b`.
The cloud's 60 target-byte comparisons were not rerun locally; complete
absent/zero repacked image identity remains a separate pending gate.

The two temporary local holds have been reviewed: the reported runtime
certificate/admission fixes now exist, so cone and UV16 return to the active
QA queue, only with `ACTOR_FORMAT32=1`. The ALL ON K list now includes that
guard plus cone=1 and UV16=1, alongside the existing lighting and part-plan
controls. A new QA_LINK=1 ALL ON disc is rebuilding in a fresh isolated
workspace; the previous ALL ON 81028934c remains preserved. These are QA
candidates, not release-recipe promotions or look/console acceptance.

Private runtime follow-up remains: collect real AC32C/AF32UV admissions and
legacy/source refusals, then mode-2 validation, matched model/view stills,
memory/gameplay/full-image gates and whole-frame console results. No old FE3
flags will be relabelled to manufacture admission. If legacy data dominate,
return the source/packer/hash inputs for a separate validated conversion.
Neutral or worse measured whole-frame results remain a reason to hold it.

Local weapon inventory checks completed on the preceding ALL ON 81028934c,
before this runtime. They do not qualify the new actor-format combination.
The intended matched console QA session still awaits disc selection/redial;
no Pi service edits, console inputs, SD write or release promotion occurred.

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

## EF01 owned-source span slice, 2026-10-29

**DONE - IMPLEMENTED / HOST VALIDATED, default off.** `ACTOR_SOURCE_SPAN=1`
extends the existing `ChunkInput -> Re4dcActorChunk -> owned_run_load ->
Re4dcModelPart` path. The real NMR package parser already publishes logical
position/normal, UV and FE stream extents into `ChunkInput`; compiled actor
arrays supply `sizeof` extents through the same interface. The transaction
now preserves those exact extents after its existing immutable chunk proof.
No extent comes from a largest referenced index or a physical RAM address.

The metadata names the source position/normal allocations, UV byte count,
explicit U16/Q15 or S16/Q8 interpretation, and the existing skin lease's
serial/frame. The never-reused serial authenticates an immutable borrow only
while that lease remains current. Owner validation precedes every source
read and every memo hit. Current source positions/normals and counts must
still match the registered owner. Replacement, re-LOD and mutation require
the existing owned-record retirement before a new lease is acquired; no
cross-frame content certificate or new package generation is invented.

Preparation bounds every level-zero position/normal/UV reference and every
stored LOD's record prefix and index lists, including unselected LODs. A
16-entry bounded memo reuses that proof only for the exact descriptor and
current owner incarnation. Invalid geometry refuses before emission. A UV
precision tag that disagrees with otherwise bounded current values retains
UV32. Legacy tags also retain UV32. Unknown/mutable/unowned inputs keep the
existing per-draw current-record scan. Vertex-colour, mutable bake and
pending-LOD formats remain excluded from this first immutable slice.
Current pose/palette, texture dimensions/scales, scroll and material state
remain live draw inputs and are absent from the reusable UV range proof.

The new knob is zero by default; zero/absent add no Make definitions. Enabled
builds require `ACTOR_FORMAT32=1 NATIVE_ACTOR_UV16=1 ACTOR_TRANSACTION=1
NATIVE_ACTOR_SKIN_LAZY=1`. `GAME_CPPFLAGS` and `PLATFORM_CPPFLAGS` receive the
same layout guard. SH-4 static assertions require 32 bytes per added span
and 1,024 bytes for the memo; the owned record adds
`32*(1 + role_count + run_count)` bytes before existing header rounding
(1,024 bytes at nine roles and 22 runs). Other stored part/chunk values also
grow by 32 bytes each. These are layout costs, not measured runtime peaks or
memory savings. `ASPAN` reports preparations, memo hits, geometry records and
these storage sizes for a later bound actual-data comparison.

**Host checks:**

```sh
python3 port/dreamcast/tests/test_actor_source_span.py --output "$FRESH_NORMAL"
python3 port/dreamcast/tests/test_actor_source_span.py --sanitize --output "$FRESH_SANITIZED"
python3 port/dreamcast/tools/cloud/build32/actor_runtime_host.py --output "$FRESH_REGRESSION"
```

The new whole-production-actor-TU fixture passes 214 assertions with each of
the ordinary and isolated skin owner implementations (428 per mode), normal
and ASan/UBSan (`detect_leaks=0`). Cases cover exact/truncated allocations,
bad geometry references, logical extent preservation despite a single UV
reference, signedness changes, legacy and unsupported record formats,
all three stored LOD tables/prefixes, same-pointer mutation after revocation,
same-frame stale serials, expired frames, live texture scale, actual owned
run loading and native submission. Freed source storage after retirement
proves the owner-before-dereference order under ASan. Nine malformed or
incompatible Make profiles refuse, and absent/zero produce identical empty
new flags. The existing Build32 whole-TU regression passes
4,354 / 4,358 / 4,358 assertions for its three grouped modes.
Existing host SQ/AVK adapters remain explicit platform boundaries.

**NEXT:** Full release-recipe absent/zero/ON target builds, with exact
resolved definitions, programme/overlay identity for absent/zero against the
shared pinned `9ee386e3` baseline, and enabled layout/object checks. The
coordinator serializes the SDK slot. Then collect actual-data admissions,
scan/reuse counts, retained/peak metadata, equivalent output and total actor
cost with a bound comparison control. This slice does not close EF01,
EF02 producer correction, EF04 general native FE fallback, or any runtime,
look, STRICT, full-image or physical-console acceptance gate.

**BLOCKED:** Target execution awaits only the coordinator's build slot;
source/host work is complete for this bounded slice. No private inputs,
disc mastering, emulator session, release change, SD/Pi action or upload.

### EF01 target build handback, 2026-10-29

**DONE - TARGET BUILD VALIDATED, default off.** Code commit
`d6a53024def32c1c8f94411114206b44a2cb83c8` built from a clean isolated tree
with pinned SH4ZAM `33fa4850cacb30dd0ad35485ef035526ec4ce782`. Three fresh
full `rP` release-recipe arms (absent, explicit zero, enabled) passed rc=0,
empty `missing.txt`, in 42 seconds each. The enabled arm appends
`ACTOR_FORMAT32=1 NATIVE_ACTOR_UV16=1 ACTOR_TRANSACTION=1
NATIVE_ACTOR_SKIN_LAZY=1 ACTOR_SOURCE_SPAN=1` to the unchanged current
`rr/recipe.conf -> ch2-build.sh rP` chain. Private programme registries and
fresh output labels kept other lanes' artifacts separate.

Current baseline dependencies were read back as transaction=1,
skin-lazy=1, PL08=1 and isolated-skin-owner-pool=0. All 527 logged C++
compilation commands per arm were audited, including game/platform and
generated module/overlay stubs: every enabled command carries the same
`RE4DC_ACTOR_SOURCE_SPAN=1` layout definition; every absent/zero command
omits it. Both global CPPFLAGS contain precisely that appended layout
definition. The existing transaction's level-zero-only admission and all
unrelated exclusions remain unchanged.

Against the shared clean pinned `9ee386e3` release baseline, both absent and
zero preserve the complete raw programme, all 15 overlays and all 11
allocated ELF sections. The programme is 3,372,036 bytes, SHA-256
`fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1`.
Ten selected layout-dependent game/platform objects also preserve every
allocated section. Debug ELF files differ and are not claimed identical.
The enabled ELF SHA-256 is
`58fa448c42f221b1be9b4f6a261d1e74811f276e8eb6819780e0e68f3db12409`.

Target assertions confirm 32-byte metadata and the memo symbol is exactly
1,024 bytes. The combined FORMAT32/UV16/SOURCE_SPAN enabled profile changes
text by +4,800 bytes, rodata by +256 and BSS by +1,120 relative to the release
baseline. These combined-profile deltas do not isolate EF01 cost or measure
retained primitive memory/peak loading overlap. No runtime performance or
memory-saving result follows from them.

Final exact-code normal and ASan/UBSan fixtures both pass 214 assertions for
each of the ordinary and isolated owner implementations; the existing
three-mode Build32 regression remains 13,070 assertions passed.

**NEXT:** Actual-data bounded-span admissions/refusals, scan/reuse and live
metadata measurements, effective output comparison, and the affected
runtime/look/STRICT/full-image/hardware gates. This first slice does not
enable legacy certificate semantics, CI/bake/pending-LOD authority, general
native FE fallback, or close all of EF01. The whole EF card remains open.

**BLOCKED:** No source/build blocker for integrating this default-off slice.
No live job remains and the exclusive SDK slot is released. Runtime and
physical-console acceptance are pending their bound inputs/session; no
emulator, disc mastering, SD/Pi change, publication or upload occurred.


## Answers (owner): 2026-10-29 combined engine integration

DONE: `ACTOR_SOURCE_SPAN` first slice merged default off with the other three bounded fixes into `77461a84ef85e978e44aab5d936a1b80a2cd93a4`, using four clean no-ff local integrations from `9e6662c36`. Combined release rc0, missing.txt present/empty; ELF SHA256 `49f12668242e722acfa0fee89514323c4aa7892e64014dcb970eb0473fbee0c3`. All four controls resolve zero; complete programme, all15 overlays and all allocated ELF section metadata/payloads match the bound9ee baseline. Fresh-base check and origin-only push/readback passed. A queue-row selection preflight stopped before the first build, then continued in the same clean merged candidate; no source conflict or failed build was hand-resolved.

ALL ON K includes the four new controls. Fresh ALL ON QA at source77461a84, with QA_LINK=1 and all four controls resolved1, passed compile, existing empty missing.txt, loader/standard disc lint with zero violations, ZIP test and staged checksums. Track03 is1,185,760,800 bytes, SHA256 `e70b865a2f55469f2c279094e3a9a86d4576efe22869da0d76f8e464be902c62`. This is a prepared private QA artifact, not a runtime/look/STRICT/memory/timing or physical-console acceptance result. Nothing was copied to SD.

NEXT/BLOCKED: retain this card's exact remaining source sub-slices and runtime/lifetime/look/current-memory/console gates. A first slice does not close the entire EF card. Use the verified image only for an explicitly selected compatible next check, with exact build/assets/scene/window and valid denominator. The user must select/swap intended verified media and establish reviewed link readiness where a console check requires it; current media/Pi/release holds remain. Independent EF02 producer, EF07 owner-scoped plan and EF08 producer-completion work proceeds from the integrated source. No default or frozen-release recipe promotion.

## EF02 real offline producer correction, 2026-10-29

**DONE - IMPLEMENTED / HOST AND NAMED-INPUT VALIDATED, opt-in only.**
`ps2leon/pack_arm.py --format32` now requests newly computed referenced-UV
interval tags from the actual configured owner-local fastpath producer. The
shared stdlib `ps2leon/actor_format32.py` supplies the same signed/unsigned
magnitude contract as `actor_format32_uv.hpp`: code `15+e` certifies
`abs(raw)<=2^e`, for `e=1..16`. The quantized U16/Q15 data and exact declared
source allocations are the authority. Old significant-bit flags are never
inputs to this calculation; absent/legacy capability remains absent.

The real private `build_blob.py` and `verify_blob.py` were available and
corrected under the worker's explicit private-code authority. They take an
explicit `--format32-helper` path; their default mode preserves legacy
output. Pre-edit and final code copies/hashes, configured paths and exact
named inputs are retained in the private handback, outside Git. Their final
code SHA-256 values are:

- `build_blob.py`: `ec096dfb5c916f8a3141263fb9f842a26c575e96c63a1e3b96edc88509022c1e`
- `verify_blob.py`: `3d1a68c27b90c63a700496c3249fdbf86ecc905b3879e4e1a39edc5ce4b748c8`

The public wrapper SHA-256 is
`9a63929885dce7840b33a729b0d0e04e051b0e850b9eb73573b7e436d2b18b8b`;
the shared helper is
`12b29f36d5fb5c2f8ba74d2def9051fc419691aebb5ba13d7baeceeb788c1434`.
These hashes identify code, not private game geometry or performance results.

Enabled source validation checks exact GX/attribute spans, the existing
optional 32-byte zero padding, count/index limits, FE3 records and all stored
LOD prefixes/lists. CI, bake and pending-LOD capabilities stay unsupported.
Fresh assembly also splits strips exceeding the runtime's 64-corner bound
with an even 62-corner advance, preserving triangle order and winding; if
the split exceeds the 1,024-index meshlet capacity it refuses. Default
assembly is unchanged and the input plan is never mutated. Enabled reports
record actual post-split index/strip counts, source-array hashes, exact UV
encoding/extents and helper identity. No cone capability is invented.

**Synthetic producer/consumer checks:**

```sh
python3 port/dreamcast/tests/test_actor_offline32.py \
  --fastpath "$CONFIGURED_FASTPATH" --legacy-producer "$IMMUTABLE_ORIGINAL_BUILD_BLOB" \
  --output "$FRESH_OUTPUT" [--sanitize]
```

Normal and ASan/UBSan (`detect_leaks=0`) each pass 91 producer/validator
checks and 131,210 assertions in the complete production actor TU. This
includes 131,072 exhaustive signed/unsigned tag comparisons, four actual
native submissions from freshly generated legacy/certified short and
near-clipped blobs, and emitted UV/interpolation error checks. The existing
charbake decoder and oriented-triangle oracle validate the actual producer
output; malformed spans, legacy/unknown tags, unsupported mixed formats,
all three LOD prefix tables, small-normal input, 63/64/65/66/127/128/129/1000
strip boundaries and 1,024-index refusal are covered. The original private
producer and corrected default producer emit identical synthetic bytes.
Host SQ/AVK adapters remain platform boundaries.

**Named regeneration:** Two original, explicitly bound fixtures were rebuilt
in fresh private output directories: historical `leon-hair-v2 --today` and
the current release's retained `a-rig` mesh with its original pl08 header.
The current mesh and pl08 source hashes match the retained release report;
neither source was edited. Default `a-rig` output reproduces both retained
release headers byte-for-byte. Certified output changes exactly byte two
of each of the eight main FE3 blobs and its one hair blob. Every source
attribute array, allocation length, decoded triangle encounter order,
winding, bind/source-signature table, material and plan constant is equal.
The independent configured validator passes legacy-versus-certified output
for both named fixtures, including coincident hair order/rotation. The
historical fixture is separate evidence from the current release fixture.
Original packages and generated assets remain untouched.

**NEXT:** One current-recipe target build against the fresh certified
`a-rig` headers with the existing FORMAT32/UV16/SOURCE_SPAN controls; then
actual-data admissions/refusals, effective output, retained/peak memory,
complete cost and affected look/STRICT/full-image/hardware qualification.
The current producer still emits level-zero blobs; synthetic stored-LOD
validation does not admit a new actor LOD producer or change source LOD
selection. This slice changes no runtime code, package, release recipe or
default and does not close every EF02 asset family/acceptance gate.

**BLOCKED:** No missing private producer or named input remains for this
slice. Target build awaits the coordinator's slot; live asset/package and
physical-console acceptance remain distinct pending gates. No emulator,
disc mastering, SD/Pi action, publication or private upload occurred.

### EF02 current-data target build handback, 2026-10-29

**DONE - TARGET BUILD AND LINKED DATA VALIDATED, opt-in only.** Public source
commit `a0142b1fd969edbde5f61d9be0254c3c0b81092c` built the current release
recipe once with the freshly certified, source-bound `a-rig` headers.
The existing unchanged pl08 package identity was copied into this new
private fixture directory to satisfy the existing dependency. The original
source/package/header locations were preserved. The explicit overrides were:

```sh
PS2_LEON_DIR="$FRESH_BOUND_CERTIFIED_RIG" ACTOR_FORMAT32=1 \
NATIVE_ACTOR_UV16=1 ACTOR_TRANSACTION=1 NATIVE_ACTOR_SKIN_LAZY=1 \
ACTOR_SOURCE_SPAN=1
```

The `rr/recipe.conf -> ch2-build.sh rP` arm `ef02oct29v1certrP` completed
rc=0 with the existing `missing.txt` empty in 41 seconds. ELF SHA-256:
`e444ff60320f388f191305822bbdd72c25554895366978ddd1a373e6e90414ad`.
All 527 logged C++ commands carry the shared source-span layout definition,
and the actor compile explicitly selects the exact fresh header directory.
Resolved PS2 rig, hand-pack, hand poses and Ganado LOD remain 1, 1, 1 and 3.
Other release look/LOD choices and guard exclusions were preserved.

The six compiled main FE streams (roles 0-4 and 7) and hair run zero match
their fresh generated arrays byte-for-byte in both `coarse_actor.o` and
the linked ELF. This binds the new certificates to actual target data rather
than merely an input filename. Roles 5/6 still use the existing hand-pack
path; their full-header streams are omitted by that unchanged derivation.
No new hand/costume/package capability or live actor admission is inferred.

**NEXT:** Coordinator integration of this tools-only default-preserving
change, followed by bound actual-data admissions/refusals, effective output,
memory, cost and affected runtime/look/STRICT/full-image/console gates.
Private named-source, tool, header, compiler and linked-array receipts are
retained separately. Existing runtime acceptance and remaining producer
families remain open; this is not all-EF02 completion or artwork acceptance.

**BLOCKED:** No source, host, named-input or target-build blocker for this
slice. No live process remains and the SDK slot was released. No runtime
source, release recipe, current asset package, emulator, SD/Pi state,
publication or private upload was changed by the target check.


## Answers (owner): 2026-10-29 producer, owner-plan and portal integration

DONE: EF02/EF07/EF08 bounded slices landed at `064bfa4ea9936d7570c304fd0735c5837d88546d` through three clean no-ff local delivery merges from042fae809. Delivery branches refreshed the coordinator's later append-only owner notes while retaining exact frozen code/test bytes; original branches and target receipts remain preserved. No source conflict was hand-resolved. Combined default-off release rc0/missing.txt present0, ELF SHA256 `d1740528a367990207948d8326cda6993c922be8c2f0cdc111499c071b8ef18a`; complete programme,15 overlays and allocated section metadata/payloads match the bound77461 baseline. Fresh-base and origin-only push/readback pass.

EF02's real public/private producer correction remains explicit opt-in; actual current a-rig legacy headers are byte-identical to retained release headers, certified streams preserve arrays/order/winding and compiled seven target arrays. Current production assets were not replaced. EF07 retains the actual global wrap-consumer invalidation fence and rejects unknown/ambiguous stamps for raw reuse. EF08's original enabled compile failure remains recorded; the changed scoped propagation repair retained every predicate and passed actual macro readback, corrected ON build and release/solo-portal OFF checks.

ALL ON K24 includes PLAN_OWNER_SCOPED=1 and the first four controls, with QA_LINK=1. WORLD_PORTAL_COMPLETION stays0 with WORLD_PORTAL29=0: its supported compose profile requires STREAM/clip extensions off and private authored-cell proof. It is parked with reason/owner instead of forced into an incompatible stack. Fresh private QA source064bfa4e passes compile, existing empty missing.txt, loader+standard disc lint, ZIP test and staged checksums; track03 SHA256 `387fa0007eb91934905d07c30083c1a52df3e08b9f13d30487084b44c525aee6`. Prepared only; no SD copy or current-QA gameplay/look/STRICT/memory/speed/hardware acceptance. The prior77461 QA's separate45s no-input stock capture reached its menu, with all16 runtime payloads bound; damaged512-NUL raw log remains unmodified. That menu observation is not a scene-draw or memory PASS and is not transferred to this new image.

NEXT/BLOCKED: retain all remaining EF card sub-slices and current-asset/output/lifecycle/look/STRICT/heap/stack/full-cost/console gates. Real portal occlusion still needs authored cells and compatible source/view proof. Private console checks require actual intended media selection/swap and reviewed link readiness at the user's console boundary. Frozen release/Pi/media/look holds remain. Independent next native decoder, immutable world preparation and cloth-sheet work proceeds through existing owners; source fixes do not wait for historical QA reconstruction or a broad census.


## Answers (owner): 2026-10-29 expanded cloud ownership

The user assigns all remaining source/synthetic implementation in this build to the cloud, including the relevant continuations from7c4c9200. See the [ready parallel work, exact file handoffs and next consumed slices](systemic-performance-20261029.md#answers-owner-2026-10-29-all-source-work-cloud-assignment). Preserve the already-running local frozen slices and all existing evidence. Cloud owns their source follow-ons after published landing/file release; local owns private assets, actual runtime/console checks and serialized integration. No full-card or hardware acceptance is implied.


## EF04 bounded portrait native continuation, 2026-10-29

**DONE - SOURCE AND HOST, scoped opt-in; target qualification pending.**
`NATIVE_FE_CONTINUATION=1` connects the existing PS2 portrait-hair producer
to the existing validated native actor positions, current normal/lighting,
clipping and packet emitter without requiring a free ordinary skin-registry
slot. The source's unchanged 119-bone loop computes the current weighted
palette; the compiled rig hair currently has 27 matrices. Immutable chunk
proof and EF01's exact unsigned-Q15 array/stream spans remain mandatory.
Mutable/unowned/LOD payloads gain no new authority or decoder.

The actual caller is `model_bridge.cpp:re4dc_draw_model_part`'s portrait
callback. `Render()` processes the model/UI OTs before `GXSetDrawSync(0xADEB)`;
the source hook at that token drains native deferred parts. Hair uses the
existing masked-material TR predicate, so its normal call really queues.
The new result wrapper reports Queued only after the original bounded queue
publishes its node. Its existing lossless view and selected-light snapshots
retain material, camera/projection, normal matrix and current lighting.
No stack palette is borrowed. Explicit identified refusal returns negative
through the existing boolean caller, preventing GC fallback while recording
neither a drawn nor successfully queued portrait. Native replay is dispatched
before generic material/GX submission and keeps EF03 Refused/PartialAbort
semantics at actual resource/header/packet boundaries.

The palette copy is allocated through `re4dc_prim_tail`, with the existing
16 KiB remaining-capacity reserve, and bound to an existing fixed
WorkspaceReservations value ticket. Every snapshot read first validates live
stream, render-frame allocation epoch, serial, exact pointer and logical
extent. Unrelated skin registrations and `prepare_frame()`'s repeated
`workspace_end` reset cannot overwrite it. Queue reset, frame abort, normal
drain/release and the existing `sourceActorRetire -> transaction_retire ->
actor_owner_retire` primitive-retirement chain revoke authority before reuse.
There is no new registry, decoder, persistent pose cache or source owner.

SH4 accounting: the guarded ModelPart fields add 20 bytes; extending the
existing 64 reservation slots adds 512 fixed bytes. A snapshot has a 72-byte
descriptor, rounded to 96, followed by exactly `palette_count * 48` pose
bytes and final 32-byte alignment: the current 27-matrix allocation is 1,408
bytes. Existing deferred view-difference storage grows according to its actual
changed words. These are structural costs, not a measured heap/stack peak or
performance claim. Zero/absent adds no Make definitions and preserves layout.
Enabled Make composition requires FORMAT32, SOURCE_SPAN, transaction, native
fast/lazy skin, the existing PS2 rig portrait option and LEON_LOD=0; new shared
layout flags are appended to both GAME_CPPFLAGS and PLATFORM_CPPFLAGS.

Public tests (synthetic arrays only):

```sh
python3 port/dreamcast/tools/cloud/build32/actor_continuation_host.py --output "$FRESH_HOST"
python3 port/dreamcast/tools/cloud/build32/actor_continuation_host.py --sanitize --output "$FRESH_SAN"
python3 port/dreamcast/tools/cloud/build32/actor_continuation_off.py --output "$FRESH_OFF"
python3 port/dreamcast/tests/test_actor_source_span.py --output "$FRESH_EF01_REGRESSION"
```

The actual portrait body, immutable proof/cache, COPY_LEAN queue/view/light
snapshot and drain bodies, native-model replay branch and whole actor TU
execute with explicit hosted source-struct, primitive-allocation, SQ/AVK and
texture-transport adapters. Normal and ASan/UBSan gates pass 390 checks in
each ordinary/isolated owner-pool x FAST_ONLY=0/1 profile. The queue survives
a full registry plus actual unrelated info/table churn and later submits;
every emitted word matches an independent existing native skin/table route
with the same current weighted pose and lights. Changed current pose changes
the output. Tests cover exact 27/256-matrix spans, fixed-ticket exhaustion,
same-address serial reuse/stale release, primitive retirement and freed
snapshots, reset/abort/resource loss, queue-full refusal, direct/packet
header-only failures, signedness, all unsupported LOD prefixes, malformed
normal/stream/palette/119-bone/finite-matrix bounds, and zero GX attempts.
Existing EF01 regression passes 214 checks in each owner profile.

Hosted actor baseline `255964fdc`, control absent and explicit zero all retain
4,358-check output and identical 82,672-byte selected allocated code/data
image SHA256 `8c639930c50617ea0c0bf5c3a3a9727e3cd5b5ca265d57eafe9f137be01ca673`.
This hosted actor control does not establish other target TUs or full-program
identity. Private receipts are under `/root/probe/engine-ef04-20261029`;
no generated artwork, private input, recipe or current package was changed.

**NEXT:** Coordinator-granted target compile/full release control, bound
enabled layout/macro propagation and actual current-data target emitter
qualification, then separate current artwork/output/look/STRICT/heap/stack/
full-cost and physical-console gates. This is the first bounded portrait
continuation slice, not all encoded families or whole EF04 completion.

**BLOCKED:** No source/host blocker. SDK slot is coordinator-controlled and
has not been used for this slice. No emulator, mastering, SD/Pi action,
push/integration, publication or private upload occurred.

### EF04 target qualification and frozen delivery, 2026-10-29

**DONE - TARGET COMPILE/LINK AND DISABLED IDENTITY, opt-in only.**
Frozen source `1404434c5d319daa5631269317725fb274a670bd` passed the full
release recipe with the new control absent and explicitly zero (41/42 s,
rc=0, existing `missing.txt` present and empty). Against the bound runtime
`064bfa4ea` output, both programmes, all 15 overlays and every one of the 11
allocated ELF sections match in bytes and section metadata. Debug ELF hashes
are distinct and are not substituted for this programme/section proof.

The first enabled arm is retained as a real failed build: rc=1 after 26 s,
no ELF and no `missing.txt`. A newly included source preflight header's
recovered placement-new shim collided with libstdc++ `<new>` in this platform
TU. Scoped repair `b77a61a9664ac1c0f414d5ac70e726d38996f4e7` uses the existing
`PLACEMENT_NEW_DEFINED` guard only inside NATIVE_FE_CONTINUATION; no common
header or runtime semantics changed. Post-repair normal host390 x4 passed.
Both absent and zero complete hosted preprocessed byte streams are identical
between the two frozen source tips (2,222,963 bytes each; SHA256
`d20719d22a3263e0430a5fa7c335b749d80040eb508f9ea67293ead2b5abb17f`), and
the affected baseline/absent/zero hosted allocated-code/data/output gate
passed again. The earlier valid target OFF evidence remains applicable.

The fresh enabled-only retry `ef04oct29v2onrP` on frozen `b77a61a9` passed
rc=0 in 42 s, with the existing `missing.txt` present and empty. ELF SHA256:
`e75b2d3a373001d7609b4cb59843df83686055c5fc398296dd107209af62dfac`.
Recipe-derived explicit overrides were:

```sh
ACTOR_FORMAT32=1 NATIVE_ACTOR_UV16=1 ACTOR_TRANSACTION=1 \
NATIVE_ACTOR_SKIN_LAZY=1 ACTOR_SOURCE_SPAN=1 NATIVE_FE_CONTINUATION=1
```

Actual resolved dependencies remain portrait=1, PS2_LEON=1, PS2 rig=1,
LEON_LOD=0, transaction=1 and lazy skin=1. Unrelated release dependencies,
look/LOD selections and guard exclusions are preserved. All 527 C++ compile
commands in each arm were checked: both new shared-layout definitions are
absent in OFF and present in ON across game, platform and modules. The actual
coarse portrait object calls snapshot acquisition and the lower native
submit; native_model calls the replay entrypoint; native_ui links retirement
hooks. All new exports link. Target assertions passed for the 72-byte
descriptor and current 1,408-byte primitive allocation; the linked current
palette is 1,296 bytes (27 matrices) and the existing reservation object is
1,032 bytes (512 additional guarded bytes).

The exact current named private headers in PS2_LEON_DIR were hashed before
launch and bound again after build: runtime
`2e894b70fe971469765de96b3f6141324b33785e2914b51dcf63b442b4dc4c65`, hair
`7c28382e175c24bdeb4eedf504dee0f7b5da76d82b4486b6e5e76e14677c76be`, pl08
identity `c27c02300e55f06be5560855904be11ef4e446106b518def9530d0a2f7f5b17f`.
They were consumed from their unchanged existing location; no regenerated
asset or package was substituted. The enabled ELF section deltas including
FORMAT32/SOURCE_SPAN dependencies are text +8,512, rodata +288 and BSS +1,632
bytes; these are linked structural costs, not a runtime memory or speed result.
Private source/header/resolved-compile/link/identity receipts remain in
`/root/probe/engine-ef04-20261029/release{1,2}`; failed and passing arms remain
separate. Original source trees and receipts are retained.

**NEXT:** Coordinator integration of the exact qualified public code/test
bytes with the newest owner documentation prefix preserved. Real current
portrait artwork, admissions/refusals, effective output, look/STRICT,
heap/stack/full cost and physical-console acceptance remain separate gates.
The independently proved host producer/queue/emitter and target compile do
not establish those live gates or other encoded producer families.

**BLOCKED:** No source, host or target-build blocker for this bounded slice.
Both runner sessions ended and the coordinator SDK slot was released. No
emulator, disc mastering, SD/Pi action, asset/package overwrite, publication,
push/integration or private upload occurred in this worker.
