# Krauser full source info pools, 2026-10-18

Both existing Krauser source presets now prepare their full original geometry and every hand/death alternative through an explicit original-body inverse-bind retarget. Native512KiB3pose checks, independent original-GX VERIFY and VQ packaging pass. This is source preparation, not a complete boss package, current-program visibility fix, animated retarget approval or LOD acceptance. No game code, runtime skeleton, motion, collision, admission gate, capacity or bone tolerance changes.

| Form | Original modelInit BIN/TPL | Original GC bones/parts | Source info pool /source live infos | Full nondegenerate triangles /strip corners | Records /palettes | Attributed draw/logic MODELLED |
|---|---|---|---|---|---|---|
| Human type1 |0x15/0x17|127/127|12alternatives /7expected from original construction|8939/13015|7383/338|Unpriced/unpriced|
| Arm type2 |0x1A/0x1D|127/127|11alternatives /7expected|8822/12718 (2original degenerates)|7135/393|Unpriced/unpriced|

The counts include full source hand alternatives and the death replacement, not a claim that all alternatives are simultaneously drawn. Human BIN5/6/7 accessories and knife9, four right-hand BIN0xA..0xD, left0xE/0xF and death0x21 remain. Arm BIN5/6/0x1B/0x1C, knife9, four right hands and death remain. Original em39HandSet swaps a live info rather than appending every alternative; death replaces the body info. The cap obj12 and held knife/gun/bow/thrown-weapon actors are separate and still need source model qualification. Original knife QTE/parries/grabs, mutated-arm shield and weak/contact hit zones, source hand swaps and death/movie callbacks stay in code. Gunship em3a preparation is separate.

## Original body owner and explicit retarget

The PS2 and GC body tables have the same127IDs/parents, but local rest translations differ by16.6567mm human/55.6813mm arm. Existing source_bind_offsets proves the same-ID/parent correspondence with pinned original body BIN hashes. Maximum virtual world offsets are20.2479/73.4712mm. Authored PS2 positions, normal/UV/material identity and numerical weights remain unchanged; the original GC127parts and inverse binds remain. Source nonidentity-matrix algebra errors are below5e-13mm, with source-weight float rest residual about5.2e-5mm. This is not original animated-pose evidence or an acceptable-look conclusion. No wider --bone-tol is used.

Source cModel::modelInit/initJoint/setPartsOffset creates cParts and their bind matrices from the body. cModel::addModel only links cModelInfo. calcWeightMat in trans.cpp uses those original body parts/bind matrices for every info. Consequently the addModel section's partial/duplicate rest table is source metadata, not another installed animation skeleton.

The optional source-pinned-retarget-owner-attachment policy requires exact attachment PS2/GC and owner PS2/GC BIN identities plus the existing separately pinned body bind-offset contract. Every PS2-weighted ID must exist in its original PS2 table, GC section and unchanged body owner. Original IDs/parents, finite translations/matrices, complete owner hierarchy, parent order, consistent duplicate records and weighted section references are checked. All original PS2/GC section records remain verbatim in source proof; no dictionary collapse removes records. The current legacy identity-owner policy stays unchanged.

Hand BINs have12rest records repeating IDs9/10/15/16, not12distinct finger bones. Right hands weight10 and left hands16, both original body IDs. Human head/accessory BIN7 has121GC records and127PS2 records. Its unused GC attach120/121 metadata has parents112/10 rather than owner99; none of this section's PS2-weighted IDs uses120/121. The source proof retains those records and validates their references while requiring weighted section IDs to name the original owner. It does not install the unused table as cParts. Arm BIN0x1C has44PS2 records and127GC records; every weighted ID remains present in the original body and GC section. No missing surface is dropped to pass conversion.

## Source and native controls

An independent audit reads each original PS2 BIN and compares the complete oriented nondegenerate triangle/corner sequence to the converted info pool: original positions under the existing5decimal dedup key, numeric weights, normals, original TPL/material-to-atlas UV identity, winding and duplicate multiplicities. All source roles pass, and every original GC owner ID/parent/rest matrix matches source.json and mesh.json. All used PS2 diffuse images are opaque alpha128; unused semitransparent images remain in the original archive and are not silently selected or flattened as active source alpha. Standard VQ colour compression and the native source look still require visual review.

Both distinct full pools pass unchanged512KiB host checks at3poses plus independent original-GX VERIFY; no source role is reduced. Human runtime header SHA25637984186d76abb9d37c75fbf623dca36851e4b31ba303d77c9c0a6cda1f69ad4; arm a735f9e7e0a3a048022abfcb0872aa46621115bc0d81b3b15faa9877f465701f.37focused/existing controls pass:12retarget-owner,6legacy-owner,3bind,8slots,4ordered-strip and4sampler/POT. A default-off Verdugo tail control's source/mesh/bindings/atlas/all generated native inputs are byte-identical across13files. Its optional RGBA atlas is absent in both; an initial verifier incorrectly required that absent opaque-only file, and the failed verifier log is retained. The first native attempt lacked an old host stub path; a verified existing host-only stub was reused, with the failed setup log retained. No native check was weakened.

## Remaining gates and evidence

Historical Island i18s4 kev1/kev2 shows source-live Krauser type1 at10000HP and changing routines/positions but no39draw census. Its registry covers em3a only. Current source already has the Em39Init placement-new fix that preserves subArc; this does not prove the historical invisible state repaired. Prepare the whole source role pool/attachments under existing registry limits and retest exact-current alive-versus-drawn, without a GC fallback, room edit or forced boss state. Source ordering, all material/hand/body/death states and original movie/knife-QTE callbacks must still qualify.

Complete cap/weapon/gunship source coverage, full actor registry/target admission, actual retarget/hand/clothing/arm/death poses, current native drawing, full/g50/g33 packages, source STRICT/decisions, complete residency/heap4/VRAM/KOS, exact ordered attributed MODELLED/Flycast and same-frame PS2/full/reduced sheets remain pending. No exclusive cost, saving, user choice or physical-console acceptance is claimed. I-006 reserves engine services to the engine lanes; these changes are offline converter proofs only.

Private boss18-krauser-20261018 currently has316files/43083705B, SHA256SUMScd27fb84126c00a11aa6bc69f0530cdc24569e6bbff3c6e6acfc301739b423d4, immediate C:/Game Dev/Emulators/re4-assets-private mirror verified. Earlier3/4file source snapshots remain under C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/source-snapshots. KRAUSER_PROGRESS.json separates pending gates. Evidence root contains krauser-full-source-identity-proof.json, owner-bind audit, full conversion/native and default-control logs. No model/media bytes are committed, chapter recipe/default selection or runtime format changed.


## Whole support and original-owner registry proof milestone

The source set now includes every independent cap/held-weapon model and the original helicopter missile, plus reused em3a body variants. All six new supports pass unchanged 512 KiB native checks at three poses, original-GX VERIFY and VQ packaging. Independent original PS2 oriented corner sequence, weights, normals, material/TPL UV mapping and original GC hierarchy/rest pass for each. Existing em3a conversions are reused from ch5regen/c16 with matching original archive hashes; rerunning the native checks reproduces both retained runtime headers byte for byte. No source archive or model role is removed.

| Separate source model | BIN / TPL | GC bones/parts | Full triangles / strip corners | Source system |
|---|---|---|---|---|
| cap obj12 |em39 0x16 /0x19|1/1|261/355|source SetObj12, parent head4, original local offset|
| knife enemy42 |em39 0x26 /0x25|2/2|334/558|parent0xA, original motion ARC0x27|
| gun enemy42 |em39 0x2C /0x2B|6/6|664/1118|parent0xA, original trans-mode state|
| bow enemy42 |em39 0x32 /0x31|5/5|1152/1776|parent0x10, original trans-mode state|
| arrow enemy42 |em39 0x37 /0x38|3/3|210/310|parent0xA, original projectile be_flag0x4000|
| helicopter missile obj38/type1 |em3a 0x9 /0xA|1/1|150/190|parent9, original shootable hit box/fire/explosion|
| em3a types0/1 |em3a 0x5 /0x6|13/13|1474/2178|original parts/patrol/wobble/weak spot/missile pod|
| em3a type2 |em3a 0xB /0xC|11/11|1925/2815|original source logic and parts|

Shared player grenade/flash source models remain the original PL_ARC0x6A/0x6B and0x6A/0x6F; they are not silently reauthored. All draw/logic MODELLED costs remain unpriced. No actual animation, source-system or full-fight result follows from these offline checks.

The six explicit source configurations are saved in tools/d367/boss18/krauser-support-presets.json. They are an offline configuration rather than a production room selection: verify the four original archive SHA256s, load only the `presets` mapping into ps2_cast.PRESETS, then run the existing convert/native/finish steps. No new ps2_cast default or chapter selection is introduced.

The optional model_registry source_owner_contract consumes a manifest with an explicit SHA256 selection. It pins canonical source.json/source-bindings.json, the exact native header, original PS2 DAT and GC archive, and original first modelInit BIN. The helper independently rereads every original BIN, PS2 bone record including duplicates, GC part record and actual PS2 weighted ID. It requires the unchanged original GC body hierarchy/rest, exact original source metadata, consistent duplicate records, finite values, source-owner BIN identities and valid weighted references in all original tables. Different unused attachment metadata remains verbatim; it never becomes runtime cParts. Header weights cannot escape the original section's source weights. This proof cannot combine with another skeleton projection. All raw material/BIN/part facts and existing target skeleton/certificate/capacity checks remain unchanged.

Thirteen owner-contract controls pass, including four BIN identities, manifest/source/header/archive pins, duplicate/finite/weighted/parent references. With this option absent, the full Verdugo source package remains byte-identical, SHA25698a65dff72b6e2a794d1f57c1e6e49b8135028543ebd033b195c713e4fc98d59. The initial ordinary whole-pool exporter refusal and subsequent full-set capacity refusals are retained as evidence, not accepted packages.

| Selection | File bytes | Skin bytes | Arena / existing capacity | Result |
|---|---|---|---|---|
| both original Krauser forms + five supports + both em3a |440224|24600|464824 /425984|REFUSED|
| complete set above + original helicopter missile |443808|24640|468448 /425984|REFUSED by42464B|
| human-only diagnostic + all supports/em3a |287488|12168|299656 /425984|target host checks only|
| arm-only diagnostic + all supports/em3a |285600|14176|299776 /425984|target host checks only|

Each phase diagnostic keeps all original hand/death alternatives for its own body form. The other body form is explicitly absent from that one-phase fixture. Neither is a complete room/fight/cutscene/handoff production candidate. Human package SHA256fba36df3ad9b463100aa83680590be91c17bf6520af18b66af3cadc8a38820a1; arm4965db26ceef9eefc768b36e2c5e5324b7ddfb018db76cf7c2555f03424b3145. Twelve checks against the actual target pack checker pass: both good packages plus wrong-room, corrupted hash, out-of-owner weight, invalid unused original parent and nonfinite owner bind refusals. These retain all127 body-owner joints; no skeleton or limit is reduced/raised.

Remaining source/runtime boundaries are explicit. A pool's first live info must prove section0, so the original death body swap to the retained nonzero death row is not yet admitted. The arrow's source be_flag0x4000 is refused by unchanged registry_bind. Separate cap/weapon object ownership remains unqualified in game. Existing pool descriptors cannot carry lod_of. No engine or admission exception is added for any of these. The complete native room set still refuses the original arena ceiling. Current-program original-input human visibility, source hand/event/death/arm retarget animation, complete materials/residency/heap4/VRAM/KOS, STRICT/decisions, cost attribution and look sheets remain open.

This milestone's private boss18-krauser-20261018 has945files/87228288B, SHA256SUMSebd24f884fe15f2585de706070eff31403f1799b82d6471751d9fe44cd1335d2, with immediate verified C mirror. The earlier316file info-pool seal above is historical. REGISTRY_PROGRESS.json, support-source-identity-proof.json, support-native-summary.json and package-host/results.json preserve the source/target evidence. Source-snapshots/krauser5 preserves the prior seal. No game/model/media bytes are committed; no production chapter recipe, format, runtime gate or capacity changes.


## Exact-current integration-core visibility diagnostic: source allocation failure

The current383 integration-core program b18aarT, source50ce1ea3, ran55.92seconds in Flycast. Stripped ELF SHA256e12eb5ad6f04c8baa63c6007b17a1d4d0df406b89df8b3475804f2ca3bccb776; final pre-strip7c651bd39d346e694e3f57d0532405d8bd4fd715ea3929519de1955af531b313. Boot and every linked overlay, the human-only package and9selected atlas packages were verified against the staged payload. The temporary copy-only final-symbol hook was restored byte-exact; source is clean. Actual KOS held49152B.

The retained Island recipe first refused the unchanged unknown-knob guard because MOTION_LARGE_CLIPS, ROUTE_FINAL, NMR_PRELOAD_SKIP and RESIDENT_SHARED_R327 are Island-only code absent from current integration. No guard was bypassed or Island branch resumed/merged. A separate documented current-core recipe excludes those four unimplemented flags. This program is not the paused Island branch's qualified streamed-room program.

The unchanged room AEV7 was independently read from staged r31c.arc. The diagnostic initial position11250,0,11500 is inside that original physical trigger; no atfunc/god/HP/flags were written. It enters original r31cEventS00, but source allocation fails: NMRPACK opens287488file+12168skin,299688aligned cell, before actors. The em39 archive1423712B leaves270624B; original resident motion allocations and93564B overlay leave39424B. The original127part allocation60000B fails, later partial allocations drain heap4 to256B and source ModelInit reports failure. No live39 and no39draw census follow. The s00 movie also fails allocation: terminal3,0/1375pictures. Configured ordinary START does not prove a skip/end callback when no picture is presented.

Entry/no-fatal/world and TEX/CAST-GC/NOT-DRAWN checkers report PASS for their sampled scope, but they do not qualify the absent boss: only native Leon and out-of-view source props41/43 are recorded. The short-walk8040.8mm displacement includes original r31cEventS00 SetPosAngY, so it is not traversal proof. Overall first-pass remains UNPROVEN. No visibility fix, original retarget animation, full fight, STRICT or cost is claimed.

At f767 VRAM is1371648pinned/1061408dynamic/90112other/free44256/largest13280B,0refusal/eviction/retry. Loads rise122to173 after early preload; residency remains open. Room memory/streaming belongs to Island/coordinator and is not changed by boss18. The complete original source package also remains42464B over its separate425984B arena limit. Investigate lossless common atlas placement to expose already-identical source geometry across forms; do not drop source forms, hands/death models or increase limits.

Evidence: krauser-current383-human-source-failure.json and h-b18krauser/scenarios/cx-r31c-human-source-a, plus byte-bound builds/b18aarT. Private source/evidence set is952files/88594571B, SHA256SUMSf2ec2d432696facfea11ee9e42d11243f662500526a215f2e758b149ea8b167b, immediate C mirror verified. Earlier seals are historical and retained. All source claims are released; no emulator or build remains running.
