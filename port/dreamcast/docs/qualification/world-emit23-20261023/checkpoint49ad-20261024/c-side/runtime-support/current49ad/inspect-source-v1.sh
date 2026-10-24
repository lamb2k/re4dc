#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/world-emit23-current-R
rg -n -e 'struct Re4dcNativeFrameStats' -e 'present_requested' "$T/port/dreamcast/game/platform/include/native_model.h"
sed -n '145,166p' "$T/port/dreamcast/game/platform/include/native_model.h"
rg -n -e 'typedef struct' -e 'flip' -e 'pending' -e 'fb_num' -e 'render_completed' /root/work/kos-re4dc-d367/kernel/arch/dreamcast/hardware/pvr/pvr_internal.h /root/work/kos-re4dc-d367/kernel/arch/dreamcast/hardware/pvr/pvr_irq.c | head -65