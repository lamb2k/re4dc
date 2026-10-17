Lane ch5found16 (island foundations, 2026-10-16) tools. Paths are the lane's ext4 roots; no private data here.
build.sh <LP> <arm> knobs...   t15-build.sh arm into the lane build dir (JOBS=4)
ident.sh / ident2.sh           knob-off identity pairs (t15 rP; castle cxc3fmW knob set) vs a pristine t15/int worktree
pakunion.py                    union of two RE4PAK1 texture packs (smaller payload wins on a shared key; CRC at +24)
c5merge.py / mkfix.sh          island fixture = t15 mW fixture + st3 lane room fixtures + union pak + resident.bin
clone_h.py / run1.sh / summ.py harness clone, one 60 s Flycast run, per-room heap4/VRAM/KOS summary
sizes.py                       island disc payload survey (sizes.out in C:\tmp\ch5)
warps/                         warp scripts: r300 door walk, r303 -> r30d -> r303 stage jump (WARP_JUMP=1)
See C:\Game Dev\Emulators\CH5-FOUNDATIONS-20261016.md and ISLAND-ROUTE-20261016.md.
Round 2 (2026-10-16 evening):
mkwarps.py / mkfix2.sh / batch2.sh   28 room fixtures (god, alivelog, kill rig), 4 Flycasts at a time
summ2.py                       per-run digest: heap 4, VRAM, KOS, cap 6 (peak / hold / release), kills, AICA no-fit, streams
snd5.sh / aicarows.py          island AICA banks + --streams ch5 (aica_banks ROOMS / ROOM_BGM0 rows)
mkv.sh / addsnd.py / addmov.py sound fixtures (arm cx5vmW) and the island route movies
build2.sh / batch3b.sh / run1t.sh / strict.sh   STRICT pairs (LOGIC_TRACE=1): cx5tmW (dba49b85) vs cx5umW (hooks).
                               run1t.sh calls a lane copy of rfp-run-one.py with its LOGIC_TRACE=0 assert relaxed
                               (C:\tmp\ch5\rfp-run-trace.py; not committed: it is the skill script's copy)
disc3.py / disc4.py            per-disc sizes for the three-disc layout from payload manifests
ident3.sh                      knob-off identity (test 15 rP) for this round
warps2/                        round 2 warps (cx-<room>-r2, r31d / r327 cap)
