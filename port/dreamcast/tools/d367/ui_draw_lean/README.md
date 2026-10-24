# UI draw setup qualification

This lane uses the full public Test 22 Make settings and current `rr/recipe.conf`.
It imports only tools already present on its `t15/int` base. No game data,
Flycast, runtime assembly or production linker changes are needed.

## Reproduce

Run from the repository root. Set these paths for the local SH4 compiler,
KOS source checkout and SDK header tree. Every output directory must be new.

```bash
UI_CXX=/path/to/sh-elf-g++
UI_KOS=/path/to/kos-source
UI_SDK=/path/to/sdk
UI_OUT=/path/to/new-build9-evidence
UI_TOOLS=port/dreamcast/tools/d367/ui_draw_lean
UI_ARGS=(--sh4-cxx "$UI_CXX" --kos-root "$UI_KOS" --sdk-root "$UI_SDK")

python3 "$UI_TOOLS/build_controls.py" "${UI_ARGS[@]}" --output "$UI_OUT/controls"

python3 "$UI_TOOLS/native_build.py" "${UI_ARGS[@]}" --output "$UI_OUT/native-build"
python3 "$UI_TOOLS/native_run.py" --build "$UI_OUT/native-build/native-build.json" \
  --output "$UI_OUT/native-run" --extended

python3 "$UI_TOOLS/bridge_build.py" "${UI_ARGS[@]}" --output "$UI_OUT/bridge-build"
python3 "$UI_TOOLS/bridge_run.py" --build "$UI_OUT/bridge-build/bridge-build.json" \
  --output "$UI_OUT/bridge-run"

python3 "$UI_TOOLS/camera_build.py" "${UI_ARGS[@]}" --output "$UI_OUT/camera-build"
python3 "$UI_TOOLS/camera_run.py" --build "$UI_OUT/camera-build/camera-build.json" \
  --output "$UI_OUT/camera-run"

python3 "$UI_TOOLS/summarize_receipts.py" \
  --controls "$UI_OUT/controls/build-controls.json" \
  --native-build "$UI_OUT/native-build/native-build.json" \
  --native-run "$UI_OUT/native-run/native-controls.json" \
  --bridge-build "$UI_OUT/bridge-build/bridge-build.json" \
  --bridge-run "$UI_OUT/bridge-run/bridge-controls.json" \
  --camera-build "$UI_OUT/camera-build/camera-build.json" \
  --camera-run "$UI_OUT/camera-run/camera-controls.json" \
  --output "$UI_OUT/measurement_receipt.json"
```

`build_controls.py` archives the exact base independently, generates its own
Make flags and headers, and compares both knob-absent and explicit-zero
preprocessing and raw objects with that base. It checks nine valid profiles:
public; `UI_QUAD_LEAN=0/2`; headers off; unordered/non-autosorted;
native messages off with valid dependencies; no viewport jitter;
accepted world knobs plus `SCENERY_SELECT_LEAN2`; and the three world recipe
knobs disabled. Five TUs are checked: native UI, bridge, ID, messages and GX.
Unchanged TUs also require ON identity. The receipt reconciles the **entire**
native, bridge and message production objects used by the target probes with
the independent public Make objects.

Host correctness uses the same generated profile and the real source/KOS bodies:

```bash
python3 "$UI_TOOLS/check_runtime.py" --profile "$UI_OUT/controls/on-profile/ui-profile.json" \
  --output "$UI_OUT/host-all" --mode all
python3 "$UI_TOOLS/check_runtime.py" --profile "$UI_OUT/controls/on-profile/ui-profile.json" \
  --output "$UI_OUT/host-sanitizer" --mode sanitizer
python3 "$UI_TOOLS/check_runtime.py" --profile "$UI_OUT/controls/on-profile/ui-profile.json" \
  --output "$UI_OUT/host-negative" --mode negative
```

## What is priced

* **Native drain:** complete compiled `ui_draw_quad`, its glyph branch, real
  `begin_pvr_packet`, scalar arithmetic and real newlib copies/clears. A typed
  texture metadata edge supplies actual layouts; an observed zero-cost
  `stream_send` edge excludes transport, upload, allocation and GPU services.
  Target cases use fully defined cached headers and compare every TA word,
  packet boundary, overlay increment and draw count.
* **Bridge:** complete compiled `re4dc_draw_id_quad`, including projection,
  palette and mask branches. Typed texture lookup, camera selection and native
  enqueue edges are synthetic. The unchanged matrix edge copies a unit matrix
  for an identity screen input; its copy cost remains in the fixture totals,
  while original SH4ZAM arithmetic cost is not claimed. Every 104-byte quad and
  mask descriptor is compared. These totals are scoped phase probes, not full
  HUD callback costs.
* **Message camera:** complete compiled message function, actual SDK ortho,
  verbatim existing scalar SH4 identity function and actual GX state functions.
  All 16 incoming matrix words and seven resulting compact words are compared.

The scalar interpreter uses normal RN/DN mode. Its additional conversions are
restricted to finite signed16 FTRC and exact small nonnegative
FLOAT(PR=1)/FCNVDS pairs; controls verify known words and reject out-of-domain
integers. General double arithmetic, FTRV/FSRRA, exception status, alternate
rounding and hardware cache behavior are outside its qualification.

Warm cycles use perfect I/D caches; cold-I starts the model's 8 KiB I-cache cold
once per complete probe, at a synthetic ELF layout. D-cache remains perfect,
DMA is disabled and store-queue cost is zero. The model does not drain final
completion. Demand bytes and 32-byte lines are actual traced accesses including
PC-relative literals, not cache fills or bus traffic. Do not sum distinct
per-call footprints as distinct lines for a frame.

KOS packed-color header compilation defines words 0..3; words 4..7 may remain
undefined after its cache-line allocation. Host cold-header checks therefore
compare defined words and every vertex. A separate full-word scalar stream
uses explicit initialized allocation markers; it does not claim deterministic
ignored hardware header tails. Cached-header target cases compare all words.

## Review receipts

`measurement_receipt.json` contains the source/recipe pins, OFF identity counts,
public object reconciliation, code/stack sizes and model/traffic rows.
`runtime_receipt.json` records the host matrix, sanitizer, negative controls and
exact-output scope. Raw ELFs, objects, disassemblies, traces and bulky JSON remain
in the local evidence directory and can be regenerated with the commands above.

The candidate comparison in the checked-in measurement receipt retains the
observed noinline/array and outlined-scalar rejections. Their archived source
snapshots are pinned by the original native build receipt. The final dimension
hoist is recorded separately against that accepted forced-inline stage; its
source copy exactly matches the final runtime. `native_build.py`
accepts an optional `--initial-source` snapshot and `--inline-probe` on an
outlined source to repeat that development comparison without runtime edits.

The final native-only refinement refreshed 36 OFF comparisons and retained
144 unchanged comparisons from the full qualification; the composite receipt
records all 180 final comparisons and both raw receipts. Reproducing the full
commands above directly checks all 180 against the final source. The optional
`--native-controls` argument to the receipt summarizer supports the incremental
route, verifying the same base objects and all unaffected source hashes.
