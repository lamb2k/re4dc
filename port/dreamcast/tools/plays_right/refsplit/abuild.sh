#!/bin/bash
# abuild.sh: the fight image with the outcome check's closed-loop player (PADRead wrapped at link time by
# tools/plays_right/autoplay/autoplay_engine.cpp; the engine's sources unchanged) -> .eng/fight-ap/e1.elf
set -eu
cd /root/work/lanes/eng-ref
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
. port/dreamcast/kos-env.sh
E=$PWD/port/dreamcast/engine; A=$PWD/port/dreamcast/tools/plays_right/autoplay
rm -rf .eng/fight-ap; cp -a .eng/fight .eng/fight-ap; rm -f .eng/fight-ap/e1.elf
kos-c++ -ffunction-sections -fdata-sections -std=gnu++20 -fpermissive -O2 -ffp-contract=off -fwrapv -fno-strict-aliasing -Wall -Wno-unused -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-threadsafe-statics -fno-rtti -g -DE2_BOSS=1 -DE2_FIGHT=1 -I$E/fight -I$E/boss -I$E/services/effects -include $E/host/e1_prelude.h -I$PWD/include -I$PWD/src -I$E/host -I$E/render -I$E/core -I$E/services -I$E/services/skeleton -I$E/services/collision -I$PWD/port/dreamcast/game/platform/include -I$A -c $A/autoplay_engine.cpp -o .eng/autoplay_engine.o
export KOS_LDFLAGS="$KOS_LDFLAGS -Wl,--wrap=PADRead $PWD/.eng/autoplay_engine.o"
make -C port/dreamcast/engine/game -j6 OUT=$PWD/.eng/fight-ap FIGHT=1 > /mnt/e/RE4DC-Lanes/eng-ref/build/fight-ap-make.log 2>&1 && echo BUILD_OK || { grep -n "error\|undefined" /mnt/e/RE4DC-Lanes/eng-ref/build/fight-ap-make.log | head; exit 1; }
sh-elf-nm .eng/fight-ap/e1.elf | grep -i "wrap_PADRead\|re4ap"
bash /mnt/e/RE4DC-Lanes/eng-ref/s/mkiso.sh fight-ap own FEED=SEED-c16own.BIN 2>&1 | grep -v Warning | tail -1
