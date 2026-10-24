#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/world-emit23-target-R
git -C "$T" grep -n -E 'fb=|upload.*frame|present.*frame|last.*present|g_present|g_upload|pvr_get_frame_buffer' -- port/dreamcast/game port/dreamcast/kos | head -55 || true
sed -n '155,191p' "$T/port/dreamcast/game/ui_bridge.cpp"