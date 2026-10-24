#pragma once
#include "gc_asset_gate.h"
#include "gc_asset_movie_stream.h"
#if RE4DC_GC_ASSET_GATE
extern "C" unsigned re4dc_gcasset_movie_bind(const void* texture,unsigned width,unsigned height,unsigned asset);
extern "C" void re4dc_gcasset_movie_begin_upload(unsigned owner,const void* texture);
extern "C" void re4dc_gcasset_movie_uploaded(unsigned owner,const void* texture,unsigned width,unsigned height,unsigned asset);
#endif
