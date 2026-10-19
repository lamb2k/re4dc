# em30 / em33 / em34 / em37: source identification

No normal selected-list instance is established for these four IDs. Their old census estimates must not be presented as costs of four additional active island bosses. This completes the ordered **identify first** intake; it does not qualify conversion, drawing or play. No synthetic actor or room was created to manufacture a timing baseline.

## List and loader proof

At source `25e817a8050c6bbdd34329c13da90070613d5055`, original PS2 USA BIO4DAT.AFS contains32 ESL files, and the retained original GC Debug Disc1 FST contains13. All45 files /11021 records were decoded in their original endianness, including inactive rows, alternate lists, Ashley and bonus lists. The ten retained PS2 chapter-list sources also match their freshly read original-disc entries byte-exact.

Only18 target-ID rows exist:9PS2 +9GC, all **em30 type0** in `emleon08.esl`, rooms104(two),105(two),10c(two),10d(three). There are no em33/em34/em37 rows in any audited list.

`src/game/stage.cpp::emlist_name` selects `emleon00..07` and `omake00..02`, not `emleon08/09`. `checkEmListNo` returns0..7 for the story,8 for Assignment Ada and9/10 for Mercenaries; those last three indices select the omake files. The debug selector is clamped to `getEmListNum()-1`, the same11-name table. Thus the nine em30 records are **not reached through this source list selector**. This is bounded list/loader evidence, not proof that no hardcoded event, different source revision or external debug path could ever construct one.

Source display names and the actual default loader are different kinds of evidence:

| ID | cEmMgr::idName | Default normal EmFileTbl / FileTbl |
|---|---|---|
| 30 | SADDLER | em30 archive / rel/em30.rel |
| 33 | INSECTBOSS EVENT | generic em10 archive / rel/em10.rel |
| 34 | MAYOR | em34 archive / rel/em34.rel |
| 37 | NO2 | generic em10 archive / rel/em10.rel |

The checked Ada table has the same four mappings. `em33.dat/.drs` and `em37.dat/.drs` are absent from the original audited disc catalogues. `em34.cpp` contains variants with Em33/Em37 helper names, selected by **type within that module**. Those source helper names do not prove global IDs33/37 load em34; the default table above does not. No missing independent em33/em37 conversion is invented.

## Complete source model roles, without admission or timing claims

| Source family | modelInit owner | Additional model infos / material source | Bones / parts; infos | Special systems retained if ever admitted |
|---|---|---|---|---|
| em30, type0/other | BIN4 / TPL5 | BIN6+8/TPL7; BIN9, A(type0) or B(other), C, D/TPL5 | body143/143; seven source infos; C/D section metadata147 | target player/partner; procedural neck3; two cloth chains; source damage/collision/death; flag-negative mode hides infos6/8 and creates three26-part head objects, each with four10-part parasites; player damage motion20 |
| em34 type0 | BIN4 / TPL8 | BIN5 shoulder,6 head,7 hand / TPL8 |161/161; four infos | two cloth chains, neck tracking, source collision/hit parts/lock-on2, phase/death/motion handoff |
| em34 type1 (Em37 helpers) | BIN9 / TPLB | BINA / TPLB |111/111; two infos | hair/coat cloth, source bite/contact/motions13..16, target player/partner, neck/hit/collision/death |
| em34 type2/3 (Em33 helpers) | BINC / TPLE(type2) or F(type3) | BIND / same TPL |201/201; two infos | two cloth chains, source bit24, hit/neck/collision/motion/death behavior; same geometry with source texture alternatives |

These are original source contracts, not a tested runtime pool. Extra section rest metadata is not silently treated as the body owner table. Grabs/QTE/visibility/cutscene paths are unqualified; full source state must remain authoritative. No g50/g33, palette compaction, hierarchy rewrite, fallback, certificate exception or larger arena is introduced.

Fresh per-BIN census confirms the former table's selected main subsets:

- em30 BIN4:4443 triangles/6319 strip vertices/143bones; BIN6:4070/5580/7. Merely summing those two,8513tri, omits five other source infos and the possible head/parasite objects. It is not a complete actor cost or simultaneous drawn set.
- em34 type0 BIN4/5/6/7:1941/2769/2612/2769 triangles; all source161bones.
- em34 type1 BIN9/A:5161/9939 triangles and6885/13013 strip vertices, source111bones. Its raw15100-triangle sum is a source inventory, not an active island fight measurement.
- em34 type2/3 BINC/D:3535/2086 triangles and4953/2936 strip vertices, source201bones.
- Same-index GC triangle counts match these source counts, but raw bytes differ. Counts do **not** prove exact material/weights/winding equality. No full roundtrip or native draw is claimed. Exact raw PS2 BIN matching against the already-touched em2c/em31/em38 archives found no reuse match; none of those bodies is substituted.

**Draw and logic costs: unpriced for every row.** There is no qualified active source actor/room/build/window or caller/field witness. The old triangle-factor census is not current exclusive attribution. No actor division or presumed30fps saving is reported. Mendez's approved em35 work is untouched.

## Preserved evidence and source boundary

Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/`:

- `item9-original-source-lists-20261019.json`: original AFS/FST offsets, all file hashes, complete hit records, source hashes.
- `item9-source-selector-loader-proof-20261019.json`: exact source-selected11 filenames, ID display names and loader targets, bounded empty selected-list intersection.
- `item9-source-model-census-20261019.json`: every BIN and parse result, original source bones/strip counts/GC parts and raw-hash comparison. Failed parses would remain explicit; none is replaced by an invented mesh.
- `item9-identification-final-seal-20261019.json`.

Private `/root/re4data/private/boss18-item9-identification-20261019`:52files/7751832 B, SHA256SUMS `e4695dbc23348ad87afcae7a2dee6ad853d44cf30528093752d279c7aee0b835`; verified immediate C mirror under `re4-assets-private`. The four raw source archive hashes are:

| File | Bytes | SHA256 |
|---|---:|---|
| PS2 em30.dat |1240672|38000f1ecdd02c24f8057cf9cea9cb42a4bf20532088499faa38323d20ec30f2|
| GC em30.drs |878592|ec55f456489a5a2b95561b7b0a7ee95785d6b9e179a1ede68bdbb7b89686bbc6|
| PS2 em34.dat |2745632|3407a5288518745c21ab7d91f42a5e0e8b08a40f09b2e5312c465f9f5a006b2a|
| GC em34.drs |2490464|75146c74c8d4287af8b892b61e6b99d3effb4d7e70fe676e8cf08eef528cf2ce|

Relevant source: `src/game/em.cpp::cEmMgr::idName`, `stage.cpp::{checkEmListNo,emlist_name,getEmListNum}`, `read.cpp::EmFileTbl`, `dvd.cpp::FileTbl`, `src/em30/em30.cpp::{em30_R0_Init,em30SetParasite}`, `src/em34/em34.cpp::em34_R0_Init`. Exact file hashes are in the private proof.

No build/emulator/converter/runtime/room/recipe/gate or shared-file edits were needed. Island remains paused. Before an actual conversion/LOD trial for these families, a room owner must establish an original active source construction path with the correct type/archive and a live/drawn fixture. This is an input boundary, not a request to add spawns or change the game. Other boss material/runtime blockers and the twins' pending user choice remain separate; no overall boss completion is claimed.