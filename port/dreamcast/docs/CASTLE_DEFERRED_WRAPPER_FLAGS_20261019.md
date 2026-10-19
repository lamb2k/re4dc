# Deferred room-wrapper flag commands, 2026-10-19

Status: default-off candidate. Fresh Disc1 off identity and isolated paired source activation/native-draw checks pass. Enabled room residency still fails; do not add this switch to a chapter/release recipe yet.

## Observed failure

The original r20c cage sends D6 (em1b type A, BIN221/TPL222) and calls `cEmWrap::setFlag(1)` while the four-enemy cap holds the send. The old wrapper accepts only a live pointer, so it drops this command. In the separately labeled bounded damage/release diagnostic, D6 leaves the held queue at frame1571 but all142 following samples through2601 show flag0 and hidden routine1/4/1; no native claw-body submission appears. The source first initialization clears ACTIVE for set15, and `em10HideJump` waits for flag bit1. This is progression evidence, not a natural-combat or full chapter pass. The original source sends, ordering and four-enemy policy remain authoritative.

## Change

`ALIVE_CAP_DEFER_FLAGS=1` remembers OR-only flag commands in64 held-slot masks (256B). Every wrapper for the same held ESL actor shares the mask; cEmWrap remains unchanged at12B. Queue compaction carries the masks with actor identity. Successful automatic releases and existing raw-pointer requests apply the mask after original first AI initialization. Direct repeat sends and room-start creation also apply it after their original first move. No ACTIVE bit, room flag, ESL record, admission order or cap exception is manufactured.

Failed/null/error-sentinel creation restores the original slot, sent marker and mask. A failed getPtr keeps the handle held for a later retry. Restore capacity is bounded: exactly one slot was removed, and every creation failure precedes first AI initialization, which is the only creator callback that could send another actor. Death or room invalidation discards the old command. Destroy/far-delete discard commands with the removed actor.

`stage.cpp::readEmList` can replace the list before room initialization. `game.cpp` calls `EmSetRoomInit` before `ScenarioRoomInit`, and the latter runs room init/scheduler before `EmSetFromList`. The existing EmSetRoomInit point therefore clears pending masks before any new room script sends, including a same-room Continue/reload or replaced ESL list. This changes no held-entry admission/deletion policy and needs no extra epoch storage.

Default is0. Make rejects invalid values and enabled use without ALIVE_CAP. Only em_set and module objects receive the feature definition when enabled. No header, room source, data image, model, converter, route recipe or release setting changes.

## Validation retained so far

- `port/dreamcast/tools/d367/castle18/test_deferred_wrapper_flags.py` compiles actual queue, creator and wrapper bodies with ASan/UBSan in disabled/enabled modes. It checks four creation paths, original initialization ordering, repeated OR/shared handles, live setter, allocation failures and retries, non-null error sentinel, all queue compactions, invalid rooms/death/reused slots, same-room/list reset, and full64-slot failed middle removal/restoration. It also checks eight Makefile cases and original room-reset ordering.
- Actual SH-4 preprocessing from the fresh CH4 command flags is byte-identical between prepatch, default and explicit0 for em_set and the base wrapper. V2/v3 include variants also match under supplemental preprocessing; they are not linked by this CH4 recipe.
- Fresh prepatch source is clean bb05534e86560a609ffdfce76ebecce60c352a12 with origin/t15/int7adb8d22bf95981b283300222099fb929a31364c. SOURCE_DATE_EPOCH1760000000, one serial -j4 slot. All resolved knobs, input recipe hashes, generated headers, logs, raw programs and symbols are retained privately.
- Fresh literal Disc1 c32dfbrP: ELF11293b47913a74d95d946c2a82885c6d3418dd2ac2b8a9628d9d9fa39a9d2487, raw3afe9d759b86afeb93f3998563ae0058ea7b41cbcdf3538eaf9f69bdd4aabe1e, end8c4061d8.
- Fresh CH4 diagnostic c32dfbmW: ELFd8e235930a99df25dc29f05608c19af6184dc23b0488ae5b9cd2e90acab26df3, raw67884ca4af30371471a665fc3707930911b571359905e1369a248e96448e8248, end8c46ed98. Eight actual wrapper commands are the base source in st1_0..3/st2_0..3. Candidate build must assert the feature on all eight and em_set.
- Historical746 is retained only as the original route snapshot; it is not relabeled as the fresh7adb control. ACTOR_PLAN resolves0 in both fresh controls.

Private evidence: `C:/Flycast-Evidence/re4-dreamcast/castle18-20261018/workers/ch32/deferred-flags/`; source failure detail is `r20c-deferred-activation-reproduction.json` in the worker root. The V17 residency union separately preserves all5765 prior records and adds only three observed death/release keys (5768total); corrected-program runtime coverage remains pending.

## Fresh candidate build receipts

Both candidate builds use reviewed/pushed db9438195, frozen clean source, the same input recipe/headers, SOURCE_DATE_EPOCH1760000000 and a single serial -j4 slot. No missing symbols. Disc1 c32dforP boot plus all10 overlays and raw program match the fresh c32dfbrP control byte for byte. Every allocated ELF section matches, including addresses, sizes and contents. The full ELF differs only in nonallocated `.debug_info`, `.debug_abbrev`, `.debug_line` and `.debug_line_str`; it is not described as whole-ELF identity. Candidate ELF9751d917754f01da75879fe5a7e6de13676c6c1511a30d3cf0000d7b6f4639de, raw3afe9d759b86afeb93f3998563ae0058ea7b41cbcdf3538eaf9f69bdd4aabe1e, end8c4061d8.

CH4 enabled c32dfnmW ELF0838b83195467bf8efe577ddd762a9610b37520161e65bc0b90242aedc3adb63, raw93e3b263642ce90da3e21e9b638ad3e9d6f0fc89ef19c4a412134446cd1b421a, end8c46f1d8 (+1088B total versus fresh CH4 baseline). The pending-mask symbol is exactly256B. All eight actually linked base wrapper compilations plus em_set carry RE4DC_ALIVE_CAP_DEFER_FLAGS=1; controls omit it. V2/v3 remain supplemental include-variant coverage, not linked runtime evidence. ACTOR_PLAN remains0 in every arm. Cap-off SH-4 preprocessing also matches the untouched source for em_set and the wrapper; no separate cap-off guest run is claimed.

Fresh paired cage fixtures select each new build's exact boot/all22 overlays and the same V17 data. They start from the original warp/source trigger and damage fixture, with no historical746 snapshot retarget. Independent ELF-keyed read-only observers use each build's actual symbol addresses. Guest admission, appearance, memory and progression remain pending.

## Fresh paired release result

The fresh 7adb off/on pair uses identical nonprogram payloads, the same V17 resident union and the same original cage plus bounded kill/killrep diagnostic. Both boot and every staged overlay are checked against their selected fresh programs. Each arm has an initial capture and its own unchanged-disc saved-state tail, all under60 seconds, with owned emulator exit and no capture errors. Neither historical746 nor the later f255 upstream is represented as this pair.

D6 leaves the queue at observer frame1571 in both arms. Off remains flag0 and routine1/4/1 through frame2583, with no actual 0ag native admission. On preserves the original pending bit, applies flag1 after first AI initialization, advances to routine1/27/1 and the source floor, and records771 actual claw-body native submissions with zero declines, fallback or semantic refusals. Its first sample observes the middle of initialization (flag0), not an ordering violation. The read-only observer posts no input and writes no guest memory. Counted Ganado census never exceeds4; raw alive totals also include other source objects.

Off captures56.38+56.09seconds; enabled56.05+56.38seconds. Exact reserve receipts hold/request49152 bytes; minimum logged headroom is38080 off and38208 enabled. Off residency passes zero late uploads. Enabled official final room tick fails15 late uploads, with guard/refusal/retry/eviction/TEX/audio failure counts zero. Full first-sight audit finds three more death-text uploads after that tick (18new keys total), so the result remains a residency failure pending an additive preload correction. The three later text keys remain in the complete raw ledger but are held separately for source menu-ownership review; only the15 gameplay keys are authorized for the room list. No paused-menu filter is relaxed. Source image/format winners are retained.

The unattended enabled enemy kills Leon (observerHP0firstat1886); retained stills show critical health then the original death transition. This demonstrates activation and native drawing, not survival, a completed fight, all queued releases, cleared doors or a no-warp chapter. The one-part id01 planL draw after death is not playable/partner Ashley evidence. No hardware timing or speed claim is made.

Private paired proof: `workers/ch32/deferred-flags/r20c-paired-runtime-proof.json`, arm logs and `r20c-{off,on}-runtime.json`. Off disc80fda0ec0d8724641affe4ca0e5a8a74f58f1d93477b028fc3ef35c414088723; enabled62b0fbec63df69f479ffd7ca2fda202758e4cf15e5a135d5eb23f45df4637539. Exact combined logs f75e9bbb0f196a4aa1efd1da364238d03b15b93563b6718b3a6b35cc41192f98 and b310b6017517d816fcf80cbada27a140231761e2a362fb0bf0b683df5f796032. Source/build file claims are released; data follow-up is separate.

## Enabled gameplay residency candidate

The separate V18 additive candidate preserves all5,776 records from the latest r212/219 union and adds15 source-observed r20c gameplay keys (5,791total). Dimensions/formats use actual source upload metadata, including non-power-of-two source sizes; selected package winners and every image byte stay unchanged. The three later death-text keys remain outside the room list, retained in the complete ledger for source ownership review. Fresh matched enabled-program validation is pending.

Private dataset `castle18-ch32-r20c-active-resident-v18-20261019` is mirrored to C:. Resident SHA fbc6957986724720d9127021a6bfda8d2fce66dac8a988a121c5bd103dd25568; manifest d730b723f64db27c2a65c5997833ea94863e2125cf8a04e32e5fe5d3141c718a. Source fragment `port/dreamcast/tools/d367/castle18/ch32-r20c-active-resident-v18-20261019.json`.
