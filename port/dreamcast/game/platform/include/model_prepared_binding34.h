#pragma once
// Build34: one scoped, archive-owned generic model part. The prepared token
// borrows an existing texture Entry through the current actor lease table;
// it never owns a new cache, header, source pointer or packet allocation.
#include "native_draw_owner_stamp.hpp"
#include "actor_resource_lease.h"
struct Re4dcModelPart;
struct Re4dcModelPacket;
// One synchronous part's archive and uploaded texture proof. No native packet
// or header is published by prepare. The existing 64-slot lease table owns the
// Entry pin; this POD lives only on the submitting call's stack.
struct Re4dcModelPreparedBinding34 {
    enum Span : unsigned { Part,Stream,Positions,Normals,Uv,Colors,Pixels,Palette,SpanCount };
    Re4dcDrawOwnerStamp source[SpanCount]{};
    Re4dcActorTextureLease texture{};
    unsigned entry=0,frame=0,upload=0,crc=0,fnv=0;
    unsigned uv_bytes=0,color_bytes=0,pixel_bytes=0,width=0,height=0,pass=0;
    float u_scale=0,v_scale=0;
    unsigned char descriptor[32]{}; // the source ModelPart prefix, not the stack view
    unsigned active=0;
};
extern "C" {
// 1 qualified, 0 unknown before I/O (use the existing late-binding path),
// -1 failed after preparation started (do not emit this part).
int re4dc_model_packet_prepare34(const Re4dcModelPart*,unsigned uv_bytes,unsigned color_bytes,
                                 Re4dcModelPreparedBinding34*);
int re4dc_model_packet_prepared_current34(const Re4dcModelPart*,const Re4dcModelPreparedBinding34*);
int re4dc_model_packet_begin_prepared34(const Re4dcModelPart*,Re4dcModelPacket*,
                                        const Re4dcModelPreparedBinding34*);
void re4dc_model_packet_prepared_release34(Re4dcModelPreparedBinding34*);
}
