# Advance controlled scripted-event coverage

Root reports controlled001 Flycast PASS: original goto60/trg90/damage100, HP1 to0 at101; by source430 RSF0/1, Smd53 +2600, AEV0A disabled, event released/Stop0; bounded36s exit with V4 supervisor PASS. This is supplied fresh execution evidence from owner/root, not execution by this read-only lane. Preserve authentic127/294; do not replay001 without a defect.

## Next bounded unit: switch, trap and reset wave

Prefer the smallest existing-rig cold fixture which carries already-observed boss-dead/open-door state as explicitly declared prerequisites and leaves RSF5 clear. Carrying those flags is setup, not a second boss/door success. Existing active saved warp state does not reload new text merely because warp.txt changes; owner chooses a cold fixture or already-supported continuation, not a new rearm mechanism.

| Original stage | Existing action | Observable result and limit |
| --- | --- | --- |
| cEmSwitch action | Initial pos/goto at measured switch geometry, facing lever; ordinary `act ... a ...` | Source action prompt0x14 requires lever rest state, within Ck_dis, height within1000 of hero+1000, facing within45 degrees, and for type!=1 lever-front within90 degrees. Proximity alone does not pull it. Observe switch motion/state. |
| r201_checkSwitch to r201_disarmTrap | Original switch ckOpen; no outcome writes | Original watcher queues camera/event; after60 source ticks setSwitchEnv sets RSF5, animates barred open and disables AEV0/1/3/28/5. Observe barred state/motion, trap areas/effects and source EventEnd. RSF5 alone is early. |
| Reset callback0C | After disarmTrap end and prerequisite RSF0, goto measured AEV0C or call existing registered atfunc0C with explicit spatial-trigger bypass label | Original callback binds lists57/5B/5C; first goes to areaD until arrival, two to18 modeB, first after30 to17 mode1. Observe callback/actor identities and actual order/arrival, not just a count of live actors. |
| Secondary reset | goto measured area12 or16 | Original watcher binds58/59/5A, activates5A, after60 orders58 to13 then15 later59 to14; after150 and bomb-fire completion orders5A to15. Observe those identities/orders. Callback start alone is not complete wave coverage. |
| Exit | goto actual original door trigger and existing ordinary act, Ashley relocation if required | Observe actual room transition/load/next room actors; crossing coordinates alone cannot prove door logic or loaded destination. Do not use disabled WARP_JUMP. |

Source: r201.cpp lines848-945,1052-1113; emswitch.cpp lines427-481. No new combat controller or mock-test cycle required for unchanged harness.

## Later r208/r204 boundaries

| Stage | Minimum existing mechanism | Required original result |
| --- | --- | --- |
| r208 wall crank rises | Original two crank flags or existing DebugTrg0 shortcut; JP0 and RSF5 clear when testing rise | R208Main sets RSF5 then original crank_set animates Smd4E/4F to4984/4000 and ends camera event. DebugTrg bypasses two-crank prerequisites and must be labelled. JP1 presets RSF5/6 and cannot prove rise/bridge. |
| r208 bridge | Registered area2 callback opens selection; select original turn option, then repeated action presses using existing acts | operateCrank checks repeated Key.trg0x00080000 (not merely held action), accelerates rotation until Smd21 angle>=1; original brige1_down sets RSF6 early, animates angle to2.0943952, updates collision, disables AEV3 and releases event. Observe final angle/collision/event release. |
| r208 Ashley/sniping platforms | Original E/16 r208_snipe and source partner/footing sequence | Need actual partner placement/AI, platform Smd57/58 rise from2900 to5400, RSF10/11 and collision rebuild; carried flags or teleported Ashley do not establish those callbacks. Savecontinue RSF12 is separate. |
| r204 chapter3-1 end | Original registered area2 r204_EventExec with RSF0 clear; teleport or atfunc invokes it | Source event r204s00/movie, Ashley removal/status cleanup, SceSetChapterEnd(CHAPTER_3_1,-1), then typewriter via openTerm. RSF0 is set BEFORE movie and RSF7 BEFORE terminal UI, so flags alone cannot prove completion. |
| Save | Original terminal UI/write then separate reload | Observe actual save success and loaded room/chapter/flags. Typewriter open is not save/reload acceptance. |

## Evidence and clock limits

Use measured current area/door coordinates; do not infer floor from AEV center. Existing goto/trg use room_frames while act uses pad_frames. act_clock source avoids wall-stall cuts; source event cuts remain, and ev is needed only for intended event/prompt input. Existing capacities are32 acts,8 gotos,8 room entries; only one trg/atfunc/kill phase in this frozen configuration. Preserve fixture bytes/hash and label every supplied flag/inventory state.

Capture before/during/after graphics and key animation frames, exact program/image/fixture identities, event/actor traces, and crash/error/exit evidence. Screenshots assess only visible frames; source traces do not assess texture correctness, sound quality or animation smoothness. Mark audio unassessed unless actually captured/listened to. A clean bounded exit establishes only that window, not full route/release/hardware acceptance. Keep raw41/V4absolute47.5/60MiB and current resource floors unchanged.

## Exact inspected source identities

Frozen runtime12a841d7c; git diff empty for listed files. SHA256:

- r201.cpp:13265eb6c38e8b248c2109637ee263f4df4aa2cd34813d008404a35c16b0e67a
- emswitch.cpp:16de9ffd38f186341c82ccaa6cb60446a8fbcb3827020a05b51444a588c95255
- r208.cpp:33222970de982fc6366afb2c4455c5c957497ae845f19b257c2b4432c9aae52e
- r204.cpp:c07923996fed358183efca25cb52f13c6dce5f7e0b32326506030d01370efb4b
- dbgwarp_bridge.cpp:69d47a81a6a43621639612225a45caf4a5e18d6846166a3f4ff019cc5dc0535f
