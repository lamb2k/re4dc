// svc_census.h: the census interface shared by the PC side (svc_trace.cpp) and the game side (svc_glue.cpp)
// of re4ref's service census build (lane eng-svc). No system or game headers.
#pragma once
#include <stdint.h>

// SVC_R_MK (lane eng-svc2): the baked motion keys, the service region from 4 MiB on (svc_io.cpp)
enum { SVC_R_PARTS = 0, SVC_R_EM, SVC_R_OBJ, SVC_R_ROOM, SVC_R_CHR, SVC_R_CORE, SVC_R_HEAP, SVC_R_SVC, SVC_R_OTHER, SVC_R_MK, SVC_REGIONS };
struct SvcRegion { uint32_t lo, hi, stride; };

extern "C" {
// svc_trace.cpp
void svc_census_regions(const SvcRegion* r);   // parts, em, obj pools (lo, hi, stride); the rest from the loads
void svc_census_parts(unsigned lo, unsigned stride, unsigned n, const uint8_t* owner, const uint8_t* bone);
void svc_census_tick(unsigned t, int begin);
void svc_census_finish(const char* actors_tsv);
void census_hit(unsigned idx, unsigned ret, unsigned arg0);
}
