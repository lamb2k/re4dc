# Event pool storage flags candidate

The normal Event pool allocates two byte-cleared slots without constructing Events.
Manager/free scans previously accessed polymorphic Event members before lifetime
began, and two deletion paths wrote a member after destruction. Address retention
alone does not preserve object lifetime.

EVENT_MANAGER_STORAGE_FLAGS defaults to zero. Enabled native builds specialize
only Event flag bookkeeping: unsigned-byte storage plus builtin memcpy load/store
and read-modify-write. The compiler supplies the cUnit flag offset; the actual
Event offset and four-byte width are checked independently. All template raw/dead
slot flag accesses, the three alive predicates and four direct EventMgr scans use
this policy. Other managers preserve their original typed/custom predicates,
including cSat. Event layout, destructor visibility, full post-destruction zero,
list ordering and deferred deletion timing remain unchanged.

Every game/platform translation unit gets the same enabled define to avoid mixed
Event template policy. Use a fresh object directory when changing flags. No
production recipe/default change or new programme/image is part of this unit.

## Qualification

Baseline: 720b75381a68f51636b17031f82fd762e72e05d3.
Actual full Event TU: baseline, omitted and explicit-zero stripped objects match
2d56ee8247dc (full SHA and commands in event-storage-event-sh4.json). Enabled TU
compiles, object122043209520; text grows560 bytes, data/BSS are unchanged. This is a source/object gate, not full-programme cost.
Actual full game TU: baseline, omitted and explicit-zero preprocessed tokens and
stripped objects match667f656646cc; enabled game object also matches. Global game
and platform define propagation and Make rejection of2/-1/yes pass.

Retained attempt01 had a missing generated forced header; attempt02 completed
Event gates then stopped at the unchanged game baseline lacking RE4DC_DOORPH.
The Makefile's DVD safety conditional supplies that required door_probe header.
Attempt03 uses DVD_READ_SAFE=1 and PVR_PIPELINE=1 in every arm; no ad-hoc macro or
source fix was used. Those qualification inputs do not change production recipes.
The second receipt records the accepted game gate and first Event receipt.

Independent actual-source strict-vptr lifecycle fixtures are pending. Allocation,
heap reset, active-object/reader epochs, other managers, yielding constructors and
stale handles remain separate audit obligations. This does not establish issue52's
hardware cause. No linked programme, guest, release or Dreamcast acceptance.

Evidence: /root/probe/cache21-event-storage-qualification-20261022-{01,02,03}.
All failed attempts are preserved. The object unit has a32MiB aggregate cap and
18GiB+64MiB+32MiB C: admission floor; global build slots and one tree lock apply.
