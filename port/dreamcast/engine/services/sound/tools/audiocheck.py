#!/usr/bin/env python3
"""audiocheck.py: did sound leave the AICA? (lane eng-snd1, H-025.1)

    audiocheck.py <capture.raw> [--rate 44100] [--channels 2] [--out report.txt]

The capture is Flycast's own audio output (the mixed sound of the emulated AICA), written by SDL's disk audio driver
while the emulator runs (the lane's runner: emu.cfg [audio] backend = sdl2, SDL_AUDIODRIVER=disk,
SDL_DISKAUDIOFILE=<file>): signed 16-bit little-endian samples, interleaved channels, at the output rate.

The rule (stated before any run): the capture is cut into 100 ms windows; after the first second, at least 10% of the
windows carry an RMS above 64 (about -54 dBFS, far above a silent output's 0), and the capture is at least 10 s long.
PASS when both hold, FAIL otherwise (a silent capture, or one too short to judge). The control is a run with the lab arm
SNDMUTE (every channel at total attenuation): it must FAIL.
Exit: 0 PASS, 1 FAIL, 2 not judged (no file)."""
import argparse
import array
import math
import os
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('raw')
    ap.add_argument('--rate', type=int, default=44100)
    ap.add_argument('--channels', type=int, default=2)
    ap.add_argument('--out')
    a = ap.parse_args()
    if not os.path.exists(a.raw):
        print(f'audiocheck: no capture {a.raw}')
        return 2
    win = a.rate * a.channels // 10          # samples in 100 ms
    skip = a.rate * a.channels               # the first second
    total = loud = 0
    peak = 0
    sumsq = 0.0
    n_all = 0
    rms_hist = []
    with open(a.raw, 'rb') as f:
        f.seek(skip * 2)
        while True:
            b = f.read(win * 2)
            if len(b) < win * 2:
                break
            s = array.array('h')
            s.frombytes(b)
            if sys.byteorder != 'little':
                s.byteswap()
            ss = sum(x * x for x in s)
            rms = math.sqrt(ss / len(s))
            total += 1
            loud += rms > 64
            peak = max(peak, max(abs(x) for x in s))
            sumsq += ss
            n_all += len(s)
            rms_hist.append(rms)
    secs = total / 10
    frac = loud / total if total else 0.0
    overall = math.sqrt(sumsq / n_all) if n_all else 0.0
    verdict = 'PASS' if secs >= 10 and frac >= 0.10 else 'FAIL'
    line = (f'audiocheck {os.path.basename(a.raw)}: {secs:.1f} s judged, windows above RMS 64: {loud} of {total} '
            f'({100 * frac:.1f}%), overall RMS {overall:.1f}, peak {peak}: {verdict}')
    print(line)
    if a.out:
        with open(a.out, 'w') as f:
            f.write(line + '\n')
            # one value a second: the loudest window of each second
            for k in range(0, len(rms_hist), 10):
                f.write('%5d s  max RMS %8.1f\n' % (k // 10 + 1, max(rms_hist[k:k + 10])))
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
