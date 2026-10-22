# Ashley healing reads an actor from the inventory swap window

The normal chapter 3-1 route cannot select Ashley as a healing target in the observed frozen 746 program. This is separate from the native renderer and the post-inventory texture-upload issue.

At r207 frame22423, Ashley has360/600 life and Leon1440/1440. The original First Aid Spray is present. The original partner actor at8cb247a0 has model id3, position395.12,126.74,381.40, within the source healing distance. Opening inventory records `wk.healing=1`, but the same partner actor's bytes are zero while the inventory is open. A normal A press on Use at22466 leaves both health values and the spray unchanged at22497.

`sscrn_bridge.cpp::re4dc_subscreen_swap_open` saves the original live spans, then clears and reuses the3MiB window. The actor's address is inside that window. `ss_pzzl.cpp:2619` nevertheless reads `pSUB->id==3` to decide whether to show the Leon/Ashley choice. The observed id0 skips that branch and defaults to the already-full Leon. This is expected reuse of swapped bytes, not evidence of heap corruption.

`item.cpp::healing` updates the authoritative global player/partner health fields and clamps to their maxima. Those fields remain outside the swap window. Successful Use also calls `PlMotionReset` or `SubCharMotionReset`; both access the original actor. A future fix must respect that lifecycle as well as the WHO predicate. Merely forcing the id predicate or writing actor work bytes would leave an incomplete contract. No fix, new allowlist or guest memory write is included here.

Private evidence: `C:/Flycast-Evidence/re4-dreamcast/castle18-20261018/r207-original-Ashley-healing-subscreen-backing-audit-20261019.json`, SHA256f2f732a99d5d11e5dbad0a47842518e24c2116af9183a49d84fa49b94ed6115c. It binds unmodified BH/BJ/BK production snapshots to four ELF code anchors, source fields and the exact PID-owned ordinary menu inputs. BJ9.31s and BK6.28s exited cleanly. The preceding BI attempt is invalid: its capture wrapper rejected a3-second sampling period before an emulator launched; it did not advance the BH checkpoint.

This observation uses historical ELF746a2a5f and is not a current ACTOR_PLAN1 chapter acceptance result. Current-source reproduction, lifecycle fix, off-identity and actual healing/return-to-gameplay gates remain open. The no-warp route continues with its real inventory and health; chapter3-1 is incomplete.
