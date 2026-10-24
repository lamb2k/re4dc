# Required Motion protocol guard

Current diagnostics and judge use v2, strict result/manifest schema2.
protocol.json is validated by the judge and its SHA is recorded in the result.
Historical nine-consumer v1 receipts remain legacy evidence and cannot pass the
current judge. No migration silently supplies a Motion checkpoint or allowance.

The old ordinals0..8 are unchanged; Motion appends ordinal9, bit200, making
Required3ff. The runtime's current wired mask stays1f6 (or136 when native font
coverage is disabled). SourceGeometry, Weapon and Motion are not advertised as
complete. Motion counter0 is an UNWIRED consumer, never a zero-use assertion.
Even later wiring SourceGeometry/Weapon to1ff still fails the required3ff mask.
No motion.cpp/native_motion/cloud animation or asset conversion is changed.

Motion requires a separately reviewed kind=motion source identity. Current
core rejects ALL Motion emissions as motion-unwired before catalog binding,
Seen dedup or PS2/authored suppression, so even an already-seen catalog-PS2
geometry token cannot certify Motion. This avoids adding repeated catalog IO or
a cache before a reviewed producer receipt exists. Future producer integration
must explicitly replace this guard with its source-bound load/lifetime proof.
The judge separately rejects
geometry/model rows presented as Motion, rejects missing tenth counters and
values beyond u32, and requires per-consumer first-use rows to match counts.
No Motion catalog entry or allowance is added. Catalog binary schema1 and exact
reason/owner/evidence allowlist schema1 retain their existing formats; they are
source identity formats, not nine-consumer coverage receipts. The last accepted
allowlist still only shrinks; a new Motion identity cannot borrow a geometry
allowance or be learned from a failed run.

Production formatter controls execute the real C++ formatters through a real
256-byte vsnprintf buffer and assert no truncation. They include invalid
roomUINTMAX, visit/frame/wired maxima, max catalog16376, full kind/id/digest,
max error/overflow and TEN u32-max counters in startup/room/transition scopes.
Actual maxima INCLUDING newline: ASSET247, COUNTS255, BEGIN157, END168. The
COUNTS line occupies255 bytes plus its NUL; any additional field/width needs
another bounded record or a protocol change, not an enlarged assumption.

Audio queue events remain52 bytes,32 slots; tickets32; catalog limit16376;
unknown quarantine8; Seen2KiB. The tenth consumer does not grow any token/index/queue
record, and existing overflow controls remain fail closed. One extra emission
counter and name pointer are added (nominal SH4 data/BSS4 bytes each before
alignment); added validation text/stack and actual target sections remain
unpriced until the next allocated selected-target check. No resident catalog,
unbounded Motion table or draw-time hash/IO is introduced. The unwired error
runs only through the existing unlocked emitted/emitted_checked APIs, never
SQ/audio/G2; no real Motion producer calls them yet.

Controls cover strict manifest/version/required/ordinal consistency, legacy v1,
missing Motion wiring/checkpoints/counter, oversized tenth value, no geometry
identity/allowance borrowing, only-shrinking Motion additions and the already
seen PS2 geometry case. These are protocol controls, not a Motion producer or
complete I-001 coverage pass. Terminal producer quiescence remains root-owned.
