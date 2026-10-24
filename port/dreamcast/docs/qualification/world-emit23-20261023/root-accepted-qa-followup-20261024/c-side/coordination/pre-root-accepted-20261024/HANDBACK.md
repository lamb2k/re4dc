# Private WorldEmit QA media handback — 2026-10-23

All allocated work is complete. The pair is sealed for root review; it is not production ready and no physical-console acceptance or speed gain is claimed.

Source/helpers: wip/interior-vis23-20261023, clean pushed bf81d1967. The programme source remains the clean isolated 49ad20f9932d638ddb7becf5db6f86b92e0a76a2 tree. No shared runtime, current recipe, generic stager, old qualification output or production DATA was edited.

Final destinations:
- C:/Game Dev/Emulators/RE4DC-QA23-WorldEmit-Off-49ad20f9
- C:/Game Dev/Emulators/RE4DC-QA23-WorldEmit-Both-49ad20f9

Each has standard raw2352 gdemu/disc.gdi and tracks, README.md, STEPS.md, IDENTITY.json and SHA256SUMS.txt. Actual combined final size is 2,376,208,884 bytes. No ZIP, publication or SD copy was made.

Evidence: C:/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9/final-qa-stage.
- FINAL-PAIR-HANDBACK.json SHA256 86609ae3b217369c7bb34dd898fd4edbc614f7a7fc0c530df9a25b15270c72f0.
- EVIDENCE-SHA256-MANIFEST.json SHA256 5ebcd7f638fc62c7ab9a0c87e98e91f45718fcad4582f2ae10007ebb20b5084f.
- Programme evidence seal 07c9bc1e180a70aa5a85fe7235a6a546881270971406d24f5ccbf9dcefc33c64.
- Sealed plan SHA256 c1f8b00a68b1f5149746852c05e3982d2a0aebfae85f9af49d396cd61b951baf.

| Flycast console QA check | Off | Both |
|---|---|---|
| Actual final GDI ordinary-input boot, 33 presets | PASS; 25.985 s child | PASS; 25.984 s child |
| Automated QA menu-warp fixture proxy, exact reset/new room chain | PASS; 21.906 s child | PASS; 21.906 s child |
| H2 fixture proxy, full 340 uploaded and presented, matched arena return restored | PASS; 33.000 s child; heap_before 40576 B | PASS; 33.016 s child; heap_before 44448 B |

Six guests only, one at a time, own lease then stat3 then trace16, Windows-verified console mode and exact55s child cap. No cap fired; no critical log rows. These child durations are run bounds, not game performance. The normal QA H2 heap values are actual observations, not production-floor or KOS squeeze/watch acceptance. No QA Mendez test was allocated or run.

The automated menu fixture proves initial101/gen1, active QA UI with33presets, exact /cd/dc/qa/r103.txt auto request, reset request/start, exact fixture load/preset arm, reset end and new103/gen2 in order. Six narrow wrong-file/reset/stale-generation/UI negatives are rejected. The original OFF new-checker FALSE receipt is preserved, with an offline source-linked corrected receipt; no guest was rerun for this parser-only correction. The actual manual key-targeted final-GDI boot is a separate result. No manual progression is inferred from the automated fixture.

Each actual final GDI passes independent readback of all1747 files, main/all14, raw-main-to-scrambled-programme equivalence, standard34QA text files, candidate and tex.pak, plus standard and loader lints. Between arms exactly15 programme files differ; all game assets and menus are identical. OFF exactly reproduces fresh unmodified current QA main/all14; the resolved pair differs only in SCENERY_SELECT_LEAN2 and SCENERY_EMIT_PREFETCH. Both options remain off in production. Quality5*far4=20, cap4, all four audit fixes, STAT1/EMretry1 and all other source knobs are retained.

The shared private PS2 file is the sole game-asset addition, 32912 B SHA256 18978dc1b97247dcd5fda5f5f1744b74e9d1b97c34dc5779977525b0a2dc477e. It is LOAD/UPLOAD REPAIR ONLY. Actual visible use is unproven and Mendez hair appearance is not production approved. All original assets, all41Ganado textures, and tex.pak are retained; no GC pixel/geometry fallback is enabled. Root's separate source gates and candidate B-t result are not promoted to QA Mendez acceptance.

Only the two newly owned disposable proxy track03.iso files were removed, after their arm passed and actual final tracks were freshly rehashed. Exact resolved-path/hash deletion journals, base manifests/SHA/IP, fixtures, programmes, source/tool byte archives, logs and all captures are retained. No prior evidence/base was deleted. Fresh lower Windows/WSL C free at seal was33,399,541,760 B (31.11 GiB); stage admissions/floors are in the sealed evidence. No owned build/guest slot is held.
