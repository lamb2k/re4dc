# Independent backface SH4 integration review

Owner tree /root/probe/codex-backface-sh4zam-review, branch codex/backface-sh4zam-review; clean source base64a28a7bdc44312924b14414501b7d4ff1d2d032. Main/peer runtime files are read-only. Sparse source checkout10,915,308 apparent bytes under256MiB; notes/Git<=1MiB, host-test allowance32MiB. No compiler, make, native query, image or guest used by this review.

Read full latest coordinator update including SH4ZAM actor scope, HANDOFF.md, COMMON.md, AGENTS.md, mainSTATUS and RE4 D367 skill. Latest user instructions supersede dated skill defaults, capacity, cleanup/release and shared-branch advice. No worker spawning.

## Initial main integration

Frozen b44e2031f4866452efb6eb9be1f30981ed3cca4e directly descends64a. Four files only: Makefile wildcard exclusion, backface.mk CPU2 knob/object wiring, backface_sh4.hpp context API, trace helper. Later main8ddb0e228 adds gate/trace tests without changing these four.

Source review:
- New trace CPP is filtered out of platform wildcard for all default/OFF and CPU1 cases. CPU2 alone explicitly adds assembly; TA_HASH other than0/4 adds trace helper and assembly macro. CPU2 requires GAME_SH4ZAM1, ACTOR_BACKFACE accepts1/2. No target-object identity established by reading Make syntax.
- Context has eight SH4 4-byte fields, q offset20/pieces28/size32. C++ wrapper passes one context pointer and accounts actual returned vertices/q. Lowmask255 world preserves normalword0,127 actor synthesizes flags, high0x100 means bit7 EOL stream reset. n/pointer validity/clipping/material/source-cull and SQ ownership are caller obligations.
- Test helper hashes completed actual piece indices/words, rather than rerunning facing classification. Actor normalword0 and EOL are synthesized. It must run with compiler ABI FPU bank/mode and all kernel live caller-saved state protected.
- CPU0/OFF word/object/programme identity, CPU1 trace behavior, actual resolved object selection and current full QA basis remain main/gate-worker checks; no complete programme identity asserted here.

## Confirmed defects reported and owner fixes

F1 — MOVCA C-reference hash mismatch. Existing native_actor_fast.cpp emit_sq hash loop copies unprimed cache word0 and changes final EOL only, whereas actual ACTOR_MOVCA1 emitter writes PVR_CMD_VERTEX for EVERY normal vertex. CPU2 helper normalizes normalword0 correctly. Therefore CPU1-vsCPU2 TA_HASH differs with garbage cache flag words although submitted words can match. Reported to root and actor owner. Root approved narrow test-only normalization inside TA_HASH!=0/4 plus garbage-flag control. Owner says implemented, sealed/object evidence pending. CPU0/1 productionTA_HASH0/4 must remain byteexact.

F2 — XMTRX corruption by initial unsealed kernel. Initial COPY_VERTEX used XD0/2/4/6, overwriting opposite-bank XF0..7 (half the live matrix), with a false comment matching existing emitters. Existing vp::emit_sq mesh_fastpath.hpp and actor emit_sq use CURRENT-bank DR0..6 and declare FR0..7 clobbers. World bind/load_screen loads XMTRX, then transforms/emits successive meshlets without reloading between them: next transform reads corrupted matrix. FPSCR restoration does not restore XF contents. Reported immediately to root/kernel owner. Owner says switched to DR copies, fixed comments and is adding all16XF sentinel proof.

DR fix requires FR7 zero comparator reload after EVERY copying path. Original normal emit already reloads it; third-back COPY2 and terminal strip COPY2 did not. Owner says both paths corrected. A later stream strip must not compare area against copied cache word7.

F3 — TRACE bank/mode contract. Initial kernel cleared PR/SZ but retained FR. Normal C entry is FR0, but advertised exactincomingFR1 support would invoke callback on wrong bank. Owner now reports clearing PR/SZ/FR internally (maskffc7ffff), saving bank0 callee state after normalization and restoring exact incoming FPSCR. Need exact all-bank sentinel/callback proof at frozen source/object; this is not accepted solely from message.

No source ownership overlap or claimed-file rewrite by this reviewer. Initial unsealed draft observations are historical; do not attribute them to a corrected sealed tip without rechecking. Future updated source/object hashes close each item.

## Correctness review of draft algorithm/ABI

Ordered original expression four fsub, two fmul, fsub and ordered fcmp matches C area semantics, including zero/unordered notfront. No fmac/fipr/reassociated edge determinant accepted without proving reference sign/pixels; numerical algebra alone is insufficient near cancellation.

Delayed final-front emission is consistent with C rule: leading/trailing backs dropped, inner one/two kept, third back flushes pending last front vertex as EOL; piece start floors triangle index to even. Stream bit7 resets strip parity; incomplete <3 strips emit none. Actual assembled opcode/differential tests still required; this source review does not execute machine code.

Kernel ABI current design saves r8-r14,PR,FPSCR,fr12/13 (fr14/15 untouched). C trace saves live r4-r7,fr7-fr11 and PR/FPSCR; callee saves r8-r14/fr12-15. r0-r3/fr0-6/T are dead/recomputed around hook. Stack push pattern appears aligned at C callback. This is reviewed source intent, not a complete opcode proof. Copy must preserve all XMTRX and nonvolatile current-bank values.

World peer says integer-only outcode scanner leaves FPU mode/live matrix alone; depth-all/drop, depthcross/oversize clipper and screenall/drop source ordering retained; CPU2 calls common kernel without fullstrip trace replay. Actor peer says whole stream uses one mask0x17f call, strip mask127, same Part skin/rigid and source-cull owners; exclusion/cull still must be checked at sealed tip. Source-cull coverage must include Leon0, Ganados10..20, El Gigante2B; alpha-mask/no-depth-write remain two-sided. Requested close Ganado fixture/current exact assets remain target gates.

## Performance architecture research — not cycle evidence

The user requires facing work fused into existing emitters, not merely a generic SH4 classifier replacing C. Initial common kernel is explicitly not a <=4-cycle result; no simulated result was generated by this reviewer and no gain claimed. Main already treats the initial schedule as open.

Concrete source-precision fusion proposal sent to kernel/root:
- Pending full 32-byte vertex B already occupies DR0..6, so Bx/By are FR1/2. Keep Axy in FR8/9, load candidate Cxy in FR12/13, preserve nextA=B in FR10/11 with two fmov.
- Once SQ stores have consumed DR0 and DR2, reuse FR1/2 for B-A; C registers12/13 become C-A. Then FR1*=FR13; FR2*=FR12; FR1-=FR2; orderedcompare. This preserves C subtraction/product/subtraction order and remaining DR4/6 payload words.
- Alternate A pair8/9 and10/11 by renamed loop phases; next iteration loads C as the pending full vertex, supplying its Bxy. Queue candidate pointer once. This avoids six XY shift copies; the additional two Cxy loads/two Bxy moves are explicit costs, not free.
- Interleave arithmetic with existing load/store slots before pref only where dependencies permit. Initial3-vertex warmup and short/long back-gap transitions need explicit logic. SQ has only two unprefetched32-byte slots, so never buffer three initial vertices or speculate pref for dropped data.
- All-back triangles have no SQ work to hide against; model them separately. Simulate full actual schedule including address/index, guards, branches, call/setup and tails. Do not subtract saved stores twice or label a detached arithmetic schedule whole-frame improvement.

Main retains final architecture, integration, model and target resource allocation. No FRAME/pixel/KOS48KiB/s30340/340/Ganado/boss/physical gate has passed through this review.

