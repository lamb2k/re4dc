#pragma once
// Test-only renderer isolation. The ordinary game has no declarations or calls.
#if defined(RE4DC_HOUSE_ARENA27) && RE4DC_HOUSE_ARENA27
extern "C" int re4dc_house_arena27_variant(void);
extern "C" int re4dc_house_arena27_active(void);
extern "C" int re4dc_house_arena27_model(const void* model);
#endif
