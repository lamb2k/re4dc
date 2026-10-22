# Sealed peer correctness review

Main integrated baseline b6f8d346e; independent runtime review targets world0a26871db927b1bc7eb429ea9a61c5ae5ba6d134, actorc932384b6302026e075662d4d2603f52747069b8 and kernel3b17fae7b. Review branch remains own64a base and contains notes/tests only; no main/peer source edits or new compiler/target execution.

## Correctness findings closed at these exact revisions

F1 MOVCA trace: actor emit_sq now normalizes normalword0 to PVR_CMD_VERTEX under MOVCA and finalword0 EOL in its existing TA_HASH!=0/4 guard. Actual emitter remains unchanged. Host control executes actual changed C trace loop and common trace helper against garbage cache word0 and preserves words1..7. CPU0/1 production preprocessing/strippedobject identities are retained; final census/material guards have explicit finalpreprocess and trace-object receipt. No unchanged claim for the deliberately corrected diagnostic trace.

F2 XMTRX: kernel COPY_VERTEX uses current-bank DR0/2/4/6. Both third-back COPY2 and terminal COPY2 reload FR7 zero after SZ returns, as normal copying already did. No opposite-bank copy remains. Kernel source preserves live transformed matrix across consecutive world meshlet transforms.

F3 TRACE bank/FPSCR: final kernel retains incoming FR internally while clearing PR/SZ; normal DRcopy therefore preserves caller-opposite XMTRX even for tested FR1 entries. TRACE saves live activeFR7..13 plus integer context/PR/FPSCR, flips and saves ALL16 opposite-bank words, normalizes FR0 around C, restores opposite bank using savedFPSCR xorFR, then restores PR/FPSCR and active regs. Function saves activeFR12..15 and calleeGPR8..14 and restores exact incoming FPSCR. Inspected stack offsets, callback-mode mask and banked pop ordering; no concrete source issue.

Read actual-object interpreter source and retained object-test.json:1067 cases/2134 comparisons, sixteen FR/SZ/PR/trace combinations, all16 opposite-bank sentinels, callee-save checks and adversarial callback that clobbers caller-save FR and opposite bank. Interpreter enforces complete32-byte SQ burst before PREF, exact emitted words/pieces and trace equal actualPREF stream. It rejects unimplemented/XD opcodes; this is bounded interpretation of actual SH4 opcodes with actual C template, not hardware/FPU-exception/TA/cache/timing proof. Source/test runner/object hashes are separately pinned in source packet; object receipt field source_sha256 refers to object_test.py, not assembly.

F4 late Make prerequisites (found/fixed by main): explicit $(TARGET) dependencies in cd5f1be0 solve objects added after main target prerequisite expansion. Independent actual-block GNU Make -n harness16 cases reproduces failure before fix and correct selected assembly/trace build recipes afterward. TARGET explicitly defined. No recipe/compiler command executed. Default/CPU0/CPU1 select neither new object; CPU2hash0/4 onlyASM, hash1ASM+trace; invalid/noSH4 refuse. This is dependency/order control, not full canonical build or OFF programme identity.

## Actor and world integration

Sealed actor dispatch uses one stream_sq mask0x17f call for whole meshlet, mask127 for one strip, no C EOL/facing pass in CPU2. Cull-none, alpha-mask and non-depth-writing parts retain old copies/header and clipper. Typed BACKFACE_CENSUS-only model_bridge accessor reads already synchronous qualified model cModel.kindid/id; no offset guesses or actor-list walk. The qualified generic/deferred submit establishes/restores BFC class around actual bursts; earlier owned transaction scopes remain. Main's model_bridge.o census define is required and present. Nonactor models retain enclosing scope. Positive actual Ganado burst remains a target observation requirement, not established by host class tests.

Source owner selection remains Leon0/Ganados10..20/ElGigante2B, both skin/rigid Part paths. Existing owner alpha/depth exclusions unchanged. Actor receipt has actualTU object/preprocess controls and actualcaller/tag/trace host tests; these do not execute common SH4 kernel or prove target pixels.

World sealed review remains clear: genericLEAN0 and1/2/3 route to commonASM appropriately, outcode scan integer-only, source clipping/order/counters preserved and qdelta counts actualSQslots. No full rejected-strip hash replay. Its CPU0/1 source/strippedobject controls are read, not rerun.

Actor strip contracts are in WORLD-AND-STRIP-REVIEW.md and source producer receipt. Owned/preconverted/runtime-generated normal segments≤64; whole1024/LOD2048 can exceed255. C actual plain[256] implementation has no >255refusal. Kernel actualC oracle is array-safe through256; longer individual-strip C oracle is not claimed. Source producer test separately covered512 split and512 valid multi-strip.

## Remaining gates

This baseline is CORRECTNESS ONLY and slow; main/kernel are optimizing fused pending-B/SQ math. No <=4 cycles, scene/frame gain, pixel equality, canonical fullOFF identity, KOS48KiB, s30340/340, QA delivery or physical acceptance follows from this review. Do not apply prior correctness conclusion automatically to new optimized bytes; repeat the narrow affected source/object differential and register-bank proof for the new sealed tip. New native pixel adapter review remains pending its sealed source/control receipts; no emulator allocation from this reviewer.

