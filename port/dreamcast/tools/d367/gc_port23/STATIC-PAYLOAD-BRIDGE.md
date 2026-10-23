# Static payload bridge handoff

The helper and actual UI latch/replay integration are implemented; the shared
native_static.cpp file has not been edited. static_payload_patch.py produces
static-payload-hooks.patch against the lane's current integration source and
rejects every ambiguous or changed anchor. Root owns application/coordination.
This proposal is not a complete static-renderer qualification.

Embed one PayloadProof in each stable View, MeshView and Ps2World object. Capture
only the complete successful immutable file bytes before Package::adopt or
adopt_by_encoding can mutate the buffer. Heap-only bindings, alignment padding,
generated colour LUT and scratch gathers are excluded. Ordinary/mesh owners
capture the exact package. Ps2World captures full mesh plus full R4PW sidecar as
separate geometry/layout identities; both full SHA256s remain authoritative.
No filename, key, converter or PS2 API grants origin. The reviewed catalog must
include exact constituent proofs or they remain bounded unknowns and fail the
judge without matching reviewed exceptions.

Retire before package release, failed adoption/free, room replacement or movie
arena loan. Stable owner objects outlive every deferred pointer. The intrusive
registry has a terminal 128-owner cap and no separately allocated table. Every
accepted proof carries the original owner serial; reusing the same owner/buffer
after retirement cannot renew an old queued token. Duplicate current capture
preserves its original digest, including after in-place conversion. Overlapping
or inconsistent owners revoke previous proofs and fail explicitly.

The scope around mesh_submit/static fallback/ps2_pass selects the exact payload
owner. Actual packet/direct/switch acceptance latches it without I/O/hash/log.
Both deferred enqueue paths retain proof pointer, serial and consumer mask;
replay cannot resolve a different current package. Frame and retire flushes run
outside SQ. Catalog replacement invalidates all tokens; persistent package
proofs fail until the owner safely reloads original immutable bytes.

Open integration boundaries, deliberately not certified by this patch:

- Mixed-owner impostor batches need exact per-accepted-quad saved proof tickets;
  attributing the whole batch to its first owner is forbidden.
- r11fNativePass's early alternate owner and far-shell draw need their own
  exact immutable payload/sidecar bounds and acceptance bridge.
- R4SG or any other consumed file that changes geometry/material/source
  interpretation requires a separate/composite reviewed identity. R4PW alone
  does not qualify those additional sidecars.
- Movie reload failure exits after the proposed capture must retire its proof;
  the final integration owner must audit every error exit before enabling it.

Until those paths are qualified, their actual generic accepted-source latch
continues to emit explicit unbound errors. No complete coverage mask, linked
image identity, memory/heap gate or guest acceptance follows from this proposal.
Embedded proof target size is expected 44 B per owner plus one deferred pointer
and small global registry state; actual SH4 object/link pricing remains required.
