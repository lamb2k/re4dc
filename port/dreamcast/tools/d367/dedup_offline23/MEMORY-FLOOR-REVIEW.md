# Memory-floor review: historical release twin versus current QA arms

2026-10-23. Read-only source/evidence review; no builds, staging or guests.
Gate decision remains with main. **The 94 KB floor is not established by the new
40,352-byte matched result.** A directly relevant e17 release-gate H2 record still
shows98,016 bytes on the same warp/pad fixtures. The large difference already
exists at arena/heap creation, before SDO3 is loaded, and is consistent with the
larger QA/diagnostic programme. The exact split among all diagnostics needs a
same-source standard-twin comparison; WORLD_METER alone is not established as the
cause.

## Evidence and identities

| Capture | Source / programme | s30 heap_before | s03 / s20 heap_before |
| --- | --- | ---: | --- |
| rr/1023-1520-2747f928/h2 |2747f928 release gate twin |102112 |889440 /794816 |
| select-only23/rr/1023-1532-so23on-2747f928/h2 |2747f928 select on |102112 |889440 /794816 |
| rr/1023-1610-451bed6f/h2 |451bed6f release gate twin |98016 |885344 /790720 |
| rr/1023-1630-e17af64a/h2 |e17af64a release gate twin |98016 |885344 /790720 |
| select-only23/rr/1023-1643-so23sb-451bed6f/h2 |451bed6f submit arm |98016 |885344 /790720 |
| dedup-offline23-20261023/full-h2-off-console-r1 |af09f0a2 dd23af09offrW |40352 |811520 /716896 |
| dedup-offline23-20261023/full-h2-on-console-r1 |af09f0a2 dd23af09on2rW |40352 |811520 /716896 |

All paths above are below C:/Flycast-Evidence/re4-dreamcast/. Historical and new
logs show s03=1465/1465, s20=571/571, s30=340/340 uploaded/presented; s30 loan return
restored1. Warp wire363 bytes SHA256
921ee89e2286ff7801736dabd1d9cb58321f25540ab3b3e3e63230eabb822012;
pad215 bytes SHA25680a97aa5b3ac9c4e3f8945089108d98f432fa8f57b00d2e7385733cb8d461ac1.
The new fragment's140448 bytes is a different post-ambush starting state and is
not the full-H2 comparison.

The nearest same-base proof is
[rr e17 H2 log](/mnt/c/Flycast-Evidence/re4-dreamcast/rr/1023-1630-e17af64a/h2/run-output.txt:3666).
Its retained [cycle.env](/root/rr/work/1023-1630-e17af64a/cycle.env:2) identifies
source e17af64a696778198474b1053cc8a37084eb2c3b. The retained
[twin receipt](/root/rr/work/1023-1630-e17af64a/twin-rre17af64g.txt:2) records
fprre17af64gW, programme hash prefix d49ac99b63bf82eb and _end8c43c038;
release_end8c430df8. The original twin output directory and base were pruned, so
this audit cannot recover or independently rehash its complete ELF or actual
resolved-knobs.txt. Do not promote the16-digit prefix to a full programme pin.
The release image SHA256 retained in kit/release-knobs.txt is
5c7226ddf63bb7237ccda1de97678039bc4af1fb1e918cfd1364113645897368;
it is the release rP image, not the gate-twin ELF.

Retained e17 file SHA256 pins:

- recipe.conf91b14bc1114a297a9c2b69eba1e620e15ea9c91a90c1e177bd9825b819d6af4b.
- kit/release-knobs.txt0c99bec3d1afcab14fbc65c728e344509a660927b4a4d4265d6d1f1d32a3b7fc.
- twin-rre17af64g.txt884c83b52609a5cb9454f1f3b79324fbb86d31cbd282c03ce19ab4fe39f59a32.

The recipe blob is identical at451bed6f, e17af64a and af09f0a2. At2747 it was
67a9dbb1e932b0c176bd8073d9b74bc7496d61658ecc9907df57c8c65171e48f;
water/traps were added subsequently. The handover's approximate94 KB value is not
an exact current programme identity, but the stronger e17 result prevents treating
the whole difference as an obsolete recipe. Latest base/recipe still had98,016
bytes in its ordinary release gate twin.

Current exact ordinary QA programmes are pinned by
[programme-pins-af09-offon-r2.json](/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/programme-pins-af09-offon-r2.json).
OFF ELF6747c71485b2c26642e087f11a1180e1b21792647ef9c4388904bb8be1e5ef64;
OFF resolved knobs973b979ed4c53c00e16054dd6b329dbee1ae65f3bab846b8cd61ee48eeff320d.
Both actual programmes are source af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34.
The existing knob-off image-identity check compared equivalent QA variants; it
must not be confused with identity to the smaller rr release/gate programme.

## Observed layout and diagnostic difference

The e17 gate twin receipt explicitly requests DBG_WARP1, WARP_JUMP1,
PC_SAMPLER0, TEX_CHECK1 and MCHECK_LEONGC1. The ordinary QA OFF resolves
QA_MENU1, WORLD_METER1, PC_SAMPLER1, PHASE_METER1, DISC_READ_METER1,
GAME_TICK_LOG60, WARP_AFTER_RESET1, WARP_JUMP0, TEX_CHECK0, MCHECK_LEONGC0.
The actual old resolved-knob file is unavailable; its release defaults plus
explicit twin overrides are retained, rather than an invented complete resolved
comparison. That request also differs in PS2_ENEMY_ROOMS0x3f versus QA0x3ff.

| Quantity | e17 gate twin | current QA OFF | OFF minus e17 |
| --- | ---: | ---: | ---: |
| _end |0x8c43c038 |0x8c44daf8 |+72384 B |
| Arena start |0x8c453fe0 |0x8c465aa0 |+72384 B |
| Arena bytes |11972608 |11898880 |-73728 B |
| r100 heap4 at creation |7487872 |7414048 |-73824 B |
| s03 and s20 free bytes |see above |see above |-73824 B |
| s30 free bytes |98016 |40352 |-57664 B |

The first two movie deficits exactly equal the heap-creation deficit. At s30,
16,160 bytes of that deficit have been offset by different dynamic residency or
allocation lifetime; this review does not attribute that remainder to one owner.
On also has heap4 size7414048 and the same three movie free-byte values. Its arena
addresses move another2976 bytes with the larger programme, while the fitted
arena size stays unchanged in these runs. Equality here establishes only zero
observed Off/On delta for this QA profile, not whole-RAM neutrality in every
profile or preservation of the historical floor.

Concrete source/ELF costs that distinguish the QA build:

- PC sampler's fixed .bss ring is16,512 bytes (target symbol re4dc_pcs size0x4080).
  [pc_sampler.cpp](/root/work/lanes/dedup-offline23/port/dreamcast/game/platform/pc_sampler.cpp:47)
  defines it. [Makefile](/root/work/lanes/dedup-offline23/port/dreamcast/game/Makefile:3131)
  also increases the initial arena's KOS reservation request by20,480 bytes when
  the sampler is on. ARENA_FIT then chooses the actual arena; do not add the
  request reserve, ring and observed arena deficit as independent losses.
- QA menu has at least23,538 bytes of identified fixed arrays: presets6720,
  chapter names640, input text8192, diagnostic text3072, log1940 and two QR
  buffers1487 each, confirmed in the current target symbol sizes. See
  [qa_menu.cpp](/root/work/lanes/dedup-offline23/port/dreamcast/game/qa_menu.cpp:163)
  and [qamenu.mk](/root/work/lanes/dedup-offline23/port/dreamcast/game/qamenu.mk:33).
  Menu code, QR code, rodata and remaining state add image bytes. These static
  costs remain even when warp.txt skips the boot menu.
- WORLD_METER expands tick-log slots32 to48: target Slot20B adds320B and its
  three snapshot arrays add192B, before its other keys, counters and code. See
  [tick_log.cpp](/root/work/lanes/dedup-offline23/port/dreamcast/game/tick_log.cpp:52).
  This512B subset is not a total WORLD_METER cost. Other enabled QA meters and
  disabled gate checks also change the programme; no exact per-knob total is
  claimed without a same-source build comparison.

[Memory setup](/root/work/lanes/dedup-offline23/port/dreamcast/game/platform/mem.cpp:73)
fits the arena after the current KOS break in4KiB units. The measured image and
arena shifts therefore provide a direct mechanism for the initial deficit.

## Minimal next comparison for main

Use the actual current source's recipe rP as the input to the existing
[fp_twin.sh](/root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/fullplay/fp_twin.sh:43),
with its release-reproduction identity check enabled. Create uniquely named Off
and On standard gate twins; only SCENERY_DEDUP differs0/3. Keep QA_MENU0,
WORLD_METER0, PC_SAMPLER0 and the existing gate overrides DBG_WARP1/WARP_JUMP1/
TEX_CHECK1/MCHECK_LEONGC1. Preserve every other exact release recipe token,
programme/source/data identity and the same full-H2 fixtures. Do not merely
remove QA_MENU while retaining the other QA diagnostics. Pin new actual resolved
knobs and programme bytes, then compare all three movie heaps, heap creation and
s30 return/reload. This audit launches nothing and does not approve that run.

Both new full-H2 run-results report console mode and elapsed59.7/56.6 host seconds
with unthrottled JIT, but the requested timeout was240 seconds. They are recorded
observations, not physical-console speed or a newly approved timeout policy.

Small explicit evidence inventory:
[memory-floor-review-pins.json](/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/memory-floor-review-pins.json),
SHA2563dd7a1aa036e6bc526e44cbcb1755446e0c562f3206d0db7dde7a235516e179e.
No large media were read/copied, and no existing evidence was changed.
