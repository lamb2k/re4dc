#!/bin/bash
# zbuild.sh <LP> <zam 0|1> <arm...> : lane sh4zam-direct builds through test13/t13-build.sh (XON passes through)
export K=/root/probe/lanes-20261015/sh4zam
export T=$K/tree
LP=$1; Z=$2; shift 2
TB=$T/port/dreamcast/tools/d367/test13/t13-build.sh
T13R=$(grep -o '^T13R="[^"]*' $TB | cut -c7-)
T13G=$(grep -o '^T13G="[^"]*' $TB | cut -c7-)
T13X="$T13R $T13G ROOM_CHANGE_EVICT=60"
[ "$Z" = 1 ] && T13X="$T13X GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1"
[ "$Z" = 2 ] && T13X="$T13X GAME_SH4ZAM=1"
cd $T && LP=$LP T13="$T13X" bash $TB "$@"
