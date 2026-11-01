# Build 17 target gates

These tools compile public source for SH4. They need the repository-pinned KOS
and SH4ZAM headers and the KOS stable compiler (GCC 15.2.0, binutils 2.45.1,
newlib 4.6.0.20260123). They do not need a game disc or private asset files.
Use a new output directory for each run.

## Complete translation units and default-off identity

```sh
python3 port/dreamcast/tools/cloud/build17/build_controls.py \
  --output /tmp/build17-target-controls \
  --sh4-cxx "$RE4DC_KOS_CC_BASE/bin/sh-elf-g++" \
  --kos-root "$RE4DC_KOS_BASE" \
  --sdk-root /path/to/pinned/sh4zam \
  --toolchain-receipt /path/to/toolchain-receipt.json
```

The gate archives integration base `ab31de24`, derives compiler commands from
each tree's actual Makefile, and compiles `dvd_read_safe.cpp`, `snd.cpp` and the
Make-generated `fs_iso9660.c`. For each of the fallback-2 and recipe-3/meter
profiles, both an absent knob and `DISC_PIO_FALLBACK=0` must match the baseline's
preprocessed source and object bytes. The explicit-zero arm additionally defines
`RE4DC_DISC_PIO_FALLBACK=0` during compilation.

The recipe parser reads the public build's selected release-knob file and all
ordered `CH2` appends in `rr/recipe.conf`. It accepts only literal assignment
words and the documented leading `$CH2` append; it never evaluates the shell
file. Missing-data overrides come from `build-public.sh`. Make generates the
ISO source through the production patch rule; the tool reconstructs other
generated headers from Make's dry run using the existing profile helper.

Enabled objects are also compiled for fallback 2 and recipe-like fallback 3
with the disc meter and existing DMA-wait knob. A relocatable link proves the
new validation and ISO cache-invalidation hooks resolve once. Ordinary game and
KOS dependencies remain unresolved at this stage. This is not a final game
link or proof of whole-image identity. Debug records are omitted consistently
in every arm, as in the existing public object gates.

`target-controls.json` records source hashes, exact Make and compiler commands,
compiler provenance, preprocessed/object hashes, executable/allocated/zero-fill
bytes, compiler stack usage, link checks and invalid-knob rejection checks.

## Controller and validator traffic/cycles

```sh
python3 port/dreamcast/tools/cloud/build17/target_cost.py \
  --output /tmp/build17-target-cost \
  --sh4-cxx "$RE4DC_KOS_CC_BASE/bin/sh-elf-g++" \
  --kos-root "$RE4DC_KOS_BASE" \
  --sdk-root /path/to/pinned/sh4zam
```

This compiles the production controller and state header under DVD's actual
Make flags, and the production stream-table validator under Snd's actual flags.
Deterministic callbacks provide device status and a synthetic clock. Controller
traces include that callback bookkeeping; the fixture transfers no payload.
The separate host fake-driver gate is responsible for proving restored bytes.

The existing SH4 instruction interpreter executes those compiled functions.
The existing hardware model prices the actual instruction trace twice: perfect
caches, and an initially cold 8 KiB instruction cache with perfect data cache.
The receipt includes loads, stores, bytes, unique 32-byte demand lines, repeated
line visits, stack usage, code size, actual state outcomes and exact request
LBA/count preservation. Architectural demand lines are not measured cache
misses or bus traffic.

BIOS execution, native semaphore/timer calls, IRQ/cache maintenance, device
waiting and PIO/DMA payload transfer remain **unpriced**. The synthetic clock
increments are scenario control, not measured elapsed time. These tools cannot
establish a PIO rate, door-load delay, movie bandwidth, or FPS result. The local
owner must measure the same files and sector counts on the affected DreamShell
loader and the known-working GDEMU configuration.

## Compact evidence for review

```sh
python3 port/dreamcast/tools/cloud/build17/compact_receipt.py \
  --input /tmp/build17-target-controls/target-controls.json \
  --output /tmp/build17-target-controls/target-controls-summary.json
python3 port/dreamcast/tools/cloud/build17/compact_receipt.py \
  --input /tmp/build17-target-cost/target-cost.json \
  --output /tmp/build17-target-cost/target-cost-summary.json
```

The summaries preserve source/object hashes, the identity matrix, exact
compiler flags with named path placeholders, profile overrides, helper stack
frames, all cycle/traffic values and limitations. Repeated Make expansions and
legacy per-function stack lists remain in the raw output. A SHA256 binds each
summary to its complete raw receipt. Zero uncached/store-queue/prefetch categories
are checked before being represented once in the cost summary.
