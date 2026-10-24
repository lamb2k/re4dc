# Exact owner, constituent and lifetime contract

Source-only handoff. This closes the mapping in PLAN.md; no source patch or coverage result is implied. Line references are frozen e303aaeb9/d5c native_static.cpp, not post-fb254 application coordinates. The implementation owner must rebase against the landed source and verify every anchor.

## Exactly 16 stable owners

Use one fixed PayloadProof per existing stable owner, behind the diagnostic gate; embedding is allowed only if all existing whole-owner resets preserve its registration/link fields. Otherwise keep that single record adjacent to the stable owner, without adding a lookup table. Retire invalidates source identity but must not erase the proof object or duplicate its registry link. These are identities, not a separately allocated owner table. Array index is identity; filename, current pointer equality and format name are not replacements for saved serials.

| ID | Stable identity | Actual file owner/selection |
|---|---|---|
| V0 | views[0] | MAINSCENARIO View |
| V1 | views[1] | FILE_00 View |
| V2 | views[2] | FILE_01 View |
| V3 | views[3] | FILE_02 View |
| V4 | views[4] | FILE_03 View |
| V5 | views[5] | FILE_04 View |
| M0 | mesh_views[0] | MAINSCENARIO MeshView |
| M1 | mesh_views[1] | FILE_00 MeshView |
| M2 | mesh_views[2] | FILE_01 MeshView |
| M3 | mesh_views[3] | FILE_02 MeshView |
| M4 | mesh_views[4] | FILE_03 MeshView |
| M5 | mesh_views[5] | FILE_04 MeshView |
| M6 | mesh_views[6] | COMMON MeshView |
| W | ps2w | Actual selected world mesh/R4PW and accepted interpretation set |
| F | farshell::st | Independent FSH1 package; proof survives State reset |
| S | std_room | Digest-only original low/index.txt receipt, retired before parsed-state reset |

The exact MeshView identity is each of the seven objects in `mesh_views[kMeshViews]` at native_static1437. Do not create a second alias owner or a seventeenth R4TI cache owner. S uses existing payload_capture_digest semantics: it proves no positive address range, its source digest is captured before tokenization/free, and its serial lives only for the corresponding complete successful parsed state. Its retirement occurs before any parsed-state replacement, including failure cleanup. Checked digest lookup is cold, never during submission.

## Exactly 12 canonical roles

The immutable composite is little-endian, 688 bytes: 64-byte header and exactly twelve 52-byte rows. Header: magic `GCSTC001` (8), six u32 words (schema=1, owner kind, room, role count=12, interpretation/profile code, reserved=0; 24), then selected full-geometry SHA256 (32). Thus header is 8+24+32=64. Each row is five u32 words (role tag, state, exact consumed length, format version, section flags) plus SHA256 (32). No ABI struct padding is serialized.

| Ordered tag | Role | Original accepted bytes |
|---|---|---|
| 1 | R4PW | Full validated placement sidecar |
| 2 | R4ID | Full validated identity sidecar |
| 3 | R4TC | Full validated transparency classes |
| 4 | R4PV | Full validated PVS file, excluding generated suffix |
| 5 | R4SG | Full validated selected group sidecar, before dedup writes |
| 6 | SCCN | Exact original room section, version/flags bound |
| 7 | SCPS | Exact original room section, before slot memset |
| 8 | SCDD | Exact original room section, after read-only validation, before dedup writes |
| 9 | SDO3_BASE80 | Exactly the consumed standard-file 80-byte header probe and selection; never full-file identity |
| 10 | R4TI_SELECTOR | Exact bytes of the accepted selector read before parsed copy |
| 11 | STD_INDEX | Exact original n-byte low/index.txt, checked through S |
| 12 | PCL1_CELL | Full validated kPcFileBytes, excluding appended frustum buffers |

Every role has explicit NOT_APPLICABLE, DISABLED, ABSENT, REJECTED, ACCEPTED or UNPROVEN state. ACCEPTED requires a nonzero full digest and reviewed origin. A compiled-out role is DISABLED, an inapplicable format role is NOT_APPLICABLE; neither is an implicit exception for reachable data. A parse failure that preserves rendering may be REJECTED but cannot authenticate contributing state. Canonical row order/length/version/flags/state/profile and selected geometry all enter the composite digest. Ordinary View/MeshView/FSH1 owners keep irrelevant roles explicit NOT_APPLICABLE; any actually consequential STD_INDEX/PCL1/source visual dependency must be included or leave the accepted use unknown. Standard full selected geometry and FSH1 capture remain full-file receipts, not BASE80.

**R4TI retained-state limit:** trans::listed5067-5080 lazily consumes a local read and retains idx_rooms/idx_n/idx_state without an original digest. Capture the original exact accepted read at its first safe cold read; later cached decisions lack that original receipt. Under this fixed16/no new cache design, a later load must mark role10 UNPROVEN unless independently reauthenticated from the original consumed bytes at an approved safe cold boundary. Do not reconstruct/hash idx_rooms, assume a filename origin, or silently carry a receipt through unrelated proof ownership. If a first read does not yield a complete original consumed-byte receipt, it is UNPROVEN too. This deliberately limits coverage; explicit root classification or a separately reviewed no-cache reauthentication protocol is needed to expand it.

## Every mutation and independent close

Revoke affected composite serials before each operation below. Revocation must preserve prior accepted-use accounting and cannot perform catalog lookup, logging or I/O inside SQ/G2/LH. If the existing retire API flushes or reads the catalog, split memory-only invalidation from deferred unlocked accounting. Never grant a replacement serial until all dependencies are captured and validated. A bounded scan over the existing owners to revoke all potentially affected static/world owners is permitted; a new resident dependency lookup table is not needed. Conservatively invalidating unaffected owners costs coverage but must not change rendering.

| Boundary | Required action |
|---|---|
| View retire781/open822-858, all failure exits | Retire Vn before storage/free/replacement, before adoption can overwrite; do not register a partial load. |
| MeshView retire1456/open1481-1524, Original/Standard replacement, all failures | Retire Mn before source storage or tables are freed/overwritten; capture complete original file before adoption/light preparation. |
| World initial load5536-5594, selected file switch, failed/partial adoption | Retire W before first overwrite; geometry and R4PW alone cannot publish it. |
| dyn::reset and R4ID block replacement5631-5660 | Revoke W before IDs free/replacement; no silent fresh-slot rebinding. Ordinary actor pose updates are mutable game state and do not mint origin. |
| trans::close5060/open5085-5107, R4TC failure | Revoke W before cls/block free/replacement; lazy selector reset/replacement also revokes every dependent owner. |
| pvs::close4904/open4921-4980, rejected new source | Revoke W before original PVS free/replacement. Generated offset arrays/runtime cur selection do not produce source receipts. |
| R4SG publication5753-5765/free or replacement | Revoke W before sg_block changes. Capture accepted original bytes before any range rewrite. |
| SCCN publish/replacement5230-5240 | Revoke W before pointers/section identity change, and before parent leave. |
| SCPS publish/replacement5247-5260, piece free/reset | Revoke W before section identity replacement. Hash original before first slot memset; declared subsequent runtime slots do not authorize rehash/renewal. |
| SCDD check/run5408-5430, dedup_free, mode change | Capture immutable original before first run; revoke W before replacing mapping or switching its source/mode. Mode1-generated and mode3-embedded states must differ from an accepted external SCDD. |
| room_file.c leave67 and new-parent replacement | Revoke affected W before original parent block free, including borrowed SCCN/SCPS/SCDD. Use a real hook, never recycled parent-pointer equality. |
| StdRoom enter/reset3364 and std_parse failure/replacement | Retire S first and revoke dependent V/M/W; hash original text before parse/free3366-3373, publish S only after complete parse. No prepared index rehash. |
| pc::unload1942/open1956-1980, independent PCL1 replacement | Revoke dependent static/world proofs before free/replacement. Hash original cell only, not mutable frustum suffix. |
| far_shell close69/open/release/movie lend/shortfall | Retire F before reset/free/overwrite, including all failed opens. W can never stand in for F. |
| ps2_movie_unpublish4491, reload5787 before first read/overwrite, reload failure | Revoke W first; retire independently affected F/other owners as appropriate. Reload's trans::close5847 and possible PVS close also revoke independently. Reused prepared SG/SCPS/SCDD/IDs plus fresh geometry/R4PW are insufficient to renew W. Keep accepted movie-return source unknown unless every original constituent is reauthenticated. |
| re4dc_ps2_mesh_retire7130-7185 and full room leave | Revoke W before its first nested close/free; nested independent hooks remain required. |
| catalog replacement/checked token mismatch; owner same-address rebind | Old saved serial remains rejected; do not resolve a new owner/proof at replay. No source lifetime is extended by object address equality. |

Permitted declared derivations (adoption, light preparation, generated PVS offsets, SCPS slots, dedup package/SG rewrites) may retain the original receipt only within that same proven ownership lifetime and the reviewed parser/derivation profile. Any independent source switch/reload/unknown mutation revokes first. Tests must mutate each of the twelve roles independently (including state/absence/length/version/flags), each independent close, and movie partial/failure paths; mesh-only equality must fail every relevant sidecar mutation. Source CLR/alpha dependencies still unproven must keep known consumer attribution with serial0, not be erased by a healthy composite.

## Allocation accounting and accepted-use controls

New persistent raw metadata is exactly704B proofs (16x44) plus576B queued quad uses (48x12) =1280B. The15 original stable owner proof records are660B of that704B; S adds44B. Do not add existing PayloadProof fields, two CheckedAssets, serial/uses/link, existing128-owner registry, existing SourceUse20B, current deferred pointer/serial/mask or existing4B active quad pointer again. They are reuse, not extra records. No ChunkPart/pick/geometry growth is required by this plan.

The688B manifest is cold stack only and dies after composite hashing/capture; two control words8B and final Digest32B give caller raw728B. Existing hash context104B/read scratch512B and compiler frames are separate call stack, not claimed included or target-priced. Quad flush borrows48x12+16+4=596B raw local state; PayloadScope also saves its existing20B SourceUse where instantiated. These are arithmetic source budgets, not measured linker size or stack high-water acceptance.

Accepted-use hooks are the actual NativeUI packet count>0 commit7012-7018, direct vertices>0 accounting7153, batch end7175-7182, and lean/direct switch7281 BEFORE next prepare7300/7305; hot/cold world9070/9233 inherit explicit W scope. Mixed quad acknowledgement requires exact emitted vertex buffer and4xactual copied quads. Selection/transform/upload/culled nr0/begin/zero count do not acknowledge; accepted prefix then abort acknowledges only the committed prefix. Stale/retired/missing proof keeps SourceGeometry/Weapon mask and stable pointer with serial0, never ambient proof. Exercise all hook branches, suppressed hooks, owner-rebind replay, unknown/mixed origins, wrong batch/count, capacity failures and all-zero output. Flush/log/catalog processing only after direct/batch/SubmitScope closure outside SQ/G2/LH. Gate0/preprocessed/object/programme identity, Required/wired masks and all existing numeric/material/receipt guards remain unchanged. No coverage PASS is granted.
