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
