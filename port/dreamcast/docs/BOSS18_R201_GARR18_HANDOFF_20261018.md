# Boss18 r201 source handoff to garr18, 2026-10-18

Garr18 owns the runtime fixes under boss INBOX I007: use the existing native path for the separate core, Leon's alternate source appearance, and props41/43. Boss18 changes data/specs/docs only. Nothing in this handoff approves source fallback or changes gameplay, a draw gate, capacity or material tolerance. Future Castle boss arms use LEON_SKIN_SLOTS=2; the observations below belong to old b18abrT/current383 and must be retested on the new exact program.

## Reproduce the source opening and keep evidence separate

Use C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/fixtures/r201-garrador-whole-full.json. Retarget boot plus every linked overlay to the intended current build. The disclosed initial31300,-2000,-42000 is inside original AEV10; ordinary forward240/90 allows the original source callback/ESL56 to create the38part type10 Garrador atHP4000. There are no HP/damage/kill/god/flag/atfunc/state writes. Initial positioning is diagnostic, not natural route traversal. Earlier AEV0f28700 positions stopx29345 in the chained camera and are not a fight opener.

Actual cx-r201-garrador-wholefull-d and -e both reach bodyalive/moving/attacking/native549. The e repeat has116 read-only samples verifying bodyid1b/type10/38parts/HP4000 and live pCore0x8cac45f0 id16/type4/14parts. That disproves a failed core constructor in this exact run; it does not qualify native auxiliary drawing. Original logs and watcher proof stay in boss18-20261018, especially garrador-core-readonly-watch.json and h-b18garrador/scenarios/cx-r201-garrador-wholefull-e/capture/run-output.txt.

## Core: existing full data, missing source-owner participation

- src/em10/em10.cpp:3004 creates SetObj16(BIN0x227,TPL0x228,target/body=em,part0x24,type4), then assigns11 original motion slots from0x229/0x22A.
- src/game/obj16.cpp:90 creates ObjMgr.createBack(0x16), checks original modelInit, stores original target/body/partsNo and source lifetime. obj16MatCalc at897 follows bodypart36, applies original local placement/scale and current motion, then calculates world parts. Source destruction/no-suspend remains in em10.cpp:818/907.
- src/game/trans.cpp:sourceActorBegin (EmMgr loop around914), sourceActorPrepare at944 and ready verification at979 enumerate EmMgr only. Its separate ObjMgr source traversal around1286 calls objTrans at original order but does not enroll an auxiliary in that actor ledger.
- port/dreamcast/game/platform/include/source_actor_owner_hooks.inc:3-12 requires current ready ledger membership and returns0 for an unrelated ObjMgr model. Registering the data alone cannot make this object a native transaction participant.

The minimal required engine-owner boundary is source-certified enrollment and lifetime for this original auxiliary through the existing native path, preserving original ObjMgr traversal/preparation/OT ordering, serial/generation, attachment/current matrices, visibility/material state and retirement. A model-id allowlist or bypass of ledger/registry proofs is not sufficient. The original target id16 collides numerically with ordinary classes, so exact source BIN/TPL and14part owner facts matter. No implementation is made here.

Ready data is H016: full14part491tri core, independent original geometry/weights/materialUV/allparents-rest proof, native512KiB3poses/GXVERIFY, and complete room registry spec boss18-r201-whole-full.json. Full room arena241952/425984B, package SHA256 e8b494ffa01b4f39fff55b13512f1a5e44b54a8a2903911191875840f03e4123; all existing ordinary descriptors/masks/facts/native bytes preserved plus core. Eight actual target controls for this package pass. Data set boss18-garrador-20261018 seal8f366319a82277fab953ae18eb148b3afaa85c91f4c7b31e206cc291b9ea7de1 is mirrored.

## Leon: original death appearance, distinct from a skin-slot allocation failure

The ordinary motion changes into source death at tick582 in both d/e logs. The e log has CROWDF t581 hp160/1440 followed by t582 hp0/1440. Three ATX_DROP records retire role masks08/10/80 (face/head/hair); ATX_INFO f583 idx6 reports why2 detail100b for data0x8c687840/TPL0x8c674aa0. actor_lifetime.inc:268-285 defines why2 as no asset template and detail as family<<12|BIN;100b is Leon family1 BIN0xB. LEONGC f582 is why4 no-plan/bind23, then sticky-source why2; acquisition remains0/0/0. At f631,7info native0/declined48 is a cumulative census after this event, not the first failure.

The source chain is explicit:
1. src/em10/em10.cpp:27069 em10PlHeadLost is the regional source head-loss death handler. At27084 it calls pPL->setHead(0). Source damaging/critical branches call this routine; ordinary steering lets the enemy cause the event. No forced death was applied.
2. src/game/pl_leon.cpp:290-310 cPlLeon::setHead(0) deletes pShape/pHair/pEye, then appends original pGS->pPlayer BIN0xB/TPL7. This is9-3+1=7 source infos on the unchanged119part body.
3. em10.cpp:27107 creates a separate flying-head object from original pG->pPlayer BIN0xC/TPL7 with SetObj01(...flags0x11). src/game/obj01.cpp:330 creates ObjMgr id1 and keeps the original movement/effects/lifetime. That object needs its own proved presentation; keeping the old attached head would change the visible source outcome.

Original PS2 BIN0xB is the37triangle neck section, weighted only to original joint3. It carries4 PS2 bone records; the GC section lists118parts because it is attached to the unchanged119part owner. BIN0xC is1727tri with1originalpart/joint0. Both original BINB/BINC bytes are identical between pl00 and pl08. They are not a generic seven-info variant or a lowered skeleton.

Current owner_pl08_bind in coarse_actor_owner_pl08.inc:33-35 requires119bodyparts plus exactly nine registered infos; actor_material_records_pl08_roles.inc has the ordinary nine roles and no BINB/TPL7 role. A different source shape needs exact registered section facts and an alternate native plan retaining all seven live source infos and current hands/neck placement. Registering a guessed seven-info count or silently dropping the new section is not acceptable. The flying head is also a separate ObjMgr lifetime, as above.

LEON_SKIN_SLOTS=2 in native_actor_fast.cpp:1364-1369 raises registered skin capacity80 to112. It is required for the new test recipe, but does not supply the missing BINB asset template or change the exact-nine source plan. This is a source finding; no new slots2 runtime result is claimed. The new program still needs the source death transition gate. The old no-plan failure is not evidence of SKINACQ exhaustion.

Original cached pl00/pl08 PS2/GC archives were reused and independently verified byte-for-byte against the original discs. They and ORIGINAL_APPEARANCE_AUDIT.json are in /root/re4data/private/boss18-r201-appearance-20261018, immediate C mirror:5files/6656710B, SHA256SUMS9707c1e61ab9456c738ab3735853bf30b8f0c9c7d368212b60b99de7378e2002. No new native Leon data is claimed. Asset intake includes geometry/material/bone counts and exact hashes for garr18, not a runtime implementation.

## Props and required final proof

src/game/em.cpp:127/133 classifies id41 as cEmDoor and id43 as cEmBox. The e NOT-DRAWN report has21alive samples: id41 max2,8in-view; id43 max10,2in-view. Existing source world/object draws are not an actor census proof. These remain FAIL for garr18 to reconcile against actual native world/object presentation; no checker exception is added here.

After runtime fixes, qualify on the intended current chapter3-1 program with slots2 and every Test18 addition: original AEV10 source fight, body+core actual native draws, ordinary source attack/death and new seven-info/flying-head appearance, no unlisted GC/LEON/TEX/NOT-DRAWN, complete KOS48KiB/VRAM/residency, and normal route/door/chapter-end save under Castle ownership. Model rendering fixes must keep STRICT/decisions and original collision/AI/events/camera. No full room/route, look, performance or console acceptance is implied by this source handoff.
