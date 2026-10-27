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
`check_provenance.py --baseline-ref <pinned pre-change commit>` exercises the real lookup with an actual private candidate,
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

## Empty-part setup control

`WORLD_REBUILD27_LIVE_MASK=1` is a separate default-off control. It requires
`WORLD_REBUILD27=1` and `PS2_PASS_MASK=1`. For r101 only, load and movie-restore
mask construction omit parts whose adopted R4IM range is empty at every LOD;
transparency-policy additions use the same live-part test. Other rooms retain
the original masks. No per-frame loop or static array is added. Diagnostics
PS2_PASS_MASK=2/3 are deliberately refused rather than silently changing their
comparison contracts.

The bounded MODELLED control observes less setup work with unchanged B1 assets,
but still exceeds the 2 ms goal by a validated lower bound. Programme layout and
model cache effects are included; its CPU-work estimate is not a certified
world-time saving. Exact pixels, route behavior, actual memory and physical
console results remain separate gates. Keep this control off in production.


## Baked house core

`WORLD_REBUILD27_BAKE=1` is a separate private default-off control requiring
WORLD_REBUILD27, the existing scenery chunk/select/replay path and PS2 lean
preload. Its additional private header pins one exact r101 mesh body and at
most sixteen L0 meshlet ranges, on source parts160/288 only. The original
R4PW, part UV basis, placements and other material records stay unchanged.
The producer must give baked meshlets distinct vertex records, including
white prelight after baking PS2 source prelight into the atlas once.

Replay splits existing selected picks into contiguous original/atlas material
runs without changing pick order, pass, cull or selector decisions. Other
parts and higher LODs keep original keys. Unsupported selection for an owned
baked part aborts before submitting wrong UV/material data. The two added
textures enter the existing room-preload list; all original shared textures
remain in the budget. Encoded bytes do not prove actual room residency.

`check_bake.py` compiles the actual routing block and uses the existing host
MeshPackage consumer. It checks a real private package, full/sparse/partial
pick streams, CRC and policy mutations, and invalid private headers. It also
checks clean-A geometry outside the named core, private vertex isolation,
source UV-basis preservation and unchanged higher LOD/owner geometry. This is
source/host coverage, not execution of camera selection or the SH4/PVR emitter.

New baked data are an explicit private data option: a knob-off control stages
original A data and its exact programme; it must not stage atlas UV geometry
with a programme that cannot route atlas materials. No recipe selects these
private data. PS2 texture provenance, decoded VQ stills/movement, route events,
KOS/H2/heap/VRAM, cache-model and physical gates remain required separately.

## Windows cache-model launch environment

Source `cache_environment.sh` before invoking Windows fp_run.py from WSL. It
propagates the required emulator/profile values with WSLENV and sets the
Windows Python reader to UTF-8. The previous cp1252 exception on U+FFFD was
a host logging fault, not a guest crash. `bash cache_environment.sh --verify`
checks the Windows child's actual values, UTF-8 output and exact emulator SHA;
it does not launch a guest. The caller still owns resource/trace leases, lane
limits, bounded duration, exact programme/assets and current media readback.
Do not reuse a mutable SD-stage pathname as an identity certificate.


`prepare_bake_arm.py` prepares only an explicitly enabled private baked arm.
It pins and checks the complete baseline manifest and candidate file manifest,
requires resolved bake/residency knobs, copies the linked programme and all
fifteen matching overlays, and adds the two exact atlas packages through the
existing loose package paths. Original tex.pak is unchanged; every other file
is checked again after preparation. Output must be fresh and disjoint. Its
receipt is not a mastered-disc, guest, memory, performance or release gate.
