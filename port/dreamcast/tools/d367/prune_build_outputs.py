#!/usr/bin/env python3
"""prune_build_outputs.py: delete REBUILDABLE build outputs (disk hygiene rule, user 2026-10-15).

Run it through prune_build_outputs.sh. Default is a dry run; --apply deletes and writes a manifest
(path, bytes, mtime, nlink, reason) to /root/probe/_prune-manifests/<timestamp>.tsv.

What it deletes (only these):
  objdir   in a build objdir (out-*, obj, obj-*, build, build-*, builds, *-obj, objdir*) that holds .o files:
           *.o *.d *.gch *.elf *.ovl (objects, deps, linked images; .a archives stay). Logs, maps, *.txt, *.json,
           sha256/candidate/syms files and generated headers stay.
  disc     staged disc images anywhere: *.iso *.cdi *.chd track*.raw track*.bin, and *.bin / *.img > 50 MB.
           .gdi/.cue sheets and disc.sha256 files stay. Images > 1.2 GB or with the GameCube disc magic are
           treated as possible source discs and kept.
  zip      *.zip > 50 MB inside an objdir or disc unit only (intermediate packages / copies).

Where and when:
  - WSL root /root/probe. A "unit" (the objdir, or the directory holding a disc image) is a candidate only
    when its newest mtime (any file or dir below it) is older than --idle-hours (6), and, when it sits in a
    git worktree, the whole worktree is idle too. Each file is re-checked (mtime) right before it is deleted.
  - Windows evidence roots (C: and D: Flycast-Evidence\\re4-dreamcast): disc images only, in evidence dirs idle
    for --idle-hours, through the PowerShell twin prune_build_outputs.ps1 (WSL interop; it reads the reference
    corpus this script writes to _prune-manifests/refs-latest.txt and tokens-latest.txt). Never anything under a data/ dir or a hwmodel-bin dir; never flycast.exe.

Never:
  - source files, .git, logs, traces, captures, results (*.log *.md *.json *.csv *.tsv *.txt RESULT* report*)
    -- the extension allow-list above is the only thing deleted;
  - protected names (any path component): the active lanes (sh4zam t2exact farhalf worldlod skiptick ps2cast
    t13rc t14rc fullplay), hwmodel-bin, re4-assets-private, the release / benchmark / SD folders, plus
    PRUNE_PROTECT (space separated, extra names or path prefixes) and the lines of
    /root/probe/_prune-manifests/keep.txt (a path prefix or a token per line);
  - release tokens (current release / candidate ids, KEEP_TOKENS below);
  - anything the harness or docs reference: every unit's name (when distinctive) and full path are looked up
    in a reference corpus (testing skills + their scripts, tools/d367 of the main checkout and the release
    trees, d367-agents/warp scripts, the harness top-level files, workspace *.md of the last 3 days,
    keep.txt). A hit keeps the unit (the BASE disc trap).
  - a worktree with uncommitted or unpushed work keeps its source; before any of its objdirs is pruned the
    tool saves git diff (binary, incl. staged), git stash list, untracked list and a bundle of the unpushed
    commits into /root/probe/_prune-manifests/backups/.

Fixes 2026-10-15 evening: idleness is the newest FILE mtime (directory mtimes are bumped by a prune itself);
out-*/build-* dirs whose objects were already pruned still count as build dirs (their ELFs/overlays go);
a unit holding a process cwd or open file is skipped; evening lanes/releases added to the protected names.

Options: --apply, --idle-hours H, --no-windows, --windows-only, --top NAME (only /root/probe/NAME; repeat),
         --list (print every unit, not only the summary), --quiet.
"""
import argparse, bisect, fnmatch, os, re, stat, subprocess, sys, time
from collections import defaultdict
from pathlib import Path

PROBE = '/root/probe'
MAN = Path(PROBE) / '_prune-manifests'
WIN_ROOTS = ['/mnt/c/Flycast-Evidence/re4-dreamcast', '/mnt/d/Flycast-Evidence/re4-dreamcast']
MAIN_REPO = '/root/work/re4-dreamcast'
SKILLS = '/mnt/c/Users/lambd/.claude/skills'
WORKSPACE = '/mnt/c/Game Dev/Emulators'
HARNESS = '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1'

PROTECT_NAMES = ['sh4zam*', 't2exact*', 'farhalf*', 'worldlod*', 'skiptick*', 'ps2cast*', 't13rc', 't14rc',
                 't14', 'rc', 'fullplay', 'hwmodel-bin', 're4-assets-private', 'RE4DC-Test13-*',
                 'RE4DC-Test14-Candidate*', 'RE4DC-Benchmark-Part1*', 'RE4DC-Benchmark-Part2*',
                 'RE4DC-Benchmark-ZAMR*', 'RE4DC-Benchmark-WLODP*', 'RE4DC-Bench-LinkOrder2*',
                 'RE4DC-Bench-LinkOrder-D*', 'LO Control*', 'RE4DC-SD-Backups*', 'RE4DC-superseded-discs*',
                 '_prune-manifests', '_archive*', '_bundles', '_wip-backup*', 't15*', 'out-t13*', 'out-t14*', 'out-t15*', '*poc101*', '*POC101*', 'poc*', 'logicwaste*', 'worldvert*', 'leonlod*', 't14rc*', 'kit-check-test14', 'discread', 'd3verify', '*LinkOrder*', 'abbench', 'benchwork', 'iso-src*', 'mirror*', 're4data', 'orig', 'orig-*']
# current release (test 13 source 05e5ff76) and the test 14 candidate (source bb2c4c51, image aa0f40a1, t14/rc 63df6c0f)
KEEP_TOKENS = ['05e5ff76', 'bb2c4c51', 'aa0f40a1', '63df6c0f', 'e2048df6', '12dddcac']

OBJDIR_RE = re.compile(r'^(out-.+|obj|obj[-_.].+|objs|build|build[-_.].+|builds|.+-obj|objdir.*|_build)$')
OBJ_EXT = {'.o', '.d', '.gch', '.elf', '.ovl'}
DISC_EXT = {'.iso', '.cdi', '.chd'}
TRACK_RE = re.compile(r'^track\d+\.(raw|bin|iso)$', re.I)
BIG = 50 * 1024 ** 2
SRC_DISC_MAX = int(1.2 * 1024 ** 3)
GENERIC = {'obj', 'objs', 'build', 'builds', 'out', 'disc', 'discs', 'tree', 'base', 'work', 'stage', 'tmp',
           'data', 'bench', 'gdemu', 'logs', 'fix', 'hold', 'route', 'lanes'}


def _open_paths():
    s = set()
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        for l in ['cwd'] + ['fd/' + x for x in (os.listdir('/proc/%s/fd' % pid) if os.access('/proc/%s/fd' % pid, os.R_OK) else [])]:
            try:
                p = os.readlink('/proc/%s/%s' % (pid, l))
            except OSError:
                continue
            if p.startswith('/root/probe'):
                s.add(p)
    return sorted(s)


OPEN_PATHS = _open_paths()


def log(*a):
    print(*a, flush=True)


def matches_protect(parts, extra):
    for p in parts:
        for pat in PROTECT_NAMES:
            if fnmatch.fnmatchcase(p, pat):
                return 'protected name ' + p
    for e in extra:
        if '/' not in e:
            if e in parts:
                return 'keep ' + e
    return None


def build_corpus(extra_files):
    """Text of everything that may reference a disc / objdir path."""
    srcs = []
    def add_tree(d, exts=('.sh', '.py', '.md', '.txt', '.json', '.conf', '.ps1', '.env', '.mk', '.cfg', '.tsv')):
        if not os.path.isdir(d):
            return
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x not in ('.git', '__pycache__', 'obj') and not x.startswith('out-')]
            for f in files:
                if f.endswith(exts) or '.' not in f:
                    srcs.append(os.path.join(root, f))
    for s in Path(SKILLS).glob('re4*'):
        add_tree(str(s))
    trees = [MAIN_REPO]
    for t in ('lanes-20261015/t14rc/tree', 'lanes-20261015/t14rc/bench', 'lanes-20261015/t13rc/tree'):
        trees.append(os.path.join(PROBE, t))
    for t in trees:
        add_tree(os.path.join(t, 'port/dreamcast/tools/d367'))
    add_tree(os.path.dirname(os.path.abspath(__file__)))     # this tree's tools/d367 (stage_ext4 names the BASE disc)
    add_tree(os.path.join(HARNESS, 'stage-ext4'))            # the stager the harness actually runs
    w = os.path.join(PROBE, 'd367-agents/warp')
    if os.path.isdir(w):
        srcs += [os.path.join(w, f) for f in os.listdir(w) if f.endswith(('.sh', '.py', '.txt', '.md'))]
    if os.path.isdir(HARNESS):
        srcs += [os.path.join(HARNESS, f) for f in os.listdir(HARNESS)
                 if f.endswith(('.py', '.json', '.txt', '.md', '.ps1', '.cfg'))]
    now = time.time()
    if os.path.isdir(WORKSPACE):
        for f in os.listdir(WORKSPACE):
            p = os.path.join(WORKSPACE, f)
            if f.endswith('.md') and os.path.isfile(p) and now - os.path.getmtime(p) < 3 * 86400:
                srcs.append(p)
    srcs += extra_files
    # Scripts, configs, keep.txt and the skills' SKILL.md files ("code") protect a unit by any path below it or
    # by its distinctive name. Other *.md docs cite evidence dirs as results all the time, so a doc protects only
    # what it names down to the disc image file itself (a path ending in a disc extension).
    code, docs = [], []
    for p in srcs:
        try:
            if os.path.getsize(p) > 8 * 1024 ** 2:
                continue
            with open(p, 'rb') as f:
                t = f.read().decode('utf-8', 'replace')
        except OSError:
            continue
        (docs if p.endswith('.md') and not p.endswith('SKILL.md') else code).append(t)

    def paths(blob):
        blob = blob.replace('\\\\', '/').replace('\\', '/')
        refs = set(re.findall(r'/root/probe/[A-Za-z0-9_.+/-]+', blob))
        for m in re.findall(r'''([CDcd]:/[^\s"'`<>|*?]+)''', blob):
            refs.add('/mnt/%s/%s' % (m[0].lower(), m[3:]))
        return blob, {r.rstrip('/.,;:)') for r in refs}
    cblob, refs = paths('\n'.join(code))
    tokens = set(re.findall(r'[A-Za-z0-9_.+-]+', cblob))
    _, drefs = paths('\n'.join(docs))
    disc_re = re.compile(r'(\.(iso|cdi|chd|gdi|cue|img|bin|raw|elf)|/track\d+\.\w+)$', re.I)
    refs |= {r for r in drefs if disc_re.search(r)}
    return sorted(refs), tokens, len(srcs)


def referenced(refs, p):
    """True if a referenced path equals p or lies below it."""
    i = bisect.bisect_left(refs, p)
    while i < len(refs) and refs[i].startswith(p):
        r = refs[i]
        if len(r) == len(p) or r[len(p)] == '/':
            return True
        i += 1
    return False


def distinctive(name):
    return (len(name) >= 5 and name.lower() not in GENERIC and re.search(r'\d', name) is not None) or \
           (len(name) >= 8 and name.lower() not in GENERIC and '-' in name)


class Scan:
    def __init__(self, cutoff):
        self.cutoff = cutoff
        self.newest = {}          # dir -> newest mtime below it (files and dirs)
        self.cands = []           # (path, size, mtime, nlink, kind, unit)
        self.skipped_big = []     # (path, size, reason)
        self.objunits = set()

    def walk(self, d, unit_obj=None, depth=0):
        """Returns newest mtime under d. unit_obj = enclosing objdir (outermost)."""
        try:
            st = os.lstat(d)
        except OSError:
            return 0
        newest = 0
        try:
            it = list(os.scandir(d))
        except OSError:
            return newest
        has_o = False
        for e in it:
            name = e.name
            try:
                if e.is_symlink():
                    continue
                if e.is_dir(follow_symlinks=False):
                    if name == '.git':
                        continue
                    sub_unit = unit_obj
                    if unit_obj is None and OBJDIR_RE.match(name):
                        sub_unit = e.path
                    n = self.walk(e.path, sub_unit, depth + 1)
                    newest = max(newest, n)
                    continue
                if not e.is_file(follow_symlinks=False):
                    continue
                s = e.stat(follow_symlinks=False)
            except OSError:
                continue
            newest = max(newest, s.st_mtime)
            if name == '.git':
                continue
            low = name.lower()
            ext = os.path.splitext(low)[1]
            kind = None
            if unit_obj is not None and ext in OBJ_EXT:
                kind = 'objdir'
                if ext == '.o':
                    has_o = True
            if ext in DISC_EXT or TRACK_RE.match(low) or (ext in ('.bin', '.img') and s.st_size > BIG):
                if s.st_size > SRC_DISC_MAX:
                    self.skipped_big.append((e.path, s.st_size, 'disc > 1.2 GB (possible source disc)'))
                    kind = None
                elif is_gc_disc(e.path):
                    self.skipped_big.append((e.path, s.st_size, 'GameCube disc magic'))
                    kind = None
                else:
                    kind = 'disc'
            elif ext == '.zip' and s.st_size > BIG:
                if unit_obj is not None:
                    kind = 'zip'
                else:
                    self.skipped_big.append((e.path, s.st_size, 'zip outside a build dir (left)'))
            if kind:
                self.cands.append([e.path, s.st_size, s.st_mtime, s.st_nlink, kind, unit_obj])
        if has_o and unit_obj:
            self.objunits.add(unit_obj)
        self.newest[d] = newest
        return newest


def is_gc_disc(p):
    try:
        with open(p, 'rb') as f:
            h = f.read(0x20)
        return len(h) >= 0x20 and h[0x1c:0x20] == b'\xc2\x33\x9f\x3d'
    except OSError:
        return True


def git(wt, *args, **kw):
    return subprocess.run(['git', '-C', wt] + list(args), capture_output=True, **kw)


def worktree_of(path, cache):
    """Nearest ancestor holding a .git entry (worktree root), or None."""
    d = os.path.dirname(path)
    chain = []
    while d and d != '/' and d.startswith(PROBE):
        if d in cache:
            r = cache[d]
            break
        chain.append(d)
        if os.path.lexists(os.path.join(d, '.git')):
            r = d
            break
        d = os.path.dirname(d)
    else:
        r = None
    for c in chain:
        cache[c] = r
    return r


def worktree_state(wt):
    st = git(wt, 'status', '--porcelain', '--untracked-files=no')
    dirty = bool(st.stdout.strip()) if st.returncode == 0 else True
    rl = git(wt, 'rev-list', '--count', 'HEAD', '--not', '--remotes')
    try:
        unpushed = int(rl.stdout.strip() or 0)
    except ValueError:
        unpushed = -1
    return dirty, unpushed


def backup_worktree(wt, ts):
    bdir = MAN / 'backups'
    bdir.mkdir(parents=True, exist_ok=True)
    tag = wt.replace(PROBE + '/', '').replace('/', '__')
    base = bdir / ('%s-%s' % (tag, ts))
    head = git(wt, 'rev-parse', 'HEAD').stdout.decode().strip()
    br = git(wt, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.decode().strip()
    with open(str(base) + '.diff', 'wb') as f:
        f.write(git(wt, 'diff', 'HEAD', '--binary').stdout)
    info = ['worktree %s' % wt, 'head %s' % head, 'branch %s' % br, '', '# git stash list (shared repo)']
    info.append(git(wt, 'stash', 'list').stdout.decode('utf-8', 'replace'))
    info.append('# untracked (not saved; source only, objdirs are ignored)')
    info.append(git(wt, 'ls-files', '--others', '--exclude-standard').stdout.decode('utf-8', 'replace')[:200000])
    info.append('# unpushed commits')
    info.append(git(wt, 'log', '--oneline', 'HEAD', '--not', '--remotes').stdout.decode('utf-8', 'replace'))
    (Path(str(base) + '.txt')).write_text('\n'.join(info))
    n = git(wt, 'rev-list', '--count', 'HEAD', '--not', '--remotes').stdout.decode().strip()
    if n and n != '0':
        r = git(wt, 'bundle', 'create', str(base) + '.bundle', 'HEAD', '--not', '--remotes')
        if r.returncode != 0:
            raise RuntimeError('bundle failed for %s: %s' % (wt, r.stderr.decode()[:300]))
    return str(base)


def human(n):
    return '%.2f GB' % (n / 1024 ** 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--idle-hours', type=float, default=float(os.environ.get('PRUNE_IDLE_HOURS', '6')))
    ap.add_argument('--no-windows', action='store_true')
    ap.add_argument('--windows-only', action='store_true')
    ap.add_argument('--top', action='append', default=[])
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    now = time.time()
    cutoff = now - a.idle_hours * 3600
    ts = time.strftime('%Y%m%d-%H%M%S')
    MAN.mkdir(parents=True, exist_ok=True)

    extra = os.environ.get('PRUNE_PROTECT', '').split()
    keepf = MAN / 'keep.txt'
    keep_lines = []
    if keepf.exists():
        keep_lines = [x.strip() for x in keepf.read_text().splitlines() if x.strip() and not x.startswith('#')]
    extra += keep_lines
    # the rr release candidate (rr/README.md): its objdirs (out-rr<sha7>*, out-fprr<sha7>*) sit idle for hours while
    # the full tier, packaging and the release read them; 11-01 a prune took the Test 25 release ELF mid-package.
    try:
        lg = Path('/root/rr/state/last-good').read_text()
        s7 = next(l.split('=', 1)[1].strip() for l in lg.splitlines() if l.startswith('sha='))[:7]
        PROTECT_NAMES.extend(['out-rr%s*' % s7, 'out-fprr%s*' % s7])
    except (OSError, StopIteration):
        pass
    keep_prefixes = [e.rstrip('/') for e in extra if '/' in e]
    keep_tokens = set(KEEP_TOKENS) | {e for e in extra if '/' not in e}

    refs, ctokens, nsrc = build_corpus([str(keepf)] if keepf.exists() else [])
    log('prune: %s, idle > %.1f h, reference corpus %d files / %d tokens' %
        ('APPLY' if a.apply else 'DRY RUN', a.idle_hours, nsrc, len(ctokens)))

    roots = []
    if not a.windows_only:
        if a.top:
            roots += [('wsl', os.path.join(PROBE, t)) for t in a.top]
        else:
            roots += [('wsl', PROBE)]
    for name, rows in (('refs-latest.txt', refs), ('tokens-latest.txt', sorted(t for t in ctokens if distinctive(t)))):
        tmp = MAN / ('.%s.%d' % (name, os.getpid()))
        tmp.write_text(''.join(r + chr(10) for r in rows))
        os.replace(tmp, MAN / name)

    units = {}   # unit -> dict
    skipped = defaultdict(lambda: [0, 0, ''])   # unit -> bytes, files, reason
    wtcache, wtstate = {}, {}
    big_src = []
    for side, root in roots:
        t0 = time.time()
        sc = Scan(cutoff)
        if side == 'wsl' and root == PROBE:
            for e in sorted(os.scandir(PROBE), key=lambda e: e.name):
                if e.is_dir(follow_symlinks=False) and not e.is_symlink():
                    if e.name.startswith(('_prune-manifests', '_archive')):
                        continue
                    sc.walk(e.path, e.path if OBJDIR_RE.match(e.name) else None)
                elif e.is_file(follow_symlinks=False):
                    pass
        else:
            sc.walk(root)
        big_src += sc.skipped_big
        if not a.quiet:
            log('scanned %s in %.0f s: %d candidate files' % (root, time.time() - t0, len(sc.cands)))
        for path, size, mtime, nlink, kind, uobj in sc.cands:
            if side == 'win':
                rel = path[len(root) + 1:].split('/')
                unit = os.path.join(root, rel[0]) if len(rel) > 1 else path
                top = root
                parts = rel
                if any(p.lower() == 'data' for p in rel[:-1]) or 'hwmodel-bin' in rel or kind != 'disc':
                    continue
            else:
                if kind == 'objdir':
                    if uobj not in sc.objunits and not os.path.basename(uobj).startswith(('out-', 'build-')):
                        continue           # an objdir-named dir without .o files: not a build dir
                    unit = uobj
                else:
                    unit = uobj if uobj else os.path.dirname(path)
                rel = path[len(PROBE) + 1:].split('/')
                top = os.path.join(PROBE, rel[0])
                parts = rel
            u = units.get(unit)
            if u is None:
                u = units[unit] = dict(unit=unit, top=top, side=side, files=[], bytes=0, shared=0, reason=None,
                                       wt=None, newest=sc.newest.get(unit, now), kinds=set())
                # --- unit level protections
                why = matches_protect(parts[:-1], extra)
                if not why:
                    for p in keep_prefixes:
                        if unit.startswith(p) or path.startswith(p):
                            why = 'keep.txt prefix ' + p
                            break
                if not why:
                    for tkn in keep_tokens:
                        if tkn in unit:
                            why = 'release token ' + tkn
                            break
                if not why and any(op == unit or op.startswith(unit + '/') for op in OPEN_PATHS):
                    why = 'in use by a process'
                if not why and u['newest'] > cutoff:
                    why = 'active (%.1f h ago)' % ((now - u['newest']) / 3600)
                if not why:
                    uname = os.path.basename(unit)
                    if referenced(refs, unit) or (distinctive(uname) and uname in ctokens):
                        if kind == 'objdir' or uobj:
                            # a referenced build dir (e.g. an ELF registered in the harness programs json):
                            # keep its ELF, overlays and discs, prune only objects and deps
                            u['objects_only'] = 'referenced (%s): objects only' % uname
                        else:
                            why = 'referenced by harness/docs (%s)' % uname
                if not why and side == 'wsl':
                    wt = worktree_of(path, wtcache)
                    if wt:
                        u['wt'] = wt
                        if wt not in wtstate:
                            wn = sc.newest.get(wt)
                            if wn is None:
                                wn = max(os.lstat(wt).st_mtime, 0)
                            wtstate[wt] = dict(newest=wn, state=None)
                        if wtstate[wt]['newest'] > cutoff:
                            why = 'worktree active (%s)' % wt
                u['reason'] = why
            if u['reason'] is None:
                # file-level: still referenced by full path? never delete referenced files
                if referenced(refs, path):
                    continue
                if u.get('objects_only') and (kind != 'objdir' or path.endswith(('.elf', '.ovl'))):
                    sk = skipped[unit + ' (ELF/overlays/discs)']
                    sk[0] += size; sk[1] += 1; sk[2] = u['objects_only']
                    continue
                if mtime > cutoff:
                    continue
                u['files'].append((path, size, mtime, nlink, kind))
                u['kinds'].add(kind)
                if nlink > 1:
                    u['shared'] += size
                else:
                    u['bytes'] += size
            else:
                sk = skipped[unit]
                sk[0] += size
                sk[1] += 1
                sk[2] = u['reason']

    # worktree states (only for worktrees we would prune in)
    todo = [u for u in units.values() if u['reason'] is None and u['files']]
    backups = []
    for u in todo:
        wt = u['wt']
        if wt and wtstate[wt]['state'] is None:
            dirty, unp = worktree_state(wt)
            wtstate[wt]['state'] = (dirty, unp)
        if wt and any(wtstate[wt]['state']):
            u['wtflag'] = 'dirty' if wtstate[wt]['state'][0] else 'unpushed %d' % wtstate[wt]['state'][1]

    # report
    per_top = defaultdict(lambda: [0, 0, 0])
    for u in todo:
        t = per_top[u['top']]
        t[0] += u['bytes']; t[1] += u['shared']; t[2] += len(u['files'])
    total = sum(v[0] for v in per_top.values())
    shared = sum(v[1] for v in per_top.values())
    tag = ('apply' if a.apply else 'dryrun') + ('-winonly' if a.windows_only else '')
    detail = MAN / ('%s-%s-units.tsv' % (ts, tag))
    with open(detail, 'w') as f:
        f.write('status\tunit\tbytes\tshared_bytes\tfiles\tkinds\tidle_h\tworktree\treason\n')
        for u in sorted(todo, key=lambda u: -u['bytes']):
            f.write('prune\t%s\t%d\t%d\t%d\t%s\t%.1f\t%s\t%s\n' % (u['unit'], u['bytes'], u['shared'], len(u['files']),
                    ','.join(sorted(u['kinds'])), (now - u['newest']) / 3600, u['wt'] or '',
                    (u.get('wtflag', '') + ' ' + u.get('objects_only', '')).strip()))
        for unit, (b, n, why) in sorted(skipped.items(), key=lambda kv: -kv[1][0]):
            f.write('keep\t%s\t%d\t0\t%d\t\t\t\t%s\n' % (unit, b, n, why))
        for p, s, why in big_src:
            f.write('keep\t%s\t%d\t0\t1\tdisc\t\t\t%s\n' % (p, s, why))
    if a.list:
        for u in sorted(todo, key=lambda u: -u['bytes']):
            log('  %8.2f GB %s [%s]%s' % (u['bytes'] / 1024 ** 3, u['unit'], ','.join(sorted(u['kinds'])),
                                          (' worktree ' + u['wtflag']) if u.get('wtflag') else ''))
    log('kept (largest protected units):')
    for unit, (b, n, why) in sorted(skipped.items(), key=lambda kv: -kv[1][0])[:25]:
        if b > 200 * 1024 ** 2:
            log('  %8.2f GB %s -- %s' % (b / 1024 ** 3, unit, why))
    for p, s, why in big_src:
        log('  %8.2f GB %s -- %s' % (s / 1024 ** 3, p, why))

    freed = defaultdict(int)
    if a.apply and todo:
        manifest = MAN / ('%s.tsv' % ts)
        mf = open(manifest, 'w')
        mf.write('path\tbytes\tmtime\tnlink\treason\n')
        done_wt = set()
        for u in sorted(todo, key=lambda u: -u['bytes']):
            if u.get('wtflag') and u['wt'] not in done_wt:
                b = backup_worktree(u['wt'], ts)
                backups.append((u['wt'], u['wtflag'], b))
                done_wt.add(u['wt'])
            # re-check the unit is still idle (a build may have started since the scan)
            busy = False
            for root_, dirs, files in os.walk(u['unit']):
                dirs[:] = [d for d in dirs if d != '.git']
                try:
                    if os.lstat(root_).st_mtime > cutoff:
                        busy = True
                        break
                except OSError:
                    pass
                if busy:
                    break
            if busy:
                log('  skip (became active): %s' % u['unit'])
                continue
            for path, size, mtime, nlink, kind in u['files']:
                try:
                    s = os.lstat(path)
                except OSError:
                    continue
                if s.st_mtime > cutoff or not stat.S_ISREG(s.st_mode):
                    continue
                try:
                    os.unlink(path)
                except OSError as e:
                    log('  could not delete %s: %s' % (path, e))
                    continue
                if s.st_nlink == 1:
                    freed[u['top']] += s.st_size
                mf.write('%s\t%d\t%s\t%d\t%s\n' % (path, s.st_size, time.strftime('%Y-%m-%dT%H:%M:%S',
                         time.localtime(s.st_mtime)), s.st_nlink, kind + (' ' + u['wtflag'] if u.get('wtflag') else '')))
        mf.close()
        log('manifest: %s' % manifest)
    log('%s per top-level dir (sole-link bytes; +hard-linked bytes freed only when every link goes):' %
        ('FREED' if a.apply else 'WOULD FREE'))
    rows = sorted(per_top.items(), key=lambda kv: -kv[1][0])
    for top, (b, sh, n) in rows:
        val = freed[top] if a.apply else b
        if val or sh:
            log('  %8.2f GB  (+%.2f GB linked) %6d files  %s' % (val / 1024 ** 3, sh / 1024 ** 3, n, top))
    log('TOTAL %s %s (+%s hard-linked); units %d; details %s' % ('freed' if a.apply else 'would free',
        human(sum(freed.values()) if a.apply else total), human(shared), len(todo), detail))
    for wt, flag, b in backups:
        log('backup: %s (%s) -> %s.*' % (wt, flag, b))
    if not a.no_windows:
        run_windows(a, ts)
    if not a.apply:
        flagged = sorted({(u['wt'], u['wtflag']) for u in todo if u.get('wtflag')})
        for wt, flag in flagged:
            log('would back up first: %s (%s)' % (wt, flag))


def run_windows(a, ts):
    """The evidence roots go through the PowerShell twin (9p walks of the evidence roots take far too long)."""
    ps1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prune_build_outputs.ps1')
    win = subprocess.run(['wslpath', '-w', ps1], capture_output=True, text=True).stdout.strip()
    psexe = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
    cmd = [psexe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', win, '-IdleHours', str(a.idle_hours),
           '-Stamp', ts]
    if a.apply:
        cmd.append('-Apply')
    if a.list:
        cmd.append('-List')
    r = subprocess.run(cmd, cwd='/mnt/c', capture_output=True)
    sys.stdout.write(r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n'))
    if r.returncode:
        sys.stdout.write('prune(win): powershell exit %d %s\n' % (r.returncode, r.stderr.decode('utf-8', 'replace')[:2000]))
    sys.stdout.flush()


if __name__ == '__main__':
    main()
