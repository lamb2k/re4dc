# Prefetch / offline-dedup context repair

Frozen4be's `emit_pick` uses `emit_corners` under SCENERY_EMIT_PREFETCH=1. That helper bypassed `corners`, the only place that refreshed the SDO3 repeat decoder. A fresh encoded plain pick therefore left dd_base null and transformed repeat metadata as coordinates; reused contexts could also retain the previous meshlet decoder. The original current4be target qualification explicitly uses PREFETCH0 and is unaffected.

The five-line runtime change repeats the existing `corners` context refresh in `emit_corners`, before plain/indexed/zero-pick early returns. It sets the current base/unique/count for an encoded meshlet and clears the base for ordinary/indexed input. No render decisions, data format, allocation, cache ownership or recipe changes are introduced. It is guarded by the existing PREFETCH1 and DEDUP3 conditions; default0 is unchanged.

Host controls use the actual extracted production methods, real package reader and portable clipper. They enable the previously unqualified PREFETCH1 branch in the existing composition harness; only its two SH4 FMAC edges use host arithmetic. Eight batch/replay/encoded-or-decoded configurations cover96 composition comparisons, including partial groups and near/far clipping. Every configuration separately checks encoded-first -> plain -> indexed -> zero-pick -> encoded under changed material/UV/cull inputs. Mutants removing the refresh or retaining a stale base must fail the context assertions. Actual preprocessing erases the entire changed region under PREFETCH0; this is a source-guard check, not a newly linked whole-programme identity claim.

```sh
python3 -B check_prefetch_context.py --source-tree /path/to/successor --baseline-native /path/to/frozen4be/port/dreamcast/game/platform/native_static.cpp --output /dev/shm/NEW-output
```

All compiler scratch and detailed outputs must stay in the new explicit RAM destination. Inputs and the frozen4be QA pair remain unchanged. This is source/host correctness evidence only. A newly integrated normal production build must still prove OFF main/all-overlay identity. DEDUP3+PREFETCH1 has no target, guest, pixel or performance qualification from these controls and must not inherit the old PREFETCH0 programme's acceptance.
