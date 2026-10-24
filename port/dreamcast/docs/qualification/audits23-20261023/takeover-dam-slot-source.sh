#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-target-on
rg -n -C5 'struct.*(Pool|Array|Slot)|struct.*Backing|re4dc_work_at_em|magic|pArray' "$T/port/dreamcast/game/parts_bridge.cpp" | head -175