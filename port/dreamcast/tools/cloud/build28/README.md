# Build 28: QA link review controls

The console change is selected by `QA_LINK=1 QA_LINK_REVIEW28=1`.
`QA_LINK_REVIEW28` defaults to **0**, adds no definition when off, and is inert
when `QA_LINK=0`. It changes only the selected QA transport, menu or benchmark
translation units. The Pi service and PC client opt in separately with
`--review28`; see [the companion README](../../qalink/README.md).

The complete hand-back is
[docs/cloud/handbacks/build-28.md](../../../docs/cloud/handbacks/build-28.md).
[VALIDATION.md](VALIDATION.md) gives the pinned toolchain, commands, source
receipts, measured scopes and any outstanding gate.

## Controls

- `transport_host.py` includes the complete production `qa_link.cpp` and
  `qa_link_bench.cpp` translation units against synthetic KOS/network providers.
  Its fixtures cover ring bounds and wrap, receive priority, dropped/truncated
  packets, stall/disconnect handling, failed cleanup, credential lifetime,
  detached-thread stack reuse, bounded log scanning and admission retries.
- `menu_contract.py` extracts the actual complete QA protocol block and its
  three driving entry points. It uses synthetic transport, clock, diagnostic
  and disc providers. Five actual diagnostic capacities exercise immutable
  multipart snapshots, real 2400-byte bulk admission, rejected sends, DIAG
  priority/busy replies, log cursors, recording statistics and link-loss input
  release. Sorting is compared with independent `std::sort` results.
- `build_controls.py` derives flags and object selection from the real Make
  rules, archives the integration base independently, and compares complete
  preprocessed source and SH-4 objects. It also checks invalid knob values,
  release exclusion and the new knob with `QA_LINK=0`.
- `sort_cost.py` executes the unchanged old RECORD loop and the actual new
  helper as SH-4 machine code, checks exact output and ABI preservation, and
  records warm/cold-I cycles plus cached-RAM opcode accesses and 32-byte lines.
- `ring_cost.py` executes the actual old/new transport ring code, including
  wraparound and refusal boundaries. It excludes sockets and the modem.
- `production_metrics.py` reports selected-TU code, allocated sections and
  compiler local stack frames before final linking. `compact_receipt.py`
  preserves the check results and source provenance without retaining bulky
  intermediate build paths.

Use fresh output directories; the scripts refuse to overwrite an existing
run. Host controls require a C++17 compiler and Python 3. Target controls use
the public pinned toolchain documented in the validation report. No private
mesh, room, game archive, image or recording is included.

## Final raw gate and historical syntax experiment

The final base is `568c357656efbec468db06a282c1f79caebaa725`, after a clean
rebase onto the newest integration. The full raw matrix **passes**: 56
absent/zero preprocessor/object comparisons, nine enabled compositions and
eight link-off/new-knob-on inert comparisons. These final receipts use
unmodified production compiler input with no syntax overlay.

At the initial Build 28 base, `8a55a9d5`, three QA-menu preprocessor conditions
contain literal backslash-`n` text. The pinned target compiler rejects the raw
base before it can produce an object. The optional `--syntax-control` mode
corrects **only those three tokens in compiler input on both sides** and records
the exact transformation. It never edits production source. A
`CONTROLLED_SYNTAX_PASS` is useful conditional evidence; it is **not** the
requested raw knob-off identity pass. The default mode performs no correction.
Upstream `568c3576` corrected the malformed directives and cleared this gate.
The optional mode remains solely to reproduce the historical experiment;
do not use it against the corrected final base.

ASan/UBSan host runs disable LeakSanitizer because the execution sandbox cannot
inspect `/proc` under ptrace. No leak-sanitizer, real scheduler, modem, Flycast,
console timing or full-disc claim is made by these controls.
