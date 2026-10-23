#include "../../../game/platform/include/gc_asset_packet_cursor.h"
#include <cassert>
using re4dc_gcasset::PacketCursor;
int main() {
    PacketCursor cursor;
    std::uint32_t polygon[8]={0x80000008,0,0,0x200};
    std::uint32_t vertex[8]={0xe0000000};
    assert(!cursor.feed(polygon));assert(cursor.feed(vertex));assert(!cursor.feed(vertex));
    cursor={};assert(!cursor.feed(vertex)); // a preceding scene's header cannot carry
    // Real FX packet: 32-byte textured sprite header plus64-byte vertex.
    // Vertex word8 is cy=-0.5f, whose high bits resemble a new sprite header.
    std::uint32_t sprite[24]={0xa0000008,0,0,0x200};sprite[8]=0xf0000000;sprite[16]=0xbf000000;
    cursor={};assert(!cursor.feed(sprite));assert(cursor.feed(sprite+8));assert(!cursor.feed(sprite+16));
    assert(cursor.textured && !cursor.first && !cursor.continuation && cursor.address==0x1000);
    assert(!cursor.feed(sprite+8));assert(!cursor.feed(sprite+16)); // repeated64B sprite, no PCW
    assert(cursor.textured && cursor.address==0x1000);
    // Textured floating-colour polygon vertices are64B too. Every second half
    // stays opaque payload, even when it resembles a different textured PCW.
    std::uint32_t wide[8]={0x80000018,0,0,0x200};
    std::uint32_t tail[8]={0x80000008,0,0,0x400};
    cursor={};assert(!cursor.feed(wide));assert(cursor.feed(vertex));assert(!cursor.feed(tail));
    assert(cursor.address==0x1000);assert(!cursor.feed(vertex));assert(!cursor.feed(tail));
    assert(cursor.address==0x1000);
    // Two-volume floating-colour headers are64B; a header tail that looks like
    // a vertex must not count as accepted primitive output.
    std::uint32_t wide_header[8]={0x80000068,0,0,0x200};
    cursor={};assert(!cursor.feed(wide_header));assert(!cursor.feed(vertex));assert(cursor.feed(vertex));
}
