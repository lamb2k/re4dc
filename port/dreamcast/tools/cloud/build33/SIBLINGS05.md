# EF05 sibling room-cell authority

Base: `7c1f53fa9b2f88251ab17998904a27d127c65aa0` (origin includes EF10 skin admission bba762626 and world clip dcc870325). Default remains `STATIC_OBJ_LIFETIME05=0`.

The remaining Build33 sibling obligation was concrete. At the base, `model_bridge.cpp:642,657` read `sobdump::S->generation` before proving that room-cell storage live. Bake frame did the same at866; its placement callback881, room cleanup930 and ModelRender skip938 dereferenced naked retained state. Bake bind844–847 also kept an `Obj&` across `re4dc_static_alloc`, then published its rest copy without a post-allocation owner check. Build33's existing handback752–758 explicitly deferred this work.

This reaches a supported source path. `model_asset_bridge.cpp:309–324` calls bake setup and diagnostic raw-list capture from the existing source OT admission walk; `model_bridge.cpp:1135` at the base calls diagnostic part capture. `native_static.cpp:6052` invokes the registered placement callback before latching its existing requests; `trans.cpp` calls `re4dc_sob_bake_skip` at ModelRender. `tools/d367/test15/t15-build.sh:42` inherits `STATIC_OBJ_BAKE=1 PS2_PLACE_GATE=1`; `crowd.mk:799` is otherwise default0. SOB_DUMP is a separate default0 diagnostic. This is a source lifetime defect, not an observed private-game crash claim.

## Correction

Only model_bridge source and a small dedicated helper change. Each sibling reuses `sob05::Cell<State>` to validate heap generation/range/allocation incarnation before payload access, including same-Frame_cnt calls. Allocation establishes a token only after returning and cannot replace a state installed by reentry. An unpublished but still valid allocation is returned, including token exhaustion.

Each bake rest copy keeps its own allocation incarnation inside the validated state. Rest comparisons and frees require the exact current extent/token. Allocator, serializer-log/materialization and placement callback returns revalidate a copied out-of-band state identity before any old reference is used. Cleanup detaches its public state first and stops if a free callback retires/replaces its held allocation. A failed placement decision clears this table's requested baked placements through the existing gate, retaining the live path. Existing world retirement/abort semantics still govern packets already emitted; this change does not retract published geometry or add a renderer.

There is no extra cache, capacity or allocator. On the 32-bit target, the two state identities add24 static bytes when both classes are selected; bake rest tokens add4 bytes per existing14 slots inside the room cell (56 bytes), not retained external capacity. Target size/disassembly/full memory accounting remains a separate gate.

## Reproducible source and host checks

```
python3 port/dreamcast/tools/cloud/build33/siblings05_host.py --output NEW_OUTPUT
python3 port/dreamcast/tools/cloud/build33/siblings05_host.py --output NEW_SAN_OUTPUT --sanitize
python3 port/dreamcast/tools/cloud/build33/siblings05_identity.py --output NEW_IDENTITY_OUTPUT
python3 port/dreamcast/tools/cloud/build33/lifetime05_host.py --output NEW_EXISTING_OUTPUT
```

The fixture extracts both actual sibling sections and the actual room allocator/lifecycle functions. Host stubs model source structures, heap backing, existing callbacks and renderer gate outputs. Thirty cases cover same-frame reset/close, freed protected payload, reused state/rest addresses, actual table-matching rest construction, ordinary baked/live decisions, OOM/exhaustion, reentrant state allocation/publication, rest allocation/logging, source-key/lazy-materialization callbacks, placement readiness/gating, and free/room-change reentry. A synthetic matrix word satisfies the real fixed rest hash to enter the actual production binder; it is not private geometry or a numeric rendering witness.

The metadata page remains readable after ordinary same-epoch free (the real room allocator revokes its header magic); consumer payload is protected. A heap reset protects metadata too, proving the generation check precedes any header/payload read. This follows the existing room API contract; it does not establish arbitrary unmapped heap behavior.

Original-source negative receipts are retained privately at `/root/probe/ef05-siblings-old-dump01-20261030` and `/root/probe/ef05-siblings-old-bake01-20261030`. The first faults on the actual serializer frame stale-state read; the sanitizer trace for the latter names `re4dc_sob_bake_frame`. Reproduce with `--source-revision 7c1f53fa9 --case dump-frame-stale` or `--case bake-frame-stale --sanitize`. They are expected failures and remain failures.

OFF checks compare the complete includes-elided bridge's selected preprocessor tokens against the base with the sibling paths selected and the control absent/zero; only whitespace is ignored. Actual extracted sibling hosted objects match byte-for-byte in both arms. Only synthetic fixture assertion line numbers are pinned; no production tokens are rewritten. These checks are explicitly narrower than full target preprocessing/object/programme identity. The five primary-Make arms in `siblings05_profiles.json` pass the existing complete public release-chain parser with ordered CH2 appends, across model_bridge/ui_bridge/native_model/native_static commands. Targeted arms keep `WORLD_PREPARED09=0 STATIC_OBJ_SPANS10=0`, so the existing lifetime define stays scoped to model_bridge/ui_bridge; existing bake parents remain enabled. Root's later composed QA covers world/spans propagation separately. Make-only SDK/header existence placeholders are never compiled; no SDK invocation occurs.

## Remaining EF05/06/07 and prepared-binding boundary

The primary SOB lifetime path already validates out-of-band allocation ownership (`model_bridge.cpp` base376–381,486–494,526–527,534–578), removes copied concatenation reuse under lifetime05 (510–519), and returns unknown content through the ordinary uncached path. EF10 requires registered matching source extents before grouped preparation (base473–482) and now declines pending source skin arrays. This sibling correction does not certify every foreign/content mutation producer.

EF07's existing owner registration invalidates related source ranges and matching owners, preserves tombstones/leases, compacts only at the safe no-lease boundary, and refuses overlapping source authority: `native_draw_plan_owner.cpp:79–116,119–145,178–216,227–233,263–285`. Actual archive publishers are native_ui5631–5724. No additional actual content writer bypass was demonstrated in this bounded audit; arbitrary pointer mutation is not evidence of a supported admitted producer.

EF06 already revokes upload identity before close callbacks (`native_ui.cpp:3888–3913`), advances on accepted publication4500, compares ordinary/SCPS cached header hits10255/10277, opaque readiness10122 and fills10535. Current prepared binding captures source extent stamps and the actual texture lease/upload/dimensions/pass (`native_ui.cpp:7564–7661`), then verifies the actual ordinary packet binding7912–7921. `native_model.cpp:1185–1201` enters only after plan/bounds/cheap cull and snapshots its selected source/light; bind/publication checks retain that identity (349–355,374–407,1258–1262).

Prepared binding intentionally handles resident archive-backed rigid unmasked, nonpaletted textures only. Cold resolution, unknown/mutable extents, palette/mask, RTT/baked overrides and deferred/draining classes retain the existing ordinary late-binding/restart path (`native_ui.cpp:7618–7638`). Upload identity alone cannot safely broaden this to yielding early I/O. A justified next source grant would need one exact existing excluded consumer and its source/content mutation and post-I/O proof; no such new concrete gap was demonstrated here. Actual current-content occurrence, eviction/reentry/movie restore, UV/header/order/look/STRICT, whole-memory/net cost and physical-console acceptance remain live/private-evidence gates. This source fix does not close the full EF cards.

No SDK, link, integration, recipe/default change, runtime, SD/media or publication acceptance is claimed. Root owns serialized target admission using the proposed existing-control profile and full disabled identity gates.
