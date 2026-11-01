#pragma once
// ACTOR_SOURCE_SPAN: exact immutable-source borrow, valid only while the
// existing skin lease is current. Zero keeps all public layouts unchanged.
#ifndef RE4DC_ACTOR_SOURCE_SPAN
#define RE4DC_ACTOR_SOURCE_SPAN 0
#endif
#ifndef RE4DC_NATIVE_FE_CONTINUATION
#define RE4DC_NATIVE_FE_CONTINUATION 0
#endif
#if RE4DC_ACTOR_SOURCE_SPAN
struct Re4dcActorSourceSpan {
    const unsigned char* positions=nullptr;
    const unsigned char* normals=nullptr;
    unsigned position_bytes=0,normal_bytes=0,uv_bytes=0;
    // Source FE records use palette-indexed s16 xyz in eight-byte records.
    // UV interpretation is explicit, never inferred from referenced indices.
    enum : unsigned { Unknown=0,U16Q15=1,S16Q8=2 };
    unsigned uv_encoding=Unknown;
    unsigned owner_serial=0,owner_frame=0;
};
#endif
