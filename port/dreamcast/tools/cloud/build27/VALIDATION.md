# Build27 target qualification

Baseline: `6be0a66ab59fa597a55aae7379fb09777d357bc1`. The receipts qualify
`WEP_MODULES_27=1` against that integration commit using the pinned GCC 15.2.0,
binutils 2.45.1, KOS `804b3195` and SH4ZAM `33fa4850` public toolchain. They
do not claim a complete game link, console run, or chapter playthrough.

## Controls and integration

[target-off.json](receipts/target-off.json) records **192 exact comparisons**:
six changed translation units, eight `WEAPON_WEP05` × `WEAPON_HEAP4` ×
`ARCHIVE_REUSE` compositions, absent and explicit-zero controls, and both raw
`-E -P` output and complete objects. Every comparison passed. Debug records
are omitted consistently; neither preprocessed text nor object bytes are
normalized for comparison. Make inputs and generated module selection are
also compared, with only checkout/output paths normalized in the Make-state
comparison.

[target-on.json](receipts/target-on.json) records successful compilation of
all six units in all eight enabled compositions. Each compiled module table
contains IDs 67, 50 and 56 exactly once, and the unchanged module generator
selects each corresponding module object exactly once. This includes the
existing `WEAPON_WEP05=1` composition. Partial links use the three real
generated module objects and resolve the new availability/refusal APIs and
entry points. Inherited game/KOS imports remain explicit. Empty, `2`, and
multiword new-knob values are rejected.

The units are `modules.cpp`, `read.cpp`, `pl_wep.cpp`, `item.cpp`, `sscrn.cpp`
and `t_option.cpp`. The public validation profile sets `NMR_POOL_LOD=0` on
both sides because private Ganado assets are unavailable. It retains the
recipe's `KOS_CACHE_P2=1`: the existing cache-audit preparation tool verifies
the pinned KOS source and creates its required public header overlay.

## Actual generated modules

[module-build.json](receipts/module-build.json) records complete source
compilation, the existing state linker script, intra-module aliases, partial
linking and export localization. The original weapon source remains unchanged.
The Make-derived final optimization is `-O1` for these three modules and
reference `wep11`; the existing hot reference `wep02` uses `-O2` and its
existing decompilation-preservation flags. No optimization recipe is changed.

| Module / ID | Executable bytes | Read-only data | Initialized data | BSS section | Allocated total | Largest local stack frame |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wep05 / 67 | 6,400 | 544 | 0 | 24 | 6,968 | 92 |
| wep06 / 50 | 6,888 | 544 | 0 | 24 | 7,456 | 96 |
| wep12 / 56 | 5,788 | 590 | 0 | 28 | 6,406 | 96 |

Wep12 has 25 bytes of writable BSS state plus three bytes of section
alignment. All three pristine-copy payloads are zero bytes. Their prolog local
frames are four bytes and epilog frames zero. Each module exposes exactly the
existing seven entry/state symbols. Their 82, 85 and 84 external imports are
all present in the union of the actually compiled existing `wep02` and `wep11`
imports; there are no new external names requiring a new provider. This
comparison does not re-prove inherited providers or their runtime behavior.

## Bounded costs and traffic

[entry-cost.json](receipts/entry-cost.json) executes the generated SH4 code
with synthetic global addresses and prices its observed instruction traces
using the repository hardware model. The registration prefix ends immediately
before the first `OSReport` call. Logging and the caller's return tail are
excluded. The epilog is executed through its complete return. Registered game
callbacks are checked but are never called by this target fixture.

| Actual code window | Warm cycles | Cold-I cycles | Loads / stores | Distinct 32-byte data lines | Observed stack |
| --- | ---: | ---: | ---: | ---: | ---: |
| wep05 registration prefix | 20 | 52 | 8 / 4 | 5 | 4 B |
| wep06 registration prefix | 20 | 51 | 8 / 4 | 5 | 4 B |
| wep12 registration prefix | 20 | 52 | 8 / 4 | 5 | 4 B |
| Each complete epilog | 4 | 26 | 1 / 1 | 2 | 0 B |

Warm uses perfect instruction and data caches. Cold-I starts the model's 8 KB
instruction cache empty while retaining a perfect data cache. Data lines count
observed addresses, including literal pools and stack accesses; they are not
measured cache fills or bus transactions. The synthetic binding layout affects
line counts. Module reset/load, archive I/O, creation, firing, reload, sound and
rendering costs are unpriced here. Separate actual-source host fixtures cover
weapon behavior and refusal controls at synthetic service boundaries.

**MODELLED whole-frame sensitivity:** assume 30 ms for all unpriced work and
one registration prefix plus one epilog in a synthetic switch tick. At 200 MHz,
`30 + (20 + 4) / 200000 = 30.000120 ms`. This is an explicit assumption-based
total, not measured frame time, and no speedup over missing-module failure is
claimed.

## Guard and module storage

[production-metrics.json](receipts/production-metrics.json) contains all eight
compositions and per-unit section/stack results. The following deltas combine
the six guarded objects with only the newly selected module objects, before
final linking or garbage collection. `ARCHIVE_REUSE` does not change these
deltas.

| Existing wep05 | WEAPON_HEAP4 | Added executable | Added allocated | Added BSS |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 20,560 B | 22,911 B | 156 B |
| 0 | 1 | 20,464 B | 22,811 B | 152 B |
| 1 | 0 | 14,160 B | 15,875 B | 108 B |
| 1 | 1 | 14,064 B | 15,775 B | 104 B |

With `WEAPON_HEAP4=1`, local frames for `ReadWepData` (568 B), `weaponLoad`
(20 B) and `cItemMgr::arm` (28 B) are unchanged. `debugWeapon` changes from
12 to 20 B. The new ID/file/availability helpers each have four-byte local
frames; the new revert wrapper has a 48-byte frame. Whole-TU maximum local
frames are unchanged. Compiler frame sizes are neither call-chain maxima nor
console stack watermarks.

## Reproduction

Run from the repository root. Output directories must be new. Paths below
refer to the toolchain used for the committed receipts; substitute equivalent
pinned paths when replaying elsewhere.

```sh
B27_CXX=/workspace/scratch/206a5d423cac/toolchain/restored/opt/toolchains/dc/sh-elf/bin/sh-elf-g++
B27_KOS=/workspace/scratch/206a5d423cac/toolchain/kos
B27_SDK=/workspace/scratch/206a5d423cac/toolchain/sh4zam
B27_TOOLCHAIN=/workspace/scratch/206a5d423cac/toolchain/toolchain.json
B27_OUT=/tmp/build27-qualification

python3 port/dreamcast/tools/cloud/build27/module_build.py \
  --output "$B27_OUT/modules" --sh4-cxx "$B27_CXX" \
  --kos-root "$B27_KOS" --sdk-root "$B27_SDK"

python3 port/dreamcast/tools/cloud/build27/build_controls.py \
  --output "$B27_OUT/off" --only off --sh4-cxx "$B27_CXX" \
  --kos-root "$B27_KOS" --sdk-root "$B27_SDK" \
  --toolchain-receipt "$B27_TOOLCHAIN" \
  --module-build "$B27_OUT/modules/module-build.json"

python3 port/dreamcast/tools/cloud/build27/build_controls.py \
  --output "$B27_OUT/on" --only on --sh4-cxx "$B27_CXX" \
  --kos-root "$B27_KOS" --sdk-root "$B27_SDK" \
  --toolchain-receipt "$B27_TOOLCHAIN" \
  --module-build "$B27_OUT/modules/module-build.json"

python3 port/dreamcast/tools/cloud/build27/entry_cost.py \
  --output "$B27_OUT/entry" --sh4-cxx "$B27_CXX" \
  --module-build "$B27_OUT/modules/module-build.json"

python3 port/dreamcast/tools/cloud/build27/production_metrics.py \
  --off "$B27_OUT/off/target-controls.json" \
  --on "$B27_OUT/on/target-controls.json" \
  --modules "$B27_OUT/modules/module-build.json" \
  --output "$B27_OUT/production-metrics.json"
```

`compact_receipt.py --input RAW --output NEW` removes duplicate command
material while retaining numeric evidence and hashes. Source/dependency
freezes, original executable hashes and raw-receipt hashes are retained in the
committed compact receipts.
