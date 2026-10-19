// Route end of a play disc (ROUTE_CH13=1, route lane c13; user 2026-10-04: "it shouldn't fade back to title it
// should say Coming Soon in the system fonts"). A door (sce_at.cpp sceAtFunc_door, also the warp rig's room jump)
// into a room this disc does not carry fades to black and shows "Coming Soon" in the game's own message system
// (file 4, the system messages, in slot 0 with the system layout: the card / VMU prompts' font and path, as the
// quality picker), then holds there. The game stays stopped (the door already set Stop_flg and the key stop), no
// room change starts, nothing halts. Reusable for any door into an unbuilt room: a room is built on this disc when
// its native world package dc/native/rXXX/ps2-world.r4pw is on it (every route room from r100 has one).
#include "types.h"
#include "global.h"
#include "main.h"
#include "mes.h"
#include "fade.h"
#include "dolphin/dvd.h"
#include "scheduler.h"
#include <stddef.h>

extern "C" void re4dc_log(const char* fmt, ...);
extern "C" void pvr_set_bg_color(float r, float g, float b);   // KOS

namespace {
// Glyph codes of the English common_p.fnt (quality_picker.cpp, verified): space 0x80, 'A'-'Z' = ch + 0x66,
// 'a'-'z' = ch + 0x60; control codes 00 page, 01 end.
struct Table {
    u32 hdr;
    u32 lang[8];
    u32 x0, count, ofs[1];
    u16 text[32];
};
alignas(4) Table table;

void build(const char* s)
{
    unsigned n = 0;
    const u32 block = offsetof(Table, x0);
    table.hdr = 8;
    for (u32& l : table.lang) l = block;
    table.x0 = 0;
    table.count = 1;
    table.ofs[0] = offsetof(Table, text) - block;
    table.text[n++] = 0x00;
    for (; *s && n < 30; ++s) {
        const char c = *s;
        table.text[n++] = c == ' ' ? 0x80 : (c >= 'A' && c <= 'Z') ? u16(c + 0x66) : u16(c + 0x60);
    }
    table.text[n++] = 0x01;
}

// attr: file 4 (0x10, the game keeps its own stop state), instant (0x40), kept after the end code
// (0x01000000), centred horizontally (no 0x20000) and vertically (0x10000).
constexpr u32 kAttr = 0x01010050;
constexpr int kFadeFrames = 30;

void coming_soon_task(int room)
{
    GXColor clear = {0, 0, 0, 0}, black = {0, 0, 0, 0xFF};   // explicit bytes, not FadeSetW's u32 colour pair
    FadeSet(1, &clear, &black, kFadeFrames, 0, 0);            // clear -> black, kept drawn (flags 3)
    TaskSleep(kFadeFrames + 2);
    // Black: stop drawing the room, as the door demo does (game.cpp: System_flg 0x100000 skips IdSys and Trans; the
    // message system still draws). The disc ends here, so nothing resumes it.
    pG->System_flg |= 0x100000;
    build("Coming Soon");
    MesData.ptr[4] = (u8*) &table;
    cMes.Delete(0);
    cMes.setLayout(0, LAYOUT_SYSTEM);
    cMes.MesSet(0, 0, 0, kAttr, 0, 0, 4);
    re4dc_log("route end: door to r%03x (not on this disc): Coming Soon, holding\n", (unsigned) room);
    for (;;) {
        pvr_set_bg_color(0.0f, 0.0f, 0.0f);   // the room's fog colour is the PVR background; black every frame
        TaskSleep(1);
    }
}
}  // namespace

extern "C" int re4dc_route_room_built(u16 room)
{
    char name[] = "dc/native/r000/ps2-world.r4pw";
    const char hex[] = "0123456789abcdef";
    name[11] = hex[(room >> 8) & 0xF];
    name[12] = hex[(room >> 4) & 0xF];
    name[13] = hex[room & 0xF];
    return DVDConvertPathToEntrynum(name) >= 0;   // not cDvd::FileExistCheck: System_flg 0x20000 makes it fail
}

extern "C" void re4dc_route_coming_soon(u16 room)
{
    TaskExec(1, (TaskFunc) coming_soon_task, (int) room);
}

#if RE4DC_ROUTE_SOON_RETURN
// ROUTE_SOON_RETURN=1 (lane route19, 2026-10-19): the same fade and "Coming Soon" message, but called from the door's
// own task (sce_at.cpp sceSoonReturn), it then fades back in and returns; the caller cancels the door like a locked
// one (Stop_flg restored, the area re-armed), so the player stays in the room and can take another exit.
constexpr int kShowFrames = 150;
extern "C" void re4dc_route_coming_soon_show(u16 room)
{
    GXColor clear = {0, 0, 0, 0}, black = {0, 0, 0, 0xFF};
    FadeSet(1, &clear, &black, kFadeFrames, 0, 0);
    TaskSleep(kFadeFrames + 2);
    pG->System_flg |= 0x100000;
    build("Coming Soon");
    MesData.ptr[4] = (u8*) &table;
    cMes.Delete(0);
    cMes.setLayout(0, LAYOUT_SYSTEM);
    cMes.MesSet(0, 0, 0, kAttr, 0, 0, 4);
    re4dc_log("route end: door to r%03x (not on this disc): Coming Soon, returning\n", (unsigned) room);
    for (int i = 0; i < kShowFrames; ++i) {
        pvr_set_bg_color(0.0f, 0.0f, 0.0f);
        TaskSleep(1);
    }
    cMes.Delete(0);
    pG->System_flg &= ~0x100000;
    FadeSet(1, &black, &clear, kFadeFrames, 0, 0);
    TaskSleep(kFadeFrames + 2);
    re4dc_log("route end: back in the room\n");
}
#endif
