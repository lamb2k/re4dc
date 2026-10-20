# Shared loading successor, 2026-10-20

Branch: origin/codex/cache21-successor. Base: c7e0358a. Current runtime imports: 1bb1ddec (weapon reuse), b753db30 (movie resume including the corrected 96-byte allocation preflight). HUD preparation tool: f33c3189. Corrected target object receipts: 37f85373.

The existing motion accounting/packing pair is already in this upstream base. The new components address shared loader lifetimes. They do not reduce enemies, animation frequency, collision, effects, or game logic.

## Components

| Component | Activation | Memory and behavior |
| --- | --- | --- |
| Weapon archive reuse | WEAPON_ARCHIVE_REUSE=1; default zero | Retains the same successfully linked archive after repeated equip. Validates mapped file and live backing; explicit release invalidates it. No extra archive allocation, two added BSS bytes. Distinct weapon files still load normally. |
| Movie motion restoration | MOTION_RESUME=1; default zero; requires motion backing accounting, movie eviction and route movies | Restores only recent actual consumers whose heap keys the movie evicted, after original resource and event restoration. Generation checks, aggregate cap, heap margins and full allocation overhead remain enforced. No extra fixed payload reservation. |
| Complete ammo digits | Optional existing-format resident.bin prepared by prepare_hud_digit_residency.py | Preserves every original record and adds missing common digits 2-9. Adds 8,192 native bytes if admitted, 14 common keys within the existing 16-key limit. No runtime or recipe change. |
| Joined reserved region | Separate follow-up, not included here | Intended to address source-possible worker/hit sets that fit the total payload budget but cannot fit two independent slabs. Requires its own source and target qualification. |

## Completed on this combined source

- All 48 actual-source weapon cases pass with address/undefined sanitizers across reuse off/on and heap4 off/on.
- All seven actual native-motion loader variants pass with address/undefined sanitizers and leak detection, including prior accounting/packing cases and movie restoration failure boundaries.
- Independent journal sanitizer tests pass: 424 bytes of tracking and 144-byte tickets.
- Each weapon default-off SH4 object matches its original parent; the actual read.cpp body is unchanged upstream before this import. Full linked identity is still required.
- Movie SH4 off objects match the c7 control. Corrected native-motion preflight was recompiled after the 96-byte correction; enabled section sizes remain unchanged. The three affected enabled objects add 3,239 text bytes and 569 BSS bytes in total. These are object deltas, not linked program growth.

## Runtime evidence belongs to the frozen earlier candidate

QA program 751a7451 / source 4aca1f83 contains only the earlier motion pair. Its original r100 ambush kills three pursuing enemies with ordinary inputs and records 21 to 24 motion loads, zero evictions and a 16.625-second final interval without reads. The baseline recorded 682 evictions. Input and death variants differ; this is functional cache evidence, not a frame-identical timing comparison.

That same program has reached the actual r103 cowbarn interior with the original Suki worker, normal alert and damage, and no firing: 23 to 25 motion loads, zero evictions. First-use reads and later body hits remain separate checks. Castle K independently tests the earlier pair on fresh program lineage. None of these windows qualifies the later weapon or movie additions.

## Remaining acceptance

Use the same explicit resolved recipe to build a current-c7 control, successor with both new knobs off, then enabled successor. Compare complete boot and overlay payloads and ELF runtime load segments. Record enabled linked size and unresolved symbols.

Qualify bounded KOS/heap pressure, ordinary movie completion and skip/cancel, inventory hold/resume, room retirement, same-archive re-equip after a real switch, distinct weapons and shared variants, continue and character-family transitions. Attribute actual weapon, motion, hand, sound, effect and texture I/O separately. Verify optional HUD preload admission and VRAM before proposing it for production.

Use fresh program lineage, never retarget a prior binary's state. Preserve frozen QA/K evidence. Full automated release, whole-route and physical Dreamcast acceptance remain open. No new successor disc has been published or copied to SD. Claude owns production integration and official releases.
