# Codex cx-fixtures replay (lane ch4regen, 2026-10-18)
Rebuilds /root/probe/codex-cx-fixtures-20261013/{output,dependencies/prepared} byte-exact (2,753 of 2,753 harvested
targets). Published read-only at /root/re4data/private/cxfix-replay-20261018 (+ C: copy, SHA256SUMS).
- Tools: Codex tree 90606dcf (gitdig18 bundle); le_mirror variants by output dir name: ancillary = 90606dcf
  (0fcb82a6), ancillary-c3d2f4cd6f00 = + rollout patch 16:56Z (01347301), ancillary-b47c37112cf4 = + 67524643 diff
  (le_mirror-67524643.diff, from the 10-12 rollout's git show).
- cxrun.py = cx_room_fixtures.prepare_room up to the texture step; cxdeps.sh = cx_room_dependencies.py (rebuilt from
  the 16:57Z here-string). cxbuild.py/psapply.py rebuild cx_room_fixtures.py from the rollout patches (+ the 16:59:20Z
  Substring fix found only in the raw jsonl, not in transcripts.db).

## Missing step in cxbuild.py (found 10-18)

Patch 55 leaves cx_room_fixtures.py broken (one Replace matched twice). Codex repaired it at
16:59:20Z with a Substring call that shows up only in the raw rollout jsonl, not in transcripts.db.
Apply it after patch 55 and before patch 60: replace the text from
`                    texture_report = read` up to (not including)
`                        blockers.append('prepare_native_ui` with
`                    if room not in ROOM_CONTRACTS:\n`.
The cx_room_fixtures.py copy in /root/re4data/private/cxfix-replay-20261018 does not have this fix.
The data in that folder was produced with the fixed copy and is sha-verified (2753/2753).
