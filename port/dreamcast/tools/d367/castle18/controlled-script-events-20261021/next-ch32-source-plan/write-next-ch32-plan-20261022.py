from pathlib import Path
import hashlib,json,datetime,re
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan='''# Next original chapter: controlled 3-2 event coverage

Prepared 2026-10-22. SOURCE PLAN ONLY: no guest, build, image or game-source change. Root must review a concrete observer/wrapper and allocate a bounded guest before execution. The user objective is teleporting through the level and triggering original scripts. This does not replace the historical no-warp chapter/release requirements.

The completed controlled001..013 evidence already covers the 3-1 prison death/door, trap switch, r208 crank rise, 3-1 ending movie/results/save, native VMU LOAD and r204 radio return. It does not establish all secondary3-1 waves or ordinary route acceptance. Actual013 remains a separate preserved state97b63602b83d6234a1603dc24a90fa42f2d0702db626ead2e4d4e5e20efafe13. Authentic127/294 and actual009VMU425595 remain immutable.

## Original route and uncovered gates

| Order | Original gate | Evidence required from new coverage |
|---|---|---|
| 3-2 start r204 -> r205 | AEV01 lower native door, destination205 Part0 | Actual205 entry; bypassing this door in a cold205 fixture must be declared. |
| r205 drain | R205Init binds AEV08; ordinary action -> r205_DrainEvent -> selection1 -> r205_DrainEventEnd | Baseline RSF0/1 clear; actual native prompt/Yes; RSF0 then1, areas08/07off,11on/15off,1B callback registration, source68 actor active/held truthfully, event/Stop return and screenshots. RSF0 is early, not completion alone. |
| r205 -> r204 Part1 | Native upper AEV00, unlocked; source exit callback selects BGM204 | Actual204 entry with original prev205/Part1 handoff. R204Init naturally starts firstcut/chase, so record its state instead of claiming completion at the door alone. |
| r204 Part1 -> r209 | Original chandelier/chase/barred/switch and upper AEV04 | Source event transitions and actual209 load; teleported traversal and any intentionally bypassed mechanism named separately. |
| r209 -> r20a | Leader/gatling, source salon-key acquisition/use at AEV02, second battle, four-panel bridge puzzle; original AEV00 exit | Record individual original callbacks/key/bridge and actual20a. Do not preset their completion flags or grant the key and call its acquisition PASS. Separate bounded units if source movie/battle waits exceed the cap. |
| r20a -> r20b | Original AEV06 path | Actual20b entry. Ashley shoulder-carry is a later conditional branch and not inferred as required for solo chapter3-2; original room door/padlock conditions remain actual gates. |
| r20b 3-2 ending | Actual AEV02 -> R20bEventS00 -> r20bs00 -> SceSetChapterEnd(CHAPTER_3_2) | Original movie progress/EOF, chapter-end UI and save/write/load are separate stages. Early RSF0/chapter increment alone is insufficient. |

The next chapter after that is3-3: r20b -> r20c -> r20f -> r206, ending at r206_die_event/SceSetChapterEnd(CHAPTER_3_3). Chapter3-4 ends at r206_takeover_event/SceSetChapterEnd(CHAPTER_3_4). Do not divert to already finished3-1 checks.

## Smallest next consolidated unit:014

The exact draft is controlled-ch32-drain014-warp-DRAFT.txt. It chooses a NEW cold active DBG_WARP lineage in205, jp0/chapter7, at the actual drain lever center46118.5419921875,996.8269653320312,48787.291015625, facing0, with49152B squeeze and read-only dump/alivelog. It has no RSF/scenario/status/dead/inventory/kill/god/atfunc directives and no saved-state seed. It is a controlled chapter/placement setup, not a continuation of013 or proof of prior chapter completion. The old historical entry28384,-1999,19201 lies inside automatic enemy AEV03 and is deliberately excluded to avoid overlapping that cutscene with the drain.

The existing native UI method is retained: exact owned-window ordinary A starts AEV08 after actualroom205/freeplay/position/front/action readiness. CheckFlag1 uses the collision-clipped front point(0,250,550) transformed by the actual actor matrix; no facing-angle bit2 is set. The center is only geometric preparation, so actual callback/prompt is observed before accepting invocation. Once the original selection prompt is live and coherent, choose actualYes (selection pending/current0; if initiallyNo, Left unless attribute00800000 calls forUp), release between pulses, recheck immediately, then ordinaryA. Preserve unknown message states rather than guessing or injecting a selection byte. No mandatory bell/aim/perfect-hit/health-drop stop policy is present.

Primary acceptance is original drain/end. If it finishes with time remaining, prepare an EXISTING engine-native goto to upperDoor00(center7314.5767,9996.8262,42846.0127; source quad/actual floor/front checked) and ordinary native A after actual arrival; goto defers while an event owns the player. This follow-on must be pinned in the reviewed final fixture/wrapper, not improvised after launch. If the bounded unit ends mid-drain or before204, preserve its real state and report partial, then request a concrete continuation. Do not close early just because one intermediate flag changed. Initial two Novistadors plus cap4 can affect68 admission; record real active/held reason rather than asserting all enemies spawned.

The draft currently contains NO input/goto schedule: the source-gated host observer and any optional final goto are the next small implementation step, not a launchable approved wrapper. No root guest allocation is requested by this plan alone. This avoids reusing the013 inactive-observer state as though changing warp.txt could rearm it: the saved rig is loaded/inactive and has no restore-rearm hook. A fresh active cold fixture is necessary for this declared teleport unit;013 is preserved untouched.

## Exact available programme and assets

Runtime source12a841d7cfe2c747266b0c330555557e651a4af0; ELF4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f; rawprogramme78fb06976cc394ec6e4cb7861046c24a15f82ddf7bcb2fcbfd452d3fcbf72e33; masterimageb67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6. Existing ccd160 binding proves exact ELF/PT_LOAD/raw/master/all18overlays. The a692 nomination is its KOS-scrambled derivative, not the consumed raw payload.

Fresh capability receipt verifies all8 route ARCs byte-for-byte against the actual master manifest, actual extracted50 selected native registries/movies/overlays/ESLs, and5 retained compile command sites for204/205/209/20a/20b. Current6room/rig source diffs against frozen12a are empty. Resolved CH31=1/CH32=1/CH3movies=1/DBG_WARP=1/ALIVE_CAP_NOVIS=1/cap4/VMU_SAVE=1; WARP_JUMP=0/KILL_PHASE=0. Native goto/ordinary action exists without those two optional flags. ROUTE_CH32 links required em2d/em25/em3c overlays and em19; em22/em18 already linked. No programme or asset rebuild is needed for this first205 drain unit. This is stored source/build-byte capability, not a fresh live behavior or full historical dependency-closure rebuild.

Known camouflage CAST failure in205 and earlier residency/cast failures stay open and separate from script execution. All events, savedata, screenshots and programme/assets keep exact identities; Flycast source coverage does not imply release or physical Dreamcast acceptance.

## Resource and review boundary

Source-only additions <=2MiB including C and Git copies inside standing global64MiB sourcepeer. No shared source claim, build slot, image copy, guest or binary retention change. Future reviewed014 must use V5exact7aa4113d44b5bab5b1010649a432ed1d50e34aaf4de7fb4899aaf692055b0ba0;41raw/39normalclose/47.5absolute/60MiBcapture/global16/castle2, fresh start20,342,374,400B and runtime19,394,461,696B plus current parent reservations if changed. Retain exact PID/path/creation handle through verifiedexit. Ordinary injuries/death remain real outcomes. No production recipes/releases/SD/third-party actions.
'''
p=L/'NEXT-CH32-ORIGINAL-EVENT-PLAN-20261022.md';assert not p.exists();p.write_text(plan,encoding='utf-8')
header='CURRENT: NEXT CHAPTER3-2 SOURCE PREPARATION ACTIVE. Original route204->205->204Part1->209->20a->20b is confirmed; first uncovered gate is original205 drain. Frozen12a supports it: actual8ARCs/50selected assets and5retained compile sites checked. Draft014 cold lever placement has no outcome flags/inputs; final source-gated observer/wrapper and root allocation are still required. No guest/build/image/shared-source change. Actual013 state97b63602,auth127/294,009VMU preserved.\n\n'
for n in ['STATUS.md','HANDBACK.md','INBOX.md']:
 p=L/n;s=p.read_text(encoding='utf-8');p.write_text(header+s,encoding='utf-8')
p=L/'STATUS.md';s=p.read_text(encoding='utf-8')
for key,value in [('Doing now','Source-only next chapter3-2 plan and draft014 lever fixture; independent perf21_scene source review. No active PID, shared game-source claim, build or image writer.'),('Next','Implement minimal source-gated original205 drain observer/wrapper after root reviews plan; no guest until concrete root allocation. Preserve real013 freeplay,auth127/294 and actual009 VMU.'),('Blocked','No user input required. No guest allocated; draft is source planning, not launch approval.')]:s=re.sub(r'(?m)^'+key+r':.*$',key+': '+value,s,count=1)
p.write_text(s,encoding='utf-8')
print('plan',sha(L/'NEXT-CH32-ORIGINAL-EVENT-PLAN-20261022.md'))
