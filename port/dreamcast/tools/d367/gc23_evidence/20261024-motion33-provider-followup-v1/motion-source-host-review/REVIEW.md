# Bounded source review CLEAR — Motion UNKNOWN detector

Reviewed implementation `fce285ddd77ced898b40f49ae310b91a539b7b5d` and test-only
successor `5e6b7d8c0f76e7431f1a7787459faa41fb0b507c` against base
`870789095c4c14fbdbf22043447b249063d2ec3a`. Read author STATUS, the entire actual
diff and surrounding accepted-output/lifecycle code. Later clean HEAD
`aab201ceac0e18107f64a3212398afe916793327` changes only Motion docs/host summary;
runtime and executable test inputs are byte-identical to the reviewed freeze.

No remaining actionable source defect found within the explicitly partial scope.
Reviewer changed only this review directory. No SDK, guest, build recipe, target
object, assets, live process control, programme integration or author edits.

## Accepted-output ownership

* Model gateway, fast actor and one_chunk scopes supply fixed ModelPose|ViewTrack
  Unknown, preserving only the explicit delayed reason. Source prelit/rigid/null/
  stopped motion, skin/frame hits, owned/coarse/hand/registry/split geometry never
  grant Motion identity or N/A. Geometry SourceUse/ReplayUse and their allowed
  masks remain independent and unchanged.
* Packet prefix/final accounting occurs inside actual nonzero packet acceptance,
  before Geometry's quad early return. Direct accounting supplies its explicit
  record count; the existing subsequent Geometry no-argument call has count0 and
  does not count again. Header-only/zero-output/reservation/cull paths add none.
* OneWindow owns every nonzero chunk prefix before possible abort and context
  change. Aggregate close and successful Leon material switch mark those records
  already accounted. Failed switch retains that marker for close. Successful
  switch consumes it and the following prepare replaces pending context. Capacity
  close/reopen follows the same ownership. Ordinary direct intervals retain their
  own count. Later transaction failure cannot subtract an accepted prefix.
* Accounted is not a valid incoming reason. Only the two actual local-accounted
  guards can install it. Nonzero acceptance consumes it once and changes pending
  to MissingRoute; later unprepared output is Unknown. Zero output is a no-op.
  Fresh prepare replaces even an unconsumed marker. There is no zero-reason
  suppression path or positive/unknown-to-N/A conversion.
* Actual merged model_bridge::flush covers cached concat, newly built concat,
  fallback individual lists and a single list with fixed delayed Unknown; a
  cancelled Pending returns before output. Generic native_model and deferred UI
  model-node replay preserve that fixed classification under unrelated ambient
  state. No current owner/source lookup or per-node/cache fields were introduced.
* World/impostor model leaves use fixed UnclassifiedWorld|ViewTrack when outside a
  model scope. This is uncertainty about consumed transforms, not an assertion
  that every world vertex was externally animated. Actual external camera-track
  lineage remains unqualified; code camera math is not claimed as an asset use.

## Safety, state and old-visit attribution

The helper has exactly six unsigned words, raw host size24B with a source static
assert. Its only undefined provider imports in the checked host object are log
and unresolved, both called solely by flush. The accepted functions sanitize/OR
bits and perform saturating integer updates; no hash, catalog/FS, allocation,
scan, callback, wait, or lock. They remain memory-only with protected-context
tripwires active. OneWindow adds a local4B flag; RAII saves a4B word per scope.
These stack costs are separate from the24B resident state; nested scopes are not
a claim of total stack usage. Target code/layout/stack pricing remains pending.

gcasset_flush drains Unknown before member/audio/catalog work and before old visit
END. Startup, transition and room ownership use existing safe boundaries;
end-frame flush is a function-scope destructor, after nested scratch-end scopes
and renderer work retire. No flush is inserted in accepted SQ/G2/LH paths.
Counters survive abort/model_handle clearing, and old counters reset only after
their safe diagnostic. Logging remains an unresolved Motion failure; accepted
record/event totals are not unique assets/evaluations. Exact maximum vs first
overflow and sticky saturation were independently exercised. The bounded new row
fits the actual256B logging buffer at maximum tested counter widths.

## Default-off and test adaptation

Strict default0 knob accepts only0/1; enabled requires GC_ASSET_GATE1 and fast
native actor. Gate's existing PVR_STREAM/AICA prerequisites still apply. Flag
propagation reaches both platform and game/model_bridge code; the helper is
filtered from the OFF link object list. Helper header rejects invalid values and
Motion-on/Gate-off. Existing dependency generation covers its new header.

Reviewed preprocessing/token comparisons for five changed runtime units under
Gate0/Motion0 and Gate1/Motion0, plus an empty OFF helper object and exact24B host
state/import controls. This is source/host default-off evidence, not a target
object, full image or production byte-identity claim.

The first full fce sweep's historical raw-UI equality failure is preserved. The
5e successor changes tests/docs only. Its strict projection removes exactly one
new include and exactly six specified guarded blocks (the direct-count block
occurs twice), then retains complete historical raw source equality and the
Motion-required mask. Ungated-call, wrong-guard and removed-Motion-mask controls
reject. There is no wildcard stripping or runtime weakening in this adaptation.

## Independently executed controls

1. Ten focused author methods rerun independently: PASS10.298s. They execute
   extracted helper, OneWindow close/chunk, Leon switch interval/block, actual UI
   prepare/packet/direct/quad/flush/END/startup, model_bridge merge and gateway,
   strict Make/header admission, helper import/state and OFF token controls.
   Thirteen compiling runtime mutants and three strict projection negatives are
   included. Surrounding renderer/platform providers are mocked; no actual Render
   session is implied.
2. Eight additional reviewer schedules passed against those actual extracted
   production bodies: nested frozen/restored scope, successful switch with zero
   following chunk, failed switch/repeated close/later output, empty close,
   zero-count then fresh prepare, forged internal-bit mixtures, exact maximum vs
   overflow, and flush preserving pending/scope. A compiling reusable-marker
   mutant was defeated. Eleven extra Make cases cover malformed knobs, disabled
   actor/gate/stream/audio and the admitted positive. Final reproducible run0.880s.
3. Read back author's exact full-sweep receipt and four-member hash manifest:
   118 discovered/117passed/1historical optional skip, complete C++tail exit0.
   That broader sweep was not independently rerun here. Its source pins agree
   with frozen Git5e. The prior failed fce receipt remains separate.

INDEPENDENT-CONTROLS.json binds exact source pins and additional outcomes.
independent_controls.py writes only its review receipt and uses transient RAM
fixtures. It checks the source stays clean and runtime/test inputs remain frozen.

## Explicit remaining gates

Required mask3ff, wired mask1f6 and emitted_checked(Motion) hard refusal are
unchanged. No Motion token, source-positive slots, digest table, N/A, no-GC-use,
provenance or completeness claim exists. Raw TR/lake, modifier/blob shadows,
alternate nonfast/world/coarse raw emission and other effect/screen routes are
not closed by this unit. Nonfast actor is refused by Make; other combinations
remain explicitly partial and cannot satisfy wired coverage. Do not advertise
all accepted routes as observed. Source/host CLEAR does not authorize a runtime,
SDK, full-programme integration, I001, appearance or hardware acceptance.
