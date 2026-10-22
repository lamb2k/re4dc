# Controlled r201 event coverage: source review

Current objective is teleporting through the level and triggering scripted events. Combat automation/readiness reviews are superseded. This review does not execute a guest. Immutable127 and authentic294 are preserved; the proposed cold fixture starts a separate controlled-coverage lineage.

## Reviewed plan and source pins

Byte-read fixture: C:\Game Dev\Emulators\codex-lanes\castle18\controlled-event001-warp.txt, SHA256 8e753b50382054b6917133dfe2ed7f7efb28f8799cc896f57cc500111e85fae6. It contains cold room0x201, jp0/chapter6, Status_flg[3] Ashley 0x04000000 declared as SETUP; initial position 31369.3315,-2000,-41951.6318 inside its measured AEV10; angle PI/2; goto60 to 19000,-2000,-45000 with angle PI/2 and Ashley relocation; original DebugTrg0 at90 room201; existing kill model0x1b at100 kind1, killpart37; inherited squeeze49152/0, alivelog30 and dump. Parser handling matches these bytes. No JP2, RSF0, atfunc, inventory, god or direct death/door flag setup. No concrete fixture/parser defect identified.

Read-only source tree /root/probe/codex-castle18, frozen runtime 12a841d7c. git diff against that commit was empty for both files below on this review:

| File | SHA256 |
| --- | --- |
| src/st2/r201.cpp | 13265eb6c38e8b248c2109637ee263f4df4aa2cd34813d008404a35c16b0e67a |
| port/dreamcast/game/dbgwarp_bridge.cpp | 69d47a81a6a43621639612225a45caf4a5e18d6846166a3f4ff019cc5dc0535f |

Frozen c21jmW ELF SHA256 4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f; image/data SHA256 b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6. Existing DBG_WARP1/WARP_JUMP0/WARP_KILL_PHASE0 controls remain unchanged.

## Event matrix for this bounded fixture

| Stage | Original source / prerequisite | Intervention | Required observation; coverage limit |
| --- | --- | --- | --- |
| Room setup | R201Init lines130-240; RSF0 clear creates source-list0x56 and registers AEV10 appearance | Cold explicit room and declared Ashley/chapter setup | Log actual room/entry/setup and boss identity; do not count supplied flags as tested outcomes. |
| Appearance | r201_appearClawMan lines978-1007 binds list0x56, activates it, enables29, registers battle-close11, sleeps17 then persists in isActive waiter | Initial position inside measured AEV10 | Observe callback/wake and live Garrador type0xA/source-list0x56. Placement alone is not successful trigger coverage. |
| Relocation | dbgwarp goto_poll uses original setPos/setAng outside event state | goto60 to lower hall | Observe actual goto execution. Its fixed frame can be delayed by a source event. Moving after appearance does not cancel the persistent cEmWrap waiter. |
| Controlled defeat setup | Original appearance waiter reads DebugTrg0 and sets HP1 (not dead); dbgwarp kill_poll queues dmg.set(0,10,kind1,...,part), not direct HP0/em_dead | trg0 at>=90, kill100 kind1/part37 | Log DebugTrg firing, selected model address/source-list/type, HP1 and queued source damage. kill selects model id, not source-list; verify it selected the Garrador. killpart37 falls back if no matching hitbox; log actual part if available. This is controlled damage/death coverage, not a shot or natural combat. |
| Original death gate | Appearance waiter exits only when original em.isActive()!=1; then sets RSF0 | No outcome flag writes | Observe death/inactive then RSF0; HP<=0 alone is earlier than actor inactivity. If source death is not processed, report incomplete rather than forcing flags. |
| Door opening | r201_setBattleArea lines764-840, called from original waiter if Room_flg0 bit40000000 clear | None | Observe EventStart, opening animation, RSF1, Room_flg0/door_flags51CC bit40000000. These flags alone are early and do not prove full animation/collision completion. |
| Collision/full opening | Opening helper sets RSF1/door flag FIRST; waits Smd53.pos.y-baseline>=1600 then disables AEV0A. Animation finishes at baseline+2600 | Read-only sampling/screenshots | For full door acceptance observe Smd53 baseline/final +2600, AEV0A flag bit0 cleared, and original EventEnd. If those cannot be sampled, label evidence early-unlock only rather than full gate passage. |
| Wave readiness | Original appearance end registers reset area0C only if RSF5 switch already complete | None in this first fixture | No wave coverage claimed unless switch/callback prerequisites and wave actors are actually observed. |

No source-method blocker identified in this bounded plan. It exercises the original persistent death-to-door callback after explicitly declared controlled damage setup. It does not establish switch action, inventory-key use, reset-wave completion, room exit, chapter end or save acceptance.

## Later route coverage boundaries

Original r201 key-use inventory completion (itemC3), switch ckOpen/disarmTrap leading RSF5, reset area0C/wave source-lists57/5B/5C and secondary58/59/5A each need their own actual callbacks/postconditions. Teleport proximity alone cannot substitute for them. Atfunc invokes an original registered callback while bypassing its spatial trigger, and must be labelled accordingly; do not duplicate the already-running appearance waiter. JP2 presets RSF0/5/4 and entrance-find and cannot prove the boss-death gate.

For subsequent room/chapter coverage, original r204_EventExec calls SceSetChapterEnd(CHAPTER_3_1,-1), then r204_openTerm sets RSF7/opens the typewriter. Chapter boundary, typewriter UI, save write and reload are separate observations. Do not infer the full chain from current r201 placement/unlock.

Resource/identity limits and v4 supervisor remain in force; no new approval request or qualification cycle is introduced by this review. Source review is not Flycast execution, release qualification or physical Dreamcast acceptance.
