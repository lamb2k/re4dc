# Build 25 — one part light path and offline character light bake

Branch: `codex/actor-light-fast-only-20261028`. Base: `origin/t15/int`
`7acd7d8fd6a828d4e596fdb57516a0655b4dc032`. Candidate only; Claude owns
merging, private appearance/gameplay qualification and release enablement.

## Runtime behavior

`ACTOR_LIGHT_FAST_ONLY=1`, default **0**, prepares one colour and three Q16
channel gains per model part. Existing eligible Leon and Ganado probes remain
live, including the shared probe used by model shadows. Ganado toggle policy
and each model's own fill setting remain in force. Other models select at most
three significant lights at the part centre, folding remaining contributions
into ambient. Material scale and diffuse behavior are handled in this setup.

The vertex loop writes the constant colour or multiplies source/baked RGB by
the prepared integer gains. It does not read normals, skin light directions
or lamp records, and does not evaluate lights. Gains above one survive until
the final channel clamp: the actual production-code fixture proves dark baked
RGB 64 becomes 96 with room tint 1 plus a half-strength flash, while source
alpha 73 remains unchanged. The gain bound keeps the integer product within
32 bits. This avoids silently suppressing flashes on dark baked surfaces.

The old directional and exact vertex-light passes and runtime rebaking are
excluded by preprocessing. Both ordinary actor submission and the shared
actor chunk/window path dispatch directly to the new pass. Geometry/resource
admission can still select the generic model renderer, but its lighting uses
the same part colour/gains; it cannot restore the old evaluator. The Makefile
requires `NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1`, which excludes the alternative
`native_actor.cpp` implementation from the image. Fast-only mode takes
precedence over the new base's `ACTOR_LIGHT_CAP`, including when its legacy
`GIGANTE_LIGHTS` prerequisite is off. BARN28 records these as fast parts.
The cap and diagnostics behavior is preserved when fast-only mode is off.

The static `MeshView` package's source-lit first-draw preparation also uses
the shared colour/gains. Its existing first-draw freeze and instance sharing
remain. This deliberately changes that legacy scenery/model fallback's
first-light appearance too. Native PS2 prelit world payloads are unchanged.

Production sites:

- `game/platform/native_actor_fast.cpp` and
  `game/platform/include/actor_light_fast_only.inc`: part preparation,
  shared probe use, both actor dispatches, scratch reduction and invariant.
- `game/platform/include/actor_light_fast_only.h`: typed colour, bounded
  integer multiply and diagnostics API.
- `game/platform/native_model.cpp`: generic representation fallback.
- `game/platform/native_static.cpp::light_part`: legacy first-light package
  preparation.
- `game/Makefile`: default, validation and target-specific define. No recipe
  is enabled. Production assembly and linker scripts are unchanged.

## What the approximation changes

Lighting no longer varies with vertex normal or vertex position within a
part. The bounded light selection, ambient residual, diffuse reduction and
source vertex-RGB multiplication change colour, highlight/shadow shape and
clamping relative to the former evaluator. Q16 introduces small rounding
differences. The legacy static-package change described above is also in
scope. Live part/probe changes still respond to room lights, flash and fire.

This changes rendering, not geometry, source alpha, pose, collision, events,
game state or AI. The owner must still run matched stills and gameplay
equivalence; source inspection and public fixtures are not that acceptance.

## Diagnostics and the zero invariant

The QA Diagnostics page and its existing QA_LINK telemetry contain three
`AL25` rows. They are **saturating lifetime totals**, not per-tick averages:

```text
AL25 lifetime parts=... fallback=0 MUST=0
AL25 avoided vcolour=... diffuse_scale=... lights_over3=... probe_decline=... basis=...
AL25 vertices flat=... multiply=... (avoided != fallback)
```

`fallback` is a live dispatch-invariant counter. It must remain zero. An
injected nonconstant dispatch in the fixture increments it to one without
entering any vertex-light evaluator, proving it is not a printed constant.
The `avoided` bins identify former decline conditions; they can overlap and
be nonzero. They are not actual fallbacks or a replay of the previous full
dispatch policy. `parts` counts preparations, including generic paths and
repeated/chunk submissions; the vertex totals cover native actor meshlet
inputs, not generic corners or unique vertices.

The existing Diagnostics pagination is enabled for this knob alone. Its
buffer is 4,096 bytes versus the old 3,072; combined `DRAW_SETUP_AUDIT` keeps
the existing 8,192-byte buffer. The actual production row/framing fixture
tests maximum unsigned counters and payload lengths through 8,191 bytes:
14 cases pass, rows occupy 244 bytes, and the largest tested datagram is
1,128 bytes, below the 1,200-byte limit. No hot-loop formatting or allocation
was added.

## Offline light/AO bake

The separate default-off tool flag is `--bake-static-light [0|1]`. The tool
consumes the existing approved PS2 render-mesh/rig exchange; it does not add
another geometry or rig converter. Absent/zero preserve input bytes exactly.
Enabled mode also preserves the original mesh/source bytes and emits a
SHA-bound RGB palette, little-endian u16 corner mapping, settings and manifest.
Deterministic BVH-accelerated AO preserves normal/material/UV/source-info seams.

The [format, pack contract and Leon/em12 commands](../../tools/cloud/build25/CHARACTER_LIGHT_BAKE.md)
include reproducible hand-authored examples, not extracted characters. Each
has seven positions, two bones, three triangles, nine corners and three RGB
entries: 9 palette bytes plus 18 corner-index bytes. Leon's example excludes
the roof occluder; em12 retains it and obtains AO in the range 0.4–1.0.

The local packer must preserve original alpha and carry the source-corner
mapping through its existing reindex/strip pass, set `material_vertex=1` and
`ambient_vertex=0`, and supply room tint plus live flash/fire while excluding
the static lamps already baked. The public checkout does not contain that
private final packer. This hand-back supplies the requested dataset and
contract; it does not claim repacked or appearance-approved game assets.

Static shading/AO is attached to the bind pose, sampled at vertices, rounded
to eight-bit RGB and used as an approximate multiplier for direct shadowing.
The tool itself adds zero game cycles, loads/stores, 32-byte lines, code,
stack, heap or VRAM before assets are repacked: **MODELLED whole-frame delta
0 ms for the offline tool alone**. Final resident colour/index sizes must be
measured on the packed assets, rather than inferred from interchange bytes.

## Public qualification

- **32 byte-identity comparisons**: complete preprocessed source and SH-4
  objects for the four changed translation units, new knob absent and zero,
  each with `QA_LINK=0` and `1`, against the integration base. Debug records
  and line markers are consistently omitted. These comparisons were rerun against the final
  integration base after resolving the cap/link28 overlap.
- **Six enabled target compositions**: public recipe, QA_LINK, probe off,
  old light controls off, setup/bytes/clip, and CAP/BARN28/DSA/QA_LINK
  composition with the old GIGANTE prerequisite off. Actual selected
  flags, compilation, relocatable links and absence of old evaluator symbols
  are checked. Unsupported knob values/prerequisites are refused.
- **Actual actor translation-unit host tests**: four profiles with
  65,653 / 65,654 / 65,655 / 65,654 controls, also under ASan/UBSan. These cover source
  immutability, zero-to-eight lights, diffuse/material/vertex flags, exhaustive
  integer colour multiplication, alpha/index preservation, Leon flash response,
  Ganado shared-probe freshness, the invariant guard, and CAP/BARN28
  precedence with zero BARN28 slow parts/vertices. LeakSanitizer alone
  is disabled because the sandbox cannot inspect process task lists.
- **Bake**: 14 test methods, 250 BVH/full-scan ray comparisons, invalid
  geometry/rig/settings, exact off bytes, deterministic enabled data and
  stale/tampered binding refusal.
- **QA framing**: 14 actual-production formatting/part-splitting cases with an
  accepting transport. The transport backlog/drop policy is outside this
  formatting fixture's scope.

The target is GCC 15.2.0, binutils 2.45.1 and newlib 4.6.0, with pinned KOS
`804b3195` plus the repository PVR patches and SH4ZAM `33fa4850`. Restored
compiler executable hashes match the preceding Build 24 toolchain receipt.
These are public translation-unit/fixture proofs. They do not establish a
complete linked game image, private asset admission, console timing or the
owner's still/gameplay/memory gates.

## Cost and size

The cost fixture executes the production SH-4 part fold and colour pass,
with `ACTOR_EXACT_FAST=1` as its old exact reference. Five former-decline
cases at 16, 64 and 128 inputs pass (15 cases). It uses the legitimate public
`ACTOR_PROBE_LIGHT=1` profile; private Ganado probe-2 timing is not claimed.
All reference lamps are one unit from the input positions, restricting the
approximate reciprocal instruction to the already qualified `FSRRA(1)` case.
Independent finite-range FTRC controls cover the Q16 conversion. Small external
identity hooks isolate the caller; their calls are counted, their real game
lookup cost is unpriced. No new production assembly or linker work is used.

Warm and initially cold 8 KiB I-cache cycles use the existing scheduling model
with perfect D-cache. Loads/stores are executed cached operand instructions;
32-byte lines are unique demanded data lines, including stack, output and
PC-relative literals. They are **not cache misses or bus transactions**.
Fold and pass footprints overlap and must not be added as unique lines.
The pass fixture includes its Part setup and preserves per-vertex alpha.
Transform/deformation, clipping, TA/SQ/device waits and real D-cache penalties
are excluded. Cold-I results depend on the fixture layout.

### Per-part light setup

| Former decline | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Loads OFF → ON | Stores OFF → ON | 32-byte lines OFF → ON | Peak fixture stack B OFF → ON |
|---|---:|---:|---:|---:|---:|---:|
| vertex-colour | 971 → 1,880 | 1,386 → 2,673 | 231 → 288 | 336 → 162 | 57 → 36 | 944 → 284 |
| material-scale | 985 → 1,884 | 1,410 → 2,665 | 236 → 289 | 336 → 162 | 58 → 36 | 944 → 284 |
| eight-lights | 2,182 → 3,949 | 2,948 → 4,776 | 514 → 629 | 480 → 317 | 77 → 45 | 944 → 284 |
| diffuse-unclamped | 979 → 1,850 | 1,394 → 2,619 | 233 → 286 | 336 → 162 | 57 → 36 | 944 → 284 |
| leon-low-material | 1,017 → 1,884 | 1,490 → 2,734 | 246 → 333 | 339 → 177 | 61 → 53 | 944 → 272 |

### Per-piece colour pass, 128 input vertices

| Former decline | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Loads OFF → ON | Stores OFF → ON | 32-byte lines OFF → ON | Peak fixture stack B OFF → ON |
|---|---:|---:|---:|---:|---:|---:|
| vertex-colour | 102,380 → 11,922 | 103,173 → 12,142 | 20,986 → 2,090 | 3,061 → 177 | 268 → 191 | 880 → 184 |
| material-scale | 100,853 → 3,987 | 101,690 → 4,204 | 20,471 → 683 | 3,060 → 178 | 267 → 191 | 880 → 184 |
| eight-lights | 168,978 → 3,987 | 169,821 → 4,204 | 32,706 → 683 | 3,775 → 178 | 284 → 191 | 880 → 184 |
| diffuse-unclamped | 98,549 → 3,987 | 99,386 → 4,204 | 20,471 → 683 | 3,060 → 178 | 267 → 191 | 880 → 184 |
| leon-low-material | 100,427 → 3,987 | 101,326 → 4,204 | 20,373 → 683 | 3,076 → 178 | 271 → 191 | 880 → 184 |

Every enabled colour-pass case reads **zero position and normal bytes**.
For the 128-input material-scale case, demand-line visits fall from 23,531
 to 861; this is less repeated traffic, not a measured miss-rate claim.
The complete receipt retains 16/64-input cases, per-region bytes and lines,
cold-I fills and model/trace hashes.

### Object code, state and stack

| Public QA object | Executable bytes OFF | Executable bytes ON | Delta |
|---|---:|---:|---:|
| `native_actor_fast` | 60,676 | 50,540 | -10,136 |
| `native_model` | 14,400 | 10,584 | -3,816 |
| `native_static` | 71,108 | 70,664 | -444 |
| `qa_menu` | 12,438 | 12,918 | +480 |

Across these objects, executable sections shrink **13,916 bytes** and total
allocated sections shrink **12,834 bytes**. Zero-fill grows 1,056 bytes:
36 bytes of actor counters, minus four generic-model bytes, plus the 1,024-byte
QA buffer increment. With DSA already enabled its larger QA buffer is reused.
These are object section counts, not a final ELF/linker-placement or heap-floor
claim. No new runtime allocation is made.

Compiler-reported function stack frames are 520 → 268 bytes for old
`build_lights` versus `fast_only_lights`, and 716 → 44 bytes for
`pass_lights_exact` versus `pass_fast_only`. Dynamic fixture peaks above include
caller setup and are a different measure. `Lights` shrinks 568 → 168 bytes.
Temporary skin tables request 114 → 65 bytes per palette entry, saving 49 bytes
per entry before allocator rounding; position/palette semantics are unchanged.

### Whole-frame figure — MODELLED

A deliberately synthetic sensitivity frame contains **42 parts × 128 input
vertices**, all using the material-scale exact-light case, at 200 MHz. Hold
**an assumed 30.000 ms of all other frame work** constant. Lighting costs
21.38598 → 1.23291 ms; the resulting whole frame is
**51.38598 → 31.23291 ms MODELLED**
(delta -20.15307 ms).

This is an exact-fallback-heavy scaling example, **not a barn/r101 prediction**.
It does not subtract these synthetic costs from the queue’s 47.8 ms reference
or explain the owner’s 21 ms barn model bucket. Actual light-path incidence,
input vertices and nonlighting work must be measured by the local owner.
All other synthetic scenarios are in the receipt; a real whole-frame delta
remains unmeasured.

## Reproduce and owner hand-back

The scripts and compact receipts live in
[`tools/cloud/build25`](../../tools/cloud/build25). Run from the repository root:

```sh
python3 -B port/dreamcast/tools/cloud/build25/runtime_host.py --output /tmp/b25-host.json
python3 -B port/dreamcast/tools/cloud/build25/runtime_host.py --sanitize --output /tmp/b25-san.json
python3 -B port/dreamcast/tools/cloud/build25/test_character_light_bake.py -v
python3 -B port/dreamcast/tools/cloud/build25/qa_contract.py --output /tmp/b25-qa
```

`build_controls.py`, `cost_build.py` and `cost_run.py` take explicit scratch
output and toolchain paths; their `--help` and committed receipts give the
exact public profile and input hashes. Use fresh output directories. No
private assets or synthetic success stubs are supplied to the game build.

Owner checks/questions are also recorded under **Open questions back to
Claude** in `CLOUD_AGENT_QUEUE.md`. Before enablement, retain exact recipe and
asset hashes; verify `AL25 fallback=0` on Leon/Ganados/partners/bosses/props,
near/inside clipping, opaque and translucent paths, and deliberately triggered
generic representation fallbacks. Compare flash/fire, model shadows and
legacy first-light scenery. Run the complete off-image identity, gameplay
equivalence, s30/memory and console checks, then pack and judge Leon/em12.
