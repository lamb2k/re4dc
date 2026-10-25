# World policy and WC24 error follow-up

This directory contains reproducible public controls for the
[follow-up report](../../../docs/cloud/WORLD_POLICY_CENSUS_FIX_20261024.md).
The [policy guide](policy_README.md) covers read-only inspection, explicit
original-policy control preparation and converter field diagnostics.

The owner's original-data control already has `err=0`. Its SLI1 wash and
SDS1 rejection remain the Build12 decisions. This patch adds useful failure
evidence; it does not reopen either layout or claim a 2 ms world.

## Runtime use

Keep the ordinary census recipe and add `WORLD_CENSUS24_ERRORS=1` only for a
diagnostic build. The new knob defaults to zero and requires
`WORLD_CENSUS24=1` (including its existing QA/renderer dependencies). No recipe
in this patch enables it. The Make rule rejects empty, multiple and unsupported
values. With it absent or zero, complete affected translation units and
objects remain identical to validation base `dd6b66b9`. Publication base
`8c992120` adds only the new owner queue answers; runtime and tool inputs are
unchanged between those bases.

An enabled build emits the normal `WC24` line, followed at window seal by
bounded `WC24E` lines. Correlate the same sequence `q` and room. The summary
contains `total`, `bins`, `spill`, `wrap` and `match`; bin rows contain the
reason, call site, path, phase, wait, count, first tick and two raw evidence
words `a`/`b`. These words are site-specific scalars, not pointers to external
data. Depth/far validation records float bit patterns where stated in source.

The QA census page shows the same details after its original 25 rows and
before PM14 rows. The existing pagination handles those lines. There is no
per-vertex or per-fault log. A maximum of 32 bins plus spill bounds storage
and seal output. `total` is the original aggregate count, including existing
nested guards; it is not a bitmask or a deduplicated incident count.

Specific `first()` tags preserve failure context before later phase changes.
The generic ps2 pass fallback/abort guard reports pass-level evidence and can
carry Selection as its phase. An `unspecified` row remains possible for an
unannotated no-argument fault. Spill and wrap stay visible, and bins+spill
reconcile with the existing aggregate modulo uint32 arithmetic. Nonzero
errors still invalidate a timing acceptance window.

## Public reproduction

Run from the repository root and choose fresh output directories. These
commands use no private game packages, captures, disc images or certificates.
Host controls use `g++`; the target commands require the verified pinned
Dreamcast toolchain described in the [Build14 guide](../build14/README.md).

```sh
python3 port/dreamcast/tools/cloud/world_policy_fix/policy_controls.py \
  --out /tmp/world-policy-repro \
  --receipt /tmp/world-policy-repro-receipt.json

python3 port/dreamcast/tools/cloud/world_policy_fix/census_errors_controls.py \
  --output /tmp/world-census-errors-host-repro

python3 port/dreamcast/tools/cloud/world_policy_fix/census_errors_hooks.py \
  --out /tmp/world-census-errors-hooks-repro \
  --receipt /tmp/world-census-errors-hooks-receipt.json
```

The core runner executes OFF/ON pairs normally and with ASan/UBSan. It checks
26 error/accounting/lifecycle cases and three actual-core PM14 compositions.
Synthetic PMU responses remain **SIMULATED**, never hardware qualification.
The hook runner extracts current renderer guards and admission/refusal
blocks directly from source, then supplies explicit package/binding/camera
and shell-group edges. Its normal/sanitized OFF/ON pairs compare aggregates,
returns and edge-call counts, plus the diagnostic reason and first evidence.
It is not a geometry, PVR, full-renderer or gameplay-equivalence run.

Example target setup for the SDK restored in this workspace:

```sh
RE4DC_FIX_CXX=/tmp/re4dc-sdk-20261024/rootfs/opt/toolchains/dc/sh-elf/bin/sh-elf-g++
RE4DC_FIX_KOS=/tmp/re4dc-sdk-20261024/kos
RE4DC_FIX_SDK=/tmp/re4dc-sdk-20261024/sh4zam
RE4DC_FIX_PROOF=/tmp/re4dc-sdk-20261024/verification.json

python3 port/dreamcast/tools/cloud/world_policy_fix/census_errors_target.py \
  --output /tmp/world-census-errors-target-repro \
  --sh4-cxx "$RE4DC_FIX_CXX" --kos-root "$RE4DC_FIX_KOS" \
  --sdk-root "$RE4DC_FIX_SDK" --toolchain-receipt "$RE4DC_FIX_PROOF"

python3 port/dreamcast/tools/cloud/world_policy_fix/census_errors_cost.py \
  --output /tmp/world-census-errors-cost-repro \
  --sh4-cxx "$RE4DC_FIX_CXX" --kos-root "$RE4DC_FIX_KOS" \
  --sdk-root "$RE4DC_FIX_SDK"
```

The target gate verifies GCC 15.2.0, binutils 2.45.1, newlib 4.6.0, KOS
`804b3195ebd1a06a27cc2b3a5eacf7a2429040a3` and SH4ZAM
`33fa4850cacb30dd0ad35485ef035526ec4ce782`. It records Make-derived flags,
44 complete OFF comparisons, three enabled partial links, nine dependency
refusals and compiler-emitted core FPU checks. It does not link the full game.

## Cost scope

The cost runner compiles the actual core with Make-derived flags and fixed
HOST clock/thread/IRQ adapters. It executes real SH4 instructions for normal
scope/tick work, first/repeated/spilled faults, clear and seal bookkeeping.
An attempted formatter call is rejected by the instruction runner; it cannot
silently count that work as free. The separate production target object
sizes/stacks include real KOS-facing code.

Warm/cold-I cycle figures assume a perfect D-cache. Traffic counts retain
every executed load/store, byte and 32-byte line, with separate bookkeeping
regions. Literal and stack placement affects total line unions. The weighted
frame scenarios use an explicitly assumed 1,000 scope sequences, one drawn
tick, no skipped ticks and a 300-draw seal at 200 MHz. The no-fault increment
is 0.110066 ms; four faults finding the last of 32 bins give 0.117197 ms:
**MODELLED core overhead only**. Add unpriced renderer tags, formatting,
serial, hardware timer/IRQ and memory wait costs. No console/world speedup,
real r101 frequency or universal observer subtraction is claimed.

## Receipts

| File | Evidence |
|---|---|
| `policy-receipt.json` | 146 checks; converter identity; production refusals and explicit synthetic provenance positives; C++ origin lookup parity |
| `receipts/census-errors-host.json` | Actual core lifecycle/accounting and PM14 OFF/ON pairs, normal and ASan/UBSan |
| `receipts/census-errors-hooks.json` | Bounded source-extracted renderer annotations with exact aggregate/edge controls |
| `receipts/census-errors-target.json` | Pinned complete target TUs, OFF identity, enabled partial links, sizes/stacks and Make rejections |
| `receipts/census-errors-costs.json` | 24 actual-opcode cases, warm/cold-I cycles, traffic, peak fixture stack and explicit MODELLED scenarios |
| `receipts/publication-base.json` | Integration base and publication scope |

Large receipts use the existing lossless `RE4DC_COMPACT_RECEIPT1` format from
[`build12/compact_receipts.py`](../build12/compact_receipts.py). A `$ref` names
a pool entry; `expand_receipt(document)` reconstructs the full parsed JSON
exactly. Original receipt byte length and SHA256 are retained. No metric,
command or source hash is dropped. Small receipts may remain plain JSON.
