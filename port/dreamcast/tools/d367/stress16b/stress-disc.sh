#!/bin/bash
# stress-disc.sh (WSL; lane stress16b): the Saddler stress disc "RE4DC Saddler Stress (NOT THE GAME)".
# Private game data never enters git: the inputs below are local paths (GC Disc 2 review ROM em31 / PS2 Saddler casts).
#  1 cast:     ps2_cast.py convert saddler-em31-00 / -01 (GC skeleton, PS2 mesh), glod_rung.py levels g70 / g50
#  2 registry: model_registry.py model-registry/stress-r119-saddler.json <out> --package-room 119 --pack-bones 96
#              --wide-identity --pool --stress-saddler            -> dc/native/r119/registry.re4nmr (526,848 B)
#  3 archive:  stress_fcv_pose.py em31.drs <posed> --keep 0xA,0x1D,0x1E,0x44,0x47,0x48 (STRESS ONLY: 79 unused
#              motions posed, 1.75 MB -> 0.19 MB), then prepare_enemy_motions.py --keep-motion-resident --textures
#              (resident 1,408,192 B; the unposed archive, 2,964,576 B, does not fit heap 4 beside the r119 world)
#  4 program:  test15/t15-build.sh rW with XON="WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1
#              BENCHMARK=1 BENCH_ID=<sha8> ARENA_FIT_KOS_BYTES=262144 STRESS_SADDLER=1 NATIVE_MODEL_REGISTRY_LOD=1 PC_SAMPLER=0"
#  5 data:     mkpkg.py (test 16 package fixture + em31 overlay / archive / textures + the r119 package), t8-pkgtree.py
#  6 scenes:   mkfix.py <dir> 300 1200 (console) | 120 300 (Flycast twin, runs <= 1 min with the X / Y / B menu)
#  7 image:    TITLE="RE4DC SADDLER STRESS (NOT THE GAME)" PRODUCT=T0003 mkgdi.sh <elf> <pkgtree> <out> <scenes dir>
echo "see the comments: the steps run from the lane scripts (C:/Game Dev/Emulators/stress16b-20261016/sh)"
