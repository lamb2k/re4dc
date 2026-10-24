RE4DC private normal QA23 dedup OFF - source 4be08e01
ROOT-REVIEWED PRIVATE CONSOLE PAIR; PHYSICAL ACCEPTANCE PENDING.
This is a private QA tool, not a release. No SD copy or publication performed.

Source: 4be08e0110592510e3630c01fa9f49b3ac2fed3d
Baseline: d5c1ceab9e06461462669b3ce1d28a379747a74a.
SCENERY_DEDUP=0; same standard DATA29 and original assets on both arms,
plus the exact same four compact ps2-dd3 alternate files. OFF0 uses originals;
ON3 selects the strict validated compact alternate. All original geometry,
UV/color/LOD/source identity and all 41 texture assets retained; no pruning.
Current audits four fixes ON, EM_READ_RETRY1, arena0; SELECT_ONLY/REPLAY_LEAN/
SUBMIT_BATCH1. Normal QA1/PC0, KOS/squeeze/census/diagnostic contamination0.
SCENERY_EMIT_PREFETCH=0 and SCENERY_SELECT_LEAN2=0 only. The separately found
experimental PREFETCH1 context defect is outside this qualified profile.
Production recipe dedup remains OFF pending root decision.

Programme dd234be08e01offqrW
Raw programme SHA256: dfdd3c2b3c38a8cafd95ba4a46a3acee12b2a50ec54a29f4bc2337bc4d48b8f7
Final standard GDI track03 SHA256: 52d2c05d1fa37d5d72546bb560cb317048540eb5ae1e97d6ae350aba9a0dc2a5
The delivered GDI has independent full track and all-file readback, both
loader/standard lint, actual final-GDI PID-targeted menu boot toR100 PASS.
Separately labelled proxies (same programme/all 14/data; only fixture-directory
redirection differs) pass QA menu->R103 and fullH2 1465/571/340 uploads/presents,
restored1. Normal QA s30 heap_before=48768 bytes.
These are bounded console-mode Flycast MODELLED safety checks, not physical
console acceptance or hardware performance. Standard non-QA matched H2
OFF 93,920 / ON 139,552 (+45,632 bytes), KOS 48 KiB all 8, required 10 GDEMU seeds, scoped census/texture/
VRAM checks, event common-window decisions and three held still views pass.
No blanket all-textures-zero claim: the known baseline Mendez late-pair
material limitation remains. Root's separate private PS2 upload repair is not
included or admitted here, and its visible use is unproven.

Compare with RE4DC-QA23-Dedup-On-4be08e01 using STEPS.txt.
README-tooling.txt is the unchanged historical QA-menu controls guide; this
README/IDENTITY give actual current provenance. MEDIA-IDENTITY.json preserves
the earlier mastering checkpoint; IDENTITY.json supersedes its pending-gates
status only within local tests. Root private-media review passed; production dedup remains off.
