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

The generated proposal now also saves each queued impostor/tree quad's exact
proof pointer, owner serial and consumer mask. Only quads actually copied into
the bounded packet enter its borrowed proof list. The actual UI commit hook
accepts that list only for the exact vertex buffer/count and four vertices per
quad; retired/missing/mixed-up proof, wrong buffer/count or more than 48 quads
fails without falling back to ambient model identity. Failed atlas binding and
capacity-rejected quads produce no acknowledgement. A source-extracted control
runs the generated real impostor flush together with the actual UI commit and
real payload/core helpers. The shared renderer is still unapplied.

Open integration boundaries, deliberately not certified by this patch:

- The separate far_shell_payload_patch.py proposal adds stable proof outside
  reset State, full validated file capture excluding generated LUT/tight data
  and padding, retirement before free, and a scope around actual direct draws.
  Loader/draw controls cover reload, failed input/bind, zero accepted vertices
  and stale proof. Both include parts preserve OFF preprocessed tokens. This
  patch and the paired static patch remain unapplied. The r11f early transaction
  routes into the same scoped ps2_pass and needs whole-boundary review.
- R4SG or any other consumed file that changes geometry/material/source
  interpretation requires a separate/composite reviewed identity. R4PW alone
  does not qualify those additional sidecars.
- The generated movie reload now revokes before its first read/overwrite and
  uses a local diagnostic cleanup guard for every refusal after capture. Actual
  reload controls cover partial reads, adopt failure, bad header/part/placement,
  capture before package mutation and successful changed same-buffer reload.
  Root must still qualify the whole arena borrow/return graph on integration.

Until those paths are qualified, their actual generic accepted-source latch
continues to emit explicit unbound errors. No complete coverage mask, linked
image identity, memory/heap gate or guest acceptance follows from this proposal.
Embedded proof target size is expected 44 B per owner plus one deferred pointer
and small global registry state. Mixed quad records add 12 B each (576 B for
48), plus a borrowed 576-byte stack proof list, small scope descriptors and one
4-byte active batch pointer on SH4. Far-shell adds one stable 44-byte proof,
excluded entirely when the gate is off. There is no heap table or resident catalog
growth. Actual SH4 object/link pricing remains required.

Compiled actor arrays now have a bounded helper contract: payload_capture_fragments hashes ASCII GCFRAG01, little-endian u32 span count and reserved zero (16-byte header), then each little-endian u32 byte length and its exact bytes in caller order. At most 48 spans and 40 MiB total; the reader streams through the existing 512-byte SHA scratch. No span list or extra PayloadProof fields are retained. This API is for explicitly immutable compiled owners only; the integration must match actual consumed arrays/descriptors before selection and must not use it for mutable/reloaded packages. Full digest binds geometry; no origin comes from compiled/local/PS2-named data. SourceGeometry/Weapon coverage remains unwired pending real actor-pack and specialized static consumers.
