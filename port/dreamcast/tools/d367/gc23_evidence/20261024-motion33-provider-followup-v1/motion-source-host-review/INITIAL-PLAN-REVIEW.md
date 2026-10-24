# Initial ownership review — source not yet frozen

Read-only review, 2026-10-24. Author `/root/gc_port23_sol61`, owned implementation
tree `/root/work/lanes/gc-motion24`, branch `wip/gc-motion24-20261024`, base
`870789095c4c14fbdbf22043447b249063d2ec3a`. Reviewer changes only this review folder.
Frozen prior census remains unchanged.

Author initial plan: separate u32 context/pending plus 16B saturated
reason/events/units/overflow latch (24B global); RAII saved word on stack;
OneWindow local accounted flag up to4B. No heap/node/quad/SkinEntry/Frame fields.
Fixed Unknown includes view-track uncertainty; no N/A/positive or wired-bit change.
This meets the design direction, subject to exact code and final state size.

Before implementation the following ownership issue was sent to author/root:

`platform/include/native_actor_leon_pipe.inc:128-132` calls
`re4dc_leon_direct_switch(...window.slots...)` and resets window.slots after success.
Those vertices are already accounted at each OneWindow chunk. Therefore Motion
suppression is needed at both successful switch and final one_close; suppressing
only direct_end doubles successful switched intervals. Ordinary direct-switch
intervals still require previous-pending accounting. Missing/zero reason cannot
become a suppression token, static N/A or implicit success. An explicit accounted
end/switch API or equally narrow ownership marker is preferable.

Actual abort order also matters: fast actor6082 and OneWindow6743 may abort
after emitted vertices and before closing. `native_ui.cpp:7040` clears model_handle
and sets stream_aborted, but leaves direct_open. Prefix observation cannot depend
on a nonnull handle or an unaborted scene, and later cancellation cannot erase it.

Required extracted controls include successful/failed switch then close, capacity
reopen, nonzero chunk then later culled chunk, partial-prefix abort, prefix/final
packet commits, batched account with SQ retained and ordinary direct account.
Counter units/events must have exclusive owners; no duplicate aggregate counting.

No final implementation review or runtime/coverage acceptance is given here.
Await exact claim list/final endpoint plan, then frozen source and actual-path
controls. No SDK/guest/process control or author edits by reviewer.
