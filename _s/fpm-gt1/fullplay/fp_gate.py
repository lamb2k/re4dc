"""fp_gate.py: the full-play release gate (Windows Python; fullplay.sh wraps it). See README.md "Full-play gate".

    python fp_gate.py <release zip | gdemu dir> [--label L] [--evidence DIR] [--only a,b] [--jobs N]
                      [--known FILE] [--keep-discs]

1. Release: the zip's gdemu/ tracks (extracted next to the evidence) or the gdemu dir, each track checked against
   the package's SHA256SUMS (the zip's inner SHA256SUMS.txt; for a dir, a sibling *GDEMU.zip's inner sums or a
   SHA256SUMS.txt naming gdemu/ files). No matching sums = FAIL.
2. Prep (WSL fp_prep.sh): release game tree, the release build (binary = the disc's 1ST_READ.BIN), the twin and
   the identity proof (fp_twin.sh), the twin and release-binary base discs with the data-tree proof (fp_master.sh).
3. Segments (segments.conf) in parallel, longest first, fp_run.py each (up to --jobs Flycasts, and never more than
   RE4DC_MAX_FLYCASTS machine-wide).
4. Verdict (fp_check.py): REPORT.md + verdict.json. Exit 0 PASS, 1 FAIL, 2 tool error.
Base discs (_discs/, ~1.7 GB) are deleted at the end unless --keep-discs (their sha256 stay in prep.json / base dirs).
"""
import argparse, concurrent.futures as cf, datetime, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fp_check

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()

def wslpath(p):
    p = str(Path(p).resolve())
    if p.startswith('\\\\wsl.localhost\\Ubuntu-24.04'):
        return p[len('\\\\wsl.localhost\\Ubuntu-24.04'):].replace('\\', '/')
    return '/mnt/' + p[0].lower() + p[2:].replace('\\', '/')

def sums_from_zip(z):
    with zipfile.ZipFile(z) as zf:
        n = next((n for n in zf.namelist() if n.endswith('SHA256SUMS.txt')), None)
        if not n:
            return None
        return {l.split()[1].split('/')[-1]: l.split()[0] for l in zf.read(n).decode().splitlines() if l.strip()}

def release_tracks(src, ev, log):
    """returns (gdemu dir, {track: sha}, verified bool, note)"""
    src = Path(src)
    files = ('disc.gdi', 'track01.bin', 'track02.raw', 'track03.bin')
    if src.is_file() and src.suffix.lower() == '.zip':
        sums = sums_from_zip(src)
        g = ev / '_release' / 'gdemu'; g.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as zf:
            for n in zf.namelist():
                b = n.split('/')[-1]
                if b in files:
                    with zf.open(n) as fi, open(g / b, 'wb') as fo:
                        shutil.copyfileobj(fi, fo, 1 << 22)
        origin = 'zip %s (inner SHA256SUMS.txt)' % src.name
    else:
        g = src if (src / 'disc.gdi').exists() else src / 'gdemu'
        sums, origin = None, None
        for z in sorted(z for z in g.parent.glob('*GDEMU*.zip') if '-QA-' not in z.name):  # QA disc zip: other tracks
            sums = sums_from_zip(z); origin = 'zip %s (inner SHA256SUMS.txt)' % z.name
            if sums:
                break
        if not sums:
            for s in (g.parent / 'SHA256SUMS.txt', g / 'SHA256SUMS.txt'):
                if s.exists() and 'track03' in s.read_text():
                    sums = {l.split()[1].split('/')[-1]: l.split()[0] for l in s.read_text().splitlines() if l.strip()}
                    origin = str(s)
                    break
    got = {f: sha(g / f) for f in files if (g / f).exists()}
    ok = bool(sums) and all(sums.get(f) == got.get(f) for f in files)
    note = '%s: %s' % (origin, 'all 4 tracks match' if ok else 'MISMATCH or no sums: ' + json.dumps(dict(sums=sums, got=got)))
    log('release tracks: ' + note)
    return g, got, ok, note

def wsl(script_text, ev, name, log):
    sp = ev / ('_%s.sh' % name)
    sp.write_text(script_text.replace('\r', ''), newline='\n')
    t = time.time()
    p = subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'bash', wslpath(sp)], capture_output=True, text=True,
                       errors='replace')
    (ev / ('_%s.log' % name)).write_text(p.stdout + p.stderr)
    log('%s rc=%d %.0fs' % (name, p.returncode, time.time() - t))
    return p.returncode, p.stdout + p.stderr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('release'); ap.add_argument('--label'); ap.add_argument('--evidence')
    ap.add_argument('--only'); ap.add_argument('--jobs', type=int, default=int(os.environ.get('FP_JOBS', '8')))
    ap.add_argument('--known', default=str(HERE / 'known-issues.txt')); ap.add_argument('--keep-discs', action='store_true')
    ap.add_argument('--conf', default=str(HERE / 'segments.conf'), help='segment conf file(s), comma-separated (crash.conf: the align crash suite; segments-ch22.conf: chapters 2-2/2-3, route releases)')
    ap.add_argument('--align', action='store_true', help='every segment on the hwmodel Flycast with the align logger (fp_run.py --align)')
    a = ap.parse_args()
    # each bare name: the conf next to this script
    a.conf = ','.join(c if Path(c).exists() else str(HERE / c) for c in a.conf.split(','))
    t0 = time.time()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    label = a.label or re.sub(r'[^A-Za-z0-9]', '', Path(a.release).stem)[-12:] or 'rel'
    ev = Path(a.evidence or r'C:\Flycast-Evidence\re4-dreamcast\fullplay-%s\%s-%s' % (stamp[:8], label, stamp[9:]))
    ev.mkdir(parents=True, exist_ok=False)
    logf = open(ev / 'gate.log', 'a')
    def log(m):
        line = '%s %s' % (datetime.datetime.now().strftime('%H:%M:%S'), m)
        print(line, flush=True); logf.write(line + '\n'); logf.flush()
    meta = dict(input=str(a.release), label=label, start=stamp, segments=[], conf=str(a.conf), align=a.align)
    log('full-play gate %s -> %s' % (a.release, ev))
    g, tracks, ok, note = release_tracks(a.release, ev, log)
    meta.update(tracks=tracks, tracks_ok=ok, tracks_verified=note)
    (ev / 'gate.json').write_text(json.dumps(meta, indent=1))
    if not ok:
        log('FAIL: release tracks not verified'); fp_check.main([str(ev), '--known', a.known, '--conf', str(a.conf)]); return 1
    tp = time.time()
    fpb = os.environ.get('FP_BUILD', '')  # WSL path of the release build's out dir, when the search finds none
    # lane stage-ext4 (default on): fp_master.sh masters the bases on ext4, caches track03.iso once in the C: disc cache
    # and hard-links it into _discs; RE4DC_STAGE_EXT4=0 = the old path (master straight into _discs through /mnt/c)
    ext4_on = os.environ.get('RE4DC_STAGE_EXT4', '1') != '0'
    ext4 = 'export RE4DC_STAGE_EXT4=%d\n' % ext4_on
    fpx = os.environ.get('FP_TWIN_EXTRA', '')  # extra twin-only diagnostic knobs (fp_prep.sh), e.g. WEP_TARGET_GUARD=2
    rc, out = wsl(('export FP_BUILD=%s\n' % fpb if fpb else '') + ("export FP_TWIN_EXTRA='%s'\n" % fpx if fpx else '') + ext4 + 'set -o pipefail\nbash %s %s %s %s %s 2>&1\n' % (
        "'%s'" % wslpath(HERE / 'fp_prep.sh'), "'%s'" % wslpath(g), tracks['track03.bin'], label, "'%s'" % wslpath(ev)), ev, 'prep', log)
    meta['prep_wall'] = '%.0f s' % (time.time() - tp)
    if rc != 0 or 'PREP_OK' not in out:
        log('prep failed:\n' + out[-3000:])
        meta['prep_error'] = out[-3000:]
        (ev / 'gate.json').write_text(json.dumps(meta, indent=1))
        return 2
    prep = json.loads((ev / 'prep.json').read_text())
    if ext4_on:  # the bases were hashed on ext4: prove the cached copy natively (no 9p re-read)
        for d in ('twin', 'rel'):
            b = ev / '_discs' / d
            h = hashlib.sha256()
            with open(b / 'track03.iso', 'rb') as f:
                for blk in iter(lambda: f.read(1 << 22), b''):
                    h.update(blk)
            if h.hexdigest() != (b / 'track03.sha256').read_text().strip():
                log('prep failed: %s/track03.iso copy does not match track03.sha256' % d)
                return 2
        log('ext4 bases: copies match track03.sha256')
    segs = fp_check.parse_conf(a.conf)
    if a.only:
        segs = [s for s in segs if s['name'] in a.only.split(',')]
    segs.sort(key=lambda s: -s['seconds'])
    meta['segments'] = [s['name'] for s in segs]
    (ev / 'gate.json').write_text(json.dumps(meta, indent=1))
    vmu_save = os.environ.get('FP_VMU_SAVE', r'C:\Flycast-Evidence\re4-dreamcast\fullplay-20261014\_inputs\user-a1-20261012.bin')
    S = HERE / 'segments'
    # Disc space (2026-10-14): each base (_discs/twin, _discs/rel) and the zip's _release extraction is deleted as soon
    # as the last segment that uses it has ended (their sha256 stay in prep.json / gate.json), not at the gate's end.
    import threading
    left = {k: sum(1 for s in segs if s['disc'] == k) for k in ('real', 'twin', 'rel')}
    lock = threading.Lock()
    def drop(kind):
        if a.keep_discs:
            return
        if kind == 'real':
            rel = ev / '_release'
            if rel.exists():
                shutil.rmtree(rel, ignore_errors=True); log('released _release (no real-disc segment left)')
            return
        gone = []
        for f in ('track03.iso', 'track02.raw', 'track01-template.iso'):
            p = ev / '_discs' / kind / f
            if p.exists():
                p.unlink(); gone.append(f)
        if gone:
            log('released _discs/%s (no %s segment left)' % (kind, kind))
    for k, n in left.items():
        if n == 0:
            drop(k)
    def run(s):
        cmd = [sys.executable, str(HERE / 'fp_run.py'), '--cap', str(ev / s['name']), '--seconds', str(s['seconds']),
               '--name', s['name'], '--grace', str(s['grace'])] + (['--align'] if a.align else [])
        if s['disc'] == 'real':
            cmd += ['--disc', str(g), '--syms', prep['syms_release']]
        else:
            cmd += ['--base', str(ev / '_discs' / s['disc']), '--syms', prep['syms_%s' % ('twin' if s['disc'] == 'twin' else 'release')]]
            if s['warp'] != '-':
                cmd += ['--warp', str(S / s['warp'])]
            if s['pad'] != '-':
                cmd += ['--pad', str(S / s['pad'])]
            w11 = S / s['warp'].replace('-warp.txt', '-w11.txt')  # W11_FIXTURE twin (FP_TWIN_EXTRA=W11_FIXTURE=1)
            if s['warp'] != '-' and w11 != S / s['warp'] and w11.exists():
                cmd += ['--w11', str(w11)]
        if s['keys'] != '-':
            cmd += ['--keys', str(S / s['keys'])]
        if s['vmu'] == 'save':
            cmd += ['--vmu', vmu_save]
        if s['stop']:
            cmd += ['--stop', s['stop']]
        t = time.time()
        log('start %s (%s, %s s max)' % (s['name'], s['disc'], s['seconds']))
        p = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
        (ev / ('%s-runner.log' % s['name'])).write_text(p.stdout + p.stderr)
        r, _ = fp_check.check_segment(ev, s, fp_check.parse_known(a.known, prep['release_tree_commit']))
        log('done  %s %s %.0fs%s' % (s['name'], r['result'], time.time() - t,
                                     ('  ' + '; '.join('%s: %s' % (f['cat'], f['what']) for f in r['failures'][:3])) if r['failures'] else ''))
        with lock:
            left[s['disc']] -= 1
            if left[s['disc']] == 0:
                drop(s['disc'])
        return s['name']
    tr = time.time()
    subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                      r'C:\Game Dev\Emulators\_private_tools\Mute-Flycast.ps1', '-Watch'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futs = []
        for s in segs:
            futs.append(pool.submit(run, s))
            time.sleep(3)  # stagger boots (disc reads, host load)
        for f in futs:
            f.result()
    meta['runs_wall'] = '%.0f s' % (time.time() - tr)
    meta['wall'] = '%.1f min' % ((time.time() - t0) / 60)
    (ev / 'gate.json').write_text(json.dumps(meta, indent=1))
    if not a.keep_discs:
        for d in ('twin', 'rel'):
            for f in ('track03.iso', 'track02.raw', 'track01-template.iso'):
                p = ev / '_discs' / d / f
                if p.exists():
                    p.unlink()
        rel = ev / '_release'
        if rel.exists():
            shutil.rmtree(rel)
    rc = fp_check.main([str(ev), '--known', a.known, '--conf', str(a.conf)])
    log('verdict rc=%d, wall %s' % (rc, meta['wall']))
    return rc

if __name__ == '__main__':
    sys.exit(main())
