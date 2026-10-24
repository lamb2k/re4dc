# Effect-pool failure audit — 2026-10-23

Base: `origin/t15/int` at `ea969bb241f77291d2ca43d706c9dc2d1226ee76`.
Branch: `codex/effect-pool-audit-20261023`.

**Two source defects reproduced and fixed behind independent default-0 knobs:**
wrapped low-priority sprite recycling skips retirement; R117's light puzzle
dereferences beams whose allocation failed. These are separate from Mendez's
already-merged `EM35_ROUTINE_BYTES` fix. No pool capacity, rendering cap, retry
policy, or release-recipe default is changed.

## Confirmed defects and changes

### `ESP_POOL_RECYCLE=1`: retire the wrapped victim

`src/game/esp.cpp`, `cEsp::operator new` (`loop4`, line 396), has two searches for
an occupied, recyclable `m_Tool_flg & 0x40000` slot. The forward search calls
`PushEsp` before clearing it. The wrapped search went straight to `found` and
`memclr_asm`, losing the old destructor and bookkeeping. `PullEsp` then increments
the live count for the replacement.

A four-slot, completely occupied fixture with the next-search position at two
and a recyclable victim at zero demonstrates the defect:

| Observation after replacement | Original | Knob on |
|---|---:|---:|
| Actual occupied slots | 4 | 4 |
| `ActiveEspNum` | 5 | 4 |
| Old destructor calls | 0 | 1 |
| Owned synthetic resource remaining | 1 | 0 |
| Old owner's count / bitmap entry | Retained | Removed |

The excess live count also makes `nEsp - ActiveEspNum` underflow in the unsigned
headroom tests in `espgen00_Update` and `espgen02_Update`. Refusal diagnostics
still count actual failed requests; their live-count peak can be inflated.

The fix calls the same `ESPD_STEAL(); PushEsp(esp);` sequence in the wrapped
branch, before the shared `found` label. Jumps from free-slot searches still
land after it. The selected slot and search order are unchanged. Ordinary
allocation, outright refusal, and forward recycling have equal fixture outputs
with the knob off/on. Correcting wrapped recycling intentionally changes its
previously broken destructor/accounting behavior.

Destructor review: `cEsp12`/`cEsp16` retire vector-buffer parents;
`cEsp3f::Destruct` retires their children; `cEsp11` destroys a light;
`cEsp4e` calls `Cloth::Destroy` (frees its grid and clears its live flag);
the base and `cEsp4c` hooks are empty. These hooks do not resize/free the ESP
pool or allocate another sprite. The test executes the actual `cEsp3f` child
destructor too: forward and wrapped retirement can release two additional
slots, then return the selected parent slot without revisiting the search.
This does not establish correctness for corrupt/cyclic ownership data.

### `R117_EFFECT_FAILURE_SAFE=1`: tolerate missing puzzle beams

`src/st1/r117.cpp`, `r117_LightSet` (line 308), already maps a failed
`EspEstSetSelect` to a **null** `W->esp[i]`. Its consumers assumed success:

| Consumer | Original failure | Knob-on behavior |
|---|---|---|
| `r117_espEnd` (103), two mode-2 waits (616, 638) | Read completion byte `0xF9` through null | A missing beam has no animation to wait for |
| `r117_LightDirCalc` (385) | Read missing beam position every frame | Leave that object's direction unchanged |
| `r117_LightRotate` (709) | Read/write missing angle during and after rotation | Skip beam writes; retain all ten sleeps, object updates, and sound |

The normal completion-byte test and all non-null beam operations remain the
original operations. Correct and incorrect puzzle answers progress under all
seven nonempty beam-failure masks in the source-body fixture. No new success
condition, puzzle solution, or arbitrary timeout is introduced.

This is a failed-allocation repair. It does not add generation tokens to
successful handles. Whether a beam record is recyclable, and therefore could
leave a stale successful handle, needs its real record/lifetime data.

## Audit coverage and findings left unchanged

The reproducible census scans **1,728** public `.cpp/.c/.h/.hpp/.inc` files in
`src`, `include`, and `port/dreamcast/game`, excluding comments/string literals.
It retains both preprocessor arms and macro bodies. There are **1,807 request
calls**: 1,763 `EstSet`, 14 `EspEstSetSelect`, eight `PullEsp`, seven `EspSeqSet`,
five front/back `PullEspgen`, three `Esp3f_Alloc`, two each `PullEspEspgen` and
`SetEstTbl`, and one each `EspgenDataSet`, `EspgenSeqSet`, and `EfmSeqSet`.
The factory inventory also covers the 45 `new cEspXX` sites and their registered
creator table. All use the shared custom allocator.

The retained [request-sites.tsv](../tools/d367/effect_pool_audit/request-sites.tsv)
contains **2,925** source locations: requests, discovered effect-system wrappers,
and queries/owner/cleanup APIs. It includes water/hit/laser/gatling, SST, and event
front ends. Caller attribution is lexical: 66 sites, mostly macro bodies or
conditional function bodies, are explicitly marked `<unresolved scope>` rather
than omitted. `inventory.py` also emits every API reference and the full
pointer/pool-field census. This is exhaustive for the named source APIs, not
whole-program symbolic execution of all 1,763 call paths or asset scripts.

Returned handles and allocator decisions were reviewed at all 44 non-`EstSet`
request calls. The following contracts explain the important distinctions:

* `PullEsp` and front/back `PullEspgen` return **0 plus a shared non-null dummy**
  on exhaustion. `EspSeqSet` preserves that failure contract. A null-only test
  would be insufficient generally; R117 deliberately converts failure to null.
* Every direct `EspEstSetSelect` caller checks its status. The blood, laser,
  weapon, and room-laser callers use handles only inside success branches.
  R117 retains the handles, exposing the later failures above.
* `SetEstTbl` ignores `EspSeqSet`'s integer result, but both lens-flare consumers
  compare its pointer with `EspGetDmyPtr`, release their controller, and return.
* The four child-sprite pulls in `esp0a` guard success. `Esp3f_Alloc` clears its
  output, rolls back partial allocations, and its three consumers handle failure.
  The three standalone water/sand controller constructors return failure before
  touching the dummy. `EstSet` returns without publishing a controller on failure.
* `espgen10_Update` retries the failed record without advancing record/time.
  Generator 00/02 can return before advancing their lifetime on a headroom
  failure; their wait counters were already reloaded. Continuous pressure can
  therefore retain controllers, particularly at zero interval. These are retry
  policies, not a demonstrated enemy-state hang. Arbitrary dropping/timeouts
  would alter successful later effects and were not added.
* `EspEstSetSelect`'s early invalid owner/index/kind returns do not initialize
  `*out`, despite its comment. Its current callers test the status, and R117
  explicitly nulls failures. This is not the full-pool dummy path.
* `EspSeqSet`'s `0xFC..0xFF` model-effect route calls `EfmSeqSet`, then returns
  success with the dummy sprite even if the separate object allocation failed.
  It exposes no effect-model handle to the caller. This is unchanged source
  behavior, distinct from exhaustion of the sprite/controller pools.

Indirect state checks were reviewed too. The 70 `EspPullCoreKind` calls issue
cleanup-group identifiers, not slot handles; `EspgenGetCallNo` is sequence
metadata. `EffGetAreaState` reads player/camera area membership. In particular,
the wait at `src/st1/r11f.cpp:822` is **not** waiting for a particle: its area bit
is published by `EffSetAreaState` even when `SstSet` cannot allocate. Tool-state
callbacks from `esp11` adjust thunder lights/window colors, not attack completion.
Mendez has 32 void `EstSet` calls and no stored sprite handle or pool-count wait;
the catch callbacks advance on motion/routine state (`em35.cpp:1779,2503,2629`).
No source evidence here attributes the reported Mendez freeze to exhaustion.

One adjacent source hazard remains separate: `esp0a.cpp` directly copies whole
sprite objects at lines 123/128/186/190, bypassing `ESP_INFO_SET` despite copying
`Core_pEm`. Those modes deserve their own owner-count/bitmap fix and tests when
`GAME_ESP_OWNER`/`GAME_FX_SCAN` are enabled. This lane does not claim to repair all
owner bookkeeping.

## Verification and cost

**PASS: 48 pool controls and 36 R117 controls**, compiled on the host with
AddressSanitizer and UndefinedBehaviorSanitizer. LeakSanitizer is disabled
because the sandbox uses ptrace. The tests extract the actual source bodies;
platform/allocator dependencies are instrumented. The allocator signature alone
is adapted to avoid the host's different operator-new `size_t` ABI.

Pool controls cover refusal, free slots, forward/wrapped recycling, child-buffer
destruction, owner counts/maps off/on, and diagnostics. Five original R117 arms
are expected sanitizer failures; knob-on cases pass. Successful R117 cases
compare every completion-byte value, fixture-owned output byte, and the ordered
camera/sleep/sound/effect/menu action trace. Their off/on outputs are identical.

Complete `esp.cpp` and the `st1_3` overlay's `r117.cpp` compile with GCC 15.2.0
using their **actual Make-expanded Test22 public recipes**. Tests verify all four
knob combinations, real Make defaults/defines, and invalid-value rejection.
Baseline, absent, and explicit-zero **preprocessed sources and complete objects
are byte-identical**. Debug records are omitted consistently; this is program
object identity, not equality of debug source-line metadata.

| Complete translation unit / affected stack | Base | Both knobs on | Delta |
|---|---:|---:|---:|
| `esp.cpp` executable bytes | 5,560 | 5,560 | 0 |
| `esp.cpp` allocated bytes | 17,118 | 17,118 | 0 |
| Allocator stack | 24 | 20 | -4 |
| `r117.cpp` executable bytes | 10,060 | 10,116 | +56 |
| `r117.cpp` allocated bytes | 10,416 | 10,472 | +56 |
| R117 direction / rotation / mechanism stack | 100 / 80 / 136 | 100 / 80 / 136 | 0 |

Both BSS sizes are unchanged. The compiled original wrapped branch skips the
`PushEsp` call; the enabled branch reaches it before clearing. The code-size
neutral result reflects register/branch rearrangement, not absence of a fix.
These are bug fixes; no frame-rate gain is claimed.

Hashes, exact size/stack results, source inventory hashes, compiler flags and
test outcomes are retained in
[retained-results.json](../tools/d367/effect_pool_audit/retained-results.json).
The default-off object SHA-256 values are:

* `esp.cpp`: `6854fd6cb69b28170d8466d54566bdc1c8e60d83d4d40fe56077dcbface2150f`
* `r117.cpp`: `2f2e06d12427329cc2aa4fee46dcf66f4446aa6dece5e33d94500cb135410f76`

Reproduce from the repository root with fresh output directories:

```sh
python3 port/dreamcast/tools/d367/effect_pool_audit/inventory.py --output /tmp/fx-inventory
python3 port/dreamcast/tools/d367/effect_pool_audit/test_failures.py --output /tmp/fx-failures
python3 port/dreamcast/tools/d367/effect_pool_audit/build_controls.py \
  --output /tmp/fx-sh4 --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$PUBLIC_SDK"
```

No game data, Flycast, console, full image link, TA-word comparison, or measured
gameplay trace was used. Real room saturation frequency and presentation after a
dropped beam remain for the maintainers to check before enabling either knob.
