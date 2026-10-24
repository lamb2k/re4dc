# Motion UNKNOWN accepted-use census — a132

Design audit only, 2026-10-24. Frozen source `/root/work/lanes/gc-catalog24` at
`a132648e8199b50a5ac51cec4d339fe7dbc60135`, clean before/after reads.
No game source, runtime metadata, coverage mask, recipe, SDK, guest or assets changed.
This is not I001, a no-GC-use assertion, a Motion provenance PASS, or implementation approval.

Final readback saw the clean tree advance to
`870789095c4c14fbdbf22043447b249063d2ec3a` (five catalog target-tool/doc additions).
Every one of the 36 audited files still matches the frozen a132 Git bytes exactly;
this review does not qualify those new tools or change its source pin.

## Result for root selection

An UNKNOWN-only first stage is feasible without source-positive motion slots,
pose digest tables, per-SkinEntry/Frame pose metadata, or a Motion catalog lookup
on an accepted path. Every audited actor/model-derived output can carry a fixed
unqualified Motion classification. It must be independent of Geometry identity.
No model/world static-not-applicable exemption is admitted by this audit.

The important distinction is **potential motion-derived input was accepted but
its lineage is unknown**, not “this geometry proves an external Motion asset was
used.” The proposed counter is an unqualified accepted-output count, not an
asset count or a count of Motion evaluations. It remains a failure/unknown.

The latest `gc-port23/STATUS.md` and
`motion-next-audit/LOW-METADATA-POSE-CONTRACT.md` were read first. There is no
separate GCSTATUS file. Current protocol v2 requires `3ff`, wired remains `1f6`;
SourceGeometry, Weapon and Motion remain incomplete. a132's gate change defers
catalog faults until IO unwinds. All other 35 source files pinned by this audit
are byte-identical to 1d63; this does not transfer Geometry qualification to Motion.

## Source facts that prevent shortcuts

* `gc_asset_members.h` SourceUse/ReplayUse carry only geometry serial/class/
  model/info/payload. ActorSourceScope selects package ranges and restores its
  predecessor. None carries a pose/root/history receipt.
* `member_accept` and `payload_accept` permit only SourceGeometry|Weapon.
  Adding Motion to those masks is invalid. `emitted_checked(Motion,...)` refuses
  before catalog/Seen and calls `unresolved`, which logs immediately. It cannot
  be called from SQ/G2/LH protected acceptance.
* `model_bridge.cpp:124-132` explicitly labels the no-pMotion/no-shape test a
  *prelit hint*. At 933 `static_geometry` only classifies rigid scroll geometry.
  Actual modelview at 911 is externally supplied. Neither hint proves no Motion.
* `trans.cpp:2250-2265` chooses object/root/bone matrices, then camera view;
  5778-5810 copies/registers palettes; 5820 onward can defer a palette build from
  retained model/weight pointers. Null/stopped/current motion and unchanged
  geometry do not establish overwrite of earlier pose/root/history.
* `native_actor_fast.cpp:1671/1718/1805/6194` caches source/palette/modelview and
  transformed matrices. Mode kRigid, source arrays, materialization, a cache hit,
  same frame, or current replacement geometry cannot remove the unknown.

## Accepted routes and proposed UNKNOWN boundary

Paths below are relative to `port/dreamcast/game/`, unless prefixed `src/`.
Exact file SHA256 and all anchor lines are in SOURCE-READBACK.json. These are
actual-source routes, not an assertion every alternative is currently enabled.

| Route | Motion-capable retained/current input | Actual accepted boundary; required handling |
|---|---|---|
| Source model bridge | `model_bridge.cpp:891-979`, `src/game/trans.cpp:3140/3289/3629/3709`; source pose buffers or original rigid arrays plus supplied modelview | `native_model.cpp` submit is dispatch, not acceptance. Establish fixed ModelUnknown context before static/actor/generic dispatch; do not count handled/cull/prepare. |
| Fast actor rigid/source/skin | `native_actor_fast.cpp:1805-1877`, skin matrix 1895+, palette registration 5223+; lazy materialize 5294/5312 | Packet prefix commit 3404 and final 6094; direct actual slots 6083. Whole cull, refused begin, header-only direct_end(0) produce no use. |
| OneWindow multi-chunk | `one_frame:6194`, `one_chunk_core:6284`, load chunk 6789+; window retains SQ across chunks | Latch each nonzero chunk `e.slots` at 6739 **before** window context changes, including partial output followed by abort. Aggregate `one_close:6273-6276` must not relabel prior chunks as last chunk. Packet fallback uses commits. Avoid counting the same direct prefix again at close. |
| Owned/preflighted material runs | `include/native_actor_owner_runs.inc:68-144`, skin/workspace pool, `coarse_actor_transaction.inc:387-417/1058-1160` | Owned/preflight success and texture pin are not output. Runs go through one_chunk. Partial accepted slots survive a later transaction failure as observed use; no negative rollback of census. |
| Owned cached/second-pass/fade/RTT | Transaction retains palette/modelviews/parts and validates them again; death fade queues/owned runs and ice overlay reuse them | Same per-run accepted hooks. Lighting, alpha, projection checks and matching live matrices are not Motion lineage. No new positive lookup on replay. |
| Coarse Leon / Ganado / cast | `coarse_actor.cpp:292-425`, coarse_ganado 147+, coarse_ganado_cast 729+ build palettes from parts matrices/root; per-info register or grouped submit | Both submit_chunks and individual actor_submit must reach fixed Unknown. Pregate/hidden/invisible/LOD notes with zero output do not count. |
| Hands / PL08 / registry / owned generic | owner_leon palettes 254+, owner_pl08 inverses, owner_ganado source bones, registry palettes 609+; hand slot geometry/copy derivation changes source package only | Same actor accepted hooks; current hand selector, reserved IDs, registry owner, bind matrices or geometry proof cannot bless Motion. No SkinEntry/Frame metadata is needed to keep every such cache hit Unknown. |
| Atlas/material split and backface split | coarse_actor_atlas_split caches projected/bound plans; actor converter split/LOD/cones retain geometry; all still read current/retained skin/root | Selected kept runs/strips only at ordinary accepted hooks; neither split preparation nor culled groups count. Each output prefix remains Unknown; converter/source equality is not Motion provenance. |
| Generic retained preparations | `native_model.cpp:130+`, retained position/normal/shade generations and copied matrix key | Builder prefix streamcommit 291 and final 924. Preserve Unknown on cache hits; partially committed prefixes count even if walk later fails. |
| Alternate non-fast actor | `native_actor.cpp:45/104/504-535`, prepared positions/shades and copied transforms | Prefix 332/final 535. If an implementation only instruments native_actor_fast it must reject this configuration or keep detector coverage incomplete. |
| Merged display-list batching | `model_bridge.cpp:368-416`, Pending.rec copy, cached concatenated stream, flush submits one merged or several originals | Freeze fixed ModelUnknown for pending group, apply when generic/actor leaf actually commits. Enqueue/build/find alone is not use. Do not recapture current ambient model while draining earlier Pending. |
| Source static replacement | `native_static.cpp:4404+/4601+`, MeshEntry plus p.modelview/world/light; GcStaticSourceScope is Geometry only | MeshDraw packet 3440/3477 or direct 7314. Already-drawn/fallback bits returning handled cause no fresh Motion use. Static/source-prelit does not admit N/A. |
| Translucent/deferred source models | `native_ui.cpp:755-805/7580-7710/9445-9466`, saved part word diffs and lighting, ReplayScope saves Geometry only | Model dequeue/restore is not acceptance; leaf packet/direct output is. A fixed DelayedModelUnknown receipt may be supplied by the queue's model-node branch without copying or examining source identity. Sprite/line/post tag branches need their own classification; do not treat every DeferredPart as a model. |
| Native tree impostors | `native_static.cpp:3653-3685/4353/4396`; queued screen quad is derived from source transform, geometry proof saved per quad | Only successfully packed quads at packet_commit(used). `payload_quads_accept` is an early return in gcasset_model_accept: Motion must not sit after that return. Bound/failure/overcapacity/dropped quads do not count. Fixed ImpostorUnknown covers all contributing quads without positive metadata. |
| Coarse-world impostors | `coarse_world.cpp:1515-1556`, queued TreeQuad.s from previous source/camera projection | Actual used quads at 1556; do not infer no Motion from code-generated atlas coordinates or missing model pointer. Separate from native_static impostor proof. |
| PS2 mesh world ordinary/direct/batched | `native_static.cpp:4951-5080/6575+/6960+`, baked placements OR dynamic delta OR source hierarchy/root, copied ChunkPart.mvq and picks | Actual packet/direct account. Batches may hold SQ through model_direct_account; chunk picks cannot inherit last pending owner. Fixed WorldTransformUnknown is safe for first stage. Matching rest pose does not prove historical source overwrite. |
| Baked-only world/far shell component | far_shell.inc:251-396 reads immutable grid vertices/group placement and ps2w view/P/V; immutable authored owner bypass at native_static:6962 | Object-pose component can be separately documented as baked on the exact no-dynamic branch, but this audit grants no whole-output N/A: camera-track lineage remains unqualified. Future exact static proof must exclude runtime source/dynamic/root/history reads on every admitted branch. |
| Alternate PS2 WorldDraw / coarse scenery | native_ps2_world WorldDraw packet commits 255/269/466/639; coarse_world other code-generated geometry | Follow actual world packet boundary, source placement and camera dependencies. Current Make selection must either exclude alternates or explicitly cover them; no inferred coverage from shared Texture hooks. |
| Native UI packet/direct/switch | prepare pending 453+, packet commit 7008+, direct account 7143+, Leon switch 7266-7310; world begins call prepare(nullptr) | Freeze independent Motion disposition before actual begin/transform. At switch account previous vertices before publishing next receipt. Header-only/zero does not emit. Generic nullptr is **unclassified**, never static N/A. |
| Optional modifier-volume/blob/raw TR | mv_shadow.cpp reads actor position/root and camera, accepted re4dc_ui_mv_send 7187; blob_shadow root/world; native_lake TR packet 8279 | These bypass model acceptance. They must get explicit derived-root/view Unknown hooks (or unsupported Make admission) before any complete detector claim. Accepted-prefix/return-success semantics must be tested at their actual send, not inferred from Texture enumeration. |

## Camera component — parent-confirmed in scope

`src/game/cam_motion.cpp:24/71-123` evaluates external Hermite track data and
history into pos/at/roll/fovy, including optional base_mat. `camera.cpp:109-142`
copies active/extra camera state into pG->Cam, then constructs rendering matrices.
World and actor output consume these matrices. Pure code camera math is not an
asset; an external track actually consumed by output is Motion. Null current
track, stopped playback or current camera geometry does not prove that all
previous track/history influence was overwritten.

For first-stage output classification keep separate reason bits for object pose
and unqualified view-track input. This does not assert every camera was externally
animated. No camera positive token, pose array or blanket all-geometry inheritance
is proposed. If a later implementation omits the camera alternatives/history
boundary, it must report that limitation and leave Motion unwired.

## What is actually outside this model-pose cohort

One narrow source example is native_ui.cpp movie_draw:9875+: four fixed-screen
corners x=0/640, y=0/480, z=1; UV depends on movie dimensions, no model/root/view/
Motion history read. Its accepted picture belongs to Movie/Texture, not an
inherited model Motion receipt. This is a local source proof, not a rule that all
UI, effects, screen-space geometry or movie-associated game state is N/A. Generic
UI, world sprites, filters, native lake, shadows, mirrors/RTT and raw packet routes
remain separate obligations where inputs can derive from root/view/track data.

No complete route-coverage claim is made by this census. It identifies where
future implementation must cover or refuse alternatives. No route is declared
Motion-positive, and no no-use counter is certified.
