#!/usr/bin/env python3
r"""re4_increment.py: the next RE4 increment in one command: build, stage the disc folder, push and run through
dc-qalink's bridge (lane eng-link2, 2026-11-23; docs/engine/CONSOLE_LOOP.md section 17). Windows, Python 3.10+, standard
library only; the build runs in WSL (Ubuntu-24.04) with this repository's tools/engine/build_console_disc.sh --folder.

    re4_increment.py --ref <git ref> --home <folder> [--bridge http://127.0.0.1:52080] [--push e1|fight|boss]
                     [--args "root=E1 ticks=9000 rows=skip"] [--no-build] [--no-push] [--repo <WSL repo path>]

<folder> (for example E:\RE4DC-Lanes\eng-link2\candidate\increment) holds:
  disc\   the RE4 disc folder the bridge serves whole (start the bridge once with --disc <folder>\disc --whole;
          the bridge reads the folder again at every push, so it never needs a restart between increments)
  push\   the images; MANIFEST.txt, SHA256SUMS, COMMIT of the increment
The new stage is built beside it (<folder>.next), checked against its SHA256SUMS, then copied over the served folder:
only files whose bytes changed are copied, files that went away are deleted. Then the image is pushed with
re4_bridge_proof.py --plan increment (push, live rows, one screen grab; the run keeps going). Only the QA Link loader is
on the SD card: no card change between increments.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def wsl_path(p):
    p = str(Path(p).resolve())
    return '/mnt/%s/%s' % (p[0].lower(), p[3:].replace('\\', '/'))


def sync(src, dst):
    """dst made equal to src: changed or new files copied, gone files deleted; returns (copied, deleted, kept)"""
    copied = deleted = kept = 0
    want = set()
    for root, _, files in os.walk(src):
        for n in files:
            s = Path(root) / n
            rel = s.relative_to(src)
            want.add(str(rel).lower())
            d = Path(dst) / rel
            if d.exists() and d.stat().st_size == s.stat().st_size and sha(d) == sha(s):
                kept += 1
                continue
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(s, d)
            copied += 1
    for root, _, files in os.walk(dst):
        for n in files:
            d = Path(root) / n
            if str(d.relative_to(dst)).lower() not in want:
                d.unlink()
                deleted += 1
    return copied, deleted, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', default='origin/engine')
    ap.add_argument('--home', required=True)
    ap.add_argument('--bridge', default='http://127.0.0.1:52080')
    ap.add_argument('--push', default='e1', choices=['e1', 'fight', 'boss'])
    ap.add_argument('--args', default='root=E1 ticks=9000 rows=skip')
    ap.add_argument('--repo', default='/root/work/lanes/eng-link2')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--no-push', action='store_true')
    a = ap.parse_args()
    home = Path(a.home)
    nxt = Path(str(home) + '.next')
    t0 = time.time()
    if not a.no_build:
        cmd = ('export PRISTINE=${PRISTINE:-/root/work/lanes/eng-skel2-data/pristine-colb} CDISC_JOBS=${CDISC_JOBS:-2} '
               'WORK=${WORK:-/root/work/re4-increment-work}; '
               'bash %s/port/dreamcast/tools/engine/build_console_disc.sh --folder --ref %s --out %s'
               % (a.repo, a.ref, wsl_path(nxt)))
        print('build and stage: %s' % a.ref, flush=True)
        rc = subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'bash', '-c', cmd]).returncode
        if rc:
            print('build failed (rc %d): nothing changed in %s' % (rc, home))
            return 1
        sums = (nxt / 'SHA256SUMS').read_text().split('\n')
        bad = [l for l in sums if l.strip() and sha(nxt / l.split(None, 1)[1].strip()) != l.split()[0]]
        if bad:
            print('the stage does not match its SHA256SUMS (%d files): nothing changed' % len(bad))
            return 1
        home.mkdir(parents=True, exist_ok=True)
        c, d, k = sync(nxt / 'disc', home / 'disc')
        for n in ('MANIFEST.txt', 'SHA256SUMS', 'COMMIT'):
            shutil.copyfile(nxt / n, home / n)
        if (home / 'push').exists():
            shutil.rmtree(home / 'push')
        shutil.copytree(nxt / 'push', home / 'push')
        shutil.rmtree(nxt)
        print('disc folder %s: %d files copied, %d deleted, %d unchanged (%.0f s so far)' % (home / 'disc', c, d, k,
                                                                                            time.time() - t0), flush=True)
    if a.no_push:
        return 0
    out = home / 'runs' / time.strftime('%Y%m%d-%H%M%S')
    rc = subprocess.run([sys.executable, str(HERE / 're4_bridge_proof.py'), a.bridge, str(out), '--push',
                         str(home / 'push' / ('%s.elf' % a.push)), '--args', a.args, '--plan', 'increment']).returncode
    print('pushed %s: %s (%.0f s in all); the run keeps going; QA Link Cloud shows it live' % (a.push, out,
                                                                                               time.time() - t0))
    return rc


if __name__ == '__main__':
    sys.exit(main())
