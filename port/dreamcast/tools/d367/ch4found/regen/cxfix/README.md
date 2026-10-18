# Codex cx-fixtures replay (lane ch4regen, 2026-10-18)
Rebuilds /root/probe/codex-cx-fixtures-20261013/{output,dependencies/prepared} byte-exact (2,753 of 2,753 harvested
targets). Published read-only at /root/re4data/private/cxfix-replay-20261018 (+ C: copy, SHA256SUMS).
- Tools: Codex tree 90606dcf (gitdig18 bundle); le_mirror variants by output dir name: ancillary = 90606dcf
  (0fcb82a6), ancillary-c3d2f4cd6f00 = + rollout patch 16:56Z (01347301), ancillary-b47c37112cf4 = + 67524643 diff
  (le_mirror-67524643.diff, from the 10-12 rollout's git show).
- cxrun.py = cx_room_fixtures.prepare_room up to the texture step; cxdeps.sh = cx_room_dependencies.py (rebuilt from
  the 16:57Z here-string). cxbuild.py/psapply.py rebuild cx_room_fixtures.py from the rollout patches (+ the 16:59:20Z
  Substring fix found only in the raw jsonl, not in transcripts.db).
