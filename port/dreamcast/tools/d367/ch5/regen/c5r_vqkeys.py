#!/usr/bin/env python3
"""ch5regen: re-run the st3 lane vqroom.py / addss.py VQ step for single keys.
usage: c5r_vqkeys.py <tools dir> <work> <src re4tex>...  -> <work>/out/<key>.re4tex (VQ + vq_pak.restamp), raw 16-bit kept
when the image is below the vqroom/addss size rule."""
import pathlib, sys, shutil
T = sys.argv[1]
sys.path.insert(0, T); sys.path.insert(0, T + '/d367'); sys.path.insert(0, T + '/d367/vram')
import vq_native_ui as vq, vq_pak
work = pathlib.Path(sys.argv[2]); src = work / 'src'; outd = work / 'vq'; prev = work / 'prev'; out = work / 'out'
for d in (src, outd, prev, out): d.mkdir(parents=True, exist_ok=True)
for f in sys.argv[3:]:
    f = pathlib.Path(f); key = f.stem; blob = f.read_bytes()
    try:
        w, h, fmt, flags, _ = vq.read_package(blob)
        (src / f.name).write_bytes(blob)
        e = vq.encode(key, src, outd, vq.PVRTEX, (w, h), prev)
        new, rule = vq_pak.restamp(blob, (outd / f.name).read_bytes())
        (out / f.name).write_bytes(new)
        print(key, w, h, 'vq', round(e['psnr_db'], 1))
    except Exception as ex:
        print(key, 'fail', ex)
