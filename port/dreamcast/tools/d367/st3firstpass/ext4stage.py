"""ext4stage.py <harness dir (WSL path)>: lane adapter (coordinator 10-15: stage discs on WSL ext4, Flycast reads them
through \\\\wsl.localhost). Patches the harness clone's stage-scenario-v2.py and run-emulator-novsync.py in place."""
import sys
from pathlib import Path
H = Path(sys.argv[1])
s = (H / 'stage-scenario-v2.py').read_text()
if 'DISCROOT' not in s:
    s = s.replace("stage_capacity=dict(free_before=shutil.disk_usage('/mnt/c').free,",
                  "DISCROOT=Path('/root/probe/lanes-20261014/st3/discs')  # st3 lane: discs on WSL ext4 (release rule 3)\n"
                  "DISCROOT.mkdir(parents=True,exist_ok=True)\n"
                  "stage_capacity=dict(free_before=shutil.disk_usage(DISCROOT).free,target=str(DISCROOT),")
    old = "out.mkdir(parents=True);(out/'disc').mkdir();disc=out/'disc/disc.bin'"
    assert old in s
    s = s.replace(old, "out.mkdir(parents=True);(out/'disc').mkdir();(DISCROOT/a.scenario).mkdir();disc=DISCROOT/a.scenario/'disc.bin'")
    old2 = "payload_delta=diff(before,after),"
    assert old2 in s
    s = s.replace(old2, "disc_unc='\\\\\\\\wsl.localhost\\\\Ubuntu-24.04'+str(disc).replace('/','\\\\'),payload_delta=diff(before,after),")
    old3 = "(out/'disc/disc.cue').write_text('FILE \"disc.bin\" BINARY\\n"
    assert old3 in s, 'cue'
    s = s.replace(old3, "(out/'disc/disc.cue').write_text('FILE \"'+report['disc_unc']+'\" BINARY\\n")
    (H / 'stage-scenario-v2.py').write_text(s)
r = (H / 'run-emulator-novsync.py').read_text()
if 'disc_unc' not in r:
    old = "meta=json.loads((stage/'stage.json').read_text());disc=stage/'disc'/'disc.bin'"
    assert old in r
    r = r.replace(old, "meta=json.loads((stage/'stage.json').read_text());disc=Path(meta['disc_unc']) if meta.get('disc_unc') else stage/'disc'/'disc.bin'")
    old2 = "os.link(disc,cap/'disc.bin')\n(cap/'game.cue').write_text('FILE \"disc.bin\" BINARY\\n"
    assert old2 in r, 'link'
    r = r.replace(old2, "if meta.get('disc_unc'):(cap/'game.cue').write_text('FILE \"'+str(disc)+'\" BINARY\\n  TRACK 01 MODE1/2048\\n    INDEX 01 00:00:00\\n')\nelse:\n  os.link(disc,cap/'disc.bin')\n  (cap/'game.cue').write_text('FILE \"disc.bin\" BINARY\\n")
    (H / 'run-emulator-novsync.py').write_text(r)
print('patched', H)
