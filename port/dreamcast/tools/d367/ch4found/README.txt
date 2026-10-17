Lane ch4found16 (chapter 4 foundations, 2026-10-16) tools. Paths are the lane's ext4 roots; no private data here.
See C:\Game Dev\Emulators\CH4-FOUNDATIONS-20261016.md and CASTLE-ROUTE-20261015.md.
mkfix.sh / fixall2.sh          room fixture = ch3found ch3f-c + Codex cx room keys + fix/ch4-add*.json, armed + pack audit
mkh.sh / runall.sh             harness per arm; rfp-run-one.py 60 s runs, N at a time (FLYMAX caps Flycasts)
summ.py / table.py / dec.py    per-run summaries: gates, heap 4, VRAM, AICA; dec.py = decisions (kills, cap 6 hold /
                               defer / release / park, ps2en: room sends, alive log)
vsum.sh                        TEXCHK + vram_gate.py per run (the VQ owner-room check)
auditchk.py                    pack-winner audit: every render mismatch must be an approved vq16-* key
evdcuts.py                     PS2 evd camera cuts -> QTE picture / frames for RouteMoviePlayQte
edit_movies.py                 ROUTE_MOVIES_CH4 hooks (r212 r214 r215 r227 r228)
edit_areas.py                  PS2 flag areas (include/ps2_flag_area.h) for r226 (flags 71 / 72) and r227 (flag 64)
edit_otwc.py                   OT_WALK_CHECK debug arm (r229 ExecOt fault); fixnl3.py repairs heredoc-split strings
aicarows4.py / snd4.sh         chapter 4 aica_banks rows (ROOMS, ROOM_BGM0, --streams ch4) and the bank / stream build
strmap.py                      chapter 4 bgmtbl tracks / streams and logged sbb offsets -> (block, number)
ident3.sh                      knob-off identity (test 15 rP) vs the recorded base image
warps/                         dec-* (decisions: god, kill rig, rsf, goto), dec2-r226, vq-* (ch1 rooms loading c42 keys)
