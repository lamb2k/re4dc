# Private Audits arena challenge

Frozen code basis: `5e4de9a0262d3629c9833c959557de198b2e9f0c`.
This docs-only checkpoint gives the private QA programme a unique source label.
It changes no runtime source, asset, production recipe or default.

Private challenge overrides, appended to that basis's exact CH2:
```text
STAT_ROUTINE_BYTES=1 STAT_DIAG=0 EM_READ_RETRY=1 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 KOS_CACHE_P2_DIAG=0 VRAM_ROOM_ARENA=1 VRAM_ROOM_ARENA_NO_TOP=0 CACHE_LINEWISE=0 KOS_WATCH=1 KOS_SQUEEZE=1 PC_SAMPLER=0
```
Use the normal QA_MENU=1 profile, with WARP_AFTER_RESET and the ordinary QA
presets. Retain the committed DATA selection unchanged. One tree lease, one
shared build slot, JOBS=1; console-mode Flycast challenges use the existing
exact-child55-second bound and shared guest-pool/trace locks, one guest at a
time for this lane.

Safety before staging for the user: loader/standard disc lint, boot/QA warp,
full H2 including s30 340/340/restored1 with actual heap_before, and48KiB KOS
held/headroom challenges (both fragmentation modes). Preserve all failed
evidence and do not offer an unsafe build as accepted.

This is a new challenge built from the current frozen source and diagnostics.
It is not layout-identical to historical arena B/B3. No physical crash cause,
hardware acceptance or performance improvement is established by building it
or by a Flycast pass.

After local safety gates, the private console steps are: load the QA r101
cross preset, keep the same view/quality and cap4, fight/move through the
village for two minutes, and report any freeze, disappearing geometry or
allocation refusal. The user runs this physical-console challenge. No SD
copy, release publication or production recipe enablement is part of this
checkpoint.
