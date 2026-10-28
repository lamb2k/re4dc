# Build 26 validation

The baseline is `9a66e3fce8899f69378f12b5f9517f297f1fa314` on `origin/t15/int`.
All three new controls default to zero. The target gate derives the public
compiler commands from Make, using the pinned Build 24 GCC 15.2.0 / binutils
2.45.1 toolchain and pinned public KOS/SH4ZAM headers. Original executable hashes
are checked against the retained Build 24 toolchain receipt.

## Target gates

`build_controls.py` checks the complete ten changed existing translation units:
game main, effects, model bridge, actor, generic model, scenery, UI, legacy PS2
world, shared chunk submission and QA menu. It also compiles the new audit core
when enabled. The disabled matrix compares the baseline with all controls
absent, each of the three controls explicitly zero, and all three explicitly
zero, for `QA_LINK=0` and `1`: 200 exact comparisons of complete preprocessed
source and target object bytes. Debug records and preprocessor line markers are
consistently absent; object bytes are neither normalized nor stripped.

The Make flags and full platform/game object lists must also match the baseline
when disabled. Invalid empty, multiword and nonbinary controls are rejected.
Enabled arms are audit, audit plus link, either fix independently, both fixes,
audit plus both fixes, and the latter with actor setup/bytes/clip reuse, scenery
gather, effect setup, `DRAW_SETUP_AUDIT=1` and `DRAW_SETUP_AUDIT_XLU=1`.
Relocatable linking checks that every new audit reference resolves. Ordinary
game, device and transport dependencies are intentionally left to the game link.

`NMR_POOL_LOD=0` is a validation-only override in both baseline and candidate:
the selected chapter-2 pool option requires private Ganado assets absent from
the public recipe. This does not modify the release recipe. These checks prove
translation-unit identity and enabled compilation, not a complete game image,
captured scene, console frame or gameplay acceptance.

The gate freezes source and dependency hashes and rejects a run if a relevant
file changes during compilation. Only the final frozen receipts are published.
The final [OFF receipt](receipts/target-off.json) passes all **200** comparisons
and the final [ON receipt](receipts/target-on.json) passes all **seven** enabled
compositions. Their 277 and 287 source/dependency hashes respectively match the
delivered tree, including the QA page-preservation/backpressure producer fix.
`production_metrics.py` reports object-section deltas and relevant compiler
local stack frames. Relocatable allocated bytes include BSS; these are not
post-link image sizes or system-memory watermarks.

The [production section/stack receipt](receipts/production-metrics.json) records
these deltas against the matching `QA_LINK` baseline:

| Enabled profile | Executable bytes added | Allocated bytes added, including BSS | BSS added |
|---|---:|---:|---:|
| Actor fix alone | 1,160 | 1,163 | 0 |
| World fix alone | 960 | 960 | 0 |
| Audit, link off | 6,072 | 14,676 | 5,200 |
| Audit, link on | 6,316 | 19,053 | 9,332 |
| Audit and both fixes, link on | 8,440 | 21,180 | 9,332 |

The production actor clip local frame changes 556→684 bytes, with a separate
36-byte front-classifier frame. The world clip local frame changes 560→572
bytes, with a 24-byte decoded-corner lambda. The QA link-pump local frame changes
2264→2708 bytes; telemetry and its step helper are inlined. `snap_diag` remains
2280 bytes and the new diagnostic-row helper is 176 bytes. Audit-enabled QA
BSS grows by 4096 bytes with link off and 8228 with link on; the latter includes
the bounded pending-snapshot storage. The audit core contributes another
1104 BSS bytes. These local frames are not a measured complete call-stack peak.

## Target cost windows

The cost tools execute the compiled SH4 instructions on bounded synthetic
inputs. The retained SH4 instruction scheduler prices warm-I and cold-I runs
separately, with perfect D-cache. Load/store counts include literal-pool and
stack accesses. Unique 32-byte data lines are touched addresses, not cache
fills, bus transfers or misses. All geometry and counters are synthetic.

* `counter_cost.py` executes the production 133-counter core, including real
  linked newlib memory routines, across 14 states. It checks saturation,
  inactive/paused calls, room changes, sealing, skipped ticks and snapshots.
  The isolated increment wrapper costs 20 warm / 51 cold-I cycles, 5 loads,
  1 store and 3 unique lines. Begin/seal cost 295/370 and 336/418 cycles.
  An inline instrumentation site can allocate registers differently from this
  isolated wrapper. Formatting and modem work are outside this window.
* `world_source_cost.py` retains the production whole/subset gather bodies and
  indexed accessor. All three feed the same synthetic six-u16 sum/store
  consumer. Fourteen workloads cover sparse, full, repeated, aliased, duplicate
  and empty selections. A 64-vertex meshlet with three consumed corners costs
  1686/1813 cycles with whole gather versus 140/228 indexed, with loads
  367→44, stores 209→15 and unique lines 116→12. Package pointers are already
  resolved; real vertex decoding, projection, clipping and submission are
  excluded. This is a source-acquisition window, not a complete draw.
* `actor_front_cost.py` includes the complete production actor translation
  unit. It executes `Part::clip_strip`, source reconstruction/projection, the
  cached-front helper and actual candidate RAM-packet writes, in 18 workloads
  with front/reuse controls independently off/on. The shared clipper records
  every prepared vertex/opacity byte and returns zero in all arms. Its maths,
  baseline output and TA/device work are therefore unpriced. Slow-edge inputs
  must remain byte-identical; candidate cached packets are checked independently.
  A 64-vertex skinned crossing strip with one near vertex and 61 front triangles
  costs 99057/99758→27971/29082 cycles with reuse off. Loads change
  26942→7286, stores 10222→4634, unique lines 158→308 and observed stack
  720→904 bytes. The extra lines include actual candidate output omitted by
  the baseline clipper stub. With reuse on, warm cycles change 40051→28047
  and observed stack 740→1060. The all-near adverse control regresses:
  99057→105925 warm cycles without reuse, and 40051→57569 with reuse.
  These regressions and the larger stack must remain visible in the hand-back.

The actor fixture linked text grows 1088 bytes in either reuse composition;
`Part` grows 116→120 bytes in this profile. The complete production object
delta is reported separately. Cached projection rounding is a render
approximation; the host production-clipper fixture covers output/cull/UV/alpha
contracts independently of this bounded cost fixture.

## Whole-frame sensitivity — MODELLED

Assume an unchanged, unpriced remainder of **30 ms** in each arm, ten instances
of the 64-vertex skinned crossing strip above, and one hundred instances of the
64-vertex/three-corner world source window, at 200 MHz. The candidate additionally
pays one thousand isolated audit-hit costs plus one begin/seal pair. Using warm
piece costs gives **35.795850 ms → 31.571705 ms**, a **4.224145 ms** reduction.
The candidate observer portion is 0.103155 ms. This is an explicit sensitivity
calculation with assumed frequencies and a fixed omitted remainder, not a
prediction for a room, the barn or a whole console frame. In particular, the
omitted old clipper/output work is not measured. Cold-I numbers above describe
isolated pieces; they are not added as though every function starts cold in a
real frame.

## Reproduction

Use fresh output directories outside the checkout. The compiler/header paths
below are arguments, not dependencies on a maintainer's private filesystem.

```sh
python3 port/dreamcast/tools/cloud/build26/build_controls.py \
  --output /tmp/build26-target \
  --sh4-cxx /path/to/sh-elf-g++ --kos-root /path/to/kos \
  --sdk-root /path/to/sh4zam --toolchain-receipt /path/to/toolchain.json

python3 port/dreamcast/tools/cloud/build26/counter_cost.py \
  --output /tmp/build26-counter \
  --sh4-cxx /path/to/sh-elf-g++ --kos-root /path/to/kos --sdk-root /path/to/sh4zam

python3 port/dreamcast/tools/cloud/build26/world_source_cost.py \
  --output /tmp/build26-world \
  --sh4-cxx /path/to/sh-elf-g++ --kos-root /path/to/kos --sdk-root /path/to/sh4zam

python3 port/dreamcast/tools/cloud/build26/actor_front_cost.py \
  --output /tmp/build26-actor \
  --sh4-cxx /path/to/sh-elf-g++ --kos-root /path/to/kos --sdk-root /path/to/sh4zam
```

`--only off` and `--only on` split the target matrix without weakening either
half. `compact_receipt.py` retains hashes and every numeric cost/traffic value;
repeated commands are removed from cost receipts and target profiles are
interned. `recipe_values.py` independently records 313 public game / 317 public
QA Make values used by the inventory. The `receipts` directory also contains
the model, world and QA production-code host/sanitizer checks.
