# Castle I-006 cap progress, 2026-10-18

Current source: codex/castle18 ea31a7a5b8c6162366adc78d9fab2a05a64db7dc (pushed). Runtime validation of this follow-up is underway. Full Castle is incomplete. Island remains paused under I-007; boss modeling belongs Boss18. Final seven accessory/weapon variants and 1650-file data seal are reused unchanged.

## Source changes

b5869b45 adds default-off ALIVE_CAP_NOVIS. With ALIVE_CAP enabled, stage2 id2D uses the same budget as Ganados10..20 for initial creation, deferred sends and fresh-not-yet-active work. Existing held ESL entries still count in SceCountEmAlive. Existing Castle no-parking exclusions and Ganado-only park selector remain intact: no live Novistador is destroyed to enforce this cap. Existing raw-pointer take exceptions remain visible. r21d's original delayed reset task waits while the combined cap is full; its setReset sets ACTIVE synchronously before another reset task can run.

ea31a7a5 adds narrow source-room repairs behind the same knob. r205 sends69/6F wait for a slot before committing their source wave flag and immediately using the real actor position to open a door. Its actor-hit-list probe skips held wrappers rather than materializing a getPtr exception; a held actor cannot be in that hit list. r213's original statue-broken persistent Rsf2 state is restored after actual release initialization: all C2..CA receive flag20000000; C5/C8 receive hp0 and run their original death routine. They are never silently dropped from the queue. r205 held58 also receives its original alert flag1 on release. There is no generic wrapper change, new queue layout, ESL mutation, renderer exception or new model work.

Source-extracted host tests compile old and combined modes. They exercise all256IDs in stages1..4, mixed4 fresh admissions, duplicate-held sends, held-alive counts, paused/full release guards and release order. Real r205 wave functions keep the door send owed while full and issue it once free; held zone wrappers never call getPtr. The actual source-room restore helper changes only the selected source context and leaves forced-death actors alive/ACTIVE until the original death routine processes hp0.

## Initial b5869b45 runtime evidence

Every emulator requested55s, actual55.89..56.44s, trace_lock/release priority/owned processes. After the first pair, Castle captures were serialized under an owned guard because foreign release/model jobs were active. No foreign process was stopped.

- r205 off/on: actual boot plus all22overlays match selected program; zero extra overlays. Reference sampled5 combined enemies, candidate4. Both logs contain5 completed source hp<=0 kills and room census through600. Candidate held70 at4, then released it after a source death, with no take/park/drop. CAST still fails active camouflage; source wave/door completion not proved.
- r213 off/on diagnostic: reference9, candidate4; candidate holds5 and releases3 in the bounded window. Source kills5/7 at different maxroomticks, so no equal-clear claim. Both recovered fixtures retained unused st2_4/em3e overlays from an old build: INVALID for full staged-identity gate, even though boot/all22 selected overlays match. Fresh clean repeats are required.
- r21d off/on diagnostic: reference8, candidate4; both8 completed source kills. Candidate releases all4 deferred1B..1E. Same two unused-overlay issue: INVALID for full staged-identity gate. Original reset/final-switch waves remain pending.
- r20a off/on: zero Novistadors observed, zero holds. Actual program/overlay-set identity passes. STRICT/decisions MUST-IDENTICAL1060ticks (room anchors178/178), zero position drift,535029 em-em checks/37038line queries/1057area/32779damage checks. This is below-cap regression evidence, not Novistador combat coverage.

C evidence root: C:/Flycast-Evidence/re4-dreamcast/castle18-20261018.
- novis-cap-build-proof.json: c18n0rP T15REC off identity11/11 against independent current293 control, actual boota64f1944; c18n0rT53355630/end8c463578 and c18n1rTa31065af/end8c463698. All missing0; source flags independently found in em_set+r21d compile commands. Full ELFs and knobs C-mirrored.
- novis-cap-initial-summary.json, novis-cap-r20a-initial-decisions.json.
- h-c18n0 / h-c18n1, scenarios cx-r{205,213,21d,20a}-walk-capn{0,1}b. setup attempts suffixa failed before stage/capture due an ordinary-runner trace0 assertion; retained as invalid setup logs. The private runner now explicitly accepts trace1 diagnostics.
- novis-cap-esl-inventory.json: exact prepared ESL rows identify r20512, r20a2 (both chapter lists), r2139 and r21d13. No other stage2 Novistador room found in all three selected chapter lists.

## Next

All ea31a7a5 builds complete missing0: c18n2rP ee66d375/end8c4061d8, c18n2rT d4423144/end8c463578, c18n3rT faa3eb4f/end8c463758. Full ELFs/knobs mirrored. novis-cap-v2-build-proof.json proves all3 object macros and off11/11identity against current293 control (boota64f1944). New clean fixtures must remove all overlays absent from the selected program and assert the entire actual staged overlay set before capture. Use earlier bounded kills, then supported production save-state continuation for queued tails/reset waves if the one-minute window is insufficient. Do not mark queue/room/route progress complete from entry or a peak alone. Keep CH4REC unchanged until these source contracts pass.

Remaining full lane work: camouflage/refraction renderer review (retain refusal), room CAST/residency/audio/clear/wave/door gates, all Castle route rooms in order. Current existing task1 Ashley/chapter2 identity/STRICT and six48KiB KOS gates remain recorded; no repeat of the fixed archive admission. Revisit KOS on any final new runtime recipe. Boss models remain current while Boss18 owns changes.
