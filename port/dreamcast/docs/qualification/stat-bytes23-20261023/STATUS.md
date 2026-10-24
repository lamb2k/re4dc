Done: The complete stat repair is saved and pushed. OFF identity, memory, census, bell and private QA checks pass. Source: 2a14662d4b025031cd93f64eed6a5d8159d473b7.
Doing now: Review the full Mendez comparison before landing. Both arms reach the exit; the camera control isolates the only required-field difference to 19 line-query counts, with zero movement drift.
Next: Land the whole qualified unit and enable its switch, then finish the four-fix audits23 unit.
Blocked / Needs the user: None for local integration; physical Dreamcast acceptance is pending.

Branch: wip/stat-bytes23-complete-20261023. Current integration: 933936ea7f45ba81c09277a780ed00111407aa23.
Shared-file changes: Main owns the stat unit, its separate landing tree, evidence and gate tooling. Source reviewer reads only. Frozen qualified trees stay unchanged. No recipe change has occurred yet. The camera-control branch is diagnostic only and must never be merged or shipped.

Qualification: Production H2 is 340/340 in both arms, heap_before 93,920 bytes each. KOS 48 KiB headroom is 6,112 / 6,176 bytes. GDEMU seed 1 passes. Census and TEXCHK pass all 27 rooms. Bell decisions match over 2,857 ticks. Mendez covers the two deaths, full s02/s10/s11, the observed normal window jump and room 10f in about 45 seconds. Its raw comparison remains MUST-DIFFER solely for 19 camera line-query counts; the legacy camera-predicate control restores MUST-IDENTICAL over 2,643 ticks. All other required fields match; zero player or enemy movement drift. Both arms' approach/jump/event-clear stills inspected.

Private disc: C:\Game Dev\Emulators\RE4DC-QA23-StatBytes-2a14662d. QA boot, menu warp, GDEMU seed 1 and H2 pass; QA heap_before is 48,768 bytes, distinct from the production image. No full-release or console acceptance, SD copy or publication is claimed.