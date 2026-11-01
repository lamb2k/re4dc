# SCCN/SCPS validation and the chunk fallback counter

The Build34 repairs use the existing default-off switches. They do not change
the release recipe. Owner decisions, historical results and private commands
are in `docs/cloud/handbacks/build-34.md`; the complete translation-unit gate
is described in this directory's `README.md`.

## Reader changes

The real `native_static.cpp::scn21_open` now calls
`platform/include/scn21_validate34.hpp`. Both readers check the 16-byte header
length before copying it and require four-byte alignment before publishing the
borrowed typed pointers. They compare the existing version, package CRC, byte
length and relevant counts. Subtract-first, divide-first extent checks prevent
overflow from admitting truncated slot or record arrays. The SCPS reserved
word must remain zero, as written by the existing builder.

SCCN additionally requires the existing R4SG group range of 1–8, a complete
64-entry table, and enough complete eight-byte records. The table begins with
zero and has positive, finite, increasing entries. Every record index must be
below 64. Radius values must be finite and nonnegative; an active record must
have a positive radius and a nonzero quantized axis in the builder's
`[-127,127]` component range with squared length at most `128²`. These checks
use integer IEEE binary32 fields, so enabling fast math cannot remove the
NaN/infinity checks.

These are format checks. They do not prove that a finite radius, axis and
slope actually bound the source triangles. The public tests deliberately show
that an insufficient but finite radius of 1 passes format validation. The
trusted `scn21_build.py` source-geometry construction, package binding and
private visual/culling checks remain required. No new data authentication or
cone-certificate claim is made.

The reader still clears its borrowed pointers before each admission attempt.
Missing, stale or malformed sections therefore leave that feature off for the
room. Successful SCCN admission does not modify source bytes. Successful SCPS
admission performs the original slot reset on every open; it does not retain
header slots from a previous room. No allocation or new retained state is
introduced. The validation loops execute at section open, outside draw loops.

`SCENERY_CONE_SIGN` accepts `1`, `+1` and `-1` when `SCENERY_CONE` is enabled.
The Make check ignores the unused sign when the cone is off, preserving the
previous disabled configuration behavior.

## Counter change

The actual `chunk_sink_strips` dispatch now increments the existing
`chunk_backend_fallbacks` once when `chunk_backend` declines and
`ACTOR_LIGHT_FAST_ONLY=0`. A backend that accepts but reports draw failure is
not counted as a fallback. The increment stays inside the existing backend
guard and the lighting profile that contains the LCHK reader. The fast-only
profile retains its existing DFA fallback reporting without adding this
unreported increment. No return value or draw-selection behavior changes.

## Public host tests

Run from the repository root with new output directories:

```bash
python3 -B port/dreamcast/tools/cloud/build34/scn21_host.py \
  --output "$RE4DC_BUILD34_OUTPUT/scn21-host"
python3 -B port/dreamcast/tools/cloud/build34/scn21_host.py --sanitize \
  --output "$RE4DC_BUILD34_OUTPUT/scn21-asan"
```

The runner extracts the production loader, counter declaration and sink body
verbatim. External package/section providers and backend/Part return values
are controlled fixtures. Synthetic source triangles use the existing public
builder's actual `cone` function and table, including inactive records. No
proprietary payload is used.

The 12 loader compositions cover cone-only, piece-only and both, each with
the existing A/B and GC-asset controls off and on. The eight sink compositions
cover backend, fast-only lighting and DFA off and on. The test cases include
short exact allocations, missing/stale sections, misalignment, wrapped counts,
truncated tables/arrays, all illegal one-byte cone indices, non-finite and
unordered table entries, invalid radii/axes, pointer retirement, repeated slot
clearing, audit admission, and accepted/declined backend return paths.

On 2026-10-28 the normal and ASan/UBSan fast-math runs each passed **7,628
cases and 140,249 assertions**: 7,436 loader cases/138,857 assertions plus
192 sink cases/1,392 assertions. The sanitizer runner sets
`ASAN_OPTIONS=detect_leaks=0` because the execution environment prevents
LeakSanitizer from inspecting its task map. Address and undefined-behavior
checks remain enabled and fatal. The receipt records every source/fragment
hash and composition. This test is not a whole-game, full-image or console
qualification.

## Bounded SH-4 cost

Use the pinned compiler, KOS and SH4ZAM trees from the established toolchain
receipt:

```bash
python3 -B port/dreamcast/tools/cloud/build34/scn21_cost.py \
  --output "$RE4DC_BUILD34_OUTPUT/scn21-cost" \
  --sh4-cxx "$RE4DC_SH4_CXX" \
  --kos-root "$RE4DC_KOS_ROOT" \
  --sdk-root "$RE4DC_SH4ZAM_ROOT"
```

The fixture compiles the actual helper with Make-derived `native_static`
flags. Input arguments remain externally mutable so the compiler retains
runtime alignment, version, identity and variable-group extent checks.
Preparation is outside the measured interval. The measured interval includes
the thin input-loading wrapper, helper calls and any executed compiler/library
dependencies. The established interpreter fails on unsupported instructions;
the reused DIV0U behavior has its eight M/Q/T-state controls.

The final 2026-10-28 synthetic result was:

| Section / outcome | Warm cycles | Cold-I cycles | Load instructions | Store instructions | Distinct 32-byte data lines | Observed chain stack |
|---|---:|---:|---:|---:|---:|---:|
| Short SCCN refusal | 90 | 199 | 32 | 15 | 9 | 72 B |
| Valid SCCN, 4 records | 3,486 | 3,821 | 549 | 420 | 24 | 76 B |
| Valid SCCN, 128 records | 16,296 | 16,631 | 2,064 | 916 | 55 | 76 B |
| SCCN, final record has invalid index | 16,201 | 16,547 | 2,055 | 912 | 56 | 76 B |
| Valid SCPS, 128 slots | 120 | 283 | 32 | 12 | 7 | 32 B |
| Short SCPS refusal | 61 | 153 | 22 | 8 | 6 | 32 B |
| SCPS count overflow refusal | 124 | 287 | 33 | 12 | 7 | 32 B |
| Stale SCCN identity refusal | 142 | 352 | 40 | 19 | 11 | 72 B |

Warm cycles assume perfect instruction/data caches. Cold-I starts an isolated
8 KiB instruction cache cold, still with perfect data cache and the fixture's
synthetic layout. Data lines are touched addresses, not observed misses or
bus transactions. Stack is the observed bounded call chain in these cases;
the compiler reports 48 B local storage for the cone helper, 4 B for the
common header helper, and 20/28 B for the cone/piece wrappers.

At 200 MHz, the 128-record warm helper result is **0.08148 ms per section
open**. It is additional validation cost. It is not a per-frame gain, and
cannot be extrapolated to a real room's cost without its actual record count
and memory behavior. The measured SCPS helper excludes the unchanged slot
`memset`. All results exclude section I/O, package opening, GC asset auditing,
log output, geometry proof, runtime cone tests, data-cache misses and GPU
work. The fixture's linked code/data sizes are not the program's repair-only
size deltas; the complete target gate reports those separately.
