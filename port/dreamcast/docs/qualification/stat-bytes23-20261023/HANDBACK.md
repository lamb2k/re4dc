Complete stat-byte audit landed on t15/int a5e972e44096410253ad93164b84d92e3c22655a.

Done: The complete stat unit is landed and enabled on t15/int. Source unit 2a14662d4; landing a5e972e44096410253ad93164b84d92e3c22655a.
Doing now: The release watcher is rebuilding the landed recipe; the private QA disc is staged and Flycast-qualified.
Next: Priority 2 is audits23. Preserve stat evidence and inspect the watcher candidate programme identity.
Blocked / Needs the user: Physical Dreamcast acceptance is pending; no source integration blocker.

Branch: wip/stat-bytes23-complete-20261023. Current integration: 933936ea7f45ba81c09277a780ed00111407aa23.
Shared-file changes: Main owns the stat unit, its separate landing tree, evidence and gate tooling. Source reviewer reads only. Frozen qualified trees stay unchanged. The production recipe enables STAT_ROUTINE_BYTES=1; STAT_DIAG remains off. The camera-control branch is diagnostic only and must never be merged or shipped.

Qualification: Production H2 is 340/340 in both arms, heap_before 93,920 bytes each. KOS 48 KiB headroom is 6,112 / 6,176 bytes. GDEMU seed 1 passes. Census and TEXCHK pass all 27 rooms. Bell decisions match over 2,857 ticks. Mendez covers the two deaths, full s02/s10/s11, the observed normal window jump and room 10f in about 45 seconds. Its raw comparison remains MUST-DIFFER solely for 19 camera line-query counts; the legacy camera-predicate control restores MUST-IDENTICAL over 2,643 ticks. All other required fields match; zero player or enemy movement drift. Both arms' approach/jump/event-clear stills inspected.

Private disc: C:\Game Dev\Emulators\RE4DC-QA23-StatBytes-2a14662d. QA boot, menu warp, GDEMU seed 1 and H2 pass; QA heap_before is 48,768 bytes, distinct from the production image. No full-release or console acceptance, SD copy or publication is claimed.
Independent reviews: REVIEW-UNIT.md and REVIEW-MENDEZ-CAMERA.md, with exact pins. All captures, including failed early fixtures and test-only camera control, remain preserved. Source/host, target build, Flycast, full-release and physical acceptance are kept separate. No SD copy/publication.
