# Shared motion consumers: source checkpoint, October 20

This continues H050/H055 and the root A01–A16 ledger. **The holistic audit is OPEN.** This checkpoint closes local evaluator/helper contracts and names the remaining dispatch/owner edges. It is not a new room audit or a claim that 66 enemy implementations were reviewed.

Source is pinned to `c7e0358a`; the generated receipt contains full SHA256 pins for every indexed source file. The sealed H050 metadata SHA256 is `3adb52b984ed441fe52d58b704d1abc392c11afc39e3ae24a78f551ba756ce60`: 66 selected QA archives, plus nine separate original/later/prepared records (75 total). No ISO extraction, asset preparation, program build, guest or new timing run was performed. Later/prepared boss data is not relabelled as QA-disc coverage.

Owner: Boss owns this document and checker/tests. Root owns aggregate capacity, integration and target checks; QA owns A10–A13 texture/effect/audio source work and resident-list checks; castle continues original progression. No shared runtime claim is held. H056/H057/H058 runtime repairs remain separate cherry-pickable components; H055's historical repair status is superseded by their handbacks.

## Proof levels and remaining audit

| Ledger | Source contract reviewed here | Still OPEN | Next source step / owner |
| --- | --- | --- | --- |
| A01 | All discovered functional Hermite calls in the source corpus route through seven locally leased scopes; wrapper families and ABI aliases are indexed below. Source work stores resident headers/proxy tables, not the leased payload table. | Selected linkage, raw/indirect pointer mutation and all wrapper argument origins are not a whole-program proof. | Continue dispatch roots and named selectors below; Boss. |
| A02 | Ordinary Hokan reads saved matrices. Seven enemy/boss blend helpers keep body plus one sign-selected secondary FCV. Additive zero-weight blend still evaluates; ordinary zero-weight blend skips secondary keys. | Cross-state setters and dynamic Work tables beyond reviewed groups. | Resolve selector/owner, not every reachable clip as a simultaneous union; Boss. |
| A03 | Face/shape evaluator is leased. Normal ShapeMove clears five storage slots then registers one pShape per active model-info. U3 extra body, Queen shell, Krauser arm and cEmWep/obj16 attachments are independent streams. | Number of active model-infos, all attachment motion setters, lifecycle and donor generations. Five slots are capacity, not five established active clips. | Attachment/shape owner graph below; Boss. |
| A04 | Six named em10 event setters and all lexical stage callers are traced to room archives; Work body/SEQ argument roles distinguished. | Other module Work tables, variable indices, phase/type dispatch and event BinTbl payload identities. | Use initializer index as input, then follow the actual dispatch family; Boss. |
| A05 | Twelve reviewed local groups mapped to selected MTC entries/keys/flags/bytes. Missing selected records are rejected, never inferred resident. | Remaining source groups, selected variants, pressure after preload loss; original/hot/follow-walk Ashley packages differ. | Map only source-established groups to existing census; Boss, with root capacity. |
| A07 | Entire source corpus indexed for subArc assignments, including normal restore sites; specific Mendez/Gigante groups reuse H055. Header identity, not player pointer name, determines cache binding. | Exceptional/interrupt/death exits and archive replacement while a borrower, face or attachment still refers to donor bytes. | Trace owner release and source callback termination together with A08; Boss + root. |

The checker runs ten structural Python regressions on the actual pinned source and sealed metadata. They detect a missing lease, a new unreviewed evaluator, changing a sequence argument into FCV data, the known Ashley failure/fix, absent variants and alias deduplication. These are **source-rule host tests**, not execution of the game evaluator, target compilation, gameplay or console acceptance. Existing cache allocator host/SH4 and QA/castle receipts keep their own narrower scopes.

## A01: evaluator and wrapper inventory

The leaf is `HermiteInterpolation`. Its source consumers are scoped by:

| Evaluator scope | Source pin | Stored identity and lifetime |
| --- | --- | --- |
| MotionSetCore | `src/game/motion.cpp:157,246,254` | Acquires key table locally; pMot/header, joint metadata, SEQ and pHermite_data proxy remain archive-owned. Local native_keys is used by MOTION_KEY on Dreamcast. |
| MotionMoveCore | `src/game/motion.cpp:660,676,792` | Per-call lease; evaluates joint and embedded attachment-camera channels from that one FCV. Attached-camera channels here do not imply another FCV. |
| MotionGetSpeed | `src/game/motion.cpp:990,1001` | Independent root-motion read through same lease mechanism; may revisit same FCV in the tick. |
| MotionGetPosition | `src/game/motion.cpp:1091,1100` | Debug/model-position path also leased. |
| CalculateShape_new | `src/game/shape.cpp:214,236,264` | ShapeWork/table is local; used during Hermite and vertex-delta loop, then released. |
| CameraMotion constructor / move | `src/game/cam_motion.cpp:24,42,50,71,84` | Constructor stores source proxy keyTbl; move substitutes a local leased table. |

`native_motion.h:20–38` RAII restores only the local destination and releases its token. `FcvGetMaxFrame` (`motion.cpp:1226`) reads the resident header word, not a key payload. `MotionSequenceCtrl` advances resident SEQ data. `MotionAddSpeed` integrates copied vectors and does not read FCV keys. Optimized Hermite leaf variants share this entry contract; their internal helpers are not separate archive consumers.

Wrappers/caller families, not just hook counts:

- `cModel::motionSet/motionMove` (`model.cpp:1808/1814`) → core setter / MotionMove. `cEmWrap::motionSet/motionMove` (`st/em_wrap.cpp:864/874`) checks live wrapper then delegates. Legacy two-argument MotionMove / MotionMoveF declarations and assembler aliases reach the same evaluator. The generated alias index includes em18..em3c, weapon modules, stage code, radio/inventory and tools; it does not assume all indexed code is linked in the selected program.
- `cPlayer::motionSet` (`pl_class.cpp:542`) selects **m0 OR m1** by dmMotCk, not two simultaneous motions. `cPlNeck::motSet` (`1677`) adds independent neck work; `cMot3::set/set0/move` (`1761/1784/1799`) stores three alternatives but plays body plus one secondary, switching at sign change. `cMotBase::move` (`cMotBase.cpp:50/58`) calls the leased speed reader, not a retained extra FCV.
- `MotionMoveSub` (`motion.cpp:645`) delegates to leased core and matrix Hokan; no external callers discovered. Direct extra core callers outside motion.cpp are U3 BodyMove, Queen ShellControl and Krauser ArmControl, reviewed below.
- em10/2b/2c/32/35/38/39 BlendMotSet wrappers each issue two MotionSetCore calls. em2cBlendMotSet2 and Gigante plBlendMotSet explicitly take two FCVs. ABI aliases em2bBlendMotSetI / em2cBlendMotSetI / em2cBlendMotSet2I / em32BlendMotSetI preserve those targets.
- Event `ExePacket_Mot/Shp/Cam` (`event.cpp:1256/1302/1145`) selects model and data independently through ModTbl/BinTbl. This wrapper is known; actual dynamic bin owner and end-of-event lifetime remain separate edges.
- Generic cEmObj, cEmWep, obj16, obj12, objGondola, objRobo, player weapon callbacks and borrowed escape handlers all reach these same core evaluators. Their **selector ownership** is not cleared merely by the common evaluator lease.

A01's lexical discovery is retained in private `motion-consumer-source-details.json` with path, line, symbol, arguments and context hints. The public receipt records counts, aliases and source hashes. Context hints are a source-navigation aid, not a C++ parser or CFG. Comments/strings are masked for call discovery; literal assembler targets are scanned separately with comments removed. Inactive branches, declarations and tools remain explicitly indexed rather than claimed as gameplay coverage.

## A02–A03: actual co-use and false unions

MotionMove (`motion.cpp:457–546`) reads the body, and at most the one attached blend work. Root speed and pose may acquire the same header repeatedly. Ordinary blend with Brate0 skips secondary keys; the additive flag0x80000000 branch still calls MotionMoveCore at Brate0. It does not recurse through an arbitrary chain of blend pointers. MotionSetCore normally clears the model blend unless the supplied work's keep-blend flag0x20000000 is set. Local literal keep-blend writers discovered in db_mod are debug/tool paths; this does not close arbitrary aliases/raw work mutations.

Hokan (`motion.cpp:333–338,837–984`) copies/interpolates prevMat and current matrices. The retained actual em12 hit entry20 (ARC33,15,584B) → back entry93 (ARC157,9,376B) does not establish two live FCVs. em10BlendMotSet is used for bowgun/rocket/gatling, not implicitly for ordinary hit/back. Both keys can recur later; the four-key farm temporal union is not declared concurrent.

| Reviewed source demand | Actual selected record mapping | Consequence / limit |
| --- | --- | --- |
| Ashley body12 + look-back18 + held face6d | Original MTC entries0/6/61 =5,152+5,056+448 =10,656B; fixed QA all inline. | The source checker flags the original **three strict cells**, clears only this selected hot group. These are ARC12/18/6d, not ARC0/6/61. The later pl11-walk package is separate. |
| Mendez spear | ARC6a body30,784 + negative6d31,680 OR other6c30,336; ARC6b is SEQ. | Each reviewed pair fits two strict-v3 cells. Reachability union of three is not thrash proof. Bearhug/release pairs remain H055 source-proven only. |
| U3 normal walk in forms0/1/2 plus independent body work | main/turn pairs B+D,3f+42,3a+3c are inline; AD entry50 is cold1,312B. | **Three real streams**, only one cached record in these selected groups. Main R0/R1 dispatch is followed by BodyMove (`em32.cpp:638/5036`); ordinary walk does not set death suppression0x4000. Other walk sign has same reviewed arity, not all-state qualification. |
| Queen type0 wait + shell | C + positiveE/otherD plus shell41 (shell alternatives40..44); all inline in later-castle em38. | Independent shell follows main dispatch (`em38.cpp:348/1919`), so two-helper-stream count alone would undercount. No cache-pressure claim for this inline package. |
| Krauser type2 wait + arm | D6 entry97 cold11,584B; source-possible Arm_rno8/default Arm_type0 selects104 entry120 cold7,840B. | Two real distinct records in this named branch. Arm controls FF..10a alternatives through Arm_type/rno; those alternatives are not all simultaneous. Type2 arm does not justify combining human MG's blend state indiscriminately. |
| Krauser human MG + gun | 7f/81 + attached gun2f =3 selected cached-hot-preload records,10,560B. | All three still count as cache payload; preload is reclaimable, not a permanent lease. Source group was already flagged by H050; no new runtime claim. |
| Ganado parasite body + core + tentacles | em12 core idle27b entry112, 5,248B; four independent tentacles253 share entry106, 2,304B; parent's current body is additional. | Source `em10SetParasite:22658–22749` passes donor header pointers into obj16. Four phase offsets do not mean four copies of one key. Full core attack/critical/borrowed-player group and variant selection remain OPEN. |
| Held face alongside borrowed body | Leon pl00/pl08 face62/63 alternatives inline; fixed Ashley6c/6d inline. | Faces use pG->pPlayer or Ashley's own ARC; borrowing subArc does not move these face owners to the enemy archive. Other playable-character variants remain explicit. |

ShapeSet (`shape.cpp:38`) retains pShape; flags2/6 hold endpoint frames. ShapeMove (`65–71`) clears all five slots and registers pShape once. CalculateShape_new runs in ModelTrans's per-slot loops (`trans.cpp:2017/5886`), so held endpoint is still a key read when rendered. The current source registration graph has one direct SetShape caller and no direct slot data writer outside SetShape; this narrows normal per-info population to one. Multiple active infos/models can each contribute a different shape. Direct event shape selection and radio's independent models require their own donor/lifetime mapping. Renderer omission of a shape is not permission to omit its source/owner contract.

## A04: em10 event selectors resolved to owners

All discovered callers of the six named event setters pass ROOM_ARC_PTR, **not em->subArc**. Therefore these references must not be costed as the selected em11/em12 cache by source name alone. Their existing room-data bytes/registration must be qualified separately; no new room data was extracted.

| Setter and stored roles | All discovered stage callers / source ARC inputs | Consumer |
| --- | --- | --- |
| setEvtMotion (`em10:25738`): m0→0,m1→4,m2→1,m3→5 | r100:1271/1275/1279 →2e/2f/30; r201:170 →20,0,21,0; r300:1489 →33,34,0,0 | R100Cliff body0+SEQ4; R201EventWait0/1 alternatives; R300Gatling body0+SEQ4. |
| setGondolaMotion (`25749`): m0..3→0..3 | r10f:162/165 →2d/2e/2f/32 | R10FGJump states use0→1→2 sequentially; player gondola shake independently borrows slot3. |
| setR11DMotion (`25760`) | r11d:448 →23 | R11DAppear2 body0. |
| setDrill (`25766`) | r212:271/275 →21/22 plus drill object and mode0/1 | R212Drill body0/1 alternatives; object pointer and mode are not FCVs. |
| setGatling (`25778`) | r209:976 →26..29; r320:440/465/1174/1301/1448/1457/1466 →24..27 | R209Gatling body0..3 alternatives; cObjGatling is an independent object owner, not fifth FCV. |
| setUFOCatch (`25807`) | r30b:700 →26/27 | UFOCatch0/1 alternatives. |

Remaining A04 selector families are named, not deferred as “needs runtime”:

1. **Ganado module/type Work tables:** em10SetWaitMotion / em10SetWalkMotion / em10SetDashMotion, damage/weapon slots and em10..em1c `_set.cpp` initializers. The H055 initializer index (1,162 alternatives) is not a simultaneous set. Follow selected Character/Ganado/Wep_type/type/set dispatch, variable bases and separate live instances. Absent FCV records in one selected variant are a variant mismatch to resolve, not resident evidence.
2. **Player/weapon table owners:** cPlayer::motionSet dmMotCk alternatives, pMotTbl, cPlNeck motL/motR, cMot3 mot0/1/2 and registered WeaponMoveFunc/BoatMoveFunc. Main pl00/pl08 inline FCVs do not clear weapon archive/hand reads. Root owns weapon/hand integration; Boss supplies motion-owner edges.
3. **Boss Work phases:** em2b tree/parasite/twin roles; em2c floor/wall/tail custom-damage; em35 upper/beam/damage; em38 type0/1/2/3/4 Work mot arrays; em31 body/tentacle/weak-point/tail objects; em32 phases and divided-player objects; em39 gun/bow/cap/knife/arm/death Work. Review source states against selected variants, not all alternatives together. Prepared island metadata is source input only; island progression remains paused.
4. **Event names:** ExePacket_Mot/Shp/Cam resolves data by event packet/BinTbl separately from model ModTbl. GetBin (`event.cpp:2827`) reuses registered data; missing name can HDReadDebugAlloc and SetBin. Actual event payload ownership/retirement and failure/retry remain named A08 edges, not claimed cache hits.

## A07: borrowing and retirement work list

The full source index covers 261 subArc assignment occurrences across 29 source files; that includes admission/reset assignments and is **not 261 reviewed borrowers**. H055's narrower144 count is retained historically. All boss families are present rather than inspecting only Mendez:

| Family / donor | Located acquire→normal restore functions | Remaining ownership edge |
| --- | --- | --- |
| Common Ganado / actor archive | em10 claw/chainsaw/neck-hang/backhold/bombhold/take-away, gondola, kicks/finishers | Follow dynamic dmgType/arc selection, Ashley/Luis callbacks, interrupts/death, and independent parasite objects. |
| El Gigante / PL_EM archive | CatchHand, Strangle, partnerCatch, DmFall, AtkParasite, stamp/kick/dash/tree escape | H055 strangle body+player+neck pair is all inline in selected package; other callbacks/type variants and owner retirement remain OPEN. |
| Verdugo / PL_EM archive | Kick, DmSide, DmTail, Sit, Escape, Backjump/Backjump2 | Normal subArc2 restoration sites exist; lethal/interrupt path and tail/object references need closure. Selected later-castle body archive is inline; that alone is no lifecycle proof. |
| Mendez / PL_EM(_G) archive | BearHug, Sit, DmFall2F, DmHook, CriticalHit, DashEscape, DmStamp, CatchHit | Bearhug/release have two strict cold records per reviewed pair; upper/beam/damage and all exceptional exits remain OPEN. Face62 comes from player archive. |
| Saddler / PL_EM archive | Escape, macro-generated damage callback, Climb, DmStamp | Macro expansions, attached four tail instances/weak objects, source event termination and borrower stop-before-unbind remain OPEN. |
| U3 / PL_EM archive | CatchHit, Sit, Backjump, Escape, C_AtkHit, P_CatchHit, Divide | Divided-player/catch-object owners, phase change and active AD extra work retirement remain OPEN. |
| Queen / PL_EM archive | AtkHit, CatchHit, DmStamp, Escape, Backjump, Sit | Parent/upper/root ownership and active shell+player+shape demand at death/phase exit remain OPEN. |
| Krauser / dmgType actor archive | Success, Failure, KnifeHit, Knife4Atk, Stamp, Sit, Backjump, LowKickHit, CliffAtk, DmSide | Source dmgType owner generation, arm/cap/weapons, fatal/QTE event paths and donor replacement remain OPEN. |
| Generic thrown weapon / PL_WEP archive | emwep Escape, Backjump, FrontEscape | Motion payload is w->Mot_escape/motBackjump/motFront; these can be caller-supplied donor headers, so PL_WEP's archive name alone is insufficient. Follow setGrenadeThrow argument owners. |
| Del Lago / boat mode | BoatMoveFunc and pl0e/pl0f boat/harpoon/drowning callbacks | Borrowed room/player/boat ARC choices and cancellation/death termination remain OPEN; em2f boss archive alone does not account for player boat motion. |
| Other source families | em21/22/25/29/2a/2d/36/3b/3c, em_sub/emBar/emdoor/emrock, obj13/objTrolley, pl_npc/pl_sub and boat pl0e/pl0f | Explicit remaining dispatch families in private index; none is certified by having been enumerated. |

Changing subArc back does not itself rewrite a retained pMot, stop a face/shape, free independent child work or prove an interrupted path restored defaults. cPlayer::endDamage (`pl_class.cpp:1046`) clears face only. The next A07/A08 pass must follow the actual damage/event finish/interrupt callback and donor unbind together, with source-generation and pointer-base invariants. Existing allocator lease tests prove pin safety for their fixtures, not this entire source lifetime graph.

## Reproduce this checkpoint

Run `motion_consumer_audit.py --repo <repo> --source-ref c7e0358a --census <sealed animation-cache-coverage-work.json> --output <receipt> --details <private details>` and `test_motion_consumer_audit.py` with the same repo/ref/census arguments. No assets are emitted. The public receipt contains hashes/metadata only. Do not reinterpret discovered call counts, initializer counts, archival STRICT/census gates or quiet guest windows as closure of an OPEN edge.
