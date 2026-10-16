import sys
from pathlib import Path
H = Path(sys.argv[1])
s = (H / 'stage-scenario-v2.py').read_text()
old = "(out/'disc/disc.cue').write_text('FILE \"'+report['disc_unc']+'\" BINARY\\n"
assert old in s
s = s.replace(old, "(disc.parent/'disc.cue').write_text('FILE \"disc.bin\" BINARY\\n  TRACK 01 MODE1/2048\\n    INDEX 01 00:00:00\\n')\n" + old)
(H / 'stage-scenario-v2.py').write_text(s)
r = (H / 'run-emulator-novsync.py').read_text()
old = "if meta.get('disc_unc'):(cap/'game.cue').write_text('FILE \"'+str(disc)+'\" BINARY\\n  TRACK 01 MODE1/2048\\n    INDEX 01 00:00:00\\n')\n"
assert old in r
r = r.replace(old, "if meta.get('disc_unc'):(cap/'game.cue.txt').write_text(str(disc.parent/'disc.cue')+'\\n')  # st3 lane: Flycast opens the ext4 cue directly\n")
old2 = "proc=subprocess.Popen([str(cap/'flycast.exe'),'game.cue'],"
assert old2 in r
r = r.replace(old2, "proc=subprocess.Popen([str(cap/'flycast.exe'),str(disc.parent/'disc.cue') if meta.get('disc_unc') else 'game.cue'],")
(H / 'run-emulator-novsync.py').write_text(r)
print('ok', H)
