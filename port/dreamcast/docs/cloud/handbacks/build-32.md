# Build 32: actor cone and UV16 admission

**2026-10-28 progress 1: DONE** source/history investigation and concrete blocker identification; **NEXT** qualify guarded runtime fixes and admission counters; **BLOCKED** actual character coverage, visual acceptance, full image identity and frame-time results need Claude's private assets and console. This first step changes documentation only.

Branch: `codex/actor-cone-uv16-20261028`, based on
`f4c1af9a1c861de58d56e71fb18d0f4e4e313217` (`origin/t15/int`).
The queue and release recipe are unchanged. No switch is promoted here.

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

## Cost and identity of this step

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
