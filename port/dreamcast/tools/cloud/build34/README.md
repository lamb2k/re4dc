# Build34 existing-switch fixes: target gate

The review and owner decisions live in `docs/cloud/handbacks/build-34.md`.
This runner qualifies the bounded repairs under the existing
`SCENERY_CONE`, `SCENERY_PIECE_STATE`, `FRONT_TEXOBJ`, `CHAR_CHUNK` and
`CHAR_CHUNK_BACKEND` switches. It does not enable them in a recipe.

## Scope

The engine is the landed Build31 Make-derived full-translation-unit gate,
with two local adaptations: unchanged link providers are explicitly ON-only,
and `FRONT_TEXOBJ` is verified in the actual generated `records30.h` that
Make passes to `trans.cpp`, rather than requiring a command-line definition.
The release recipe is read by the existing restricted Build18 helper. No
shell recipe assignments or private asset builders are executed.

The qualified baseline is `ac154934df7ddf14fc5c6b6932a24a99a253f8e6`.
The final runtime base is `1511637ac54057807b654ac55ea43a48f6e8ae47`;
`receipts/baseline-equivalence.json` verifies the documentation-only advance
against all 196 consumed baseline and 246 candidate inputs. The changed
production translation units are `platform/native_static.cpp`,
`../../../src/game/trans.cpp`, and `platform/native_actor_fast.cpp` (which
includes `native_actor_chunk.inc`). Current release and QA profiles compare
all three against an independently archived baseline, with all five controls
absent and explicitly zero. That produces 24 raw full-preprocessor/object
identity comparisons. Debug records and preprocessor line directives are
omitted consistently; there is no normalized-content comparison.

Six enabled profiles compile the complete production sources: cone sign1,
cone sign-1, piece-state, front-cache, and all repaired paths with actor fast
lighting0 and1. The exact-light arm uses `CHAR_CHUNK=2` to compile the
actual LCHK fallback-counter reader; the fast-light arm uses mode1. `native_ui.cpp` and `chunk_submit.cpp` are unchanged ON-only
providers. Relocatable links check the existing piece-slot and chunk-submit
interfaces. Remaining ordinary game references are expected: this is not a
whole-game link, overlay/image identity gate, private-data run, or console
acceptance.

Six small baseline ON controls additionally compile only the relevant changed
TU with exactly the same enabled Make options: native_static for both cone
signs and piece-state, trans for the front cache, and native_actor_fast for
both lighting profiles. These produce repair-only code/data/local-stack
comparisons against the existing ON implementation, separately from the older
feature's total ON-vs-OFF size. Unchanged providers are not rebuilt for them.

Make-only checks reject enabled cone signs empty/0/2/multiple values and two
invalid existing chunk-backend compositions. They also require acceptance
of explicit +1, and of irrelevant invalid/empty signs when the cone is off.

The selected recipe keeps its existing stream/replay/batch settings.
`FRONT_NATIVE=2` is an older replay/check profile rejected by the current
`ACTOR_TRANSACTION=1` prerequisite, so the target gate uses the actual release
`FRONT_NATIVE=1`. The bounded front-cache host tests cover the cache/snapshot-flush helpers;
they do not execute a complete FRONT_NATIVE2 replay or establish that current
release composition.

`NMR_POOL_LOD=0` is the established public-data validation override, identical
in baseline and candidate. This is recorded in every receipt and does not
change the private release recipe. The SH4ZAM pin remains the current standard
pin; no optional skin-fork upgrade is performed.

## Reproduce

From the repository root, choose a new output directory and use the pinned
compiler/KOS/SH4ZAM trees described by the landed Build24 toolchain receipt:

```bash
python3 -B port/dreamcast/tools/cloud/build34/build_controls.py \
  --output "$RE4DC_BUILD34_OUTPUT" \
  --baseline 1511637ac54057807b654ac55ea43a48f6e8ae47 \
  --sh4-cxx "$RE4DC_SH4_CXX" \
  --kos-root "$RE4DC_KOS_ROOT" \
  --sdk-root "$RE4DC_SH4ZAM_ROOT" \
  --toolchain-receipt "$RE4DC_TOOLCHAIN_RECEIPT"
```

`--baseline FULL_SHA` provides an explicit final integration override.
`--baseline-cache DIRECTORY` reuses independently archived Git trees; every
consumed baseline input is checked against its exact Git blob. `--print-config`
prints the complete matrix. `--only off|on` and `--composition NAME` select
subsets for a reported preflight, not a substitute for the final complete gate.

The complete raw output retains compile commands, expanded profiles, dependency
closures, full `.ii` and `.o` files, `.su` stack reports, Make logs and partial
links. The compact committed receipt records hashes, sizes, maximum local stack,
identity comparisons and exact profile options. Stack reports describe local
frames, not maximum call-chain stack. Code/object sizes do not establish console
speed or full-image memory floors.

## Host correctness, bounded cost and SCPS-only data

[SCN21-VALIDATION.md](SCN21-VALIDATION.md) documents the actual scenery loader
and character sink fixtures, their sanitizer twins and the dynamic-input SH-4
cost fixture. [FRONT_TEXOBJ.md](FRONT_TEXOBJ.md) documents the actual cache
oracle, reproduced old failures and separate-provider cost comparison. The
committed `receipts/` files retain their full source hashes and limitations.

The metadata-only SCPS producer avoids importing the historical sc21 mesh and
strip-group bundle. It accepts existing R4IM v1/v2/v3 header/part extents and a
bounded, CRC-valid R4RC v1 container, binds the optional table to the unchanged
mesh, and preserves all other section payloads and metadata except offsets.
It updates the container count/size/CRC, writes zero initial slots, never writes
mesh/policy/group files and refuses to overwrite outputs. Geometry adoption
and the owner’s current heap/console gate remain independent.

```bash
python3 -B -m unittest discover -s port/dreamcast/tools/cloud/build34 \
  -p test_scps_only.py -v
python3 -B port/dreamcast/tools/cloud/build34/scps_only.py --scps-only34=1 \
  --mesh "$DISC_TREE/dc/native/r103/ps2-world.re4mesh" \
  --room-file "$DISC_TREE/dc/native/r103/room.r4rc" \
  --out "$RE4DC_BUILD34_OUTPUT/scps/r103/room.r4rc" \
  --report "$RE4DC_BUILD34_OUTPUT/scps/r103/report.json"
```

Without `--scps-only34=1`, no files are read or written. The reported
`runtime_scps_block_contribution` is the 32-byte-rounded contribution to the
existing shared room block, not a separate allocation or total allocator
cost. It excludes overhead and the existing allocator’s eviction effects.
Use identical generated room metadata in the program-off/program-on pair;
the final hand-back gives complete image replacement and capture commands.
