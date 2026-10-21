# Original J chapter 3-1 finish and resume contract

This is preparation, not completed route acceptance. Continue the original game on the qualified J program and image. No new build, data patch, state retarget or game-memory write is authorized by this document.

## Exact current checkpoint

The last actual guest is J202, with Leon at 368/1200 and Ashley at 600/600. The original Garrador death callback passed: room-save bits 0 and 1 were set at source frame 54426, followed by 30 stable freeplay ticks. The saved state is at frame 54465 with room flags `0xec400000` and SHA256 `7a98a65054ae20ee0a0c54e5db230e4b9066bf53aaa06851b482700043d589ce`. The original HP-zero corpse remains present. The handgun is empty, with 15 reserve rounds; Ashley is still in the safe western Wait corner. Next use normal reload and Follow, then the original stairs/exit and reset waves.

Historical J198 was refused before guest creation and advanced nothing. J199 subsequently resumed the exact last actual J197 state. J200/J201 used normal handgun shots; the J201 controller timeout label preceded its next enemy-HP read and is stale. Its authoritative saved state proves HP zero but no death callback yet; J202 supplies that separate callback acceptance. Raw logs and screenshots remain intact.

The unchanged guest preflight requires 17,314,086,912 bytes free on C:. The runtime floor is 17,246,978,048 bytes, with a bounded 128 MiB output allowance. Check Windows and WSL processes, serialized guest ownership and live free space immediately before launch. A refusal does not authorize reducing the floor or deleting protected files.

The immutable runtime is `12a841d7c`, ELF SHA256 `4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f`, and image SHA256 `87ba0ee4f54b289a1c227328e58577e57f3d5d72df9c22f4e4de33c1fe6e016b`. Use the existing J image, 23 program payloads and original VMU/Continue lineage. The optional host centre-aim controller is syntax-checked only and has no live qualification.

## Garrador death and original dungeon exit

`src/st2/r201.cpp`, `r201_appearClawMan`, waits for the original enemy wrapper to become inactive before setting room-save bit 0. HP zero or damage routine 2 alone is not death acceptance. Require bit 0, stable freeplay phase 3/0, Stop zero and SSLoop zero, together with native death/corpse evidence. Preserve the original lever bit 5.

The original callback opens the battle area and controls its camera. `r201_setBattleArea_sub(1)` sets room-save bit 1 and the corresponding global door flag. The rising door disables its collision at height 1600, then reaches 2600. Require actual ordinary stair traversal after this callback. Do not write flags or bypass collision. J193's failed escape overlapped the original battle-door event and its Stop mask; it is not an isolated physics diagnosis.

The source SAT route prepared in `J194-postboss-dungeon-exit-source-SAT-route.json` is a navigation hint. It starts at (23750,-2000,-46000), crosses west to (16750,-2000,-45500), then climbs toward (16000,2000,-37750). The game must actually open the gate first.

After the boss and lever, original area 0xC at approximately (16188,1969.78,-30606) arms the reset wave. Account for all six source actors: 0x57, 0x5B, 0x5C initially, then 0x58, 0x59 and 0x5A in the side watcher. Cap-four holding, deferred Goto, releases and original clear callbacks remain explicit gates. Four visible enemies do not prove wave completion.

## Chapter end and actual VMU save

The remaining original room order is r201 -> r208 -> r204, following the earlier r200 -> r202 -> r207 -> r203 route. Do not warp to the chapter end.

In `src/st2/r204.cpp:1037`, original area 2 runs `r204_EventExec` once. It sets room-save bit 0 and scenario bit 0x40000, then plays movie 0x20400 or the original r204s00 event. Its normal callback destroys the partner actor, clears the corresponding status bit, calls `SceSetChapterEnd(CHAPTER_3_1,-1)`, and opens terminal 0xE. Ashley's absence after this source callback is expected; do not force her present or report an absent pointer as a native-renderer decline.

`include/sce.h` defines CHAPTER_3_1 as 6. In `src/game/sce_com.cpp:900`, `SceSetChapterEnd` performs the original fade, pause and chapter-end task. `SceChapterEnd` at line 765 sets the stored chapter to 7 and swaps the room out with its original 0x20000 margin while loading the chapter display. It presents save message 0x80, runs `GameSaveSave(...,2)`, restores the room, and calls `CardSave(0,10)` only when the original selection is Yes (selection 1). With door -1, it restores the normal room and BGM without a forced warp.

Acceptance requires the actual end presentation, normal Yes/CardSave interaction, verified VMU byte change and successful original CardLoad/reload. Chapter 7 or a scenario flag alone is not save acceptance. Do not inspect actor or motion-binding pointers while Stop, SSLoop or held-world room swapping makes them invalid.

## Evidence

Retain PNGs for actual damage, death, door opening/traversal, wave transitions, room entries, movie/menu return and save/reload. Each sidecar records run, immutable ELF, room, sampled source-frame interval, health and the action/result. Read the saved state after capture; asynchronous framebuffer sampling spans several source frames and is not an exact frozen tick.

The J195-J198 receipt preserves the bell-observer correction: J195 proves a bell hit, not AI consumption; J196 independently records the original AI destination matching the bell for five source ticks; J197 returns to the upper stairs. No boss kill, exit, wave clear, end save, whole-drive quiet, hardware performance or full-residency claim is made.