#!/bin/bash
set -euo pipefail
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367 RE4DC_KOS_CC_BASE=/root/probe/lanes/world-scratch23-integration/toolchain
source /root/probe/codex-actor-visibility23-eligibility-witness-integration/port/dreamcast/kos-env.sh
export PATH="$RE4DC_KOS_BASE/utils/build_wrappers:$RE4DC_KOS_CC_BASE/bin:$PATH"
exec python3 "$ACTOR23_PROOF/compile_evidence.py" on
