# October 7 source bug qualification

## Follow-up crash context for issues 8, 9 and 2

The crash screen now records the saved main-thread PR and signed milliseconds
to a timed wait deadline, includes timed main-thread stack return candidates,
and prints the active inventory area and overlay load address. Return addresses
are kept complete within the screen width. This addresses gaps in the existing
photographs; it does not identify or fix the reported faults.

The opt-in `crashtest.txt` test hook accepts `sleep`, using the existing one-shot
flag to sleep the main thread for 120 seconds. Ordinary execution leaves that
flag zero. The original source hang detector can halt after 3,600 vsyncs during
this deliberately long sleep; recovery from the synthetic hang is not claimed.
The test file is not added to a play disc.

* Host checks exercise the actual report, stack scan and signal bodies with
  synthetic thread states, including expired and 64-bit deadlines, full screen
  bounds, an active overlay, normal signals, and both one-shot block modes.
* Clean Dreamcast cross build has no missing symbols. Relative to the accepted
  combined play build, text grows by 640 bytes, BSS is unchanged, and linked
  `_end` advances by 192 bytes. The inventory bridge receives the crash-screen
  build definition through its existing generated header dependency.
* A private Flycast cold title Load into the r103 typewriter save completes two
  normal inventory closes and returns to the rendered room. The backing checks
  restore 3,129,056 and 3,128,864 bytes with matching `d5441259` and `4baf3fd6`
  hashes. No deliberate sleep is armed during those normal cycles.
* On the third open, the private harness writes value 2 to the existing test
  flag in its owned emulator. After the deliberate stall, the captured screen
  shows `ss area 8c80b9e0 overlay 8c80ba20+1eb40`, `wait +89527ms`, and full
  main-thread return candidates. `8c0337e6` resolves to the injected sleep in
  `OSSignalSemaphore`. This is a synthetic diagnostic check, not reproduction
  of issue 9 or evidence that a real console resumes after a hang.

The qualified ELF is
`3894026f17bf54999a5cbda8cb44b207fb6d013d06bcdccb302faa278b90cab5`.
Private evidence is under
`C:/Flycast-Evidence/re4-dreamcast/coldload-20261007`, scenario
`cold-crash-context-v2`. The earlier v1 run is retained: it exposed a missing
build definition that omitted the overlay line. No release, SD change or issue
closure is part of this diagnostic follow-up.

### Cold and warm load comparison

Further private tests use the same early FILE1 r103 save. Its frame counter is
508; the original save block intentionally stores and restores that counter.
The warm test therefore uses controller timing based on display retraces, so
loading the save cannot delay later controller inputs until an old source tick
is reached. No gameplay counter or save contents are changed for these tests.

* Cold title Load with the qualified ELF above and Flycast's interpreter plus
  alignment checks completes three inventory closes in 368.09 seconds. All
  backing hashes match, the alignment log records no misaligned access, and
  movement continues through source tick 6120. This is a stricter emulator
  check, not a model of every console cache, DMA or timing behavior.
* An additional cold-load build uses the existing `POISON_RAM=0xA5` option for
  unused RAM, the arena, VRAM and sound RAM. Its 361.22-second run completes
  three closes with exact backing restoration, then movement and world
  execution through source tick 8760. This deliberately different startup
  fill does not reproduce the fault. It is not enabled in the manual candidate.
* Normal New Game completes all three opening movies and the radio, followed
  by ordinary pause-menu Load of the same r103 VMU. The 454.03-second run
  completes three inventory closes and post-close movement through source tick
  4200. The radio restores 3,145,600 bytes; the three inventories restore
  3,122,752 / 3,122,688 / 3,122,688 bytes, with matching hashes `a8d7d4c8`,
  `ce1429e8` and `8e0f19f0`. The runtime is the same qualified ELF above, with
  ordinary Flycast execution rather than the interpreter used for alignment.

Both normal cold cycles in the earlier synthetic-diagnostic run and all warm
cycles succeed. Cold and warm paths have different live memory layouts, but
these tests do not reproduce a failing-versus-passing distinction. They do not
establish the reporter workaround's cause or fix issues 8, 9 or 2.

Earlier incomplete fixtures remain preserved: warm v1 reached New Game and
Load but no inventory cycle, and poison v1 stopped at the storage floor before
the inventory test. Neither is counted as a passing inventory regression.
Exact private reports are `cold-extended-qualification.json`,
`warm-inventory-v2-qualification.json` and `save-frame-inspection.json` under
the coldload evidence root above.

A local manual diagnostic candidate is prepared from runtime source
`c97764515c214ebf95d2c0c447c855c367313800`, using the qualified ELF above.
The CUE and GDEMU folders are under `C:/RE4DC-Play-Discs`, named
`crash-diagnostic-20261007-title` and `crash-diagnostic-20261007-gdemu`.
They contain `READY.txt` and `SHA256SUMS.txt`; no automated input, warp,
debug-save or forced-crash file is included. The GDI verifies all 1,195
payloads in both namespaces and boots to the title menu in a 91.20-second
Flycast run. Track 3 SHA256 is
`b78efdfea87d8b9598b87c9a0575b1f677d379a624bf59ef0fc9a24457437c28`.
This is prepared for a console diagnostic attempt, not physical-console
acceptance, a public release, an SD write or a reported-bug fix.

## Missing weapon beam, issue 12

The reporter and user confirm that the target dot already appears; only the beam
is missing. The source weapon target, collision result and dot are unchanged.
The source Esp19 line had no native presentation route during the coarse effect
pass. `NATIVE_LASER=1` retains its original callback and carries the final source
endpoints, maximum-length clamp, colour fade, blend, depth and fog state into
the existing deferred effect queue. One untextured 160-byte strip packet draws
the one-pixel line in source OT order. There is no new renderer/frame owner,
texture, persistent cache, heap allocation or memory reservation. The general
make default is 0; the play recipe enables it.

Private qualification is rooted at
`D:/Flycast-Evidence/re4-dreamcast/bugs-20261007`. No release or SD was changed.

* Same wall, handgun aim commands and 1,195-payload fixture: beam absent in the
  control and present in the candidate. Both 180-second Flycast runs finish
  normally. Captures are visual checks, not an exact held-frame pixel gate.
* Full common source-frame window 0..2910: 2,911 STRICT logic records and
  MUST-IDENTICAL decision records, including both aiming periods. `ACT_CAP=0`.
* r22j and accepted 512-entry clean knob-off twins match their respective
  retained baselines in all allocated section addresses, sizes and bytes, and
  in the sub-screen overlay. Debug metadata differs.
* Both 320-entry and 512-entry clean laser-on builds add 1,664 text bytes. All
  allocated section addresses, every other section size, BSS and linked `_end`
  match their own off twins. Overlay import addresses are regenerated for the
  changed main functions; overlay bytes therefore differ.
* At sampled native frames 480/600/720, control and candidate match VRAM use
  1,895,808 bytes, peak 1,952,640, texture loads/frees 268/149, model resource
  rejection 294/414/534 and wrap rejection. Model capacity/state/invalid/overflow,
  stream discarded, pipeline failures/timeouts and UI/effect drops remain zero.
  Existing ambient effect missing/capped counters are 19/5 in both arms. Those
  pre-existing warnings are not described as zero or as a beam regression.
* SH4 nominal hardware model at 200 MHz, r101 wall aim, source frames 630..633:
  direct entry proof finds one beam on each drawn frame 630/632 and none on
  skipped frames 631/633. The 32-frame census is 630..661. The synchronous
  Esp19 callback subtree is 0.0228075 ms per drawn frame, with no IRQ cost in
  that subtree. The shared drain's extra 160-byte submission is outside this
  number. This is neither physical-console timing nor a whole-frame FPS delta.

* Laser-on no-item-action inventory regression: the source-pad-clock fixture
  runs 301.14 seconds, completes three closes, and restores matching hashes
  `fb7a2a22` / `b5f45eaf` / `79a53681` for 3,134,048 / 3,134,272 / 3,134,272
  bytes. World execution resumes between those visits; the script then leaves
  a fourth inventory open with its UI still advancing. No required allocation
  failure or exception occurs. The earlier six-pulse retrace fixture completed
  only two closes and is retained without calling it a three-cycle pass.

The reviewed runtime is commit `abd0853b`. A fresh clean rebuild from that
committed source, with no private inventory diagnostic patch, produces ELF
`33c0fd02cffc36aa3a63c48f7ac752f2ccd96a7b60c76bbd885dd1e9dd0dfd83`.
All allocated section addresses/sizes/bytes, the boot binary and the sub-screen
overlay match the qualified final clean candidate exactly. Private helper/debug
metadata explains the different full ELF hash. No missing symbols are reported.

The final combined play-stack resource gate below passes with the 512-entry
collision list, beam on and Ganado source lighting off. Console beam/depth/fog
quality and the reported console faults are not certified by these checks.

## Console inventory fault, issue 8

The clean diagnostic-off build has exact r22j allocated-byte/overlay identity.
Its automatic no-item-action r101 fixture and an observational cleanup twin
each complete three inventory opens and closes. All backing bytes restore with
matching hashes; every observed cleanup phase and subsequent world execution
finishes. The fault is not reproduced, and no speculative cleanup change is
adopted. The reporter subsequently confirms that starting New Game before
loading the save prevents the inventory crash. This is a reported workaround,
not an independently reproduced cause. The reporter cannot supply the failing
VMU; it is not a prerequisite for further investigation. Pacing remains
unconfirmed, and a follow-up asks whether the workaround prevents issue 9.

A further cold-boot test uses normal title Load, a preserved private FILE1 r103
typewriter save and no warp. The diagnostic r22j runtime runs 361.28 seconds,
completes three no-item-action inventory closes, reaches cleanup phase 30 on
each close and continues world execution after the third. Restored sizes and
hashes are 3,129,056 / `c3d0e545`, 3,128,864 / `495c5382` and 3,129,088 /
`4a87721b`. The final framebuffer shows native gameplay. ELF identity is
`1c9ab2e203bcd6551d21654c53d14ee433a731e9b29a164bc77b6fe1cceffc9d`;
the reviewed private report is
`C:/Flycast-Evidence/re4-dreamcast/coldload-20261007/cold-inventory-qualification.json`.
This save does not reproduce the cold-load failure. These Flycast checks do not
fix or certify the console report; no runtime change follows this investigation.

## Bridge door hang, issue 9

The reporter confirms the door at the end of the pictured bridge, loading the
next area. Archive door 1 points from r108 to r109 and starts with trigger 2;
the original `SceAtRoomSet` turns it into runtime action trigger 8. The live
source dump confirms that conversion. A walking-only fixture does not activate
this door and is not transition evidence.

The corrected fixture uses ordinary A presses and movement from a synthesized
bridge start. Source door loading enters r109 generation 2, completes its room
initialization and continues for the remainder of the 300-second run without
HALT, MISSING or a hang. This is a real source door transition in Flycast, not a
forced room jump or a reproduction of the reporter's hardware/save history.
The console cause remains unresolved. The reporter cannot provide the VMU;
investigation continues without treating that file as a prerequisite. Pacing
and a console capture with the improved crash context remain unconfirmed.

## Ganados use Leon's prelit lighting path

On October 7 the user reconfirmed Leon's historical baked-lighting performance
choice and asked that Ganados use the same path. The play recipe now selects
`ACTOR_GANADO_SOURCE_LIGHT=0`. Native Ganado owners use the existing constant
`SourceLighting` record already used by Leon, including registered native
appearances. This turns off the existing live-light capture override. Meshes,
textures, source poses, simulation and existing fallback/proof rules remain.
No new lightmaps, format, renderer, frame owner or model conversion is introduced.
Unqualified source fallback still keeps its original semantic checks.
The separate private live-Leon lighting probe is not adopted; both rejected
Leon performance knobs stay off. The general lighting make default was already 0.

* Beam-on live-light versus beam-on prelit trace twins: all 2,911 common source
  frames 0..2910 are STRICT; required decisions are MUST-IDENTICAL. No exclusions
  or diagnostic delays are added. Both traced runs finish normally.
* SH4 nominal model at 200 MHz, r101 wall aim, source frames 630..633, `ACT_CAP=0`,
  320-entry list, `DBG_WARP=1`, `PC_SAMPLER=1`: live-light ELF `389c401a` versus
  prelit `979fafae`. Direct entries prove the same two drawn/two skipped frames,
  seven actor draws, one world draw and one beam on each drawn frame. All 32
  census frames 630..661 are retained. The sample instruction means differ
  from their census means by -0.335% / -0.381%; untraced modes are not invented.
  Drawn cost 70.259773 -> 69.478605 ms; skipped 26.441400 -> 26.093970 ms;
  balanced sample 48.350586 -> 47.786288 ms (-0.564299, 1.17%). This small local
  whole-model gain includes compiler/cache/interrupt effects; it is not a
  lighting-subtree saving, general crowd result, physical-console FPS or 30 fps
  acceptance. Raw attribution shows native actor work moving between paths.
* Clean final 512-entry ELF shrinks text by 544 bytes and character data by 32
  versus the laser-only carry build. Compared with the accepted capacity-only
  baseline, beam plus prelit adds 1,120 text bytes and removes 32 character-data
  bytes. All allocated addresses, BSS and linked `_end=0x8c3dfe7c` are unchanged;
  there is no arena/reserve growth. The existing per-owner live-light record is
  omitted by its already supported build switch.
* Final combined 512-entry diagnostic play build, `ACT_CAP=0`, completes a
  420.91-second synthesized r100 source-event run. s03/s20/s30 finish
  1,465/571/340 frames. s30 starts with 63,584 bytes, matching the accepted
  capacity baseline. Both radio visits restore all 3,144,448 / 3,027,520 bytes
  with matching `dea20b8a` / `a7924635` hashes. World execution continues through
  source tick 9,600. No required allocation, work-backing, pipeline failure,
  timeout, HALT or MISSING is reported. This is Flycast event/resource evidence,
  not continuous normal New Game or physical-console acceptance.

The lighting draw-only host run was stopped by the capacity guard at 129.56
seconds, after the sampled aim interval, and is retained as aborted. The final
trace/resource runs and separate hardware-model arm complete normally. Earlier
beam trace and laser-only radio attempts stopped by the same storage guard are
also retained. Completed owned test discs were compressed with before/after
SHA256 identity verification; none was deleted and no SD/release was changed.
Private exact reports include `ganado-cost-evidence.json`,
`ganado-linked-resources.json`, `gate-ganado-all.json`,
`gate-ganado-decisions.json` and `ganado-final-radio-resource.json`.

## Fog and older freeze

Issue 11: r108 source fog is type 4, start -2,733, end 246,702. The native table
uses the selected far limit 25,000 and reaches full opacity over its last 20%
to hide rejection at that same distance. PS2 haze is also enabled. The user's
issue comment confirms that the reduced drawing distance is partly intentional.
The range/fog decision is preserved; the unmatched comparison does not establish
a KOS defect. A less opaque table alone would expose that distance boundary.

Issue 2 remains a separate earlier hardware/save freeze, with no supplied failing
VMU or current r22j confirmation. None of the above checks closes it.
