import re
T='/root/probe/lanes-20261016/ch4found/tree/src/st2/'
# r226
p=T+'r226.cpp'; s=open(p).read()
anchor='#include "eprintf.h"\n'
assert s.count(anchor)==1
s=s.replace(anchor, anchor+'''#if defined(RE4DC_PS2_ENEMY_CASTLE) && (RE4DC_PS2_ENEMY_CASTLE & 0x20)
// PS2 USA r226 AEV 0x28 / 0x29 (absent from the GameCube AEV): type 4 event flags 71 / 72, the two places R226Main's
// PS2 reinforcement block tests (Room_flg[2] 0x01000000 / 0x00800000). tools/d367/ps2ref/ps2roomdiff.py aev r226.
#include "ps2_flag_area.h"
static const AreaData r226Ps2Area[2] = {
    {1, AREA_TYPE_XZ4, 0, {{4241.625f, 8453.5244140625f, 750.0f, {{-8605.07421875f, -7034.826171875f}, {8689.6650390625f, -7201.412109375f}, {7795.22900390625f, 4543.69677734375f}, {-8257.4501953125f, 5554.0966796875f}}}}},
    {1, AREA_TYPE_XZ4, 0, {{3974.9169921875f, 9116.7734375f, 750.0f, {{-7966.78564453125f, -37051.73828125f}, {8962.16796875f, -37038.078125f}, {8992.24609375f, -25312.625f}, {-7736.45263671875f, -25386.51953125f}}}}},
};
#endif
''',1)
a2='    PSetRobo(wp->robo, NULL);\n'
assert s.count(a2)==1
s=s.replace(a2, a2+'''#if defined(RE4DC_PS2_ENEMY_CASTLE) && (RE4DC_PS2_ENEMY_CASTLE & 0x20)
    re4dc_ps2FlagArea(&r226Ps2Area[0], 71, 1, "r226 PS2 AEV 0x28");
    re4dc_ps2FlagArea(&r226Ps2Area[1], 72, 1, "r226 PS2 AEV 0x29");
#endif
''',1)
open(p,'w').write(s)
# r227
p=T+'r227.cpp'; s=open(p).read()
anchor='#include "cSceObj.h"\n'
assert s.count(anchor)==1
s=s.replace(anchor, anchor+'''#if defined(RE4DC_PS2_ENEMY_CASTLE) && (RE4DC_PS2_ENEMY_CASTLE & 0x40)
// PS2 USA r227 AEV 0x15 (absent from the GameCube AEV): type 4 event flag 64, trigger 2, the area that stops
// r227_ps2SendTask's sends (Room_flg[2] bit 31). tools/d367/ps2ref/ps2roomdiff.py aev r227.
#include "ps2_flag_area.h"
static const AreaData r227Ps2Area15 =
    {1, AREA_TYPE_XZ4, 0, {{62.50030517578125f, 12200.0f, 750.0f, {{-17054.796875f, -14550.2490234375f}, {17625.845703125f, -17427.841796875f}, {13212.7392578125f, 17864.34375f}, {-17192.916015625f, 17449.181640625f}}}}};
#endif
''',1)
a2='    wp = (R227Work*) MEM_CALLOC(sizeof(R227Work), 1, 0xD);\n'
assert s.count(a2)==1
s=s.replace(a2, a2+'''#if defined(RE4DC_PS2_ENEMY_CASTLE) && (RE4DC_PS2_ENEMY_CASTLE & 0x40)
    re4dc_ps2FlagArea(&r227Ps2Area15, 64, 2, "r227 PS2 AEV 0x15");
#endif
''',1)
open(p,'w').write(s)
print('ok')
