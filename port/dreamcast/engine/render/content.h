#pragma once
#include <stdint.h>
/* eng-look: run-time content steps for the owner's look calls (ENGINE_PLAN.md section 6). Step 0 of every item is
   today's full detail; steps 1, 2 and 3 are progressively lighter. The bench sets them per window from its schedule
   (".L2" and so on); the defaults are CONTENT_DEFAULT_INIT below. CS_GLOW is the source's frame-alpha glow (filter03), on unless a
   window says ".G0"; CS_PICK_CONTROL makes the engine's light pick wrong on purpose (the light-pick test's control). */
enum { CS_LEVELS, CS_WORLD, CS_CARDS, CS_EFFECTS, CS_BAKED, CS_GLOW, CS_PICK_CONTROL, CS_COUNT };
/* Owner-approved defaults (2026-11-19, "Lets go with best options" on the eng-look still sheets): character levels
   step 3 and effect cap step 2 are on by default; world cap, prop cards and baked lighting stay at step 0. A window
   can still ask for any step, including ".L0" and ".E0" for full detail, so console A/B runs keep their control. */
#define CONTENT_DEFAULT_INIT {[CS_LEVELS]=3,[CS_EFFECTS]=2,[CS_GLOW]=1}
extern volatile uint32_t m1_content[CS_COUNT];
/* per window: actors drawn at character level 0..3 [0-3], rigid far variants [4], flat cards [5], glow sprites [6], effects (E) or world pieces (W) dropped by the cap [7] */
extern volatile uint32_t m1_content_counts[8];
/* the pack's distance-variant table (section 14 after the sky words; empty is valid) */
int content_variants_open(const uint8_t* p,unsigned n,unsigned models);
