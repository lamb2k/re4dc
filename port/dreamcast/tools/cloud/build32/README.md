# Build 32 target qualification

`build_controls.py` derives production SH-4 commands from the checked-in public
recipe through Make. It imports the landed Build 26/24/18 qualification helpers,
verifies the pinned compiler/KOS/SH4ZAM receipt, and uses no private game data.
The Build 31 branch is not a dependency of this runner.

```sh
python3 -B port/dreamcast/tools/cloud/build32/build_controls.py \
  --baseline a785bb5b113f1888cdce794fe016f1c6d978b142 \
  --output "$OUT/build32-target" --baseline-cache "$OUT/integration-trees" \
  --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT" \
  --toolchain-receipt "$TOOLCHAIN_RECEIPT"
```

The output directory must be new. An optional baseline cache holds independent
`git archive` trees. Every consumed cached source/build input is checked against
its exact integration Git blob before use. Source, Make, recipe and helper
hashes must remain unchanged throughout a run.

## Disabled identity

The matrix compiles complete `native_actor_fast.cpp`, `native_ui.cpp` and the
existing `coarse_actor.cpp` table producer. Each profile compares the exact
baseline with the candidate's `ACTOR_FORMAT32` absent and explicitly zero.
Both complete preprocessed files and complete object files must match byte for
byte, along with Make flags and selected objects/link inputs. Debug records and
preprocessor line markers are disabled consistently in every arm; there is no
further normalization of source or object bytes.

The five profiles are release, QA, existing cone mode 1, existing cone mode 2,
and the established legacy UV16 direct-off compatibility profile. That gives
60 comparisons: five profiles × three TUs × two control modes × two outputs.
The last profile uses the explicit `DIRECT_OFF` list from
`actor_setup_lean/build_profile.py`, also used by
`actor_bytes_lean/supplemental_controls.py`. It preserves coverage of the old
UV16 path; it is not the normal actor transaction or a grouped UV32 performance
control.

The cloud-only `NMR_POOL_LOD=0` override is identical on both sides because its
selected private generated header is unavailable. It does not change the
release recipe, which remains the owner of private image builds.

## Enabled compilation

Four profiles compile all three production TUs and relocatably link them:
cone mode 1, cone mode 2, UV16 with normal grouped submission, and cone+UV16 with
normal grouped submission. Every enabled profile uses
`ACTOR_LIGHT_FAST_ONLY=1`; UV16 retains `ACTOR_MOVCA=0` and
`LEON_NATIVE_PIPE=0`. The UV profiles require the three new request/result/live
handshake exports to be present and resolved. Ordinary game/KOS references
remain unresolved: this is not a full linked game, overlay or image test.

The old `COARSE_ONE_SUBMIT=2` check composition is not part of this target
matrix. `ACTOR_TRANSACTION=1` requires grouped mode 1 exactly in
`demo_candidate.mk`, and `ACTOR_PLAN=1` independently requires it. Changing
those controls would change the actor ownership profile. Existing guards are
preserved; no grouped-mode-2 release or console claim follows from a host test.

`target-controls.json` records source identities, object sizes and local static
stack maxima, full-file hashes, comparison results, invalid-value rejections,
Make selections and partial-link hook checks. Raw commands, full profiles,
compiler logs, `.ii`, `.o`, `.d` and `.su` files remain under the output directory.
Neither successful compilation nor synthetic host tests establish real texture
coverage, raster equivalence, target cache timing or a whole-frame gain.

Use `--only off` or `--only on` for one half and `--composition NAME` for a single
profile. `--print-config` exposes the complete matrix; `--config FILE` accepts
that JSON shape for isolated follow-up builds.
