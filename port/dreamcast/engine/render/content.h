#pragma once
#include <stdint.h>
/* eng-look: run-time content steps for the owner's look calls (ENGINE_PLAN.md section 6). Step 0 of every item is
   today's full detail; steps 1, 2 and 3 are progressively lighter. The bench sets them per window from its schedule
   (".L2" and so on); nothing here is a default. CS_GLOW is the source's frame-alpha glow (filter03), on unless a
   window says ".G0"; CS_PICK_CONTROL makes the engine's light pick wrong on purpose (the light-pick test's control). */
enum { CS_LEVELS, CS_WORLD, CS_CARDS, CS_EFFECTS, CS_BAKED, CS_GLOW, CS_PICK_CONTROL, CS_COUNT };
extern volatile uint32_t m1_content[CS_COUNT];
/* per window: actors drawn at character level 0..3 [0-3], rigid far variants [4], flat cards [5], glow sprites [6], effects dropped by the cap [7] */
extern volatile uint32_t m1_content_counts[8];
/* the pack's distance-variant table (section 14 after the sky words; empty is valid) */
int content_variants_open(const uint8_t* p,unsigned n,unsigned models);
