# Additional static source boundaries

Source pin: d5c4c3197, whose shared native_static.cpp remains identical to the
merged 933936ea integration source. Line references below refer to that file.
This is an implementation proposal, not an origin verdict or coverage pass.

| Input | Exact accepted source boundary | Use and mutation | Retirement |
| --- | --- | --- | --- |
| Ordinary scenery / mesh package | Successful full read before Package::adopt / adopt_by_encoding, around 822-858 and 1481-1510 | Geometry, material keys and embedded impostor records; adoption or later preparation may mutate bytes | View / MeshView retire before free; existing generated patch |
| PS2 world mesh plus R4PW | Full mesh msize and sidecar psize at separate validated spans, around 5536-5588 | Geometry, texture keys, pass/cull values, placements; package adoption and dedup later mutate mesh | Ps2World retire before arena loan/free/overwrite; existing generated patch |
| Far-shell FSH1 file | Full successful size after header/groups validate, before return from farshell::open | Group geometry, material keys, strips; generated LUT/tight data and alignment are outside the file identity | Separate stable proof outside reset State; generated far-shell proposal |
| R4SG | Successful gsize-byte file accepted at 5753-5765, before scn21_open / dedup_open | Corner ranges and group visibility data passed to MeshDraw at 6285, 6327, 6599, 6665. dedup::run mode 1 rewrites ranges in place; a later hash is invalid | Same world lifetime; revoke before sg_block free at 7168, and before replacement |
| R4TC | Successful size-byte class file after header/source CRC validation at 5085-5107 | Per-part classes alter opaque/PT/TR material pass and drop policy; class bytes live at block+sizeof(Head) | trans::close before free; movie reload closes the table and returns to ordinary policy |
| R4ID | Full isize-byte file before adoption into dyn::block at 5631-5660 | Placement-to-source-object association selects actual live transforms and suppresses stale placements | dyn::reset before free; movie return intentionally preserves this current bound owner |
| PVS R4PV | Full size-byte file before generated offset arrays at pvs::open, 4921-4980 | Visibility set selects source geometry; extra per-placement/part offsets are generated after file bytes | pvs::close before free; current frame references are cleared on movie return |
| Room SCCN | Section pointer/len/version after room-file ownership and exact package validation, 5230-5240 | Cone/group selection; borrowed room-section bytes, no independent allocation | Clear cone pointers before room-file retirement; parent generation must be frozen at capture |
| Room SCPS | Section pointer/len/version before memset at 5247-5260 | Runtime per-piece slot state. File header/initial body may be hashed only before the initial memset | Clear piece pointers before parent room-file retirement; never rehash runtime slot words |
| Room SCDD | Section pointer/len/version before dedup::run, 5408-5430 | Validated repeat map controls vertex reorder and group range rewrite; check proves matching positions but does not prove source origin | dedup_free clears borrowed pointers before room-file retirement; movie reload reuses current prepared mapping |

The trclass.idx listing controls whether a class table is opened. It supplies no
pixels or geometry. Likewise compiled visibility/area policies may be permitted
game logic, but that classification must be explicit. A local converter, CRC
match, successful parser, matching positions, or PS2-specific API cannot grant
PS2 or original-DC provenance to any row above. R4PW alone does not prove a
different accepted sidecar. Root must review which source-interpretation inputs
belong to the asset identity and which are permitted logic.

The smallest bounded extension would retain the existing geometry token and
use the existing layout-token slot for one exact, framed interpretation
manifest. At immutable load, stream a versioned ordered sequence of tag, exact
length and full SHA256 for R4PW and every accepted source-interpretation
constituent; include explicit absence markers. Hash no generated padding or
mutable runtime slots. Bind the resulting full manifest digest as a separate
catalog identity. Reviewed provenance must account for every constituent;
mixed or missing evidence stays unknown. This avoids a new resident table or
per-draw I/O, and preserves exact constituent hashes in the offline receipt.

That approach still requires a concrete lifetime protocol: retire the owning
proof before replacing any constituent, freeze the manifest only after all
participating immutable captures, and preserve its original token while a
movie return reuses the same still-live prepared sources. If any constituent
changes independently, revoke/rebind at that boundary; never rebuild a manifest
by hashing relocated mesh, rewritten R4SG or mutated SCPS. Optional tables that
open after geometry adoption need their own temporary immutable digest capture
before the final manifest bind. No runtime extension is implemented by this
document. The current two-token helper remains unchanged and coverage remains
explicitly incomplete.
