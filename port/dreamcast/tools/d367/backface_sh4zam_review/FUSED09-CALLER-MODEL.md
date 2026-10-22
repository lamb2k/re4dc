# Fused candidate09: complete SDK caller model

Frozen compile09 ELF0f478a84930ebbd698a3d514496332398a1c797c826b8445f07af5647658dd7c and sdk-dev09 source files were interpreted read-only. The target-lowered oracle agreed on exact output words, counts and clip-stop pointers in every model case. No compiler, guest, image or implementation edit was performed.

For64 input indices, first outcode0 and all other outcodes0:

| Pattern | Single strip cycles |32-strip batch cycles per strip | Fair OFF batch cycles per strip |
|---|---:|---:|---:|
|All front,64 emitted|2421|2309.594|1109.031|
|All back,0 emitted|1611|1499.594|1109.031|
|Mixed,35 emitted|2637|2525.594|1109.031|

These are MODELLED complete SDK submission costs, including the shared lease, scan, classification, mask/run handling, SQ writes, counters and return. The thin RE4 adapter and cache/SQ/TA stalls are excluded. Common transform/skinning/projection/light work is unchanged and is not credited as a saving. No whole-scene, physical or faster-than-OFF pass follows.

The accepted path with first outcode4 and every other outcode0 costs an additional447 cycles per strip: singles2868/2058/3084 and batch32 per-strip2756.594/1946.594/2972.594. This case is not screen-all rejected: the prepass runs, then the part remains eligible. It must remain in scene weighting rather than being combined with first-code0.

Rejections now separate the repaired first-code paths from interior crossings. At64 indices: all-depth627, all-screen639, first-depth1 crossing604; oversize with first-depth0 clips in140. Oversize with first-depth1/all1 rejects depth-all before limit in626, while first1/rest0 clips in603. First outcode0 with a depth crossing at positions1,31,32 or63 still costs1539 in each case. These exact source-order controls passed, but the remaining cost is explicit.

Actual representative hot phase is22 MODELLED cycles for28 instructions, down from38 cycles/31 instructions in compile06. Software pipelining hides the earlier FMUL/FMAC load and arithmetic dependency bubbles. Remaining extra waits are one index load-use cycle and one FCMP-to-ROTCL cycle. The exact PCs, instructions, groups/dependencies and issue times are in FUSED09-HOT-PHASE-SCHEDULE.json. The owner received two narrow scheduling opportunities: move an independent subtraction into the next-index load-use hole and, if all lifetimes permit, seed the next phase after FCMP consumes the current result without changing T. These are model-guided proposals, not a claim of target-hardware issue behavior.

Evidence: DYNAMIC-SDK-CALLER-FUSED09-MODEL.json and dynamic-sdk-caller-fused09-model.py bind the immutable objects/materialized sources; the working repository patch is explicitly not the source identity for these dev objects. The fixed batch sizes1..32 preserve the test harness memory layout and SQ extent. Actor caller and scene weighting remain separate; all prior safety/default-off/physical evidence distinctions stay in force.
