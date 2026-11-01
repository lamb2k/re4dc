#pragma once
// Internal completion contract. Queue publication is ownership transfer, not
// presentation: a later frame abort can still discard accepted FIFO packets.
// Existing int entrypoints remain ABI wrappers; no result retains source data.
namespace re4dc {
enum class NativeDrawOutcome : unsigned {
    Submitted, Queued, Culled, PolicySkip,
    UnsupportedBeforePublication, Refused, PartialAbort
};
struct NativeDrawResult {
    NativeDrawOutcome outcome;
    unsigned submitted = 0, queued = 0;
    bool published() const { return submitted || queued; }
    bool complete() const {
        return outcome != NativeDrawOutcome::UnsupportedBeforePublication &&
               outcome != NativeDrawOutcome::Refused && outcome != NativeDrawOutcome::PartialAbort;
    }
    bool fallback_allowed() const {
        return !published() && (outcome == NativeDrawOutcome::UnsupportedBeforePublication ||
                                outcome == NativeDrawOutcome::Refused);
    }
};
// Stop at the first failed child. Already accepted packets cannot be replayed
// by a whole-producer fallback, even if later children have no output.
struct NativeDrawProgress {
    NativeDrawResult result{NativeDrawOutcome::Culled};
    bool add(NativeDrawResult child) {
        if (!result.complete()) return false;
        result.submitted += child.submitted;
        result.queued += child.queued;
        if (!child.complete()) {
            result.outcome = result.published() || child.outcome == NativeDrawOutcome::PartialAbort
                ? NativeDrawOutcome::PartialAbort : child.outcome;
            return false;
        }
        if (result.queued) result.outcome = NativeDrawOutcome::Queued;
        else if (result.submitted) result.outcome = NativeDrawOutcome::Submitted;
        else if (child.outcome == NativeDrawOutcome::PolicySkip) result.outcome = NativeDrawOutcome::PolicySkip;
        return true;
    }
};
}
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
struct Re4dcEffectQuad;
struct Re4dcEffectMesh21;
struct Re4dcEffectSprite;
struct Re4dcWaterLayer;
// Sprite counts are one submitted packet or copied FIFO/RTT packet. Water
// counts are one layer once its header is sent, or one accepted WaterNode;
// vertex/chunk/pixel counts and eventual presentation are separate facts.
extern "C" re4dc::NativeDrawResult re4dc_effect_sprite_result(const Re4dcEffectSprite*);
// Legacy water admission can be true even if direct emission is empty/invalid.
// Copy it independently when the caller must preserve that original contract.
extern "C" re4dc::NativeDrawResult re4dc_water_layer_result(const Re4dcWaterLayer*,int* legacy_admitted=nullptr);
extern "C" re4dc::NativeDrawResult re4dc_effect_quad_result(const Re4dcEffectQuad*);
extern "C" re4dc::NativeDrawResult re4dc_effect_mesh21_result(const Re4dcEffectMesh21*);
#endif
