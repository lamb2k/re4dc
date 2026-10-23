#pragma once
#include <cstdint>

struct Re4dcModelDirect;

// Borrowed only by one synchronous scenery chunk replay. Each logical part
// still ends normally; sq retains only the original SQ lock's base address.
// Reusing that base preserves the ordinary per-part address/window limit.
struct Re4dcWorldSubmitBatch { std::uint32_t* sq=nullptr; };

extern "C" int re4dc_ps2_world_direct_begin_batch(const unsigned*,Re4dcModelDirect*,Re4dcWorldSubmitBatch*);
extern "C" void re4dc_ps2_world_direct_end_batch(unsigned,Re4dcWorldSubmitBatch*);
// Close only between logical parts. A live direct part must end first.
extern "C" void re4dc_ps2_world_batch_close(Re4dcWorldSubmitBatch*);
