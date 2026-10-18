# Shared pose service, phase 1B

The approved first client is chapter-1 Ganados in r101/r103, followed by Leon's
pose and bosses. Controllers, clocks, root movement and event dispatch stay with
the source game. The service must keep gameplay dependencies current each tick
and finish visual-only bones once the current image decision is known. It must
preserve the existing bone-matrix interface. Character drawing belongs to
chardraw18.

## Foundation status

`engine/pose_service.{c,h}` supplies a bounded EDCL reader, masked local sampling,
parent/procedural dependency closure, ordered masked override layers and affine
composition. There is no fixed runtime bone count, allocator, global pose cache,
actor clock, source controller or drawing dependency. Callers own storage and
may share immutable clips while retaining independent actor phases. EDCL v1's
8-bit on-disc bone count is an inherited format limit, not a service limit.
Scale tracks, shortened last key segments and multiple roots are supported.

The foundation is not connected to gameplay or included in a game recipe. No
in-game gain, STRICT result, off-identity result or gameplay acceptance is claimed.
The old GAME_LOCOMOTION_POSE cross-enemy cache remains rejected and disabled.

Validation on 2026-10-18:

- 41,644 host checks across 153 clips (152 retained em12 clips and one synthetic
  fixture), maximum component difference 0.000087705 versus the Python codec
  oracle. This establishes decode/mask/math behavior, not source MotionMove
  equivalence.
- Separate ASan/UBSan truncated-allocation and per-byte mutation probes pass.
- SH-4 GCC C11/O2 compile with fast math disabled and warnings as errors passes:
  4,725 bytes text, zero data/BSS. This is an object compilation, not a linked game
  or Dreamcast timing result.

## Integration contracts still to qualify

1. **Pose stage:** the imported demo baker samples after offline IK and the model
   blend table. Its host IK has no live floor collision. A live pre-IK adapter must
   explicitly request and identify source-local clips; feeding demo clips through
   live IK again would solve twice. Keep legacy demo bytes unchanged by default.
2. **Source fields:** MotionMoveCore updates Euler channels, flags and key history.
   A quaternion-to-matrix sampler does not by itself maintain those contracts.
   AddRot, flips, blend/hokan, nonuniform parent scale cancellation, attachments,
   dead-body compression and procedural IK need explicit handling or source
   fallback. Generic affine composition and nlerp are not source equivalence.
3. **Dependencies:** derive each action's required closure from hit volumes,
   attachments, live IK, blends and external readers. Demo head/hand chains are
   insufficient evidence. updateOldPos's collision histories must remain valid.
4. **Cadence:** TaskScheduler runs before re4dc_pace_decide_image. The skip flag
   during logic describes the preceding prepared image. Do not use it as a guess
   for whether this tick's skeleton will draw; visual completion needs the actual
   current decision before Trans without rerunning clocks or events.
5. **Residency:** the retained em12 demo archive is 1,693,968 bytes. Do not silently
   load it on top of source motions. Measure active-clip metadata, scratch space,
   archive sharing and heap-4 residency before choosing a runtime pack.
6. **Math:** start with this reference implementation. Use the pinned SH4ZAM
   adapter only where target measurements and numerical/feel gates establish an
   advantage. No library-wide fast-math or speculative assembly is needed.

The first live implementation requires one default-off knob, off-image identity,
STRICT/decisions comparison first, then the approved gameplay-equivalence and feel
checks where quantization changes results. Timing must identify build, r101 cross
window and MODELLED units. Farm idle/work coverage is retained separately from a
normal-input fight. Leon's controller/input/aim/camera and boss controllers are
outside this first client.
