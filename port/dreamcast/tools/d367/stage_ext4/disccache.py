#!/usr/bin/env python3
"""disccache.py: content-addressed disc cache on C: with NTFS hard links (lane stage-ext4, 2026-10-14).

A finished image (built and hashed on WSL ext4) crosses to Windows once, into
  $RE4DC_DISCCACHE/<sha256>/<name>      (default /mnt/c/Flycast-Evidence/_disccache)
with <name>.sha256 next to it. Scenario / evidence dirs get NTFS hard links to it, so N runs of one image cost
one image on C:. A file is "referenced" while its NTFS link count is above 1 (a scenario dir, a capture dir or a
full-play _discs dir still links it); only unreferenced entries are evicted, least recently used first, when the
cache is above its cap (RE4DC_DISCCACHE_CAP_GB, default 6) or C: would drop below the floor.
The harness only reads disc images (Flycast opens them read-only; run-emulator*.py hashes and hard-links them),
so sharing one inode is safe. Never put a file a tool writes in place (fp_iso.py redirect targets) in here.

CLI (WSL):
  disccache.py put <file> <sha256> [--name N]   copy in (if absent), print the cached path
  disccache.py link <sha256> <name> <dest>      hard-link a cached file to dest
  disccache.py evict [--need BYTES]             evict unreferenced entries (cap / floor)
  disccache.py status
"""
import fcntl, json, os, shutil, sys, time
from pathlib import Path

ROOT = Path(os.environ.get('RE4DC_DISCCACHE', '/mnt/c/Flycast-Evidence/_disccache'))
CAP = int(float(os.environ.get('RE4DC_DISCCACHE_CAP_GB', '6')) * 1024 ** 3)
FLOOR = 16 * 1024 ** 3
# the drive that receives the cache's bytes (lane world-ch31 11-03: the floor message said C: for a D: cache)
DRIVE = (ROOT.parts[2].upper() + ':') if len(ROOT.parts) > 2 and ROOT.parts[1] == 'mnt' else str(ROOT.anchor)
LOCK = Path(os.environ.get('RE4DC_STAGE_ROOT', '/root/stage')) / 'disccache.lock'

class locked:
    def __enter__(self):
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(LOCK, 'w'); fcntl.flock(self.f, fcntl.LOCK_EX); return self
    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN); self.f.close()

def entries():
    out = []
    if not ROOT.exists():
        return out
    for d in ROOT.iterdir():
        if not d.is_dir() or d.name.startswith('.'):
            continue
        files = [f for f in d.iterdir() if f.is_file() and not f.name.endswith(('.sha256', '.json'))]
        size = sum(f.stat().st_size for f in files)
        refs = max([f.stat().st_nlink - 1 for f in files] or [0])
        out.append(dict(dir=d, size=size, refs=refs, used=d.stat().st_mtime))
    return out

def evict(need=0, reserve=0, log=None):
    """Free unreferenced entries until the cache is under its cap and C: keeps need+reserve above the floor."""
    removed = []
    es = sorted(entries(), key=lambda e: e['used'])
    total = sum(e['size'] for e in es)
    for e in es:
        free = shutil.disk_usage(str(ROOT if ROOT.exists() else ROOT.parent)).free
        if total <= CAP and free - need - reserve >= FLOOR:
            break
        if e['refs'] > 0:
            continue
        shutil.rmtree(e['dir'], ignore_errors=True)
        total -= e['size']; removed.append(e['dir'].name)
        if log: log('disccache: evicted %s (%d MB)' % (e['dir'].name[:16], e['size'] >> 20))
    return removed

def lookup(sha, name):
    p = ROOT / sha / name
    s = ROOT / sha / (name + '.sha256')
    if p.is_file() and s.is_file() and s.read_text().split()[0] == sha:
        os.utime(ROOT / sha)  # LRU
        return p
    return None

def put(src, sha, name, reserve=0, log=None):
    """Copy src (already hashed on ext4) into the cache once. Returns (path, copied_bytes)."""
    src = Path(src)
    with locked():
        hit = lookup(sha, name)
        if hit:
            return hit, 0
        size = src.stat().st_size
        evict(need=size, reserve=reserve, log=log)
        free = shutil.disk_usage(str(ROOT if ROOT.exists() else ROOT.parent)).free
        assert free - size - reserve >= FLOOR, '%s too full for %d MB (free %d MB, floor 16 GiB; cache %s)' % (DRIVE, size >> 20, free >> 20, ROOT)
        ROOT.mkdir(parents=True, exist_ok=True)
        tmp = ROOT / ('.tmp-%d-%s' % (os.getpid(), sha[:16])); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
        n = 0
        with open(src, 'rb') as fi, open(tmp / name, 'xb') as fo:
            for b in iter(lambda: fi.read(1 << 22), b''):
                fo.write(b); n += len(b)
        assert (tmp / name).stat().st_size == size, 'short copy'
        (tmp / (name + '.sha256')).write_text('%s  %s\n' % (sha, name))
        dst = ROOT / sha
        if dst.exists():  # an earlier, incomplete entry
            shutil.rmtree(dst)
        os.rename(tmp, dst)
        return dst / name, n

def link(cached, dest):
    dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    os.link(cached, dest)

def main(argv):
    cmd = argv[0]
    if cmd == 'put':
        name = argv[argv.index('--name') + 1] if '--name' in argv else Path(argv[1]).name
        p, n = put(argv[1], argv[2], name, log=lambda m: print(m, file=sys.stderr))
        print(p); print('copied %d' % n, file=sys.stderr)
    elif cmd == 'link':
        p = lookup(argv[1], argv[2]); assert p, 'not cached: %s/%s' % (argv[1], argv[2]); link(p, argv[3]); print(argv[3])
    elif cmd == 'evict':
        need = int(argv[argv.index('--need') + 1]) if '--need' in argv else 0
        with locked():
            print('evicted', evict(need, log=print))
    elif cmd == 'status':
        es = entries()
        for e in sorted(es, key=lambda e: -e['used']):
            print('%s %6d MB refs=%d %s' % (e['dir'].name[:16], e['size'] >> 20, e['refs'], time.strftime('%m-%d %H:%M', time.localtime(e['used']))))
        print('entries %d, %d MB (cap %d MB), %s free %d MB' % (len(es), sum(e['size'] for e in es) >> 20, CAP >> 20, DRIVE,
                                                                 shutil.disk_usage(str(ROOT if ROOT.exists() else ROOT.parent)).free >> 20))
    else:
        sys.exit(__doc__)

if __name__ == '__main__':
    main(sys.argv[1:])
