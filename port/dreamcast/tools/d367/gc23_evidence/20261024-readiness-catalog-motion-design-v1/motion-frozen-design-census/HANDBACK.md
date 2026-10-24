# Bounded handback

Use ROUTE-MAP.md for actual routes and MINIMAL-API.md for the root decision.
SOURCE-READBACK.json binds 36 actual a132 source files and line anchors, plus
eight read-only source-fact controls and eight detected counterfactual edits.
The readback control is explicitly not a Motion detector or renderer execution.
Reproduce source readback only with:

    python3 -B /mnt/c/Game\ Dev/Emulators/codex-lanes/gc-port23/motion-unknown-census/readback.py

Recommendation: first instrument fixed UNKNOWN accepted-output classifications,
independent of Geometry, with zero per-SkinEntry/Frame/pose metadata or new source
slots. Fixed Unknown remains Unknown through caches, owner/hand/split variants,
merged/deferred models and impostors. It never asserts a specific external Motion
asset was consumed and never grants static N/A from null/stopped current motion.

Source-specific pitfalls for implementation: OneWindow needs exclusive per-chunk
prefix accounting; direct aggregate close cannot count/attribute it again. Leon
header switch must account previous pending interval first. Quad-batch Geometry
early return cannot bypass Motion. Generic prepared/merged and delayed replay
cannot acquire Motion identity from the replay-time current model. Existing
unresolved/emitted_checked(Motion) logs and is not a protected acceptance API.

Parent confirmed external camera tracks are in scope. Baked object geometry
does not prove view-track history was overwritten. Do not infer Motion from
every geometry token, nor exempt every raw/screen-space/UI output; audit actual
inputs and retain incomplete coverage for unresolved alternate routes.

No target objects, full preprocessing, SDK, assets, guest, counter values,
no-GC-use result or runtime allocation was produced. Game/source tree stayed
clean. All new artifacts are confined to this directory.
