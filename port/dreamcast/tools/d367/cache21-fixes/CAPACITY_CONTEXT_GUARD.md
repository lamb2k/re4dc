# Refuse motion-capacity waits from protected contexts

This is a narrow successor to frozen capacity
`1f7c34e4fc7a72222fd99c81afe66d08f890aa9e`. Root approved this repair after
the separate safety review `aa7ae95d` (copied here as review-only `8c7aad64`).
It does not import or enable the old capacity candidate on current integration.
The existing `MOTION_CAPACITY` switch remains default zero; no recipe changes,
new allocation policy or budget expansion is included.

KOS `irq_disable` returns the complete saved SR. The old wait predicate refused
only IMASK `0xf0`, allowing partially masked critical sections and SR BL/RB
exception states. The new predicate requires a non-null thread, no active ISR,
IMASK zero and BL/RB clear (`old & 0x300000f0` must be zero). It retains the
same-thread lock and reader-lease exclusions. Every exit restores the exact
saved SR. It never enables interrupts to make a protected caller wait.

The already-locked internal admission path is still nonwaiting. Its ownership
check now also requires a non-null thread, so two null pointers cannot falsely
identify an internal lock owner. Valid internal metadata/reserve admissions keep
their existing reclaim/retry behavior.

## Actual-source host qualification

The existing frozen source/SDK fixture and sealed review test are reused.
`test_capacity_review.py` exports exact1f7 source and can overlay only the
selected successor native_motion.cpp. Exact source/header/test hashes and
commands bind each arm. Its raw-SR service adapter models the local KOS SR
save/mask/restore contract; exception observers stop unsafe old waits for
inspection. This is not SH-4 scheduler, target deadlock or gameplay evidence.

Baseline and successor ASan/UBSan arms cover all 16 IMASK values; BL, RB and both;
ISR state even with prior IMASK zero; null thread and same-thread reader pins.
Actual required allocation and capacity retirement refuse unsupported contexts
with zero `thd_pass` calls and identical prior SR. Baseline still characterizes
the old admitted partial-mask/exception waits. The successor accepts only the
unmasked ordinary-thread predicate case.

The existing simultaneous-pin/pointer-stability, unmasked other-thread pin wait,
lock-busy/inflight-read, eight concurrent required allocators, internal new-bind
admission, fragmentation/original-failure, aggregate-cap, failed-read/hold and
strict-v3 controls pass. A second successor arm with lean leases and movie resume
also passes the original movie-owned/background ticket controls. K05 remains
three loads/zero evictions at 72,224 bytes demand with 64,832 reserved bytes.
All 28 selected reader/helper source-contract hashes remain unchanged.

From WSL, choose a fresh output directory:

```
python3 port/dreamcast/tools/d367/cache21-fixes/test_capacity_review.py --motion-source port/dreamcast/game/platform/native_motion.cpp --expect-context-guard --out /root/probe/<owned-new-output>
```

Add `--lease-lean 1 --resume 1` for the second qualified successor configuration.
Omitting the motion override and expectation reruns the exact old1f7 control.

## SH-4 object qualification

`qualify_capacity_context_sh4.py` reuses the sealed actual capacity object
commands. It copies and hashes every forced header, uses a shared source
snapshot path and normal quote-include lookup, and builds the whole native
motion unit with the pinned KOS d367/GCC15.2 toolchain. No full link is requested.

| Arm | Stripped native_motion.o SHA-256 | Text / data / BSS bytes |
| --- | --- | --- |
| Exact1f7 and successor, capacity0 | `496cfa7b1fcb1549db2869b9c066a41eb63f6944252055533115c730f1024e98` | 12793 / 0 / 1126 |
| Exact1f7, capacity1 | `afd0242f0a3480d0588ffaba35ac4848b3ccddd43dae3224d11afc9ea0be5066` | 14959 / 0 / 1283 |
| Successor, capacity1 | `9cf204c9a3c7eb02ea959c583ef9d655a6ac7ba459788c36805f66c3f80533eb` | 14959 / 0 / 1283 |

Default-off object identity passes; enabled text/data/BSS sizes are unchanged.
That is code-size evidence, not timing. The original capacity candidate's other
four objects were not changed or rebuilt here. Small-object guards remain
16 GiB plus 128 MiB preflight and 16 GiB plus 64 MiB stop with 2 MiB command-log bounds.
Full-build thresholds are unchanged. With the KOS environment sourced:

```
python3 port/dreamcast/tools/d367/cache21-fixes/qualify_capacity_context_sh4.py --out /root/probe/<owned-new-output>
```

Host receipts are `capacity-context-{baseline,guard,lean-resume}-host.json` and
the target receipt is `capacity-context-sh4.json`. Raw proof is mirrored under
`C:/Flycast-Evidence/re4-dreamcast/cache21-fixes-20261021/capacity-context`.
All original controls and earlier unsuccessful scaffolding remain preserved.

## Still open

The actual static reserve preflight/high-placement repros, held reset refusal,
post-destroy metadata/reserve frees and injected admission-during-teardown repro
remain unchanged and are rerun as characterization controls. Root separately
owns native feasibility/placement transactions and complete owner/reset
serialization. Scoped reader/callback/generation closure remains independent.

No full-program/overlay identity, stage, guest, screenshot, physical-console,
release/issue or SD action ran. This context repair is source/object-qualified,
not acceptance of the complete capacity candidate. Root selects integration;
Claude alone merges production, tags and publishes.
