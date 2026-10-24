# Capture protocol exclusions

The original R-m-b1-q1 and L-m-b1-q1 are preserved in place but excluded from every accepted meter summary. R started monotonic554541.406 and lasted41.156s; L started554580.390, giving2.172s overlap. These runs violated the assigned one-owned-guest condition. The shared3-slot/global16 locks were held but do not enforce a tighter per-worker limit.

R-m-b1-q2 and L-m-b1-q2 replace those captures. The replacement chain waits for B-m-s2-q1 bounded-launch to record guest_exited and RUN_COMPLETE before starting R; L begins only after R's complete wrapper process returns. Final analysis additionally asserts disjoint guest lifetimes for all eight accepted matrix captures. No failed/overlapping capture is silently substituted or inferred complete.

All requests40s and exact-child guard55s. Guest_rc1 follows harness-requested termination; acceptance requires RUN_COMPLETE, errors[], reader completion, guardfalse and actual observed lifetime<=55, rather than treating that termination code as natural game exit. This is bounded capture completion, not a gameplay-exit gate.