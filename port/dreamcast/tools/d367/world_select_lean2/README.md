# Build 3 world selection controls

These tools qualify `SCENERY_SELECT_LEAN2` against integration commit
`75229c8fa54d4a939095666036c8ee1c8f52e2fe`. They use public source and synthetic
mesh packages. They do not contain game data or claim a Flycast/console trace.

## Complete builds and Make contracts

Set `SH4_CXX`, `KOS_ROOT` and `SDK_ROOT` to the public SH4 compiler, KOS source
and SDK header roots. Use a fresh output directory for every invocation.

```sh
python3 port/dreamcast/tools/d367/world_select_lean2/build_controls.py --output /tmp/select2-build --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SDK_ROOT"
python3 port/dreamcast/tools/d367/world_select_lean2/verify_knobs.py --profile /tmp/select2-build/build-controls.json --output /tmp/select2-knobs
python3 port/dreamcast/tools/d367/world_select_lean2/build_guards.py --output /tmp/select2-guards --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SDK_ROOT"
```

`build_controls.py` archives the exact integration base to derive its own
Make recipes. It compares absent/zero recipe flags and generated headers to
the current tree, and checks that enabling the option adds only the
`native_static` define. It preprocesses/compiles complete `native_static`,
`native_ui` and `native_actor_fast` translation units for all 32 combinations
of the five earlier switches. In addition to the Make zero case, the static
zero arm explicitly defines the preprocessor macro to zero. The two unaffected
translation units also remain identical when selection lean2 is enabled.

Preprocessor line markers and debug line records are omitted consistently;
executable optimization and SH4 ABI flags remain those from the public Test22
recipe. Identical compiler inputs across otherwise different combinations
reuse an artifact, recorded with the compiler-input hash and original label.
Baseline/current and absent/explicit-CPP-zero inputs are separate compilations.
The receipts distinguish logical comparisons from unique compiler invocations.

`verify_knobs.py` checks actual Make commands for the new knob's values and
dependency, all prior-switch combinations, and the surrounding cone, PVS,
interior, quality, strip-group, foliage and transparency settings. It preserves
the existing rejection of `SCENERY_SUBMIT_BATCH=1` with `PS2_PVS=1`.
`build_guards.py` also compiles twelve accepted surrounding configurations,
comparing complete baseline/absent/zero objects and building the enabled arm.
No link, disc-memory or gameplay-state gate is claimed by these commands.

## Exact selection controls

```sh
python3 port/dreamcast/tools/d367/world_select_lean2/check_selection.py --output /tmp/select2-selection
python3 port/dreamcast/tools/d367/world_select_lean2/check_selection.py --output /tmp/select2-sanitized --sanitize
```

The host fixture extracts the actual `lean` namespace, `ScenerySelector`,
shared `chunk_select` include and `group_visible`, freezing the new helper
include into the generated source. Production `MeshPackage::adopt` validates
the synthetic R4IM v2/v3 packages before any selection call. It compares every
byte of the ordered poisoned Pick storage, semantic selection/accounting
counters and guard outcomes. Canaries bracket the output storage. Both runtime
SG settings and a wrapping initial counter value are exercised.

The corpus covers partial clusters, full-inside bypasses, LODs, empty levels,
1/2/4/8 groups, short and long runs, cone/cull cases, missing optional inputs,
adjacent float32 camera values, shears/reflections and the full u16 bounds
range. Direct helper controls enumerate every five-plane mask and group count
0 through 8, including empty, repeated and decreasing strip-end records with
different group boxes. Direct box controls include degenerate/reversed bounds,
signed zero, extreme finite values and nonfinite words. The nonfinite host
controls are comparison checks, not a claim of target fast-math semantics.

The full host run compiles the shared selector with all 32 earlier-switch
definitions and extra guard profiles. This is not a 32-way queue integration
test: complete-TU builds establish composition, and the target controls also
exercise the actual full/light selection contexts. Guard-active cases assert
independently that selection stays ineligible. The
sanitizer mode is one bounded off/on pair with AddressSanitizer and UBSan;
leak detection is disabled because it is unrelated to the stack/helper change.

Host comparisons do not execute SH4 instructions or TA submission. The tool
also asserts that the downstream `emit_pick`, `chunk_emit`, strip-walk caller
and gather consumers are unchanged from the base. Equal ordered picks and
ranges therefore preserve those existing consumers' inputs; target numeric
and compiled-cost controls are a separate evidence layer.

## Target measurements

The `target_*` tools compile the production source under the Make-derived
profile and execute selected paths in the retained SH4 instruction model.
Their receipts describe fixture boundaries, observed return edges, code/stack
size and architectural data traffic. Warm/cold-I cycle values are model
estimates. Repeated/unique 32-byte-line touches are not cache-miss counts.
The integration lane measures the actual frame on Flycast and console.

```sh
python3 port/dreamcast/tools/d367/world_select_lean2/target_build.py --output /tmp/select2-target --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SDK_ROOT" --cone-matrix
python3 port/dreamcast/tools/d367/world_select_lean2/target_run.py --build /tmp/select2-target/target-build-controls.json --output /tmp/select2-target-exact --no-model
python3 port/dreamcast/tools/d367/world_select_lean2/target_run.py --build /tmp/select2-target/target-build-controls.json --output /tmp/select2-target-cost --context light --sg-mode 1
```

The target build enables all five earlier optimization knobs through actual
Make assignments, and compiles off/on selection arms with cone support both
off and on. The exact command runs all 126 synthetic packages through both
runtime strip-group implementations and both full `MeshDraw` and light
`ScenerySelector` entries: 1,008 paired comparisons. It compares the entire
2,560-byte poisoned Pick buffer, including unused fields, padding and unwritten
capacity, plus all 63 accounting words. Expected simple outcomes are also
asserted independently. Unused capacity is compared between arms rather than
required to stay poisoned: the baseline can initialize the next `Pick` before
a cone rejection. Source/ELF hashes identify the frozen inputs; the runner
checks that its own model/interpreter inputs and each ELF did not change during
execution.

The scoped cost command repeats 252 paired comparisons and prices 74 cost
families with the public lean strip-group setting and light selector. Both
commands execute real SH4 compiler output for selection and its setup. They
do not execute geometry transformation, TA submission, queue replay, or the
renderer's `FTRV` path. The numeric interpreter and pipeline model are inherited
from the earlier qualified replay controls; their existing memory-event
self-checks are rerun. The complete-TU/32-combination build checks above remain
the evidence for switch composition outside these selector entrypoints.
Repeat `--case NAME` to price only the cases needed for a report; the final
report's cost receipt uses 24 such cases, or 48 paired comparisons, alongside
the full 1,008-comparison correctness receipt.

The cost corpus varies 1/2/4/8/32 tested meshlets per cluster and one/eight
clusters per part. It also varies 1/2/4/8 groups with one, two or five demanded
camera planes. The `mask1` case label means one plane; its actual right-plane
mask is `2`. Group masks in the receipt are the actual target arguments.
Fully-in/out meshlet families keep their parent cluster partly visible using
an unselected coarse LOD. These are controlled synthetic cases, not a room
population survey. Per-meshlet and per-cluster amortizations include the
constructor, first coefficient preparation and exit; finite differences across
sequence lengths can separate the repeated component without erasing those
first costs from the complete totals.

Warm cycles assume perfect instruction and data caches. Cold instruction-cache
cycles start an empty 8 KB instruction cache once for each complete part
sequence and still assume perfect data cache. Neither model prices bus,
DMA, store queues or final pipeline drain. Cold results depend on synthetic
ELF placement. Architectural load/store bytes include stack and PC-relative
literal reads; instruction fetches are excluded. The receipt separates meshlet
headers, cluster headers, group records, stack and other data. Whole-sequence
unique 32-byte lines and sums of per-meshlet/per-cluster interval line unions
are both retained. Intervals split at the first demand read of each record,
with entry and exit charged. The repeated line count is not a cache-miss count
or a prediction of external memory traffic.

To price a numeric-only control without changing its input bytes, make a
derived copy of the build receipt and case manifest, keep the original ELF and
binary fixture paths, and mark the selected case `cost: true` with its known
`clusters`, `meshlets_per_cluster` and `selected_level_meshlets` counts. The
reported bypass controls use the unchanged `whole-inside` and `whole-tested`
fixtures, both one cluster/one meshlet, for placement-inside and cluster-inside
respectively. Set `expected_visited_meshlets: 0` for these controls: the inside
shortcut picks meshlet indices without reading their headers. Run that derived
receipt with `--context light --sg-mode 1` in a
fresh directory; record the original build receipt hash with the derived one.
