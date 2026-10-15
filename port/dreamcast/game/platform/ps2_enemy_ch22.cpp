#include "ps2_enemy_ch22.h"
#if defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22 && \
    defined(RE4DC_PS2_ENEMY_RULES) && RE4DC_PS2_ENEMY_RULES
#include <stdio.h>
#include <string.h>

/* This translation unit is built only for ROUTE_CH22 && PS2_ENEMY_RULES.
 * The generator emits private game bytes only after the room activation
 * evidence is qualified. No external reads, allocation, or per-frame work.
 */
struct Ps2EnemyCh22Row {
    unsigned short index;
    unsigned char data[32];
};
struct Ps2EnemyCh22List {
    int list_no;
    const Ps2EnemyCh22Row *baseline;
    unsigned baseline_count;
    const Ps2EnemyCh22Row *replacement;
    unsigned replacement_count;
};
#include "ps2_enemy_ch22_data.inc"

#if defined(RE4DC_PS2_ENEMY_ROOMS)
#define PS2_ROOMS (RE4DC_PS2_ENEMY_ROOMS)
#else
#define PS2_ROOMS 0
#endif
/* Rows this adapter owns (room = u16 at row byte 0x18; room 0 = an empty slot the PS2 fills).
 * Chapter 2-2 rows only (r111 / r112 / r113; r11c with PS2_ENEMY_ROOMS bit 0x40, empty room-0 slots are
 * verified). r100 / r104 (list 0) and r11a (list 1) belong to PS2_ENEMY_ROOMS bits 0x01 / 0x04 / 0x10
 * (stage.cpp, applied before this): the qualified table also carries them, and applying them here changed
 * r100 under ROUTE_CH22 without those bits (H2 STRICT divergence at tick 660).
 */
static int ps2EnemyCh22Owned(const unsigned char *d)
{
    const unsigned room = d[0x18] | (d[0x19] << 8);
    return room == 0 || room == 0x111 || room == 0x112 || room == 0x113 || (room == 0x11C && (PS2_ROOMS & 0x40));
}

extern "C" int re4dc_ps2EnemyListCh22(int list_no, void *data, unsigned size)
{
    const Ps2EnemyCh22List *list = NULL;
    unsigned i, j, nv = 0, nr = 0;
    for (i = 0; i < sizeof(ps2_enemy_ch22_lists) / sizeof(ps2_enemy_ch22_lists[0]); ++i) {
        if (ps2_enemy_ch22_lists[i].list_no == list_no) {
            list = &ps2_enemy_ch22_lists[i];
            break;
        }
    }
    if (!list) return 0;
    if (!data) {
        printf("PS2_ENEMY_CH22: FAIL list=%d null buffer\n", list_no);
        return -1;
    }
    unsigned char *bytes = static_cast<unsigned char *>(data);
    /* Check every byte of every selected row, including unchanged rooms,
     * rotations, HP, emset_no and reserved bytes, before writing anything.
     */
    for (i = 0; i < list->baseline_count; ++i) {
        const Ps2EnemyCh22Row &row = list->baseline[i];
        const unsigned offset = static_cast<unsigned>(row.index) * 32;
        if (!ps2EnemyCh22Owned(row.data)) continue;
        ++nv;
        if (offset > size || size - offset < 32) {
            printf("PS2_ENEMY_CH22: FAIL list=%d row=%u buffer=%u\n", list_no,
                   static_cast<unsigned>(row.index), size);
            return -1;
        }
        for (j = 0; j < 32; ++j) {
            if (bytes[offset + j] != row.data[j]) {
                printf("PS2_ENEMY_CH22: FAIL list=%d row=%u byte=%u expected=%02x got=%02x\n",
                       list_no, static_cast<unsigned>(row.index), j,
                       static_cast<unsigned>(row.data[j]),
                       static_cast<unsigned>(bytes[offset + j]));
                return -2;
            }
        }
    }
    for (i = 0; i < list->replacement_count; ++i) {
        const Ps2EnemyCh22Row &row = list->replacement[i];
        if (!ps2EnemyCh22Owned(row.data)) continue;
        ++nr;
        memcpy(bytes + static_cast<unsigned>(row.index) * 32, row.data, 32);
    }
    printf("PS2_ENEMY_CH22: list=%d verified=%u replaced=%u full32=1\n",
           list_no, nv, nr);
    return 1;
}
#endif
