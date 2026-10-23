# Completed-window whole-frame wall measurement

This private default-off successor extends source2158. It changes neither the
sample selection, 600-iteration cache lease nor the cache/storage arithmetic.
A is normal cache/RAM; B is reduced cache/RAM; C is reduced cache/OCRAM records.
The original 100-byte, 25-word status snapshot stays version1 with unchanged
field offsets. A separate 128-byte version1 MeterSnapshot and bounded coherent
read accessor expose whole-period measurements. Existing frozen programmes and
their address/ELF-pinned readers stay unchanged. A newly linked successor must
bind its own actual symbol addresses/ELF hashes; source compatibility does NOT
authorize reusing2158 absolute addresses in a different image.

## Exact clock and window

Use the existing monotonic KOS timer_us_gettime64, once at the earliest statement
of re4dc_ui_begin or re4dc_ui_begin_skip. No vertex/meshlet timers are added.
src/game/main.cpp calls Render_before (which calls UI begin), then Render,
TaskScheduler, Trans, watchers, sound, UI/effects, iTaskScheduler, Render_done,
frame waits and Render_swap (which calls UI end), followed by pacing/vsync/tick
tail work. Measuring earliest begin to the following earliest begin therefore
includes each whole frame period exactly once, including that later tail and
the final scratch end-guard restoration. Existing render_end and WORLD_METER
remain subset diagnostics and never establish this result by themselves.

The first selected period starts BEFORE cache entry. Its clock candidate must
already name the same nonzero loaded room when the existing scratch begin
acquires a token. Every next period must retire exactly one real engine token
and frame, in the same room and arm, with no faults/live token/missing pair.
Normal UI begins count as drawn-path periods; skip UI begins count as skipped
periods. Drawn-path count does not certify a displayed picture or successful
flip. Total wall_us equals draw_us plus skip_us exactly, with no overlapping
subset sum. These are WALL PERIODS INCLUDING PRESENTATION/PACING/VSYNC WAITS,
interrupts, diagnostics and ordinary timer/publication overhead, not CPU-only
work. Do not run menus, still holds or other pauses during a performance sample.
Keep camera/pose/assets/culling/pacing/diagnostic settings matched across arms.

The engine's600th end restores ordinary mode before returning. Its old status
can then correctly say runtime complete, while the new record is still PENDING
BOUNDARY with599 closed periods. Only the following same-room earliest begin
can close period600 and publish COMPLETE, after restored CCR/entry-exit balance
and the original no-fault runtime completion predicate hold. A room/movie/cancel
or owner/deferred-cancel crossing this interval invalidates measurement. Missing
ends, live consumers, stale tokens, clock regression or incomplete600 also
invalidate; they cannot rearm or later become complete. Later contexts do not
rewrite an already completed record.

Entry/exit microseconds are shown SEPARATELY FOR CONTEXT, ALREADY INCLUDED IN
WHOLE WALL TOTALS. Never add them again. No per-frame or per-meshlet cache-mode
toggle has been introduced. The completed arm remains C after mode A restores;
the record explicitly shows completed arm, selected room, periods/drawn/skipped,
borrows/faults, restored CCR, total/drawn/skip/max wall and entry/exit durations.

## Diagnostics and evidence scope

Only WORLD_SCRATCH=1 gives qa_menu.o its private flag/header dependency. Its
Diagnostics rows show the completed selected arm separately from the live FPS
and ordinary WORLD_METER rows. ACTIVE, PENDING BOUNDARY and INVALID are explicit;
they are never completed performance results. No production/default/recipe,
actor, allocator, original cache helper or packet-reservation change is made.

run_tests.py exercises the actual portable Engine/runtime wrapper and formatter:
all A/B/C600-period totals, alternating drawn/skip, final-tail/restoration cost
included once,64-bit accounting, pending final boundary, room/cancel/foreign
owner invalidation, missing/stale/live token/clock failures, immutable completed
arm and coherent-reader odd-sequence refusal. Existing scratch byte, ownership,
late-selection and admission controls remain. The old/successor default-off
runtime object bytes match; old/new Diagnostics preprocessing matches with
WORLD_METER0 and1; Make verifies the QA flag appears only when scratch is enabled.
These are focused HOST/source checks, not a target/full-programme identity,
linked ownership/memory, guest/image or physical Dreamcast speed result. Main
owns those gates and integration, including any future combined actor image.

The completed-only log uses two lines: WS23 wall-time and WS23 wall-state.
Both repeat serial, completed arm and room so a retained line cannot silently
inherit another context. The real logger has a256-byte vsnprintf buffer. Actual
production format/argument expressions are tested through that exact buffer
contract with every unsigned at UINT_MAX and every timing at ULLONG_MAX:252 and
170 bytes including newline (plus NUL), so neither line truncates. No per-frame
logs were added; both completion lines are emitted after the measured window.
