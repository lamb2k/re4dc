"""still_at.py <cap dir> <out dir> <fb front,back> <s1,s2,...>  (lane castle31): fp_run writes run-output.txt only at
the end, so stills are taken by wall time after flycast.pid appears, with the framebuffer pointers of an earlier run of
the same program (the 'fb=' pair of a native UI line)."""
import sys, time, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import capture_ui_vram as m
cap, out, fb, times = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], [float(x) for x in sys.argv[4].split(',')]
limit = time.time() + 120
while not (cap / 'flycast.pid').exists() and time.time() < limit:
    time.sleep(0.2)
t0 = time.time()
for t in times:
    while time.time() - t0 < t:
        time.sleep(0.1)
    ev = out / ('ev-%03d' % t)
    ev.mkdir(parents=True, exist_ok=True)
    for n in ('emu.cfg', 'flycast.log', 'flycast.pid'):
        shutil.copy2(cap / n, ev / n)
    (ev / 'boot.log').write_text('native UI: fb=%s\n' % fb, encoding='utf-16')
    try:
        print(t, m.capture(ev, out / ('t%03d' % t)), flush=True)
    except Exception as e:
        print(t, 'fail', e, flush=True)
