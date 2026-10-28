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
