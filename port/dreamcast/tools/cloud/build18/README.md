# Build 18 target gates

These tools compile public source for SH4 with repository-pinned KOS and
SH4ZAM headers. They are independent of the Build17 branch. No game data or
console is required. Use a new output directory for each qualification run.

## Complete translation units and default-off identity

```sh
python3 port/dreamcast/tools/cloud/build18/build_controls.py \
  --output /tmp/build18-target-controls \
  --sh4-cxx "$RE4DC_KOS_CC_BASE/bin/sh-elf-g++" \
  --kos-root "$RE4DC_KOS_BASE" \
  --sdk-root /path/to/pinned/sh4zam \
  --toolchain-receipt /path/to/toolchain-receipt.json
```

The gate archives integration base `74154cae`, obtains the real Make compiler
commands, and builds complete `native_ui.cpp` and `ui_bridge.cpp` translation
units. Profiles cover the current public Test24 recipe, existing queue-log and
queue-diagnostic composition, and `FX_ROOM_SPILL_KB=0` compatibility. Every
profile compiles baseline, knob absent, and explicit zero. The first two also
compile enabled arms. Enabled `FX_ROOM_SPILL_KB=0` must be rejected by Make:
additional capacity requires an existing distinct room cell. The cost fixture
covers the actual failed-allocation/model-tail alias under the nonzero 24 KiB
setting. The explicit-zero arm also defines `RE4DC_FX_R200_ENTRY_CAP=0` in the
compiler command.

All absent/zero preprocessed output and whole ELF object bytes must equal the
baseline. Debug records are consistently omitted; nothing is stripped from the
objects after compilation. Source bytes are supplied on stdin, with the real
source include directory retained using `-iquote`. Only source/output paths are
normalized when comparing Make flags. The dependency files record the included
repository headers, including shared effect paths.

Enabled native UI and bridge objects are linked relocatably to check that the
live-room getter resolves exactly once. This is not a final game link. A
separate production layout object appends a constant exporter to the actual
native UI source, reporting the target sizes of the admission state, queue node,
packet types, frame storage and model slab subdivisions.

`build_profile.py` reads the release-knob file selected by `build-public.sh` and
all ordered CH2 appends in `rr/recipe.conf`. It accepts literal assignments and
the documented leading `$CH2` append only. It does not evaluate shell recipe
text. Missing-data substitutions come from the public build script and are
recorded in the receipt. On this base that includes
`LEON_PS2_PORTRAIT_HAIR=0`, applied after the recipe's `=1` because the public
fixture has no private PS2 portrait hair assets.

## Admission costs

```sh
python3 port/dreamcast/tools/cloud/build18/target_cost.py \
  --output /tmp/build18-target-cost \
  --sh4-cxx "$RE4DC_KOS_CC_BASE/bin/sh-elf-g++" \
  --kos-root "$RE4DC_KOS_BASE" \
  --sdk-root /path/to/pinned/sh4zam

python3 port/dreamcast/tools/cloud/build18/native_cost.py \
  --output /tmp/build18-native-cost \
  --sh4-cxx "$RE4DC_KOS_CC_BASE/bin/sh-elf-g++" \
  --kos-root "$RE4DC_KOS_BASE" \
  --sdk-root /path/to/pinned/sh4zam
```

The cost gate compiles the production admission helper using native UI's real
flags and runs deterministic synthetic room/generation/storage states. It uses
the existing SH4 opcode interpreter and hardware scheduling model. Results
report actual dynamic instructions, warm/perfect-cache and cold-I cycles,
loads/stores, bytes, 32-byte demand-line counts, and stack use.

`native_cost.py` separately compiles the complete unchanged `native_ui.cpp`.
It changes only the local adapter symbol's visibility in a copy of the object,
checks that its unrelocated code bytes remain identical, and retains that
production adapter at isolated link. The caller and room/getter callbacks are
explicit synthetic stubs in a separately compiled fixture. Their instructions
are counted, and the real newlib `memset` is included. The adapter's own
production frame is reported separately from combined fixture stack use.
The production constant-propagated adapter assumes aligned requests from its
real callers; the native fixture uses 128-byte and 192-byte requests. Invalid request sizes
are covered by the unspecialized helper fixture.

The native fixture also provides a clearly labelled **MODELLED** hypothetical
frame with 42 accepted extra-tail laser-line requests of 192 bytes and one
refusal in one continuous trace, assuming the primary and room spill are full.
That uncapped producer path uses 8,064 tail bytes with 128 left. The separate
64-grant sprite fill is selector stress only: the real ordinary sprite producer
cap prevents the complete 65-attempt adapter sequence. The 200 MHz conversion
is `cycles / 200000` milliseconds, with one
initial cold instruction cache for the entire sequence. This gives admission
overhead under stated assumptions, not the total game frame or a saving.

Architectural demand lines are not measured cache misses. The cases model only
selection or native adapter admission and their fixture wrappers. Texture preparation, packet generation,
source queue traversal, accepted-sprite rendering, PVR work, real room-state
lookup, and console timing are outside this cost boundary. Recovering admission
can add rendering work; these tests make no frame-rate or owner-render-speed
claim. The local owner must replay the r200 entry scene and check drops, queue
pressure, memory, ordering, and the resulting picture.

## Compact receipts

These commands retain all numeric results and source/object hashes while
deduplicating repeated flag/recipe/dependency arrays. Raw build commands,
objects, disassembly and trace artifacts remain beside the input receipts.

```sh
python3 port/dreamcast/tools/cloud/build18/compact_receipt.py \
  --input /tmp/build18-target-controls/target-controls.json \
  --output /tmp/build18-target-controls/target-controls-compact.json
python3 port/dreamcast/tools/cloud/build18/compact_receipt.py \
  --input /tmp/build18-target-cost/target-cost.json \
  --output /tmp/build18-target-cost/target-cost-compact.json
python3 port/dreamcast/tools/cloud/build18/compact_receipt.py \
  --input /tmp/build18-native-cost/target-native-cost.json \
  --output /tmp/build18-native-cost/target-native-cost-compact.json
```
