# SDK relocation stage1: actual caller-inclusive world model

Source worktree /root/probe/codex-backface-sh4zam-fused was read without editing it or invoking a compiler. The linked SDK world caller ELF05c3ab2d4796c91eec49a611cde40f31d3818fbf96ce420c181247ade5cade8f includes shz_strip_walk_sq plus the relocated complete strip kernel. Its words, stop pointer and additive counters were compared with the target-lowered C oracle for every retained model case. Source/patch/materialized input and ELF identities are in DYNAMIC-SDK-CALLER-STAGE1-MODEL.json.

The model records actual executed target opcodes and taken branches through the complete SDK call. It includes count/outcode scan, decision order, strip-context setup, call/return, core kernel, SQ/EOL, caller counters and epilogue. Only the RE4 adapter above the SDK API remains excluded. Existing AVK issue-group/latency rules apply; no cache, SQ drain/TA stalls, FPU exceptions or hardware timing is simulated.

For one64-index zero-outcode accepted source strip (62triangles):

| Pattern | Emitted vertices | Full SDK caller MODELLED cycles | Per input triangle | OFF complete lean walk |
|---|---:|---:|---:|---:|
| All front |64|2971|47.92|1141|
| All back |0|3635|58.63|1141|
| Mixed retained fixture |35|3815|61.53|1141|

OFF is the actual original compiled world walk from object5189391c, including its outcode decisions and all64 copies. Same projected inputs, zero outcodes and source limit are used. The SDK's additional caller overhead is393 cycles for this case relative to its standalone kernel. These rows do not establish the user faster-than-OFF gate and are intentionally the relocation baseline before the fused hot path.

Separate64-index decisions cost367 cycles for depth-all reject,374 for screen-all reject,364 for limit-stop and361 for depth crossing. The model checks no output and the exact return count-byte pointer/end in these paths. No diagnostic TA_HASH work is priced because trace0 is used. No scene weighting, actor full-caller cost, rendered frame, Flycast performance or physical claim follows.

The owner then renamed only generic SDK configuration/hook names in boundary02. Both linked ELFs are BYTE IDENTICAL to the modelled originals: trace0 above, trace1 adb65022694241654506ad3c2363fbafc29477d7fe0c68ccfae01a35464753a2. All four materialized files match manifest8a405b68 and patch30ee92b666d6b526802a208115061e8cbbffdad26fd3e742022a220952a1d1c4. SDK-CALLER-BOUNDARY02-IDENTITY.json retains exact mapping, so no redundant model run was required. The implementation was still working bytes when inspected; a later source commit should point to these receipts and preserve those exact object identities.
