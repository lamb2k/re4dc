# Bulk motion retirement preflight

MOTION_RETIRE_PREFLIGHT=0 remains the default. With the switch enabled,
re4dc_motion_retire_all scans every active binding for pins under its existing
Locked scope before releasing any binding. Original per-binding checks remain.

The original loop can release earlier bindings and then halt on a later pinned
binding. Actual-source host controls reproduce that ordering. Enabled controls
preserve the complete motion-binding set on this refusal. This is a bounded
retirement safety repair, not a performance optimization.

Eight host cases per baseline/OFF/ON across three reserve/packing profiles pass
UBSan with explicit allocator/discard/lock boundaries. The selected QA SH4
stripped object is byte-identical for baseline/default/zero. Enabled code adds
68 text bytes; data/BSS and the 16-byte static retire_all frame are unchanged.
Make dry-run validates default/0/1 and rejects seven invalid values.

Whole room-reset quiescence remains open: gameRoomMemInit releases weapon and
overlay resources before this API, and its other owner/readers/heap transitions
need a single admission/retirement contract across yields. A local scan must not
be presented as that contract. No program, target, release or hardware gate ran.
motion-retire-preflight-review.json pins sources and exact mirrored receipts.
