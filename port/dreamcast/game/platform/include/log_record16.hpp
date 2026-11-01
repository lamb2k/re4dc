#pragma once

// re4dc_log formats into one 256-byte automatic array. This is a bound for
// that producer only; re4dc_log_raw and the KOS device accept larger appends.
namespace re4dc::log_record16 {
constexpr unsigned max_bytes = 255;
constexpr unsigned capacity = max_bytes + 1;
}
