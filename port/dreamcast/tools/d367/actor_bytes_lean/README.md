# ACTOR_BYTES_LEAN evidence

See [Build 7 report](../../../docs/cloud/BUILD7_ACTOR_BYTES_LEAN_20261024.md).
These tools need the public source, the selected SH-4 toolchain/KOS headers and
the public compatibility headers. They do not use game data or a console image.
All generated output directories must be new.

From this directory, with `ACTOR_CXX`, `ACTOR_KOS`, `ACTOR_SDK` and
`ACTOR_EVIDENCE` set to your toolchain/compiler, KOS source, compatibility-header
root and an external evidence directory:

```sh
python3 build_controls.py --output "$ACTOR_EVIDENCE/build" \
  --sh4-cxx "$ACTOR_CXX" --kos-root "$ACTOR_KOS" --sdk-root "$ACTOR_SDK"
python3 supplemental_controls.py --output "$ACTOR_EVIDENCE/supplemental" \
  --sh4-cxx "$ACTOR_CXX" --kos-root "$ACTOR_KOS" --sdk-root "$ACTOR_SDK"
python3 check_runtime.py --profile "$ACTOR_EVIDENCE/build/absent-profile/actor-profile.json" \
  --output "$ACTOR_EVIDENCE/runtime" --mode all
python3 check_runtime.py --profile "$ACTOR_EVIDENCE/build/absent-profile/actor-profile.json" \
  --output "$ACTOR_EVIDENCE/negative" --mode negative
python3 check_runtime.py --profile "$ACTOR_EVIDENCE/build/absent-profile/actor-profile.json" \
  --output "$ACTOR_EVIDENCE/sanitizer" --mode sanitizer
python3 target_build.py --output "$ACTOR_EVIDENCE/target-build" \
  --sh4-cxx "$ACTOR_CXX" --kos-root "$ACTOR_KOS" --sdk-root "$ACTOR_SDK"
python3 target_run.py --build "$ACTOR_EVIDENCE/target-build/target-build-controls.json" \
  --output "$ACTOR_EVIDENCE/target-run" --quick
python3 kernel_audit.py --profile "$ACTOR_EVIDENCE/build/absent-profile/actor-profile.json" \
  --sh4-cxx "$ACTOR_CXX" --output "$ACTOR_EVIDENCE/kernel"
```

`build_controls.py` independently archives the exact integration base, expands
the current public Make recipe for eight SETUP/DIRECT/CONE combinations, and
compares complete preprocessing and raw objects with absent/explicit-zero arms.
Debug records are omitted in every arm. This checks the actor translation unit,
not a linked console disc or the installed KOS patch set.

`check_runtime.py` includes the complete production actor translation unit and
the earlier actor-setup harness. Its receipt lists every host adaptation.
Comparisons cover TA words, ownership/result traces, colour-prefix growth,
changing Parts/frames, coarse windows, clipping, per-vertex alpha and headroom.
The negative controls deliberately break growth, new-Part reset and half-post
folding; each must fail. Host AVK and store-queue adapters do not establish
general target floating-point equivalence.

`target_build.py` instantiates the complete production Part type with fixture
inputs and extracts the setup/colour fragments after the complete actor source.
Unchanged dynamic-lighting calls become explicit return edges.
Observed calls keep constructor stores live and delimit meshlets. This creates
synthetic alias/register boundaries: production can omit some of those stores.
Positioning, flags priming, selection, emission and unchanged dynamic-light math
are outside this phase measurement. The linked test edges are evidence-only;
they add no assembly or linker change to the game.

`kernel_audit.py` runs the unchanged Make-built AVK opcodes on restricted input
fixtures to expose address traffic and palette runs. Its FP adapter admits only
diagonal zero/one matrices, bounded integer dot products and an explicitly pinned
reciprocal-square-root input of one. This is not general SH-4 FP conformance.

Warm/cold-I timing uses the existing instruction model with perfect D-cache,
no DMA and zero store-queue cost. Demand loads/stores, bytes, unique 32-byte
lines, repeated line touches and PREF requests are separate quantities. Cold-I
is an isolated phase entry, not a cost to multiply by every sprite or meshlet
in a real frame. Console and gameplay gates belong to the integration lane.
