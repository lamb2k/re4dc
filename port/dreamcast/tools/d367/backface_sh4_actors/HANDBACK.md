Actor CPU_BACKFACE=2 caller integration

The actor caller now sends an unclipped strip to the common SH-4 kernel with mask 127, and a whole meshlet in one call with mask 0x17f. Assembly handles the embedded EOL boundaries and resets parity. CPU2 performs no C boundary scan or C facing/run walk. Cull-none, alpha-mask and non-depth-writing parts keep their previous lean copy/header; near-plane clipping remains the existing clipper. CPU1 keeps its C reference.

The common kernel owns register/FPSCR preservation and emitted-word synthesis. Every emitted actor command must be VERTEX or EOL, including ACTOR_MOVCA builds whose cache word0 is not primed; words1..7 must remain exact. The actor wrapper retains the census class scope around the kernel, including the fallback class6 for an untagged actor.

The existing source-cull selection in coarse_actor_transaction.inc covers Leon id0, Ganados 0x10..0x20 and El Gigante 0x2b. The owned run path calls one_chunk and the same Part strip/whole methods for rigid and skinned frames. native_actor_owner_runs.inc continues to clear cull for alpha-mask and non-depth-writing materials. These files and native_ui.cpp were read only. The optional LEON_NATIVE_PIPE experiment defaults off and is absent from the selected recipe; its separate cull-none implementation was not enabled or modified.

There is one test-only correction to the C trace: ACTOR_MOVCA emit_sq now hashes the VERTEX command actually written for every nonfinal vertex, rather than its unprimed cache word0. The actual emitter is unchanged. CPU0/1 production TA_HASH0/4 still compile identically.

Qualification completed:

- Actual SH-4 TU preprocessing matches the baseline exactly for CPU0 and CPU1. Compiled objects match after stripping KOS path/line debug, in MOVCA0/skin0 and MOVCA1/SH4ZAM-skin1 configurations. CPU2 and its census/trace object compile. The baseline actor source is identical in 20752045 and 64a28a7b.
- Host controls compile the actual changed caller method bodies and the actual common trace helper. They check one whole-meshlet call, mask/parity boundary contracts, queue/sent updates, Leon/Ganado/Gigante class tags, cull-none and nondirect bypass, and exact C/ASM trace agreement with garbage MOVCA cache flags. This host mock is not execution of the SH-4 kernel.
- Claude's retained cB2-g8 census has positive class3 Leon and class5/id2b El Gigante culling. The selected historical s1 census has no class4 Ganado burst. Main still needs the requested close Ganado fixture; code coverage is not loaded-path acceptance.

Remaining gates belong to main/kernel: real kernel SQ-word and FPSCR/register qualification, all-front/mixed/short-run performance, target pixel comparison, canonical linked CPU0 identity, KOS48 KiB and r100 s30, separate actor timing, and the QA disc. No guest, image, recipe or gameplay change was made here. No <=4 cycles claim is made.

Generic source and deferred submissions also carry actual source cull: model_bridge.cpp re4dc_draw_model_part assigns re4dc_model_cull(m->CullMode,debug); native_model.cpp dispatches nonstatic/encoded parts to re4dc_actor_submit, whose skin and rigid frames share Part. A confirmed census gap was that this entry did not retain the transaction class scope. BACKFACE_CENSUS-only typed model_bridge accessor and qualified-submit scope now identify these draws, including replay, without offsets, actor walks or gameplay changes. The existing crowd-class accessor cannot supply exact Leon/Gigante IDs and is conditional on ACTOR_CROWD, so it is insufficient here. Nonactor draws preserve their previous outer tag. Main's separate model_bridge.o census define is required. A close Ganado run must still prove positive class4 with real alive/NMRS and visible pixels; the old class6 bursts alone do not establish identity.

Published owned blobs have at most64 indices per strip (coarse_actor_preflight.h); the runtime converter/LOD stripifier also caps64. Whole streams may exceed255 and must not be capped to one strip. CPU2's common ASM owns whole-stream EOL handling.

Final controls: FINAL-GUARD-RECEIPT.json rechecks unchanged CPU0/1 preprocessing after the census/material guards and compiles the final trace object. HOST-DISPATCH-RECEIPT.json checks typed generic tags and alpha/depth bypass as well as exact MOVCA words. The initial full TU matrix and initial host receipt remain separately preserved.

Only native_actor_fast.cpp, diagnostic-only model_bridge.cpp and this actor test/evidence namespace form the actor delta. The preceding421e234cd and588964ee2 commits are main's ABI/wiring cherry-picks; main should cherry-pick only the following actor commit.
