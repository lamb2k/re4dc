#!/usr/bin/env bash
set -euo pipefail
O=/root/probe/lanes/route/out-sb23on2a14rP
rg 'ESP_POOL|R117_EFFECT|KOS_CACHE|R10C_SPAWN|EM_READ|VRAM_ROOM_ARENA|STAT_ROUTINE' "$O/resolved-knobs.txt"
rg -n 'resolved-knobs|knob.*inventory|KOS_CACHE_P2' /root/work/lanes/audits23/port/dreamcast/tools/d367/route/route-build.sh /root/work/lanes/audits23/port/dreamcast/game/Makefile | tail -12