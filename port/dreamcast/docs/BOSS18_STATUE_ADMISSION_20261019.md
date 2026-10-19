# r226 statue: source feasibility and native ownership — 2026-10-19

The original statue model is usable source data, but there is no qualified native ownership/input contract yet. This audit identifies the first blockers without making a new model, reduction, room fixture, runtime exception or pricing-only run. The full live source is necessary for the statue chase; cataloguec00 does not replace those actions (H033).

## Exact original source

`r226.cpp307` constructs `SetObjRobo` with room BIN1F/TPL20. `objRobo.cpp94..99` creates **ObjMgr object0x37**, then calls modelInit once; `obj.cpp284..285/315` constructs cObjRobo and installs its id. cObj's constructor sets kindid1; cModel's constructor defaults type0/OT0. The statue does not change OT or append another model info. This is **not enemyem37**, not the room's em11 enemy package and not scenery.

The existing original source set is immutable: `boss18-statue-source-20261019`, seal31041d53. Original PS2r226.dat SHA1fd7de5d, GCSt2/r226.das SHAe7be1402, decodedGC archive SHA01d1810b. Exact BINs: PS2`72ef8816697e2ecec9481f1da5cfd691ddc7a4e86079c1176675ab1c90f5238c`, GC`0bc3b7e1716426368905c6eedd6e29dd753039a9c52a1daa25208a02e282200a`. PS2TPL20 SHA`da331fe5505fda9941a38cec809e8e95a94dd43ea0e5f8ed8d6bda3b9fd38600`.

All23 source joint IDs/parents/local rests match GC exactly. All12631 PS2 triangles and17573 raw strip vertices remain original; no native packing or roundtrip is claimed. Every source influence is one or two bones, every numeric weight sum exactly1.0, all weighted IDs within the original23. Joint20 is unweighted but retained; it is not permission to fold/delete a source joint or change procedural/collision hierarchy.

All12 original material records are flag0, diffuse indices span all11 source images, and opacity/bump/spec texture indices areFF. All11 decoded source images are fully opaque (every alpha255). This establishes an opaque source-image footprint independent of cyclic face order; no sampling/tolerance or altered candidate membership. It does **not** certify final PS2GS lighting/render-state equivalence, native quantization, RGB atlas filtering/orientation, image compression or target appearance. Source material order, UVs/normals and texture identities must remain complete in a future conversion.

## First runtime ownership boundary

At pinned boss source89e5d4cc, `trans.cpp890..937` builds the frame ledger by walking **EmMgr only**. Registry id/part matching only nominates a plan; it cannot create a source ledger member. `platform/include/source_actor_owner_hooks.inc14..22` has separate ObjMgr kinds only for the Garrador core0x16/type4/14parts and Leon's flyinghead0x01/1part. **The statue0x37/type0/23parts is not one.** The identity function53..66 therefore has no admitted statue membership. With AUX0 it is absent as well. Do not move the statue into EmMgr or disguise it as an admitted class.

Owner: coordinator routes the **existing character renderer/registry owner under Performance P2** to establish a proper typed ObjMgr presentation contract: original live-list identity/lifetime and preparation, source model/info/material/texture facts, stable full original23-part pose, native skin lease, OT0 pass/visibility and source postlude equivalence. Test malformed identities, object reuse/lifetime, source state and actual live drawing; preserve the source objects and gameplay. No hidden allowlist, id-only match or guard/capacity relaxation is a fix. Boss18 does no runtime implementation.

This is an audit of the exact pinned source, not proof that another later Performance branch has no relevant work. The owner should check its current branch before implementation; no parallel runtime request or duplicate worker is started.

## Converter/data boundary

`ps2_cast.py::inputs` currently reads `BIO4DAT:<archive>.dat` and **GCem/<archive>.drs**, and records those paths. The statue comes from **PS2r226.dat and originalGCSt2/r226.das** (decoded source archive). Pre-populating an enemy-named cache or using enemyem37 would mislabel its lifetime/source identity. Do not do that.

When the ownership/input contract is concrete, boss18 can use the existing full exporter/native/registry machinery with an explicit room-source binding: preserve the full original archive hash, BIN1F/TPL20 facts,23owner joints and source textures. Coordinate any narrow shared converter edit through STATUS first; no change was made here. Use engine19's existing room data boundary when needed, not a new per-room format. Eleven source TPL images do not hit Salazar's34/max23 issue; native arena fit still needs an actual generated package/checker, not a vertex-based byte estimate.

## Live systems and required future checks

`objRobo.cpp169..242` creates original foot SAT/EAT and body EAT, hand switch dummy objects and14 hit boxes. Foot-carry uses source parts5/10 in SatMove737..800, pushes player/Ganados and updates source collision/dummies. Hands use original21/22, tread/hit parts13/16, and all source idle/hand/passage/door/bridge/fall motions remain authoritative. SetBeginEvent150 preserves movement through source no-suspend, so “event” is not synonymous with prerecorded movie. None of these systems uses a simplified render mesh for collision.

Future full-data qualification: complete oriented PS2 corners/material/UV/normal/weight roundtrip, original23-joint native rest/representative poses, unchanged source room archive lifetime/facts, actual ObjMgr statue native draw, all live hand/foot/carry/chase actions, materials/VRAM/residency/48KiBKOS and STRICT/decisions, then a current whole-frame disjoint cost window from required route/fight qualification. **No g50 until that fight projects over33ms**, g33 only ifg50 still misses. Raw vertex estimate12.3011ms alone does not supply the missing whole-fight remainder.

## Receipt

Private `boss18-statue-admission-20261019`: 6files/85005B, SHA256SUMS `4c281573aca08b1ac1f72dc7ab2cdd827779bfc37e60b4fe92462290bf9c0552`, immediate byte-verified C mirror. It retains source feasibility/material/alpha/weight proof, exact source file hashes, original source receipts and scripts. Actual original game bytes remain in the existing source set; no native model, new image or video is generated. Hash-only public handoff: `tools/d367/boss18/statue-source-owner-20261019.json`. Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/statue-admission-20261019/`. No recipe/runtime/allowlist/room/gate/build/Flycast/LOD change or route/whole-boss completion claim.
