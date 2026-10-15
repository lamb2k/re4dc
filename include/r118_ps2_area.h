#ifndef R118_PS2_AREA_H
#define R118_PS2_AREA_H
// PS2 USA r118.dat AEV records 0x12 and 0x13 (ps2code lane 2026-10-15): two PS2-only flag areas (type 4, kind 0, flag
// no 64 = Room_flg[2] bit 31, trigger inside, player). Room_flg[2] is cleared every frame (SceAtWorkLoopInit), so the
// flag means "Leon is inside either quad this frame"; r118.cpp tests both quads directly.
#define R118_PS2_AREA_A {1, AREA_TYPE_XZ4, 0, {{9954.5f, 2550.3f, 750.0f, {{13557.1f, -38830.0f}, {31295.8f, -39719.1f}, {30901.4f, -7129.9f}, {13993.7f, -7378.8f}}}}}
#define R118_PS2_AREA_B {1, AREA_TYPE_XZ4, 0, {{9019.1f, 3645.2f, 750.0f, {{7284.5f, -18190.8f}, {15925.8f, -21683.9f}, {16558.1f, -5950.5f}, {6801.8f, -8696.1f}}}}}
#endif
