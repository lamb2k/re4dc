#pragma once

// Default-off issue52 diagnostic. Source hooks pass integers only; the collector
// and crash renderer never dereference a candidate actor or its vtable.
extern "C" unsigned long re4dc_issue52_stage_base();
extern "C" void re4dc_issue52_actor_note(unsigned phase, unsigned frame,
                                         unsigned room, unsigned long actor);
