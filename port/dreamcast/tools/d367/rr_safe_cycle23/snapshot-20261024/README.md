# Historical source and evidence snapshot — 2026-10-24

This archive preserves root's completed **one final-GDI console title boot** and its source/metadata trail. Runtime adapter source remains exact `34a5c48bfe22c3d9718810166407048a906b8bcc`; candidate source is `fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2`. No runtime code or recipe changes accompany this snapshot.

Root's actual console child PID8704 had an observed upper duration8.265999999945052 seconds under55. The saved launch config explicitly sets FPS=yes; title goal, five-second grace and no-error checks passed, separately from process bounds. `ROOT-EXECUTION.json` and `ROOT-DELIVERY.json` record that result. Candidate metadata was accepted under canonical rr.lock; programme/all14, assets, four tracks, recipe and QA ZIP stayed unchanged. The new candidate IDENTITY hash is `2e43f6f01573a604e323287e6e4134824b093daeec0cc31bbd559fd592132fab`.

This is title-log evidence only. It does not establish a fresh full quick/QA cycle, New Game, visible pixels, route progression, physical-console behavior or performance. The installed cron's old quick/QA passes remain separate legacy-profile evidence. No activation beyond this one boot follows.

The sequence is retained: historical2c6 source review, explicit-limited successor and semantic bad-read repair, V2 Windows alias refusal before any guest, V3 relocation/read-only Windows49-pin pass, independent source/binding reviews, root's49-input/75-member admission, actual boot, separate judges and metadata acceptance. `ROOT-ADMISSION.json` contains the timestamped root status at admission; it is not a claim about the current cron state.

## Contents and preservation

`root-helpers/` contains exact exported admit/execute/prepare/accept source. These are historical records with real side effects if run; this snapshot does not authorize replay. `runtime-v3/` retains pending/approved configs and the completed lease record; that historical lease grants no current ownership. `preparation/`, `inventories/`, `refusal-v2/`, `acceptance-v3/` and `capture-metadata-only/` retain small metadata/review/config records. No archived helper was imported or executed while exporting.

The approved config intentionally contains **before-acceptance metadata pins**. Root preserved those exact old bytes privately before updating the candidate. `HISTORICAL-INPUT-BINDINGS.json` binds those originals and their before/after hashes. Do not replace old pins with new candidate metadata or rerun that historical config as though it were fresh admission.

Game logs, binaries, assets, VMUs, disc/capture media, screenshots, full game-file manifests and original candidate backup contents are omitted. `PRIVATE-EVIDENCE-PINS.json` and the retained configs pin referenced private bodies by path/hash only. Original evidence, source units and reviews stay untouched; current lane STATUS/HANDBACK snapshots are explicitly timestamped.

## Physical bytes versus Git LF bytes

Worktree exports initially copied source bytes exactly. This directory explicitly stores text as LF in Git. `EXPORT-MAP.json` records each original physical SHA256/size and each Git LF SHA256/size. Eight actual source records normalize; their Git blobs are **not** claimed byte-identical to the physical originals. Reversible zero-based CRLF newline ordinals allow exact physical-byte reconstruction, including mixed endings. The map also records any UTF8 BOM; it is retained.

Run only the verifier to check this archive:

```
python3 -B verify_export.py --revision HEAD --out /NEW/EXCLUSIVE/receipt.json
```

`--revision INDEX` verifies a staged export. It checks every actual Git blob, reconstructs each original physical digest, and catches broken-digest/missing-newline-map mutants. It does not access private evidence or execute archived helpers. No SDK, emulator, asset conversion, extraction, cleanup or candidate edit is involved.

Actual capture configs retain their intentional trailing blank lines; the local whitespace rule permits those archival bytes rather than trimming evidence.
