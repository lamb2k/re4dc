# Build 33 target qualification

`build_controls.py` copies the landed Build 31 generic gate and imports the
landed Build 26/24/18 profile helpers. It derives production SH-4 commands from
the public release recipe through Make and verifies the pinned compiler, KOS
and SH4ZAM receipt. It has no dependency on the Build 32 branch or private data.

```sh
python3 -B port/dreamcast/tools/cloud/build33/build_controls.py \
  --baseline 14f6ef1ef864682d183e7f8647a06fea514578fe \
  --output "$OUT/build33-target" --baseline-cache "$OUT/integration-trees" \
  --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT" \
  --toolchain-receipt "$TOOLCHAIN_RECEIPT"
```

Use a new output directory. The optional cache stores independent `git archive`
trees; every consumed archived source/build input is checked against its exact
Git blob. Candidate source, Make, recipe and helper hashes are frozen during
the run. Debug records and preprocessor line markers are disabled consistently
for every arm, with no further normalization of source or object bytes.

## Disabled identity matrix

The gate compiles complete `model_bridge.cpp` and `native_ui.cpp`, comparing the
integration baseline against `STATIC_OBJ_BATCH33` absent and explicitly zero.
Both preprocessed source and SH-4 objects must match byte for byte; Make flags,
object selections and link inputs must also match.

| Profile | Existing controls |
|---|---|
| Release | Public recipe: `STATIC_OBJ_BATCH=2`, word comparison enabled |
| QA | Same recipe plus the established QA/link/world-meter observers |
| Legacy 1 | QA with `STATIC_OBJ_BATCH=1` |
| Byte comparison | QA with `STATIC_OBJ_BATCH=2 STATIC_OBJ_BATCH_WORDCMP=0` |
| Legacy disabled | QA with `STATIC_OBJ_BATCH=0 STATIC_OBJ_BATCH_WORDCMP=0` |
| TA hash | QA with `TA_HASH=1 SCENERY_STREAM=0` |
| Actor format | QA with `ACTOR_FORMAT32=1 ACTOR_BACKFACE_CONE=1 NATIVE_ACTOR_UV16=1 ACTOR_LIGHT_FAST_ONLY=1` |

This is 56 complete comparisons: seven profiles × two TUs × two control modes ×
two outputs. `NMR_POOL_LOD=0` is the same validation-only override in all arms
because its private generated input is unavailable. The release recipe is
unchanged.

## Enabled and rejection matrix

Five profiles enable `STATIC_OBJ_BATCH33=1`: release, QA, legacy mode 1,
the TA-hash diagnostic and the landed actor-format combination. Both
production TUs compile and undergo a relocatable
link. The marker and header helper introduce no required cross-TU API;
ordinary existing game/KOS references remain unresolved. This is not a full
ELF, overlay, repacked-image or console test.

The actor-format arm retains grouped mode 1 and compiles the actual UV16
header path together with Build 33. Its three landed request/result/live
exports must be present and resolved. The unchanged actor TU is not added to
the OFF matrix; the two changed TUs contain the marker and final-header logic.

The TA-hash composition disables the existing scenery-stream experiment on
both sides because its existing guard explicitly rejects `TA_HASH`. It tests
observer compatibility and is not a performance control for the release
composition. The packet and direct UI paths both compile with `TA_DIRECT=1`;
no `TA_DIRECT=0` recipe composition is claimed, since the inherited world mesh
and scenery submission controls require direct TA submission.

Make probes reject empty, nonboolean and multiple new-switch values, existing
static-object modes 0/3 with the new switch enabled, and missing stream/renderer
prerequisites. `TA_GUARD=1` is rejected because its existing physical packet
contract requires one header per send. Logical GC-asset packet auditing is
retained; it needs no added restriction. No old guard is widened or removed.

`target-controls.json` records the comparisons, source hashes, object sizes,
local static stack maxima, Make states and partial-link results. Full commands,
profiles, compiler logs, `.ii`, `.o`, `.d` and `.su` files remain in the output
directory. Host/header tests and successful target compilation do not establish
private object coverage, hardware raster equivalence or a whole-frame gain.

Use `--only off` or `--only on` for one half, `--composition NAME` for one
profile, or `--print-config` / `--config FILE` for an explicit matrix.
