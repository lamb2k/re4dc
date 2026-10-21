# AICA layout failure recovery (separate candidate)

`AICA_LAYOUT_RECOVER=1` defaults to zero and requires `AICA_AUDIO=1`. It is a narrow recovery candidate on c7e0358a, separate from the already built six-knob cache successor. No production recipe, image or saved state changes here.

## Failure and resulting behavior

The original first-layout loop increments `g_aicaUsed` as it allocates slots. If a later allocation fails, it frees earlier slots without subtracting their accounted bytes. The next attempt can refuse an otherwise-fit layout despite zero allocator-held layout bytes. Enabled code keeps newly allocated slots private until all succeed, frees exactly this attempt's allocations on failure and subtracts their aligned owned byte total. Existing owners' allocations/accounting remain intact. It publishes the same slot order and sizes on success.

A separate failure occurs after all one-shot slots succeed: stream-ring allocation can fail after `g_layout` becomes true. Later banks then reuse the valid layout without retrying the missing ring. Enabled code preserves that one-shot success and retries ring readiness independently, at most once per second, at a later bank admission or the existing stream-reader loop. A failed retry neither frees banks nor changes stream generation, source registration, voices or I/O attribution. Success allocates the same original ring once. It is not a new stream or payload tier.

The retry checks aggregate accounted AICA use against the same pool/movie-reserve budget, then uses the existing KOS allocator; fragmentation or other owners may still refuse it. It does not evict other owners or lower reserves. A budget refusal is also rate limited. Reader retries take `g_lock`; the original bank ARQ path already holds it around native admission. The helper itself expects this lock. The allocator lock order remains `g_lock -> snd_mem` as in ordinary bank admission; the KOS `snd_mem_malloc` implementation uses its own mutex and metadata allocation, with no callback into this backend. This source check and the serialized host test do not establish whole-system lock-order acceptance.

## Source and target-object checks

`python3 port/dreamcast/tools/d367/cache21/test_audio_layout_recovery.py --out <directory>` extracts the actual original and modified layout/helper functions. ASan+UBSan pass **396 assertions**: normal and repeated success, mismatched-header reuse of working slots, all nine slot failures, sparse/aligned slots, existing unrelated ownership, an owner accounting change during a failed allocation callback, no partial publication, retry, aggregate budget refusal, throttled ring failure/recovery and two serialized bank/reader threads and competing initial bank owners. It also checks the real ARQ/reader lock callsites. Capacities and allocator/timer are synthetic; the original one-shot/stream backend and physical console are not run by this fixture.

The exact retained QA SH4 audio translation-unit flags compile off and on successfully. Debug-stripped off object is byte-identical to original (`53c6959766087789e313c23d02b52cefda418cbce314693b674ce3d8846a989b`). Unstripped/preprocessed files differ only in the existing `__LINE__`-generated local G2 lock names/debug information. Enabled change: **+371 B text, +8 B BSS, data unchanged**. Target `-fstack-usage`: ARQ frame180 ->252 B (+72 B pending slots), stream reader remains64 B, new helper12 B. These are per-function static frames, not total task/thread stack bounds.

Machine receipt: `audio-layout-recovery-validation.json`. No full linked program, default-off whole-program/overlay identity, KOS squeeze, whole-call-chain stack bound, native output or target fault recovery is qualified here. These are integration gates before use.

## Limits retained

- This does not fix failed source sound-header registration, repeated invalid module admission, native prebuilt replacement validity, stream-index failure/restart, or any effect/emitter teardown issue from A10-A13.
- It does not establish that either allocation failure occurred in the reported console shooting slowdown. No per-shot I/O or speed gain is claimed.
- Working/playing bank payloads, source bank IDs/flags, sound/voice behavior, movie reserve, ring size, normal read callers and stream-thread meter tagging remain unchanged by the patch. Target playback still needs verification.
- Fresh integration must explicitly enable the single knob and preserve old candidate/state lineage. Current frozen QA and the existing successor exclude this repair.
