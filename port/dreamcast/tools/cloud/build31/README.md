# Build 31 target qualification

`build_controls.py` derives compiler commands from the checked-in public recipe
through Make. It uses the same pinned compiler, KOS and SH4ZAM verification as
Build 26. It does not execute recipe shell text or use private game assets.

```sh
python3 -B port/dreamcast/tools/cloud/build31/build_controls.py \
  --baseline f4c1af9a1c861de58d56e71fb18d0f4e4e313217 \
  --output "$OUT/build31-target" --baseline-cache "$OUT/integration-trees" \
  --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT" \
  --toolchain-receipt "$TOOLCHAIN_RECEIPT"
```

The output directory must be new. The optional cache stores an independent
`git archive` of each exact baseline; every source/build input actually consumed
from a reused archive is checked against that commit's Git blob identity.

The default matrix compares whole preprocessed source and SH-4 object bytes
with the new switches absent and explicitly zero in four profiles: the public
release recipe, QA, the supported portal prerequisites, and magenta diagnostics.
It compiles changed `native_static.cpp`, the allocator in `ui_bridge.cpp`, and
the existing `native_ui.cpp` which provides the scene and opaque-submission
proof hooks. Enabled portal,
part-plan, combined and magenta arms are compiled and relocatably linked, with
the proof hooks required to resolve. Ordinary external game/KOS references
remain unresolved; this is not a full linked-game or image-equivalence claim.

The supported portal profile disables `SCENERY_STREAM` and
`SCENERY_SUBMIT_BATCH` on **both** control and candidate. The part-plan-only
profile retains the public recipe. Console cost evaluation must compare portal
against both its matched control and the normal release. Magenta is a visual
diagnostic, not a performance result.

`target-controls.json` contains compact hashes, sizes, stack maxima, defaults,
Make selection hashes, comparisons and source identities. Full commands,
profiles, compiler logs, `.ii`, `.o`, `.d` and `.su` files remain in the output
directory. Debug records and preprocessor line markers are disabled consistently
in all arms. A gate rejects source/build input changes during its run.

Use `--only off` or `--only on` for one half, and `--composition NAME` for a
single profile. For another build, copy `--print-config` output to JSON and pass
`--config FILE`. `units` maps each name to its Make object target and source
relative to `port/dreamcast/game`; `new_units` excludes newly added units from
the baseline comparison. `knob_units` binds each enabled switch to the TUs that
must receive its `-DRE4DC_NAME=value`. The profile lists contain Make assignments.

## Reproduce the existing PVS + batch blocker

The richer `PS2_PVS_BATCH_COMPOSE=1` profile is retained under
`unqualified_profiles`, outside the passing matrix. At baseline `a3320b54`,
Make accepts this profile but preprocessing the original `native_static.cpp`
rejects PVS with submit batching and two early composition prerequisite guards.
No Build 31 code is needed to reproduce it. To run that expected failure:

```sh
python3 -B port/dreamcast/tools/cloud/build31/build_controls.py --print-config \
  > "$OUT/build31-repro-config.json"
python3 - "$OUT/build31-repro-config.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
config = json.loads(p.read_text())
config['off_profiles'] = config['unqualified_profiles']
p.write_text(json.dumps(config, indent=2) + '\n')
PY
python3 -B port/dreamcast/tools/cloud/build31/build_controls.py \
  --config "$OUT/build31-repro-config.json" --only off \
  --baseline a3320b546e5d7936d35a1975b02f0eacb9002600 \
  --output "$OUT/build31-existing-compose-repro" \
  --baseline-cache "$OUT/integration-trees" \
  --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT" \
  --toolchain-receipt "$TOOLCHAIN_RECEIPT"
```

Expected nonzero exit; inspect
`legacy-compose-baseline-native_static-ii.log`. The final supported matrix does
not remove or bypass these existing source guards.
