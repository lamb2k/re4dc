# ch2 data regeneration (lane ch2regen, 2026-10-17)

Replays of the recorded chapter 2-2 / 2-3 data chain after the 10-17 WSL /root loss. Target shas per disc file come
from surviving staged-run evidence (C:\Flycast-Evidence\re4-dreamcast\ch2code-20261016\n3-c4w-r10f\payload-manifest.json,
targets.py / cover.py). Outputs live under /root/probe/lanes-20261017r/ch2regen (private data, never committed).

- recovered/: scripts recovered verbatim from C:\tmp\ch22 and the transcript DB (re4dc-recovery\transcripts.db).
- room.sh <room> <tools tree>: ch22w room.sh (le_mirror, prepare_native_ui, compact, convert_room_bins, room_smd release).
  r113 with origin/lane/ch2code16 tools: st1/r113.arc + MAINSCENARIO.re4mesh byte-exact.
- ps2w.sh <room> <tree>: ch22w ps2w.ps1 (gc_room_lit + ps2_room_r4im.py, Windows Python), inputs ps2rooms-20260930.
  r113 at fed4122a: ps2-world.{re4mesh,r4pw,ids} byte-exact.
- r113.dar: aica_banks.fit (lane fit-r113.py recipe) on rel-r113/st1/r113.dar with the Test 16.3 disc tree: byte-exact.
- reg113p-{a,b,c}.sh: ps2cast s152 + ganado-em17-0cp convert/native/finish (cast_bundle.py recovered) + regcast/merge +
  head mask runs + model_registry --pool at ecf2a44a: dc/native/r113/registry.re4nmr fa23cc54 byte-exact.
