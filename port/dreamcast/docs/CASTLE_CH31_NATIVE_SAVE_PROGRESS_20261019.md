# Castle chapter 3-1 native-save progress, 2026-10-19

This is incomplete Flycast progression evidence. The chapter is not ready.

The c18oimW program (ELF `746a2a5feb7cf6293ea31c2738c815a3f6ce305a29c8af82b482ca8758b2136e`) loads the native chapter-6 start save through the original title/card flow. Its VMU is `b1e234c8527c1d76e5a59f970dfdd66a1e28ba2a0ec0385928a41a767c06f4eb`. The preceding chapter was not played; its end event created this start save with disclosed inventory/Ashley preconditions. Subsequent runs continue exact production snapshots of disc `60aa53ee11ce24e79630447aa302899bac322c5a8b0eb98a2b35097b3e8684c1`. There are no room/position/flag/inventory/god/kill directives after native load. All inputs are ordinary controller messages to the verified owned emulator window; snapshots and guest memory are never edited.

The original r200 door leads to r202. The crank and cannon run through their original A callbacks. Post-cannon frame 7964 has source Rsf `e3000000`, no live em11, an empty held queue, and the original Merchant entry 0x30 created as em18/type7. Leon has 1440 health and Ashley 600. This is the original cannon purge, not deletion added by the cap implementation.

The normal Follow command reunites Ashley. Original Merchant Trade opens the shop; ordinary B returns to gameplay, restores one archive/eight assets/eighteen infos without exhaustion, and preserves 1440/600 health. Temporary shop views are not interpreted as gameplay health or actor pointers.

The original door changes r202 to r207 at frame 12527. Its radio finishes naturally. The source return restores two archives, all 32 assets and 32 infos. Read-only exact-ELF state inspection proves all seven Ashley infos retain the current archive owner revision, material templates and adopted roles with pending=0. This confirms the earlier default-off partner-capacity fix on the ordinary-door route. A normal Wait command leaves Ashley safely at the entrance while Leon reaches the lower sword prompt. The pickup, puzzle, waves and onward door remain open.

Evidence is under `C:/Flycast-Evidence/re4-dreamcast/castle18-20261018`: `H023-native-cannon-shop-door207-progress-proof-20261019.json`, the two `I009-native-r202-*-proof-20261019.json` source-state proofs, and `r207-I009-natural-door-radio-Ashley-certificates-20261019.json`. Runs j/k/m/o/r/s/t/u/v are individually bounded below 60 seconds and bind the exact program, disc and state hashes in H023. Earlier controller aborts p/q and no-pickup attempt v are retained and do not count as requested-action coverage.

The immutable route disc still uses V8 data and has real late texture uploads/evictions. V9/V10 inputs qualify separate room gates and must not retarget these snapshots. A fresh integrated data/controls run through the actual chapter-end save is still required. The r207 source-role texture preparation gap and Verdugo order-type gap remain coordinator dependencies. AUX_OBJ_NATIVE stays 0; no renderer admission or source scripting was changed here.

Worker A's first six captures were unsqueezed (`held=0 requested=0`), so their earlier 48 KiB claims are withdrawn; texture/draw observations remain separately labelled. Use `tools/d367/castle18/verify_kos_reserve.py` to require complete exact reserve receipts. Actual qualified main r201n, r101q, r207j warm and native-route warm receipts are sealed separately. Native progression alone is not memory/residency acceptance.


## H024: original sword puzzle and visible Ashley

On the same frozen c18oimW disc, ordinary A picks up the Platinum Sword at frame15992 and the Gold Sword at16728. Ordinary inventory Use installs Platinum upstairs at16819. After the normal stairs return, Use Gold downstairs runs the original wall-opening event and returns to gameplay at18016, with source Rsf `c9300000`. Runs w/x/y/z/aa/ab/ac/ad are each below60seconds. Their actual state, controller and run-result hashes are in `H024-native-sword-puzzle-and-Ashley-firstsight-proof-20261019.json` under the Castle evidence root.

The ordinary upper-floor enemy event has four loaded positive-HP monks (D8/D9/DA/D3) and two deferred sends (D4/D5). This is an observed admission/queue point, not a full release/wave proof. Symbol-bound inspection confirms `aliveCapN` is a scalar count and Held/Sent are64-byte arrays; only the firstN entries are active. Stale bytes pastN do not represent waiting actors. The post-cannon queue remains empty atN0; the newer symbol-bound proof refines the earlier scalar-only Held/Sent labels without changing that result.

Immediately after the wall event, all seven Ashley assets/templates are current, with five infos already adopted. Returning to Ashley through the normal aisle produces all seven adopted infos with current archive revision928 and pending0. Leon and Ashley remain healthy at1440/600. This is lazy first-visible adoption, not a renderer workaround. The next step is ordinary Follow and the upstairs door to r203. The immutable V8 data's residency failures and the remaining chapter/wave/end-save gates remain open. Source has since merged upstream7adb8d22 with its new options off; these snapshots retain the original746program and are not new-source acceptance.

## Original combat, item use and Continue recovery (H025, 2026-10-19)

The no-warp chapter 3-1 route remains incomplete. These are bounded normal-input observations on the unchanged c18oimW ELF746a2a5f and disc60aa53ee; they do not qualify the newer merged source or clear the room.

Owned-window knife-ready and attack inputs reduce the original monks' health. The original inventory First Aid Spray is then selected and used normally: Leon's health rises from68 to1440, the item is consumed, and gameplay resumes. No health, inventory, ammunition, flags or saved-state bytes are written by the controller.

Subsequent normal combat kills source entry DA. The source death bit is set, both original kill counters become1, and the cap-held queue releases another original source send: held count2 becomes1, retaining D3. This establishes one actual death and release rather than inferring a kill from an actor disappearing. It does not establish the complete wave or final room-clear path. Later combat kills Leon while Ashley remains600; this failed attempt is retained.

Normal accept input then invokes the original Continue path. The game itself restores its r207 checkpoint at frame13242, Leon1440/Ashley600, and resets both kill counters and DA's death bit to0. The controller does not reset the emulator or select an older external snapshot. The next ordinary Wait/stairs retry reaches the upper room, but Ashley takes damage600 to360 while waiting near the entrance; waiting there is not a qualified safe escort strategy.

Private evidence is under castle18-20261018/h-c18oimW-r200l/scenarios: resevtam records original item use, resevtap records the source death bits and queue release, resevtaq records Leon's death, and resevtar records the normal Continue recovery. Every emulator capture is shorter than60 seconds and ownership is checked before window input. The controller has only process read/query rights.

A missing warm-disc hardlink caused one pre-guest staging failure, resevtao. It is explicitly invalid as a runtime gate. Existing identical disc bytes were still present through78 other hardlinks. The missing link was restored only after its complete SHA256 matched60aa53ee11ce24e79630447aa302899bac322c5a8b0eb98a2b35097b3e8684c1; no image, program, fixture or snapshot was regenerated or retargeted. The exact repair journal is retained. The cause of that missing link is unassigned.

Worker source/data integration is separate from this immutable route. Source6ee01aa1 includes upstream7adb8d22 and the original chapter3-2 movie/save/cold-load proof, bounded r20c source queue evidence, and r211's matched9-to0 residency correction. Chapter3-2's end save is diagnostic-origin; it is not a replacement for playing from chapter3-1's end save. Fresh upstream Disc1 knob-off identity is assigned to Worker A. ACTOR_PLAN and ENEMY_VIS_CULL remain subject to the coordinator's landing notice. No chapter-ready claim is made.

## H027 continuing: original r203 reunion and internal door

The route still uses the immutable historical746 program and60aa disc, with the same native chapter6 origin and unedited production-state lineage. New I014 build and inventory checks are separate; their current ACTOR_PLAN1 program is not substituted into this route.

Ordinary Follow and the original upstairs exit change r207 to r203 in runBY at frame27335. The initial r203 saved-room flags are0, and crossing the original reunion area starts20300. The existing native pad script presses normal START at picture16; the original skip callback completes and sets source Rsf3. This is source-event progression, not full unskipped movie coverage:17 of1595 pictures are uploaded,16 presented, with one audio underrun retained. The exact initial-versus-current saved-room proof is `r203-native-initial-vs-current-saved-room-flags-20261019.json`.

The next ordinary corridor segment, CB, reaches(-34928,4156,-9780) in8.20seconds. CC stops on the original metal-door collision at(-37005,4156,-10063), with the actual A OPEN prompt visible; its52.77second owned run is not a route failure. CD uses only the original A action, then observes90 source ticks. The viewed still shows the door open and gameplay remains inr203. The original `emDoorAction` dispatches through `plemDoorOpen`; no door state, actor or source-script bytes are changed by the controller. CD owned-exits in7.02seconds.

All these endpoints retain Leon1440/Ashley360, phase3/Stop0 and chapter6. CB state is12525b14abd44f6f78b7ba0e524e7d2a4bcd906e4a073bf63da5f40a2259c997; CC isd7516372a7d064e1e89454008de33acfc14e58c24ea009f289150c802778ef9c; CD is6bfc35e1c549ad13f247f2e49f1943f41ec73257a976b773b2c236f03f38adaa. Exact four-code-anchor read-only audits and owned controller/run receipts are preserved under `castle18-20261018`, with scenario suffixes resevtcb/cc/cd.

AtCB the original four loaded type7 monks are source entries44/45/46/47, eachHP1000, and the five held byte-list entries remain48/37/39/3A/3B. This is an admission/navigation observation, not a wave-clear or release proof. The initial private audit's wrong word-width queue decode is retained as invalid; the verified artifact uses the symbol-proven64-byte Held array and only its firstN bytes.

The prison key, further waves, locked door, Garrador route and chapter-end save remain open. Original r203 GetKeyItem sends4B..4F and immediately callssetGoto, another potential held-command consumer; actual activation/release evidence is still needed and the new default-off fix remains explicitly r207-only. No room-general guarantee is claimed.

Current source is separately refreshed through upstreame86bf58e and WorkerA'sa996608e control document in48def0f3. Frozen I014 a808/25d default-off identity and inventory target-upload gates remain bound to their exact recorded controls; later upstream is not covered by that identity comparison.

## H027 continuing: original r203 Castle Gate Key and source queue

The same immutable historical 746 program and 60aa disc continue from the native chapter 6 route. Both metal doors open through normal A input, and ordinary movement follows the original stairs to the upper chest. The normal chest action completes its original callback in CL: the area 7 item-event entry is removed, source Rsf4 is set, and gameplay resumes. CM then uses normal A to take the revealed Castle Gate Key. At source frame 33098, the original ItemMgr contains active item A7 with quantity 1; phase is 3, Stop is 0, and Leon/Ashley remain 1440/360. There are no inventory, health, actor, flag or snapshot writes.

The exact CM state is 5c224652c3ea026f72e5469ae3cf760d4770b83ab12f79594ec94ecf743b201c. Four independent unchanged ELF anchors bind the read-only audit to this program. The owned pickup capture exits after 7.62 seconds with no capture errors. Evidence is `r203-native-CM-original-prison-key-snapshot-20261019.json` and the controller receipt under `h-c18oimW-r200l/scenarios/cx-r200-walk-resevtcm` in the Castle evidence root.

The original GetKeyItem callback adds source entries 4B/4C/4D/4E to the held queue. Its first nine byte entries are now 48/37/39/3A/3B/4B/4C/4D/4E; the same four original type7 enemies 44/45/46/47 remain loaded at HP1000. This proves the pickup's source send behavior and retention, not later releases, movement, wave clear or room acceptance. The immediate source setGoto calls remain a separate r203 consumer to qualify; the new movement fix is deliberately limited to r207.

The route next returns through the same corridors to the original locked castle gate and uses the actual key. Garrador, the remaining chapter rooms, current-source replay, residency and the chapter-end save remain open.
## H027 continuing: Castle Gate Key accepted by the original gate

The actual original key-item screen identifies A7 as the **Castle Gate Key**. Earlier prose and private evidence filenames called it the prison key; that descriptive label was wrong. The numeric item, source callback, archive, original inputs and saved-state lineage were always A7. Existing evidence filenames are retained with this correction. The later r201 dungeon/prison key is a separate item.

The normal return follows the source stairs and both internal metal doors, opening each through its actual A OPEN prompt. CY acknowledges the original locked-gate dialog and opens the original key-item screen (type0x80). It visibly shows Castle Gate Key as the sole key-column item, index0. The read-only original itemInfo/makeItemList audit independently matches that order; the metadata function is unchanged from the native build's source.

CZ selects this original entry and its original Use command. ItemMgr consumes A7 and the original r209_CheckUseKey watcher sets door_unlock[0] bit0x00020000. The source confirmation visibly reads “You used the Castle Gate Key.” DA acknowledges that confirmation normally and returns to phase3/Stop0 at frame36358, with Leon1440/Ashley360. Both original actor identities are restored (id0/id3), A7 is absent from active inventory, and all nine previously recorded held source rows remain retained. No actor, item, health, flag, executable or snapshot bytes are written by the controller.

Exact DA snapshot:8f6f0d603b4be4aa2d8037bb449f5897630571d8e5a6e969a6edaf72803f4646. The four-code-anchor proof is `r203-native-DA-original-castle-gate-unlock-snapshot-20261019.json`. CZ's used-key state isfed2a00c56269c1b9c1c07d67379c906e5676d08f87e555119f168610db1e3d7. Owned times are CY11.78s, CZ48.31s and DA8.45s; each exits cleanly with no capture errors.

CX is explicitly a host-guard false positive, not a game death or route failure. The first original A action opens the healthy lock dialog, whose Stop mask is0xffffffbf. The inherited guard mistakenly classified that mask alone as Continue and closed its4.2-second capture. The original snapshot proves health1440/360 and the actual source death bit clear. Subsequent private controllers use the source death bit plus health, preserve that snapshot, and continue the original dialog without guest edits.

This remains the unchanged historical746 program and60aa disc. The gate's source progression is proved; current-source chapter acceptance, wave clear, all room residency and the final chapter save remain open. The next step is ordinary entry through the unlocked gate to r201.
## Original r201 Prison Key and dungeon unlock

The unchanged historical 746 program and 60aa disc continue through the original unlocked r203 gate into r201, retaining native chapter 6 and health 1440/360. Normal navigation follows the original hall, opens its interior door with A, and reaches the source picture CHECK area. DO invokes the original picture callback and item event 80. The viewed pickup identifies **Prison Key**, actual item C3 quantity 1; its source name is DungeonKey. This is separate from the earlier Castle Gate Key A7.

The normal return reaches the dungeon's actual CHECK prompt. DT starts the healthy locked-door up-cut; DU and DV acknowledge successive original pages. Read-only input feedback proves A reaches the game's Key.on/Key.trg and its message pointer advances. DX finishes the remaining pages and the original handler opens key-item screen type80. There is no message-hang claim. DW is invalid before staging because an outer output redirect occupied the driver's exclusive result-log filename; no guest ran, and the invalid log is retained.

The original itemInfo/makeItemList audit proves C3 is the sole key-column item at index0. DY selects that item and its original Use command. The actual item is consumed and the original r201_checkDungeonKeyUse watcher sets door_unlock[0] bit8000. DZ acknowledges the confirmation normally and returns to phase3/Stop0 at frame47628, with Leon1440/Ashley360, actor identities0/3 and no held enemy sends. The original script, rather than the host, performs its Continue-backup update and battle-area opening.

The final snapshot is144b6dcb94ac130b3d32a66fca46aaf903384c1823a6c6a976ef2c25c235867f. Four exact ELF anchors bind the read-only state audit; door_unlock[0] is28000 (retaining the earlier gate bit), C3 is absent, and the source death bit is clear. Owned times are DO6.44s, DX13.72s, DY48.49s and DZ11.28s. Full controller, run, still and snapshot receipts remain under the corresponding resevtdo/dx/dy/dz scenarios. No actor, health, item, flag, source or saved-state bytes are written by the host.

EA then crosses the unlocked doorway and descends the original stairs, reaching source floor y-86 before the normal controller stops at the railing; lower-floor traversal continues. Garrador activation/combat, the switch, further chapter rooms and the chapter-end save remain open. The later current-source full partner additions are separate and are not substituted into these immutable snapshots.

## Original r201 cell, lever and Continue

Normal movement descends the unlocked dungeon stairs and follows the source collision geometry. The cell shows its actual A OPEN prompt. EG sends the original Ashley Wait command (flags42) and opens the cell through A. EH crosses the original area10; source row56/em1b type10 activates and moves with4000HP. Ashley remains outside the cell at360HP.

The first lever approach is failed play: EI takes real Garrador hits1440→864→608 and the health guard closes. EJ attempts the existing First Aid Spray through normal inventory input, reaches the loading inventory at352, then the host rejects an uninitialized puzzle board before any Use. EK is an early-pG host retry that sends no input. EL observes actualHP0 and the original source death bit. These attempts are retained; no heal or survival pass is claimed. EL's guarded retry uses the exact EJ seed, while no-input EK is not spliced into its accepted lineage.

EM sends only normal Continue acceptance. The source restores its own key-use checkpoint at frame47585: phase3/Stop0, Leon1440/Ashley360, no active C3, door_unlock0 still28000, actual source death bit clear. Snapshot86dd5ba1a0612977bc36bbfa521f00cba6f3114591aa5208c1d5122686690178 is retained with four exact ELF anchors. This is original game recovery, not health/state writes or loading an earlier external checkpoint.

The ordinary retry returns down the same stairs and opens the cell. EP makes the approach and original A action continuous, retaining1440/360. The actual original lever callback runs: room-save Rsf5 is set (saved r201 flags6c400000), and the barred gate rises fromy2000 to4300. The camera view shows the trap cleared. EP's first controller criterion mistakenly inspected temporary pG.Room_flg0, where58000000 is distinct from the saved room flags; its unconfirmed label remains in the raw receipt. The exact source flag_rsf.h and RoomData record prove the authoritative completion, without editing either value. EP snapshot isb8d940963c28bc54574c2b55c7bec97909c47c7043fcb0dc6559875649a5669b; owned capture13.89s.

The Garrador remains4000HP after that event. Actual source death, the dungeon exit, later reset waves and chapter-end save remain open. This historical program's evidence does not qualify current083 actor-plan behavior or the later default-off command/message fixes.
