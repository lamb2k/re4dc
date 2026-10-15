#ifndef R101_PS2_AREA15_H
#define R101_PS2_AREA15_H
// PS2 USA r101 AEV area 15 (the square trio, PS2_ENEMY_ROOMS bit 0x100): the AreaData initializer of its quad from the PS2 room .dat, as r101Ps2Area21 / r113Ps2Areas.
// From the ps2code lane 2026-10-15: PS2 r101.dat AEV record 0x0F, type 2 (exec), trigger 1 (inside, not one-shot),
// checkType 1 (player), checkFlag 0; PS2 R101Init installs it (SceAtDataSet_exec(0x0F, SCE_LEVEL20, ...)) while rsf 11
// is clear. The same parser reproduces r101Ps2Area21.
#define R101_PS2_AREA15 {1, AREA_TYPE_XZ4, 0, {{-39.975731f, 2197.7998f, 750.0f, {{-33710.828f, -4571.4067f}, {-29254.357f, -9009.6904f}, {-14285.516f, 9200.3926f}, {-21396.785f, 13438.8f}}}}}
#endif
