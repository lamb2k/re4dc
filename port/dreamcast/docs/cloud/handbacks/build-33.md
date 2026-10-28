# Build 33: ordered static-object output batches

**2026-10-28 progress 1: DONE** source/history and ordering design; **NEXT**
default-off runtime header coalescing, synthetic order oracle and SH-4 gates;
**BLOCKED** private coverage and net console benefit require the owner runs below.

Branch: `codex/static-object-batch-20261028`, based on
`a785bb5b113f1888cdce794fe016f1c6d978b142` (`origin/t15/int`).
This first commit changes this report only. It does not enable a switch or
change the queue, release recipe, runtime, assets or image inputs.

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
`GDEMU_ZIP`, a new `OUT` and `QALINK_PI` (SSH alias or `user@host`). Use the
complete built Dreamcast SDK. Baseline only; candidate commands will be added
with the runtime step:

```sh
set -euo pipefail
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
