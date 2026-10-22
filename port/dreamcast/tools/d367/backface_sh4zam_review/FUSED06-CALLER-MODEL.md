# Actual fused dev06 world caller model

Compile06 trace-off linked ELF fae7b0cb8406e4b8168e27b5c586ad393d58d8cf0e3ea2b06e83a6330e9b1b99 was interpreted read-only with exact dev06 materialized sources pinned. The implementation patch had not yet been updated, so the report explicitly identifies the immutable dev06 sources instead of treating the older repository patch as this implementation's provenance. No implementation edit, compiler, guest or image was run by this reviewer.

The model includes the complete SDK world entry, one shared lease, fused codes/facing, mask/run work, SQ/EOL, counters and return. It excludes the thin RE4 adapter and all cache/SQ/TA stalls. Common projection/transform/skinning/light work is unchanged and is NOT counted as a saving. The model is submission evidence only; no complete scene or physical speed claim follows.

|64-index pattern|SDK fused single-strip cycles|Relocation baseline|Original OFF full walk|
|---|---:|---:|---:|
|All front,64 emitted|3424|2971|1141|
|All back,0 emitted|2614|3635|1141|
|Mixed,35 emitted|3640|3815|1141|

For32 identical strips under one lease, per-strip fused costs are3315.5 /2505.5 /3531.5 respectively. OFF also amortizes:1109.03 per strip, not1141. These models therefore do not pass the user's faster-than-OFF gate. Lease amortization saves about108.5 fused cycles per strip from the single-strip case; it does not remove the core scan cost.

Fused rejection cases now execute area arithmetic before their final decision. At64 indices the depth-all, screen-all, limit-stop and depth-cross controls cost2570,2582,2557 and2551 cycles, versus roughly361..374 in the relocation. This cost regression was sent to the implementation owner immediately. The current depth-cross fixture sets only outcode[0]=1. Further early-prepass qualification must include interior crossings at positions1/31/32/63 with first code0, so it cannot hide the remaining cost behind only a first-code improvement. Oversize depth-all rejection must still precede limit clipping.

A representative actual phase is38 MODELLED cycles for31 instructions. Nine extra wait/redirect cycles are exposed: branch redirection2, index/outcode load-use2, FMUL-to-FNEG2, FMAC-to-FCMP2, FCMP-to-ROTCL1. The address prefix is serialized before math: indexload5/extu7, code load9/AND11/OR12, address shifts/add13..17, XY18/19, FRmoves20..23, FSUB23..26, FMUL27/FNEG30/FMAC31/FCMP34/ROTCL36..37. This explains why six labels alone did not pipeline the work. The owner is moving next-index/address/XY and code folds into those latency slots and removing avoidable per-phase branch pairs where tail logic permits.

All retained synthetic input/output words, stop pointers and additive counts matched the target-lowered oracle. Larger64-strip batches would collide with the bounded interpreter's current test-memory layout; the receipt deliberately caps batches at32, which already reaches2048 emitted vertices/64KiB SQ destination range. The separate OFF model raised only its host instruction-count ceiling to200000 for the32-strip replay; no implementation or opcode semantics changed.

Evidence: DYNAMIC-SDK-CALLER-FUSED06-MODEL.json, DYNAMIC-OFF-WORLD-BATCH-MODEL.json and FUSED06-HOT-PHASE-SCHEDULE.json. These use the existing AVK issue-group/latency approximation, actual branch paths, no cache model and no new hardware calibration. Short-strip/actor material coverage, actual world/Leon/Ganado/ElGigante frame weighting, complete-render performance, pixels and memory gates remain separate.
