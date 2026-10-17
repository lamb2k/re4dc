#include "ps2_enemy_ch4.h"
#if defined(RE4DC_PS2_CH4_ENEMY) && RE4DC_PS2_CH4_ENEMY && \
    defined(RE4DC_PS2_ENEMY_RULES) && RE4DC_PS2_ENEMY_RULES
#include <stdio.h>
#include <string.h>

/* This translation unit is built only for PS2_CH4_ENEMY (castle chapter 4 lists 4 / 5; a copy of ps2_enemy_ch4.cpp).
 * The generator emits private game bytes only after the room activation
 * evidence is qualified. No external reads, allocation, or per-frame work.
 */
struct Ps2EnemyCh4Row {
    unsigned short index;
    unsigned char data[32];
};
struct Ps2EnemyCh4List {
    int list_no;
    const Ps2EnemyCh4Row *baseline;
    unsigned baseline_count;
    const Ps2EnemyCh4Row *replacement;
    unsigned replacement_count;
};
#include "ps2_enemy_ch4_data.inc"


extern "C" int re4dc_ps2EnemyListCh4(int list_no, void *data, unsigned size)
{
    const Ps2EnemyCh4List *list = NULL;
    unsigned i, j, nv = 0, nr = 0;
    for (i = 0; i < sizeof(ps2_enemy_ch4_lists) / sizeof(ps2_enemy_ch4_lists[0]); ++i) {
        if (ps2_enemy_ch4_lists[i].list_no == list_no) {
            list = &ps2_enemy_ch4_lists[i];
            break;
        }
    }
    if (!list) return 0;
    if (!data) {
        printf("PS2_ENEMY_CH4: FAIL list=%d null buffer\n", list_no);
        return -1;
    }
    unsigned char *bytes = static_cast<unsigned char *>(data);
    /* Check every byte of every selected row, including unchanged rooms,
     * rotations, HP, emset_no and reserved bytes, before writing anything.
     */
    for (i = 0; i < list->baseline_count; ++i) {
        const Ps2EnemyCh4Row &row = list->baseline[i];
        const unsigned offset = static_cast<unsigned>(row.index) * 32;
        ++nv;
        if (offset > size || size - offset < 32) {
            printf("PS2_ENEMY_CH4: FAIL list=%d row=%u buffer=%u\n", list_no,
                   static_cast<unsigned>(row.index), size);
            return -1;
        }
        for (j = 0; j < 32; ++j) {
            if (bytes[offset + j] != row.data[j]) {
                printf("PS2_ENEMY_CH4: FAIL list=%d row=%u byte=%u expected=%02x got=%02x\n",
                       list_no, static_cast<unsigned>(row.index), j,
                       static_cast<unsigned>(row.data[j]),
                       static_cast<unsigned>(bytes[offset + j]));
                return -2;
            }
        }
    }
    for (i = 0; i < list->replacement_count; ++i) {
        const Ps2EnemyCh4Row &row = list->replacement[i];
        ++nr;
        memcpy(bytes + static_cast<unsigned>(row.index) * 32, row.data, 32);
    }
    printf("PS2_ENEMY_CH4: list=%d verified=%u replaced=%u full32=1\n",
           list_no, nv, nr);
    return 1;
}
#endif
