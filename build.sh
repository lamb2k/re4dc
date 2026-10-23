#!/bin/bash
set -euo pipefail
arm=${1:?off/on}; case "$arm" in on|off) ;; *) exit 2;; esac; T=/root/probe/codex-actor-visibility23-eligibility-witness-integration
E=/root/probe/lanes/actor-visibility23-eligibility-witness-integration; O=$E/${ACTOR23_ARM_OUTPUT:-$arm}
[ ! -e "$O/re4dc-game.elf" ] || { echo sealed-output-exists; exit 1; }
mkdir -p "$O"
export T K=$E/controls SOURCE_DATE_EPOCH=1760000000 JOBS=1
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367 RE4DC_KOS_CC_BASE=/root/probe/lanes/world-scratch23-integration/toolchain
source "$T/port/dreamcast/kos-env.sh"
export PATH="$RE4DC_KOS_BASE/utils/build_wrappers:$RE4DC_KOS_CC_BASE/bin:$PATH"
source "$T/port/dreamcast/tools/d367/rr/recipe.conf"
# Only assignments and the unused build helper; no shared build/staging invocation.
source <(sed '/^L=${LP/,$d' "$T/port/dreamcast/tools/d367/test15/t15-build.sh")
export ASSETS=/root/probe/lanes/play-actor-bundle OBJDIR=$O/obj OUT=$O
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367 RE4DC_KOS_CC_BASE=/root/probe/lanes/world-scratch23-integration/toolchain
actor_args="ACTOR_VISIBILITY23=0 ACTOR_VISIBILITY23_WITNESS=0"
if [ "$arm" = on ]; then actor_args="ACTOR_VISIBILITY23=1 ACTOR_VISIBILITY23_WITNESS=1 ACTOR_VISIBILITY23_CERT=/root/probe/lanes/actor-visibility23-coverage-integration/certificate ACTOR_VISIBILITY23_SDK=/root/probe/codex-actor-visibility23/port/dreamcast/game/.actor-visibility23-sdk-final"; fi
cd "$T"
# Intentional word splitting: these are trusted make NAME=value assignment lists.
bash port/dreamcast/tools/d367/build-r21.sh LOGIC_TRACE=0 GAME_DECISION_TRACE=0 ACTOR_TRANSACTION_DIAG=0 GAME_PWC_DIAG=1 ARENA_FIT_KOS_BYTES=147456 QUALITY_PICKER=0 PACE_MODE=fast $F $LOOK $BASE $T13 $T14 $T15REC $CH2 IMAGE_PAD_BYTES=0 DBG_WARP=1 PC_SAMPLER=1 QA_MENU=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=22 QA_SRC=ws23 WORLD_METER=1 WORLD_SCRATCH=0 MESH_FASTPATH=1 $actor_args CPU_BACKFACE=0 ACTOR_BACKFACE=0 VRAM_ROOM_ARENA=0
cp port/dreamcast/game/obj/missing.txt "$O/missing.txt"

python3 "$ACTOR23_SCRIPTS/receipt.py" "$arm"
python3 "$ACTOR23_SCRIPTS/compile_evidence.py" "$arm"
