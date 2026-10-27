# Private r101 reconstruction qualification

The October 27 brief defines three matched arms: A is the current accepted
world, B is a sparse opaque structural proxy, and C restores recognizable
features with each detail group priced. This directory contains qualification
helpers, not game data or a production recipe.

`pin_baseline.py` reads the actual candidate disc through the existing ISO
reader, compares every file against its release manifest, and extracts the
current r101 inputs. Its output, including source/program/asset identities,
belongs in the private store. It refuses an existing output directory.

`WORLD_REBUILD27=1 WORLD_REBUILD27_DIR=<private directory>` enables additional
r101 policy-binding certificates. It requires the current rect21/n256/strip-group
path. The generated private include is `world_rebuild27_certificates.inc`,
defining `rebuild27_certificates` as an array of the existing `Certificate`
structure. Only the render mesh identity may differ from the current r101 row.
The complete physical R4PW identity and all source policy fields remain bound.
The new candidate path recomputes the R4IM body CRC using the existing caller's
CRC implementation, after matching the candidate tuple. It runs at room load.
The original 27-row lookup is unchanged. Missing or zero knobs add no flags.

The private producer must separately prove full input/output hashes, unchanged
materials/placements/IDs, unchanged dynamic-owner geometry, and valid rebuilt
strip groups. Binding a mesh is not proof of its appearance or visibility.
`check_provenance.py` exercises the real lookup with an actual private candidate,
wrong tuples, changed physical policy bytes, changed mesh bytes, absent CRC
validation, and an invalid compiled source certificate. It also compares
preprocessed knob-off header output against the baseline. These are host/source
checks; final programme byte identity and runtime gates remain separate.

## Matched experiment

- Pin one source, programme, overlays, assets, cap 4, camera route, effects,
  settings, emulator executable and environment for every A/B/C comparison.
- Preserve the entire current `room.r4rc`, not just GRID/OCCL. Repairing stale
  render-derived data in B alone would introduce a second variable.
- Use the existing world census for phase/count/PVR observations, and a separate
  uninstrumented arm for timing. Count complete world preparation and submission,
  near and far passes, per drawn frame. State ticks per picture.
- Run comparisons through cache-model Flycast with `RE4DC_EMU=console`,
  `RE4DC_CONSOLE_DYNAREC=no`, `RE4DC_GD_PROFILE=gdemu`. Each run is at most
  60 seconds. Its frame times are not console timing; report MODELLED values
  separately, and mark an unreached measurement window unmeasured.
- Qualify walking, aiming, building entry, openings, combat, and re-entry;
  preserve normal gameplay and changing-object ownership. Counter screenshots
  alone do not qualify the route.
- Retain exact stills/clips and stage private A/B/C console discs with STEPS.txt,
  plus the uninstrumented arm. The user judges appearance and console timing;
  Claude handles integration, release and SD operations.

The final decision table must distinguish a traversal/setup floor in B, detail
cost in C, and any remaining non-world frame cost. Do not expand beyond r101
before that table has been shown to the user. No speed claim follows from
triangle counts alone.
