#pragma once
// GC_CENSUS_TRIM=1 (lane t2exact 2026-10-15, census #11): re4dc_coarse_actor_source / re4dc_coarse_ganado_source ask
// "is this cModelInfo pointer one of a static chunk table's elements?" for every native actor part (~25-165 calls a
// frame), and answered it by comparing the pointer with every element's address. The answer is the same from the
// table's address range: inside it on an element boundary is that element, anything else is no element.
#include <cstddef>
#include <cstdint>
template<class T, std::size_t N>
static inline T* re4dc_chunk_find(T (&table)[N], const void* p)
{
    const std::uintptr_t a = reinterpret_cast<std::uintptr_t>(p), b = reinterpret_cast<std::uintptr_t>(&table[0]);
    if (a < b || a - b >= N * sizeof(T) || (a - b) % sizeof(T)) return nullptr;
    return &table[(a - b) / sizeof(T)];
}
